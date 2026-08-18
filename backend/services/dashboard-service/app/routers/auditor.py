import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from vora_shared.database import session_scope
from vora_shared.models import (
    DeploymentFramework,
    PackageGapAnalysis,
    DeploymentPackageMerge,
    EvidenceOutput,
    FrameworkAssignment,
)
from vora_shared.responses import server_error, success
from vora_shared.security import RequestContext, get_context


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
            if _get(pkg, "status") == "live" and _get(pkg, "type") == "deployed":
                live_packages.append({"df": df, "pkg": pkg})
                gap_analysis = _get(pkg, "gapAnalysis")
                merge_doc = _get(pkg, "mergeDocument")
                if gap_analysis:
                    gap_analysis_ids.append(str(gap_analysis))
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
        
        fw_total_controls = 0
        fw_passing_controls = 0
        fw_total_dps = 0
        fw_implemented_dps = 0
        fw_active_gaps = []
        
        # 1. Parse customization map from FrameworkAssignment
        custom_controls = {}
        if fw_assignment_id:
            assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
            if assignment and assignment.fileVersions and len(assignment.fileVersions) > 0:
                latest_fv = assignment.fileVersions[-1]
                ai_extraction = _get(latest_fv, "aiExtraction") or []
                for sec in ai_extraction:
                    for ctrl in _get(sec, "controls") or []:
                        ctrl_id = _get(ctrl, "id")
                        if ctrl_id:
                            is_custom = _get(_get(ctrl, "customization") or {}, "source") == "custom"
                            custom_controls[ctrl_id] = is_custom
        
        # 2. Parse expected controls and DPs from mergeDocument
        expected_controls = {}
        controls_data = _get(merge_doc.controls or {}, "controls_data") or []
        for sec in controls_data:
            for ctrl in _get(sec, "controls") or []:
                ctrl_id = _get(ctrl, "id")
                if ctrl_id:
                    expected_controls[ctrl_id] = {
                        "name": _get(ctrl, "name") or ctrl_id,
                        "description": _get(ctrl, "description", ""),
                        "required_dps": len(_get(ctrl, "deployment_points") or []),
                        "is_extra": custom_controls.get(ctrl_id, False)
                    }

        # 2. Extract actual implemented counts from current gapAnalysis
        gap_results = _get(gap_data, "deployment_gap_results") or []
        actual_implemented = {}
        for result in gap_results:
            ctrl_id = _get(result, "assigned_framework_control_id")
            if not ctrl_id: continue
            if ctrl_id not in actual_implemented:
                actual_implemented[ctrl_id] = 0
            
            status = str(_get(result, "implementation_status") or "").lower()
            if status in ["implemented", "compliant", "passed", "fully implemented"]:
                actual_implemented[ctrl_id] += 1

        # 3. Extract implemented counts from historical gapAnalysis for trend
        prev_actual_implemented = {}
        if df_id and ga.createdAt:
            for hga in historical_gap_analyses:
                hga_df_id = _get(hga.gapAnalysis or {}, "deployment_framework_id")
                if hga_df_id == df_id and hga.createdAt and hga.createdAt < ga.createdAt:
                    hga_results = _get(hga.gapAnalysis or {}, "deployment_gap_results") or []
                    for result in hga_results:
                        ctrl_id = _get(result, "assigned_framework_control_id")
                        if not ctrl_id: continue
                        if ctrl_id not in prev_actual_implemented:
                            prev_actual_implemented[ctrl_id] = 0
                        status = str(_get(result, "implementation_status") or "").lower()
                        if status in ["implemented", "compliant", "passed", "fully implemented"]:
                            prev_actual_implemented[ctrl_id] += 1
                    break

        # 4. Evaluate each expected control
        for ctrl_id, expected in expected_controls.items():
            fw_total_controls += 1
            total_controls_overall += 1
            if expected["is_extra"]:
                extra_controls_overall += 1
            
            req_dps = expected["required_dps"]
            impl_dps = actual_implemented.get(ctrl_id, 0)
            
            fw_total_dps += req_dps
            fw_implemented_dps += min(impl_dps, req_dps)
            
            total_dps_overall += req_dps
            implemented_dps_overall += min(impl_dps, req_dps)
            
            if req_dps > 0 and impl_dps >= req_dps:
                fw_passing_controls += 1
                passing_controls_overall += 1
            else:
                critical_gaps += 1
                
                failing_percentage = 100
                if req_dps > 0:
                    failing_percentage = round(((req_dps - impl_dps) / req_dps) * 100)
                
                trend = "flat"
                if ctrl_id in prev_actual_implemented:
                    prev_impl = prev_actual_implemented[ctrl_id]
                    prev_failing_pct = 100
                    if req_dps > 0:
                        prev_failing_pct = round(((req_dps - prev_impl) / req_dps) * 100)
                    
                    if failing_percentage > prev_failing_pct:
                        trend = "down"
                    elif failing_percentage < prev_failing_pct:
                        trend = "up"
                        
                fw_active_gaps.append({
                    "id": ctrl_id,
                    "framework": fw_name,
                    "version": fw_version,
                    "control": expected["name"],
                    "description": expected["description"],
                    "instances": req_dps,
                    "failing": failing_percentage, 
                    "lastNC": ga.createdAt.isoformat() if ga.createdAt else None,
                    "trend": trend
                })

        active_gaps.extend(fw_active_gaps)
        
        fw_health = 0
        if fw_total_dps > 0:
            fw_health = round((fw_implemented_dps / fw_total_dps) * 100)
            
        framework_health.append({
            "name": fw_name,
            "version": fw_version,
            "readiness": fw_health
        })

    return total_controls_overall, passing_controls_overall, extra_controls_overall, critical_gaps, active_gaps, framework_health, total_dps_overall, implemented_dps_overall


