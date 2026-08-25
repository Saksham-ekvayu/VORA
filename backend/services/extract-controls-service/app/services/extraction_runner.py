"""Async extraction / merge runners — no RabbitMQ; driven by WebSocket connect."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.control_extractor import (
    convert_to_section_structure,
    extract_framework_controls,
)
from app.services.control_merger import (
    get_framework_previous_controls,
    merge_controls_cumulative,
)
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    DeploymentFramework,
    DeploymentPackageMerge,
    DocumentExtraction,
    Framework,
    FrameworkMerge,
)

logger = logging.getLogger(__name__)

MSG_EXTRACTION_COMPLETED = "Extraction completed"
MSG_DEPLOYMENT_EXTRACTION_COMPLETED = "Deployment framework extraction completed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


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
    history.append(
        {"status": "completed", "timestamp": completed, "message": MSG_EXTRACTION_COMPLETED}
    )
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
            logger.info("[LOAD] Starting PDF extraction...")
            text_extracted = False

            # Try 1: pdfplumber text extraction
            try:
                import pdfplumber

                logger.info("[LOAD] Attempt 1: pdfplumber text extraction...")
                with pdfplumber.open(file_path) as pdf:
                    logger.info(f"[LOAD] PDF has {len(pdf.pages)} pages")
                    if len(pdf.pages) > 0:
                        for page_num, page in enumerate(pdf.pages, 1):
                            try:
                                page_text = page.extract_text()
                                if page_text and page_text.strip():
                                    for line in page_text.split("\n"):
                                        if line.strip():
                                            text_lines.append(line.strip())
                                    text_extracted = True
                            except Exception as e:
                                logger.warning(f"[LOAD] Page {page_num} pdfplumber failed: {e}")
                        if text_extracted:
                            logger.info(f"[LOAD]  pdfplumber extracted {len(text_lines)} lines")
            except Exception as e:
                logger.warning(f"[LOAD] pdfplumber failed: {e}")

            # Try 1.5: If pdfplumber didn't work (or mis-reported "0 pages"
            # on a PDF that actually DOES have a real text layer), try
            # PyMuPDF (fitz) before falling back to lossy OCR. Different
            # parser than pdfplumber — frequently succeeds exactly where
            # pdfplumber fails. This is what avoids OCR-style corruption
            # (e.g. "A.11.3.1" being misread as "AI.3.1") on PDFs that
            # actually have a real text layer.
            if not text_extracted:
                try:
                    import fitz  # PyMuPDF

                    logger.info("[LOAD] Attempt 1.5: PyMuPDF (fitz) text extraction...")
                    doc = fitz.open(file_path)
                    logger.info(f"[LOAD] PyMuPDF reports {doc.page_count} pages")
                    if doc.page_count > 0:
                        for page_num, page in enumerate(doc, 1):
                            try:
                                page_text = page.get_text("text")
                                if page_text and page_text.strip():
                                    for line in page_text.split("\n"):
                                        if line.strip():
                                            text_lines.append(line.strip())
                                    text_extracted = True
                            except Exception as e:
                                logger.warning(f"[LOAD] Page {page_num} PyMuPDF failed: {e}")
                        if text_extracted:
                            logger.info(f"[LOAD]  PyMuPDF extracted {len(text_lines)} lines")
                    doc.close()
                except ImportError:
                    logger.warning(
                        "[LOAD] PyMuPDF not installed — skipping Attempt 1.5. "
                        "Run: pip install PyMuPDF"
                    )
                except Exception as e:
                    logger.warning(f"[LOAD] PyMuPDF attempt failed: {e}")

            # Try 2: If pdfplumber and PyMuPDF didn't work, use OCR
            if not text_extracted:
                logger.info("[LOAD] Attempt 2: OCR extraction (pdf2image + pytesseract)...")
                try:
                    import pdf2image
                    import pytesseract

                    logger.info("[LOAD] Converting PDF to images...")
                    images = pdf2image.convert_from_path(file_path, dpi=300)
                    logger.info(f"[LOAD] Converted to {len(images)} images")

                    if images:
                        for page_num, image in enumerate(images, 1):
                            try:
                                logger.info(f"[LOAD] OCR scanning page {page_num}/{len(images)}...")
                                ocr_text = pytesseract.image_to_string(image, lang="eng")
                                if ocr_text and ocr_text.strip():
                                    for line in ocr_text.split("\n"):
                                        if line.strip():
                                            text_lines.append(line.strip())
                                    text_extracted = True
                                    logger.info(
                                        f"[LOAD] Page {page_num}: OCR extracted {len(ocr_text.split(chr(10)))} lines"
                                    )
                            except Exception as page_err:
                                logger.warning(f"[LOAD] Page {page_num} OCR failed: {page_err}")

                        if text_extracted:
                            logger.info(
                                f"[LOAD]  OCR extraction complete: {len(text_lines)} total lines"
                            )
                    else:
                        logger.error("[LOAD]  pdf2image returned no images")

                except ImportError as imp_err:
                    logger.error(f"[LOAD]  OCR libraries not installed: {imp_err}")
                    logger.error("[LOAD] Install: pip install pdf2image pytesseract")
                    logger.error("[LOAD] Also install: apt-get install tesseract-ocr poppler-utils")
                except Exception as ocr_err:
                    logger.error(f"[LOAD]  OCR extraction failed: {ocr_err}")

            # Try 3: pypdf as last resort
            if not text_extracted:
                logger.info("[LOAD] Attempt 3: pypdf text extraction...")
                try:
                    import pypdf

                    with open(file_path, "rb") as f:
                        try:
                            reader = pypdf.PdfReader(f)
                            logger.info(f"[LOAD] pypdf found {len(reader.pages)} pages")
                            for page_num, page in enumerate(reader.pages, 1):
                                try:
                                    page_text = page.extract_text()
                                    if page_text and page_text.strip():
                                        for line in page_text.split("\n"):
                                            if line.strip():
                                                text_lines.append(line.strip())
                                        text_extracted = True
                                except Exception as e:
                                    logger.warning(f"[LOAD] Page {page_num} pypdf failed: {e}")
                            if text_extracted:
                                logger.info(f"[LOAD]  pypdf extracted {len(text_lines)} lines")
                        except Exception as reader_err:
                            logger.warning(f"[LOAD] pypdf reader failed: {reader_err}")
                except Exception as e:
                    logger.warning(f"[LOAD] pypdf not available: {e}")

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

        logger.info(f"[LOAD] Loaded {len(text_lines)} lines into {len(chunks)} chunks")
        return chunks

    except Exception as e:
        logger.error(f"[LOAD] Failed to load document: {e}", exc_info=True)
        return []


def _find_file_version(file_versions: list[Any], file_id: str) -> tuple[int | None, dict | None]:
    for i, fv in enumerate(file_versions or []):
        if not isinstance(fv, dict):
            continue
        if str(fv.get("fileId")) == str(file_id):
            return i, dict(fv)
    return None, None


async def _update_framework_ai_status(
    session: Any,
    framework_id: str,
    file_id: str,
    status_data: dict[str, Any],
    replace: bool = False,
) -> None:
    fw = await session.get(Framework, framework_id)
    if not fw:
        return
    versions = list(fw.fileVersions or [])
    idx, fv = _find_file_version(versions, file_id)
    if idx is None or fv is None:
        return

    file_hash = str(fv.get("fileHash") or "")
    existing_ai = fv.get("aiExtraction")
    existing_id = existing_ai if isinstance(existing_ai, str) else None

    # Get or create DocumentExtraction
    extraction = await _get_or_create_doc_extraction(session, file_hash, existing_id)

    if replace:
        extraction.aiExtraction = status_data
    else:
        ai = dict(extraction.aiExtraction or {})
        ai.update(status_data)
        extraction.aiExtraction = ai

    fv["aiExtraction"] = extraction.id
    versions[idx] = fv
    fw.fileVersions = versions
    flag_modified(fw, "fileVersions")
    session.add(fw)


async def _update_deployment_framework_ai_status(
    session: Any,
    df_id: str,
    pkg_ver: str,
    file_id: str,
    status_data: dict[str, Any],
    replace: bool = False,
) -> None:

    df = await session.get(DeploymentFramework, df_id)
    if not df:
        return

    packages = list(df.packages or [])
    updated = False

    for p_idx, pkg in enumerate(packages):
        if not isinstance(pkg, dict) or pkg.get("packageVersion") != pkg_ver:
            continue
        docs = list(pkg.get("documents") or [])
        for d_idx, doc in enumerate(docs):
            if isinstance(doc, dict) and str(doc.get("fileId")) == file_id:
                file_hash = str(doc.get("fileHash") or "")
                existing_ai = doc.get("aiExtraction")
                existing_id = existing_ai if isinstance(existing_ai, str) else None

                extraction = await _get_or_create_doc_extraction(session, file_hash, existing_id)

                if replace:
                    extraction.aiExtraction = status_data
                else:
                    ai = dict(extraction.aiExtraction or {})
                    ai.update(status_data)
                    extraction.aiExtraction = ai

                doc["aiExtraction"] = extraction.id
                docs[d_idx] = doc
                updated = True
                break
        if updated:
            pkg["documents"] = docs
            packages[p_idx] = pkg
            break

    if updated:
        df.packages = packages
        flag_modified(df, "packages")
        session.add(df)


async def _update_deployment_framework_mergeDocument_status(
    session: Any, df_id: str, pkg_ver: str, merge_id: str | None
) -> None:

    df = await session.get(DeploymentFramework, df_id)
    if not df:
        return

    packages = list(df.packages or [])
    updated = False

    for p_idx, pkg in enumerate(packages):
        if not isinstance(pkg, dict) or pkg.get("packageVersion") != pkg_ver:
            continue

        pkg["mergeDocument"] = merge_id
        packages[p_idx] = pkg
        updated = True
        break

    if updated:
        df.packages = packages
        flag_modified(df, "packages")
        session.add(df)



async def run_framework_extraction(framework_id: str, file_id: str) -> None:
    """Load Framework, extract controls using AI, save to document_extraction table"""
    framework_id = str(framework_id).strip()
    file_id = str(file_id).strip()
    uploaded_ts = _iso()

    logger.info(f"{'='*80}")
    logger.info("[EXTRACT-START] Framework Extraction Started")
    logger.info(f"  Framework ID: {framework_id}")
    logger.info(f"  File ID: {file_id}")
    logger.info(f"  Timestamp: {uploaded_ts}")
    logger.info(f"{'='*80}")

    try:
        # Get framework and file info
        logger.info("[EXTRACT] Step 1: Loading framework from database...")
        async with session_scope() as session:
            framework = await session.get(Framework, framework_id)
            if not framework:
                logger.error(f"[EXTRACT] Framework not found: {framework_id}")
                return

            logger.info(f"[EXTRACT] Framework found: {framework.frameworkName}")

            # Find file version
            file_versions = framework.fileVersions or []
            logger.info(f"[EXTRACT] Found {len(file_versions)} file versions in framework")

            file_info = None
            for fv in file_versions:
                if isinstance(fv, dict) and str(fv.get("fileId")) == file_id:
                    file_info = fv
                    break

            if not file_info:
                logger.error(f"[EXTRACT] File not found in framework: {file_id}")
                return

            file_path = file_info.get("fileUrl")
            file_hash = file_info.get("fileHash")
            logger.info("[EXTRACT] File found")
            logger.info(f"  File Path: {file_path}")
            logger.info(f"  File Hash: {file_hash}")

            # Update status to processing
            logger.info("[EXTRACT] Step 2: Updating status to 'processing'...")
            await _update_framework_ai_status(
                session,
                framework_id,
                file_id,
                {
                    "status": "processing",
                    "timestamp": uploaded_ts,
                    "message": "Framework ai extraction in progress",
                },
            )
            logger.info("[EXTRACT] Status updated to 'processing'")

        # Load document from file
        logger.info("[EXTRACT] Step 3: Loading document from disk...")
        chunks = await asyncio.to_thread(_load_document_chunks, file_path)
        if not chunks:
            logger.error("[EXTRACT] No text extracted from document")
            async with session_scope() as session:
                await _update_framework_ai_status(
                    session,
                    framework_id,
                    file_id,
                    {
                        "status": "failed",
                        "timestamp": _iso(),
                        "message": "Failed to extract text from document",
                    },
                )
            return

        logger.info(f"[EXTRACT] Document loaded: {len(chunks)} chunks extracted")

        # Extract controls using AI
        logger.info("[EXTRACT] Step 4: Running AI extraction...")
        controls_flat = await asyncio.to_thread(extract_framework_controls, chunks, framework_id)
        logger.info(
            f"[EXTRACT] Framework ai extraction complete: {len(controls_flat)} controls extracted"
        )

        # Convert to section structure
        logger.info("[EXTRACT] Step 5: Converting to section structure...")
        controls_structured = await asyncio.to_thread(
            convert_to_section_structure, controls_flat, resource_type="framework"
        )
        logger.info(f"[EXTRACT] Structure converted: {len(controls_structured)} sections")

        # Merge with previous versions if exists
        merge_summary = None  # Initialize for later use
        logger.info("[EXTRACT] Step 5b: Checking for previous versions to merge...")
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

                    logger.info("[EXTRACT] Merge complete:")
                    logger.info(f"  - Merged controls: {merge_summary.get('merged_controls', 0)}")
                    logger.info(f"  - New controls: {merge_summary.get('new_controls', 0)}")
                    logger.info(f"  - New deployment points: {merge_summary.get('new_dps', 0)}")
                    logger.info(f"  - New sections: {merge_summary.get('new_sections', 0)}")
                else:
                    logger.info("[EXTRACT] No previous version to merge")
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
            "message": "Framework ai extraction completed",
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
        logger.info("[EXTRACT] Step 6: Saving to database...")
        async with session_scope() as session:
            # Update framework's aiExtraction
            logger.info("[EXTRACT] 6a: Updating framework's aiExtraction...")
            await _update_framework_ai_status(
                session,
                framework_id,
                file_id,
                extraction_data,
                replace=True,
            )
            logger.info("[EXTRACT] Framework updated")

            # Save to document_extraction table (by fileHash) - PRIMARY TABLE
            if file_hash:
                logger.info("[EXTRACT] 6b: Saving to document_extraction table...")
                doc_extraction = await _get_or_create_doc_extraction(session, file_hash, None)
                doc_extraction.aiExtraction = extraction_data
                session.add(doc_extraction)
                await session.flush()
                await session.commit()
                logger.info("[EXTRACT] Saved to document_extractions table")
                logger.info("  Table: document_extractions")
                logger.info(f"  ID: {doc_extraction.id}")
                logger.info(f"  FileHash: {file_hash}")
                logger.info("  Status: extracted")
                logger.info(f"  Total Controls: {total_controls}")
            else:
                logger.warning("[EXTRACT] No fileHash - skipping document_extraction save")

        logger.info(f"{'='*80}")
        logger.info("[EXTRACT-SUCCESS] Framework extraction complete!")
        logger.info(f"  Framework ID: {framework_id}")
        logger.info(f"  File ID: {file_id}")
        logger.info(f"  Total Controls: {total_controls}")
        logger.info(f"  Total Sections: {len(controls_structured)}")
        logger.info(f"  Processing Time: {history['processing_time_seconds']:.2f}s")
        logger.info("[EXTRACT-SAVED] Data saved to: document_extractions table")
        logger.info(f"{'='*80}")

    except Exception as exc:
        logger.error(f"{'='*80}")
        logger.error("[EXTRACT-ERROR] Framework extraction failed!")
        logger.error(f"  Framework ID: {framework_id}")
        logger.error(f"  File ID: {file_id}")
        logger.error(f"  Error: {str(exc)}")
        logger.error(f"{'='*80}")
        logger.exception("[EXTRACT] Exception traceback:")

        fail_ts = _iso()
        try:
            async with session_scope() as session:
                await _update_framework_ai_status(
                    session,
                    framework_id,
                    file_id,
                    {
                        "status": "failed",
                        "timestamp": fail_ts,
                        "message": f"Extraction failed: {str(exc)}",
                    },
                )
                logger.info("[EXTRACT] Updated status to 'failed' in database")
        except Exception as db_exc:
            logger.error(f"[EXTRACT] Failed to update status in database: {db_exc}")


async def run_deployment_framework_extraction(df_id: str, pkg_ver: str, file_id: str) -> None:
    """Extract controls from deployment framework document."""
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()
    file_id = str(file_id).strip()
    uploaded_ts = _iso()

    logger.info(f"{'='*80}")
    logger.info("[DEPLOYMENT-EXTRACT-START] Deployment Framework Extraction Started")
    logger.info(f"  Deployment Framework ID: {df_id}")
    logger.info(f"  Package Version: {pkg_ver}")
    logger.info(f"  File ID: {file_id}")
    logger.info(f"  Timestamp: {uploaded_ts}")
    logger.info(f"{'='*80}")

    try:
        # Get deployment framework and file info
        logger.info("[DEPLOYMENT-EXTRACT] Step 1: Loading deployment framework from database...")
        async with session_scope() as session:

            df = await session.get(DeploymentFramework, df_id)
            if not df:
                logger.error(f"[DEPLOYMENT-EXTRACT] Deployment Framework not found: {df_id}")
                return

            logger.info(f"[DEPLOYMENT-EXTRACT] Deployment Framework found: {df.frameworkName}")

            # Find package
            packages = df.packages or []
            pkg_info = None
            for pkg in packages:
                if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                    pkg_info = pkg
                    break

            if not pkg_info:
                logger.error(f"[DEPLOYMENT-EXTRACT] Package not found: {pkg_ver}")
                return

            # Find file in package documents
            documents = pkg_info.get("documents") or []
            file_info = None
            for doc in documents:
                if isinstance(doc, dict) and str(doc.get("fileId")) == file_id:
                    file_info = doc
                    break

            if not file_info:
                logger.error(f"[DEPLOYMENT-EXTRACT] File not found in package: {file_id}")
                return

            file_path = file_info.get("fileUrl")
            if file_path and file_path.startswith("/uploads/"):
                from pathlib import Path

                from vora_shared.file_storage import UPLOAD_BASE_PATH

                relative = file_path.replace("/uploads/", "", 1)
                file_path = str((Path(UPLOAD_BASE_PATH) / relative).resolve())

            file_hash = file_info.get("fileHash")
            logger.info("[DEPLOYMENT-EXTRACT] File found")
            logger.info(f"  File Path: {file_path}")
            logger.info(f"  File Hash: {file_hash}")

            logger.info("[DEPLOYMENT-EXTRACT] Step 1.5: Updating status to 'processing'...")
            await _update_deployment_framework_ai_status(
                session,
                df_id,
                pkg_ver,
                file_id,
                {
                    "status": "processing",
                    "timestamp": uploaded_ts,
                    "message": "Deployment framework ai extraction in progress",
                },
            )
            logger.info("[DEPLOYMENT-EXTRACT] Status updated to 'processing'")

        # Load document from file
        logger.info("[DEPLOYMENT-EXTRACT] Step 2: Loading document from disk...")
        chunks = await asyncio.to_thread(_load_document_chunks, file_path)
        if not chunks:
            logger.error("[DEPLOYMENT-EXTRACT] No text extracted from document")
            return

        logger.info(f"[DEPLOYMENT-EXTRACT] Document loaded: {len(chunks)} chunks extracted")

        # Extract controls using AI (client controls for deployment frameworks)
        logger.info("[DEPLOYMENT-EXTRACT] Step 3: Running AI extraction...")
        controls_flat = await asyncio.to_thread(extract_framework_controls, chunks, df_id, True)
        logger.info(
            f"[DEPLOYMENT-EXTRACT] Framework ai extraction complete: {len(controls_flat)} controls extracted"
        )

        # Convert to section structure
        logger.info("[DEPLOYMENT-EXTRACT] Step 4: Converting to section structure...")
        controls_structured = await asyncio.to_thread(
            convert_to_section_structure, controls_flat, resource_type="deployment"
        )
        logger.info(
            f"[DEPLOYMENT-EXTRACT] Structure converted: {len(controls_structured)} sections"
        )

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
        logger.info("[DEPLOYMENT-EXTRACT] Step 5: Saving to database...")
        async with session_scope() as session:
            logger.info("[DEPLOYMENT-EXTRACT] 5a: Updating framework's aiExtraction...")
            await _update_deployment_framework_ai_status(
                session,
                df_id,
                pkg_ver,
                file_id,
                extraction_data,
                replace=True,
            )
            logger.info("[DEPLOYMENT-EXTRACT] Updated framework packages")

            # Save to document_extraction table (by fileHash)
            if file_hash:
                logger.info("[DEPLOYMENT-EXTRACT] Saving to document_extraction table...")
                doc_extraction = await _get_or_create_doc_extraction(session, file_hash, None)
                doc_extraction.aiExtraction = extraction_data
                session.add(doc_extraction)
                await session.flush()
                await session.commit()
                logger.info("[DEPLOYMENT-EXTRACT] Saved to document_extractions table")

        logger.info(f"{'='*80}")
        logger.info("[DEPLOYMENT-EXTRACT-SUCCESS] Deployment Framework extraction complete!")
        logger.info(f"  Deployment Framework ID: {df_id}")
        logger.info(f"  Package Version: {pkg_ver}")
        logger.info(f"  File ID: {file_id}")
        logger.info(f"  Total Controls: {total_controls}")
        logger.info(f"  Total Sections: {len(controls_structured)}")
        logger.info(f"  Processing Time: {history['processing_time_seconds']:.2f}s")
        logger.info(f"{'='*80}")

    except Exception as exc:
        logger.error(f"{'='*80}")
        logger.error("[DEPLOYMENT-EXTRACT-ERROR] Deployment Framework extraction failed!")
        logger.error(f"  Deployment Framework ID: {df_id}")
        logger.error(f"  Package Version: {pkg_ver}")
        logger.error(f"  File ID: {file_id}")
        logger.error(f"  Error: {str(exc)}")
        logger.error(f"{'='*80}")
        logger.exception("[DEPLOYMENT-EXTRACT] Exception traceback:")

        fail_ts = _iso()
        try:
            async with session_scope() as session:
                await _update_deployment_framework_ai_status(
                    session,
                    df_id,
                    pkg_ver,
                    file_id,
                    {
                        "status": "failed",
                        "timestamp": fail_ts,
                        "message": f"Extraction failed: {str(exc)}",
                    },
                )
                logger.info("[DEPLOYMENT-EXTRACT] Updated status to 'failed' in database")
        except Exception as db_exc:
            logger.error(f"[DEPLOYMENT-EXTRACT] Failed to update status in database: {db_exc}")


async def run_deployment_package_merge(df_id: str, pkg_ver: str) -> None:
    """Merge all extracted documents in a deployment framework package."""
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()

    logger.info(f"{'='*80}")
    logger.info("[PACKAGE-MERGE-START] Package Merge Started")
    logger.info(f"  Deployment Framework ID: {df_id}")
    logger.info(f"  Package Version: {pkg_ver}")
    logger.info(f"{'='*80}")
    file_hashes = []
    try:
        async with session_scope() as session:

            df = await session.get(DeploymentFramework, df_id)
            if not df:
                logger.error(f"[PACKAGE-MERGE] Deployment Framework not found: {df_id}")
                return

            # Find package
            packages = df.packages or []
            pkg_info = None
            for pkg in packages:
                if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                    pkg_info = pkg
                    break

            if not pkg_info:
                logger.error(f"[PACKAGE-MERGE] Package not found: {pkg_ver}")
                return

            logger.info(f"[PACKAGE-MERGE] Package found | version={pkg_ver}")

            # Collect all extracted controls from documents
            documents = pkg_info.get("documents") or []
            all_sections = []
            file_hashes = []

            for doc in documents:
                if not isinstance(doc, dict):
                    continue

                file_id = doc.get("fileId")
                file_hash = doc.get("fileHash")
                ai_extraction = doc.get("aiExtraction")

                if not ai_extraction:
                    logger.info(
                        f"[PACKAGE-MERGE] Skipping document - no extraction reference | fileId={file_id}"
                    )
                    continue

                from vora_shared.models import DocumentExtraction

                existing_id = (
                    ai_extraction
                    if isinstance(ai_extraction, str)
                    else (ai_extraction.get("id") if isinstance(ai_extraction, dict) else None)
                )

                doc_ext = (
                    await session.get(DocumentExtraction, existing_id) if existing_id else None
                )
                ai_ext_data = doc_ext.aiExtraction if doc_ext else None

                status = ai_ext_data.get("status") if isinstance(ai_ext_data, dict) else None
                if status != "extracted":
                    logger.info(
                        f"[PACKAGE-MERGE] Skipping document - not extracted | fileId={file_id} | status={status}"
                    )
                    continue

                if file_hash:
                    file_hashes.append(file_hash)

                # Extract controls from extraction data
                if isinstance(ai_ext_data, dict):
                    controls_block = ai_ext_data.get("controls", {})
                    if isinstance(controls_block, dict):
                        controls_data = controls_block.get("controls_data", [])
                    elif isinstance(controls_block, list):
                        controls_data = controls_block
                    else:
                        controls_data = []

                    if controls_data:
                        all_sections.extend(controls_data)
                        logger.info(
                            f"[PACKAGE-MERGE] Added document | fileId={file_id} | "
                            f"sections={len(controls_data)}"
                        )

            file_hashes = sorted(list(set(file_hashes)))

            # Find or create DeploymentPackageMerge record
            existing_merge_id = pkg_info.get("mergeDocument")
            existing_merge = None
            if existing_merge_id:
                existing_merge = await session.get(DeploymentPackageMerge, existing_merge_id)

            if not existing_merge and file_hashes:
                existing_merge = (
                    (
                        await session.execute(
                            select(DeploymentPackageMerge)
                            .where(DeploymentPackageMerge.fileHashes == file_hashes)
                            .order_by(DeploymentPackageMerge.createdAt.desc())
                        )
                    )
                    .scalars()
                    .first()
                )

            if not existing_merge:
                existing_merge = DeploymentPackageMerge(
                    id=new_id(),
                    fileHashes=file_hashes,
                    status="processing",
                )
                session.add(existing_merge)
            else:
                existing_merge.status = "processing"
                existing_merge.fileHashes = file_hashes
                session.add(existing_merge)

            await session.commit()

            # Assign its ID to the JSON
            await _update_deployment_framework_mergeDocument_status(
                session, df_id, pkg_ver, existing_merge.id
            )
            await session.commit()

            if not all_sections:
                logger.warning("[PACKAGE-MERGE] No extracted sections found in package")
                existing_merge.status = "failed"
                existing_merge.summary = {"message": "No extracted sections found"}
                session.add(existing_merge)
                await session.commit()
                return

            # Merge controls (cumulative)
            logger.info("[PACKAGE-MERGE] Step 1: Merging documents...")
            merged_controls, merge_summary = await asyncio.to_thread(
                merge_controls_cumulative, [], all_sections
            )

            logger.info("[PACKAGE-MERGE] Merge complete:")
            logger.info(f"  - Total controls: {merge_summary.get('new_controls', 0)}")
            logger.info(f"  - Total sections: {len(merged_controls)}")

            # Build payload
            controls_payload = {
                "total_controls": sum(len(s.get("controls", [])) for s in merged_controls),
                "total_sections": len(merged_controls),
                "controls_data": merged_controls,
            }

            # Save to deployment_package_merges table
            logger.info("[PACKAGE-MERGE] Step 2: Saving to database...")
            # Still passing file_ids array to this helper if needed, but it's okay to pass empty or omit
            await _save_merge_to_framework_merge(
                session, file_hashes, merged_controls, merge_summary
            )

            if existing_merge:
                logger.info("[PACKAGE-MERGE] Updating existing package merge...")
                existing_merge.status = "merged"
                existing_merge.fileHashes = file_hashes
                existing_merge.controls = controls_payload
                existing_merge.summary = merge_summary
                session.add(existing_merge)

            await session.flush()
            await session.commit()



            # Step 4: Clear stale comparison results so they get recalculated
            logger.info("[PACKAGE-MERGE] Step 4: Clearing stale comparison results...")
            await _clear_deployment_framework_comparison_results(session, df_id, pkg_ver)
            await session.commit()
            logger.info(
                "[PACKAGE-MERGE]  Cleared stale comparisons - will be recalculated on next run"
            )

            logger.info(f"{'='*80}")
            logger.info("[PACKAGE-MERGE-SUCCESS] Package merge complete!")
            logger.info(f"  Deployment Framework ID: {df_id}")
            logger.info(f"  Package Version: {pkg_ver}")
            logger.info(f"  Files merged: {len(file_hashes)}")
            logger.info(f"  Total controls: {controls_payload['total_controls']}")
            logger.info(f"{'='*80}")

    except Exception as exc:
        logger.error(f"{'='*80}")
        logger.error("[PACKAGE-MERGE-ERROR] Package merge failed!")
        logger.error(f"  Deployment Framework ID: {df_id}")
        logger.error(f"  Package Version: {pkg_ver}")
        logger.error(f"  Error: {str(exc)}")
        logger.exception("[PACKAGE-MERGE] Exception traceback:")
        logger.error(f"{'='*80}")

        try:
            async with session_scope() as session:
                df = await session.get(DeploymentFramework, df_id)
                if df:
                    for pkg in (df.packages or []):
                        if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                            merge_id = pkg.get("mergeDocument")
                            if merge_id:
                                existing_merge = await session.get(DeploymentPackageMerge, merge_id)
                                if existing_merge:
                                    existing_merge.status = "failed"
                                    existing_merge.summary = {"message": f"Merge failed: {str(exc)}"}
                                    session.add(existing_merge)
                                    await session.commit()
                            break
        except Exception as db_exc:
            logger.error(f"[PACKAGE-MERGE] Failed to update failure status: {db_exc}")


async def _clear_deployment_framework_comparison_results(
    session: Any, df_id: str, pkg_ver: str
) -> None:
    """Clear/reset stale comparison results after merge so they get recalculated."""
    try:
        from vora_shared.models import PackageComparison

        # Find all comparisons for this deployment framework package
        comparisons = (
            (
                await session.execute(
                    select(PackageComparison).where(
                        PackageComparison.deploymentFrameworkId == df_id
                    )
                )
            )
            .scalars()
            .all()
        )

        cleared_count = 0
        for pc in comparisons:
            if isinstance(pc.comparison, dict):
                # Reset the comparison_result to empty so it gets recalculated
                pc.comparison["comparison_result"] = []
                pc.comparison["comparison_score"] = 0
                pc.comparison["status"] = "pending_recalculation"
                session.add(pc)
                cleared_count += 1

        if cleared_count > 0:
            logger.info(
                f"[PACKAGE-MERGE] Cleared {cleared_count} comparison records for recalculation"
            )
        await session.flush()

    except Exception as e:
        logger.warning(f"[PACKAGE-MERGE]  Could not clear comparisons (non-critical): {e}")


async def _get_or_create_doc_extraction(
    session: Any, file_hash: str, existing_id: str | None
) -> DocumentExtraction:
    if existing_id:
        row = await session.get(DocumentExtraction, str(existing_id))
        if row:
            return row
    if file_hash:
        row = (
            await session.execute(
                select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash)
            )
        ).scalar_one_or_none()
        if row:
            return row
    row = DocumentExtraction(id=new_id(), fileHash=file_hash or new_id(), aiExtraction={})
    session.add(row)
    await session.flush()
    return row


async def _save_merge_to_framework_merge(
    session: Any,
    file_hashes: list[str],
    merged_controls: list[dict[str, Any]],
    merge_summary: dict[str, Any],
) -> None:
    """Save merged controls to framework_merges table (canonical storage by mergeHashes)."""
    sorted_hashes = sorted(file_hashes)

    existing = (
        (
            await session.execute(
                select(FrameworkMerge).where(FrameworkMerge.mergeHashes == sorted_hashes)
            )
        )
        .scalars()
        .first()
    )

    controls_payload = {
        "total_controls": sum(len(s.get("controls", [])) for s in merged_controls),
        "total_sections": len(merged_controls),
        "controls_data": merged_controls,
    }

    if existing:
        logger.info("[MERGE-TABLE] Updating existing merge...")
        existing.controls = controls_payload
        existing.summary = merge_summary
        existing.mergeHashes = sorted_hashes
        session.add(existing)
    else:
        merge_record = FrameworkMerge(
            id=new_id(),
            mergeHashes=sorted_hashes,
            controls=controls_payload,
            summary=merge_summary,
        )
        session.add(merge_record)
        logger.info(
            f"[MERGE-TABLE] Saved merge "
            f"| hashes={len(sorted_hashes)} | controls={controls_payload['total_controls']}"
        )


async def run_deployment_document_extraction(dd_id: str, file_id: str) -> None:
    """Load DeploymentDocument, extract controls using AI, save to document_extraction table"""
    dd_id = str(dd_id).strip()
    file_id = str(file_id).strip()
    uploaded_ts = _iso()

    logger.info(f"{'='*80}")
    logger.info("[DD-EXTRACT-START] Deployment Document Extraction Started")
    logger.info(f"  Deployment Document ID: {dd_id}")
    logger.info(f"  File ID: {file_id}")
    logger.info(f"  Timestamp: {uploaded_ts}")
    logger.info(f"{'='*80}")

    try:
        # Get deployment document and file info
        logger.info("[DD-EXTRACT] Step 1: Loading deployment document from database...")
        async with session_scope() as session:
            from vora_shared.models import DeploymentDocument

            dd = await session.get(DeploymentDocument, dd_id)
            if not dd:
                logger.error(f"[DD-EXTRACT]  Deployment Document not found: {dd_id}")
                return

            logger.info(f"[DD-EXTRACT]  Deployment Document found: {dd.frameworkName}")

            # Find package and file. DeploymentDocument doesn't store packages;
            # load parent DeploymentFramework and look up the package by version.
            pkg_info = None
            try:
                from vora_shared.models import DeploymentFramework

                df = await session.get(DeploymentFramework, dd.deploymentFrameworkId)
                if not df:
                    logger.error(f"[DD-EXTRACT]  DeploymentFramework not found: {dd.deploymentFrameworkId}")
                    return

                packages = list(df.packages or [])
                # package version may be stored on the deployment document or on the framework
                pkg_ver = getattr(dd, "frameworkVersion", None) or getattr(df, "currentPackageVersion", None)

                for pkg in packages:
                    if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                        pkg_info = pkg
                        break

                if not pkg_info:
                    logger.error(f"[DD-EXTRACT]  Package not found: {pkg_ver}")
                    return

                documents = pkg_info.get("documents") or []
                file_info = None
                for doc in documents:
                    if isinstance(doc, dict) and str(doc.get("fileId")) == file_id:
                        file_info = doc
                        break

                # If file not present in framework packages (e.g. reprocessed uploads
                # or documents saved without updating the parent framework), fall
                # back to using the file info stored directly on the
                # DeploymentDocument.
                if not file_info:
                    doc_data = dd.document or {}
                    if isinstance(doc_data, dict) and str(doc_data.get("fileId")) == file_id:
                        file_info = dict(doc_data)
                    else:
                        logger.error(f"[DD-EXTRACT]  File not found in deployment package: {file_id}")
                        return

                file_path = file_info.get("fileUrl")
            except Exception as e:
                logger.error(f"[DD-EXTRACT] Error locating package/file: {e}")
                return
            if file_path and file_path.startswith("/uploads/"):
                from pathlib import Path

                from vora_shared.file_storage import UPLOAD_BASE_PATH

                relative = file_path.replace("/uploads/", "", 1)
                file_path = str((Path(UPLOAD_BASE_PATH) / relative).resolve())

            file_hash = file_info.get("fileHash")
            logger.info("[DD-EXTRACT]  File found")
            logger.info(f"  File Path: {file_path}")
            logger.info(f"  File Hash: {file_hash}")

            logger.info("[DD-EXTRACT] Step 1.5: Updating status to 'processing'...")
            await _update_deployment_document_ai_status(
                session,
                dd_id,
                file_id,
                {
                    "status": "processing",
                    "timestamp": uploaded_ts,
                    "message": "Deployment document ai extraction in progress",
                },
            )
            logger.info("[DD-EXTRACT]  Status updated to 'processing'")

        # Load document from file
        logger.info("[DD-EXTRACT] Step 2: Loading document from disk...")
        chunks = await asyncio.to_thread(_load_document_chunks, file_path)
        if not chunks:
            logger.error("[DD-EXTRACT]  No text extracted from document")
            return

        logger.info(f"[DD-EXTRACT]  Document loaded: {len(chunks)} chunks extracted")

        # Extract controls using AI (client controls for deployment documents)
        logger.info("[DD-EXTRACT] Step 3: Running AI extraction...")
        controls_flat = await asyncio.to_thread(extract_framework_controls, chunks, dd_id, True)
        logger.info(
            f"[DD-EXTRACT]  Framework ai extraction complete: {len(controls_flat)} controls extracted"
        )

        # Convert to section structure
        logger.info("[DD-EXTRACT] Step 4: Converting to section structure...")
        controls_structured = await asyncio.to_thread(
            convert_to_section_structure, controls_flat, resource_type="deployment"
        )
        logger.info(f"[DD-EXTRACT]  Structure converted: {len(controls_structured)} sections")

        # Build controls payload
        total_controls = sum(len(s.get("controls", [])) for s in controls_structured)
        controls_payload = {
            "total_controls": total_controls,
            "total_sections": len(controls_structured),
            "controls_data": controls_structured,
        }
        logger.info(f"[DD-EXTRACT] Total controls: {total_controls}")

        completed_ts = _iso()
        history = _status_history(uploaded_ts, uploaded_ts, completed_ts)

        # Prepare extraction data
        extraction_data = {
            "status": "extracted",
            "timestamp": completed_ts,
            "message": "Deployment document AI extraction completed",
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

        # Attach document/file metadata so document_extraction rows include source info
        try:
            meta = {
                "fileId": file_id,
                "fileHash": file_hash,
                "fileUrl": file_path,
                "fileSize": file_info.get("fileSize") if isinstance(file_info, dict) else None,
                "fileType": file_info.get("fileType") if isinstance(file_info, dict) else None,
                "originalFileName": file_info.get("originalFileName") if isinstance(file_info, dict) else None,
                "uploadedAt": file_info.get("uploadedAt") if isinstance(file_info, dict) else None,
            }
            extraction_data["document"] = meta
        except Exception:
            pass

        # Update deployment document with extracted data
        logger.info("[DD-EXTRACT] Step 5: Saving to database...")
        async with session_scope() as session:
            logger.info("[DD-EXTRACT] 5a: Updating deployment document's aiExtraction...")
            await _update_deployment_document_ai_status(
                session,
                dd_id,
                file_id,
                extraction_data,
                replace=True,
            )
            logger.info("[DD-EXTRACT]  Deployment document updated")

             # Save to document_extraction table (by fileHash) - PRIMARY TABLE
            if file_hash:
                logger.info("[DD-EXTRACT] 5b: Saving to document_extraction table...")
                doc_extraction = await _get_or_create_doc_extraction(session, file_hash, None)
                doc_extraction.aiExtraction = extraction_data
                session.add(doc_extraction)
                await session.flush()
                await session.commit()
                logger.info("[DD-EXTRACT]  Saved to document_extractions table")
                logger.info("  Table: document_extractions")
                logger.info(f"  ID: {doc_extraction.id}")
                logger.info(f"  FileHash: {file_hash}")
                logger.info("  Status: extracted")
                logger.info(f"  Total Controls: {total_controls}")
                
                # Trigger compliance evaluation automatically in the background
                try:
                    import httpx
                    logger.info(f"[DD-EXTRACT] Triggering compliance agent evaluation for dd_id: {dd_id}...")
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        resp = await client.post(f"http://localhost:7008/api/compliance-agent/evaluate/{dd_id}")
                        if resp.status_code in (200, 201, 202):
                            logger.info(f"[DD-EXTRACT] Successfully triggered compliance agent for dd_id: {dd_id}")
                        else:
                            logger.warning(f"[DD-EXTRACT] Failed to trigger compliance agent, status: {resp.status_code}")
                except Exception as e:
                    logger.warning(f"[DD-EXTRACT] Could not reach compliance agent service: {e}")
            else:
                logger.warning("[DD-EXTRACT]  No fileHash - skipping document_extraction save")

        logger.info(f"{'='*80}")
        logger.info("[DD-EXTRACT-SUCCESS]  Deployment document extraction complete!")
        logger.info(f"  Deployment Document ID: {dd_id}")
        logger.info(f"  File ID: {file_id}")
        logger.info(f"  Total Controls: {total_controls}")
        logger.info(f"  Total Sections: {len(controls_structured)}")
        logger.info(f"  Processing Time: {history['processing_time_seconds']:.2f}s")
        logger.info("[DD-EXTRACT-SAVED]  Data saved to: document_extractions table")
        logger.info(f"{'='*80}")

    except Exception as exc:
        logger.error(f"{'='*80}")
        logger.error("[DD-EXTRACT-ERROR]  Deployment document extraction failed!")
        logger.error(f"  Deployment Document ID: {dd_id}")
        logger.error(f"  File ID: {file_id}")
        logger.error(f"  Error: {str(exc)}")
        logger.error(f"{'='*80}")
        logger.exception("[DD-EXTRACT] Exception traceback:")

        fail_ts = _iso()
        try:
            async with session_scope() as session:
                await _update_deployment_document_ai_status(
                    session,
                    dd_id,
                    file_id,
                    {
                        "status": "failed",
                        "timestamp": fail_ts,
                        "message": f"Extraction failed: {str(exc)}",
                    },
                )
                logger.info("[DD-EXTRACT] Updated status to 'failed' in database")
        except Exception as db_exc:
            logger.error(f"[DD-EXTRACT] Failed to update status in database: {db_exc}")


async def _update_deployment_document_ai_status(
    session: Any, dd_id: str, file_id: str, status_data: dict[str, Any], replace: bool = False
) -> None:
    """Update deployment document's aiExtraction field in the packages structure"""
    # DeploymentDocument does not store package lists; update the parent
    # DeploymentFramework package entry instead.
    from vora_shared.models import DeploymentDocument

    dd = await session.get(DeploymentDocument, dd_id)
    if not dd:
        return

    pkg_ver = getattr(dd, "frameworkVersion", None)
    df_id = getattr(dd, "deploymentFrameworkId", None)
    if not df_id or not pkg_ver:
        # Nothing to update on framework side; try to update the DeploymentDocument's
        # own `document.aiExtraction` field and return.
        try:
            doc_data = dd.document or {}
            if isinstance(doc_data, dict):
                if replace:
                    doc_data["aiExtraction"] = status_data
                else:
                    ai = dict(doc_data.get("aiExtraction") or {})
                    ai.update(status_data)
                    doc_data["aiExtraction"] = ai
                dd.document = doc_data
                flag_modified(dd, "document")
                session.add(dd)
                return
        except Exception:
            return

    # Attempt to update the parent framework package entry. If that does not
    # find the package/document, fall back to updating the DeploymentDocument row.
    try:
        await _update_deployment_framework_ai_status(session, df_id, pkg_ver, file_id, status_data, replace=replace)
    except Exception:
        try:
            # Fallback to updating DeploymentDocument.document.aiExtraction
            doc_data = dd.document or {}
            if isinstance(doc_data, dict):
                if replace:
                    doc_data["aiExtraction"] = status_data
                else:
                    ai = dict(doc_data.get("aiExtraction") or {})
                    ai.update(status_data)
                    doc_data["aiExtraction"] = ai
                dd.document = doc_data
                flag_modified(dd, "document")
                session.add(dd)
        except Exception:
            return


async def _get_or_create_doc_extraction(
    session: Any, file_hash: str, existing_id: str | None = None
) -> DocumentExtraction:
    """Get or create a DocumentExtraction record by file hash"""
    existing = (
        await session.execute(
            select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash)
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    doc_extraction = DocumentExtraction(
        id=existing_id or new_id(),
        fileHash=file_hash,
        aiExtraction={"status": "processing", "timestamp": _iso(), "message": "Processing..."},
    )
    session.add(doc_extraction)
    await session.flush()
    return doc_extraction