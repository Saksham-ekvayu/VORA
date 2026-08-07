"""Extract-controls HTTP + WebSocket routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.extraction_runner import (
    run_deployment_extraction,
    run_framework_extraction,
    run_package_merge,
)
from fastapi import APIRouter, Body
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    ExtractionResult,
    PackageMergeTracking,
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
    try:
        page = clamp_page(page)
        page_size = clamp_limit(page_size, default=10)
        async with session_scope() as session:
            total = (await session.execute(select(func.count()).select_from(ExtractionResult))).scalar_one()
            rows = (
                (
                    await session.execute(
                        select(ExtractionResult)
                        .order_by(ExtractionResult.createdAt.desc())
                        .offset((page - 1) * page_size)
                        .limit(page_size)
                    )
                )
                .scalars()
                .all()
            )

            items = []
            for e in rows:
                result = e.result or {}
                controls = result.get("controls") or {}
                total_controls = controls.get("total_controls", 0) if isinstance(controls, dict) else 0
                items.append(
                    {
                        "id": e.ref_id,
                        "resourceType": e.resource_type,
                        "status": e.status,
                        "total_controls": total_controls,
                        "created_at": _serialize_dt(e.createdAt),
                        "package_version": e.package_version,
                        "file_id": e.file_id,
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



