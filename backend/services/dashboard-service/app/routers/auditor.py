import logging
from typing import Annotated

from app.helpers import (
    build_overall_protection_rows,
    filter_and_sort_rows,
    get_live_packages,
    get_nested,
    process_gap_analyses,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from vora_shared.config import get_settings
from vora_shared.database import session_scope
from vora_shared.models import (
    DeploymentFramework,
    DeploymentPackageMerge,
    EvidenceOutput,
    FrameworkAssignment,
    PackageGapAnalysis,
)
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import paginated, server_error, success
from vora_shared.security import RequestContext, get_context

router = APIRouter(tags=["auditor-dashboard"])
logger = logging.getLogger(__name__)


def _iter_evidence_records(ev: EvidenceOutput):
    """Yield records from an evidence output."""
    out = ev.output or {}
    fw_name = get_nested(out, "frameworkName")
    fw_version = get_nested(out, "frameworkVersion") or get_nested(out, "currentFileVersion") or ""

    for fv in get_nested(out, "fileVersions") or []:
        for cdata in (get_nested(fv, "data") or {}).values():
            for rec in get_nested(cdata, "records") or []:
                yield fw_name, fw_version, rec


def _format_stream_record(ev: EvidenceOutput, fw_name: str, fw_version: str, rec: dict) -> dict:
    """Format a single audit stream record."""
    status_str = get_nested(rec, "compliance_status", "").lower()

    status = "warn"
    if "not compliant" in status_str:
        status = "fail"
    elif "compliant" in status_str:
        status = "pass"

    desc = get_nested(rec, "deployment_point", "")

    llm_analysis = get_nested(rec, "llm_analysis") or {}
    reason = get_nested(llm_analysis, "reason", "")
    confidence = get_nested(llm_analysis, "confidence", "")

    return {
        "id": get_nested(rec, "file_id", str(ev.id)),
        "dp_id": get_nested(rec, "dp_id", ""),
        "status": status,
        "framework": fw_name,
        "version": fw_version,
        "description": desc,
        "reason": reason,
        "confidence": confidence,
        "timestamp": ev.createdAt.isoformat() if ev.createdAt else None,
    }


def _process_live_streams(evidence_outputs: list[EvidenceOutput]) -> list[dict]:
    """Extract and format recent live audit streams."""
    live_streams = []
    for ev in evidence_outputs:
        for fw_name, fw_version, rec in _iter_evidence_records(ev):
            live_streams.append(_format_stream_record(ev, fw_name, fw_version, rec))
    return live_streams


def _process_ai_insights(evidence_outputs: list[EvidenceOutput]) -> list[dict]:
    """Extract AI insights based on LLM recommendations in evidence outputs."""
    insights = []
    for ev in evidence_outputs:
        for fw_name, fw_version, rec in _iter_evidence_records(ev):
            llm_analysis = get_nested(rec, "llm_analysis") or {}
            recommendation = get_nested(llm_analysis, "recommendation")
            if recommendation:
                confidence = str(get_nested(llm_analysis, "confidence") or "").title()
                priority = confidence if confidence in ["High", "Medium", "Low"] else "Low"
                insights.append({"text": recommendation, "priority": priority})
    return insights


def _get_dp_count_for_merge(pm: DeploymentPackageMerge) -> int:
    controls = pm.controls or {}
    controls_data = get_nested(controls, "controls_data") or []
    dp_count = 0
    for section in controls_data:
        for control in get_nested(section, "controls") or []:
            dp_count += len(get_nested(control, "deployment_points") or [])
    return dp_count


def _process_deployment_points(
    merges: list[DeploymentPackageMerge], live_packages: list[dict]
) -> list[dict]:
    """Aggregate configured deployment points per framework."""
    deployment_points = []
    for pm in merges:
        dp_count = _get_dp_count_for_merge(pm)

        fw_name = "Unknown Framework"
        fw_version = ""
        for lp in live_packages:
            if str(get_nested(lp["pkg"], "mergeDocument")) == str(pm.id):
                fw_name = lp["df"].frameworkName or fw_name
                fw_version = lp["df"].frameworkVersion or ""
                break

        deployment_points.append({"name": fw_name, "version": fw_version, "count": dp_count})
    return deployment_points


@router.get("/analytics")
async def get_auditor_dashboard_analytics(
    ctx: Annotated[RequestContext, Depends(get_context)],
):
    try:
        tenant_id = ctx.tenant_id

        async with session_scope() as session:
            dfs = list(
                (
                    await session.execute(
                        select(DeploymentFramework).where(DeploymentFramework.tenantId == tenant_id)
                    )
                )
                .scalars()
                .all()
            )

            live_packages, gap_analysis_ids, merge_doc_ids = get_live_packages(dfs)

            gap_analyses = (
                list(
                    (
                        await session.execute(
                            select(PackageGapAnalysis).where(
                                PackageGapAnalysis.id.in_(gap_analysis_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                if gap_analysis_ids
                else []
            )

            merges = (
                list(
                    (
                        await session.execute(
                            select(DeploymentPackageMerge).where(
                                DeploymentPackageMerge.id.in_(merge_doc_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                if merge_doc_ids
                else []
            )

            assignment_ids = [
                get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
                for ga in gap_analyses
                if get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
            ]

            assignments = (
                list(
                    (
                        await session.execute(
                            select(FrameworkAssignment).where(
                                FrameworkAssignment.id.in_(assignment_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                if assignment_ids
                else []
            )

            evidence_outputs = list(
                (
                    await session.execute(
                        select(EvidenceOutput).order_by(desc(EvidenceOutput.createdAt))
                    )
                )
                .scalars()
                .all()
            )

            historical_gap_analysis_ids = [
                get_nested(pkg, "gapAnalysis")
                for df in dfs
                for pkg in (df.packages or [])
                if get_nested(pkg, "gapAnalysis")
            ]

            historical_gap_analyses = (
                list(
                    (
                        await session.execute(
                            select(PackageGapAnalysis)
                            .where(PackageGapAnalysis.id.in_(historical_gap_analysis_ids))
                            .order_by(desc(PackageGapAnalysis.createdAt))
                        )
                    )
                    .scalars()
                    .all()
                )
                if historical_gap_analysis_ids
                else []
            )

            (
                total_controls_overall,
                passing_controls_overall,
                extra_controls_overall,
                critical_gaps,
                active_gaps,
                framework_health,
                total_dps_overall,
                implemented_dps_overall,
                _, # Ignore prev_implemented_dps_overall
            ) = process_gap_analyses(
                gap_analyses, live_packages, historical_gap_analyses, merges, assignments
            )
            overall_protection = (
                round((implemented_dps_overall / total_dps_overall) * 100)
                if total_dps_overall > 0
                else 0
            )

            live_streams = _process_live_streams(evidence_outputs)
            ai_insights = _process_ai_insights(evidence_outputs)
            deployment_points = _process_deployment_points(merges, live_packages)

            response_data = {
                "overallProtection": overall_protection,
                "criticalGaps": critical_gaps,
                "controlPassing": f"{passing_controls_overall}/{total_controls_overall}",
                "extraControls": extra_controls_overall,
                "frameworkHealth": framework_health,
                "activeGaps": active_gaps,
                "liveAuditStreams": live_streams,
                "deploymentPoints": deployment_points,
                "aiInsights": ai_insights,
            }

            return success(
                response_data, message="Auditor dashboard analytics retrieved successfully"
            )

    except Exception:
        logger.exception("Error in auditor dashboard analytics")
        return server_error("Failed to fetch analytics")


@router.get("/overall-protection")
async def get_auditor_overall_protection(
    ctx: Annotated[RequestContext, Depends(get_context)],
    page: int = 1,
    limit: int = 10,
    search: str = "",
    status_filter: Annotated[str, Query(alias="statusFilter")] = "",
    sort_by: Annotated[str, Query(alias="sortBy")] = "framework",
    sort_order: Annotated[str, Query(alias="sortOrder")] = "asc",
):
    try:
        tenant_id = ctx.tenant_id

        async with session_scope() as session:
            dfs = list(
                (
                    await session.execute(
                        select(DeploymentFramework).where(DeploymentFramework.tenantId == tenant_id)
                    )
                )
                .scalars()
                .all()
            )

            live_packages, gap_analysis_ids, merge_doc_ids = get_live_packages(dfs)

            gap_analyses = (
                list(
                    (
                        await session.execute(
                            select(PackageGapAnalysis).where(
                                PackageGapAnalysis.id.in_(gap_analysis_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                if gap_analysis_ids
                else []
            )

            merges = (
                list(
                    (
                        await session.execute(
                            select(DeploymentPackageMerge).where(
                                DeploymentPackageMerge.id.in_(merge_doc_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                if merge_doc_ids
                else []
            )

            assignment_ids = [
                get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
                for ga in gap_analyses
                if get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
            ]

            assignments = (
                list(
                    (
                        await session.execute(
                            select(FrameworkAssignment).where(
                                FrameworkAssignment.id.in_(assignment_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                if assignment_ids
                else []
            )

            historical_gap_analysis_ids = [
                get_nested(pkg, "gapAnalysis")
                for df in dfs
                for pkg in (df.packages or [])
                if get_nested(pkg, "gapAnalysis")
            ]

            historical_gap_analyses = (
                list(
                    (
                        await session.execute(
                            select(PackageGapAnalysis)
                            .where(PackageGapAnalysis.id.in_(historical_gap_analysis_ids))
                            .order_by(desc(PackageGapAnalysis.createdAt))
                        )
                    )
                    .scalars()
                    .all()
                )
                if historical_gap_analysis_ids
                else []
            )

            (
                total_controls_overall,
                _,
                _,
                _,
                _,
                framework_health,
                total_dps_overall,
                implemented_dps_overall,
                prev_implemented_dps_overall,
            ) = process_gap_analyses(
                gap_analyses, live_packages, historical_gap_analyses, merges, assignments
            )

            overall_protection = (
                round((implemented_dps_overall / total_dps_overall) * 100)
                if total_dps_overall > 0
                else 0
            )
            overall_prev_protection = (
                round((prev_implemented_dps_overall / total_dps_overall) * 100)
                if total_dps_overall > 0
                else overall_protection
            )

            overall_trend_val = overall_protection - overall_prev_protection
            overall_trend_up = overall_trend_val >= 0
            overall_trend_abs = abs(overall_trend_val)

            settings = get_settings()

            # Build rows
            rows = build_overall_protection_rows(framework_health, settings)

            # Apply filters and sorting
            rows = filter_and_sort_rows(rows, search, status_filter, sort_by, sort_order)

            # Pagination
            page_num = clamp_page(page)
            limit_num = clamp_limit(limit)

            total = len(rows)
            start = (page_num - 1) * limit_num
            end = start + limit_num
            paged_rows = rows[start:end]

            data = {
                "frameworks": paged_rows,
                "stats": {
                    "score": overall_protection,
                    "trend": overall_trend_abs,
                    "trendUp": overall_trend_up,
                    "frameworksActive": len(framework_health),
                    "controlsEvaluated": total_controls_overall,
                    "deploymentPoints": total_dps_overall,
                },
            }

            return paginated(
                data,
                build_pagination_meta(page_num, limit_num, total),
                "Overall protection retrieved successfully",
            )

    except Exception:
        logger.exception("Error in overall protection")
        return server_error("Failed to fetch overall protection")
