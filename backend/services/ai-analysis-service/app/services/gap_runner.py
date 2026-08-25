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
    DeploymentPackageMerge,
    FrameworkAssignment,
    GapThresholdConfig,
    PackageComparison,
    PackageGapAnalysis,
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
        await session.execute(select(GapThresholdConfig).where(GapThresholdConfig.is_active))
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
        logger.info(
            f"[GAP-CONFIG] Loaded thresholds: high={config.implemented_threshold}, medium={config.partially_implemented_threshold}"
        )

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


async def _load_comparison_grouped(session, df: DeploymentFramework, pkg_ver: str) -> list[dict[str, Any]]:
    # Load comparison results from PackageComparison table
    comparison_id = None
    for pkg in df.packages or []:
        if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
            comparison_id = pkg.get("comparison")
            break

    if not comparison_id:
        return []

    pc = await session.get(PackageComparison, str(comparison_id))
    if pc and isinstance(pc.comparison, dict):
        result = pc.comparison.get("comparison_result") or []
        if result:
            return result
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


async def _fetch_from_package_merge(session, merge_doc_id: str) -> list[dict[str, Any]]:
    if not merge_doc_id:
        return []
    logger.info(f"[GAP-RUNNER] Trying to load from DeploymentPackageMerge: {merge_doc_id}")
    pm = await session.get(DeploymentPackageMerge, merge_doc_id)
    if pm and isinstance(pm.controls, dict):
        controls = pm.controls.get("controls_data") or []
        logger.info(f"[GAP-RUNNER]  Loaded {len(controls)} sections from DeploymentPackageMerge")
        return controls
    logger.warning(f"[GAP-RUNNER]   DeploymentPackageMerge not found or invalid: {merge_doc_id}")
    return []


async def _load_merged_controls(session, df: DeploymentFramework, pkg_ver: str) -> list[dict[str, Any]]:
    merge_doc_id = None
    merged_controls_from_pkg = []

    for pkg in df.packages or []:
        if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
            merge_doc_id = pkg.get("mergeDocument")
            merged_pkg_controls = pkg.get("mergedControls")
            if isinstance(merged_pkg_controls, dict):
                merged_controls_from_pkg = merged_pkg_controls.get("controls_data") or []
                logger.info(
                    f"[GAP-RUNNER]  Loaded {len(merged_controls_from_pkg)} sections from package.mergedControls"
                )
            else:
                logger.info(
                    f"[GAP-RUNNER]   No mergedControls in package (type: {type(merged_pkg_controls)})"
                )
            break

    if not merged_controls_from_pkg:
        merged_controls_from_pkg = await _fetch_from_package_merge(session, merge_doc_id)

    return merged_controls_from_pkg


def _extract_controls_from_section(section: dict) -> list[dict]:
    controls = []
    if isinstance(section, dict):
        for ctrl in section.get("controls") or []:
            if isinstance(ctrl, dict):
                controls.append(ctrl)
    return controls


