"""Deployment gap runner — uses comparison results + controls; no RabbitMQ."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    DeploymentFramework,
    FrameworkAssignment,
    GapThresholdConfig,
    PackageComparison,
    PackageGapAnalysis,
    PackageMerge,
)

logger = logging.getLogger(__name__)


DEFAULT_STATUSES = {
    "implemented": "Implemented",
    "partially_implemented": "Partially Implemented",
    "not_implemented": "Not Implemented",
}

# Default thresholds - will be overridden by config if available
_DEFAULT_THRESHOLDS = {
    "implemented": 75.0,
    "partially_implemented": 50.0,
}


def _get_thresholds() -> dict[str, float]:
    """Get thresholds from config or use defaults."""
    try:
        from vora_shared.config import get_settings
        settings = get_settings()
        return {
            "implemented": settings.similarity_threshold_high,
            "partially_implemented": settings.similarity_threshold_medium,
        }
    except Exception:
        return dict(_DEFAULT_THRESHOLDS)


DEFAULT_THRESHOLDS = _get_thresholds()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


async def _load_gap_config(session) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load gap analysis configuration from database or use defaults."""
    statuses = dict(DEFAULT_STATUSES)
    thresholds = dict(DEFAULT_THRESHOLDS)
    
    # Try to load from new GapThresholdConfig table first
    config = (
        await session.execute(
            select(GapThresholdConfig).where(GapThresholdConfig.is_active)
        )
    ).scalar_one_or_none()
    
    if config:
        # Update thresholds and labels from database
        thresholds = {
            "implemented": config.implemented_threshold,
            "partially_implemented": config.partially_implemented_threshold,
        }
        statuses = {
            "implemented": config.implemented_label,
            "partially_implemented": config.partially_implemented_label,
            "not_implemented": config.not_implemented_label,
        }
        logger.info(f"[GAP-CONFIG] Loaded thresholds: high={config.implemented_threshold}, medium={config.partially_implemented_threshold}")
    
    return statuses, thresholds


def _status_for_score(score: float, thresholds: dict[str, Any], statuses: dict[str, Any]) -> str:
    implemented_t = float(thresholds.get("implemented", 75.0))
    partial_t = float(thresholds.get("partially_implemented", 50.0))
    # Scores from comparison are 0..1; accept either 0..1 or 0..100
    pct = score * 100 if score <= 1.0 else score
    if pct >= implemented_t:
        return statuses.get("implemented", "Implemented")
    if pct >= partial_t:
        return statuses.get("partially_implemented", "Partially Implemented")
    return statuses.get("not_implemented", "Not Implemented")


async def _load_comparison_grouped(session, df_id: str, pkg_ver: str) -> list[dict[str, Any]]:
    # Load comparison results from PackageComparison table
    pc = (
        await session.execute(select(PackageComparison).where(PackageComparison.frameworkId == df_id))
    ).scalar_one_or_none()
    if pc and isinstance(pc.comparison, dict):
        result = pc.comparison.get("comparison_result") or []
        if result:
            return result

    pc = (
        await session.execute(select(PackageComparison).where(PackageComparison.frameworkId == df_id))
    ).scalar_one_or_none()
    if pc and isinstance(pc.comparison, dict):
        return pc.comparison.get("comparison_result") or []
    return []


async def _load_assignment_controls(session, assignment_id: str) -> list[dict[str, Any]]:
    fa = await session.get(FrameworkAssignment, str(assignment_id))
    if not fa:
        return []
    for fv in fa.fileVersions or []:
        if not isinstance(fv, dict):
            continue
        ai = fv.get("aiExtraction") or fv.get("aiUpload")
        if isinstance(ai, list) and ai:
            return ai
        if isinstance(ai, dict):
            return ai.get("controls_data") or ai.get("controls") or []
    return []


