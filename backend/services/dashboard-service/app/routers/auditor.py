import logging
from typing import Annotated

from app.helpers import (
    build_controls_passing_response,
    build_critical_gaps_response,
    build_extra_controls_response,
    build_overall_protection_rows,
    filter_and_sort_rows,
    get_live_packages,
    get_nested,
    process_gap_analyses,
    process_live_streams,
    process_ai_insights,
    process_deployment_points,
    process_deployment_points_detailed,
    build_deployment_points_response,
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
                gap_analyses, live_packages, historical_gap_analyses, merges, assignments, settings
            )
            overall_protection = (
                round((implemented_dps_overall / total_dps_overall) * 100)
                if total_dps_overall > 0
                else 0
            )

            live_streams = process_live_streams(evidence_outputs)
            ai_insights = process_ai_insights(evidence_outputs)
            deployment_points = process_deployment_points(merges, live_packages)

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
                gap_analyses, live_packages, historical_gap_analyses, merges, assignments, settings
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
    """Get auditor critical gaps for dashboard table."""
    try:
        from app.helpers import build_critical_gaps_response
        async with session_scope() as session:
            dfs = list((await session.execute(
                select(DeploymentFramework).where(DeploymentFramework.tenantId == ctx.tenant_id)
            )).scalars().all())

            live_packages, gap_analysis_ids, merge_doc_ids = get_live_packages(dfs)

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
                gap_analyses, live_packages, historical_gap_analyses, merges, assignments, settings
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
    """Get auditor controls passing for dashboard table."""
    try:
        settings = get_settings()
        
        async with session_scope() as session:
            dfs = list((await session.execute(
                select(DeploymentFramework).where(DeploymentFramework.tenantId == ctx.tenant_id)
            )).scalars().all())

            live_packages, gap_analysis_ids, merge_doc_ids = get_live_packages(dfs)

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
                live_packages,
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
    """Get auditor extra controls for dashboard table."""
    try:
        settings = get_settings()
        
        async with session_scope() as session:
            dfs = list((await session.execute(
                select(DeploymentFramework).where(DeploymentFramework.tenantId == ctx.tenant_id)
            )).scalars().all())

            live_packages, gap_analysis_ids, merge_doc_ids = get_live_packages(dfs)

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
                gap_analyses, live_packages, [], merges, assignments, settings
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
    """Get detailed deployment points with control percentages."""
    try:
        async with session_scope() as session:
            dfs = list((await session.execute(
                select(DeploymentFramework).where(DeploymentFramework.tenantId == ctx.tenant_id)
            )).scalars().all())

            live_packages, gap_analysis_ids, merge_doc_ids = get_live_packages(dfs)

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
                gap_analyses, live_packages, merges, assignments
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
    try:
        tenant_id = ctx.tenant_id
        async with session_scope() as session:
            from vora_shared.models import PackageComparison, FrameworkAssignment
            # 1. Fetch Deployment Framework
            df = (await session.execute(
                select(DeploymentFramework)
                .where(DeploymentFramework.id == deployment_framework_id)
                .where(DeploymentFramework.tenantId == tenant_id)
            )).scalar_one_or_none()

            if not df:
                return server_error("Framework not found")

            # 2. Fetch Comparison Document (using comparison ID from package)
            package = df.packages[0] if df.packages else None
            comparison_id = package.get("comparison") if package and isinstance(package, dict) else (getattr(package, "comparison", None) if package else None)
            
            comparison_doc = None
            if comparison_id:
                comparison_doc = (await session.execute(
                    select(PackageComparison).where(PackageComparison.id == comparison_id)
                )).scalar_one_or_none()

            # 3. Fetch Assigned Framework to get customization sources
            assigned_fw = (await session.execute(
                select(FrameworkAssignment).where(FrameworkAssignment.id == df.assignedFrameworkId)
            )).scalar_one_or_none()

            source_map = {}
            applicable_map = {}
            if assigned_fw and getattr(assigned_fw, "fileVersions", None):
                for fv in assigned_fw.fileVersions:
                    for ext in fv.get("aiExtraction", []):
                        for ctrl in ext.get("controls", []):
                            c_id = ctrl.get("id")
                            customization = ctrl.get("customization") or {}
                            source = customization.get("source")
                            if c_id and source:
                                source_map[c_id] = source
                            
                            is_applicable = customization.get("is_applicable", True)
                            if c_id:
                                applicable_map[c_id] = is_applicable

            # Process logic based on config
            settings = get_settings()
            comp_threshold = settings.compliance_score_threshold

            subscribed = 0
            compliant = 0
            non_compliant = 0
            
            custom_count = 0
            pre_count = 0
            
            gap_analysis = []
            non_compliant_list = []

            if comparison_doc and comparison_doc.comparison and "comparison_result" in comparison_doc.comparison:
                results = comparison_doc.comparison["comparison_result"]
                for section in results:
                    for ctrl in section.get("controls", []):
                        ctrl_id = ctrl.get("assigned_framework_control_id", "")
                        
                        # Skip if not applicable
                        if not applicable_map.get(ctrl_id, True):
                            continue
                            
                        subscribed += 1
                        score = ctrl.get("comparison_score", 0)

                        is_compliant = score >= comp_threshold
                        if is_compliant:
                            compliant += 1
                        else:
                            non_compliant += 1
                            
                            # Add to non-compliant list
                            dps = ctrl.get("deployment_framework_deployment_points", [])
                            instances = len(dps)
                            failing = f"{round((1 - score) * 100)}%"
                            
                            non_compliant_list.append({
                                "sl": non_compliant,
                                "ctrlNo": ctrl_id,
                                "name": ctrl.get("assigned_framework_control_name", ""),
                                "instances": instances,
                                "failing": failing
                            })
                            
                        # Count org specific vs pre controls based on customization source from FrameworkAssignment
                        source = source_map.get(ctrl_id)
                        if source == "custom":
                            custom_count += 1
                        else:
                            pre_count += 1
                            
                        # Add control to gap analysis
                        ctrl_name = ctrl.get("assigned_framework_control_name", "Unknown")
                        gap_val = round((1 - score) * 10)  # Gap representation 0-10
                        gap_analysis.append({"id": ctrl_id, "name": ctrl_name, "value": gap_val})

            return success({
                "id": str(df.id),
                "frameworkName": df.frameworkName,
                "frameworkVersion": df.frameworkVersion,
                "controls": {
                    "subscribed": subscribed,
                    "compliant": compliant,
                    "nonCompliant": non_compliant,
                    "notAssessed": 0
                },
                "coverage": {
                    "total": pre_count + custom_count,
                    "breakdown": [
                        {"name": "Pre controls", "value": pre_count},
                        {"name": "Org. Specific", "value": custom_count}
                    ]
                },
                "compliance": {
                    "total": compliant + non_compliant,
                    "breakdown": [
                        {"name": "Compliant", "value": compliant},
                        {"name": "Non-Compliant", "value": non_compliant},
                        {"name": "Not Assessed", "value": 0}
                    ]
                },
                "auditDashboard": {"gapAnalysis": gap_analysis},
                "nonCompliantControls": non_compliant_list,
                "notAssessed": []
            }, "Framework details retrieved successfully")

    except Exception:
        logger.exception("Error fetching framework details")
        return server_error("Failed to fetch framework details")