def _build_merged_control_map(merge_controls: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged_control_map = {}
    for section in merge_controls:
        for ctrl in _extract_controls_from_section(section):
            ctrl_name = (ctrl.get("name") or "").strip().lower()
            if ctrl_name:
                dps_count = len(ctrl.get("deployment_points") or [])
                merged_control_map[ctrl_name] = ctrl
                logger.info(f"[GAP-RUNNER] 📌 Indexed control '{ctrl_name}' with {dps_count} DPs")
    return merged_control_map


def _process_assignment_control_for_synthesis(ctrl: dict, merged_control_map: dict) -> dict | None:
    if not isinstance(ctrl, dict):
        return None

    df_control_id = ""
    df_control_name = ""
    df_control_description = ""
    merged_dps = []  # ✅ Initialize as empty list
    
    ctrl_name_lower = (ctrl.get("name") or "").strip().lower()
    if ctrl_name_lower in merged_control_map:
        matched_merged = merged_control_map[ctrl_name_lower]
        df_control_id = str(matched_merged.get("id") or "")
        df_control_name = matched_merged.get("name") or ""
        df_control_description = matched_merged.get("description") or ""
        raw_dps = matched_merged.get("deployment_points") or []
        merged_dps = [
            {"id": str(dp.get("id") or new_id()), "point": dp.get("name") or ""}
            for dp in raw_dps
            if isinstance(dp, dict)
        ]
        logger.info(f"[GAP-RUNNER]  Matched '{ctrl_name_lower}': {len(merged_dps)} DPs")
        for dp in merged_dps:
            logger.info(f"              └─ {dp['point']}")
    else:
        logger.info(f"[GAP-RUNNER]   No match for '{ctrl_name_lower}'")

    return {
        "assigned_framework_control_id": str(ctrl.get("id") or ""),
        "assigned_framework_control_name": ctrl.get("name") or "",
        "assigned_framework_control_description": ctrl.get("description") or "",
        "assigned_framework_deployment_points": [
            {"id": str(dp.get("id") or new_id()), "point": dp.get("name") or ""}
            for dp in (ctrl.get("deployment_points") or [])
            if isinstance(dp, dict)
        ],
        "deployment_framework_control_id": df_control_id,
        "deployment_framework_control_name": df_control_name,
        "deployment_framework_control_description": df_control_description,
        "deployment_framework_deployment_points": merged_dps,
        "comparison_score": 1.0 if df_control_id else 0.0,
    }


async def _synthesize_comparison_sections(
    session, df: DeploymentFramework, pkg_ver: str, assignment_sections: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merge_controls = await _load_merged_controls(session, df, pkg_ver)
    logger.info(f"[GAP-RUNNER] Total merged controls loaded: {len(merge_controls)}")

    if not assignment_sections and not merge_controls:
        return []

    merged_control_map = _build_merged_control_map(merge_controls)
    logger.info(f"[GAP-RUNNER]  Built index of {len(merged_control_map)} merged controls")

    comparison_sections = []
    for section in assignment_sections or []:
        if not isinstance(section, dict):
            continue

        items = []
        for ctrl in section.get("controls") or []:
            customization = ctrl.get("customization") or {}
            if not customization.get("is_applicable", True):
                continue
            
            processed = _process_assignment_control_for_synthesis(ctrl, merged_control_map)
            if processed:
                items.append(processed)

        comparison_sections.append(
            {
                "id": section.get("id") or new_id(),
                "name": section.get("name") or "Section",
                "controls": items,
            }
        )
    return comparison_sections


def _find_best_dp_match(af_dp_text: str, deployment_dps: list[dict[str, Any]]) -> tuple[float, str, str]:
    """Find best DP match using batch encoding."""
    best_df_dp_id = ""
    best_df_dp_text = ""

    if not af_dp_text or not deployment_dps:
        return 0.0, "", ""

    from app.services.comparison_runner import _batch_encode, _batch_similarity

    # Extract all DP texts
    dp_texts = [dp.get("point") or "" for dp in deployment_dps if isinstance(dp, dict)]
    if not dp_texts:
        return 0.0, "", ""

    # Batch encode all DPs at once
    af_emb = _batch_encode([af_dp_text])[0]
    dp_embeddings = _batch_encode(dp_texts)

    # Find best match
    dp_score, best_idx = _batch_similarity(af_emb, dp_embeddings)
    dp_score_pct = dp_score * 100 if dp_score <= 1.0 else dp_score

    if best_idx >= 0 and best_idx < len(deployment_dps):
        best_df_dp_id = str(deployment_dps[best_idx].get("id") or "")
        best_df_dp_text = deployment_dps[best_idx].get("point") or ""

    return dp_score_pct, best_df_dp_id, best_df_dp_text


def _process_control_item(
    item: dict, section_id: str, section_name: str, thresholds: dict, statuses: dict
) -> list[dict]:
    assigned_id = str(
        item.get("assigned_framework_control_id") or item.get("Framework_control_id") or "Unknown"
    )
    assigned_name = item.get("assigned_framework_control_name") or ""
    assigned_desc = item.get("assigned_framework_control_description") or ""
    df_control_id = item.get("deployment_framework_control_id") or ""
    df_control_name = item.get("deployment_framework_control_name") or ""

    assigned_dps = item.get("assigned_framework_deployment_points") or [{"id": new_id(), "point": "General"}]
    deployment_dps = item.get("deployment_framework_deployment_points") or [
        {"id": new_id(), "point": "General"}
    ]

    logger.info(f"[GAP-RUNNER] DP comparison for control: {assigned_name}")
    logger.info(f"  Assigned DPs: {len(assigned_dps)}, Deployment DPs: {len(deployment_dps)}")

    results = []
    for af_dp in assigned_dps:
        if not isinstance(af_dp, dict):
            continue

        af_dp_id = str(af_dp.get("id") or "")
        af_dp_text = af_dp.get("point") or ""
        best_dp_score, best_df_dp_id, best_df_dp_text = _find_best_dp_match(af_dp_text, deployment_dps)

        impl_status = _status_for_score(best_dp_score / 100.0, thresholds, statuses)

        results.append(
            {
                "assigned_framework_control_id": assigned_id,
                "assigned_framework_control_name": assigned_name,
                "assigned_framework_control_description": assigned_desc,
                "assigned_framework_section_id": section_id,
                "assigned_framework_section_name": section_name,
                "assigned_framework_deployment_points": {"id": af_dp_id, "point": af_dp_text},
                "deployment_framework_control_id": df_control_id,
                "deployment_framework_control_name": df_control_name,
                "deployment_framework_deployment_points": {"id": best_df_dp_id, "point": best_df_dp_text},
                "comparison_score": float(item.get("comparison_score") or 0),
                "similarity_score": round(best_dp_score, 2),
                "implementation_status": impl_status,
                "gap_score": round(max(0.0, 100.0 - best_dp_score) / 100.0, 4),
                "reviewComment": "",
            }
        )
    return results


def _calculate_gap_results(
    comparison_sections: list[dict[str, Any]], thresholds: dict[str, Any], statuses: dict[str, Any]
) -> list[dict[str, Any]]:
    """Calculate gap results with DP-to-DP semantic similarity comparison."""
    logger.info("[GAP-RUNNER] Processing comparison sections for gap analysis...")
    logger.info("[GAP-RUNNER] Running DP-to-DP semantic similarity comparison...")

    gap_results = []

    for section in comparison_sections:
        if not isinstance(section, dict):
            continue
        section_id = section.get("id") or ""
        section_name = section.get("name") or ""

        for item in section.get("controls") or []:
            if not isinstance(item, dict):
                continue

            item_results = _process_control_item(item, section_id, section_name, thresholds, statuses)
            for row in item_results:
                gap_results.append(row)

    logger.info(f"[GAP-RUNNER] Completed DP-to-DP comparisons: {len(gap_results)} deployment point gaps")
    return gap_results


async def _save_gap_analysis_result(
    session, df_id: str, fa_id: str, pkg_ver: str, gap_id: str | None, gap_results: list[dict[str, Any]]
) -> PackageGapAnalysis:
    logger.info("[GAP-RUNNER] Saving gap analysis result...")
    gap_payload = {
        "status": "completed",
        "message": "Gap analysis completed",
        "timestamp": _iso(),
        "deployment_gap_results": gap_results,
        "deployment_framework_id": df_id,
        "framework_assignment_id": str(fa_id),
        "package_version": pkg_ver,
    }

    pga = None
    if gap_id:
        pga = await session.get(PackageGapAnalysis, gap_id)
        if pga:
            logger.info("[GAP-RUNNER] Found PackageGapAnalysis by gap_id, updating")
            pga.gapAnalysis = gap_payload
            pga.updatedAt = _utcnow()
            session.add(pga)
        else:
            logger.warning(f"[GAP-RUNNER] PackageGapAnalysis with gap_id={gap_id} not found")

    if not pga:
        logger.warning("[GAP-RUNNER] No PackageGapAnalysis found, creating new")
        pga = PackageGapAnalysis(id=new_id(), fileHashes=[], gapAnalysis=gap_payload)
        session.add(pga)

    await session.flush()
    logger.info(f"[GAP-RUNNER] Updated PackageGapAnalysis: {pga.id}")

    logger.info("[GAP-RUNNER] Updating deployment framework packages...")
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
        logger.info("[GAP-RUNNER] Updated deployment framework packages")
    return pga


async def _save_failure_status(gap_id: str | None, exc: Exception):
    try:
        async with session_scope() as session:
            if gap_id:
                pga = await session.get(PackageGapAnalysis, str(gap_id))
                if pga:
                    pga.gapAnalysis = {
                        "status": "failed",
                        "message": f"Gap analysis failed: {str(exc)}",
                        "timestamp": _iso(),
                        "deployment_gap_results": [],
                    }
                    session.add(pga)
                    await session.commit()
    except Exception as db_exc:
        logger.exception(f"[GAP-RUNNER-ERROR] Failed to update failure status: {db_exc}")


async def run_gap(
    df_id: str, pkg_ver: str, framework_assignment_id: str | None = None, gap_id: str | None = None
) -> None:
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
    logger.info("[GAP-RUNNER] Starting gap analysis processing")
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

            logger.info(f"[GAP-RUNNER] Resolved framework_assignment_id: {fa_id}")
            logger.info("[GAP-RUNNER] Loading gap configuration...")
            statuses, thresholds = await _load_gap_config(session)

            logger.info("[GAP-RUNNER] Loading comparison results...")
            comparison_sections = await _load_comparison_grouped(session, df, pkg_ver)
            logger.info(f"[GAP-RUNNER] Loaded {len(comparison_sections)} comparison sections")

            if not comparison_sections:
                logger.info("[GAP-RUNNER] Synthesizing comparison sections from latest merge...")
                assignment_sections = await _load_assignment_controls(session, str(fa_id))
                comparison_sections = await _synthesize_comparison_sections(
                    session, df, pkg_ver, assignment_sections
                )
                if not comparison_sections:
                    logger.error("No comparison results or controls available for gap analysis")
                    return

            logger.info("[GAP-RUNNER] Starting DP-to-DP matching (offloading to thread pool)...")
            # Offload CPU-intensive DP matching to thread pool to avoid blocking event loop
            gap_results = await asyncio.to_thread(_calculate_gap_results, comparison_sections, thresholds, statuses)

            pga = await _save_gap_analysis_result(session, df_id, str(fa_id), pkg_ver, gap_id, gap_results)

            logger.info("[GAP-RUNNER] Committing all changes to database...")
            await session.commit()
            logger.info("[GAP-RUNNER] All changes committed successfully")

            logger.info("[GAP-RUNNER] Verifying update - fresh query from database...")
            verified_pga = await session.get(PackageGapAnalysis, pga.id)
            if verified_pga and verified_pga.gapAnalysis:
                status_in_db = verified_pga.gapAnalysis.get("status", "unknown")
                results_count = len(verified_pga.gapAnalysis.get("deployment_gap_results", []))
                logger.info("[GAP-RUNNER] Verified in database:")
                logger.info(f"  Status: {status_in_db}")
                logger.info(f"  Results count: {results_count}")
            else:
                logger.warning("[GAP-RUNNER] Could not verify - record not found after commit")

            elapsed = (_utcnow() - started).total_seconds()
            logger.info(f"{'='*80}")
            logger.info("[GAP-RUNNER-SUCCESS] Gap analysis complete!")
            logger.info(f"  Deployment Framework ID: {df_id}")
            logger.info(f"  Package Version: {pkg_ver}")
            logger.info(f"  Framework Assignment ID: {fa_id}")
            logger.info(f"  Total Gap Results: {len(gap_results)}")
            logger.info(f"  Processing Time: {elapsed:.2f}s")
            logger.info("[GAP-RUNNER-SAVED] Data saved to: PackageGapAnalysis table")
            logger.info(f"{'='*80}")

    except Exception as exc:  # noqa: BLE001
        logger.error(f"{'='*80}")
        logger.error("[GAP-RUNNER-ERROR] run_gap failed!")
        logger.error(f"  Deployment Framework ID: {df_id}")
        logger.error(f"  Package Version: {pkg_ver}")
        logger.exception(f"  Error: {str(exc)}")
        logger.error(f"{'='*80}")
        logger.exception("run_gap exception traceback:")
        await _save_failure_status(gap_id, exc)
