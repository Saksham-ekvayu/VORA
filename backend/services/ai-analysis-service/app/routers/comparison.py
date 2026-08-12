"""Comparison service HTTP + WebSocket routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.services.comparison_runner import run_comparison
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import DeploymentFramework, FrameworkAssignment, PackageComparison
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

    deployment_framework_id: str
    package_version: str


# ---------------------------------------------------------------------------
# POST /comparison/start — Start comparison (background)
# ---------------------------------------------------------------------------


@router.post("/start")
async def start_comparison(request: ComparisonRequest):
    """
    Start comparison between deployment framework package and assigned framework.
    Flow: deployment_framework_id → resolve framework_assignment_id → start comparison

    Args:
        deployment_framework_id: ID of the deployment framework
        package_version: Version of the package to compare

    Returns:
        Comparison job with resolved framework_assignment_id, deployment_framework_id, package_version
    """
    try:
        deployment_framework_id = str(request.deployment_framework_id).strip()
        package_version = str(request.package_version).strip()

        if not deployment_framework_id or not package_version:
            logger.error("Invalid deployment_framework_id or package_version")
            return error("Invalid deployment_framework_id or package_version")

        logger.info("=" * 80)
        logger.info("[COMPARISON-START] New comparison request received")
        logger.info(f"  deployment_framework_id: {deployment_framework_id}")
        logger.info(f"  package_version: {package_version}")
        logger.info("=" * 80)

        # ===== VALIDATION 1: Check Deployment Framework exists =====
        logger.info("[COMPARISON] Validation 1: Checking Deployment Framework...")
        framework_assignment_id = None
        async with session_scope() as session:
            df = await session.get(DeploymentFramework, deployment_framework_id)
            if not df:
                logger.error(f"[COMPARISON] Deployment Framework not found: {deployment_framework_id}")
                return not_found(f"Deployment Framework not found: {deployment_framework_id}")

            framework_assignment_id = df.assignedFrameworkId
            logger.info(f"[COMPARISON] Deployment Framework found: {df.frameworkName}")
            logger.info(f"    Current Package Version: {df.currentPackageVersion}")
            logger.info(f"    Resolved Framework Assignment ID: {framework_assignment_id}")

        # ===== VALIDATION 2: Check Framework Assignment exists =====
        logger.info("[COMPARISON] Validation 2: Checking Framework Assignment...")
        async with session_scope() as session:
            fa = await session.get(FrameworkAssignment, framework_assignment_id)
            if not fa:
                logger.error(f"[COMPARISON] Framework Assignment not found: {framework_assignment_id}")
                return not_found(f"Framework Assignment not found: {framework_assignment_id}")

            logger.info(f"[COMPARISON] Framework Assignment found: {fa.frameworkName}")
            logger.info(f"    Framework ID: {fa.frameworkId}")
            logger.info(f"    Framework Version: {fa.frameworkVersion}")

        # ===== VALIDATION 3: Check Package version exists =====
        logger.info("[COMPARISON] Validation 3: Checking Package version...")
        if not package_version or package_version.strip() == "":
            logger.error("[COMPARISON] Invalid package version")
            return error("Package version cannot be empty")
        logger.info(f"[COMPARISON] Package version valid: {package_version}")

        # ===== Update or create comparison record in database =====
        logger.info("[COMPARISON] Updating/Creating comparison record...")
        comparison_id = None
        async with session_scope() as session:
            # First, try to find the existing comparison ID from the deployment framework packages
            df = await session.get(DeploymentFramework, deployment_framework_id)
            for pkg in df.packages:
                if pkg.get("packageVersion") == package_version:
                    comparison_id = pkg.get("comparison")
                    break

            if comparison_id:
                comparison = await session.get(PackageComparison, comparison_id)
                if comparison:
                    logger.info(f"[COMPARISON] Found existing comparison record: {comparison_id}")
                    # Ensure it has all the keys needed for processing status
                    comparison.comparison.update(
                        {
                            "status": "processing",
                            "message": "Comparison in progress",
                            "timestamp": _iso(),
                            "deployment_framework_id": deployment_framework_id,
                            "framework_assignment_id": framework_assignment_id,
                            "package_version": package_version,
                        }
                    )
                    from sqlalchemy.orm.attributes import flag_modified

                    flag_modified(comparison, "comparison")
                else:
                    comparison_id = None

            if not comparison_id:
                logger.info("[COMPARISON] Creating new comparison record...")
                comparison = PackageComparison(
                    id=new_id(),
                    fileHashes=[],
                    comparison={
                        "status": "processing",
                        "message": "Comparison in progress",
                        "timestamp": _iso(),
                        "deployment_framework_id": deployment_framework_id,
                        "framework_assignment_id": framework_assignment_id,
                        "package_version": package_version,
                    },
                )
                session.add(comparison)
                await session.flush()
                comparison_id = comparison.id

            await session.commit()
            logger.info(f"[COMPARISON] Comparison record ready | id={comparison_id}")

        # ===== Queue comparison as background task =====
        logger.info("[COMPARISON] Queueing background task...")
        task = asyncio.create_task(
            run_comparison(deployment_framework_id, package_version, framework_assignment_id, comparison_id)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        logger.info("[COMPARISON] Comparison task queued")

        return success(
            message="Comparison started successfully",
            data={
                "comparison_id": comparison_id,
                "deployment_framework_id": deployment_framework_id,
                "framework_assignment_id": framework_assignment_id,
                "package_version": package_version,
                "status": "processing",
                "timestamp": _iso(),
            },
        )

    except Exception as exc:
        logger.exception(f"[COMPARISON-START] Error: {exc}")
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
        Comparison data with results, status, and metadata
    """
    try:
        comparison_id = str(comparison_id).strip()
        if not comparison_id:
            return error("Invalid comparison_id")

        async with session_scope() as session:
            # Refresh from database to get latest data
            comparison = await session.get(PackageComparison, comparison_id)
            if not comparison:
                return not_found(f"Comparison not found: {comparison_id}")

            # Ensure we get fresh data
            await session.refresh(comparison)

            comp_data = comparison.comparison or {}

            return success(
                message="Comparison retrieved successfully",
                data={
                    "id": comparison.id,
                    "deployment_framework_id": comp_data.get("deployment_framework_id"),
                    "framework_assignment_id": comp_data.get("framework_assignment_id"),
                    "package_version": comp_data.get("package_version"),
                    "status": comp_data.get("status", "pending"),
                    "message": comp_data.get("message"),
                    "timestamp": comp_data.get("timestamp"),
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
# GET /comparison/list/all — List all comparisons (paginated)
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
            # Get fresh session without any cached objects
            total = (await session.execute(select(func.count()).select_from(PackageComparison))).scalar_one()

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
                        "deployment_framework_id": comp_data.get("deployment_framework_id"),
                        "framework_assignment_id": comp_data.get("framework_assignment_id"),
                        "package_version": comp_data.get("package_version"),
                        "status": comp_data.get("status", "pending"),
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
