"""Deployment-gap HTTP + WebSocket routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import func, select

from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import DeploymentGapJob, DeploymentGapResult, GapConfig
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import error, not_found, paginated, server_error, success

from app.services.gap_runner import DEFAULT_STATUSES, DEFAULT_THRESHOLDS, run_gap
from app.utils.ws_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["gap"])


class StatusConfigUpdate(BaseModel):
    implemented: str
    partially_implemented: str
    not_implemented: str


class ThresholdConfigUpdate(BaseModel):
    implemented: float
    partially_implemented: float


async def _get_config(session, key: str) -> GapConfig | None:
    return (
        await session.execute(select(GapConfig).where(GapConfig.config_key == key))
    ).scalar_one_or_none()


async def _upsert_config(session, key: str, value: dict[str, Any]) -> GapConfig:
    row = await _get_config(session, key)
    if row is None:
        row = GapConfig(id=new_id(), config_key=key, config_value=value)
        session.add(row)
    else:
        row.config_value = value
    return row


@router.get("/health")
async def health_check():
    return success(
        message="Service is healthy",
        data={"service": "deployment-gap-service", "status": "healthy"},
    )


@router.get("/status")
async def service_status():
    try:
        async with session_scope() as session:
            total_jobs = (
                await session.execute(select(func.count()).select_from(DeploymentGapJob))
            ).scalar_one()
        return success(
            message="Service status retrieved successfully",
            data={
                "service": "deployment-gap-service",
                "status": "running",
                "database": {"type": "PostgreSQL", "status": "connected"},
                "messaging": {"type": "none", "status": "disabled"},
                "statistics": {"total_jobs": total_jobs},
                "version": "1.0.0",
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("service_status error")
        return server_error(str(exc))


@router.get("/list")
async def list_deployment_gap_analyses(page: int = 1, page_size: int = 10):
    try:
        page = clamp_page(page)
        page_size = clamp_limit(page_size, default=10)
        async with session_scope() as session:
            total = (
                await session.execute(
                    select(func.count()).select_from(DeploymentGapResult)
                )
            ).scalar_one()
            rows = (
                await session.execute(
                    select(DeploymentGapResult)
                    .order_by(DeploymentGapResult.createdAt.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).scalars().all()
            items = []
            for row in rows:
                result = row.result or {}
                items.append(
                    {
                        "id": row.id,
                        "deployment_framework_id": row.deployment_framework_id,
                        "package_version": row.package_version,
                        "deployment_gap_id": result.get("deployment_gap_id"),
                        "gap_time_seconds": result.get("gap_time_seconds"),
                        "result_count": len(result.get("deployment_gap_results") or []),
                        "createdAt": row.createdAt.isoformat() if row.createdAt else None,
                    }
                )
            return paginated(
                data=items,
                pagination=build_pagination_meta(page, page_size, total),
                message=f"Retrieved {len(items)} gap analyses",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("list_deployment_gap_analyses error")
        return server_error(str(exc))


@router.get("/results/{deployment_gap_id}")
async def get_deployment_gap_results_by_id(deployment_gap_id: str):
    try:
        async with session_scope() as session:
            # Match by job id stored in result, or by result PK
            rows = (
                await session.execute(
                    select(DeploymentGapResult).order_by(DeploymentGapResult.createdAt.desc())
                )
            ).scalars().all()
            match: DeploymentGapResult | None = None
            for row in rows:
                if row.id == deployment_gap_id:
                    match = row
                    break
                if (row.result or {}).get("deployment_gap_id") == deployment_gap_id:
                    match = row
                    break
            if not match:
                job = await session.get(DeploymentGapJob, deployment_gap_id)
                if job:
                    for row in rows:
                        if (
                            row.deployment_framework_id == job.deployment_framework_id
                            and row.package_version == job.package_version
                        ):
                            match = row
                            break
            if not match:
                return not_found(
                    f"Deployment gap results not found for: {deployment_gap_id}"
                )

            result = match.result or {}
            grouped = result.get("grouped_gap_results")
            if not grouped:
                flat = result.get("deployment_gap_results") or []
                grouped_map: dict[str, list] = {}
                for item in flat:
                    cid = (
                        item.get("assigned_framework_control_id")
                        or item.get("Framework_control_id")
                        or "Unknown"
                    )
                    grouped_map.setdefault(cid, []).append(item)
                grouped = [{cid: pts} for cid, pts in grouped_map.items()]

            return success(
                message="Deployment gap results retrieved successfully (grouped by control)",
                data={
                    "id": match.id,
                    "deployment_gap_id": result.get("deployment_gap_id") or match.id,
                    "deployment_framework_id": match.deployment_framework_id,
                    "package_version": match.package_version,
                    "grouped_gap_results": grouped,
                    "deployment_gap_results": result.get("deployment_gap_results") or [],
                    "gap_time_seconds": result.get("gap_time_seconds"),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_deployment_gap_results_by_id error")
        return server_error(str(exc))


@router.get("/available-controls/{deployment_gap_id}")
async def get_available_controls_for_deployment_gap(deployment_gap_id: str):
    try:
        async with session_scope() as session:
            rows = (
                await session.execute(
                    select(DeploymentGapResult).order_by(DeploymentGapResult.createdAt.desc())
                )
            ).scalars().all()
            match: DeploymentGapResult | None = None
            for row in rows:
                if row.id == deployment_gap_id or (row.result or {}).get(
                    "deployment_gap_id"
                ) == deployment_gap_id:
                    match = row
                    break
            if not match:
                return not_found(
                    f"Deployment gap results not found for: {deployment_gap_id}"
                )

            flat = (match.result or {}).get("deployment_gap_results") or []
            controls = []
            seen = set()
            for item in flat:
                cid = item.get("assigned_framework_control_id")
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                controls.append(
                    {
                        "id": cid,
                        "name": item.get("assigned_framework_control_name"),
                        "description": item.get("assigned_framework_control_description"),
                        "implementation_status": item.get("implementation_status"),
                        "comparison_score": item.get("comparison_score"),
                    }
                )
            return success(
                message="Available controls retrieved successfully",
                data={
                    "deployment_gap_id": deployment_gap_id,
                    "controls": controls,
                    "total": len(controls),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_available_controls error")
        return server_error(str(exc))


@router.websocket("/ws/gap/{deployment_framework_id}/{package_version}")
async def ws_gap_auto(
    websocket: WebSocket, deployment_framework_id: str, package_version: str
):
    deployment_framework_id = deployment_framework_id.strip()
    package_version = package_version.strip()
    conn_key = f"gap:{deployment_framework_id}:{package_version}"
    await manager.connect(conn_key, websocket)

    async def send_cb(msg: dict[str, Any]) -> None:
        await manager.send_json(conn_key, msg)

    task = asyncio.create_task(run_gap(deployment_framework_id, package_version, send_cb))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(conn_key, websocket)
    except Exception as exc:  # noqa: BLE001
        logger.error("WS gap error | %s", exc, exc_info=True)
        await manager.disconnect(conn_key, websocket)
    finally:
        _ = task


# ---------------------------------------------------------------------------
# GapConfig CRUD — implementation-status + thresholds
# ---------------------------------------------------------------------------


@router.get("/config/implementation-status")
async def get_implementation_status_config():
    try:
        async with session_scope() as session:
            row = await _get_config(session, "implementation_status")
            if not row:
                return success(
                    message="Default implementation status config",
                    data={"source": "default", "statuses": DEFAULT_STATUSES},
                )
            return success(
                message="Implementation status config retrieved",
                data={"source": "postgres", "statuses": row.config_value},
            )
    except Exception as exc:  # noqa: BLE001
        return server_error(str(exc))


@router.post("/config/implementation-status")
async def create_implementation_status_config(body: StatusConfigUpdate):
    try:
        async with session_scope() as session:
            existing = await _get_config(session, "implementation_status")
            if existing:
                return error("Already exists. Use PUT to update.", 409)
            await _upsert_config(session, "implementation_status", body.model_dump())
        return success(
            message="Config created",
            data={"statuses": body.model_dump()},
        )
    except Exception as exc:  # noqa: BLE001
        return server_error(str(exc))


@router.put("/config/implementation-status")
async def update_implementation_status_config(body: StatusConfigUpdate):
    try:
        async with session_scope() as session:
            await _upsert_config(session, "implementation_status", body.model_dump())
        return success(
            message="Config updated",
            data={"statuses": body.model_dump()},
        )
    except Exception as exc:  # noqa: BLE001
        return server_error(str(exc))


@router.get("/config/thresholds")
async def get_threshold_config():
    try:
        async with session_scope() as session:
            row = await _get_config(session, "thresholds")
            if not row:
                return success(
                    message="Default threshold config",
                    data={"source": "default", "thresholds": DEFAULT_THRESHOLDS},
                )
            return success(
                message="Threshold config retrieved",
                data={"source": "postgres", "thresholds": row.config_value},
            )
    except Exception as exc:  # noqa: BLE001
        return server_error(str(exc))


@router.post("/config/thresholds")
async def create_threshold_config(body: ThresholdConfigUpdate):
    try:
        async with session_scope() as session:
            existing = await _get_config(session, "thresholds")
            if existing:
                return error("Already exists. Use PUT to update.", 409)
            await _upsert_config(session, "thresholds", body.model_dump())
        return success(
            message="Threshold config created",
            data={"thresholds": body.model_dump()},
        )
    except Exception as exc:  # noqa: BLE001
        return server_error(str(exc))


@router.put("/config/thresholds")
async def update_threshold_config(body: ThresholdConfigUpdate):
    try:
        async with session_scope() as session:
            await _upsert_config(session, "thresholds", body.model_dump())
        return success(
            message="Threshold config updated",
            data={"thresholds": body.model_dump()},
        )
    except Exception as exc:  # noqa: BLE001
        return server_error(str(exc))


@router.delete("/config/thresholds")
async def reset_threshold_config():
    try:
        async with session_scope() as session:
            row = await _get_config(session, "thresholds")
            if row:
                await session.delete(row)
        return success(
            message="Threshold config reset to defaults",
            data={"thresholds": DEFAULT_THRESHOLDS},
        )
    except Exception as exc:  # noqa: BLE001
        return server_error(str(exc))
