import logging

from typing import Any, Annotated
from datetime import datetime
UNKNOWN_FRAMEWORK = "Unknown Framework"


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

@router.get("/analytics")
async def get_auditor_dashboard_analytics(
    ctx: Annotated[RequestContext, Depends(get_context)],
):

    def _get(obj: Any, key: str, default: Any = None) -> Any:
        """Helper to safely get attributes or dictionary keys."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if hasattr(obj, key) else default

    def _evaluate_trend(
        ctrl_id: str,
        req_dps: int,
        failing_percentage: int,
        prev_actual_implemented: dict[str, int] | None,
    ) -> str:
        if prev_actual_implemented is None or ctrl_id not in prev_actual_implemented:
            return "flat"
    
        prev_impl = prev_actual_implemented[ctrl_id]
        prev_failing_pct = 100
        if req_dps > 0:
            prev_failing_pct = round(((req_dps - prev_impl) / req_dps) * 100)
    
        if failing_percentage > prev_failing_pct:
            return "down"
        if failing_percentage < prev_failing_pct:
            return "up"
        return "flat"

    def calculate_gap_severity(failing_percentage: int, settings: Any) -> str:
        if failing_percentage > (1 - settings.compliance_score_low) * 100:
            return "High"
        if failing_percentage > (1 - settings.compliance_score_medium) * 100:
            return "Medium"
        return "Low"

    def _extract_control_weight(ctrl: Any) -> float:
        """Extract customer weightage from a control object."""
        custom = _get(ctrl, "customization") or {}
        weight_obj = _get(custom, "weightage") or {}
        return float(_get(weight_obj, "customer_weightage", 10.0))

    def calculate_fw_weight_score(
        fw_assignment_id: str, assignments: list[FrameworkAssignment]
    ) -> float:
        """Calculate dynamic framework weight based on assigned controls' customer_weightage."""
        fw_weight_score = 0.0
        if not fw_assignment_id:
            return fw_weight_score
    
        assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
        if not assignment or not assignment.fileVersions:
            return fw_weight_score
    
        latest_fv = assignment.fileVersions[-1]
        ai_ext = get_nested(latest_fv, "aiExtraction") or []
    
        for sec in ai_ext:
            for ctrl in get_nested(sec, "controls") or []:
                fw_weight_score += _extract_control_weight(ctrl)
    
        return fw_weight_score

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




    def get_latest_packages(dfs: list[DeploymentFramework]) -> tuple[list[dict], list[str], list[str]]:
        """Extract latest packages, gap analysis IDs, and merge document IDs."""
        latest_packages = []
        gap_analysis_ids = []
        merge_doc_ids = []
    
        for df in dfs:
            if not df.packages:
                continue
                
            latest_pkg = max(df.packages, key=lambda p: get_nested(p, "createdAt") or "")
    
            latest_packages.append({"df": df, "pkg": latest_pkg})
    
            gap_analysis = get_nested(latest_pkg, "gapAnalysis")
            if gap_analysis:
                gap_analysis_ids.append(str(gap_analysis))
    
            merge_doc = get_nested(latest_pkg, "mergeDocument")
            if merge_doc:
                merge_doc_ids.append(str(merge_doc))
    
        return latest_packages, gap_analysis_ids, merge_doc_ids

    def get_nested(obj: Any, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def extract_custom_controls(
        fw_assignment_id: str | None, assignments: list[FrameworkAssignment]
    ) -> dict[str, bool]:
        """Parse custom controls map from FrameworkAssignment."""
        custom_controls = {}
        if not fw_assignment_id:
            return custom_controls
    
        assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
        if not assignment or not assignment.fileVersions:
            return custom_controls
    
        latest_fv = assignment.fileVersions[-1]
        ai_extraction = _get(latest_fv, "aiExtraction") or []
        for sec in ai_extraction:
            for ctrl in _get(sec, "controls") or []:
                ctrl_id = _get(ctrl, "id")
                if ctrl_id:
                    is_custom = _get(_get(ctrl, "customization") or {}, "source") == "custom"
                    custom_controls[ctrl_id] = is_custom
    
        return custom_controls

    def extract_expected_controls(merge_doc: Any, custom_controls: dict[str, bool]) -> dict[str, Any]:
        """Parse expected controls and DPs from mergeDocument."""
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
                        "is_extra": custom_controls.get(ctrl_id, False),
                    }
        return expected_controls

    def extract_actual_implemented(gap_results: list[Any]) -> dict[str, int]:
        """Extract actual implemented counts from current gapAnalysis."""
        actual_implemented = {}
        for result in gap_results:
            ctrl_id = _get(result, "deployment_framework_control_id")
            if not ctrl_id:
                continue
            if ctrl_id not in actual_implemented:
                actual_implemented[ctrl_id] = 0
    
            status = str(_get(result, "implementation_status") or "").lower()
            if status in ["implemented", "compliant", "passed", "fully implemented"]:
                actual_implemented[ctrl_id] += 1
    
        return actual_implemented

    def extract_historical_implemented(
        df_id: str, current_created_at: datetime | None, historical_gap_analyses: list[Any]
    ) -> dict[str, int] | None:
        """Extract implemented counts from historical gapAnalysis for trend calculation. Returns None if no history exists."""
        if not df_id or not current_created_at:
            return None
    
        for hga in historical_gap_analyses:
            hga_df_id = _get(hga.gapAnalysis or {}, "deployment_framework_id")
            if hga_df_id == df_id and hga.createdAt and hga.createdAt < current_created_at:
                hga_results = _get(hga.gapAnalysis or {}, "deployment_gap_results") or []
                return extract_actual_implemented(hga_results)
    
        return None

    def calculate_fw_health_and_trend(
        fw_implemented_dps: int,
        fw_total_dps: int,
        prev_actual_implemented: Any,
        fw_prev_implemented_dps: int,
    ) -> tuple[float, float, bool]:
        """Calculate framework health and trend values."""
        fw_health = 0
        fw_prev_health = 0
        if fw_total_dps > 0:
            fw_health = round((fw_implemented_dps / fw_total_dps) * 100)
            if prev_actual_implemented is not None:
                fw_prev_health = round((fw_prev_implemented_dps / fw_total_dps) * 100)
            else:
                fw_prev_health = fw_health
    
        trend_val = fw_health - fw_prev_health
        trend_up = trend_val >= 0
        trend_abs = abs(trend_val)
    
        return fw_health, trend_abs, trend_up

    def _create_active_gap(
        ctrl_id: str,
        expected: dict,
        req_dps: int,
        impl_dps: int,
        prev_actual_implemented: dict[str, int] | None,
        ga: Any,
        fw_id: str,
        fw_name: str,
        fw_version: str,
        pkg_version: str,
        settings: Any,
    ) -> dict:
        failing_percentage = 100
        if req_dps > 0:
            failing_percentage = round(((req_dps - impl_dps) / req_dps) * 100)
    
        trend = _evaluate_trend(ctrl_id, req_dps, failing_percentage, prev_actual_implemented)
    
        return {
            "id": ctrl_id,
            "frameworkId": fw_id,
            "framework": fw_name,
            "version": fw_version,
            "packageVersion": pkg_version,
            "control": expected["name"],
            "description": expected["description"],
            "instances": req_dps,
            "failing": failing_percentage,
            "lastNC": ga.createdAt.isoformat() if ga and ga.createdAt else None,
            "trend": trend,
            "severity": calculate_gap_severity(failing_percentage, settings),
        }

    def evaluate_controls(
        expected_controls: dict[str, Any],
        actual_implemented: dict[str, int],
        prev_actual_implemented: dict[str, int] | None,
        ga: Any,
        fw_id: str,
        fw_name: str,
        fw_version: str,
        pkg_version: str,
        settings: Any,
    ) -> tuple[int, int, int, int, int, int, int, list[dict], int]:
        """Evaluate controls against implemented DPs and return aggregated metrics."""
        fw_total_controls = 0
        fw_passing_controls = 0
        fw_total_dps = 0
        fw_implemented_dps = 0
        fw_extra_controls = 0
        fw_extra_controls_list = []
        fw_critical_gaps = 0
        fw_active_gaps = []
        fw_prev_implemented_dps = 0
    
        for ctrl_id, expected in expected_controls.items():
            fw_total_controls += 1
            req_dps = expected["required_dps"]
    
            if expected["is_extra"]:
                fw_extra_controls += 1
                fw_extra_controls_list.append(
                    {
                        "id": fw_id,
                        "ctrlId": ctrl_id,
                        "control": expected["name"],
                        "frameworkVersion": fw_version,
                        "frameworkName": fw_name,
                        "deploymentPoints": req_dps,
                    }
                )
    
            impl_dps = actual_implemented.get(ctrl_id, 0)
            is_implemented = impl_dps > 0
            
            prev_impl = (
                prev_actual_implemented.get(ctrl_id, 0) if prev_actual_implemented is not None else 0
            )
            is_prev_implemented = prev_impl > 0
    
            # Now fw_total_dps represents total controls
            fw_total_dps += 1
            fw_implemented_dps += 1 if is_implemented else 0
            fw_prev_implemented_dps += 1 if is_prev_implemented else 0
    
            if is_implemented:
                fw_passing_controls += 1
            else:
                fw_critical_gaps += 1
                fw_active_gaps.append(
                    _create_active_gap(
                        ctrl_id,
                        expected,
                        req_dps,
                        req_dps if is_implemented else 0,
                        prev_actual_implemented,
                        ga,
                        fw_id,
                        fw_name,
                        fw_version,
                        pkg_version,
                        settings,
                    )
                )
    
        return (
            fw_total_controls,
            fw_passing_controls,
            fw_total_dps,
            fw_implemented_dps,
            fw_extra_controls,
            fw_extra_controls_list,
            fw_critical_gaps,
            fw_active_gaps,
            fw_prev_implemented_dps,
        )

    def process_gap_analyses(
        gap_analyses: list[PackageGapAnalysis],
        latest_packages: list[dict],
        historical_gap_analyses: list[PackageGapAnalysis],
        merges: list[DeploymentPackageMerge],
        assignments: list[FrameworkAssignment],
        settings: Any,
    ) -> tuple:
        """Extract and calculate gap analysis metrics."""
        total_controls_overall = 0
        passing_controls_overall = 0
        extra_controls_overall = 0
        extra_controls_list = []
        critical_gaps = 0
        active_gaps = []
        framework_health = []
        total_dps_overall = 0
        implemented_dps_overall = 0
        prev_implemented_dps_overall = 0
    
        for lp in latest_packages:
            ga_id = str(get_nested(lp["pkg"], "gapAnalysis"))
            merge_id = str(get_nested(lp["pkg"], "mergeDocument"))
    
            ga = next((g for g in gap_analyses if str(g.id) == ga_id), None)
            merge_doc = next((m for m in merges if str(m.id) == merge_id), None)
    
            if not ga or not merge_doc:
                continue
    
            gap_data = ga.gapAnalysis or {}
            df_id = get_nested(gap_data, "deployment_framework_id")
            fw_assignment_id = get_nested(gap_data, "framework_assignment_id")
    
            fw_name = lp["df"].frameworkName or UNKNOWN_FRAMEWORK
            fw_version = lp["df"].frameworkVersion or ""
            pkg_version = str(get_nested(lp["pkg"], "packageVersion") or "")
    
            custom_controls = extract_custom_controls(fw_assignment_id, assignments)
            expected_controls = extract_expected_controls(merge_doc, custom_controls)
    
            gap_results = get_nested(gap_data, "deployment_gap_results") or []
            actual_implemented = extract_actual_implemented(gap_results)
    
            prev_actual_implemented = extract_historical_implemented(
                df_id, ga.createdAt, historical_gap_analyses
            )
    
            (
                fw_total_controls,
                fw_passing_controls,
                fw_total_dps,
                fw_implemented_dps,
                fw_extra_controls,
                fw_extra_controls_list,
                fw_critical_gaps,
                fw_active_gaps,
                fw_prev_implemented_dps,
            ) = evaluate_controls(
                expected_controls,
                actual_implemented,
                prev_actual_implemented,
                ga,
                str(lp["df"].id),
                fw_name,
                fw_version,
                pkg_version,
                settings,
            )
    
            total_controls_overall += fw_total_controls
            passing_controls_overall += fw_passing_controls
            extra_controls_overall += fw_extra_controls
            extra_controls_list.extend(fw_extra_controls_list)
            total_dps_overall += fw_total_dps
            implemented_dps_overall += fw_implemented_dps
            if prev_actual_implemented is not None:
                prev_implemented_dps_overall += fw_prev_implemented_dps
            else:
                prev_implemented_dps_overall += fw_implemented_dps
    
            critical_gaps += fw_critical_gaps
            active_gaps.extend(fw_active_gaps)
    
            fw_health, trend_abs, trend_up = calculate_fw_health_and_trend(
                fw_implemented_dps, fw_total_dps, prev_actual_implemented, fw_prev_implemented_dps
            )
    
            fw_weight_score = calculate_fw_weight_score(fw_assignment_id, assignments)
    
            framework_health.append(
                {
                    "id": str(lp["df"].id),
                    "name": fw_name,
                    "version": fw_version,
                    "readiness": fw_health,
                    "weight_score": fw_weight_score,
                    "trend": trend_abs,
                    "trendUp": trend_up,
                }
            )
    
        return (
            total_controls_overall,
            passing_controls_overall,
            extra_controls_overall,
            extra_controls_list,
            critical_gaps,
            active_gaps,
            framework_health,
            total_dps_overall,
            implemented_dps_overall,
            prev_implemented_dps_overall,
        )

    def process_live_streams(evidence_outputs: list[EvidenceOutput]) -> list[dict]:
        """Extract and format recent live audit streams."""
        live_streams = []
        for ev in evidence_outputs:
            for fw_name, fw_version, rec in _iter_evidence_records(ev):
                live_streams.append(_format_stream_record(ev, fw_name, fw_version, rec))
        return live_streams

    def process_ai_insights(evidence_outputs: list[EvidenceOutput]) -> list[dict]:
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

    def process_deployment_points(
        merges: list[DeploymentPackageMerge], latest_packages: list[dict]
    ) -> list[dict]:
        """Aggregate configured deployment points per framework."""
        deployment_points = []
        for lp in latest_packages:
            df = lp["df"]
            pkg = lp["pkg"]
            fw_name = df.frameworkName or UNKNOWN_FRAMEWORK
            fw_version = df.frameworkVersion or ""
            
            merge_id = str(get_nested(pkg, "mergeDocument"))
            
            # Check if the package has embedded mergedControls (some versions may have this)
            merged_controls = get_nested(pkg, "mergedControls")
            if merged_controls and get_nested(merged_controls, "controls_data"):
                dp_count = 0
                for sec in get_nested(merged_controls, "controls_data") or []:
                    for ctrl in get_nested(sec, "controls") or []:
                        dp_count += len(get_nested(ctrl, "deployment_points") or [])
            else:
                # Fallback to the DeploymentPackageMerge document
                pm = next((m for m in merges if str(m.id) == merge_id), None)
                dp_count = _get_dp_count_for_merge(pm) if pm else 0
                
            deployment_points.append({"name": fw_name, "version": fw_version, "count": dp_count})
            
        return deployment_points


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

            latest_packages, gap_analysis_ids, merge_doc_ids = get_latest_packages(dfs)

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

            settings = get_settings()
            (
                total_controls_overall,
                passing_controls_overall,
                extra_controls_overall,
                _, # Ignore extra_controls_list
                critical_gaps,
                active_gaps,
                framework_health,
                total_dps_overall,
                implemented_dps_overall,
                _, # Ignore prev_implemented_dps_overall
            ) = process_gap_analyses(
                gap_analyses, latest_packages, historical_gap_analyses, merges, assignments, settings
            )
            overall_protection = (
                round((implemented_dps_overall / total_dps_overall) * 100)
                if total_dps_overall > 0
                else 0
            )

            live_streams = process_live_streams(evidence_outputs)
            ai_insights = process_ai_insights(evidence_outputs)
            deployment_points = process_deployment_points(merges, latest_packages)

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

    def _get(obj: Any, key: str, default: Any = None) -> Any:
        """Helper to safely get attributes or dictionary keys."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if hasattr(obj, key) else default

    def _evaluate_trend(
        ctrl_id: str,
        req_dps: int,
        failing_percentage: int,
        prev_actual_implemented: dict[str, int] | None,
    ) -> str:
        if prev_actual_implemented is None or ctrl_id not in prev_actual_implemented:
            return "flat"
    
        prev_impl = prev_actual_implemented[ctrl_id]
        prev_failing_pct = 100
        if req_dps > 0:
            prev_failing_pct = round(((req_dps - prev_impl) / req_dps) * 100)
    
        if failing_percentage > prev_failing_pct:
            return "down"
        if failing_percentage < prev_failing_pct:
            return "up"
        return "flat"

    def calculate_gap_severity(failing_percentage: int, settings: Any) -> str:
        if failing_percentage > (1 - settings.compliance_score_low) * 100:
            return "High"
        if failing_percentage > (1 - settings.compliance_score_medium) * 100:
            return "Medium"
        return "Low"

    def calculate_framework_weight(
        ws: float, total_weight_score: float, idx: int, fw_count: int, allocated_weight: float
    ) -> tuple[float, float]:
        """Calculate the relative weight for a single framework."""
        if total_weight_score > 0:
            if idx == fw_count - 1:
                weight_val = 100 - allocated_weight
            else:
                weight_val = round((ws / total_weight_score) * 100)
                allocated_weight += weight_val
        else:
            weight_val = 100 // fw_count if fw_count > 0 else 0
            if idx == 0 and fw_count > 0:
                weight_val += 100 % fw_count
        return weight_val, allocated_weight

    def get_framework_status(readiness: float, settings: Any) -> str:
        """Determine framework compliance status based on score."""
        if readiness < (settings.compliance_score_low * 100):
            return "At Risk"
        if readiness <= (settings.compliance_score_medium * 100):
            return "Needs Attention"
        return "On Track"

    def _extract_control_weight(ctrl: Any) -> float:
        """Extract customer weightage from a control object."""
        custom = _get(ctrl, "customization") or {}
        weight_obj = _get(custom, "weightage") or {}
        return float(_get(weight_obj, "customer_weightage", 10.0))

    def calculate_fw_weight_score(
        fw_assignment_id: str, assignments: list[FrameworkAssignment]
    ) -> float:
        """Calculate dynamic framework weight based on assigned controls' customer_weightage."""
        fw_weight_score = 0.0
        if not fw_assignment_id:
            return fw_weight_score
    
        assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
        if not assignment or not assignment.fileVersions:
            return fw_weight_score
    
        latest_fv = assignment.fileVersions[-1]
        ai_ext = get_nested(latest_fv, "aiExtraction") or []
    
        for sec in ai_ext:
            for ctrl in get_nested(sec, "controls") or []:
                fw_weight_score += _extract_control_weight(ctrl)
    
        return fw_weight_score


    def get_latest_packages(dfs: list[DeploymentFramework]) -> tuple[list[dict], list[str], list[str]]:
        """Extract latest packages, gap analysis IDs, and merge document IDs."""
        latest_packages = []
        gap_analysis_ids = []
        merge_doc_ids = []
    
        for df in dfs:
            if not df.packages:
                continue
                
            latest_pkg = max(df.packages, key=lambda p: get_nested(p, "createdAt") or "")
    
            latest_packages.append({"df": df, "pkg": latest_pkg})
    
            gap_analysis = get_nested(latest_pkg, "gapAnalysis")
            if gap_analysis:
                gap_analysis_ids.append(str(gap_analysis))
    
            merge_doc = get_nested(latest_pkg, "mergeDocument")
            if merge_doc:
                merge_doc_ids.append(str(merge_doc))
    
        return latest_packages, gap_analysis_ids, merge_doc_ids

    def get_nested(obj: Any, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def extract_custom_controls(
        fw_assignment_id: str | None, assignments: list[FrameworkAssignment]
    ) -> dict[str, bool]:
        """Parse custom controls map from FrameworkAssignment."""
        custom_controls = {}
        if not fw_assignment_id:
            return custom_controls
    
        assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
        if not assignment or not assignment.fileVersions:
            return custom_controls
    
        latest_fv = assignment.fileVersions[-1]
        ai_extraction = _get(latest_fv, "aiExtraction") or []
        for sec in ai_extraction:
            for ctrl in _get(sec, "controls") or []:
                ctrl_id = _get(ctrl, "id")
                if ctrl_id:
                    is_custom = _get(_get(ctrl, "customization") or {}, "source") == "custom"
                    custom_controls[ctrl_id] = is_custom
    
        return custom_controls

    def extract_expected_controls(merge_doc: Any, custom_controls: dict[str, bool]) -> dict[str, Any]:
        """Parse expected controls and DPs from mergeDocument."""
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
                        "is_extra": custom_controls.get(ctrl_id, False),
                    }
        return expected_controls

    def extract_actual_implemented(gap_results: list[Any]) -> dict[str, int]:
        """Extract actual implemented counts from current gapAnalysis."""
        actual_implemented = {}
        for result in gap_results:
            ctrl_id = _get(result, "deployment_framework_control_id")
            if not ctrl_id:
                continue
            if ctrl_id not in actual_implemented:
                actual_implemented[ctrl_id] = 0
    
            status = str(_get(result, "implementation_status") or "").lower()
            if status in ["implemented", "compliant", "passed", "fully implemented"]:
                actual_implemented[ctrl_id] += 1
    
        return actual_implemented

    def extract_historical_implemented(
        df_id: str, current_created_at: datetime | None, historical_gap_analyses: list[Any]
    ) -> dict[str, int] | None:
        """Extract implemented counts from historical gapAnalysis for trend calculation. Returns None if no history exists."""
        if not df_id or not current_created_at:
            return None
    
        for hga in historical_gap_analyses:
            hga_df_id = _get(hga.gapAnalysis or {}, "deployment_framework_id")
            if hga_df_id == df_id and hga.createdAt and hga.createdAt < current_created_at:
                hga_results = _get(hga.gapAnalysis or {}, "deployment_gap_results") or []
                return extract_actual_implemented(hga_results)
    
        return None

    def calculate_fw_health_and_trend(
        fw_implemented_dps: int,
        fw_total_dps: int,
        prev_actual_implemented: Any,
        fw_prev_implemented_dps: int,
    ) -> tuple[float, float, bool]:
        """Calculate framework health and trend values."""
        fw_health = 0
        fw_prev_health = 0
        if fw_total_dps > 0:
            fw_health = round((fw_implemented_dps / fw_total_dps) * 100)
            if prev_actual_implemented is not None:
                fw_prev_health = round((fw_prev_implemented_dps / fw_total_dps) * 100)
            else:
                fw_prev_health = fw_health
    
        trend_val = fw_health - fw_prev_health
        trend_up = trend_val >= 0
        trend_abs = abs(trend_val)
    
        return fw_health, trend_abs, trend_up

    def _create_active_gap(
        ctrl_id: str,
        expected: dict,
        req_dps: int,
        impl_dps: int,
        prev_actual_implemented: dict[str, int] | None,
        ga: Any,
        fw_id: str,
        fw_name: str,
        fw_version: str,
        pkg_version: str,
        settings: Any,
    ) -> dict:
        failing_percentage = 100
        if req_dps > 0:
            failing_percentage = round(((req_dps - impl_dps) / req_dps) * 100)
    
        trend = _evaluate_trend(ctrl_id, req_dps, failing_percentage, prev_actual_implemented)
    
        return {
            "id": ctrl_id,
            "frameworkId": fw_id,
            "framework": fw_name,
            "version": fw_version,
            "packageVersion": pkg_version,
            "control": expected["name"],
            "description": expected["description"],
            "instances": req_dps,
            "failing": failing_percentage,
            "lastNC": ga.createdAt.isoformat() if ga and ga.createdAt else None,
            "trend": trend,
            "severity": calculate_gap_severity(failing_percentage, settings),
        }

    def evaluate_controls(
        expected_controls: dict[str, Any],
        actual_implemented: dict[str, int],
        prev_actual_implemented: dict[str, int] | None,
        ga: Any,
        fw_id: str,
        fw_name: str,
        fw_version: str,
        pkg_version: str,
        settings: Any,
    ) -> tuple[int, int, int, int, int, int, int, list[dict], int]:
        """Evaluate controls against implemented DPs and return aggregated metrics."""
        fw_total_controls = 0
        fw_passing_controls = 0
        fw_total_dps = 0
        fw_implemented_dps = 0
        fw_extra_controls = 0
        fw_extra_controls_list = []
        fw_critical_gaps = 0
        fw_active_gaps = []
        fw_prev_implemented_dps = 0
    
        for ctrl_id, expected in expected_controls.items():
            fw_total_controls += 1
            req_dps = expected["required_dps"]
    
            if expected["is_extra"]:
                fw_extra_controls += 1
                fw_extra_controls_list.append(
                    {
                        "id": fw_id,
                        "ctrlId": ctrl_id,
                        "control": expected["name"],
                        "frameworkVersion": fw_version,
                        "frameworkName": fw_name,
                        "deploymentPoints": req_dps,
                    }
                )
    
            impl_dps = actual_implemented.get(ctrl_id, 0)
            is_implemented = impl_dps > 0
            
            prev_impl = (
                prev_actual_implemented.get(ctrl_id, 0) if prev_actual_implemented is not None else 0
            )
            is_prev_implemented = prev_impl > 0
    
            # Now fw_total_dps represents total controls
            fw_total_dps += 1
            fw_implemented_dps += 1 if is_implemented else 0
            fw_prev_implemented_dps += 1 if is_prev_implemented else 0
    
            if is_implemented:
                fw_passing_controls += 1
            else:
                fw_critical_gaps += 1
                fw_active_gaps.append(
                    _create_active_gap(
                        ctrl_id,
                        expected,
                        req_dps,
                        req_dps if is_implemented else 0,
                        prev_actual_implemented,
                        ga,
                        fw_id,
                        fw_name,
                        fw_version,
                        pkg_version,
                        settings,
                    )
                )
    
        return (
            fw_total_controls,
            fw_passing_controls,
            fw_total_dps,
            fw_implemented_dps,
            fw_extra_controls,
            fw_extra_controls_list,
            fw_critical_gaps,
            fw_active_gaps,
            fw_prev_implemented_dps,
        )

    def process_gap_analyses(
        gap_analyses: list[PackageGapAnalysis],
        latest_packages: list[dict],
        historical_gap_analyses: list[PackageGapAnalysis],
        merges: list[DeploymentPackageMerge],
        assignments: list[FrameworkAssignment],
        settings: Any,
    ) -> tuple:
        """Extract and calculate gap analysis metrics."""
        total_controls_overall = 0
        passing_controls_overall = 0
        extra_controls_overall = 0
        extra_controls_list = []
        critical_gaps = 0
        active_gaps = []
        framework_health = []
        total_dps_overall = 0
        implemented_dps_overall = 0
        prev_implemented_dps_overall = 0
    
        for lp in latest_packages:
            ga_id = str(get_nested(lp["pkg"], "gapAnalysis"))
            merge_id = str(get_nested(lp["pkg"], "mergeDocument"))
    
            ga = next((g for g in gap_analyses if str(g.id) == ga_id), None)
            merge_doc = next((m for m in merges if str(m.id) == merge_id), None)
    
            if not ga or not merge_doc:
                continue
    
            gap_data = ga.gapAnalysis or {}
            df_id = get_nested(gap_data, "deployment_framework_id")
            fw_assignment_id = get_nested(gap_data, "framework_assignment_id")
    
            fw_name = lp["df"].frameworkName or UNKNOWN_FRAMEWORK
            fw_version = lp["df"].frameworkVersion or ""
            pkg_version = str(get_nested(lp["pkg"], "packageVersion") or "")
    
            custom_controls = extract_custom_controls(fw_assignment_id, assignments)
            expected_controls = extract_expected_controls(merge_doc, custom_controls)
    
            gap_results = get_nested(gap_data, "deployment_gap_results") or []
            actual_implemented = extract_actual_implemented(gap_results)
    
            prev_actual_implemented = extract_historical_implemented(
                df_id, ga.createdAt, historical_gap_analyses
            )
    
            (
                fw_total_controls,
                fw_passing_controls,
                fw_total_dps,
                fw_implemented_dps,
                fw_extra_controls,
                fw_extra_controls_list,
                fw_critical_gaps,
                fw_active_gaps,
                fw_prev_implemented_dps,
            ) = evaluate_controls(
                expected_controls,
                actual_implemented,
                prev_actual_implemented,
                ga,
                str(lp["df"].id),
                fw_name,
                fw_version,
                pkg_version,
                settings,
            )
    
            total_controls_overall += fw_total_controls
            passing_controls_overall += fw_passing_controls
            extra_controls_overall += fw_extra_controls
            extra_controls_list.extend(fw_extra_controls_list)
            total_dps_overall += fw_total_dps
            implemented_dps_overall += fw_implemented_dps
            if prev_actual_implemented is not None:
                prev_implemented_dps_overall += fw_prev_implemented_dps
            else:
                prev_implemented_dps_overall += fw_implemented_dps
    
            critical_gaps += fw_critical_gaps
            active_gaps.extend(fw_active_gaps)
    
            fw_health, trend_abs, trend_up = calculate_fw_health_and_trend(
                fw_implemented_dps, fw_total_dps, prev_actual_implemented, fw_prev_implemented_dps
            )
    
            fw_weight_score = calculate_fw_weight_score(fw_assignment_id, assignments)
    
            framework_health.append(
                {
                    "id": str(lp["df"].id),
                    "name": fw_name,
                    "version": fw_version,
                    "readiness": fw_health,
                    "weight_score": fw_weight_score,
                    "trend": trend_abs,
                    "trendUp": trend_up,
                }
            )
    
        return (
            total_controls_overall,
            passing_controls_overall,
            extra_controls_overall,
            extra_controls_list,
            critical_gaps,
            active_gaps,
            framework_health,
            total_dps_overall,
            implemented_dps_overall,
            prev_implemented_dps_overall,
        )

    def filter_and_sort_rows(
        rows: list[dict], search: str, status_filter: str, sort_by: str, sort_order: str
    ) -> list[dict]:
        """Apply search, status filter, and sorting to rows."""
        if search:
            s = search.lower()
            rows = [
                r
                for r in rows
                if s in r.get("framework", "").lower() or s in r.get("version", "").lower()
            ]
    
        if status_filter:
            rows = [r for r in rows if r.get("status") == status_filter]
    
        if sort_by:
            reverse = sort_order == "desc"
            rows.sort(
                key=lambda x: (
                    x.get(sort_by, 0)
                    if isinstance(x.get(sort_by), (int, float))
                    else x.get(sort_by, "")
                ),
                reverse=reverse,
            )
    
        return rows

    def build_overall_protection_rows(framework_health: list[dict], settings: Any) -> list[dict]:
        """Transform framework health into table rows with dynamic weight and status."""
        rows = []
        fw_count = len(framework_health)
        total_weight_score = sum(fw.get("weight_score", 0) for fw in framework_health)
    
        allocated_weight = 0
        for idx, fw in enumerate(framework_health):
            readiness = fw.get("readiness", 0)
            ws = fw.get("weight_score", 0)
            weight_val, allocated_weight = calculate_framework_weight(
                ws, total_weight_score, idx, fw_count, allocated_weight
            )
            status = get_framework_status(readiness, settings)
    
            rows.append(
                {
                    "id": fw.get("id"),
                    "version": fw.get("version", ""),
                    "framework": fw.get("name", ""),
                    "weight": weight_val,
                    "rawScore": readiness,
                    "contribution": round(weight_val * readiness / 100, 2),
                    "trend": fw.get("trend", 0),
                    "trendUp": fw.get("trendUp", True),
                    "status": status,
                }
            )
        return rows


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

            latest_packages, gap_analysis_ids, merge_doc_ids = get_latest_packages(dfs)

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

            settings = get_settings()
            (
                total_controls_overall,
                _,
                _,
                _,
                _, # Ignore extra_controls_list
                _,
                framework_health,
                total_dps_overall,
                implemented_dps_overall,
                prev_implemented_dps_overall,
            ) = process_gap_analyses(
                gap_analyses, latest_packages, historical_gap_analyses, merges, assignments, settings
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

            overall_trend_abs = abs(overall_trend_val)
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


@router.get("/critical-gaps")
async def get_auditor_critical_gaps(
    ctx: Annotated[RequestContext, Depends(get_context)],
    page: Annotated[int, Query(alias="page")] = 1,
    limit: Annotated[int, Query(alias="limit")] = 10,
    search: Annotated[str, Query(alias="search")] = "",
    severity_filter: Annotated[str, Query(alias="severityFilter")] = "",
    sort_by: Annotated[str, Query(alias="sortBy")] = "failingPct",
    sort_order: Annotated[str, Query(alias="sortOrder")] = "desc",
):

    def _get(obj: Any, key: str, default: Any = None) -> Any:
        """Helper to safely get attributes or dictionary keys."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if hasattr(obj, key) else default

    def _evaluate_trend(
        ctrl_id: str,
        req_dps: int,
        failing_percentage: int,
        prev_actual_implemented: dict[str, int] | None,
    ) -> str:
        if prev_actual_implemented is None or ctrl_id not in prev_actual_implemented:
            return "flat"
    
        prev_impl = prev_actual_implemented[ctrl_id]
        prev_failing_pct = 100
        if req_dps > 0:
            prev_failing_pct = round(((req_dps - prev_impl) / req_dps) * 100)
    
        if failing_percentage > prev_failing_pct:
            return "down"
        if failing_percentage < prev_failing_pct:
            return "up"
        return "flat"

    def calculate_gap_severity(failing_percentage: int, settings: Any) -> str:
        if failing_percentage > (1 - settings.compliance_score_low) * 100:
            return "High"
        if failing_percentage > (1 - settings.compliance_score_medium) * 100:
            return "Medium"
        return "Low"

    def _extract_control_weight(ctrl: Any) -> float:
        """Extract customer weightage from a control object."""
        custom = _get(ctrl, "customization") or {}
        weight_obj = _get(custom, "weightage") or {}
        return float(_get(weight_obj, "customer_weightage", 10.0))

    def calculate_fw_weight_score(
        fw_assignment_id: str, assignments: list[FrameworkAssignment]
    ) -> float:
        """Calculate dynamic framework weight based on assigned controls' customer_weightage."""
        fw_weight_score = 0.0
        if not fw_assignment_id:
            return fw_weight_score
    
        assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
        if not assignment or not assignment.fileVersions:
            return fw_weight_score
    
        latest_fv = assignment.fileVersions[-1]
        ai_ext = get_nested(latest_fv, "aiExtraction") or []
    
        for sec in ai_ext:
            for ctrl in get_nested(sec, "controls") or []:
                fw_weight_score += _extract_control_weight(ctrl)
    
        return fw_weight_score

    def get_latest_packages(dfs: list[DeploymentFramework]) -> tuple[list[dict], list[str], list[str]]:
        """Extract latest packages, gap analysis IDs, and merge document IDs."""
        latest_packages = []
        gap_analysis_ids = []
        merge_doc_ids = []
    
        for df in dfs:
            if not df.packages:
                continue
                
            latest_pkg = max(df.packages, key=lambda p: get_nested(p, "createdAt") or "")
    
            latest_packages.append({"df": df, "pkg": latest_pkg})
    
            gap_analysis = get_nested(latest_pkg, "gapAnalysis")
            if gap_analysis:
                gap_analysis_ids.append(str(gap_analysis))
    
            merge_doc = get_nested(latest_pkg, "mergeDocument")
            if merge_doc:
                merge_doc_ids.append(str(merge_doc))
    
        return latest_packages, gap_analysis_ids, merge_doc_ids

    def get_nested(obj: Any, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def extract_custom_controls(
        fw_assignment_id: str | None, assignments: list[FrameworkAssignment]
    ) -> dict[str, bool]:
        """Parse custom controls map from FrameworkAssignment."""
        custom_controls = {}
        if not fw_assignment_id:
            return custom_controls
    
        assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
        if not assignment or not assignment.fileVersions:
            return custom_controls
    
        latest_fv = assignment.fileVersions[-1]
        ai_extraction = _get(latest_fv, "aiExtraction") or []
        for sec in ai_extraction:
            for ctrl in _get(sec, "controls") or []:
                ctrl_id = _get(ctrl, "id")
                if ctrl_id:
                    is_custom = _get(_get(ctrl, "customization") or {}, "source") == "custom"
                    custom_controls[ctrl_id] = is_custom
    
        return custom_controls

    def extract_expected_controls(merge_doc: Any, custom_controls: dict[str, bool]) -> dict[str, Any]:
        """Parse expected controls and DPs from mergeDocument."""
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
                        "is_extra": custom_controls.get(ctrl_id, False),
                    }
        return expected_controls

    def extract_actual_implemented(gap_results: list[Any]) -> dict[str, int]:
        """Extract actual implemented counts from current gapAnalysis."""
        actual_implemented = {}
        for result in gap_results:
            ctrl_id = _get(result, "deployment_framework_control_id")
            if not ctrl_id:
                continue
            if ctrl_id not in actual_implemented:
                actual_implemented[ctrl_id] = 0
    
            status = str(_get(result, "implementation_status") or "").lower()
            if status in ["implemented", "compliant", "passed", "fully implemented"]:
                actual_implemented[ctrl_id] += 1
    
        return actual_implemented

    def extract_historical_implemented(
        df_id: str, current_created_at: datetime | None, historical_gap_analyses: list[Any]
    ) -> dict[str, int] | None:
        """Extract implemented counts from historical gapAnalysis for trend calculation. Returns None if no history exists."""
        if not df_id or not current_created_at:
            return None
    
        for hga in historical_gap_analyses:
            hga_df_id = _get(hga.gapAnalysis or {}, "deployment_framework_id")
            if hga_df_id == df_id and hga.createdAt and hga.createdAt < current_created_at:
                hga_results = _get(hga.gapAnalysis or {}, "deployment_gap_results") or []
                return extract_actual_implemented(hga_results)
    
        return None

    def calculate_fw_health_and_trend(
        fw_implemented_dps: int,
        fw_total_dps: int,
        prev_actual_implemented: Any,
        fw_prev_implemented_dps: int,
    ) -> tuple[float, float, bool]:
        """Calculate framework health and trend values."""
        fw_health = 0
        fw_prev_health = 0
        if fw_total_dps > 0:
            fw_health = round((fw_implemented_dps / fw_total_dps) * 100)
            if prev_actual_implemented is not None:
                fw_prev_health = round((fw_prev_implemented_dps / fw_total_dps) * 100)
            else:
                fw_prev_health = fw_health
    
        trend_val = fw_health - fw_prev_health
        trend_up = trend_val >= 0
        trend_abs = abs(trend_val)
    
        return fw_health, trend_abs, trend_up

    def _create_active_gap(
        ctrl_id: str,
        expected: dict,
        req_dps: int,
        impl_dps: int,
        prev_actual_implemented: dict[str, int] | None,
        ga: Any,
        fw_id: str,
        fw_name: str,
        fw_version: str,
        pkg_version: str,
        settings: Any,
    ) -> dict:
        failing_percentage = 100
        if req_dps > 0:
            failing_percentage = round(((req_dps - impl_dps) / req_dps) * 100)
    
        trend = _evaluate_trend(ctrl_id, req_dps, failing_percentage, prev_actual_implemented)
    
        return {
            "id": ctrl_id,
            "frameworkId": fw_id,
            "framework": fw_name,
            "version": fw_version,
            "packageVersion": pkg_version,
            "control": expected["name"],
            "description": expected["description"],
            "instances": req_dps,
            "failing": failing_percentage,
            "lastNC": ga.createdAt.isoformat() if ga and ga.createdAt else None,
            "trend": trend,
            "severity": calculate_gap_severity(failing_percentage, settings),
        }

    def evaluate_controls(
        expected_controls: dict[str, Any],
        actual_implemented: dict[str, int],
        prev_actual_implemented: dict[str, int] | None,
        ga: Any,
        fw_id: str,
        fw_name: str,
        fw_version: str,
        pkg_version: str,
        settings: Any,
    ) -> tuple[int, int, int, int, int, int, int, list[dict], int]:
        """Evaluate controls against implemented DPs and return aggregated metrics."""
        fw_total_controls = 0
        fw_passing_controls = 0
        fw_total_dps = 0
        fw_implemented_dps = 0
        fw_extra_controls = 0
        fw_extra_controls_list = []
        fw_critical_gaps = 0
        fw_active_gaps = []
        fw_prev_implemented_dps = 0
    
        for ctrl_id, expected in expected_controls.items():
            fw_total_controls += 1
            req_dps = expected["required_dps"]
    
            if expected["is_extra"]:
                fw_extra_controls += 1
                fw_extra_controls_list.append(
                    {
                        "id": fw_id,
                        "ctrlId": ctrl_id,
                        "control": expected["name"],
                        "frameworkVersion": fw_version,
                        "frameworkName": fw_name,
                        "deploymentPoints": req_dps,
                    }
                )
    
            impl_dps = actual_implemented.get(ctrl_id, 0)
            is_implemented = impl_dps > 0
            
            prev_impl = (
                prev_actual_implemented.get(ctrl_id, 0) if prev_actual_implemented is not None else 0
            )
            is_prev_implemented = prev_impl > 0
    
            # Now fw_total_dps represents total controls
            fw_total_dps += 1
            fw_implemented_dps += 1 if is_implemented else 0
            fw_prev_implemented_dps += 1 if is_prev_implemented else 0
    
            if is_implemented:
                fw_passing_controls += 1
            else:
                fw_critical_gaps += 1
                fw_active_gaps.append(
                    _create_active_gap(
                        ctrl_id,
                        expected,
                        req_dps,
                        req_dps if is_implemented else 0,
                        prev_actual_implemented,
                        ga,
                        fw_id,
                        fw_name,
                        fw_version,
                        pkg_version,
                        settings,
                    )
                )
    
        return (
            fw_total_controls,
            fw_passing_controls,
            fw_total_dps,
            fw_implemented_dps,
            fw_extra_controls,
            fw_extra_controls_list,
            fw_critical_gaps,
            fw_active_gaps,
            fw_prev_implemented_dps,
        )

    def calculate_control_status(pass_rate: int, settings: Any) -> str:
        if pass_rate == 100:
            return "Passing"
        if pass_rate >= (settings.compliance_score_medium * 100):
            return "Warning"
        return "Failing"

    def process_gap_analyses(
        gap_analyses: list[PackageGapAnalysis],
        latest_packages: list[dict],
        historical_gap_analyses: list[PackageGapAnalysis],
        merges: list[DeploymentPackageMerge],
        assignments: list[FrameworkAssignment],
        settings: Any,
    ) -> tuple:
        """Extract and calculate gap analysis metrics."""
        total_controls_overall = 0
        passing_controls_overall = 0
        extra_controls_overall = 0
        extra_controls_list = []
        critical_gaps = 0
        active_gaps = []
        framework_health = []
        total_dps_overall = 0
        implemented_dps_overall = 0
        prev_implemented_dps_overall = 0
    
        for lp in latest_packages:
            ga_id = str(get_nested(lp["pkg"], "gapAnalysis"))
            merge_id = str(get_nested(lp["pkg"], "mergeDocument"))
    
            ga = next((g for g in gap_analyses if str(g.id) == ga_id), None)
            merge_doc = next((m for m in merges if str(m.id) == merge_id), None)
    
            if not ga or not merge_doc:
                continue
    
            gap_data = ga.gapAnalysis or {}
            df_id = get_nested(gap_data, "deployment_framework_id")
            fw_assignment_id = get_nested(gap_data, "framework_assignment_id")
    
            fw_name = lp["df"].frameworkName or UNKNOWN_FRAMEWORK
            fw_version = lp["df"].frameworkVersion or ""
            pkg_version = str(get_nested(lp["pkg"], "packageVersion") or "")
    
            custom_controls = extract_custom_controls(fw_assignment_id, assignments)
            expected_controls = extract_expected_controls(merge_doc, custom_controls)
    
            gap_results = get_nested(gap_data, "deployment_gap_results") or []
            actual_implemented = extract_actual_implemented(gap_results)
    
            prev_actual_implemented = extract_historical_implemented(
                df_id, ga.createdAt, historical_gap_analyses
            )
    
            (
                fw_total_controls,
                fw_passing_controls,
                fw_total_dps,
                fw_implemented_dps,
                fw_extra_controls,
                fw_extra_controls_list,
                fw_critical_gaps,
                fw_active_gaps,
                fw_prev_implemented_dps,
            ) = evaluate_controls(
                expected_controls,
                actual_implemented,
                prev_actual_implemented,
                ga,
                str(lp["df"].id),
                fw_name,
                fw_version,
                pkg_version,
                settings,
            )
    
            total_controls_overall += fw_total_controls
            passing_controls_overall += fw_passing_controls
            extra_controls_overall += fw_extra_controls
            extra_controls_list.extend(fw_extra_controls_list)
            total_dps_overall += fw_total_dps
            implemented_dps_overall += fw_implemented_dps
            if prev_actual_implemented is not None:
                prev_implemented_dps_overall += fw_prev_implemented_dps
            else:
                prev_implemented_dps_overall += fw_implemented_dps
    
            critical_gaps += fw_critical_gaps
            active_gaps.extend(fw_active_gaps)
    
            fw_health, trend_abs, trend_up = calculate_fw_health_and_trend(
                fw_implemented_dps, fw_total_dps, prev_actual_implemented, fw_prev_implemented_dps
            )
    
            fw_weight_score = calculate_fw_weight_score(fw_assignment_id, assignments)
    
            framework_health.append(
                {
                    "id": str(lp["df"].id),
                    "name": fw_name,
                    "version": fw_version,
                    "readiness": fw_health,
                    "weight_score": fw_weight_score,
                    "trend": trend_abs,
                    "trendUp": trend_up,
                }
            )
    
        return (
            total_controls_overall,
            passing_controls_overall,
            extra_controls_overall,
            extra_controls_list,
            critical_gaps,
            active_gaps,
            framework_health,
            total_dps_overall,
            implemented_dps_overall,
            prev_implemented_dps_overall,
        )

    def build_critical_gaps_response(
        active_gaps: list[dict],
        search: str,
        severity_filter: str,
        sort_by: str,
        sort_order: str,
        page: int,
        limit: int,
    ) -> tuple:
        formatted = []
        high = 0
        medium = 0
        low = 0
    
        for g in active_gaps:
            sev = g.get("severity", "Low")
            if sev == "High":
                high += 1
            elif sev == "Medium":
                medium += 1
            else:
                low += 1
    
            formatted.append(
                {
                    "id": g.get("frameworkId"),
                    "frameworkVersion": g["version"],
                    "frameworkName": g["framework"],
                    "ctrlNo": g["id"],
                    "controlName": g["control"],
                    "instances": g["instances"],
                    "failingPct": f"{g['failing']}%",
                    "failingRaw": g["failing"],
                    "severity": sev,
                }
            )
    
        if severity_filter:
            s_filter = severity_filter.lower()
            formatted = [f for f in formatted if f["severity"].lower() == s_filter]
    
        if search:
            q = search.lower()
            formatted = [
                f
                for f in formatted
                if q in f["ctrlNo"].lower()
                or q in f["controlName"].lower()
                or q in f["frameworkName"].lower()
            ]
    
        if sort_by:
            reverse = sort_order == "desc"
            # Since 'failingPct' is a string like '9%', sort by the raw value
            actual_sort_key = "failingRaw" if sort_by == "failingPct" else sort_by
            formatted.sort(
                key=lambda x: (
                    x.get(actual_sort_key, 0)
                    if isinstance(x.get(actual_sort_key), (int, float))
                    else x.get(actual_sort_key, "")
                ),
                reverse=reverse,
            )
    
        total = len(formatted)
    
        # Calculate pagination slice bounds, clamping page and limit.
        from vora_shared.query_builder import clamp_page, clamp_limit
    
        safe_page = clamp_page(page)
        safe_limit = clamp_limit(limit)
        start = (safe_page - 1) * safe_limit
        end = start + safe_limit
    
        return {
            "results": formatted[start:end],
            "stats": {"priorities": {"high": high, "medium": medium, "low": low}},
        }, total


    """Get auditor critical gaps for dashboard table."""
    try:
        async with session_scope() as session:
            dfs = list((await session.execute(
                select(DeploymentFramework).where(DeploymentFramework.tenantId == ctx.tenant_id)
            )).scalars().all())

            latest_packages, gap_analysis_ids, merge_doc_ids = get_latest_packages(dfs)

            gap_analyses = list((await session.execute(
                select(PackageGapAnalysis).where(PackageGapAnalysis.id.in_(gap_analysis_ids))
            )).scalars().all()) if gap_analysis_ids else []

            merges = list((await session.execute(
                select(DeploymentPackageMerge).where(DeploymentPackageMerge.id.in_(merge_doc_ids))
            )).scalars().all()) if merge_doc_ids else []

            assignment_ids = [
                get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
                for ga in gap_analyses
                if get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
            ]

            assignments = list((await session.execute(
                select(FrameworkAssignment).where(FrameworkAssignment.id.in_(assignment_ids))
            )).scalars().all()) if assignment_ids else []

            historical_gap_analysis_ids = [
                get_nested(pkg, "gapAnalysis")
                for df in dfs
                for pkg in (df.packages or [])
                if get_nested(pkg, "gapAnalysis")
            ]

            historical_gap_analyses = list((await session.execute(
                select(PackageGapAnalysis)
                .where(PackageGapAnalysis.id.in_(historical_gap_analysis_ids))
                .order_by(desc(PackageGapAnalysis.createdAt))
            )).scalars().all()) if historical_gap_analysis_ids else []

            settings = get_settings()
            # We only need active_gaps, but process_gap_analyses returns a big tuple
            res = process_gap_analyses(
                gap_analyses, latest_packages, historical_gap_analyses, merges, assignments, settings
            )
            active_gaps = res[5]

            # Build and paginate rows using helper
            data, total_items = build_critical_gaps_response(
                active_gaps, search, severity_filter, sort_by, sort_order, page, limit
            )
            
            return paginated(
                data,
                build_pagination_meta(clamp_page(page), clamp_limit(limit), total_items),
                "Critical gaps retrieved successfully"
            )

    except Exception:
        logger.exception("Error in critical gaps")
        return server_error("Failed to fetch critical gaps")


@router.get("/controls-passing")
async def get_auditor_controls_passing(
    ctx: Annotated[RequestContext, Depends(get_context)],
    page: Annotated[int, Query(alias="page")] = 1,
    limit: Annotated[int, Query(alias="limit")] = 10,
    search: Annotated[str, Query(alias="search")] = "",
    status_filter: Annotated[str, Query(alias="statusFilter")] = "",
    sort_by: Annotated[str, Query(alias="sortBy")] = "ctrlId",
    sort_order: Annotated[str, Query(alias="sortOrder")] = "asc",
):

    def _get(obj: Any, key: str, default: Any = None) -> Any:
        """Helper to safely get attributes or dictionary keys."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if hasattr(obj, key) else default

    def get_latest_packages(dfs: list[DeploymentFramework]) -> tuple[list[dict], list[str], list[str]]:
        """Extract latest packages, gap analysis IDs, and merge document IDs."""
        latest_packages = []
        gap_analysis_ids = []
        merge_doc_ids = []
    
        for df in dfs:
            if not df.packages:
                continue
                
            latest_pkg = max(df.packages, key=lambda p: get_nested(p, "createdAt") or "")
    
            latest_packages.append({"df": df, "pkg": latest_pkg})
    
            gap_analysis = get_nested(latest_pkg, "gapAnalysis")
            if gap_analysis:
                gap_analysis_ids.append(str(gap_analysis))
    
            merge_doc = get_nested(latest_pkg, "mergeDocument")
            if merge_doc:
                merge_doc_ids.append(str(merge_doc))
    
        return latest_packages, gap_analysis_ids, merge_doc_ids

    def get_nested(obj: Any, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def extract_custom_controls(
        fw_assignment_id: str | None, assignments: list[FrameworkAssignment]
    ) -> dict[str, bool]:
        """Parse custom controls map from FrameworkAssignment."""
        custom_controls = {}
        if not fw_assignment_id:
            return custom_controls
    
        assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
        if not assignment or not assignment.fileVersions:
            return custom_controls
    
        latest_fv = assignment.fileVersions[-1]
        ai_extraction = _get(latest_fv, "aiExtraction") or []
        for sec in ai_extraction:
            for ctrl in _get(sec, "controls") or []:
                ctrl_id = _get(ctrl, "id")
                if ctrl_id:
                    is_custom = _get(_get(ctrl, "customization") or {}, "source") == "custom"
                    custom_controls[ctrl_id] = is_custom
    
        return custom_controls

    def extract_expected_controls(merge_doc: Any, custom_controls: dict[str, bool]) -> dict[str, Any]:
        """Parse expected controls and DPs from mergeDocument."""
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
                        "is_extra": custom_controls.get(ctrl_id, False),
                    }
        return expected_controls

    def extract_actual_implemented(gap_results: list[Any]) -> dict[str, int]:
        """Extract actual implemented counts from current gapAnalysis."""
        actual_implemented = {}
        for result in gap_results:
            ctrl_id = _get(result, "deployment_framework_control_id")
            if not ctrl_id:
                continue
            if ctrl_id not in actual_implemented:
                actual_implemented[ctrl_id] = 0
    
            status = str(_get(result, "implementation_status") or "").lower()
            if status in ["implemented", "compliant", "passed", "fully implemented"]:
                actual_implemented[ctrl_id] += 1
    
        return actual_implemented

    def _process_package_controls(
        expected_controls: dict,
        actual_implemented: dict,
        fw_id: str,
        fw_name: str,
        fw_version: str,
        ga_created_at: Any,
        stats: dict,
    ) -> list[dict]:
        formatted = []
        for ctrl_id, expected in expected_controls.items():
            stats["total"] += 1
            req_dps = expected["required_dps"]
            is_implemented = actual_implemented.get(ctrl_id, 0) > 0
    
            if is_implemented:
                pass_rate = 100
                status = "Passing"
                stats["passing"] += 1
            else:
                pass_rate = 0
                status = "Failing"
                stats["failing"] += 1
    
            formatted.append(
                {
                    "id": fw_id,
                    "ctrlId": ctrl_id,
                    "control": expected["name"],
                    "frameworkVersion": fw_version,
                    "frameworkName": fw_name,
                    "section": expected.get("section", "General"),
                    "instances": req_dps,
                    "passRate": pass_rate,
                    "status": status,
                    "lastRun": ga_created_at.isoformat() if ga_created_at else None,
                }
            )
        return formatted

    def _filter_and_sort_controls(
        formatted: list[dict], search: str, status_filter: str, sort_by: str, sort_order: str
    ) -> list[dict]:
        if status_filter:
            s_filter = status_filter.lower()
            formatted = [f for f in formatted if f["status"].lower() == s_filter]
    
        if search:
            q = search.lower()
            formatted = [
                f
                for f in formatted
                if q in f["ctrlId"].lower()
                or q in f["control"].lower()
                or q in f["frameworkName"].lower()
            ]
    
        if sort_by:
            reverse = sort_order == "desc"
            formatted.sort(
                key=lambda x: (
                    x.get(sort_by, 0)
                    if isinstance(x.get(sort_by), (int, float))
                    else x.get(sort_by, "")
                ),
                reverse=reverse,
            )
        return formatted

    def build_controls_passing_response(
        gap_analyses: list[PackageGapAnalysis],
        latest_packages: list[dict],
        merges: list[DeploymentPackageMerge],
        assignments: list[FrameworkAssignment],
        settings: Any,
        search: str,
        status_filter: str,
        sort_by: str,
        sort_order: str,
        page: int,
        limit: int,
    ) -> tuple:
        formatted = []
        stats = {"passing": 0, "warning": 0, "failing": 0, "not_evaluated": 0, "total": 0}
    
        for lp in latest_packages:
            ga_id = str(get_nested(lp["pkg"], "gapAnalysis"))
            merge_id = str(get_nested(lp["pkg"], "mergeDocument"))
    
            ga = next((g for g in gap_analyses if str(g.id) == ga_id), None)
            merge_doc = next((m for m in merges if str(m.id) == merge_id), None)
    
            if not ga or not merge_doc:
                continue
    
            gap_data = ga.gapAnalysis or {}
            fw_assignment_id = get_nested(gap_data, "framework_assignment_id")
            fw_name = lp["df"].frameworkName or UNKNOWN_FRAMEWORK
            fw_version = lp["df"].frameworkVersion or ""
    
            custom_controls = extract_custom_controls(fw_assignment_id, assignments)
            expected_controls = extract_expected_controls(merge_doc, custom_controls)
    
            gap_results = get_nested(gap_data, "deployment_gap_results") or []
            actual_implemented = extract_actual_implemented(gap_results)
    
            formatted.extend(
                _process_package_controls(
                    expected_controls,
                    actual_implemented,
                    str(lp["df"].id),
                    fw_name,
                    fw_version,
                    ga.createdAt if ga else None,
                    stats,
                )
            )
    
        formatted = _filter_and_sort_controls(formatted, search, status_filter, sort_by, sort_order)
    
        total = len(formatted)
    
        from vora_shared.query_builder import clamp_page, clamp_limit
    
        safe_page = clamp_page(page)
        safe_limit = clamp_limit(limit)
        start = (safe_page - 1) * safe_limit
        end = start + safe_limit
    
        overall_pass_rate = 0
        if stats["total"] > 0:
            overall_pass_rate = round((stats["passing"] / stats["total"]) * 100)
    
        return {
            "results": formatted[start:end],
            "stats": {
                "passing": stats["passing"],
                "failing": stats["failing"],
                "warning": stats["warning"],
                "notEvaluated": stats["not_evaluated"],
                "passRate": overall_pass_rate,
                "failingOrEvidence": stats["failing"] + stats["warning"],
            },
        }, total


    """Get auditor controls passing for dashboard table."""
    try:
        settings = get_settings()
        
        async with session_scope() as session:
            dfs = list((await session.execute(
                select(DeploymentFramework).where(DeploymentFramework.tenantId == ctx.tenant_id)
            )).scalars().all())

            latest_packages, gap_analysis_ids, merge_doc_ids = get_latest_packages(dfs)

            gap_analyses = list((await session.execute(
                select(PackageGapAnalysis).where(PackageGapAnalysis.id.in_(gap_analysis_ids))
            )).scalars().all()) if gap_analysis_ids else []

            merges = list((await session.execute(
                select(DeploymentPackageMerge).where(DeploymentPackageMerge.id.in_(merge_doc_ids))
            )).scalars().all()) if merge_doc_ids else []

            assignment_ids = [
                get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
                for ga in gap_analyses
                if get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
            ]

            assignments = list((await session.execute(
                select(FrameworkAssignment).where(FrameworkAssignment.id.in_(assignment_ids))
            )).scalars().all()) if assignment_ids else []

            data, total_items = build_controls_passing_response(
                gap_analyses,
                latest_packages,
                merges,
                assignments,
                settings,
                search,
                status_filter,
                sort_by,
                sort_order,
                page,
                limit
            )
            
            return paginated(
                data,
                build_pagination_meta(clamp_page(page), clamp_limit(limit), total_items),
                "Controls passing retrieved successfully"
            )

    except Exception:
        logger.exception("Error in controls passing")
        return server_error("Failed to fetch controls passing")


@router.get("/extra-controls")
async def get_auditor_extra_controls(
    ctx: Annotated[RequestContext, Depends(get_context)],
    page: Annotated[int, Query(alias="page")] = 1,
    limit: Annotated[int, Query(alias="limit")] = 10,
    search: Annotated[str, Query(alias="search")] = "",
    sort_by: Annotated[str, Query(alias="sortBy")] = "createdAt",
    sort_order: Annotated[str, Query(alias="sortOrder")] = "desc",
):

    def _get(obj: Any, key: str, default: Any = None) -> Any:
        """Helper to safely get attributes or dictionary keys."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if hasattr(obj, key) else default

    def _evaluate_trend(
        ctrl_id: str,
        req_dps: int,
        failing_percentage: int,
        prev_actual_implemented: dict[str, int] | None,
    ) -> str:
        if prev_actual_implemented is None or ctrl_id not in prev_actual_implemented:
            return "flat"
    
        prev_impl = prev_actual_implemented[ctrl_id]
        prev_failing_pct = 100
        if req_dps > 0:
            prev_failing_pct = round(((req_dps - prev_impl) / req_dps) * 100)
    
        if failing_percentage > prev_failing_pct:
            return "down"
        if failing_percentage < prev_failing_pct:
            return "up"
        return "flat"

    def calculate_gap_severity(failing_percentage: int, settings: Any) -> str:
        if failing_percentage > (1 - settings.compliance_score_low) * 100:
            return "High"
        if failing_percentage > (1 - settings.compliance_score_medium) * 100:
            return "Medium"
        return "Low"

    def _extract_control_weight(ctrl: Any) -> float:
        """Extract customer weightage from a control object."""
        custom = _get(ctrl, "customization") or {}
        weight_obj = _get(custom, "weightage") or {}
        return float(_get(weight_obj, "customer_weightage", 10.0))

    def calculate_fw_weight_score(
        fw_assignment_id: str, assignments: list[FrameworkAssignment]
    ) -> float:
        """Calculate dynamic framework weight based on assigned controls' customer_weightage."""
        fw_weight_score = 0.0
        if not fw_assignment_id:
            return fw_weight_score
    
        assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
        if not assignment or not assignment.fileVersions:
            return fw_weight_score
    
        latest_fv = assignment.fileVersions[-1]
        ai_ext = get_nested(latest_fv, "aiExtraction") or []
    
        for sec in ai_ext:
            for ctrl in get_nested(sec, "controls") or []:
                fw_weight_score += _extract_control_weight(ctrl)
    
        return fw_weight_score

    def get_latest_packages(dfs: list[DeploymentFramework]) -> tuple[list[dict], list[str], list[str]]:
        """Extract latest packages, gap analysis IDs, and merge document IDs."""
        latest_packages = []
        gap_analysis_ids = []
        merge_doc_ids = []
    
        for df in dfs:
            if not df.packages:
                continue
                
            latest_pkg = max(df.packages, key=lambda p: get_nested(p, "createdAt") or "")
    
            latest_packages.append({"df": df, "pkg": latest_pkg})
    
            gap_analysis = get_nested(latest_pkg, "gapAnalysis")
            if gap_analysis:
                gap_analysis_ids.append(str(gap_analysis))
    
            merge_doc = get_nested(latest_pkg, "mergeDocument")
            if merge_doc:
                merge_doc_ids.append(str(merge_doc))
    
        return latest_packages, gap_analysis_ids, merge_doc_ids

    def get_nested(obj: Any, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def extract_custom_controls(
        fw_assignment_id: str | None, assignments: list[FrameworkAssignment]
    ) -> dict[str, bool]:
        """Parse custom controls map from FrameworkAssignment."""
        custom_controls = {}
        if not fw_assignment_id:
            return custom_controls
    
        assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
        if not assignment or not assignment.fileVersions:
            return custom_controls
    
        latest_fv = assignment.fileVersions[-1]
        ai_extraction = _get(latest_fv, "aiExtraction") or []
        for sec in ai_extraction:
            for ctrl in _get(sec, "controls") or []:
                ctrl_id = _get(ctrl, "id")
                if ctrl_id:
                    is_custom = _get(_get(ctrl, "customization") or {}, "source") == "custom"
                    custom_controls[ctrl_id] = is_custom
    
        return custom_controls

    def extract_expected_controls(merge_doc: Any, custom_controls: dict[str, bool]) -> dict[str, Any]:
        """Parse expected controls and DPs from mergeDocument."""
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
                        "is_extra": custom_controls.get(ctrl_id, False),
                    }
        return expected_controls

    def extract_actual_implemented(gap_results: list[Any]) -> dict[str, int]:
        """Extract actual implemented counts from current gapAnalysis."""
        actual_implemented = {}
        for result in gap_results:
            ctrl_id = _get(result, "deployment_framework_control_id")
            if not ctrl_id:
                continue
            if ctrl_id not in actual_implemented:
                actual_implemented[ctrl_id] = 0
    
            status = str(_get(result, "implementation_status") or "").lower()
            if status in ["implemented", "compliant", "passed", "fully implemented"]:
                actual_implemented[ctrl_id] += 1
    
        return actual_implemented

    def extract_historical_implemented(
        df_id: str, current_created_at: datetime | None, historical_gap_analyses: list[Any]
    ) -> dict[str, int] | None:
        """Extract implemented counts from historical gapAnalysis for trend calculation. Returns None if no history exists."""
        if not df_id or not current_created_at:
            return None
    
        for hga in historical_gap_analyses:
            hga_df_id = _get(hga.gapAnalysis or {}, "deployment_framework_id")
            if hga_df_id == df_id and hga.createdAt and hga.createdAt < current_created_at:
                hga_results = _get(hga.gapAnalysis or {}, "deployment_gap_results") or []
                return extract_actual_implemented(hga_results)
    
        return None

    def calculate_fw_health_and_trend(
        fw_implemented_dps: int,
        fw_total_dps: int,
        prev_actual_implemented: Any,
        fw_prev_implemented_dps: int,
    ) -> tuple[float, float, bool]:
        """Calculate framework health and trend values."""
        fw_health = 0
        fw_prev_health = 0
        if fw_total_dps > 0:
            fw_health = round((fw_implemented_dps / fw_total_dps) * 100)
            if prev_actual_implemented is not None:
                fw_prev_health = round((fw_prev_implemented_dps / fw_total_dps) * 100)
            else:
                fw_prev_health = fw_health
    
        trend_val = fw_health - fw_prev_health
        trend_up = trend_val >= 0
        trend_abs = abs(trend_val)
    
        return fw_health, trend_abs, trend_up

    def _create_active_gap(
        ctrl_id: str,
        expected: dict,
        req_dps: int,
        impl_dps: int,
        prev_actual_implemented: dict[str, int] | None,
        ga: Any,
        fw_id: str,
        fw_name: str,
        fw_version: str,
        pkg_version: str,
        settings: Any,
    ) -> dict:
        failing_percentage = 100
        if req_dps > 0:
            failing_percentage = round(((req_dps - impl_dps) / req_dps) * 100)
    
        trend = _evaluate_trend(ctrl_id, req_dps, failing_percentage, prev_actual_implemented)
    
        return {
            "id": ctrl_id,
            "frameworkId": fw_id,
            "framework": fw_name,
            "version": fw_version,
            "packageVersion": pkg_version,
            "control": expected["name"],
            "description": expected["description"],
            "instances": req_dps,
            "failing": failing_percentage,
            "lastNC": ga.createdAt.isoformat() if ga and ga.createdAt else None,
            "trend": trend,
            "severity": calculate_gap_severity(failing_percentage, settings),
        }

    def evaluate_controls(
        expected_controls: dict[str, Any],
        actual_implemented: dict[str, int],
        prev_actual_implemented: dict[str, int] | None,
        ga: Any,
        fw_id: str,
        fw_name: str,
        fw_version: str,
        pkg_version: str,
        settings: Any,
    ) -> tuple[int, int, int, int, int, int, int, list[dict], int]:
        """Evaluate controls against implemented DPs and return aggregated metrics."""
        fw_total_controls = 0
        fw_passing_controls = 0
        fw_total_dps = 0
        fw_implemented_dps = 0
        fw_extra_controls = 0
        fw_extra_controls_list = []
        fw_critical_gaps = 0
        fw_active_gaps = []
        fw_prev_implemented_dps = 0
    
        for ctrl_id, expected in expected_controls.items():
            fw_total_controls += 1
            req_dps = expected["required_dps"]
    
            if expected["is_extra"]:
                fw_extra_controls += 1
                fw_extra_controls_list.append(
                    {
                        "id": fw_id,
                        "ctrlId": ctrl_id,
                        "control": expected["name"],
                        "frameworkVersion": fw_version,
                        "frameworkName": fw_name,
                        "deploymentPoints": req_dps,
                    }
                )
    
            impl_dps = actual_implemented.get(ctrl_id, 0)
            is_implemented = impl_dps > 0
            
            prev_impl = (
                prev_actual_implemented.get(ctrl_id, 0) if prev_actual_implemented is not None else 0
            )
            is_prev_implemented = prev_impl > 0
    
            # Now fw_total_dps represents total controls
            fw_total_dps += 1
            fw_implemented_dps += 1 if is_implemented else 0
            fw_prev_implemented_dps += 1 if is_prev_implemented else 0
    
            if is_implemented:
                fw_passing_controls += 1
            else:
                fw_critical_gaps += 1
                fw_active_gaps.append(
                    _create_active_gap(
                        ctrl_id,
                        expected,
                        req_dps,
                        req_dps if is_implemented else 0,
                        prev_actual_implemented,
                        ga,
                        fw_id,
                        fw_name,
                        fw_version,
                        pkg_version,
                        settings,
                    )
                )
    
        return (
            fw_total_controls,
            fw_passing_controls,
            fw_total_dps,
            fw_implemented_dps,
            fw_extra_controls,
            fw_extra_controls_list,
            fw_critical_gaps,
            fw_active_gaps,
            fw_prev_implemented_dps,
        )

    def process_gap_analyses(
        gap_analyses: list[PackageGapAnalysis],
        latest_packages: list[dict],
        historical_gap_analyses: list[PackageGapAnalysis],
        merges: list[DeploymentPackageMerge],
        assignments: list[FrameworkAssignment],
        settings: Any,
    ) -> tuple:
        """Extract and calculate gap analysis metrics."""
        total_controls_overall = 0
        passing_controls_overall = 0
        extra_controls_overall = 0
        extra_controls_list = []
        critical_gaps = 0
        active_gaps = []
        framework_health = []
        total_dps_overall = 0
        implemented_dps_overall = 0
        prev_implemented_dps_overall = 0
    
        for lp in latest_packages:
            ga_id = str(get_nested(lp["pkg"], "gapAnalysis"))
            merge_id = str(get_nested(lp["pkg"], "mergeDocument"))
    
            ga = next((g for g in gap_analyses if str(g.id) == ga_id), None)
            merge_doc = next((m for m in merges if str(m.id) == merge_id), None)
    
            if not ga or not merge_doc:
                continue
    
            gap_data = ga.gapAnalysis or {}
            df_id = get_nested(gap_data, "deployment_framework_id")
            fw_assignment_id = get_nested(gap_data, "framework_assignment_id")
    
            fw_name = lp["df"].frameworkName or UNKNOWN_FRAMEWORK
            fw_version = lp["df"].frameworkVersion or ""
            pkg_version = str(get_nested(lp["pkg"], "packageVersion") or "")
    
            custom_controls = extract_custom_controls(fw_assignment_id, assignments)
            expected_controls = extract_expected_controls(merge_doc, custom_controls)
    
            gap_results = get_nested(gap_data, "deployment_gap_results") or []
            actual_implemented = extract_actual_implemented(gap_results)
    
            prev_actual_implemented = extract_historical_implemented(
                df_id, ga.createdAt, historical_gap_analyses
            )
    
            (
                fw_total_controls,
                fw_passing_controls,
                fw_total_dps,
                fw_implemented_dps,
                fw_extra_controls,
                fw_extra_controls_list,
                fw_critical_gaps,
                fw_active_gaps,
                fw_prev_implemented_dps,
            ) = evaluate_controls(
                expected_controls,
                actual_implemented,
                prev_actual_implemented,
                ga,
                str(lp["df"].id),
                fw_name,
                fw_version,
                pkg_version,
                settings,
            )
    
            total_controls_overall += fw_total_controls
            passing_controls_overall += fw_passing_controls
            extra_controls_overall += fw_extra_controls
            extra_controls_list.extend(fw_extra_controls_list)
            total_dps_overall += fw_total_dps
            implemented_dps_overall += fw_implemented_dps
            if prev_actual_implemented is not None:
                prev_implemented_dps_overall += fw_prev_implemented_dps
            else:
                prev_implemented_dps_overall += fw_implemented_dps
    
            critical_gaps += fw_critical_gaps
            active_gaps.extend(fw_active_gaps)
    
            fw_health, trend_abs, trend_up = calculate_fw_health_and_trend(
                fw_implemented_dps, fw_total_dps, prev_actual_implemented, fw_prev_implemented_dps
            )
    
            fw_weight_score = calculate_fw_weight_score(fw_assignment_id, assignments)
    
            framework_health.append(
                {
                    "id": str(lp["df"].id),
                    "name": fw_name,
                    "version": fw_version,
                    "readiness": fw_health,
                    "weight_score": fw_weight_score,
                    "trend": trend_abs,
                    "trendUp": trend_up,
                }
            )
    
        return (
            total_controls_overall,
            passing_controls_overall,
            extra_controls_overall,
            extra_controls_list,
            critical_gaps,
            active_gaps,
            framework_health,
            total_dps_overall,
            implemented_dps_overall,
            prev_implemented_dps_overall,
        )

    def build_extra_controls_response(
        extra_controls: list[dict], search: str, sort_by: str, sort_order: str, page: int, limit: int
    ) -> tuple:
        formatted = list(extra_controls)
    
        if search:
            q = search.lower()
            formatted = [
                f
                for f in formatted
                if q in str(f.get("ctrlId", "")).lower()
                or q in str(f.get("control", "")).lower()
                or q in str(f.get("frameworkName", "")).lower()
            ]
    
        if sort_by:
            reverse = sort_order == "desc"
            formatted.sort(
                key=lambda x: (
                    x.get(sort_by, 0)
                    if isinstance(x.get(sort_by), (int, float))
                    else str(x.get(sort_by, ""))
                ),
                reverse=reverse,
            )
    
        total = len(formatted)
    
        from vora_shared.query_builder import clamp_page, clamp_limit
    
        safe_page = clamp_page(page)
        safe_limit = clamp_limit(limit)
        start = (safe_page - 1) * safe_limit
        end = start + safe_limit
    
        return formatted[start:end], total


    """Get auditor extra controls for dashboard table."""
    try:
        settings = get_settings()
        
        async with session_scope() as session:
            dfs = list((await session.execute(
                select(DeploymentFramework).where(DeploymentFramework.tenantId == ctx.tenant_id)
            )).scalars().all())

            latest_packages, gap_analysis_ids, merge_doc_ids = get_latest_packages(dfs)

            gap_analyses = list((await session.execute(
                select(PackageGapAnalysis).where(PackageGapAnalysis.id.in_(gap_analysis_ids))
            )).scalars().all()) if gap_analysis_ids else []

            merges = list((await session.execute(
                select(DeploymentPackageMerge).where(DeploymentPackageMerge.id.in_(merge_doc_ids))
            )).scalars().all()) if merge_doc_ids else []

            assignment_ids = [
                get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
                for ga in gap_analyses
                if get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
            ]

            assignments = list((await session.execute(
                select(FrameworkAssignment).where(FrameworkAssignment.id.in_(assignment_ids))
            )).scalars().all()) if assignment_ids else []

            res = process_gap_analyses(
                gap_analyses, latest_packages, [], merges, assignments, settings
            )
            extra_controls_list = res[3]

            data, total_items = build_extra_controls_response(
                extra_controls_list, search, sort_by, sort_order, page, limit
            )
            
            return paginated(
                data,
                build_pagination_meta(clamp_page(page), clamp_limit(limit), total_items),
                "Extra controls retrieved successfully"
            )

    except Exception:
        logger.exception("Error in extra controls")
        return server_error("Failed to fetch extra controls")

@router.get("/deployment-points")
async def get_auditor_deployment_points(
    ctx: Annotated[RequestContext, Depends(get_context)],
    page: Annotated[int, Query(alias="page")] = 1,
    limit: Annotated[int, Query(alias="limit")] = 10,
    search: Annotated[str, Query(alias="search")] = "",
    framework_filter: Annotated[str, Query(alias="frameworkFilter")] = "",
):

    def _get(obj: Any, key: str, default: Any = None) -> Any:
        """Helper to safely get attributes or dictionary keys."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if hasattr(obj, key) else default

    def _extract_control_weight(ctrl: Any) -> float:
        """Extract customer weightage from a control object."""
        custom = _get(ctrl, "customization") or {}
        weight_obj = _get(custom, "weightage") or {}
        return float(_get(weight_obj, "customer_weightage", 10.0))

    def get_latest_packages(dfs: list[DeploymentFramework]) -> tuple[list[dict], list[str], list[str]]:
        """Extract latest packages, gap analysis IDs, and merge document IDs."""
        latest_packages = []
        gap_analysis_ids = []
        merge_doc_ids = []
    
        for df in dfs:
            if not df.packages:
                continue
                
            latest_pkg = max(df.packages, key=lambda p: get_nested(p, "createdAt") or "")
    
            latest_packages.append({"df": df, "pkg": latest_pkg})
    
            gap_analysis = get_nested(latest_pkg, "gapAnalysis")
            if gap_analysis:
                gap_analysis_ids.append(str(gap_analysis))
    
            merge_doc = get_nested(latest_pkg, "mergeDocument")
            if merge_doc:
                merge_doc_ids.append(str(merge_doc))
    
        return latest_packages, gap_analysis_ids, merge_doc_ids

    def get_nested(obj: Any, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def extract_custom_controls(
        fw_assignment_id: str | None, assignments: list[FrameworkAssignment]
    ) -> dict[str, bool]:
        """Parse custom controls map from FrameworkAssignment."""
        custom_controls = {}
        if not fw_assignment_id:
            return custom_controls
    
        assignment = next((a for a in assignments if str(a.id) == fw_assignment_id), None)
        if not assignment or not assignment.fileVersions:
            return custom_controls
    
        latest_fv = assignment.fileVersions[-1]
        ai_extraction = _get(latest_fv, "aiExtraction") or []
        for sec in ai_extraction:
            for ctrl in _get(sec, "controls") or []:
                ctrl_id = _get(ctrl, "id")
                if ctrl_id:
                    is_custom = _get(_get(ctrl, "customization") or {}, "source") == "custom"
                    custom_controls[ctrl_id] = is_custom
    
        return custom_controls

    def extract_expected_controls(merge_doc: Any, custom_controls: dict[str, bool]) -> dict[str, Any]:
        """Parse expected controls and DPs from mergeDocument."""
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
                        "is_extra": custom_controls.get(ctrl_id, False),
                    }
        return expected_controls

    def extract_actual_implemented(gap_results: list[Any]) -> dict[str, int]:
        """Extract actual implemented counts from current gapAnalysis."""
        actual_implemented = {}
        for result in gap_results:
            ctrl_id = _get(result, "deployment_framework_control_id")
            if not ctrl_id:
                continue
            if ctrl_id not in actual_implemented:
                actual_implemented[ctrl_id] = 0
    
            status = str(_get(result, "implementation_status") or "").lower()
            if status in ["implemented", "compliant", "passed", "fully implemented"]:
                actual_implemented[ctrl_id] += 1
    
        return actual_implemented

    def _calculate_control_percentages(
        expected_controls: dict, actual_implemented: dict
    ) -> tuple[int, list[dict]]:
        total_dps = 0
        controls_list = []
    
        for ctrl_id, expected in expected_controls.items():
            req_dps = expected["required_dps"]
            total_dps += req_dps
    
            impl_dps = actual_implemented.get(ctrl_id, 0)
            is_implemented = impl_dps > 0
    
            pct = 100 if is_implemented else 0
    
            controls_list.append({"name": expected["name"], "pct": pct})
    
        return total_dps, controls_list

    def process_deployment_points_detailed(
        gap_analyses: list[PackageGapAnalysis],
        latest_packages: list[dict],
        merges: list[DeploymentPackageMerge],
        assignments: list[FrameworkAssignment],
    ) -> list[dict]:
        """Calculate deployment points and their control percentages per framework."""
        result = []
    
        for lp in latest_packages:
            ga_id = str(get_nested(lp["pkg"], "gapAnalysis"))
            merge_id = str(get_nested(lp["pkg"], "mergeDocument"))
    
            ga = next((g for g in gap_analyses if str(g.id) == ga_id), None)
            merge_doc = next((m for m in merges if str(m.id) == merge_id), None)
    
            if not merge_doc:
                continue
    
            fw_id = str(lp["df"].id)
            fw_name = lp["df"].frameworkName or UNKNOWN_FRAMEWORK
            fw_version = lp["df"].frameworkVersion or ""
    
            gap_data = ga.gapAnalysis or {} if ga else {}
            fw_assignment_id = get_nested(gap_data, "framework_assignment_id")
    
            custom_controls = (
                extract_custom_controls(fw_assignment_id, assignments) if fw_assignment_id else {}
            )
            expected_controls = extract_expected_controls(merge_doc, custom_controls)
    
            gap_results = get_nested(gap_data, "deployment_gap_results") or []
            actual_implemented = extract_actual_implemented(gap_results)
    
            total_dps, controls_list = _calculate_control_percentages(
                expected_controls, actual_implemented
            )
    
            result.append(
                {
                    "id": fw_id,
                    "frameworkName": fw_name,
                    "frameworkVersion": fw_version,
                    "instances": total_dps,
                    "controls": controls_list,
                }
            )
    
        return result

    def build_deployment_points_response(
        dp_list: list[dict], search: str, framework_filter: str, page: int, limit: int
    ) -> tuple[list[dict], int]:
        filtered = dp_list
        if search:
            s = search.lower()
            filtered = [dp for dp in filtered if s in (dp.get("frameworkName") or "").lower()]
        if framework_filter and framework_filter != "All Frameworks":
            filtered = [dp for dp in filtered if dp.get("frameworkVersion") == framework_filter]
    
        total_items = len(filtered)
        total_instances = sum(dp.get("instances", 0) for dp in filtered)
    
        from vora_shared.query_builder import clamp_page, clamp_limit
    
        safe_page = clamp_page(page)
        safe_limit = clamp_limit(limit)
        start = (safe_page - 1) * safe_limit
        end = start + safe_limit
    
        return filtered[start:end], total_items, total_instances


    """Get detailed deployment points with control percentages."""
    try:
        async with session_scope() as session:
            dfs = list((await session.execute(
                select(DeploymentFramework).where(DeploymentFramework.tenantId == ctx.tenant_id)
            )).scalars().all())

            latest_packages, gap_analysis_ids, merge_doc_ids = get_latest_packages(dfs)

            gap_analyses = list((await session.execute(
                select(PackageGapAnalysis).where(PackageGapAnalysis.id.in_(gap_analysis_ids))
            )).scalars().all()) if gap_analysis_ids else []

            merges = list((await session.execute(
                select(DeploymentPackageMerge).where(DeploymentPackageMerge.id.in_(merge_doc_ids))
            )).scalars().all()) if merge_doc_ids else []

            assignment_ids = [
                get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
                for ga in gap_analyses
                if get_nested(ga.gapAnalysis or {}, "framework_assignment_id")
            ]

            assignments = list((await session.execute(
                select(FrameworkAssignment).where(FrameworkAssignment.id.in_(assignment_ids))
            )).scalars().all()) if assignment_ids else []

            data = process_deployment_points_detailed(
                gap_analyses, latest_packages, merges, assignments
            )
            
            paginated_data, total_items, total_instances = build_deployment_points_response(
                data, search, framework_filter, page, limit
            )
            
            return paginated(
                {
                    "results": paginated_data,
                    "totalInstances": total_instances
                },
                build_pagination_meta(clamp_page(page), clamp_limit(limit), total_items),
                "Deployment points retrieved successfully"
            )

    except Exception:
        logger.exception("Error in deployment points")
        return server_error("Failed to fetch deployment points")


@router.get("/framework-details/{deployment_framework_id}")
async def get_auditor_framework_details(
    deployment_framework_id: str,
    ctx: Annotated[RequestContext, Depends(get_context)]
):

    def get_nested(obj: Any, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _update_assignment_maps(file_version: dict, source_map: dict, applicable_map: dict) -> None:
        for extraction in file_version.get("aiExtraction", []):
            for control in extraction.get("controls", []):
                control_id = control.get("id")
                if not control_id:
                    continue

                customization = control.get("customization") or {}
                source = customization.get("source")
                if source:
                    source_map[control_id] = source

                applicable_map[control_id] = customization.get("is_applicable", True)

    async def _build_framework_assignment_maps(
        session, assigned_framework_id: str
    ) -> tuple[dict, dict]:
        assigned_fw = (
            await session.execute(
                select(FrameworkAssignment).where(FrameworkAssignment.id == assigned_framework_id)
            )
        ).scalar_one_or_none()

        source_map = {}
        applicable_map = {}
        if not assigned_fw:
            return source_map, applicable_map

        for file_version in getattr(assigned_fw, "fileVersions", None) or []:
            _update_assignment_maps(file_version, source_map, applicable_map)

        return source_map, applicable_map

    def _update_auditor_control_metrics(
        ctrl: dict,
        metrics: dict,
        source_map: dict,
        comp_threshold: float,
        gap_score: float = None,
    ) -> None:
        ctrl_id = ctrl.get("assigned_framework_control_id", "")
        metrics["subscribed"] += 1
        score = ctrl.get("comparison_score", 0)

        if score >= comp_threshold:
            metrics["compliant"] += 1
        else:
            metrics["non_compliant"] += 1
            dps = ctrl.get("deployment_framework_deployment_points", [])
            metrics["non_compliant_list"].append(
                {
                    "sl": metrics["non_compliant"],
                    "ctrlNo": ctrl_id,
                    "name": ctrl.get("assigned_framework_control_name", ""),
                    "instances": len(dps),
                    "failing": f"{round((1 - score) * 100)}%",
                }
            )

        if source_map.get(ctrl_id) == "custom":
            metrics["custom_count"] += 1
        else:
            metrics["pre_count"] += 1

        ctrl_name = ctrl.get("assigned_framework_control_name", "Unknown")
        if gap_score is not None:
            val = round(gap_score * 10)
        else:
            val = round((1 - score) * 10)

        metrics["gap_analysis"].append(
            {"id": ctrl_id, "name": ctrl_name, "value": val}
        )

    def _calculate_gap_scores(gap_doc) -> dict:
        if not gap_doc or not gap_doc.gapAnalysis:
            return {}

        gap_results = gap_doc.gapAnalysis.get("deployment_gap_results", [])
        control_gaps = {}
        for res in gap_results:
            cid = res.get("assigned_framework_control_id")
            if cid:
                control_gaps.setdefault(cid, []).append(res.get("gap_score", 0))

        return {cid: sum(scores) / len(scores) for cid, scores in control_gaps.items()}

    def _natural_sort_key(item, key_name):
        import re
        val = item.get(key_name, "")
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', val)]

    def _calculate_auditor_metrics(
        comparison_doc, gap_doc, source_map: dict, applicable_map: dict, comp_threshold: float
    ) -> dict:
        metrics = {
            "subscribed": 0,
            "compliant": 0,
            "non_compliant": 0,
            "custom_count": 0,
            "pre_count": 0,
            "gap_analysis": [],
            "non_compliant_list": [],
        }

        if (
            not comparison_doc
            or not comparison_doc.comparison
            or "comparison_result" not in comparison_doc.comparison
        ):
            return metrics

        gap_scores = _calculate_gap_scores(gap_doc)

        results = comparison_doc.comparison["comparison_result"]
        for section in results:
            for ctrl in section.get("controls", []):
                ctrl_id = ctrl.get("assigned_framework_control_id", "")
                if applicable_map.get(ctrl_id, True):
                    _update_auditor_control_metrics(
                        ctrl, metrics, source_map, comp_threshold, gap_scores.get(ctrl_id)
                    )

        metrics["gap_analysis"].sort(key=lambda x: _natural_sort_key(x, "id"))
        metrics["non_compliant_list"].sort(key=lambda x: _natural_sort_key(x, "ctrlNo"))

        for idx, item in enumerate(metrics["non_compliant_list"]):
            item["sl"] = idx + 1

        return metrics

    try:
        tenant_id = ctx.tenant_id
        from vora_shared.models import PackageComparison

        settings = get_settings()
        comp_threshold = settings.compliance_score_threshold

        async with session_scope() as session:
            df = (
                await session.execute(
                    select(DeploymentFramework)
                    .where(DeploymentFramework.id == deployment_framework_id)
                    .where(DeploymentFramework.tenantId == tenant_id)
                )
            ).scalar_one_or_none()

            if not df:
                return server_error("Framework not found")

            package = max(df.packages, key=lambda p: get_nested(p, "createdAt") or "") if df.packages else None

            comparison_id = None
            ga_id = None
            if package:
                if isinstance(package, dict):
                    comparison_id = package.get("comparison")
                    ga_id = package.get("gapAnalysis")
                else:
                    comparison_id = getattr(package, "comparison", None)
                    ga_id = getattr(package, "gapAnalysis", None)

            comparison_doc = None
            if comparison_id:
                comparison_doc = (
                    await session.execute(
                        select(PackageComparison).where(PackageComparison.id == str(comparison_id))
                    )
                ).scalar_one_or_none()

            gap_doc = None
            if ga_id:
                gap_doc = (
                    await session.execute(
                        select(PackageGapAnalysis).where(PackageGapAnalysis.id == str(ga_id))
                    )
                ).scalar_one_or_none()

            source_map, applicable_map = await _build_framework_assignment_maps(
                session, df.assignedFrameworkId
            )
            m = _calculate_auditor_metrics(comparison_doc, gap_doc, source_map, applicable_map, comp_threshold)

            data = {
                "id": str(df.id),
                "frameworkName": df.frameworkName,
                "frameworkVersion": df.frameworkVersion,
                "controls": {
                    "subscribed": m["subscribed"],
                    "compliant": m["compliant"],
                    "nonCompliant": m["non_compliant"],
                    "notAssessed": 0,
                },
                "coverage": {
                    "total": m["pre_count"] + m["custom_count"],
                    "breakdown": [
                        {"name": "Pre controls", "value": m["pre_count"]},
                        {"name": "Org. Specific", "value": m["custom_count"]},
                    ],
                },
                "compliance": {
                    "total": m["compliant"] + m["non_compliant"],
                    "breakdown": [
                        {"name": "Compliant", "value": m["compliant"]},
                        {"name": "Non-Compliant", "value": m["non_compliant"]},
                        {"name": "Not Assessed", "value": 0},
                    ],
                },
                "auditDashboard": {"gapAnalysis": m["gap_analysis"]},
                "nonCompliantControls": m["non_compliant_list"],
                "notAssessed": [],
            }

        return success(data, "Framework details retrieved successfully")

    except Exception:
        logger.exception("Error fetching framework details")
        return server_error("Failed to fetch framework details")