import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from vora_shared.database import session_scope
from vora_shared.models import (
    DeploymentFramework,
    PackageGapAnalysis,
    DeploymentPackageMerge,
    EvidenceOutput,
    FrameworkAssignment,
)
from vora_shared.responses import error, server_error, success, paginated
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.security import RequestContext, get_context
from vora_shared.config import get_settings
from app.helpers import (
    extract_actual_implemented,
    extract_custom_controls,
    extract_expected_controls,
    extract_historical_implemented,
    evaluate_controls,
)


router = APIRouter(tags=["auditor-dashboard"])
logger = logging.getLogger(__name__)


def _get(obj: Any, key: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get_live_packages(dfs: list[DeploymentFramework]) -> tuple[list[dict], list[str], list[str]]:
    """Extract live packages, gap analysis IDs, and merge document IDs."""
    live_packages = []
    gap_analysis_ids = []
    merge_doc_ids = []

    for df in dfs:
        for pkg in df.packages or []:
            if _get(pkg, "status") != "live" or _get(pkg, "type") != "deployed":
                continue
            
            live_packages.append({"df": df, "pkg": pkg})
            
            gap_analysis = _get(pkg, "gapAnalysis")
            if gap_analysis:
                gap_analysis_ids.append(str(gap_analysis))
                
            merge_doc = _get(pkg, "mergeDocument")
            if merge_doc:
                merge_doc_ids.append(str(merge_doc))
                    
    return live_packages, gap_analysis_ids, merge_doc_ids


def _process_gap_analyses(gap_analyses: list[PackageGapAnalysis], live_packages: list[dict], historical_gap_analyses: list[PackageGapAnalysis], merges: list[DeploymentPackageMerge], assignments: list[FrameworkAssignment]) -> tuple:
    """Extract and calculate gap analysis metrics."""
    total_controls_overall = 0
    passing_controls_overall = 0
    extra_controls_overall = 0
    critical_gaps = 0
    active_gaps = []
    framework_health = []
    total_dps_overall = 0
    implemented_dps_overall = 0
    prev_implemented_dps_overall = 0

    for lp in live_packages:
        ga_id = str(_get(lp["pkg"], "gapAnalysis"))
        merge_id = str(_get(lp["pkg"], "mergeDocument"))
        
        ga = next((g for g in gap_analyses if str(g.id) == ga_id), None)
        merge_doc = next((m for m in merges if str(m.id) == merge_id), None)
        
        if not ga or not merge_doc:
            continue
            
        gap_data = ga.gapAnalysis or {}
        df_id = _get(gap_data, "deployment_framework_id")
        fw_assignment_id = _get(gap_data, "framework_assignment_id")
        
        fw_name = lp["df"].frameworkName or "Unknown Framework"
        fw_version = lp["df"].frameworkVersion or ""
        
        custom_controls = extract_custom_controls(fw_assignment_id, assignments)
        expected_controls = extract_expected_controls(merge_doc, custom_controls)
        
        # 2. Extract actual implemented counts from current gapAnalysis
        gap_results = _get(gap_data, "deployment_gap_results") or []
        actual_implemented = extract_actual_implemented(gap_results)
        
        # 3. Extract implemented counts from historical gapAnalysis for trend
        prev_actual_implemented = extract_historical_implemented(
            df_id, ga.createdAt, historical_gap_analyses
        )
        
        # 4. Evaluate each expected control
        (
            fw_total_controls,
            fw_passing_controls,
            fw_total_dps,
            fw_implemented_dps,
            fw_extra_controls,
            fw_critical_gaps,
            fw_active_gaps,
            fw_prev_implemented_dps
        ) = evaluate_controls(
            expected_controls,
            actual_implemented,
            prev_actual_implemented,
            ga,
            fw_name,
            fw_version
        )
        
        # Accumulate global metrics
        total_controls_overall += fw_total_controls
        passing_controls_overall += fw_passing_controls
        extra_controls_overall += fw_extra_controls
        total_dps_overall += fw_total_dps
        implemented_dps_overall += fw_implemented_dps
        if prev_actual_implemented is not None:
            prev_implemented_dps_overall += fw_prev_implemented_dps
        else:
            prev_implemented_dps_overall += fw_implemented_dps
            
        critical_gaps += fw_critical_gaps
        active_gaps.extend(fw_active_gaps)
        
        fw_health = 0
        fw_prev_health = 0
        if fw_total_dps > 0:
            fw_health = round((fw_implemented_dps / fw_total_dps) * 100)
            if prev_actual_implemented is not None:
                fw_prev_health = round((fw_prev_implemented_dps / fw_total_dps) * 100)
            else:
                fw_prev_health = fw_health # If no history, trend should be 0
            
        trend_val = fw_health - fw_prev_health
        trend_up = trend_val >= 0
        trend_abs = abs(trend_val)
            
        # Calculate dynamic framework weight based on assigned controls' customer_weightage
        fw_weight_score = 0.0
        if fw_assignment_id:
            assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
            if assignment and assignment.fileVersions:
                latest_fv = assignment.fileVersions[-1]
                ai_ext = (latest_fv.get("aiExtraction") if isinstance(latest_fv, dict) else getattr(latest_fv, "aiExtraction", [])) or []
                for sec in ai_ext:
                    for ctrl in (sec.get("controls") if isinstance(sec, dict) else getattr(sec, "controls", [])) or []:
                        custom = ctrl.get("customization") if isinstance(ctrl, dict) else getattr(ctrl, "customization", {})
                        weight_obj = (custom.get("weightage") if isinstance(custom, dict) else getattr(custom, "weightage", {})) or {}
                        c_weight = weight_obj.get("customer_weightage", 10.0) if isinstance(weight_obj, dict) else getattr(weight_obj, "customer_weightage", 10.0)
                        fw_weight_score += float(c_weight)

        framework_health.append({
            "id": str(lp["df"].id),
            "name": fw_name,
            "version": fw_version,
            "readiness": fw_health,
            "weight_score": fw_weight_score,
            "trend": trend_abs,
            "trendUp": trend_up
        })

    return total_controls_overall, passing_controls_overall, extra_controls_overall, critical_gaps, active_gaps, framework_health, total_dps_overall, implemented_dps_overall, prev_implemented_dps_overall


def _iter_evidence_records(ev: EvidenceOutput):
    """Yield records from an evidence output."""
    out = ev.output or {}
    fw_name = _get(out, "frameworkName")
    fw_version = _get(out, "frameworkVersion") or _get(out, "currentFileVersion") or ""
    
    for fv in _get(out, "fileVersions") or []:
        for cdata in (_get(fv, "data") or {}).values():
            for rec in _get(cdata, "records") or []:
                yield fw_name, fw_version, rec


def _format_stream_record(ev: EvidenceOutput, fw_name: str, fw_version: str, rec: dict) -> dict:
    """Format a single audit stream record."""
    status_str = _get(rec, "compliance_status", "").lower()
    
    status = "warn"
    if "not compliant" in status_str:
        status = "fail"
    elif "compliant" in status_str:
        status = "pass"
        
    desc = _get(rec, "deployment_point", "")
    
    llm_analysis = _get(rec, "llm_analysis") or {}
    reason = _get(llm_analysis, "reason", "")
    confidence = _get(llm_analysis, "confidence", "")
        
    return {
        "id": _get(rec, "file_id", str(ev.id)),
        "dp_id": _get(rec, "dp_id", ""),
        "status": status,
        "framework": fw_name,
        "version": fw_version,
        "description": desc,
        "reason": reason,
        "confidence": confidence,
        "timestamp": ev.createdAt.isoformat() if ev.createdAt else None
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
            llm_analysis = _get(rec, "llm_analysis") or {}
            recommendation = _get(llm_analysis, "recommendation")
            if recommendation:
                confidence = str(_get(llm_analysis, "confidence") or "").title()
                priority = confidence if confidence in ["High", "Medium", "Low"] else "Low"
                insights.append({
                    "text": recommendation,
                    "priority": priority
                })
    return insights


def _get_dp_count_for_merge(pm: DeploymentPackageMerge) -> int:
    controls = pm.controls or {}
    controls_data = _get(controls, "controls_data") or []
    dp_count = 0
    for section in controls_data:
        for control in _get(section, "controls") or []:
            dp_count += len(_get(control, "deployment_points") or [])
    return dp_count

def _process_deployment_points(
    merges: list[DeploymentPackageMerge], 
    live_packages: list[dict]
) -> list[dict]:
    """Aggregate configured deployment points per framework."""
    deployment_points = []
    for pm in merges:
        dp_count = _get_dp_count_for_merge(pm)
        
        fw_name = "Unknown Framework"
        fw_version = ""
        for lp in live_packages:
            if str(_get(lp["pkg"], "mergeDocument")) == str(pm.id):
                fw_name = lp["df"].frameworkName or fw_name
                fw_version = lp["df"].frameworkVersion or ""
                break
        
        deployment_points.append({
            "name": fw_name,
            "version": fw_version,
            "count": dp_count
        })
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
                ).scalars().all()
            )

            live_packages, gap_analysis_ids, merge_doc_ids = _get_live_packages(dfs)

            gap_analyses = list((await session.execute(
                select(PackageGapAnalysis).where(PackageGapAnalysis.id.in_(gap_analysis_ids))
            )).scalars().all()) if gap_analysis_ids else []

            merges = list((await session.execute(
                select(DeploymentPackageMerge).where(DeploymentPackageMerge.id.in_(merge_doc_ids))
            )).scalars().all()) if merge_doc_ids else []
            
            assignment_ids = [
                _get(ga.gapAnalysis or {}, "framework_assignment_id")
                for ga in gap_analyses if _get(ga.gapAnalysis or {}, "framework_assignment_id")
            ]
            
            assignments = list((await session.execute(
                select(FrameworkAssignment).where(FrameworkAssignment.id.in_(assignment_ids))
            )).scalars().all()) if assignment_ids else []
            
            evidence_outputs = list((await session.execute(
                select(EvidenceOutput).order_by(desc(EvidenceOutput.createdAt))
            )).scalars().all())
            
            historical_gap_analysis_ids = [
                _get(pkg, "gapAnalysis")
                for df in dfs for pkg in (df.packages or [])
                if _get(pkg, "gapAnalysis")
            ]
            
            historical_gap_analyses = list((await session.execute(
                select(PackageGapAnalysis)
                .where(PackageGapAnalysis.id.in_(historical_gap_analysis_ids))
                .order_by(desc(PackageGapAnalysis.createdAt))
            )).scalars().all()) if historical_gap_analysis_ids else []

            total_controls_overall, passing_controls_overall, extra_controls_overall, critical_gaps, active_gaps, framework_health, total_dps_overall, implemented_dps_overall = _process_gap_analyses(gap_analyses, live_packages, historical_gap_analyses, merges, assignments)
            overall_protection = round((implemented_dps_overall / total_dps_overall) * 100) if total_dps_overall > 0 else 0

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

            return success(response_data, message="Auditor dashboard analytics retrieved successfully")

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
    sort_order: Annotated[str, Query(alias="sortOrder")] = "asc"
):
    try:
        tenant_id = ctx.tenant_id

        async with session_scope() as session:
            dfs = list(
                (
                    await session.execute(
                        select(DeploymentFramework).where(DeploymentFramework.tenantId == tenant_id)
                    )
                ).scalars().all()
            )

            live_packages, gap_analysis_ids, merge_doc_ids = _get_live_packages(dfs)

            gap_analyses = list((await session.execute(
                select(PackageGapAnalysis).where(PackageGapAnalysis.id.in_(gap_analysis_ids))
            )).scalars().all()) if gap_analysis_ids else []

            merges = list((await session.execute(
                select(DeploymentPackageMerge).where(DeploymentPackageMerge.id.in_(merge_doc_ids))
            )).scalars().all()) if merge_doc_ids else []
            
            assignment_ids = [
                _get(ga.gapAnalysis or {}, "framework_assignment_id")
                for ga in gap_analyses if _get(ga.gapAnalysis or {}, "framework_assignment_id")
            ]
            
            assignments = list((await session.execute(
                select(FrameworkAssignment).where(FrameworkAssignment.id.in_(assignment_ids))
            )).scalars().all()) if assignment_ids else []
            
            historical_gap_analysis_ids = [
                _get(pkg, "gapAnalysis")
                for df in dfs for pkg in (df.packages or [])
                if _get(pkg, "gapAnalysis")
            ]
            
            historical_gap_analyses = list((await session.execute(
                select(PackageGapAnalysis)
                .where(PackageGapAnalysis.id.in_(historical_gap_analysis_ids))
                .order_by(desc(PackageGapAnalysis.createdAt))
            )).scalars().all()) if historical_gap_analysis_ids else []

            total_controls_overall, _, _, _, _, framework_health, total_dps_overall, implemented_dps_overall, prev_implemented_dps_overall = _process_gap_analyses(gap_analyses, live_packages, historical_gap_analyses, merges, assignments)
            
            overall_protection = round((implemented_dps_overall / total_dps_overall) * 100) if total_dps_overall > 0 else 0
            overall_prev_protection = round((prev_implemented_dps_overall / total_dps_overall) * 100) if total_dps_overall > 0 else overall_protection
            
            overall_trend_val = overall_protection - overall_prev_protection
            overall_trend_up = overall_trend_val >= 0
            overall_trend_abs = abs(overall_trend_val)

            settings = get_settings()
            
            # Transform framework health into table rows
            rows = []
            fw_count = len(framework_health)
            total_weight_score = sum(fw.get("weight_score", 0) for fw in framework_health)
            
            # To handle rounding issues so sum is exactly 100
            allocated_weight = 0
            
            for idx, fw in enumerate(framework_health):
                readiness = fw.get("readiness", 0)
                ws = fw.get("weight_score", 0)
                
                # Dynamic weight based on sum of control weightages in DB
                if total_weight_score > 0:
                    if idx == fw_count - 1:
                        # Give remaining percentage to the last item to ensure total is exactly 100
                        weight_val = 100 - allocated_weight
                    else:
                        weight_val = round((ws / total_weight_score) * 100)
                        allocated_weight += weight_val
                else:
                    # Fallback to equal distribution if no weights are found
                    weight_val = 100 // fw_count if fw_count > 0 else 0
                    if idx == 0 and fw_count > 0:
                        weight_val += 100 % fw_count
                    
                status = "On Track"
                if readiness < (settings.compliance_score_low * 100):
                    status = "At Risk"
                elif readiness <= (settings.compliance_score_medium * 100):
                    status = "Needs Attention"
                    
                rows.append({
                    "id": fw.get("id"),
                    "version": fw.get("version", ""),
                    "framework": fw.get("name", ""),
                    "weight": weight_val,
                    "rawScore": readiness,
                    "contribution": round(weight_val * readiness / 100, 2),
                    "trend": fw.get("trend", 0),
                    "trendUp": fw.get("trendUp", True),
                    "status": status
                })

            # Filtering
            if search:
                s = search.lower()
                rows = [r for r in rows if s in r.get("framework", "").lower() or s in r.get("version", "").lower()]
                
            if status_filter:
                rows = [r for r in rows if r.get("status") == status_filter]

            # Sorting
            if sort_by:
                reverse = sort_order == "desc"
                rows.sort(key=lambda x: x.get(sort_by, 0) if isinstance(x.get(sort_by), (int, float)) else x.get(sort_by, ""), reverse=reverse)

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
                }
            }

            return paginated(data, build_pagination_meta(page_num, limit_num, total), "Overall protection retrieved successfully")

    except Exception:
        logger.exception("Error in auditor overall protection")
        return server_error("Failed to fetch overall protection")
