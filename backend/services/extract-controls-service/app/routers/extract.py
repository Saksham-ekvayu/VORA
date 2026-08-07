"""Extract-controls HTTP + WebSocket routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.services.extraction_runner import (
    run_framework_extraction,
)
from fastapi import APIRouter
from sqlalchemy import func, select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    Framework,
    DocumentExtraction,
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

                # Check if already exists
                existing = (
                    await session.execute(
                        select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash)
                    )
                ).scalar_one_or_none()

                if existing:
                    doc_extraction_id = existing.id
                    logger.info(
                        f"[API] Using existing document_extraction | id={doc_extraction_id}"
                    )
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
                    logger.info(f"[API] ✅ Created document_extraction | id={doc_extraction_id}")

        # Queue extraction as background task (don't wait for it)
        task = asyncio.create_task(run_framework_extraction(framework_id, file_id))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        logger.info("[API] ✅ Extraction task queued")

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
        logger.exception(f"[API] ❌ Request failed: {exc}")
        logger.exception("Framework extraction request error:")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# Document Extraction Data Retrieval
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
            return error("Invalid file_hash")

        async with session_scope() as session:
            doc_extraction = (
                await session.execute(
                    select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash)
                )
            ).scalar_one_or_none()

            if not doc_extraction:
                return not_found(f"No extraction found for file hash: {file_hash}")

            ai_data = doc_extraction.aiExtraction or {}

            return success(
                message="Document extraction data retrieved successfully",
                data={
                    "id": doc_extraction.id,
                    "fileHash": doc_extraction.fileHash,
                    "status": ai_data.get("status", "pending"),
                    "message": ai_data.get("message"),
                    "timestamp": ai_data.get("timestamp"),
                    "controls": ai_data.get("controls", {}),
                    "statusHistory": ai_data.get("statusHistory", {}),
                    "createdAt": _serialize_dt(doc_extraction.createdAt),
                    "updatedAt": _serialize_dt(doc_extraction.updatedAt),
                },
            )
    except Exception as exc:  # noqa: BLE001
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

        async with session_scope() as session:
            total = (
                await session.execute(select(func.count()).select_from(DocumentExtraction))
            ).scalar_one()

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
                total_controls = (
                    controls.get("total_controls", 0) if isinstance(controls, dict) else 0
                )

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

            return paginated(
                data=items,
                pagination=build_pagination_meta(page, page_size, total),
                message=f"Retrieved {len(items)} document extractions",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("list_document_extractions error")
        return server_error(str(exc))
