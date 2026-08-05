"""Comparison service HTTP + WebSocket routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from vora_shared.database import session_scope
from vora_shared.models import ComparisonResult
from vora_shared.responses import success, not_found, server_error

from app.services.comparison_runner import run_comparison
from app.utils.ws_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["comparison"])


@router.get("/health")
async def health_check():
    return success(
        message="Service is healthy",
        data={"service": "comparison-service", "status": "healthy"},
    )


@router.get("/compare/results")
async def get_compare_results(
    deployment_framework_id: Optional[str] = None,
    package_version: Optional[str] = None,
):
    try:
        async with session_scope() as session:
            stmt = select(ComparisonResult).order_by(ComparisonResult.createdAt.desc())
            if deployment_framework_id:
                stmt = stmt.where(
                    ComparisonResult.deployment_framework_id == deployment_framework_id
                )
            if package_version:
                stmt = stmt.where(ComparisonResult.package_version == package_version)
            rows = (await session.execute(stmt.limit(50))).scalars().all()
            if not rows:
                return not_found("Comparison results not found")

            # Prefer latest matching row
            row = rows[0]
            result = row.result or {}
            return success(
                message="Comparison results retrieved successfully",
                data={
                    "id": row.id,
                    "deployment_framework_id": row.deployment_framework_id,
                    "package_version": row.package_version,
                    "comparison_result": result.get("grouped_results") or [],
                    "comparison_time_seconds": result.get("comparison_time_seconds"),
                    "framework_assignment_id": result.get("framework_assignment_id"),
                    "createdAt": row.createdAt.isoformat() if row.createdAt else None,
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_compare_results error")
        return server_error(str(exc))


@router.websocket("/ws/comparison/{deployment_framework_id}/{package_version}")
async def ws_comparison_auto(
    websocket: WebSocket, deployment_framework_id: str, package_version: str
):
    deployment_framework_id = deployment_framework_id.strip()
    package_version = package_version.strip()
    conn_key = f"comparison:{deployment_framework_id}:{package_version}"
    await manager.connect(conn_key, websocket)

    async def send_cb(msg: dict[str, Any]) -> None:
        await manager.send_json(conn_key, msg)

    task = asyncio.create_task(
        run_comparison(deployment_framework_id, package_version, send_cb)
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(conn_key, websocket)
    except Exception as exc:  # noqa: BLE001
        logger.error("WS comparison error | %s", exc, exc_info=True)
        await manager.disconnect(conn_key, websocket)
    finally:
        _ = task


@router.websocket(
    "/ws/comparison/{deployment_framework_id}/{package_version}/{framework_assignment_id}"
)
async def ws_comparison_with_assignment(
    websocket: WebSocket,
    deployment_framework_id: str,
    package_version: str,
    framework_assignment_id: str,
):
    deployment_framework_id = deployment_framework_id.strip()
    package_version = package_version.strip()
    framework_assignment_id = framework_assignment_id.strip()
    conn_key = (
        f"comparison:{deployment_framework_id}:{package_version}:{framework_assignment_id}"
    )
    await manager.connect(conn_key, websocket)

    async def send_cb(msg: dict[str, Any]) -> None:
        await manager.send_json(conn_key, msg)

    task = asyncio.create_task(
        run_comparison(
            deployment_framework_id,
            package_version,
            send_cb,
            framework_assignment_id=framework_assignment_id,
        )
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(conn_key, websocket)
    except Exception as exc:  # noqa: BLE001
        logger.error("WS comparison(assignment) error | %s", exc, exc_info=True)
        await manager.disconnect(conn_key, websocket)
    finally:
        _ = task
