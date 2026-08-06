"""Deployment gap runner — uses comparison results + controls; no RabbitMQ."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    ComparisonResult,
    DeploymentFramework,
    DeploymentGapJob,
    DeploymentGapResult,
    FrameworkAssignment,
    GapConfig,
    PackageComparison,
    PackageGapAnalysis,
    PackageMerge,
    PackageMergeTracking,
)

logger = logging.getLogger(__name__)



DEFAULT_STATUSES = {
    "implemented": "Implemented",
    "partially_implemented": "Partially Implemented",
    "not_implemented": "Not Implemented",
}

DEFAULT_THRESHOLDS = {
    "implemented": 75.0,
    "partially_implemented": 50.0,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()





async def _load_gap_config(session) -> tuple[dict[str, Any], dict[str, Any]]:
    statuses = dict(DEFAULT_STATUSES)
    thresholds = dict(DEFAULT_THRESHOLDS)
    rows = (
        (
            await session.execute(
                select(GapConfig).where(GapConfig.config_key.in_(["implementation_status", "thresholds"]))
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        if row.config_key == "implementation_status":
            statuses.update(row.config_value or {})
        elif row.config_key == "thresholds":
            thresholds.update(row.config_value or {})
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
    row = (
        (
            await session.execute(
                select(ComparisonResult)
                .where(
                    ComparisonResult.deployment_framework_id == df_id,
                    ComparisonResult.package_version == pkg_ver,
                )
                .order_by(ComparisonResult.createdAt.desc())
            )
        )
        .scalars()
        .first()
    )
    if row and isinstance(row.result, dict):
        grouped = row.result.get("grouped_results") or []
        if grouped:
            return grouped

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


async def run_gap(df_id: str, pkg_ver: str) -> None:
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()
    started = _utcnow()

    try:
        async with session_scope() as session:
            df = await session.get(DeploymentFramework, df_id)
            if not df:
                logger.error(f"DeploymentFramework not found with id: {df_id}")
                return

            fa_id = df.assignedFrameworkId or df.frameworkId
            if not fa_id:
                logger.error("No assignedFrameworkId or frameworkId found")
                return

            statuses, thresholds = await _load_gap_config(session)
            comparison_sections = await _load_comparison_grouped(session, df_id, pkg_ver)

            # If no comparison yet, try to synthesize from merge + assignment with score 0
            if not comparison_sections:
                track = (
                    await session.execute(
                        select(PackageMergeTracking).where(
                            PackageMergeTracking.deployment_framework_id == df_id,
                            PackageMergeTracking.package_version == pkg_ver,
                        )
                    )
                ).scalar_one_or_none()
                merge_controls = (track.data or {}).get("controls_data") if track else []
                if not merge_controls:
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

            job = DeploymentGapJob(
                id=new_id(),
                deployment_framework_id=df_id,
                package_version=pkg_ver,
                status="processing",
                data={"framework_assignment_id": str(fa_id)},
            )
            session.add(job)
            gap_job_id = job.id



        gap_results: list[dict[str, Any]] = []
        grouped_by_control: dict[str, list[dict[str, Any]]] = {}

        for section in comparison_sections:
            if not isinstance(section, dict):
                continue
            for item in section.get("controls") or []:
                if not isinstance(item, dict):
                    continue
                score = float(item.get("comparison_score") or 0)
                impl_status = _status_for_score(score, thresholds, statuses)
                assigned_id = str(
                    item.get("assigned_framework_control_id") or item.get("Framework_control_id") or "Unknown"
                )

                # One gap row per assigned deployment point (or one if none)
                assigned_dps = item.get("assigned_framework_deployment_points") or [
                    {"id": new_id(), "point": "General"}
                ]
                for dp in assigned_dps:
                    if not isinstance(dp, dict):
                        continue
                    gap_row = {
                        "assigned_framework_control_id": assigned_id,
                        "assigned_framework_control_name": item.get("assigned_framework_control_name") or "",
                        "assigned_framework_control_description": item.get(
                            "assigned_framework_control_description"
                        )
                        or "",
                        "assigned_framework_deployment_point_id": str(dp.get("id") or ""),
                        "assigned_framework_deployment_point": dp.get("point") or "",
                        "deployment_framework_control_id": item.get("deployment_framework_control_id") or "",
                        "deployment_framework_control_name": item.get("deployment_framework_control_name")
                        or "",
                        "comparison_score": score,
                        "implementation_status": impl_status,
                        "gap_score": round(max(0.0, 1.0 - (score if score <= 1 else score / 100)), 4),
                        "section_id": section.get("id"),
                        "section_name": section.get("name"),
                    }
                    gap_results.append(gap_row)
                    grouped_by_control.setdefault(assigned_id, []).append(gap_row)

        grouped_array = [{cid: points} for cid, points in grouped_by_control.items()]
        elapsed = (_utcnow() - started).total_seconds()

        async with session_scope() as session:
            result_row = DeploymentGapResult(
                id=new_id(),
                deployment_framework_id=df_id,
                package_version=pkg_ver,
                result={
                    "deployment_gap_id": gap_job_id,
                    "framework_assignment_id": str(fa_id),
                    "deployment_gap_results": gap_results,
                    "grouped_gap_results": grouped_array,
                    "gap_time_seconds": elapsed,
                    "statuses": statuses,
                    "thresholds": thresholds,
                },
            )
            session.add(result_row)

            gap_payload = {
                "status": "completed",
                "message": "Gap analysis completed",
                "timestamp": _iso(),
                "deployment_gap_results": gap_results,
            }
            pga = (
                await session.execute(
                    select(PackageGapAnalysis).where(PackageGapAnalysis.frameworkId == df_id)
                )
            ).scalar_one_or_none()
            if pga is None:
                pga = PackageGapAnalysis(
                    id=new_id(),
                    frameworkId=df_id,
                    fileHashes=[],
                    gapAnalysis=gap_payload,
                )
                session.add(pga)
            else:
                pga.gapAnalysis = gap_payload
                pga.updatedAt = _utcnow()

            job = await session.get(DeploymentGapJob, gap_job_id)
            if job:
                job.status = "completed"
                job.data = {
                    **(job.data or {}),
                    "deployment_gap_result_id": result_row.id,
                }

            df = await session.get(DeploymentFramework, df_id)
            if df:
                packages = list(df.packages or [])
                for i, pkg in enumerate(packages):
                    if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                        pkg = dict(pkg)
                        pkg["gapAnalysis"] = result_row.id
                        packages[i] = pkg
                        break
                df.packages = packages

    except Exception as exc:  # noqa: BLE001
        logger.exception("run_gap failed | df=%s pkg=%s", df_id, pkg_ver)
