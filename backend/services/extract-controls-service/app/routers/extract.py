"""Extract-controls HTTP + WebSocket routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.extraction_runner import (
    run_deployment_extraction,
    run_framework_extraction,
    run_package_merge,
    _load_document_chunks,
)
from app.services import control_extractor
from fastapi import APIRouter, Body
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    ExtractionResult,
    Framework,
    PackageMergeTracking,
    DocumentExtraction,
)
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import error, not_found, paginated, server_error, success

logger = logging.getLogger(__name__)
router = APIRouter(tags=["extract"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


def _serialize_dt(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def _extract_ai_data(
    file_versions: list[Any],
    status: str,
    processing_time: int,
    status_history: dict[str, Any],
    controls: list[Any],
) -> tuple[str, int, dict[str, Any], list[Any]]:
    if not file_versions:
        return status, processing_time, status_history, controls

    aiupload = {}
    for fv in reversed(file_versions):
        if not isinstance(fv, dict):
            continue
        a = fv.get("aiUpload") or fv.get("aiExtraction") or {}
        if a.get("status") in ("extracted", "completed"):
            aiupload = a
            break
    if not aiupload and isinstance(file_versions[-1], dict):
        aiupload = file_versions[-1].get("aiUpload") or file_versions[-1].get("aiExtraction") or {}

    new_status = aiupload.get("status", status)
    new_pt = aiupload.get("processing_time_seconds", processing_time)
    new_sh = aiupload.get("status_history", status_history)
    new_ctrls = (aiupload.get("controls") or {}).get("controls_data", controls)

    return new_status, new_pt, new_sh, new_ctrls


@router.get("/results/{id}")
async def get_extraction_results(id: str):
    try:
        async with session_scope() as session:
            row = (
                await session.execute(select(ExtractionResult).where(ExtractionResult.ref_id == id))
            ).scalar_one_or_none()
            if not row:
                # Fallback: treat id as ExtractionResult PK
                row = await session.get(ExtractionResult, id)
            if not row:
                return not_found(f"Extraction not found for id: {id}")

            result = row.result or {}
            controls = []
            status = row.status or "uploaded"
            status_history = result.get("status_history") or {}
            processing_time = 0
            if isinstance(result.get("controls"), dict):
                controls = result["controls"].get("controls_data") or []
                processing_time = (result.get("status_history") or {}).get("processing_time_seconds", 0)
            file_versions = result.get("fileVersions") or []
            status, processing_time, status_history, controls = _extract_ai_data(
                file_versions, status, processing_time, status_history, controls
            )

            return success(
                message="Extraction results retrieved successfully",
                data={
                    "id": row.ref_id,
                    "resourceType": row.resource_type,
                    "status": status,
                    "started_at": _serialize_dt(row.createdAt),
                    "completed_at": (
                        status_history.get("completed_at") if isinstance(status_history, dict) else None
                    ),
                    "processing_time_seconds": processing_time,
                    "total_controls": len(controls) if isinstance(controls, list) else 0,
                    "controls": controls,
                    "status_history": status_history,
                    "fileVersions": file_versions,
                    "package_version": row.package_version,
                    "file_id": row.file_id,
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_extraction_results error | id=%s", id)
        return server_error(str(exc))


@router.get("/list")
async def list_extractions(page: int = 1, page_size: int = 10):
    """List all extractions from document_extractions table"""
    try:
        page = clamp_page(page)
        page_size = clamp_limit(page_size, default=10)
        async with session_scope() as session:
            total = (
                await session.execute(
                    select(func.count()).select_from(DocumentExtraction)
                )
            ).scalar_one()
            
            rows = (
                (
                    await session.execute(
                        select(DocumentExtraction)
                        .order_by(DocumentExtraction.updatedAt.desc())
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
                        "total_sections": controls.get("total_sections", 0) if isinstance(controls, dict) else 0,
                        "created_at": _serialize_dt(doc.createdAt),
                        "updated_at": _serialize_dt(doc.updatedAt),
                    }
                )
            return paginated(
                data=items,
                pagination=build_pagination_meta(page, page_size, total),
                message=f"Retrieved {len(items)} extractions",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("list_extractions error")
        return server_error(str(exc))


@router.get("/package-merges")
async def get_package_merges(ref_id: Optional[str] = None, page: int = 1, page_size: int = 50):
    try:
        page = clamp_page(page)
        page_size = clamp_limit(page_size, default=50)
        async with session_scope() as session:
            stmt = select(PackageMergeTracking)
            count_stmt = select(func.count()).select_from(PackageMergeTracking)
            if ref_id:
                stmt = stmt.where(PackageMergeTracking.deployment_framework_id == ref_id)
                count_stmt = count_stmt.where(PackageMergeTracking.deployment_framework_id == ref_id)
            total = (await session.execute(count_stmt)).scalar_one()
            rows = (
                (
                    await session.execute(
                        stmt.order_by(PackageMergeTracking.updatedAt.desc())
                        .offset((page - 1) * page_size)
                        .limit(page_size)
                    )
                )
                .scalars()
                .all()
            )
            merge_data = []
            for m in rows:
                data = m.data or {}
                merge_data.append(
                    {
                        "id": m.id,
                        "deploymentFrameworkId": m.deployment_framework_id,
                        "packageVersion": m.package_version,
                        "status": m.status,
                        "mergeRefId": data.get("mergeRefId"),
                        "mergeHistoryCount": len(data.get("mergeHistory") or []),
                        "mergeHistory": data.get("mergeHistory") or [],
                        "createdAt": _serialize_dt(m.createdAt),
                        "updatedAt": _serialize_dt(m.updatedAt),
                    }
                )
            return paginated(
                data=merge_data,
                pagination=build_pagination_meta(page, page_size, total),
                message=f"Retrieved {len(merge_data)} package merges",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_package_merges error")
        return server_error(str(exc))


@router.get("/package-merges/{deployment_framework_id}/{package_version}")
async def get_package_merge_by_version(deployment_framework_id: str, package_version: str):
    try:
        async with session_scope() as session:
            track = (
                await session.execute(
                    select(PackageMergeTracking).where(
                        PackageMergeTracking.deployment_framework_id == deployment_framework_id,
                        PackageMergeTracking.package_version == package_version,
                    )
                )
            ).scalar_one_or_none()
            if not track:
                return not_found("Package merge not found")
            data = track.data or {}
            return success(
                message="Package merge retrieved successfully",
                data={
                    "id": track.id,
                    "deploymentFrameworkId": track.deployment_framework_id,
                    "packageVersion": track.package_version,
                    "status": track.status,
                    "mergeRefId": data.get("mergeRefId"),
                    "mergeHistory": data.get("mergeHistory") or [],
                    "controls_data": data.get("controls_data") or [],
                    "createdAt": _serialize_dt(track.createdAt),
                    "updatedAt": _serialize_dt(track.updatedAt),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_package_merge_by_version error")
        return server_error(str(exc))


@router.delete("/delete/{id}")
async def delete_extraction(id: str):
    try:
        async with session_scope() as session:
            rows = (
                (await session.execute(select(ExtractionResult).where(ExtractionResult.ref_id == id)))
                .scalars()
                .all()
            )
            if not rows:
                row = await session.get(ExtractionResult, id)
                rows = [row] if row else []
            if not rows:
                return not_found(f"Extraction not found: {id}")
            for row in rows:
                await session.delete(row)
            return success(message="Extraction deleted successfully", data={"id": id})
    except Exception as exc:  # noqa: BLE001
        logger.exception("delete_extraction error | id=%s", id)
        return server_error(str(exc))


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
                logger.info(f"[API] Creating document_extraction entry with status=processing...")
                
                # Check if already exists
                existing = (
                    await session.execute(
                        select(DocumentExtraction).where(
                            DocumentExtraction.fileHash == file_hash
                        )
                    )
                ).scalar_one_or_none()
                
                if existing:
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
                    logger.info(f"[API] ✅ Created document_extraction | id={doc_extraction_id}")
        
        # Queue extraction as background task (don't wait for it)
        asyncio.create_task(run_framework_extraction(framework_id, file_id))
        logger.info(f"[API] ✅ Extraction task queued")
        
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
        logger.error(f"[API] ❌ Request failed: {exc}")
        logger.exception("Framework extraction request error:")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# Deployment Document Extraction
# ---------------------------------------------------------------------------


@router.post("/deployment-document/{deployment_doc_id}/ai-extract")
async def extract_deployment_document_controls(deployment_doc_id: str):
    """
    Initiate AI extraction for a deployment document.
    
    Args:
        deployment_doc_id: The deployment document ID
    
    Returns:
        Extraction result with status and controls data
    """
    try:
        deployment_doc_id = str(deployment_doc_id).strip()
        
        if not deployment_doc_id:
            return error("Invalid deployment_doc_id")
        
        # Validate deployment document exists
        async with session_scope() as session:
            from vora_shared.models import DeploymentDocument
            
            doc = await session.get(DeploymentDocument, deployment_doc_id)
            if not doc:
                return not_found(f"Deployment document not found: {deployment_doc_id}")
        
        # Store extraction result
        extraction_id = await _upsert_extraction_result(
            ref_id=deployment_doc_id,
            resource_type="deployment-document",
            file_id=None,
            package_version=None,
            status="processing",
            result={"status": "processing", "started_at": _iso()},
        )
        
        return success(
            message="Deployment document extraction started",
            data={
                "deployment_doc_id": deployment_doc_id,
                "extraction_id": extraction_id,
                "status": "processing",
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("extract_deployment_document_controls error | doc=%s", deployment_doc_id)
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# Deployment Framework Package Extraction
# ---------------------------------------------------------------------------


@router.post("/deployment-framework/{deployment_framework_id}/package/{package_version}/files/{file_id}/ai-extract")
async def extract_deployment_package_document(
    deployment_framework_id: str,
    package_version: str,
    file_id: str,
):
    """
    Initiate AI extraction for a deployment framework package document.
    
    Args:
        deployment_framework_id: The deployment framework ID
        package_version: The package version
        file_id: The file ID within the package
    
    Returns:
        Extraction result with status and controls data
    """
    try:
        deployment_framework_id = str(deployment_framework_id).strip()
        package_version = str(package_version).strip()
        file_id = str(file_id).strip()
        
        if not deployment_framework_id or not package_version or not file_id:
            return error("Invalid deployment_framework_id, package_version, or file_id")
        
        # Validate deployment framework and package exists
        async with session_scope() as session:
            from vora_shared.models import DeploymentFramework
            
            df = await session.get(DeploymentFramework, deployment_framework_id)
            if not df:
                return not_found(f"Deployment framework not found: {deployment_framework_id}")
            
            # Validate package exists
            packages = df.packages or []
            package_found = False
            file_found = False
            
            for pkg in packages:
                if isinstance(pkg, dict) and pkg.get("packageVersion") == package_version:
                    package_found = True
                    documents = pkg.get("documents") or []
                    for doc in documents:
                        if isinstance(doc, dict) and str(doc.get("fileId")) == file_id:
                            file_found = True
                            break
                    break
            
            if not package_found:
                return not_found(f"Package not found: {package_version}")
            
            if not file_found:
                return not_found(f"File not found in package: {file_id}")
        
        # Trigger extraction asynchronously
        asyncio.create_task(run_deployment_extraction(deployment_framework_id, package_version, file_id))
        
        return success(
            message="Deployment package document extraction started",
            data={
                "deployment_framework_id": deployment_framework_id,
                "package_version": package_version,
                "file_id": file_id,
                "status": "processing",
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "extract_deployment_package_document error | df=%s pkg=%s file=%s",
            deployment_framework_id,
            package_version,
            file_id,
        )
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
                    select(DocumentExtraction).where(
                        DocumentExtraction.fileHash == file_hash
                    )
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
                await session.execute(
                    select(func.count()).select_from(DocumentExtraction)
                )
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
                total_controls = controls.get("total_controls", 0) if isinstance(controls, dict) else 0
                
                items.append(
                    {
                        "id": doc.id,
                        "fileHash": doc.fileHash,
                        "status": ai_data.get("status", "pending"),
                        "total_controls": total_controls,
                        "total_sections": controls.get("total_sections", 0) if isinstance(controls, dict) else 0,
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
