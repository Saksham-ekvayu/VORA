"""Comparison service HTTP + WebSocket routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from app.services.comparison_runner import run_comparison
from fastapi import APIRouter
from sqlalchemy import select
from vora_shared.database import session_scope
from vora_shared.models import ComparisonResult
from vora_shared.responses import not_found, server_error, success

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
                stmt = stmt.where(ComparisonResult.deployment_framework_id == deployment_framework_id)
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


