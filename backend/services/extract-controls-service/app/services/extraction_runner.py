"""Async extraction / merge runners — no RabbitMQ; driven by WebSocket connect."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
import os
from pathlib import Path

from sqlalchemy import select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    DocumentExtraction,
    Framework,
)
from vora_shared.models.framework_merge import FrameworkMerge
from vora_shared.models.deployment_package_merge import DeploymentPackageMerge
from app.services.control_extractor import (
    extract_framework_controls,
    convert_to_section_structure,
)
from app.services.control_merger import (
    get_framework_previous_controls,
    merge_controls_cumulative,
)

logger = logging.getLogger(__name__)

MSG_EXTRACTION_COMPLETED = "Extraction completed"
MSG_DEPLOYMENT_EXTRACTION_COMPLETED = "Deployment framework extraction completed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


def _compute_merge_key(file_hashes: list[str]) -> str:
    """Compute deterministic mergeKey from sorted file hashes."""
    import hashlib
    if not file_hashes:
        return ""
    s = "|".join(sorted(file_hashes))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()





def _status_history(
    uploaded: str, processing: str, completed: str | None = None, failed: str | None = None
) -> dict[str, Any]:
    history = [
        {"status": "uploaded", "timestamp": uploaded, "message": "Document uploaded"},
        {"status": "processing", "timestamp": processing, "message": "Extraction in progress"},
    ]
    if failed:
        history.append({"status": "failed", "timestamp": failed, "message": "Extraction failed"})
        return {
            "processing_time_seconds": 0,
            "completed_at": failed,
            "history": history,
        }
    completed = completed or _iso()
    history.append({"status": "completed", "timestamp": completed, "message": MSG_EXTRACTION_COMPLETED})
    try:
        start = datetime.fromisoformat(uploaded.replace("Z", "+00:00"))
        end = datetime.fromisoformat(completed.replace("Z", "+00:00"))
        elapsed = max(0.0, (end - start).total_seconds())
    except Exception:  # noqa: BLE001
        elapsed = 1.0
    return {
        "processing_time_seconds": elapsed,
        "completed_at": completed,
        "history": history,
    }


def _load_document_chunks(file_path: str, chunk_size: int = 1000) -> list[str]:
    """Load document from file and chunk it for processing"""
    try:
        if not file_path or not os.path.exists(file_path):
            logger.error(f"[LOAD] File not found: {file_path}")
            return []

        ext = Path(file_path).suffix.lower()
        logger.info(f"[LOAD] Loading document | ext={ext} | path={file_path}")

        text_lines = []

        # Handle PDF
        if ext == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        # Extract tables
                        tables = page.extract_tables()
                        if tables:
                            for table in tables:
                                for row in table:
                                    row_text = " ".join([cell or "" for cell in row if cell])
                                    if row_text.strip():
                                        text_lines.append(row_text.strip())
                        # Extract text
                        page_text = page.extract_text()
                        if page_text:
                            for line in page_text.split("\n"):
                                if line.strip():
                                    text_lines.append(line.strip())
            except ImportError:
                logger.warning("[LOAD] pdfplumber not available, trying pypdf")
                import pypdf
                reader = pypdf.PdfReader(file_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        for line in page_text.split("\n"):
                            if line.strip():
                                text_lines.append(line.strip())

        # Handle Word documents
        elif ext == ".docx":
            try:
                from docx import Document
                doc = Document(file_path)
                for para in doc.paragraphs:
                    if para.text.strip():
                        text_lines.append(para.text.strip())
            except Exception as e:
                logger.error(f"[LOAD] Failed to load docx: {e}")
                return []

        # Handle Excel
        elif ext in [".xls", ".xlsx"]:
            try:
                import pandas as pd
                xls = pd.ExcelFile(file_path)
                for sheet in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet)
                    text_lines.append(df.to_string(index=False))
            except Exception as e:
                logger.error(f"[LOAD] Failed to load excel: {e}")
                return []

        # Handle text files
        elif ext in [".txt", ".csv"]:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            text_lines.append(line.strip())
            except Exception as e:
                logger.error(f"[LOAD] Failed to load text file: {e}")
                return []

        else:
            logger.error(f"[LOAD] Unsupported file type: {ext}")
            return []

        if not text_lines:
            logger.warning(f"[LOAD] No text extracted from {file_path}")
            return []

        # Chunk the text
        chunks = []
        current = ""
        for line in text_lines:
            if len(current) + len(line) <= chunk_size:
                current += " " + line
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = line

        if current.strip():
            chunks.append(current.strip())

        logger.info(f"[LOAD] ✅ Loaded {len(text_lines)} lines into {len(chunks)} chunks")
        return chunks

    except Exception as e:
        logger.error(f"[LOAD] ❌ Failed to load document: {e}", exc_info=True)
        return []


def _find_file_version(file_versions: list[Any], file_id: str) -> tuple[int | None, dict | None]:
    for i, fv in enumerate(file_versions or []):
        if not isinstance(fv, dict):
            continue
        if str(fv.get("fileId")) == str(file_id):
            return i, dict(fv)
    return None, None


async def _update_framework_ai_status(
    session: Any, framework_id: str, file_id: str, status_data: dict[str, Any], replace: bool = False
) -> None:
    fw = await session.get(Framework, framework_id)
    if not fw:
        return
    versions = list(fw.fileVersions or [])
    idx, fv = _find_file_version(versions, file_id)
    if idx is None or fv is None:
        return

    if replace:
        fv["aiExtraction"] = status_data
    else:
        ai = dict(fv.get("aiExtraction") or {})
        ai.update(status_data)
        fv["aiExtraction"] = ai

    versions[idx] = fv
    fw.fileVersions = versions


async def run_framework_extraction(framework_id: str, file_id: str) -> None:
    """Load Framework, extract controls using AI, save to document_extraction table"""
    framework_id = str(framework_id).strip()
    file_id = str(file_id).strip()
    uploaded_ts = _iso()

    logger.info(f"{'='*80}")
    logger.info(f"[EXTRACT-START] Framework Extraction Started")
    logger.info(f"  Framework ID: {framework_id}")
    logger.info(f"  File ID: {file_id}")
    logger.info(f"  Timestamp: {uploaded_ts}")
    logger.info(f"{'='*80}")

    try:
        # Get framework and file info
        logger.info(f"[EXTRACT] Step 1: Loading framework from database...")
        async with session_scope() as session:
            framework = await session.get(Framework, framework_id)
            if not framework:
                logger.error(f"[EXTRACT] ❌ Framework not found: {framework_id}")
                return

            logger.info(f"[EXTRACT] ✅ Framework found: {framework.frameworkName}")

            # Find file version
            file_versions = framework.fileVersions or []
            logger.info(f"[EXTRACT] Found {len(file_versions)} file versions in framework")
            
            file_info = None
            for fv in file_versions:
                if isinstance(fv, dict) and str(fv.get("fileId")) == file_id:
                    file_info = fv
                    break

            if not file_info:
                logger.error(f"[EXTRACT] ❌ File not found in framework: {file_id}")
                return

            file_path = file_info.get("fileUrl")
            file_hash = file_info.get("fileHash")
            logger.info(f"[EXTRACT] ✅ File found")
            logger.info(f"  File Path: {file_path}")
            logger.info(f"  File Hash: {file_hash}")

            # Update status to processing
            logger.info(f"[EXTRACT] Step 2: Updating status to 'processing'...")
            await _update_framework_ai_status(
                session, framework_id, file_id,
                {
                    "status": "processing",
                    "timestamp": uploaded_ts,
                    "message": "AI extraction in progress",
                },
            )
            logger.info(f"[EXTRACT] ✅ Status updated to 'processing'")

        # Load document from file
        logger.info(f"[EXTRACT] Step 3: Loading document from disk...")
        chunks = await asyncio.to_thread(_load_document_chunks, file_path)
        if not chunks:
            logger.error(f"[EXTRACT] ❌ No text extracted from document")
            async with session_scope() as session:
                await _update_framework_ai_status(
                    session, framework_id, file_id,
                    {
                        "status": "failed",
                        "timestamp": _iso(),
                        "message": "Failed to extract text from document",
                    },
                )
            return

        logger.info(f"[EXTRACT] ✅ Document loaded: {len(chunks)} chunks extracted")

        # Extract controls using AI
        logger.info(f"[EXTRACT] Step 4: Running AI extraction...")
        controls_flat = await asyncio.to_thread(extract_framework_controls, chunks, framework_id)
        logger.info(f"[EXTRACT] ✅ AI extraction complete: {len(controls_flat)} controls extracted")

        # Convert to section structure
        logger.info(f"[EXTRACT] Step 5: Converting to section structure...")
        controls_structured = await asyncio.to_thread(convert_to_section_structure, controls_flat, resource_type="framework")
        logger.info(f"[EXTRACT] ✅ Structure converted: {len(controls_structured)} sections")

        # Merge with previous versions if exists
        merge_summary = None  # Initialize for later use
        logger.info(f"[EXTRACT] Step 5b: Checking for previous versions to merge...")
        async with session_scope() as session:
            framework = await session.get(Framework, framework_id)
            if framework:
                file_versions = framework.fileVersions or []
                old_sections, prev_version, prev_hash = await asyncio.to_thread(
                    get_framework_previous_controls, file_versions, file_info.get("fileVersion")
                )

                if old_sections:
                    logger.info(f"[EXTRACT] Found previous version: {prev_version}")
                    logger.info(f"[EXTRACT] Previous file hash: {prev_hash}")
                    
                    # Perform cumulative merge
                    controls_structured, merge_summary = await asyncio.to_thread(
                        merge_controls_cumulative, old_sections, controls_structured
                    )
                    
                    logger.info(f"[EXTRACT] ✅ Merge complete:")
                    logger.info(f"  - Merged controls: {merge_summary.get('merged_controls', 0)}")
                    logger.info(f"  - New controls: {merge_summary.get('new_controls', 0)}")
                    logger.info(f"  - New deployment points: {merge_summary.get('new_dps', 0)}")
                    logger.info(f"  - New sections: {merge_summary.get('new_sections', 0)}")
                else:
                    logger.info(f"[EXTRACT] No previous version to merge")
                    merge_summary = None

        # Build controls payload
        total_controls = sum(len(s.get("controls", [])) for s in controls_structured)
        controls_payload = {
            "total_controls": total_controls,
            "total_sections": len(controls_structured),
            "controls_data": controls_structured,
        }
        logger.info(f"[EXTRACT] Total controls: {total_controls}")

        completed_ts = _iso()
        history = _status_history(uploaded_ts, uploaded_ts, completed_ts)

        # Prepare extraction data with merge summary
        extraction_data = {
            "status": "extracted",
            "timestamp": completed_ts,
            "message": "AI extraction completed",
            "statusHistory": {
                "processingTimeSeconds": history["processing_time_seconds"],
                "completedAt": history["completed_at"],
                "history": [
                    {
                        "status": ("extracted" if h["status"] == "completed" else h["status"]),
                        "timestamp": h["timestamp"],
                        "message": h.get("message"),
                    }
                    for h in history["history"]
                ],
            },
            "controls": controls_payload,
        }

        # Add merge summary if merge was performed
        if merge_summary:
            extraction_data["mergeSummary"] = merge_summary

        # Update framework with extracted data
        logger.info(f"[EXTRACT] Step 6: Saving to database...")
        async with session_scope() as session:
            # Update framework's aiExtraction
            logger.info(f"[EXTRACT] 6a: Updating framework's aiExtraction...")
            await _update_framework_ai_status(
                session, framework_id, file_id,
                extraction_data,
                replace=True,
            )
            logger.info(f"[EXTRACT] ✅ Framework updated")

            # Save to document_extraction table (by fileHash) - PRIMARY TABLE
            if file_hash:
                logger.info(f"[EXTRACT] 6b: Saving to document_extraction table...")
                doc_extraction = await _get_or_create_doc_extraction(
                    session, file_hash, None
                )
                doc_extraction.aiExtraction = extraction_data
                session.add(doc_extraction)
                await session.flush()
                await session.commit()
                logger.info(f"[EXTRACT] ✅ Saved to document_extractions table")
                logger.info(f"  Table: document_extractions")
                logger.info(f"  ID: {doc_extraction.id}")
                logger.info(f"  FileHash: {file_hash}")
                logger.info(f"  Status: extracted")
                logger.info(f"  Total Controls: {total_controls}")
            else:
                logger.warning(f"[EXTRACT] ⚠️ No fileHash - skipping document_extraction save")

            # Save merge to framework_merges table if merge happened
            if merge_summary:
                logger.info(f"[EXTRACT] 6c: Saving merge to framework_merges table...")
                all_file_hashes = []
                all_file_versions = []
                for fv in framework.fileVersions or []:
                    if isinstance(fv, dict):
                        fv_hash = fv.get("fileHash")
                        fv_ver = fv.get("fileVersion")
                        if fv_hash:
                            all_file_hashes.append(fv_hash)
                        if fv_ver:
                            all_file_versions.append(fv_ver)

                await _save_merge_to_framework_merge(
                    session,
                    framework_id,
                    all_file_hashes,
                    all_file_versions,
                    controls_structured,
                    merge_summary,
                )
                logger.info(f"[EXTRACT] ✅ Saved merge to framework_merges table")
                logger.info(f"  Merge key: {_compute_merge_key(all_file_hashes)[:16]}...")
                logger.info(f"  Files merged: {len(all_file_hashes)}")

        logger.info(f"{'='*80}")
        logger.info(f"[EXTRACT-SUCCESS] ✅ Framework extraction complete!")
        logger.info(f"  Framework ID: {framework_id}")
        logger.info(f"  File ID: {file_id}")
        logger.info(f"  Total Controls: {total_controls}")
        logger.info(f"  Total Sections: {len(controls_structured)}")
        logger.info(f"  Processing Time: {history['processing_time_seconds']:.2f}s")
        logger.info(f"[EXTRACT-SAVED] ✅ Data saved to: document_extractions table")
        logger.info(f"{'='*80}")

    except Exception as exc:
        logger.error(f"{'='*80}")
        logger.error(f"[EXTRACT-ERROR] ❌ Framework extraction failed!")
        logger.error(f"  Framework ID: {framework_id}")
        logger.error(f"  File ID: {file_id}")
        logger.error(f"  Error: {str(exc)}")
        logger.error(f"{'='*80}")
        logger.exception(f"[EXTRACT] Exception traceback:")
        
        fail_ts = _iso()
        try:
            async with session_scope() as session:
                await _update_framework_ai_status(
                    session, framework_id, file_id,
                    {
                        "status": "failed",
                        "timestamp": fail_ts,
                        "message": f"Extraction failed: {str(exc)}",
                    },
                )
                logger.info(f"[EXTRACT] Updated status to 'failed' in database")
        except Exception as db_exc:
            logger.error(f"[EXTRACT] Failed to update status in database: {db_exc}")


async def run_deployment_framework_extraction(df_id: str, pkg_ver: str, file_id: str) -> None:
    """Extract controls from deployment framework document."""
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()
    file_id = str(file_id).strip()
    uploaded_ts = _iso()

    logger.info(f"{'='*80}")
    logger.info(f"[DEPLOYMENT-EXTRACT-START] Deployment Framework Extraction Started")
    logger.info(f"  Deployment Framework ID: {df_id}")
    logger.info(f"  Package Version: {pkg_ver}")
    logger.info(f"  File ID: {file_id}")
    logger.info(f"  Timestamp: {uploaded_ts}")
    logger.info(f"{'='*80}")

    try:
        # Get deployment framework and file info
        logger.info(f"[DEPLOYMENT-EXTRACT] Step 1: Loading deployment framework from database...")
        async with session_scope() as session:
            from vora_shared.models import DeploymentFramework
            
            df = await session.get(DeploymentFramework, df_id)
            if not df:
                logger.error(f"[DEPLOYMENT-EXTRACT] ❌ Deployment Framework not found: {df_id}")
                return

            logger.info(f"[DEPLOYMENT-EXTRACT] ✅ Deployment Framework found: {df.frameworkName}")

            # Find package
            packages = df.packages or []
            pkg_info = None
            for pkg in packages:
                if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                    pkg_info = pkg
                    break

            if not pkg_info:
                logger.error(f"[DEPLOYMENT-EXTRACT] ❌ Package not found: {pkg_ver}")
                return

            # Find file in package documents
            documents = pkg_info.get("documents") or []
            file_info = None
            for doc in documents:
                if isinstance(doc, dict) and str(doc.get("fileId")) == file_id:
                    file_info = doc
                    break

            if not file_info:
                logger.error(f"[DEPLOYMENT-EXTRACT] ❌ File not found in package: {file_id}")
                return

            file_path = file_info.get("fileUrl")
            file_hash = file_info.get("fileHash")
            logger.info(f"[DEPLOYMENT-EXTRACT] ✅ File found")
            logger.info(f"  File Path: {file_path}")
            logger.info(f"  File Hash: {file_hash}")

        # Load document from file
        logger.info(f"[DEPLOYMENT-EXTRACT] Step 2: Loading document from disk...")
        chunks = await asyncio.to_thread(_load_document_chunks, file_path)
        if not chunks:
            logger.error(f"[DEPLOYMENT-EXTRACT] ❌ No text extracted from document")
            return

        logger.info(f"[DEPLOYMENT-EXTRACT] ✅ Document loaded: {len(chunks)} chunks extracted")

        # Extract controls using AI (client controls for deployment frameworks)
        logger.info(f"[DEPLOYMENT-EXTRACT] Step 3: Running AI extraction...")
        controls_flat = await asyncio.to_thread(extract_framework_controls, chunks, df_id)
        logger.info(f"[DEPLOYMENT-EXTRACT] ✅ AI extraction complete: {len(controls_flat)} controls extracted")

        # Convert to section structure
        logger.info(f"[DEPLOYMENT-EXTRACT] Step 4: Converting to section structure...")
        controls_structured = await asyncio.to_thread(convert_to_section_structure, controls_flat, resource_type="deployment")
        logger.info(f"[DEPLOYMENT-EXTRACT] ✅ Structure converted: {len(controls_structured)} sections")

        # Build controls payload
        total_controls = sum(len(s.get("controls", [])) for s in controls_structured)
        controls_payload = {
            "total_controls": total_controls,
            "total_sections": len(controls_structured),
            "controls_data": controls_structured,
        }
        logger.info(f"[DEPLOYMENT-EXTRACT] Total controls: {total_controls}")

        completed_ts = _iso()
        history = _status_history(uploaded_ts, uploaded_ts, completed_ts)

        # Prepare extraction data
        extraction_data = {
            "status": "extracted",
            "timestamp": completed_ts,
            "message": MSG_DEPLOYMENT_EXTRACTION_COMPLETED,
            "statusHistory": {
                "processingTimeSeconds": history["processing_time_seconds"],
                "completedAt": history["completed_at"],
                "history": [
                    {
                        "status": ("extracted" if h["status"] == "completed" else h["status"]),
                        "timestamp": h["timestamp"],
                        "message": h.get("message"),
                    }
                    for h in history["history"]
                ],
            },
            "controls": controls_payload,
        }

        # Update deployment framework with extracted data
        logger.info(f"[DEPLOYMENT-EXTRACT] Step 5: Saving to database...")
        async with session_scope() as session:
            from vora_shared.models import DeploymentFramework
            
            df = await session.get(DeploymentFramework, df_id)
            if df:
                packages = list(df.packages or [])
                for pkg in packages:
                    if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                        documents = list(pkg.get("documents") or [])
                        for doc in documents:
                            if isinstance(doc, dict) and str(doc.get("fileId")) == file_id:
                                doc["aiExtraction"] = extraction_data
                                break
                        pkg["documents"] = documents
                        break
                df.packages = packages
                session.add(df)
                await session.flush()
                await session.commit()
                logger.info(f"[DEPLOYMENT-EXTRACT] ✅ Saved to deployment_frameworks table")

            # Save to document_extraction table (by fileHash) 
            if file_hash:
                logger.info(f"[DEPLOYMENT-EXTRACT] Saving to document_extraction table...")
                doc_extraction = await _get_or_create_doc_extraction(session, file_hash, None)
                doc_extraction.aiExtraction = extraction_data
                session.add(doc_extraction)
                await session.flush()
                await session.commit()
                logger.info(f"[DEPLOYMENT-EXTRACT] ✅ Saved to document_extractions table")

        logger.info(f"{'='*80}")
        logger.info(f"[DEPLOYMENT-EXTRACT-SUCCESS] ✅ Deployment Framework extraction complete!")
        logger.info(f"  Deployment Framework ID: {df_id}")
        logger.info(f"  Package Version: {pkg_ver}")
        logger.info(f"  File ID: {file_id}")
        logger.info(f"  Total Controls: {total_controls}")
        logger.info(f"  Total Sections: {len(controls_structured)}")
        logger.info(f"  Processing Time: {history['processing_time_seconds']:.2f}s")
        logger.info(f"{'='*80}")

    except Exception as exc:
        logger.error(f"{'='*80}")
        logger.error(f"[DEPLOYMENT-EXTRACT-ERROR] ❌ Deployment Framework extraction failed!")
        logger.error(f"  Deployment Framework ID: {df_id}")
        logger.error(f"  Package Version: {pkg_ver}")
        logger.error(f"  File ID: {file_id}")
        logger.error(f"  Error: {str(exc)}")
        logger.error(f"{'='*80}")
        logger.exception(f"[DEPLOYMENT-EXTRACT] Exception traceback:")


async def run_deployment_package_merge(df_id: str, pkg_ver: str) -> None:
    """Merge all extracted documents in a deployment framework package."""
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()

    logger.info(f"{'='*80}")
    logger.info(f"[PACKAGE-MERGE-START] Package Merge Started")
    logger.info(f"  Deployment Framework ID: {df_id}")
    logger.info(f"  Package Version: {pkg_ver}")
    logger.info(f"{'='*80}")

    try:
        async with session_scope() as session:
            from vora_shared.models import DeploymentFramework

            df = await session.get(DeploymentFramework, df_id)
            if not df:
                logger.error(f"[PACKAGE-MERGE] ❌ Deployment Framework not found: {df_id}")
                return

            # Find package
            packages = df.packages or []
            pkg_info = None
            for pkg in packages:
                if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                    pkg_info = pkg
                    break

            if not pkg_info:
                logger.error(f"[PACKAGE-MERGE] ❌ Package not found: {pkg_ver}")
                return

            logger.info(f"[PACKAGE-MERGE] Package found | version={pkg_ver}")

            # Collect all extracted controls from documents
            documents = pkg_info.get("documents") or []
            all_sections = []
            file_hashes = []
            file_ids = []
            merge_history = []

            for doc in documents:
                if not isinstance(doc, dict):
                    continue

                file_id = doc.get("fileId")
                file_hash = doc.get("fileHash")
                ai_extraction = doc.get("aiExtraction")

                if not ai_extraction:
                    logger.info(f"[PACKAGE-MERGE] Skipping document - no extraction | fileId={file_id}")
                    continue

                status = ai_extraction.get("status") if isinstance(ai_extraction, dict) else None
                if status != "extracted":
                    logger.info(f"[PACKAGE-MERGE] Skipping document - not extracted | fileId={file_id} | status={status}")
                    continue

                if file_hash:
                    file_hashes.append(file_hash)
                if file_id:
                    file_ids.append(file_id)

                # Extract controls from extraction data
                if isinstance(ai_extraction, dict):
                    controls_block = ai_extraction.get("controls", {})
                    if isinstance(controls_block, dict):
                        controls_data = controls_block.get("controls_data", [])
                    elif isinstance(controls_block, list):
                        controls_data = controls_block
                    else:
                        controls_data = []

                    if controls_data:
                        all_sections.extend(controls_data)
                        merge_history.append({
                            "fileId": file_id,
                            "fileName": doc.get("originalFileName", file_id),
                            "status": "merged",
                            "timestamp": _iso(),
                        })

                        logger.info(
                            f"[PACKAGE-MERGE] Added document | fileId={file_id} | "
                            f"sections={len(controls_data)}"
                        )

            if not all_sections:
                logger.warning(f"[PACKAGE-MERGE] ⚠️ No extracted sections found in package")
                return

            # Merge controls (cumulative)
            logger.info(f"[PACKAGE-MERGE] Step 1: Merging {len(file_ids)} documents...")
            merged_controls, merge_summary = await asyncio.to_thread(
                merge_controls_cumulative, [], all_sections
            )

            logger.info(f"[PACKAGE-MERGE] ✅ Merge complete:")
            logger.info(f"  - Total controls: {merge_summary.get('new_controls', 0)}")
            logger.info(f"  - Total sections: {len(merged_controls)}")

            # Build payload
            controls_payload = {
                "total_controls": sum(len(s.get("controls", [])) for s in merged_controls),
                "total_sections": len(merged_controls),
                "controls_data": merged_controls,
            }

            # Save to deployment_package_merges table
            logger.info(f"[PACKAGE-MERGE] Step 2: Saving to database...")
            merge_key = _compute_merge_key(file_hashes)

            existing = (
                await session.execute(
                    select(DeploymentPackageMerge).where(
                        DeploymentPackageMerge.deploymentFrameworkId == df_id,
                        DeploymentPackageMerge.packageVersion == pkg_ver,
                    )
                )
            ).scalar_one_or_none()

            if existing:
                logger.info(f"[PACKAGE-MERGE] Updating existing package merge...")
                existing.status = "merged"
                existing.mergeKey = merge_key
                existing.fileHashes = file_hashes
                existing.fileIds = file_ids
                existing.controls = controls_payload
                existing.summary = merge_summary
                existing.mergeHistory = merge_history
                session.add(existing)
            else:
                merge_record = DeploymentPackageMerge(
                    id=new_id(),
                    deploymentFrameworkId=df_id,
                    packageVersion=pkg_ver,
                    status="merged",
                    mergeKey=merge_key,
                    fileHashes=file_hashes,
                    fileIds=file_ids,
                    controls=controls_payload,
                    summary=merge_summary,
                    mergeHistory=merge_history,
                )
                session.add(merge_record)
                logger.info(f"[PACKAGE-MERGE] ✅ Saved package merge record")

            await session.flush()
            await session.commit()

            logger.info(f"{'='*80}")
            logger.info(f"[PACKAGE-MERGE-SUCCESS] ✅ Package merge complete!")
            logger.info(f"  Deployment Framework ID: {df_id}")
            logger.info(f"  Package Version: {pkg_ver}")
            logger.info(f"  Files merged: {len(file_ids)}")
            logger.info(f"  Total controls: {controls_payload['total_controls']}")
            logger.info(f"[PACKAGE-MERGE-KEY] {merge_key[:16]}...")
            logger.info(f"{'='*80}")

    except Exception as exc:
        logger.error(f"[PACKAGE-MERGE-ERROR] ❌ Package merge failed!")
        logger.error(f"  Deployment Framework ID: {df_id}")
        logger.error(f"  Package Version: {pkg_ver}")
        logger.error(f"  Error: {str(exc)}")
        logger.exception(f"[PACKAGE-MERGE] Exception traceback:")


async def _get_or_create_doc_extraction(
    session: Any, file_hash: str, existing_id: str | None
) -> DocumentExtraction:
    if existing_id:
        row = await session.get(DocumentExtraction, str(existing_id))
        if row:
            return row
    if file_hash:
        row = (
            await session.execute(select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash))
        ).scalar_one_or_none()
        if row:
            return row
    row = DocumentExtraction(id=new_id(), fileHash=file_hash or new_id(), aiExtraction={})
    session.add(row)
    await session.flush()
    return row


async def _save_merge_to_framework_merge(
    session: Any,
    framework_id: str,
    file_hashes: list[str],
    file_versions: list[str],
    merged_controls: list[dict[str, Any]],
    merge_summary: dict[str, Any],
) -> None:
    """Save merged controls to framework_merges table (canonical storage by mergeKey)."""
    merge_key = _compute_merge_key(file_hashes)
    
    existing = (
        await session.execute(
            select(FrameworkMerge).where(
                FrameworkMerge.frameworkId == framework_id,
                FrameworkMerge.mergeKey == merge_key,
            )
        )
    ).scalar_one_or_none()

    controls_payload = {
        "total_controls": sum(len(s.get("controls", [])) for s in merged_controls),
        "total_sections": len(merged_controls),
        "controls_data": merged_controls,
    }

    if existing:
        logger.info(f"[MERGE-TABLE] Updating existing merge | key={merge_key[:16]}...")
        existing.controls = controls_payload
        existing.summary = merge_summary
        existing.fileVersions = file_versions
        existing.mergeHashes = sorted(file_hashes)
        session.add(existing)
    else:
        merge_record = FrameworkMerge(
            id=new_id(),
            frameworkId=framework_id,
            mergeKey=merge_key,
            mergeHashes=sorted(file_hashes),
            fileVersions=file_versions,
            controls=controls_payload,
            summary=merge_summary,
        )
        session.add(merge_record)
        logger.info(
            f"[MERGE-TABLE] ✅ Saved merge | fw={framework_id} | key={merge_key[:16]}... "
            f"| hashes={len(file_hashes)} | controls={controls_payload['total_controls']}"
        )


