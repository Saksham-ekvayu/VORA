"""Extract-controls HTTP + WebSocket routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.services.extraction_runner import (
    run_deployment_document_extraction,
    run_deployment_framework_extraction,
    run_deployment_package_merge,
    run_framework_extraction,
)
from fastapi import APIRouter
from sqlalchemy import func, select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    DocumentExtraction,
    DeploymentDocument,
    Framework,
)
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import error, not_found, paginated, server_error, success

logger = logging.getLogger(__name__)
router = APIRouter(tags=["extract"])

_background_tasks = set()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


def _serialize_dt(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


# ---------------------------------------------------------------------------
# Framework Extraction
# ---------------------------------------------------------------------------


@router.post("/framework/{framework_id}/files/{file_id}/ai-extract")
async def extract_framework_controls(framework_id: str, file_id: str):
    """
    Initiate AI extraction for a framework file (async background task).
    Creates immediate DB entry with processing status.
    """
    try:
        framework_id = str(framework_id).strip()
        file_id = str(file_id).strip()

        if not framework_id or not file_id:
            return error("Invalid framework_id or file_id")

        logger.info(f"[API] Extraction requested | framework={framework_id} | file={file_id}")

        # Validate framework exists and get file info
        file_hash = None
        async with session_scope() as session:
            framework = await session.get(Framework, framework_id)
            if not framework:
                return not_found(f"Framework not found: {framework_id}")

            file_versions = framework.fileVersions or []
            file_info = None
            for fv in file_versions:
                if isinstance(fv, dict) and str(fv.get("fileId")) == file_id:
                    file_info = fv
                    break

            if not file_info:
                return not_found(f"File not found in framework: {file_id}")

            file_hash = file_info.get("fileHash")
            logger.info(f"[API] File found | hash={file_hash}")

        # Create document_extraction entry immediately with "processing" status
        doc_extraction_id = None
        if file_hash:
            async with session_scope() as session:
                logger.info("[API] Creating document_extraction entry with status=processing...")

                # Check if already exists and is currently processing
                existing = (
                    await session.execute(
                        select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash)
                    )
                ).scalar_one_or_none()

                if existing:
                    ai_data = existing.aiExtraction or {}
                    if ai_data.get("status") == "processing":
                        logger.info(f"[API] ⚠️ Extraction already in progress | id={existing.id}")
                        return success(
                            message="Extraction already in progress",
                            data={
                                "framework_id": framework_id,
                                "file_id": file_id,
                                "file_hash": file_hash,
                                "extraction_id": existing.id,
                                "status": "processing",
                            },
                        )
                    doc_extraction_id = existing.id
                    logger.info(f"[API] Using existing document_extraction | id={doc_extraction_id}")
                else:
                    doc_extraction = DocumentExtraction(
                        id=new_id(),
                        fileHash=file_hash,
                        aiExtraction={
                            "status": "processing",
                            "timestamp": _iso(),
                            "message": "AI extraction in progress",
                        },
                    )
                    session.add(doc_extraction)
                    await session.flush()
                    doc_extraction_id = doc_extraction.id
                    logger.info(f"[API] Created document_extraction | id={doc_extraction_id}")

        # Queue extraction as background task (don't wait for it)
        task = asyncio.create_task(run_framework_extraction(framework_id, file_id))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        logger.info("[API] Extraction task queued")

        return success(
            message="Framework extraction started",
            data={
                "framework_id": framework_id,
                "file_id": file_id,
                "file_hash": file_hash,
                "extraction_id": doc_extraction_id,
                "status": "processing",
            },
        )

    except Exception as exc:
        logger.exception(f"[API] Request failed: {exc}")
        logger.exception("Framework extraction request error:")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# Deployment Framework Extraction
# ---------------------------------------------------------------------------


@router.post("/deployment-framework/{df_id}/packages/{pkg_ver}/files/{file_id}/ai-extract")
async def extract_deployment_framework_controls(df_id: str, pkg_ver: str, file_id: str):
    """
    Initiate AI extraction for a deployment framework file (async background task).
    Creates immediate DB entry with processing status.
    """
    try:
        df_id = str(df_id).strip()
        pkg_ver = str(pkg_ver).strip()
        file_id = str(file_id).strip()

        if not df_id or not pkg_ver or not file_id:
            return error("Invalid df_id, pkg_ver, or file_id")

        logger.info(
            f"[API] Deployment Framework extraction requested | df={df_id} | "
            f"pkg_ver={pkg_ver} | file={file_id}"
        )

        # Validate deployment framework exists and get file info
        file_hash = None
        async with session_scope() as session:
            from vora_shared.models import DeploymentFramework

            df = await session.get(DeploymentFramework, df_id)
            if not df:
                return not_found(f"Deployment Framework not found: {df_id}")

            packages = df.packages or []
            pkg_info = None
            for pkg in packages:
                if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                    pkg_info = pkg
                    break

            if not pkg_info:
                return not_found(f"Package not found in deployment framework: {pkg_ver}")

            documents = pkg_info.get("documents") or []
            file_info = None
            for doc in documents:
                if isinstance(doc, dict) and str(doc.get("fileId")) == file_id:
                    file_info = doc
                    break

            if not file_info:
                return not_found(f"File not found in package: {file_id}")

            file_hash = file_info.get("fileHash")
            logger.info(f"[API] File found | hash={file_hash}")

        # Create document_extraction entry immediately with "processing" status
        doc_extraction_id = None
        if file_hash:
            async with session_scope() as session:
                logger.info("[API] Creating document_extraction entry with status=processing...")

                # Check if already exists and is currently processing
                existing = (
                    await session.execute(
                        select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash)
                    )
                ).scalar_one_or_none()

                if existing:
                    ai_data = existing.aiExtraction or {}
                    if ai_data.get("status") == "processing":
                        logger.info(f"[API] ⚠️ Extraction already in progress | id={existing.id}")
                        return success(
                            message="Extraction already in progress",
                            data={
                                "df_id": df_id,
                                "pkg_ver": pkg_ver,
                                "file_id": file_id,
                                "file_hash": file_hash,
                                "extraction_id": existing.id,
                                "status": "processing",
                            },
                        )
                    doc_extraction_id = existing.id
                    logger.info(f"[API] Using existing document_extraction | id={doc_extraction_id}")
                else:
                    doc_extraction = DocumentExtraction(
                        id=new_id(),
                        fileHash=file_hash,
                        aiExtraction={
                            "status": "processing",
                            "timestamp": _iso(),
                            "message": "Deployment framework AI extraction in progress",
                        },
                    )
                    session.add(doc_extraction)
                    await session.flush()
                    doc_extraction_id = doc_extraction.id
                    logger.info(f"[API] Created document_extraction | id={doc_extraction_id}")

        # Queue extraction as background task (don't wait for it)
        task = asyncio.create_task(run_deployment_framework_extraction(df_id, pkg_ver, file_id))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        logger.info("[API] Deployment Framework extraction task queued")

        return success(
            message="Deployment Framework extraction started",
            data={
                "df_id": df_id,
                "pkg_ver": pkg_ver,
                "file_id": file_id,
                "file_hash": file_hash,
                "extraction_id": doc_extraction_id,
                "status": "processing",
            },
        )

    except Exception as exc:
        logger.exception(f"[API] Deployment Framework request failed: {exc}")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# Deployment Package Merge
# ---------------------------------------------------------------------------


@router.post("/deployment-framework/{df_id}/packages/{pkg_ver}/merge")
async def merge_deployment_package(df_id: str, pkg_ver: str):
    """
    Merge all extracted documents in a deployment framework package.
    Call this after all files in a package have been extracted.
    """
    try:
        df_id = str(df_id).strip()
        pkg_ver = str(pkg_ver).strip()

        if not df_id or not pkg_ver:
            return error("Invalid df_id or pkg_ver")

        logger.info(f"[API] Package merge requested | df={df_id} | pkg_ver={pkg_ver}")

        # Validate deployment framework and package exist
        async with session_scope() as session:
            from vora_shared.models import DeploymentFramework

            df = await session.get(DeploymentFramework, df_id)
            if not df:
                return not_found(f"Deployment Framework not found: {df_id}")

            packages = df.packages or []
            pkg_info = None
            for pkg in packages:
                if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                    pkg_info = pkg
                    break

            if not pkg_info:
                return not_found(f"Package not found: {pkg_ver}")

        # Queue merge as background task
        task = asyncio.create_task(run_deployment_package_merge(df_id, pkg_ver))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        logger.info("[API] Package merge task queued")

        return success(
            message="Deployment package merge started",
            data={
                "df_id": df_id,
                "pkg_ver": pkg_ver,
                "status": "processing",
            },
        )

    except Exception as exc:
        logger.exception(f"[API] Package merge request failed: {exc}")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# Deployment Document Extraction
# ---------------------------------------------------------------------------


@router.post("/deployment-document/{dd_id}/ai-extract")
async def extract_deployment_document_controls(dd_id: str):
    """
    Initiate AI extraction for a deployment document (async background task).
    The deployment document contains a single file - no need to specify file_id.
    Creates immediate DB entry with processing status.
    """
    try:
        dd_id = str(dd_id).strip()

        if not dd_id:
            return error("Invalid dd_id")

        logger.info(f"[API] Deployment Document extraction requested | dd={dd_id}")

        # Validate deployment document exists and get file info
        file_hash = None
        file_id = None
        async with session_scope() as session:
            dd = await session.get(DeploymentDocument, dd_id)
            if not dd:
                return not_found(f"Deployment Document not found: {dd_id}")

            doc_data = dd.document or {}
            if isinstance(doc_data, dict):
                file_info = doc_data
                file_id = file_info.get("fileId")
                file_hash = file_info.get("fileHash")
                logger.info(f"[API] File found | fileId={file_id} | hash={file_hash}")

            if not file_hash or not file_id:
                return not_found(f"No file found in deployment document: {dd_id}")

        # Create document_extraction entry immediately with "processing" status
        doc_extraction_id = None
        if file_hash:
            async with session_scope() as session:
                logger.info("[API] Creating document_extraction entry with status=processing...")

                # Check if already exists and is currently processing
                existing = (
                    await session.execute(
                        select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash)
                    )
                ).scalar_one_or_none()

                if existing:
                    ai_data = existing.aiExtraction or {}
                    if ai_data.get("status") == "processing":
                        logger.info(f"[API] ⚠️ Extraction already in progress | id={existing.id}")
                        return success(
                            message="Extraction already in progress",
                            data={
                                "dd_id": dd_id,
                                "file_hash": file_hash,
                                "extraction_id": existing.id,
                                "status": "processing",
                            },
                        )
                    doc_extraction_id = existing.id
                    logger.info(f"[API] Using existing document_extraction | id={doc_extraction_id}")
                else:
                    doc_extraction = DocumentExtraction(
                        id=new_id(),
                        fileHash=file_hash,
                        aiExtraction={
                            "status": "processing",
                            "timestamp": _iso(),
                            "message": "Deployment document AI extraction in progress",
                        },
                    )
                    session.add(doc_extraction)
                    await session.flush()
                    doc_extraction_id = doc_extraction.id
                    logger.info(f"[API] ✅ Created document_extraction | id={doc_extraction_id}")

        # Queue extraction as background task (don't wait for it)
        task = asyncio.create_task(run_deployment_document_extraction(dd_id, file_id))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        logger.info("[API] ✅ Deployment Document extraction task queued")

        return success(
            message="Deployment Document extraction started",
            data={
                "dd_id": dd_id,
                "file_hash": file_hash,
                "extraction_id": doc_extraction_id,
                "status": "processing",
            },
        )

    except Exception as exc:
        logger.exception(f"[API] ❌ Deployment Document request failed: {exc}")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# Deployment Document Extraction Data Retrieval
# ---------------------------------------------------------------------------


@router.get("/deployment-document/{dd_id}")
async def get_deployment_document(dd_id: str):
    """
    Get a deployment document by ID with its extraction data.
    Returns the document info along with any AI extraction results.
    """
    try:
        dd_id = str(dd_id).strip()
        if not dd_id:
            return error("Invalid dd_id")

        logger.info(f"[GET-DD] Fetching deployment document | id={dd_id}")
        async with session_scope() as session:
            dd = await session.get(DeploymentDocument, dd_id)
            if not dd:
                return not_found(f"Deployment Document not found: {dd_id}")

            logger.info(f"[GET-DD] ✅ Retrieved deployment document | id={dd_id}")

            # Get extraction data if document has aiExtraction
            doc_data = dd.document or {}
            ai_extraction = doc_data.get("aiExtraction") if isinstance(doc_data, dict) else None

            return success(
                message="Deployment document retrieved successfully",
                data={
                    "id": dd.id,
                    "tenantId": dd.tenantId,
                    "deploymentFrameworkId": dd.deploymentFrameworkId,
                    "frameworkName": dd.frameworkName,
                    "frameworkCode": dd.frameworkCode,
                    "frameworkVersion": dd.frameworkVersion,
                    "uploadedBy": dd.uploadedBy,
                    "document": dd.document,
                    "aiExtraction": ai_extraction,
                    "createdAt": _serialize_dt(dd.createdAt),
                    "updatedAt": _serialize_dt(dd.updatedAt),
                },
            )
    except Exception as exc:
        logger.error(f"[GET-DD] Error for dd_id={dd_id}: {exc}")
        logger.exception("get_deployment_document error")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# Deployment Document Extraction
# ---------------------------------------------------------------------------



@router.get("/document-extraction/{file_hash}")
async def get_document_extraction(file_hash: str):
    """
    Get extraction data by file hash from document_extractions table.
    This retrieves cached AI extraction results.

    Args:
        file_hash: The file hash to look up

    Returns:
        Extraction data with controls, status, and history
    """
    try:
        file_hash = str(file_hash).strip()
        if not file_hash:
            logger.warning("[GET-EXTRACTION] Invalid file_hash provided")
            return error("Invalid file_hash")

        logger.info(f"[GET-EXTRACTION] Fetching extraction | file_hash={file_hash}")
        async with session_scope() as session:
            doc_extraction = (
                await session.execute(
                    select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash)
                )
            ).scalar_one_or_none()

            if not doc_extraction:
                logger.warning(f"[GET-EXTRACTION] No extraction found | file_hash={file_hash}")
                return not_found(f"No extraction found for file hash: {file_hash}")

            ai_data = doc_extraction.aiExtraction or {}
            status = ai_data.get("status", "pending")
            logger.info(f"[GET-EXTRACTION] Retrieved extraction | id={doc_extraction.id} | status={status}")

            return success(
                message="Document extraction data retrieved successfully",
                data={
                    "id": doc_extraction.id,
                    "fileHash": doc_extraction.fileHash,
                    "status": status,
                    "message": ai_data.get("message"),
                    "timestamp": ai_data.get("timestamp"),
                    "controls": ai_data.get("controls", {}),
                    "statusHistory": ai_data.get("statusHistory", {}),
                    "createdAt": _serialize_dt(doc_extraction.createdAt),
                    "updatedAt": _serialize_dt(doc_extraction.updatedAt),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[GET-EXTRACTION] Error for file_hash={file_hash}: {exc}")
        logger.exception("get_document_extraction error | file_hash=%s", file_hash)
        return server_error(str(exc))


@router.get("/document-extractions")
async def list_document_extractions(page: int = 1, page_size: int = 10):
    """
    List all document extractions with pagination.

    Returns:
        Paginated list of document extractions
    """
    try:
        page = clamp_page(page)
        page_size = clamp_limit(page_size, default=10)

        logger.info(f"[LIST-EXTRACTIONS] Listing extractions | page={page} | page_size={page_size}")
        async with session_scope() as session:
            total = (await session.execute(select(func.count()).select_from(DocumentExtraction))).scalar_one()

            rows = (
                (
                    await session.execute(
                        select(DocumentExtraction)
                        .order_by(DocumentExtraction.createdAt.desc())
                        .offset((page - 1) * page_size)
                        .limit(page_size)
                    )
                )
                .scalars()
                .all()
            )

            items = []
            for doc in rows:
                ai_data = doc.aiExtraction or {}
                controls = ai_data.get("controls", {})
                total_controls = controls.get("total_controls", 0) if isinstance(controls, dict) else 0

                items.append(
                    {
                        "id": doc.id,
                        "fileHash": doc.fileHash,
                        "status": ai_data.get("status", "pending"),
                        "total_controls": total_controls,
                        "total_sections": (
                            controls.get("total_sections", 0) if isinstance(controls, dict) else 0
                        ),
                        "created_at": _serialize_dt(doc.createdAt),
                        "updated_at": _serialize_dt(doc.updatedAt),
                    }
                )

            logger.info(f"[LIST-EXTRACTIONS] Retrieved {len(items)} extractions from {total} total")
            return paginated(
                data=items,
                pagination=build_pagination_meta(page, page_size, total),
                message=f"Retrieved {len(items)} document extractions",
            )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[LIST-EXTRACTIONS] Error: {exc}")
        logger.exception("list_document_extractions error")
        return server_error(str(exc))
