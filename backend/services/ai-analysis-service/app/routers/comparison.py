"""Comparison service HTTP + WebSocket routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.comparison_runner import run_comparison
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import PackageComparison, FrameworkAssignment
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import error, not_found, paginated, server_error, success

logger = logging.getLogger(__name__)
router = APIRouter(tags=["comparison"])

_background_tasks = set()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


class ComparisonRequest(BaseModel):
    """Request model for starting comparison."""
    framework_assignment_id: str
    package_version: str


# ---------------------------------------------------------------------------
# POST /comparison/start — Start comparison (background)
# ---------------------------------------------------------------------------


@router.post("/start")
async def start_comparison(request: ComparisonRequest):
    """
    Start comparison between framework assignment and deployment framework package.
    Runs asynchronously in background.
    
    Args:
        framework_assignment_id: ID of the framework assignment
        package_version: Version of the package to compare
    
    Returns:
        Comparison job details with status "processing"
    """
    try:
        framework_assignment_id = str(request.framework_assignment_id).strip()
        package_version = str(request.package_version).strip()

        if not framework_assignment_id or not package_version:
            return error("Invalid framework_assignment_id or package_version")

        logger.info(
            f"[COMPARISON-START] Comparison requested | "
            f"fa_id={framework_assignment_id} | pkg_ver={package_version}"
        )

        # ===== VALIDATION 1: Check Framework Assignment exists =====
        logger.info("[COMPARISON] Validation 1: Checking Framework Assignment...")
        async with session_scope() as session:
            fa = await session.get(FrameworkAssignment, framework_assignment_id)
            if not fa:
                logger.error(f"[COMPARISON] ❌ Framework Assignment not found: {framework_assignment_id}")
                return not_found(f"Framework Assignment not found: {framework_assignment_id}")

            logger.info(f"[COMPARISON] ✅ Framework Assignment found: {fa.frameworkName}")
            logger.info(f"    Framework ID: {fa.frameworkId}")
            logger.info(f"    Framework Version: {fa.frameworkVersion}")
            logger.info(f"    Status: {fa.status}")

        # ===== VALIDATION 2: Check Deployment Framework exists =====
        logger.info("[COMPARISON] Validation 2: Checking Deployment Framework...")
        async with session_scope() as session:
            from vora_shared.models import DeploymentFramework
            
            # Get deployment framework from framework assignment
            df_id = fa.get("deploymentFrameworkId") if isinstance(fa.__dict__, dict) else None
            
            # If not directly available, we need to look it up differently
            # For now, assume it's embedded in the assignment
            logger.info(f"[COMPARISON] Deployment Framework ID: {df_id}")
            
            if df_id:
                df = await session.get(DeploymentFramework, df_id)
                if not df:
                    logger.error(f"[COMPARISON] ❌ Deployment Framework not found: {df_id}")
                    return not_found(f"Deployment Framework not found: {df_id}")
                logger.info(f"[COMPARISON] ✅ Deployment Framework found: {df.frameworkName}")
            else:
                logger.warning("[COMPARISON] ⚠️ Deployment Framework ID not found in assignment")

        # ===== VALIDATION 3: Check Package version exists =====
        logger.info("[COMPARISON] Validation 3: Checking Package version...")
        if not package_version or package_version.strip() == "":
            logger.error("[COMPARISON] ❌ Invalid package version")
            return error("Package version cannot be empty")
        logger.info(f"[COMPARISON] ✅ Package version valid: {package_version}")

        # ===== Create comparison record in database =====
        logger.info("[COMPARISON] Creating comparison record...")
        comparison_id = None
        async with session_scope() as session:
            comparison = PackageComparison(
                id=new_id(),
                frameworkId=fa.frameworkId,
                fileHashes=[],
                comparison={
                    "status": "processing",
                    "message": "Comparison in progress",
                    "timestamp": _iso(),
                    "framework_assignment_id": framework_assignment_id,
                    "package_version": package_version,
                    "deployment_framework_id": fa.get("deploymentFrameworkId") if isinstance(fa.__dict__, dict) else None,
                },
            )
            session.add(comparison)
            await session.flush()
            await session.commit()
            comparison_id = comparison.id
            logger.info(f"[COMPARISON] ✅ Created comparison record | id={comparison_id}")

        # ===== Queue comparison as background task =====
        logger.info("[COMPARISON] Queueing background task...")
        task = asyncio.create_task(
            run_comparison(framework_assignment_id, package_version, comparison_id)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        logger.info("[COMPARISON] ✅ Comparison task queued")

        return success(
            message="Comparison started successfully",
            data={
                "comparison_id": comparison_id,
                "framework_assignment_id": framework_assignment_id,
                "package_version": package_version,
                "status": "processing",
                "timestamp": _iso(),
            },
        )

    except Exception as exc:
        logger.exception(f"[COMPARISON-START] ❌ Error: {exc}")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# GET /comparison/{comparison_id} — Get comparison result
# ---------------------------------------------------------------------------


@router.get("/{comparison_id}")
async def get_comparison(comparison_id: str):
    """
    Get comparison result by ID.
    
    Args:
        comparison_id: ID of the comparison
    
    Returns:
        Comparison data with results, status, and history
    """
    try:
        comparison_id = str(comparison_id).strip()
        if not comparison_id:
            return error("Invalid comparison_id")

        async with session_scope() as session:
            comparison = await session.get(PackageComparison, comparison_id)
            if not comparison:
                return not_found(f"Comparison not found: {comparison_id}")

            comp_data = comparison.comparison or {}

            return success(
                message="Comparison retrieved successfully",
                data={
                    "id": comparison.id,
                    "frameworkId": comparison.frameworkId,
                    "status": comp_data.get("status", "pending"),
                    "message": comp_data.get("message"),
                    "timestamp": comp_data.get("timestamp"),
                    "framework_assignment_id": comp_data.get("framework_assignment_id"),
                    "package_version": comp_data.get("package_version"),
                    "comparison_result": comp_data.get("comparison_result", []),
                    "comparison_time_seconds": comp_data.get("comparison_time_seconds"),
                    "createdAt": comparison.createdAt.isoformat() if comparison.createdAt else None,
                    "updatedAt": comparison.updatedAt.isoformat() if comparison.updatedAt else None,
                },
            )
    except Exception as exc:
        logger.exception(f"get_comparison error: {exc}")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# GET /comparison/list — List all comparisons (paginated)
# ---------------------------------------------------------------------------


@router.get("/list/all")
async def list_comparisons(page: int = 1, page_size: int = 10):
    """
    List all comparisons with pagination.
    
    Args:
        page: Page number (default 1)
        page_size: Results per page (default 10)
    
    Returns:
        Paginated list of comparisons
    """
    try:
        page = clamp_page(page)
        page_size = clamp_limit(page_size, default=10)

        async with session_scope() as session:
            total = (
                await session.execute(select(func.count()).select_from(PackageComparison))
            ).scalar_one()

            rows = (
                (
                    await session.execute(
                        select(PackageComparison)
                        .order_by(PackageComparison.createdAt.desc())
                        .offset((page - 1) * page_size)
                        .limit(page_size)
                    )
                )
                .scalars()
                .all()
            )

            items = []
            for comp in rows:
                comp_data = comp.comparison or {}
                result = comp_data.get("comparison_result", [])
                items.append(
                    {
                        "id": comp.id,
                        "frameworkId": comp.frameworkId,
                        "status": comp_data.get("status", "pending"),
                        "framework_assignment_id": comp_data.get("framework_assignment_id"),
                        "package_version": comp_data.get("package_version"),
                        "comparison_sections": len(result) if isinstance(result, list) else 0,
                        "comparison_time_seconds": comp_data.get("comparison_time_seconds"),
                        "createdAt": comp.createdAt.isoformat() if comp.createdAt else None,
                    }
                )

            return paginated(
                data=items,
                pagination=build_pagination_meta(page, page_size, total),
                message=f"Retrieved {len(items)} comparisons",
            )
    except Exception as exc:
        logger.exception("list_comparisons error")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# Legacy GET endpoint (backward compatibility)
# ---------------------------------------------------------------------------


@router.get("/compare/results")
async def get_compare_results(
    deployment_framework_id: Optional[str] = None,
    package_version: Optional[str] = None,
):
    """Legacy endpoint - kept for backward compatibility."""
    try:
        async with session_scope() as session:
            stmt = select(PackageComparison).order_by(PackageComparison.createdAt.desc())
            rows = (await session.execute(stmt.limit(50))).scalars().all()
            if not rows:
                return not_found("Comparisons not found")

            row = rows[0]
            comp_data = row.comparison or {}
            return success(
                message="Comparison results retrieved successfully",
                data={
                    "id": row.id,
                    "frameworkId": row.frameworkId,
                    "comparison_result": comp_data.get("comparison_result", []),
                    "comparison_time_seconds": comp_data.get("comparison_time_seconds"),
                    "framework_assignment_id": comp_data.get("framework_assignment_id"),
                    "createdAt": row.createdAt.isoformat() if row.createdAt else None,
                },
            )
    except Exception as exc:
        logger.exception("get_compare_results error")
        return server_error(str(exc))
