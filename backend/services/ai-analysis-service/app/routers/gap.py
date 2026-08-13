"""Gap Analysis service HTTP routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.services.gap_runner import run_gap
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import DeploymentFramework, FrameworkAssignment, PackageGapAnalysis
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import error, not_found, paginated, server_error, success

logger = logging.getLogger(__name__)
router = APIRouter(tags=["gap"])

_background_tasks = set()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


class GapAnalysisRequest(BaseModel):
    """Request model for starting gap analysis."""

    deployment_framework_id: str
    package_version: str


# ---------------------------------------------------------------------------
# POST /deployment-gap/start — Start gap analysis (background)
# ---------------------------------------------------------------------------


@router.post("/start")
async def start_gap_analysis(request: GapAnalysisRequest):
    """
    Start gap analysis between deployment framework package and assigned framework.
    Flow: deployment_framework_id → resolve framework_assignment_id → start analysis

    Args:
        deployment_framework_id: ID of the deployment framework
        package_version: Version of the package to analyze

    Returns:
        Gap analysis job with resolved framework_assignment_id, deployment_framework_id, package_version
    """
    try:
        deployment_framework_id = str(request.deployment_framework_id).strip()
        package_version = str(request.package_version).strip()

        if not deployment_framework_id or not package_version:
            return error("Invalid deployment_framework_id or package_version")

        logger.info(
            f"[GAP-START] Gap analysis requested | "
            f"df_id={deployment_framework_id} | pkg_ver={package_version}"
        )

        # ===== VALIDATION 1: Check Deployment Framework exists =====
        logger.info("[GAP] Validation 1: Checking Deployment Framework...")
        framework_assignment_id = None
        async with session_scope() as session:
            df = await session.get(DeploymentFramework, deployment_framework_id)
            if not df:
                logger.error(f"[GAP] Deployment Framework not found: {deployment_framework_id}")
                return not_found(f"Deployment Framework not found: {deployment_framework_id}")

            framework_assignment_id = df.assignedFrameworkId
            gap_id = None
            for pkg in df.packages:
                if pkg.get("packageVersion") == package_version:
                    gap_id = pkg.get("gapAnalysis")
                    break
            logger.info(f"[GAP] Deployment Framework found: {df.frameworkName}")
            logger.info(f"    Current Package Version: {df.currentPackageVersion}")
            logger.info(f"    Resolved Framework Assignment ID: {framework_assignment_id}")

        # ===== VALIDATION 2: Check Framework Assignment exists =====
        logger.info("[GAP] Validation 2: Checking Framework Assignment...")
        async with session_scope() as session:
            fa = await session.get(FrameworkAssignment, framework_assignment_id)
            if not fa:
                logger.error(f"[GAP] Framework Assignment not found: {framework_assignment_id}")
                return not_found(f"Framework Assignment not found: {framework_assignment_id}")

            logger.info(f"[GAP] Framework Assignment found: {fa.frameworkName}")
            logger.info(f"    Framework ID: {fa.frameworkId}")
            logger.info(f"    Framework Version: {fa.frameworkVersion}")

        # ===== VALIDATION 3: Check Package version exists =====
        logger.info("[GAP] Validation 3: Checking Package version...")
        if not package_version or package_version.strip() == "":
            logger.error("[GAP] Invalid package version")
            return error("Package version cannot be empty")
        logger.info(f"[GAP] Package version valid: {package_version}")

        # ===== Create or update gap analysis record in database =====
        logger.info("[GAP] Creating or updating gap analysis record...")
        async with session_scope() as session:
            if gap_id:
                gap_analysis = await session.get(PackageGapAnalysis, gap_id)
                if gap_analysis:
                    logger.info(f"[GAP] Found existing gap analysis record: {gap_id}")
                    gap_analysis.gapAnalysis.update(
                        {
                            "status": "processing",
                            "message": "Gap analysis in progress",
                            "timestamp": _iso(),
                            "deployment_framework_id": deployment_framework_id,
                            "framework_assignment_id": framework_assignment_id,
                            "package_version": package_version,
                        }
                    )
                    from sqlalchemy.orm.attributes import flag_modified

                    flag_modified(gap_analysis, "gapAnalysis")
                else:
                    gap_id = None

            if not gap_id:
                gap_analysis = PackageGapAnalysis(
                    id=new_id(),
                    fileHashes=[],
                    gapAnalysis={
                        "status": "processing",
                        "message": "Gap analysis in progress",
                        "timestamp": _iso(),
                        "deployment_framework_id": deployment_framework_id,
                        "framework_assignment_id": framework_assignment_id,
                        "package_version": package_version,
                    },
                )
                session.add(gap_analysis)
            await session.flush()
            await session.commit()
            gap_id = gap_analysis.id
            logger.info(f"[GAP] Created gap analysis record | id={gap_id}")

        # ===== Queue gap analysis as background task =====
        logger.info("[GAP] Queueing background task...")
        task = asyncio.create_task(
            run_gap(deployment_framework_id, package_version, framework_assignment_id, gap_id)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        logger.info("[GAP] Gap analysis task queued")

        return success(
            message="Gap analysis started successfully",
            data={
                "gap_id": gap_id,
                "deployment_framework_id": deployment_framework_id,
                "framework_assignment_id": framework_assignment_id,
                "package_version": package_version,
                "status": "processing",
                "timestamp": _iso(),
            },
        )

    except Exception as exc:
        logger.exception(f"[GAP-START] Error: {exc}")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# GET /deployment-gap/{gap_id} — Get gap analysis result
# ---------------------------------------------------------------------------


@router.get("/{gap_id}")
async def get_gap_analysis(gap_id: str):
    """
    Get gap analysis result by ID.

    Args:
        gap_id: ID of the gap analysis

    Returns:
        Gap analysis data with results, status, and metadata
    """
    try:
        gap_id = str(gap_id).strip()
        if not gap_id:
            return error("Invalid gap_id")

        async with session_scope() as session:
            # Refresh from database to get latest data
            gap_analysis = await session.get(PackageGapAnalysis, gap_id)
            if not gap_analysis:
                return not_found(f"Gap analysis not found: {gap_id}")

            # Ensure we get fresh data
            await session.refresh(gap_analysis)

            gap_data = gap_analysis.gapAnalysis or {}

            return success(
                message="Gap analysis retrieved successfully",
                data={
                    "id": gap_analysis.id,
                    "deployment_framework_id": gap_data.get("deployment_framework_id"),
                    "framework_assignment_id": gap_data.get("framework_assignment_id"),
                    "package_version": gap_data.get("package_version"),
                    "status": gap_data.get("status", "pending"),
                    "message": gap_data.get("message"),
                    "timestamp": gap_data.get("timestamp"),
                    "deployment_gap_results": gap_data.get("deployment_gap_results", []),
                    "gap_time_seconds": gap_data.get("gap_time_seconds"),
                    "createdAt": gap_analysis.createdAt.isoformat() if gap_analysis.createdAt else None,
                    "updatedAt": gap_analysis.updatedAt.isoformat() if gap_analysis.updatedAt else None,
                },
            )
    except Exception as exc:
        logger.exception(f"get_gap_analysis error: {exc}")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# GET /deployment-gap/list/all — List all gap analyses (paginated)
# ---------------------------------------------------------------------------


@router.get("/list/all")
async def list_gap_analyses(page: int = 1, page_size: int = 10):
    """
    List all gap analyses with pagination.

    Args:
        page: Page number (default 1)
        page_size: Results per page (default 10)

    Returns:
        Paginated list of gap analyses
    """
    try:
        page = clamp_page(page)
        page_size = clamp_limit(page_size, default=10)

        async with session_scope() as session:
            # Get fresh session without any cached objects
            total = (await session.execute(select(func.count()).select_from(PackageGapAnalysis))).scalar_one()

            rows = (
                (
                    await session.execute(
                        select(PackageGapAnalysis)
                        .order_by(PackageGapAnalysis.createdAt.desc())
                        .offset((page - 1) * page_size)
                        .limit(page_size)
                    )
                )
                .scalars()
                .all()
            )

            items = []
            for gap in rows:
                gap_data = gap.gapAnalysis or {}
                results = gap_data.get("deployment_gap_results", [])
                items.append(
                    {
                        "id": gap.id,
                        "deployment_framework_id": gap_data.get("deployment_framework_id"),
                        "framework_assignment_id": gap_data.get("framework_assignment_id"),
                        "package_version": gap_data.get("package_version"),
                        "status": gap_data.get("status", "pending"),
                        "gap_results_count": len(results) if isinstance(results, list) else 0,
                        "gap_time_seconds": gap_data.get("gap_time_seconds"),
                        "createdAt": gap.createdAt.isoformat() if gap.createdAt else None,
                    }
                )

            return paginated(
                data=items,
                pagination=build_pagination_meta(page, page_size, total),
                message=f"Retrieved {len(items)} gap analyses",
            )
    except Exception as exc:
        logger.exception("list_gap_analyses error")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# DELETE /deployment-gap/{gap_id} — Delete gap analysis
# ---------------------------------------------------------------------------


@router.delete("/{gap_id}")
async def delete_gap_analysis(gap_id: str):
    """
    Delete a gap analysis record by ID.

    Args:
        gap_id: ID of the gap analysis to delete

    Returns:
        Success message
    """
    try:
        gap_id = str(gap_id).strip()
        if not gap_id:
            return error("Invalid gap_id")

        logger.info(f"[GAP-DELETE] Deleting gap analysis | id={gap_id}")

        async with session_scope() as session:
            gap_analysis = await session.get(PackageGapAnalysis, gap_id)
            if not gap_analysis:
                logger.warning(f"[GAP-DELETE] Gap analysis not found: {gap_id}")
                return not_found(f"Gap analysis not found: {gap_id}")

            gap_data = gap_analysis.gapAnalysis or {}
            df_id = gap_data.get("deployment_framework_id")
            pkg_ver = gap_data.get("package_version")

            await session.delete(gap_analysis)
            await session.commit()

            logger.info(f"[GAP-DELETE] ✅ Deleted successfully")
            logger.info(f"  Deployment Framework ID: {df_id}")
            logger.info(f"  Package Version: {pkg_ver}")

            return success(
                message="Gap analysis deleted successfully",
                data={
                    "id": gap_id,
                    "deployment_framework_id": df_id,
                    "package_version": pkg_ver,
                },
            )
    except Exception as exc:
        logger.exception(f"delete_gap_analysis error: {exc}")
        return server_error(str(exc))
