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
from app.utils.ws_manager import manager
from fastapi import APIRouter, Body, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    DeploymentFramework,
    ExtractionResult,
    Framework,
    FrameworkAssignment,
    PackageMergeTracking,
)
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import error, not_found, paginated, server_error, success

logger = logging.getLogger(__name__)
router = APIRouter(tags=["extract"])


class ControlUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    deployment_points: Optional[list[dict[str, Any]]] = None
    id: Optional[str] = None


class AddControlRequest(BaseModel):
    name: str
    description: str = ""
    deployment_points: list[dict[str, Any]] = Field(default_factory=list)
    section_id: Optional[str] = None
    new_section: Optional[dict[str, Any]] = None


class ApprovalStatusRequest(BaseModel):
    status: str
    timestamp: Optional[str] = None
    reason: Optional[str] = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


def _serialize_dt(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


# ---------------------------------------------------------------------------
# Health / reads
# ---------------------------------------------------------------------------


@router.get("/health")
async def health_check():
    return success(
        message="Service is healthy",
        data={"status": "healthy", "service": "extract-controls-service"},
    )


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
            if file_versions:
                aiupload = {}
                for fv in reversed(file_versions):
                    if not isinstance(fv, dict):
                        continue
                    a = fv.get("aiUpload") or fv.get("aiExtraction") or {}
                    if a.get("status") in ("extracted", "completed"):
                        aiupload = a
                        break
                if not aiupload and isinstance(file_versions[-1], dict):
                    aiupload = (
                        file_versions[-1].get("aiUpload") or file_versions[-1].get("aiExtraction") or {}
                    )
                status = aiupload.get("status", status)
                processing_time = aiupload.get("processing_time_seconds", processing_time)
                status_history = aiupload.get("status_history", status_history)
                controls = (aiupload.get("controls") or {}).get("controls_data", controls)

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


@router.get("/frameworks/{id}")
async def get_framework(id: str):
    try:
        async with session_scope() as session:
            fw = await session.get(Framework, id)
            if not fw:
                return not_found(f"Framework not found for id: {id}")
            return success(
                message="Framework retrieved successfully",
                data={
                    "id": fw.id,
                    "frameworkName": fw.frameworkName,
                    "frameworkVersion": fw.frameworkVersion,
                    "frameworkCategoryId": fw.frameworkCategoryId,
                    "frameworkCode": fw.frameworkCode,
                    "uploadedBy": fw.uploadedBy,
                    "currentFileVersion": fw.currentFileVersion,
                    "fileVersions": fw.fileVersions or [],
                    "approval": fw.approval or {},
                    "createdAt": _serialize_dt(fw.createdAt),
                    "updatedAt": _serialize_dt(fw.updatedAt),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_framework error | id=%s", id)
        return server_error(str(exc))


@router.get("/deployment-frameworks/{id}")
async def get_deployment_framework(id: str):
    try:
        async with session_scope() as session:
            df = await session.get(DeploymentFramework, id)
            if not df:
                return not_found(f"DeploymentFramework not found for id: {id}")
            return success(
                message="Deployment framework retrieved successfully",
                data={
                    "id": df.id,
                    "tenantId": df.tenantId,
                    "assignedFrameworkId": df.assignedFrameworkId,
                    "frameworkId": df.frameworkId,
                    "frameworkName": df.frameworkName,
                    "frameworkCode": df.frameworkCode,
                    "frameworkVersion": df.frameworkVersion,
                    "uploadedBy": df.uploadedBy,
                    "currentPackageVersion": df.currentPackageVersion,
                    "packages": df.packages or [],
                    "createdAt": _serialize_dt(df.createdAt),
                    "updatedAt": _serialize_dt(df.updatedAt),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_deployment_framework error | id=%s", id)
        return server_error(str(exc))


@router.get("/framework-assignments/{id}")
async def get_framework_assignment(id: str):
    try:
        async with session_scope() as session:
            fa = await session.get(FrameworkAssignment, id)
            if not fa:
                return not_found(f"FrameworkAssignment not found for id: {id}")
            return success(
                message="Framework assignment retrieved successfully",
                data={
                    "id": fa.id,
                    "tenantId": fa.tenantId,
                    "customerId": fa.customerId,
                    "frameworkId": fa.frameworkId,
                    "frameworkCode": fa.frameworkCode,
                    "frameworkName": fa.frameworkName,
                    "frameworkVersion": fa.frameworkVersion,
                    "currentFileVersion": fa.currentFileVersion,
                    "fileVersions": fa.fileVersions or [],
                    "status": fa.status,
                    "assignment": fa.assignment or {},
                    "finalization": fa.finalization or {},
                    "createdAt": _serialize_dt(fa.createdAt),
                    "updatedAt": _serialize_dt(fa.updatedAt),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_framework_assignment error | id=%s", id)
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
# WebSockets — start engine on connect
# ---------------------------------------------------------------------------


@router.websocket("/ws/framework/{id}/fileid/{file_id}")
async def ws_framework(websocket: WebSocket, id: str, file_id: str):
    id = id.strip()
    file_id = file_id.strip()
    conn_key = f"framework:{id}:{file_id}"
    await manager.connect(conn_key, websocket)

    async def send_cb(msg: dict[str, Any]) -> None:
        await manager.send_json(conn_key, msg)

    task = asyncio.create_task(run_framework_extraction(id, file_id, send_cb))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(conn_key, websocket)
    except Exception as exc:  # noqa: BLE001
        logger.error("WS framework error | %s", exc, exc_info=True)
        await manager.disconnect(conn_key, websocket)
    finally:
        if not task.done():
            # Let extraction finish even if client disconnects mid-flight
            pass


@router.websocket("/ws/deployment-framework/{id}/packageVersion/{pkg_ver}/fileid/{file_id}")
async def ws_deployment_framework(websocket: WebSocket, id: str, pkg_ver: str, file_id: str):
    id = id.strip()
    pkg_ver = pkg_ver.strip()
    file_id = file_id.strip()
    conn_key = f"deployment-framework:{id}:{pkg_ver}:{file_id}"
    await manager.connect(conn_key, websocket)

    async def send_cb(msg: dict[str, Any]) -> None:
        await manager.send_json(conn_key, msg)

    task = asyncio.create_task(run_deployment_extraction(id, pkg_ver, file_id, send_cb))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(conn_key, websocket)
    except Exception as exc:  # noqa: BLE001
        logger.error("WS deployment-framework error | %s", exc, exc_info=True)
        await manager.disconnect(conn_key, websocket)
    finally:
        _ = task


def _normalize_ws_param(value: str) -> str:
    return (value or "").strip()


@router.websocket("/ws/package-merge/{deployment_framework_id}/{package_version}")
async def ws_package_merge(websocket: WebSocket, deployment_framework_id: str, package_version: str):
    deployment_framework_id = _normalize_ws_param(deployment_framework_id)
    package_version = _normalize_ws_param(package_version)

    if not deployment_framework_id or not package_version:
        await websocket.accept()
        await websocket.send_json(
            {
                "event": "merge_url_failed",
                "data": {
                    "id": deployment_framework_id,
                    "status": "validation_failed",
                    "message": "WebSocket URL or parameter validation failed",
                    "timestamp": _iso(),
                },
            }
        )
        await websocket.close(code=1008)
        return

    if package_version and not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", package_version):
        await websocket.accept()
        await websocket.send_json(
            {
                "event": "merge_url_failed",
                "data": {
                    "id": deployment_framework_id,
                    "status": "validation_failed",
                    "message": "packageVersion must use semantic version format x.y.z",
                    "timestamp": _iso(),
                },
            }
        )
        await websocket.close(code=1008)
        return

    conn_key = f"package-merge:{deployment_framework_id}:{package_version}"
    await manager.connect(conn_key, websocket)

    async def send_cb(msg: dict[str, Any]) -> None:
        await manager.send_json(conn_key, msg)

    task = asyncio.create_task(run_package_merge(deployment_framework_id, package_version, send_cb))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(conn_key, websocket)
    except Exception as exc:  # noqa: BLE001
        logger.error("WS package-merge error | %s", exc, exc_info=True)
        await manager.disconnect(conn_key, websocket)
    finally:
        _ = task


# ---------------------------------------------------------------------------
# Framework control CRUD (AI jobs paths used by framework-service)
# ---------------------------------------------------------------------------


def _get_controls_from_framework(fw: Framework, file_version: str) -> tuple[list, dict | None, int | None]:
    versions = list(fw.fileVersions or [])
    for i, fv in enumerate(versions):
        if not isinstance(fv, dict):
            continue
        if str(fv.get("fileVersion")) == str(file_version):
            ai = dict(fv.get("aiExtraction") or {})
            controls_block = ai.get("controls") or {}
            if isinstance(controls_block, dict):
                return list(controls_block.get("controls_data") or []), fv, i
            if isinstance(controls_block, list):
                return list(controls_block), fv, i
            return [], fv, i
    return [], None, None


def _set_controls_on_framework(fw: Framework, fv_idx: int, fv: dict, controls_data: list) -> None:
    versions = list(fw.fileVersions or [])
    ai = dict(fv.get("aiExtraction") or {})
    total = sum(len(s.get("controls") or []) for s in controls_data if isinstance(s, dict))
    ai["controls"] = {
        "total_controls": total,
        "total_sections": len(controls_data),
        "controls_data": controls_data,
    }
    if not ai.get("status"):
        ai["status"] = "extracted"
    fv["aiExtraction"] = ai
    versions[fv_idx] = fv
    fw.fileVersions = versions


async def _sync_extraction_result_controls(ref_id: str, file_version: str, controls_data: list):
    async with session_scope() as session:
        row = (
            await session.execute(
                select(ExtractionResult).where(
                    ExtractionResult.ref_id == ref_id,
                    ExtractionResult.resource_type == "framework",
                )
            )
        ).scalar_one_or_none()
        if not row:
            return
        result = dict(row.result or {})
        controls = {
            "total_controls": sum(len(s.get("controls") or []) for s in controls_data if isinstance(s, dict)),
            "total_sections": len(controls_data),
            "controls_data": controls_data,
        }
        result["controls"] = controls
        file_versions = list(result.get("fileVersions") or [])
        for i, fv in enumerate(file_versions):
            if isinstance(fv, dict) and str(fv.get("fileVersion")) == str(file_version):
                ai = dict(fv.get("aiUpload") or {})
                ai["controls"] = controls
                fv["aiUpload"] = ai
                file_versions[i] = fv
        result["fileVersions"] = file_versions
        row.result = result
        row.updatedAt = _utcnow()


@router.patch("/ai/jobs/{id}/file-versions/{file_version}/controls/{control_id}")
async def update_control(id: str, file_version: str, control_id: str, body: ControlUpdateRequest):
    try:
        async with session_scope() as session:
            fw = await session.get(Framework, id)
            if not fw:
                return not_found(f"Framework not found: {id}")
            controls_data, fv, fv_idx = _get_controls_from_framework(fw, file_version)
            if fv is None or fv_idx is None:
                return not_found(f"File version not found: {file_version}")

            update_data = body.model_dump(exclude_none=True)
            found = False
            for section in controls_data:
                for control in section.get("controls") or []:
                    cid = control.get("id") or control.get("Control_id")
                    if str(cid) == str(control_id):
                        control.update(update_data)
                        found = True
                        break
                if found:
                    break
            if not found:
                return not_found(f"Control not found: {control_id}")

            _set_controls_on_framework(fw, fv_idx, fv, controls_data)

        await _sync_extraction_result_controls(id, file_version, controls_data)
        return success(
            message="Control updated successfully",
            data={"id": id, "fileVersion": file_version, "controlId": control_id},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("update_control error")
        return server_error(str(exc))


@router.delete("/ai/jobs/{id}/file-versions/{file_version}/controls/{control_id}")
async def delete_control(id: str, file_version: str, control_id: str):
    try:
        async with session_scope() as session:
            fw = await session.get(Framework, id)
            if not fw:
                return not_found(f"Framework not found: {id}")
            controls_data, fv, fv_idx = _get_controls_from_framework(fw, file_version)
            if fv is None or fv_idx is None:
                return not_found(f"File version not found: {file_version}")

            found = False
            for section in controls_data:
                controls = section.get("controls") or []
                new_controls = [
                    c for c in controls if str(c.get("id") or c.get("Control_id")) != str(control_id)
                ]
                if len(new_controls) != len(controls):
                    section["controls"] = new_controls
                    found = True
            if not found:
                return not_found(f"Control not found: {control_id}")

            _set_controls_on_framework(fw, fv_idx, fv, controls_data)

        await _sync_extraction_result_controls(id, file_version, controls_data)
        return success(
            message="Control deleted successfully",
            data={"id": id, "fileVersion": file_version, "controlId": control_id},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("delete_control error")
        return server_error(str(exc))


@router.post("/ai/jobs/{id}/file-versions/{file_version}/controls")
async def add_control(id: str, file_version: str, body: AddControlRequest):
    try:
        async with session_scope() as session:
            fw = await session.get(Framework, id)
            if not fw:
                return not_found(f"Framework not found: {id}")
            controls_data, fv, fv_idx = _get_controls_from_framework(fw, file_version)
            if fv is None or fv_idx is None:
                return not_found(f"File version not found: {file_version}")

            new_control = {
                "id": new_id(),
                "name": body.name,
                "description": body.description or "",
                "deployment_points": body.deployment_points or [],
            }

            if body.new_section:
                section = {
                    "id": body.new_section.get("id") or new_id(),
                    "name": body.new_section.get("name") or "Custom Section",
                    "controls": [new_control],
                }
                controls_data.append(section)
            else:
                target = None
                if body.section_id:
                    for section in controls_data:
                        if str(section.get("id")) == str(body.section_id):
                            target = section
                            break
                if target is None:
                    if controls_data:
                        target = controls_data[0]
                    else:
                        target = {
                            "id": new_id(),
                            "name": "General",
                            "controls": [],
                        }
                        controls_data.append(target)
                target.setdefault("controls", []).append(new_control)

            _set_controls_on_framework(fw, fv_idx, fv, controls_data)

        await _sync_extraction_result_controls(id, file_version, controls_data)
        return success(
            message="Control added successfully",
            data={
                "id": id,
                "fileVersion": file_version,
                "control": new_control,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("add_control error")
        return server_error(str(exc))


@router.post("/ai/jobs/{id}/approval-status")
async def update_approval_status(id: str, body: ApprovalStatusRequest):
    try:
        async with session_scope() as session:
            fw = await session.get(Framework, id)
            if not fw:
                return not_found(f"Framework not found: {id}")

            approval = dict(fw.approval or {})
            approval["status"] = body.status
            approval["date"] = body.timestamp or _iso()
            if body.reason:
                approval["remark"] = body.reason
            fw.approval = approval

            # Also stamp deployment_points status on current file version controls
            versions = list(fw.fileVersions or [])
            for i, fv in enumerate(versions):
                if not isinstance(fv, dict):
                    continue
                if str(fv.get("fileVersion")) != str(fw.currentFileVersion):
                    continue
                ai = dict(fv.get("aiExtraction") or {})
                controls_block = ai.get("controls") or {}
                controls_data = (
                    controls_block.get("controls_data")
                    if isinstance(controls_block, dict)
                    else controls_block
                ) or []
                dp_status = "approved" if body.status == "approved" else "rejected"
                for section in controls_data:
                    for control in section.get("controls") or []:
                        for dp in control.get("deployment_points") or []:
                            if isinstance(dp, dict):
                                dp["status"] = dp_status
                if isinstance(controls_block, dict):
                    controls_block["controls_data"] = controls_data
                    ai["controls"] = controls_block
                fv["aiExtraction"] = ai
                versions[i] = fv
            fw.fileVersions = versions

        return success(
            message="Approval status updated successfully",
            data={"id": id, "status": body.status},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("update_approval_status error")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# Framework-assignment paths used by deployment-framework-service
# ---------------------------------------------------------------------------


def _fa_file_version(fa: FrameworkAssignment, file_version: str) -> tuple[int | None, dict | None]:
    versions = list(fa.fileVersions or [])
    for i, fv in enumerate(versions):
        if isinstance(fv, dict) and str(fv.get("fileVersion")) == str(file_version):
            return i, dict(fv)
    return None, None


def _fa_sections(fv: dict) -> list:
    ai = fv.get("aiExtraction") or fv.get("aiUpload") or []
    if isinstance(ai, list):
        return ai
    if isinstance(ai, dict):
        return ai.get("controls_data") or ai.get("controls") or []
    return []


@router.patch("/framework-assignments/{id}/file-versions/{fileVersion}/controls/{controlId}/weightage")
async def update_fa_control_weightage(id: str, fileVersion: str, controlId: str, body: dict = Body(...)):
    try:
        weightage = body.get("weightage", {})
        if not isinstance(weightage, dict):
            return error("weightage must be a dict", 400)

        async with session_scope() as session:
            fa = await session.get(FrameworkAssignment, id)
            if not fa:
                return not_found(f"FrameworkAssignment not found: {id}")
            fv_idx, fv = _fa_file_version(fa, fileVersion)
            if fv is None or fv_idx is None:
                return not_found(f"File version not found: {fileVersion}")

            sections = _fa_sections(fv)
            found = False
            for section in sections:
                for control in section.get("controls") or []:
                    if str(control.get("id")) == str(controlId):
                        customization = dict(control.get("customization") or {})
                        customization["weightage"] = weightage
                        customization.setdefault("source", "system")
                        customization.setdefault("is_applicable", True)
                        control["customization"] = customization
                        found = True
                        break
                if found:
                    break
            if not found:
                return not_found(f"Control not found: {controlId}")

            versions = list(fa.fileVersions or [])
            fv["aiExtraction"] = sections
            versions[fv_idx] = fv
            fa.fileVersions = versions

        return success(
            message="Control weightage updated successfully",
            data={
                "assignmentId": id,
                "fileVersion": fileVersion,
                "controlId": controlId,
                "weightage": weightage,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("update_fa_control_weightage error")
        return server_error(str(exc))


@router.patch("/framework-assignments/{id}/finalize")
async def finalize_framework_assignment(id: str, body: dict = Body(default=None)):
    try:
        body = body or {}
        is_finalized = body.get("isFinalized", body.get("is_finalized", True))
        finalized_by = body.get("finalizedBy", body.get("finalized_by"))

        async with session_scope() as session:
            fa = await session.get(FrameworkAssignment, id)
            if not fa:
                return not_found(f"FrameworkAssignment not found: {id}")
            finalization = dict(fa.finalization or {})
            finalization["isFinalized"] = bool(is_finalized)
            finalization["finalizedBy"] = finalized_by
            finalization["finalizedAt"] = _iso()
            fa.finalization = finalization

        return success(
            message="Framework assignment finalized successfully",
            data={
                "assignmentId": id,
                "isFinalized": bool(is_finalized),
                "finalizedBy": finalized_by,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("finalize_framework_assignment error")
        return server_error(str(exc))


@router.patch("/framework-assignments/{id}/file-versions/{fileVersion}/controls/applicability")
async def update_fa_controls_applicability(id: str, fileVersion: str, body: dict = Body(...)):
    try:
        control_ids = body.get("controlIds") or []
        is_applicable = body.get("is_applicable", True)
        if not control_ids:
            return error("controlIds list is required", 400)
        if not isinstance(control_ids, list):
            control_ids = [control_ids]
        control_ids = [str(c) for c in control_ids]

        async with session_scope() as session:
            fa = await session.get(FrameworkAssignment, id)
            if not fa:
                return not_found(f"FrameworkAssignment not found: {id}")
            fv_idx, fv = _fa_file_version(fa, fileVersion)
            if fv is None or fv_idx is None:
                return not_found(f"File version not found: {fileVersion}")

            sections = _fa_sections(fv)
            updated = 0
            for section in sections:
                for control in section.get("controls") or []:
                    if str(control.get("id")) in control_ids:
                        customization = dict(control.get("customization") or {})
                        customization["is_applicable"] = bool(is_applicable)
                        customization.setdefault("source", "system")
                        customization.setdefault(
                            "weightage",
                            {"framework_weightage": 10, "customer_weightage": 10},
                        )
                        control["customization"] = customization
                        updated += 1
            if updated == 0:
                return not_found(f"No controls found in {control_ids}")

            versions = list(fa.fileVersions or [])
            fv["aiExtraction"] = sections
            versions[fv_idx] = fv
            fa.fileVersions = versions

        return success(
            message="Control applicability updated successfully",
            data={
                "assignmentId": id,
                "fileVersion": fileVersion,
                "updatedControls": control_ids,
                "is_applicable": bool(is_applicable),
                "updatedCount": updated,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("update_fa_controls_applicability error")
        return server_error(str(exc))