def _process_live_streams(evidence_outputs: list[EvidenceOutput]) -> list[dict]:
    """Extract and format recent live audit streams."""
    live_streams = []
    for ev in evidence_outputs:
        out = ev.output or {}
        fw_name = _get(out, "frameworkName")
        fw_version = _get(out, "frameworkVersion") or _get(out, "currentFileVersion") or ""
        file_versions = _get(out, "fileVersions") or []
        
        for fv in file_versions:
            data = _get(fv, "data") or {}
            for cid, cdata in data.items():
                records = _get(cdata, "records") or []
                for rec in records:
                    status_str = _get(rec, "compliance_status", "").lower()
                    
                    status = "warn"
                    if "not compliant" in status_str:
                        status = "fail"
                    elif "compliant" in status_str:
                        status = "pass"
                        
                    desc = _get(rec, "deployment_point", "")
                    if len(desc) > 50:
                        desc = desc[:47] + "..."
                        
                    live_streams.append({
                        "id": _get(rec, "file_id", str(ev.id)),
                        "status": status,
                        "framework": fw_name,
                        "version": fw_version,
                        "description": f"{desc} • {fw_name}",
                        "timestamp": ev.createdAt.isoformat() if ev.createdAt else None
                    })
                    if len(live_streams) >= 20:
                        break
            if len(live_streams) >= 20:
                break
        if len(live_streams) >= 20:
            break
            
    return live_streams


def _process_deployment_points(
    merges: list[DeploymentPackageMerge], 
    live_packages: list[dict]
) -> list[dict]:
    """Aggregate configured deployment points per framework."""
    deployment_points = []
    for pm in merges:
        controls = pm.controls or {}
        controls_data = _get(controls, "controls_data") or []
        dp_count = 0
        for section in controls_data:
            for control in _get(section, "controls") or []:
                dp_count += len(_get(control, "deployment_points") or [])
        
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

            gap_analyses = []
            if gap_analysis_ids:
                gap_analyses = list(
                    (
                        await session.execute(
                            select(PackageGapAnalysis).where(PackageGapAnalysis.id.in_(gap_analysis_ids))
                        )
                    ).scalars().all()
                )

            merges = []
            if merge_doc_ids:
                merges = list(
                    (
                        await session.execute(
                            select(DeploymentPackageMerge).where(DeploymentPackageMerge.id.in_(merge_doc_ids))
                        )
                    ).scalars().all()
                )
            
            assignment_ids = []
            for ga in gap_analyses:
                fw_assignment_id = _get(ga.gapAnalysis or {}, "framework_assignment_id")
                if fw_assignment_id:
                    assignment_ids.append(fw_assignment_id)
            
            assignments = []
            if assignment_ids:
                assignments = list(
                    (
                        await session.execute(
                            select(FrameworkAssignment).where(FrameworkAssignment.id.in_(assignment_ids))
                        )
                    ).scalars().all()
                )
            
            evidence_outputs = list(
                (
                    await session.execute(
                        select(EvidenceOutput)
                        .order_by(desc(EvidenceOutput.createdAt))
                        .limit(50)
                    )
                ).scalars().all()
            )
            
            historical_gap_analysis_ids = []
            for df in dfs:
                for pkg in (df.packages or []):
                    gid = _get(pkg, "gapAnalysis")
                    if gid:
                        historical_gap_analysis_ids.append(gid)
            
            historical_gap_analyses = []
            if historical_gap_analysis_ids:
                historical_gap_analyses = list(
                    (
                        await session.execute(
                            select(PackageGapAnalysis)
                            .where(PackageGapAnalysis.id.in_(historical_gap_analysis_ids))
                            .order_by(desc(PackageGapAnalysis.createdAt))
                        )
                    ).scalars().all()
                )

            total_controls_overall, passing_controls_overall, extra_controls_overall, critical_gaps, active_gaps, framework_health, total_dps_overall, implemented_dps_overall = _process_gap_analyses(gap_analyses, live_packages, historical_gap_analyses, merges, assignments)
            overall_protection = round((implemented_dps_overall / total_dps_overall) * 100) if total_dps_overall > 0 else 0

            live_streams = _process_live_streams(evidence_outputs)
            deployment_points = _process_deployment_points(merges, live_packages)

            response_data = {
                "overallProtection": overall_protection,
                "criticalGaps": critical_gaps,
                "controlPassing": f"{passing_controls_overall}/{total_controls_overall}",
                "extraControls": extra_controls_overall, 
                "frameworkHealth": framework_health,
                "activeGaps": active_gaps[:10], 
                "liveAuditStreams": live_streams,
                "deploymentPoints": deployment_points,
            }

            return success(response_data, message="Auditor dashboard analytics retrieved successfully")

    except Exception:
        logger.exception("Error in auditor dashboard analytics")
        return server_error("Failed to fetch analytics")
