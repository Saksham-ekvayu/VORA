"""Deployment-gap HTTP + WebSocket routes (Postgres, no RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.services.gap_runner import DEFAULT_STATUSES, DEFAULT_THRESHOLDS, run_gap
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import DeploymentGapJob, DeploymentGapResult, GapConfig, PackageGapAnalysis, FrameworkAssignment
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
    framework_assignment_id: str
    package_version: str


# ---------------------------------------------------------------------------
# POST /gap/start — Start gap analysis (background)
# ---------------------------------------------------------------------------


@router.post("/start")
async def start_gap_analysis(request: GapAnalysisRequest):
    """
    Start gap analysis between framework assignment and deployment framework package.
    Runs asynchronously in background.
    
    Args:
        framework_assignment_id: ID of the framework assignment
        package_version: Version of the package to analyze
    
    Returns:
        Gap analysis job details with status "processing"
    """
    try:
        framework_assignment_id = str(request.framework_assignment_id).strip()
        package_version = str(request.package_version).strip()

        if not framework_assignment_id or not package_version:
            return error("Invalid framework_assignment_id or package_version")

        logger.info(
            f"[GAP-START] Gap analysis requested | "
            f"fa_id={framework_assignment_id} | pkg_ver={package_version}"
        )

        # ===== VALIDATION 1: Check Framework Assignment exists =====
        logger.info("[GAP] Validation 1: Checking Framework Assignment...")
        async with session_scope() as session:
            fa = await session.get(FrameworkAssignment, framework_assignment_id)
            if not fa:
                logger.error(f"[GAP] ❌ Framework Assignment not found: {framework_assignment_id}")
                return not_found(f"Framework Assignment not found: {framework_assignment_id}")

            logger.info(f"[GAP] ✅ Framework Assignment found: {fa.frameworkName}")
            logger.info(f"    Framework ID: {fa.frameworkId}")
            logger.info(f"    Framework Version: {fa.frameworkVersion}")
            logger.info(f"    Status: {fa.status}")

        # ===== VALIDATION 2: Check Deployment Framework exists =====
        logger.info("[GAP] Validation 2: Checking Deployment Framework...")
        async with session_scope() as session:
            from vora_shared.models import DeploymentFramework
            
            # Get deployment framework from framework assignment
            df_id = fa.get("deploymentFrameworkId") if isinstance(fa.__dict__, dict) else None
            
            logger.info(f"[GAP] Deployment Framework ID: {df_id}")
            
            if df_id:
                df = await session.get(DeploymentFramework, df_id)
                if not df:
                    logger.error(f"[GAP] ❌ Deployment Framework not found: {df_id}")
                    return not_found(f"Deployment Framework not found: {df_id}")
                logger.info(f"[GAP] ✅ Deployment Framework found: {df.frameworkName}")
            else:
                logger.warning("[GAP] ⚠️ Deployment Framework ID not found in assignment")

        # ===== VALIDATION 3: Check Package version exists =====
        logger.info("[GAP] Validation 3: Checking Package version...")
        if not package_version or package_version.strip() == "":
            logger.error("[GAP] ❌ Invalid package version")
            return error("Package version cannot be empty")
        logger.info(f"[GAP] ✅ Package version valid: {package_version}")

        # ===== Create gap analysis record in database =====
        logger.info("[GAP] Creating gap analysis record...")
        gap_id = None
        async with session_scope() as session:
            gap_analysis = PackageGapAnalysis(
                id=new_id(),
                frameworkId=fa.frameworkId,
                fileHashes=[],
                gapAnalysis={
                    "status": "processing",
                    "message": "Gap analysis in progress",
                    "timestamp": _iso(),
                    "framework_assignment_id": framework_assignment_id,
                    "package_version": package_version,
                    "deployment_framework_id": fa.get("deploymentFrameworkId") if isinstance(fa.__dict__, dict) else None,
                },
            )
            session.add(gap_analysis)
            await session.flush()
            await session.commit()
            gap_id = gap_analysis.id
            logger.info(f"[GAP] ✅ Created gap analysis record | id={gap_id}")

        # ===== Queue gap analysis as background task =====
        logger.info("[GAP] Queueing background task...")
        task = asyncio.create_task(
            run_gap(framework_assignment_id, package_version, gap_id)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        logger.info("[GAP] ✅ Gap analysis task queued")

        return success(
            message="Gap analysis started successfully",
            data={
                "gap_id": gap_id,
                "framework_assignment_id": framework_assignment_id,
                "package_version": package_version,
                "status": "processing",
                "timestamp": _iso(),
            },
        )

    except Exception as exc:
        logger.exception(f"[GAP-START] ❌ Error: {exc}")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# GET /gap/{gap_id} — Get gap analysis result
# ---------------------------------------------------------------------------


@router.get("/{gap_id}")
async def get_gap_analysis(gap_id: str):
    """
    Get gap analysis result by ID.
    
    Args:
        gap_id: ID of the gap analysis
    
    Returns:
        Gap analysis data with results, status, and history
    """
    try:
        gap_id = str(gap_id).strip()
        if not gap_id:
            return error("Invalid gap_id")

        async with session_scope() as session:
            gap_analysis = await session.get(PackageGapAnalysis, gap_id)
            if not gap_analysis:
                return not_found(f"Gap analysis not found: {gap_id}")

            gap_data = gap_analysis.gapAnalysis or {}

            return success(
                message="Gap analysis retrieved successfully",
                data={
                    "id": gap_analysis.id,
                    "frameworkId": gap_analysis.frameworkId,
                    "status": gap_data.get("status", "pending"),
                    "message": gap_data.get("message"),
                    "timestamp": gap_data.get("timestamp"),
                    "framework_assignment_id": gap_data.get("framework_assignment_id"),
                    "package_version": gap_data.get("package_version"),
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
# GET /gap/list/all — List all gap analyses (paginated)
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
            total = (
                await session.execute(select(func.count()).select_from(PackageGapAnalysis))
            ).scalar_one()

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
                        "frameworkId": gap.frameworkId,
                        "status": gap_data.get("status", "pending"),
                        "framework_assignment_id": gap_data.get("framework_assignment_id"),
                        "package_version": gap_data.get("package_version"),
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


class StatusConfigUpdate(BaseModel):
    implemented: str
    partially_implemented: str
    not_implemented: str


class ThresholdConfigUpdate(BaseModel):
    implemented: float
    partially_implemented: float


async def _get_config(session, key: str) -> GapConfig | None:
    return (await session.execute(select(GapConfig).where(GapConfig.config_key == key))).scalar_one_or_none()


async def _upsert_config(session, key: str, value: dict[str, Any]) -> GapConfig:
    row = await _get_config(session, key)
    if row is None:
        row = GapConfig(id=new_id(), config_key=key, config_value=value)
        session.add(row)
    else:
        row.config_value = value
    return row


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
                await session.execute(select(func.count()).select_from(DeploymentGapResult))
            ).scalar_one()
            rows = (
                (
                    await session.execute(
                        select(DeploymentGapResult)
                        .order_by(DeploymentGapResult.createdAt.desc())
                        .offset((page - 1) * page_size)
                        .limit(page_size)
                    )
                )
                .scalars()
                .all()
            )
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
                (
                    await session.execute(
                        select(DeploymentGapResult).order_by(DeploymentGapResult.createdAt.desc())
                    )
                )
                .scalars()
                .all()
            )
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
                return not_found(f"Deployment gap results not found for: {deployment_gap_id}")

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
                (
                    await session.execute(
                        select(DeploymentGapResult).order_by(DeploymentGapResult.createdAt.desc())
                    )
                )
                .scalars()
                .all()
            )
            match: DeploymentGapResult | None = None
            for row in rows:
                if (
                    row.id == deployment_gap_id
                    or (row.result or {}).get("deployment_gap_id") == deployment_gap_id
                ):
                    match = row
                    break
            if not match:
                return not_found(f"Deployment gap results not found for: {deployment_gap_id}")

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