async def run_gap(df_id: str, pkg_ver: str, framework_assignment_id: str | None = None, gap_id: str | None = None) -> None:
    """
    Run gap analysis processing.
    
    Args:
        df_id: Deployment framework ID
        pkg_ver: Package version
        framework_assignment_id: Framework assignment ID
        gap_id: The specific PackageGapAnalysis record ID created by POST endpoint
    """
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()
    gap_id = str(gap_id).strip() if gap_id else None
    started = _utcnow()

    logger.info("=" * 80)
    logger.info(f"[GAP-RUNNER] Starting gap analysis processing")
    logger.info(f"  Deployment Framework ID: {df_id}")
    logger.info(f"  Package Version: {pkg_ver}")
    logger.info(f"  Framework Assignment ID: {framework_assignment_id}")
    logger.info("=" * 80)

    try:
        async with session_scope() as session:
            logger.info("[GAP-RUNNER] Loading deployment framework...")
            df = await session.get(DeploymentFramework, df_id)
            if not df:
                logger.error(f"DeploymentFramework not found with id: {df_id}")
                return

            fa_id = framework_assignment_id or df.assignedFrameworkId or df.frameworkId
            if not fa_id:
                logger.error("No assignedFrameworkId or frameworkId found")
                return
            
            logger.info(f"[GAP-RUNNER] ✅ Resolved framework_assignment_id: {fa_id}")
            logger.info("[GAP-RUNNER] Loading gap configuration...")

            statuses, thresholds = await _load_gap_config(session)
            logger.info(f"[GAP-RUNNER] Loading comparison results...")
            comparison_sections = await _load_comparison_grouped(session, df_id, pkg_ver)
            logger.info(f"[GAP-RUNNER] ✅ Loaded {len(comparison_sections)} comparison sections")

            # If no comparison yet, try to synthesize from merge + assignment with score 0
            if not comparison_sections:
                merge_controls = []
                pm = (
                    await session.execute(select(PackageMerge).where(PackageMerge.frameworkId == df_id))
                ).scalar_one_or_none()
                if pm and isinstance(pm.mergeExtraction, dict):
                    merge_controls = pm.mergeExtraction.get("controls_data") or []

                assignment_sections = await _load_assignment_controls(session, str(fa_id))
                if not assignment_sections and not merge_controls:
                    logger.error("No comparison results or controls available for gap analysis")
                    return

                # Build minimal comparison-like structure from assignment controls
                comparison_sections = []
                for section in assignment_sections or []:
                    if not isinstance(section, dict):
                        continue
                    items = []
                    for ctrl in section.get("controls") or []:
                        if not isinstance(ctrl, dict):
                            continue
                        items.append(
                            {
                                "assigned_framework_control_id": str(ctrl.get("id") or ""),
                                "assigned_framework_control_name": ctrl.get("name") or "",
                                "assigned_framework_control_description": ctrl.get("description") or "",
                                "assigned_framework_deployment_points": [
                                    {
                                        "id": str(dp.get("id") or new_id()),
                                        "point": dp.get("name") or "",
                                    }
                                    for dp in (ctrl.get("deployment_points") or [])
                                    if isinstance(dp, dict)
                                ],
                                "deployment_framework_control_id": "",
                                "deployment_framework_control_name": "",
                                "deployment_framework_control_description": "",
                                "deployment_framework_deployment_points": [],
                                "comparison_score": 0.0,
                            }
                        )
                    comparison_sections.append(
                        {
                            "id": section.get("id") or new_id(),
                            "name": section.get("name") or "Section",
                            "controls": items,
                        }
                    )

        logger.info("[GAP-RUNNER] Processing comparison sections for gap analysis...")
        logger.info("[GAP-RUNNER] Running DP-to-DP semantic similarity comparison...")
        
        gap_results: list[dict[str, Any]] = []
        grouped_by_control: dict[str, list[dict[str, Any]]] = {}

        for section in comparison_sections:
            if not isinstance(section, dict):
                continue
            section_id = section.get("id") or ""
            section_name = section.get("name") or ""
            
            for item in section.get("controls") or []:
                if not isinstance(item, dict):
                    continue
                
                assigned_id = str(
                    item.get("assigned_framework_control_id") or item.get("Framework_control_id") or "Unknown"
                )
                assigned_name = item.get("assigned_framework_control_name") or ""
                assigned_desc = item.get("assigned_framework_control_description") or ""
                df_control_id = item.get("deployment_framework_control_id") or ""
                df_control_name = item.get("deployment_framework_control_name") or ""

                # Get deployment points from both frameworks
                assigned_dps = item.get("assigned_framework_deployment_points") or [
                    {"id": new_id(), "point": "General"}
                ]
                deployment_dps = item.get("deployment_framework_deployment_points") or [
                    {"id": new_id(), "point": "General"}
                ]
                
                logger.info(f"[GAP-RUNNER] DP comparison for control: {assigned_name}")
                logger.info(f"  Assigned DPs: {len(assigned_dps)}, Deployment DPs: {len(deployment_dps)}")

                # DP-to-DP comparison: for each assigned DP, find best match in deployment DPs using semantic similarity
                for af_dp in assigned_dps:
                    if not isinstance(af_dp, dict):
                        continue
                    
                    af_dp_id = str(af_dp.get("id") or "")
                    af_dp_text = af_dp.get("point") or ""

                    best_dp_score = 0.0
                    best_df_dp_id = ""
                    best_df_dp_text = ""

                    # Find best matching deployment point for this assigned DP using semantic similarity
                    for df_dp in deployment_dps:
                        if not isinstance(df_dp, dict):
                            continue
                        
                        df_dp_id = str(df_dp.get("id") or "")
                        df_dp_text = df_dp.get("point") or ""
                        
                        # Score this DP pair using semantic similarity (0-100)
                        if af_dp_text and df_dp_text:
                            from app.services.comparison_runner import _similarity
                            # _similarity returns 0-1, convert to 0-100 for threshold comparison
                            dp_similarity = _similarity(af_dp_text, df_dp_text)
                            dp_score = dp_similarity * 100 if dp_similarity <= 1.0 else dp_similarity
                        else:
                            dp_score = 0.0
                        
                        if dp_score > best_dp_score:
                            best_dp_score = dp_score
                            best_df_dp_id = df_dp_id
                            best_df_dp_text = df_dp_text

                    # Determine implementation status based on DP-level semantic score
                    impl_status = _status_for_score(best_dp_score / 100.0, thresholds, statuses)
                    
                    gap_row = {
                        "assigned_framework_control_id": assigned_id,
                        "assigned_framework_control_name": assigned_name,
                        "assigned_framework_control_description": assigned_desc,
                        "assigned_framework_section_id": section_id,
                        "assigned_framework_section_name": section_name,
                        "assigned_framework_deployment_point_id": af_dp_id,
                        "assigned_framework_deployment_point": af_dp_text,
                        "deployment_framework_control_id": df_control_id,
                        "deployment_framework_control_name": df_control_name,
                        "deployment_framework_deployment_point_id": best_df_dp_id,
                        "deployment_framework_deployment_point": best_df_dp_text,
                        "comparison_score": float(item.get("comparison_score") or 0),
                        "deployment_point_similarity_score": round(best_dp_score, 2),
                        "implementation_status": impl_status,
                        "gap_score": round(max(0.0, 100.0 - best_dp_score) / 100.0, 4),
                    }
                    gap_results.append(gap_row)
                    grouped_by_control.setdefault(assigned_id, []).append(gap_row)
        
        logger.info(f"[GAP-RUNNER] ✅ Completed DP-to-DP comparisons: {len(gap_results)} deployment point gaps")

        grouped_array = [{cid: points} for cid, points in grouped_by_control.items()]
        elapsed = (_utcnow() - started).total_seconds()

        async with session_scope() as session:
            logger.info("[GAP-RUNNER] Saving gap analysis result...")
            
            logger.info("[GAP-RUNNER] Updating PackageGapAnalysis record...")
            gap_payload = {
                "status": "completed",
                "message": "Gap analysis completed",
                "timestamp": _iso(),
                "deployment_gap_results": gap_results,
                "deployment_framework_id": df_id,
                "framework_assignment_id": str(fa_id),
                "package_version": pkg_ver,
            }
            
            # Use the gap_id passed from POST endpoint to update the specific record
            pga = None
            if gap_id:
                pga = await session.get(PackageGapAnalysis, gap_id)
                if pga:
                    logger.info("[GAP-RUNNER] ✅ Found PackageGapAnalysis by gap_id, updating")
                    pga.gapAnalysis = gap_payload
                    pga.updatedAt = _utcnow()
                    session.add(pga)
                else:
                    logger.warning(f"[GAP-RUNNER] ⚠️ PackageGapAnalysis with gap_id={gap_id} not found")
            
            # Fallback: query by frameworkId if gap_id not provided or not found
            if not pga:
                pga = (
                    await session.execute(
                        select(PackageGapAnalysis).where(PackageGapAnalysis.frameworkId == df_id)
                    )
                ).scalar_one_or_none()
                if pga:
                    logger.info("[GAP-RUNNER] ✅ Found PackageGapAnalysis by frameworkId, updating")
                    pga.gapAnalysis = gap_payload
                    pga.updatedAt = _utcnow()
                    session.add(pga)
            
            # Last resort: create new if still not found
            if not pga:
                logger.warning("[GAP-RUNNER] ⚠️ No PackageGapAnalysis found, creating new")
                pga = PackageGapAnalysis(
                    id=new_id(),
                    frameworkId=df_id,
                    fileHashes=[],
                    gapAnalysis=gap_payload,
                )
                session.add(pga)
            
            await session.flush()
            logger.info(f"[GAP-RUNNER] ✅ Updated PackageGapAnalysis: {pga.id}")

            logger.info(f"[GAP-RUNNER] Updating deployment framework packages...")
            df = await session.get(DeploymentFramework, df_id)
            if df:
                packages = list(df.packages or [])
                for i, pkg in enumerate(packages):
                    if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                        pkg = dict(pkg)
                        pkg["gapAnalysis"] = pga.id
                        packages[i] = pkg
                        break
                df.packages = packages
                session.add(df)
                await session.flush()
                logger.info(f"[GAP-RUNNER] ✅ Updated deployment framework packages")

            # Commit all changes
            logger.info(f"[GAP-RUNNER] Committing all changes to database...")
            await session.commit()
            logger.info(f"[GAP-RUNNER] ✅ All changes committed successfully")
            
            # Fresh query from database to verify update
            logger.info(f"[GAP-RUNNER] Verifying update - fresh query from database...")
            verified_pga = await session.get(PackageGapAnalysis, pga.id)
            if verified_pga and verified_pga.gapAnalysis:
                status_in_db = verified_pga.gapAnalysis.get('status', 'unknown')
                results_count = len(verified_pga.gapAnalysis.get('deployment_gap_results', []))
                logger.info(f"[GAP-RUNNER] ✅ Verified in database:")
                logger.info(f"  Status: {status_in_db}")
                logger.info(f"  Results count: {results_count}")
            else:
                logger.warning(f"[GAP-RUNNER] ⚠️ Could not verify - record not found after commit")

            logger.info(f"{'='*80}")
            logger.info(f"[GAP-RUNNER-SUCCESS] ✅ Gap analysis complete!")
            logger.info(f"  Deployment Framework ID: {df_id}")
            logger.info(f"  Package Version: {pkg_ver}")
            logger.info(f"  Framework Assignment ID: {fa_id}")
            logger.info(f"  Total Gap Results: {len(gap_results)}")
            logger.info(f"  Processing Time: {elapsed:.2f}s")
            logger.info(f"[GAP-RUNNER-SAVED] ✅ Data saved to: PackageGapAnalysis table")
            logger.info(f"{'='*80}")

    except Exception as exc:  # noqa: BLE001
        logger.error(f"{'='*80}")
        logger.error(f"[GAP-RUNNER-ERROR] ❌ run_gap failed!")
        logger.error(f"  Deployment Framework ID: {df_id}")
        logger.error(f"  Package Version: {pkg_ver}")
        logger.error(f"  Error: {str(exc)}")
        logger.error(f"{'='*80}")
        logger.exception("run_gap exception traceback:")
