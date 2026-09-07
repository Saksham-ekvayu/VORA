"""Async extraction / merge runners — no RabbitMQ; driven by WebSocket connect."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.control_extractor import (
    convert_to_section_structure,
    extract_deployment_controls,
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
UPLOADS_PREFIX = "/uploads/"


def _utcnow() -> datetime:
    return datetime.now(UTC)


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
    history.append({"status": "completed", "timestamp": completed, "message": MSG_EXTRACTION_COMPLETED})
    try:
        start = datetime.fromisoformat(uploaded)
        end = datetime.fromisoformat(completed)
        elapsed = max(0.0, (end - start).total_seconds())
    except Exception:  # noqa: BLE001
        elapsed = 1.0
    return {
        "processing_time_seconds": elapsed,
        "completed_at": completed,
        "history": history,
    }


def _append_lines(text_lines: list[str], text: str) -> bool:
    if not text or not text.strip():
        return False
    text_lines.extend(line.strip() for line in text.split("\n") if line.strip())
    return True


def _extract_pdf_page_text(
    pages: Any,
    text_lines: list[str],
    extractor: Any,
    label: str,
) -> bool:
    extracted = False
    for page_num, page in enumerate(pages, 1):
        try:
            if _append_lines(text_lines, extractor(page)):
                extracted = True
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[LOAD] Page {page_num} {label} failed: {exc}")
    if extracted:
        logger.info(f"[LOAD]  {label} extracted {len(text_lines)} lines")
    return extracted


def _extract_pdf_pages(file_path: str, text_lines: list[str], module_name: str) -> bool:
    module = __import__(module_name)
    if module_name == "pdfplumber":
        logger.info("[LOAD] Attempt 1: pdfplumber text extraction...")
        with module.open(file_path) as pdf:
            logger.info(f"[LOAD] PDF has {len(pdf.pages)} pages")
            return _extract_pdf_page_text(
                pdf.pages, text_lines, lambda page: page.extract_text(), "pdfplumber"
            )
    logger.info("[LOAD] Attempt 1.5: PyMuPDF (fitz) text extraction...")
    doc = module.open(file_path)
    try:
        logger.info(f"[LOAD] PyMuPDF reports {doc.page_count} pages")
        return _extract_pdf_page_text(
            doc, text_lines, lambda page: page.get_text("text"), "PyMuPDF"
        )
    finally:
        doc.close()


def _extract_pdf_ocr(file_path: str, text_lines: list[str]) -> bool:
    import pdf2image
    import pytesseract

    logger.info("[LOAD] Converting PDF to images...")
    images = pdf2image.convert_from_path(file_path, dpi=300)
    logger.info(f"[LOAD] Converted to {len(images)} images")
    if not images:
        logger.error("[LOAD]  pdf2image returned no images")
        return False
    extracted = False
    for page_num, image in enumerate(images, 1):
        try:
            logger.info(f"[LOAD] OCR scanning page {page_num}/{len(images)}...")
            ocr_text = pytesseract.image_to_string(image, lang="eng")
            if _append_lines(text_lines, ocr_text):
                extracted = True
                logger.info(f"[LOAD] Page {page_num}: OCR extracted {len(ocr_text.split(chr(10)))} lines")
        except Exception as page_err:  # noqa: BLE001
            logger.warning(f"[LOAD] Page {page_num} OCR failed: {page_err}")
    if extracted:
        logger.info(f"[LOAD]  OCR extraction complete: {len(text_lines)} total lines")
    return extracted


def _extract_pdf_pypdf(file_path: str, text_lines: list[str]) -> bool:
    import pypdf

    extracted = False
    with open(file_path, "rb") as f:
        try:
            reader = pypdf.PdfReader(f)
            logger.info(f"[LOAD] pypdf found {len(reader.pages)} pages")
            for page_num, page in enumerate(reader.pages, 1):
                try:
                    if _append_lines(text_lines, page.extract_text()):
                        extracted = True
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"[LOAD] Page {page_num} pypdf failed: {e}")
            if extracted:
                logger.info(f"[LOAD]  pypdf extracted {len(text_lines)} lines")
        except Exception as reader_err:  # noqa: BLE001
            logger.warning(f"[LOAD] pypdf reader failed: {reader_err}")
    return extracted


def _load_pdf_lines(file_path: str) -> list[str]:
    text_lines: list[str] = []
    logger.info("[LOAD] Starting PDF extraction...")
    try:
        extracted = _extract_pdf_pages(file_path, text_lines, "pdfplumber")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[LOAD] pdfplumber failed: {e}")
        extracted = False
    if not extracted:
        try:
            extracted = _extract_pdf_pages(file_path, text_lines, "fitz")
        except ImportError:
            logger.warning("[LOAD] PyMuPDF not installed — skipping Attempt 1.5. Run: pip install PyMuPDF")
            extracted = False
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[LOAD] PyMuPDF attempt failed: {e}")
            extracted = False
    if not extracted:
        logger.info("[LOAD] Attempt 2: OCR extraction (pdf2image + pytesseract)...")
        try:
            extracted = _extract_pdf_ocr(file_path, text_lines)
        except ImportError as imp_err:
            logger.exception(f"[LOAD]  OCR libraries not installed: {imp_err}")
            logger.error("[LOAD] Install: pip install pdf2image pytesseract")
            logger.error("[LOAD] Also install: apt-get install tesseract-ocr poppler-utils")
            extracted = False
        except Exception as ocr_err:  # noqa: BLE001
            logger.exception(f"[LOAD]  OCR extraction failed: {ocr_err}")
            extracted = False
    if not extracted:
        logger.info("[LOAD] Attempt 3: pypdf text extraction...")
        try:
            _extract_pdf_pypdf(file_path, text_lines)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[LOAD] pypdf not available: {e}")
    return text_lines


def _load_document_lines(file_path: str, ext: str) -> list[str]:
    if ext == ".pdf":
        return _load_pdf_lines(file_path)
    if ext == ".docx":
        try:
            from docx import Document

            doc = Document(file_path)
            return [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        except Exception as e:  # noqa: BLE001
            logger.exception(f"[LOAD] Failed to load docx: {e}")
            return []
    if ext in [".xls", ".xlsx"]:
        try:
            import pandas as pd

            xls = pd.ExcelFile(file_path)
            return [pd.read_excel(xls, sheet_name=sheet).to_string(index=False) for sheet in xls.sheet_names]
        except Exception as e:  # noqa: BLE001
            logger.exception(f"[LOAD] Failed to load excel: {e}")
            return []
    if ext in [".txt", ".csv"]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:  # noqa: BLE001
            logger.exception(f"[LOAD] Failed to load text file: {e}")
            return []
    logger.error(f"[LOAD] Unsupported file type: {ext}")
    return []


def _chunk_lines(text_lines: list[str], chunk_size: int) -> list[str]:
    chunks: list[str] = []
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
    return chunks


def _load_document_chunks(file_path: str, chunk_size: int = 1000) -> list[str]:
    """Load document from file and chunk it for processing"""
    try:
        if not file_path or not os.path.exists(file_path):
            logger.error(f"[LOAD] File not found: {file_path}")
            return []
        ext = Path(file_path).suffix.lower()
        logger.info(f"[LOAD] Loading document | ext={ext} | path={file_path}")
        if ext not in [".pdf", ".docx", ".xls", ".xlsx", ".txt", ".csv"]:
            logger.error(f"[LOAD] Unsupported file type: {ext}")
            return []
        try:
            text_lines = _load_document_lines(file_path, ext)
        except Exception as e:  # noqa: BLE001
            logger.exception(f"[LOAD] Failed to load document: {e}")
            return []
        if not text_lines:
            logger.warning(f"[LOAD] No text extracted from {file_path}")
            return []
        chunks = _chunk_lines(text_lines, chunk_size)
        logger.info(f"[LOAD] Loaded {len(text_lines)} lines into {len(chunks)} chunks")
        return chunks
    except Exception:
        logger.exception("[LOAD] Failed to load document")
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


def _apply_ai_status(extraction: Any, status_data: dict[str, Any], replace: bool) -> None:
    if replace:
        extraction.aiExtraction = status_data
        return
    ai = dict(extraction.aiExtraction or {})
    ai.update(status_data)
    extraction.aiExtraction = ai


def _find_deployment_document(
    packages: list[Any], pkg_ver: str, file_id: str
) -> tuple[int, int, dict[str, Any]] | None:
    for package_index, package in enumerate(packages):
        if not isinstance(package, dict) or package.get("packageVersion") != pkg_ver:
            continue
        for document_index, document in enumerate(package.get("documents") or []):
            if isinstance(document, dict) and str(document.get("fileId")) == file_id:
                return package_index, document_index, document
    return None


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
    location = _find_deployment_document(packages, pkg_ver, file_id)
    if location is None:
        return

    package_index, document_index, document = location
    file_hash = str(document.get("fileHash") or "")
    existing_ai = document.get("aiExtraction")
    existing_id = existing_ai if isinstance(existing_ai, str) else None
    extraction = await _get_or_create_doc_extraction(session, file_hash, existing_id)
    _apply_ai_status(extraction, status_data, replace)

    document["aiExtraction"] = extraction.id
    package = packages[package_index]
    documents = list(package.get("documents") or [])
    documents[document_index] = document
    package["documents"] = documents
    packages[package_index] = package
    df.packages = packages
    flag_modified(df, "packages")
    session.add(df)


async def _update_deployment_framework_merge_document_status(
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


async def _get_framework_file_info(
    framework_id: str, file_id: str, uploaded_ts: str
) -> tuple[str | None, str | None, str | None]:
    async with session_scope() as session:
        framework = await session.get(Framework, framework_id)
        if not framework:
            logger.error(f"[EXTRACT] Framework not found: {framework_id}")
            return None, None, None
        file_info = next(
            (
                version
                for version in (framework.fileVersions or [])
                if isinstance(version, dict) and str(version.get("fileId")) == file_id
            ),
            None,
        )
        if not file_info:
            logger.error(f"[EXTRACT] File not found in framework: {file_id}")
            return None, None, None
        file_path = file_info.get("fileUrl")
        file_hash = file_info.get("fileHash")
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
        return file_path, file_hash, file_info.get("fileVersion")


async def _extract_framework_payload(
    chunks: list, framework_id: str, file_version: str | None
) -> tuple[dict[str, Any], dict[str, Any] | None, int]:
    controls_flat = await asyncio.to_thread(extract_framework_controls, chunks, framework_id)
    controls_structured = await asyncio.to_thread(
        convert_to_section_structure, controls_flat, resource_type="framework"
    )
    merge_summary = None
    async with session_scope() as session:
        framework = await session.get(Framework, framework_id)
        if framework:
            old_sections, prev_version, prev_hash = await asyncio.to_thread(
                get_framework_previous_controls, framework.fileVersions or [], file_version
            )
            if old_sections:
                logger.info(f"[EXTRACT] Found previous version: {prev_version}")
                logger.info(f"[EXTRACT] Previous file hash: {prev_hash}")
                controls_structured, merge_summary = await asyncio.to_thread(
                    merge_controls_cumulative, old_sections, controls_structured
                )

    total_controls = sum(len(section.get("controls", [])) for section in controls_structured)
    controls_payload = {
        "total_controls": total_controls,
        "total_sections": len(controls_structured),
        "controls_data": controls_structured,
    }
    return controls_payload, merge_summary, total_controls


def _build_framework_extraction_data(
    controls_payload: dict[str, Any],
    merge_summary: dict[str, Any] | None,
    uploaded_ts: str,
) -> tuple[dict[str, Any], str]:
    completed_ts = _iso()
    history = _status_history(uploaded_ts, uploaded_ts, completed_ts)
    extraction_data = {
        "status": "extracted",
        "timestamp": completed_ts,
        "message": "Framework ai extraction completed",
        "statusHistory": {
            "processingTimeSeconds": history["processing_time_seconds"],
            "completedAt": history["completed_at"],
            "history": [
                {
                    "status": ("extracted" if item["status"] == "completed" else item["status"]),
                    "timestamp": item["timestamp"],
                    "message": item.get("message"),
                }
                for item in history["history"]
            ],
        },
        "controls": controls_payload,
    }
    if merge_summary:
        extraction_data["mergeSummary"] = merge_summary
    return extraction_data, completed_ts


async def _save_framework_extraction(
    framework_id: str,
    file_id: str,
    file_hash: str | None,
    extraction_data: dict[str, Any],
) -> None:
    async with session_scope() as session:
        await _update_framework_ai_status(
            session, framework_id, file_id, extraction_data, replace=True
        )
        if file_hash:
            doc_extraction = await _get_or_create_doc_extraction(session, file_hash, None)
            doc_extraction.aiExtraction = extraction_data
            session.add(doc_extraction)
            await session.flush()
            await session.commit()


async def _get_deployment_framework_file_info(
    df_id: str, pkg_ver: str, file_id: str, uploaded_ts: str
) -> tuple[str | None, str | None]:
    async with session_scope() as session:
        deployment_framework = await session.get(DeploymentFramework, df_id)
        if not deployment_framework:
            logger.error(f"[DEPLOYMENT-EXTRACT] Deployment Framework not found: {df_id}")
            return None, None
        package = next(
            (
                item
                for item in (deployment_framework.packages or [])
                if isinstance(item, dict) and item.get("packageVersion") == pkg_ver
            ),
            None,
        )
        if not package:
            logger.error(f"[DEPLOYMENT-EXTRACT] Package not found: {pkg_ver}")
            return None, None
        file_info = next(
            (
                document
                for document in (package.get("documents") or [])
                if isinstance(document, dict) and str(document.get("fileId")) == file_id
            ),
            None,
        )
        if not file_info:
            logger.error(f"[DEPLOYMENT-EXTRACT] File not found in package: {file_id}")
            return None, None
        file_path = file_info.get("fileUrl")
        if file_path and file_path.startswith(UPLOADS_PREFIX):
            from vora_shared.file_storage import UPLOAD_BASE_PATH

            relative = file_path.replace(UPLOADS_PREFIX, "", 1)
            file_path = str((Path(UPLOAD_BASE_PATH) / relative).resolve())
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
        return file_path, file_info.get("fileHash")


async def _extract_deployment_payload(
    chunks: list[str],
) -> tuple[dict[str, Any], int]:
    controls_flat = await asyncio.to_thread(extract_deployment_controls, chunks)
    controls_structured = await asyncio.to_thread(
        convert_to_section_structure, controls_flat, resource_type="deployment"
    )
    total_controls = sum(len(section.get("controls", [])) for section in controls_structured)
    return {
        "total_controls": total_controls,
        "total_sections": len(controls_structured),
        "controls_data": controls_structured,
    }, total_controls


def _build_deployment_extraction_data(
    controls_payload: dict[str, Any], uploaded_ts: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    completed_ts = _iso()
    history = _status_history(uploaded_ts, uploaded_ts, completed_ts)
    return {
        "status": "extracted",
        "timestamp": completed_ts,
        "message": MSG_DEPLOYMENT_EXTRACTION_COMPLETED,
        "statusHistory": {
            "processingTimeSeconds": history["processing_time_seconds"],
            "completedAt": history["completed_at"],
            "history": [
                {
                    "status": ("extracted" if item["status"] == "completed" else item["status"]),
                    "timestamp": item["timestamp"],
                    "message": item.get("message"),
                }
                for item in history["history"]
            ],
        },
        "controls": controls_payload,
    }, history


async def _save_deployment_extraction(
    df_id: str,
    pkg_ver: str,
    file_id: str,
    file_hash: str | None,
    extraction_data: dict[str, Any],
) -> None:
    async with session_scope() as session:
        await _update_deployment_framework_ai_status(
            session, df_id, pkg_ver, file_id, extraction_data, replace=True
        )
        if file_hash:
            doc_extraction = await _get_or_create_doc_extraction(session, file_hash, None)
            doc_extraction.aiExtraction = extraction_data
            session.add(doc_extraction)
            await session.flush()
            await session.commit()


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
        file_path, file_hash, file_version = await _get_framework_file_info(
            framework_id, file_id, uploaded_ts
        )
        if not file_path:
            return
        chunks = await asyncio.to_thread(_load_document_chunks, file_path)
        if not chunks:
            async with session_scope() as session:
                await _update_framework_ai_status(
                    session, framework_id, file_id,
                    {"status": "failed", "timestamp": _iso(),
                     "message": "Failed to extract text from document"},
                )
            return
        controls_payload, merge_summary, total_controls = await _extract_framework_payload(
            chunks, framework_id, file_version
        )
        extraction_data, completed_ts = _build_framework_extraction_data(
            controls_payload, merge_summary, uploaded_ts
        )
        await _save_framework_extraction(framework_id, file_id, file_hash, extraction_data)
        logger.info(
            f"[EXTRACT-SUCCESS] Framework extraction complete | controls={total_controls} "
            f"| sections={controls_payload['total_sections']} | completed={completed_ts}"
        )

    except Exception as exc:
        logger.error(f"{'='*80}")
        logger.error("[EXTRACT-ERROR] Framework extraction failed!")
        logger.error(f"  Framework ID: {framework_id}")
        logger.error(f"  File ID: {file_id}")
        logger.exception(f"  Error: {exc!s}")
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
                        "message": f"Extraction failed: {exc!s}",
                    },
                )
                logger.info("[EXTRACT] Updated status to 'failed' in database")
        except Exception as db_exc:  # noqa: BLE001
            logger.exception(f"[EXTRACT] Failed to update status in database: {db_exc}")


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
        file_path, file_hash = await _get_deployment_framework_file_info(
            df_id, pkg_ver, file_id, uploaded_ts
        )
        if not file_path:
            return
        chunks = await asyncio.to_thread(_load_document_chunks, file_path)
        if not chunks:
            logger.error("[DEPLOYMENT-EXTRACT] No text extracted from document")
            return
        controls_payload, total_controls = await _extract_deployment_payload(chunks)
        extraction_data, history = _build_deployment_extraction_data(
            controls_payload, uploaded_ts
        )
        await _save_deployment_extraction(
            df_id, pkg_ver, file_id, file_hash, extraction_data
        )
        logger.info(
            f"[DEPLOYMENT-EXTRACT-SUCCESS] Extraction complete | controls={total_controls} "
            f"| sections={controls_payload['total_sections']} "
            f"| processing_time={history['processing_time_seconds']:.2f}s"
        )

    except Exception as exc:
        logger.error(f"{'='*80}")
        logger.error("[DEPLOYMENT-EXTRACT-ERROR] Deployment Framework extraction failed!")
        logger.error(f"  Deployment Framework ID: {df_id}")
        logger.error(f"  Package Version: {pkg_ver}")
        logger.error(f"  File ID: {file_id}")
        logger.exception(f"  Error: {exc!s}")
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
                        "message": f"Extraction failed: {exc!s}",
                    },
                )
                logger.info("[DEPLOYMENT-EXTRACT] Updated status to 'failed' in database")
        except Exception as db_exc:  # noqa: BLE001
            logger.exception(f"[DEPLOYMENT-EXTRACT] Failed to update status in database: {db_exc}")


async def _get_deployment_package(
    session: Any, df_id: str, pkg_ver: str
) -> dict[str, Any] | None:
    deployment_framework = await session.get(DeploymentFramework, df_id)
    if not deployment_framework:
        logger.error(f"[PACKAGE-MERGE] Deployment Framework not found: {df_id}")
        return None
    package = next(
        (
            item
            for item in (deployment_framework.packages or [])
            if isinstance(item, dict) and item.get("packageVersion") == pkg_ver
        ),
        None,
    )
    if not package:
        logger.error(f"[PACKAGE-MERGE] Package not found: {pkg_ver}")
        return None
    logger.info(f"[PACKAGE-MERGE] Package found | version={pkg_ver}")
    return package


async def _get_document_sections(
    session: Any, document: dict[str, Any]
) -> tuple[list[dict[str, Any]], str | None]:
    file_id = document.get("fileId")
    file_hash = document.get("fileHash")
    ai_extraction = document.get("aiExtraction")
    if not ai_extraction:
        logger.info(f"[PACKAGE-MERGE] Skipping document - no extraction reference | fileId={file_id}")
        return [], None
    existing_id = None
    if isinstance(ai_extraction, str):
        existing_id = ai_extraction
    elif isinstance(ai_extraction, dict):
        existing_id = ai_extraction.get("id")
    doc_ext = await session.get(DocumentExtraction, existing_id) if existing_id else None
    ai_ext_data = doc_ext.aiExtraction if doc_ext else None
    status = ai_ext_data.get("status") if isinstance(ai_ext_data, dict) else None
    if status != "extracted":
        logger.info(
            f"[PACKAGE-MERGE] Skipping document - not extracted | fileId={file_id} | status={status}"
        )
        return [], None
    controls_block = ai_ext_data.get("controls", {}) if isinstance(ai_ext_data, dict) else {}
    controls_data: list[dict[str, Any]] = []
    if isinstance(controls_block, dict):
        controls_data = controls_block.get("controls_data", [])
    elif isinstance(controls_block, list):
        controls_data = controls_block
    if controls_data:
        logger.info(
            f"[PACKAGE-MERGE] Added document | fileId={file_id} | sections={len(controls_data)}"
        )
    return controls_data, file_hash


async def _collect_deployment_package_sections(
    session: Any, package: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    sections: list[dict[str, Any]] = []
    file_hashes: list[str] = []
    for document in package.get("documents") or []:
        if not isinstance(document, dict):
            continue
        controls_data, file_hash = await _get_document_sections(session, document)
        sections.extend(controls_data)
        if file_hash:
            file_hashes.append(file_hash)
    return sections, sorted(set(file_hashes))


async def _get_or_create_deployment_merge(
    session: Any, package: dict[str, Any], file_hashes: list[str]
) -> DeploymentPackageMerge:
    merge_id = package.get("mergeDocument")
    existing_merge = (
        await session.get(DeploymentPackageMerge, merge_id) if merge_id else None
    )
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
            id=new_id(), fileHashes=file_hashes, status="processing"
        )
    else:
        existing_merge.status = "processing"
        existing_merge.fileHashes = file_hashes
    session.add(existing_merge)
    await session.commit()
    return existing_merge


async def _mark_empty_deployment_merge(
    session: Any, merge: DeploymentPackageMerge
) -> None:
    logger.warning("[PACKAGE-MERGE] No extracted sections found in package")
    merge.status = "failed"
    merge.summary = {"message": "No extracted sections found"}
    session.add(merge)
    await session.commit()


async def _save_deployment_package_merge(
    session: Any,
    merge: DeploymentPackageMerge,
    file_hashes: list[str],
    merged_controls: list[dict[str, Any]],
    merge_summary: dict[str, Any],
) -> dict[str, Any]:
    controls_payload = {
        "total_controls": sum(len(section.get("controls", [])) for section in merged_controls),
        "total_sections": len(merged_controls),
        "controls_data": merged_controls,
    }
    await _save_merge_to_framework_merge(session, file_hashes, merged_controls, merge_summary)
    merge.status = "merged"
    merge.fileHashes = file_hashes
    merge.controls = controls_payload
    merge.summary = merge_summary
    session.add(merge)
    await session.flush()
    await session.commit()
    return controls_payload


async def _mark_deployment_merge_failed(df_id: str, pkg_ver: str, message: str) -> None:
    async with session_scope() as session:
        deployment_framework = await session.get(DeploymentFramework, df_id)
        if not deployment_framework:
            return
        package = next(
            (
                item
                for item in (deployment_framework.packages or [])
                if isinstance(item, dict) and item.get("packageVersion") == pkg_ver
            ),
            None,
        )
        merge_id = package.get("mergeDocument") if package else None
        if not merge_id:
            return
        merge = await session.get(DeploymentPackageMerge, merge_id)
        if not merge:
            return
        merge.status = "failed"
        merge.summary = {"message": message}
        session.add(merge)
        await session.commit()


async def run_deployment_package_merge(df_id: str, pkg_ver: str) -> None:
    """Merge all extracted documents in a deployment framework package."""
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()
    logger.info("[PACKAGE-MERGE-START] Package Merge Started | df=%s | version=%s", df_id, pkg_ver)
    try:
        async with session_scope() as session:
            package = await _get_deployment_package(session, df_id, pkg_ver)
            if not package:
                return
            all_sections, file_hashes = await _collect_deployment_package_sections(session, package)
            merge = await _get_or_create_deployment_merge(session, package, file_hashes)
            await _update_deployment_framework_merge_document_status(
                session, df_id, pkg_ver, merge.id
            )
            await session.commit()
            if not all_sections:
                await _mark_empty_deployment_merge(session, merge)
                return
            logger.info("[PACKAGE-MERGE] Merging documents...")
            merged_controls, merge_summary = await asyncio.to_thread(
                merge_controls_cumulative, [], all_sections
            )
            controls_payload = await _save_deployment_package_merge(
                session, merge, file_hashes, merged_controls, merge_summary
            )
            await _clear_deployment_framework_comparison_results(session, df_id)
            await session.commit()
            logger.info(
                "[PACKAGE-MERGE-SUCCESS] Complete | files=%s | controls=%s",
                len(file_hashes),
                controls_payload["total_controls"],
            )
    except Exception as exc:
        logger.exception("[PACKAGE-MERGE-ERROR] Package merge failed")
        try:
            await _mark_deployment_merge_failed(df_id, pkg_ver, f"Merge failed: {exc!s}")
        except Exception:
            logger.exception("[PACKAGE-MERGE] Failed to update failure status")


async def _clear_deployment_framework_comparison_results(session: Any, df_id: str) -> None:
    """Clear/reset stale comparison results after merge so they get recalculated."""
    try:
        from vora_shared.models import PackageComparison

        # Find all comparisons for this deployment framework package
        comparisons = (
            (
                await session.execute(
                    select(PackageComparison).where(PackageComparison.deploymentFrameworkId == df_id)
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
            logger.info(f"[PACKAGE-MERGE] Cleared {cleared_count} comparison records for recalculation")
        await session.flush()

    except Exception as e:  # noqa: BLE001
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
    file_hashes: list[str],
    merged_controls: list[dict[str, Any]],
    merge_summary: dict[str, Any],
) -> None:
    """Save merged controls to framework_merges table (canonical storage by mergeHashes)."""
    sorted_hashes = sorted(file_hashes)

    existing = (
        (await session.execute(select(FrameworkMerge).where(FrameworkMerge.mergeHashes == sorted_hashes)))
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


async def _prepare_deployment_document(
    dd_id: str, file_id: str, uploaded_ts: str
) -> tuple[str | None, str | None, str | None, dict[str, Any] | None]:
    from vora_shared.models import DeploymentDocument

    async with session_scope() as session:
        deployment_document = await session.get(DeploymentDocument, dd_id)
        if not deployment_document:
            logger.error(f"[DD-EXTRACT] Deployment Document not found: {dd_id}")
            return None, None, None, None
        doc_data = deployment_document.document or {}
        if not isinstance(doc_data, dict) or str(doc_data.get("fileId")) != file_id:
            logger.error("[DD-EXTRACT] File ID mismatch or invalid document data")
            return None, None, None, None
        extraction_id = doc_data.get("aiExtraction")
        if not extraction_id:
            logger.error("[DD-EXTRACT] No aiExtraction ID in deployment document")
            return None, None, None, None
        doc_extraction = await session.get(DocumentExtraction, extraction_id)
        if not doc_extraction:
            logger.error(f"[DD-EXTRACT] DocumentExtraction not found: {extraction_id}")
            return None, None, None, None
        ai_ext = doc_extraction.aiExtraction or {}
        status = ai_ext.get("status") if isinstance(ai_ext, dict) else None
        if status not in ("pending", "failed"):
            logger.info(f"[DD-EXTRACT] Extraction status is {status}, skipping.")
            return None, None, None, None
        file_path = doc_data.get("fileUrl")
        if file_path and file_path.startswith(UPLOADS_PREFIX):
            from vora_shared.file_storage import UPLOAD_BASE_PATH

            relative = file_path.replace(UPLOADS_PREFIX, "", 1)
            file_path = str((Path(UPLOAD_BASE_PATH) / relative).resolve())
        updated_ai_ext = dict(ai_ext)
        updated_ai_ext.update(
            {
                "status": "processing",
                "timestamp": uploaded_ts,
                "message": "Deployment document ai extraction in progress",
            }
        )
        doc_extraction.aiExtraction = updated_ai_ext
        session.add(doc_extraction)
        await session.commit()
        return file_path, str(extraction_id), doc_data.get("fileHash"), doc_data


async def _extract_deployment_document_payload(
    file_path: str, uploaded_ts: str, file_id: str, file_hash: str | None,
    doc_data: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], int]:
    chunks = await asyncio.to_thread(_load_document_chunks, file_path)
    if not chunks:
        raise ValueError("No text extracted from document")
    controls_flat = await asyncio.to_thread(extract_deployment_controls, chunks)
    controls_structured = await asyncio.to_thread(
        convert_to_section_structure, controls_flat, resource_type="deployment"
    )
    total_controls = sum(len(section.get("controls", [])) for section in controls_structured)
    controls_payload = {
        "total_controls": total_controls,
        "total_sections": len(controls_structured),
        "controls_data": controls_structured,
    }
    completed_ts = _iso()
    history = _status_history(uploaded_ts, uploaded_ts, completed_ts)
    extraction_data = {
        "status": "extracted",
        "timestamp": completed_ts,
        "message": "Deployment document AI extraction completed",
        "statusHistory": {
            "processingTimeSeconds": history["processing_time_seconds"],
            "completedAt": history["completed_at"],
            "history": [
                {
                    "status": "extracted" if item["status"] == "completed" else item["status"],
                    "timestamp": item["timestamp"],
                    "message": item.get("message"),
                }
                for item in history["history"]
            ],
        },
        "controls": controls_payload,
        "document": {
            "fileId": file_id,
            "fileHash": file_hash,
            "fileUrl": file_path,
            "fileSize": doc_data.get("fileSize"),
            "fileType": doc_data.get("fileType"),
            "originalFileName": doc_data.get("originalFileName"),
            "uploadedAt": doc_data.get("uploadedAt"),
        },
    }
    return extraction_data, history, total_controls


async def _save_deployment_document_extraction(
    dd_id: str, extraction_id: str, extraction_data: dict[str, Any]
) -> None:
    async with session_scope() as session:
        doc_extraction = await session.get(DocumentExtraction, extraction_id)
        if doc_extraction:
            doc_extraction.aiExtraction = extraction_data
            session.add(doc_extraction)
            await session.flush()
            await session.commit()
            logger.info("[DD-EXTRACT] Saved to document_extractions table")
    try:
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"http://localhost:7008/api/compliance-agent/evaluate/{dd_id}"
            )
        if response.status_code in (200, 201, 202):
            logger.info(f"[DD-EXTRACT] Triggered compliance agent for dd_id: {dd_id}")
        else:
            logger.warning(
                f"[DD-EXTRACT] Compliance agent returned status: {response.status_code}"
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[DD-EXTRACT] Could not reach compliance agent service: {exc}")


async def _mark_deployment_document_failed(extraction_id: str, message: str) -> None:
    async with session_scope() as session:
        doc_extraction = await session.get(DocumentExtraction, extraction_id)
        if not doc_extraction:
            return
        ai_data = dict(doc_extraction.aiExtraction or {})
        ai_data.update({"status": "failed", "timestamp": _iso(), "message": message})
        doc_extraction.aiExtraction = ai_data
        session.add(doc_extraction)
        await session.commit()


async def run_deployment_document_extraction(dd_id: str, file_id: str) -> None:
    """Load DeploymentDocument and run extraction when pending or failed."""
    dd_id = str(dd_id).strip()
    file_id = str(file_id).strip()
    uploaded_ts = _iso()
    extraction_id: str | None = None
    try:
        file_path, extraction_id, file_hash, doc_data = await _prepare_deployment_document(
            dd_id, file_id, uploaded_ts
        )
        if not file_path or not extraction_id or not doc_data:
            return
        extraction_data, history, total_controls = await _extract_deployment_document_payload(
            file_path, uploaded_ts, file_id, file_hash, doc_data
        )
        await _save_deployment_document_extraction(dd_id, extraction_id, extraction_data)
        logger.info(
            "[DD-EXTRACT-SUCCESS] Complete | dd_id=%s | controls=%s | processing_time=%.2fs",
            dd_id,
            total_controls,
            history["processing_time_seconds"],
        )
    except Exception as exc:
        logger.exception("[DD-EXTRACT-ERROR] Deployment document extraction failed")
        if extraction_id:
            try:
                await _mark_deployment_document_failed(
                    extraction_id, f"Extraction failed: {exc!s}"
                )
            except Exception:
                logger.exception("[DD-EXTRACT] Failed to update status in database")


async def _get_or_create_doc_extraction(
    session: Any, file_hash: str, existing_id: str | None = None
) -> DocumentExtraction:
    """Get or create a DocumentExtraction record by file hash"""
    existing = (
        await session.execute(select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash))
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
