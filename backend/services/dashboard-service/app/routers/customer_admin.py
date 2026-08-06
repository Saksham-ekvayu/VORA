"""Port of deployment-framework-service dashboard routes/controllers."""

import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from vora_shared.database import session_scope
from vora_shared.models import (
    Customer,
    DeploymentFramework,
    DocumentExtraction,
    FrameworkAssignment,
    PackageComparison,
    PackageGapAnalysis,
    PackageMerge,
    User,
)
from vora_shared.responses import server_error, success
from vora_shared.security import RequestContext, get_context

logger = logging.getLogger("dashboard_router")

router = APIRouter(tags=["dashboard"])


def _get(obj: Any, key: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get_time_ago(date_value: datetime | None) -> str:
    if not date_value:
        return ""
    if isinstance(date_value, str):
        try:
            date_value = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        except ValueError:
            return ""
    now = datetime.now(timezone.utc)
    if date_value.tzinfo is None:
        date_value = date_value.replace(tzinfo=timezone.utc)
    diff = now - date_value
    diff_days = diff.days
    diff_hours = diff.seconds // 3600
    diff_mins = diff.seconds // 60

    if diff_days > 1:
        return f"{diff_days} days ago"
    if diff_days == 1:
        return "Yesterday"
    if diff_hours > 0:
        return f"{diff_hours} hours ago"
    if diff_mins > 0:
        return f"{diff_mins} minutes ago"
    return "Just now"


def _process_user_stats(users: list[User]) -> dict[str, Any]:
    role_counts: dict[str, int] = {}
    for u in users:
        role = u.role or "Unknown"
        role_counts[role] = role_counts.get(role, 0) + 1
    return {
        "totalProfiles": len(users),
        "profilesByRole": [{"role": role, "count": count} for role, count in role_counts.items()],
    }


def _get_deployment_points_from_package(pkg: dict) -> list:
    """Extract deployment points from a package."""
    live_package = pkg if _get(pkg, "status") == "live" else None
    merge_doc_id = _get(live_package, "mergeDocument") if live_package else None
    
    if not merge_doc_id:
        return []
    
    # We need the package_merges dict to get the actual merge object
    # This function is called from _calculate_framework_progress which has access
    return []


def _count_deployment_points(controls_data: list) -> tuple[int, int]:
    """Count total and configured deployment points from controls data."""
    total = 0
    configured = 0
    
    all_deployment_points = [
        dp
        for section in (controls_data or [])
        for control in (_get(section, "controls") or [])
        for dp in (_get(control, "deployment_points") or [])
    ]
    
    for dp in all_deployment_points:
        total += 1
        if (_get(dp, "path") or "").strip():
            configured += 1
    
    return total, configured


def _calculate_single_framework_progress(
    df: DeploymentFramework,
    package_merges: dict[str, PackageMerge],
) -> tuple[int, int]:
    """Calculate progress for a single deployment framework."""
    fw_configured = 0
    fw_total = 0
    
    live_package = next((p for p in (df.packages or []) if _get(p, "status") == "live"), None)
    merge_doc_id = _get(live_package, "mergeDocument") if live_package else None
    pm = package_merges.get(str(merge_doc_id)) if merge_doc_id else None
    
    merge_extraction = _get(pm, "mergeExtraction") if pm else None
    controls_data = _get(merge_extraction, "controls_data") if merge_extraction else []
    
    total, configured = _count_deployment_points(controls_data)
    fw_total += total
    fw_configured += configured
    
    return fw_total, fw_configured


def _calculate_framework_progress(
    deployment_frameworks: list[DeploymentFramework],
    package_merges: dict[str, PackageMerge],
    assignment,
) -> tuple[int, int, int, dict]:
    """Calculate progress for a single framework assignment."""
    fw_configured = 0
    fw_total = 0

    dfs_for_assignment = [
        d
        for d in deployment_frameworks
        if d.assigned_framework_id and str(d.assigned_framework_id) == str(assignment.id)
    ]

    for df in dfs_for_assignment:
        total, configured = _calculate_single_framework_progress(df, package_merges)
        fw_total += total
        fw_configured += configured

    percentage = round((fw_configured / fw_total) * 100) if fw_total > 0 else 0

    progress_data = {
        "id": str(assignment.id) if assignment and getattr(assignment, "id", None) else None,
        "frameworkName": assignment.framework_name or assignment.framework_code,
        "frameworkVersion": assignment.framework_version,
        "frameworkCode": assignment.framework_code,
        "configured": fw_configured,
        "total": fw_total,
        "percentage": percentage,
    }
    return fw_configured, fw_total, percentage, progress_data


def _get_deployed_framework_info(
    deployment_frameworks: list[DeploymentFramework],
    assignment,
) -> dict | None:
    """Get deployment info for a framework assignment."""
    df = next(
        (
            d
            for d in deployment_frameworks
            if d.assigned_framework_id and str(d.assigned_framework_id) == str(assignment.id)
        ),
        None,
    )
    deployed_on = None
    if df and df.packages:
        live_package = next((p for p in df.packages if _get(p, "status") == "live"), None)
        if live_package:
            deployed_on = _get(live_package, "updatedAt") or _get(live_package, "createdAt")

    assignment_info = assignment.assignment or {}
    return {
        "name": assignment.framework_name,
        "version": assignment.framework_version,
        "count": 1,
        "assignedOn": _get(assignment_info, "assignedAt") or assignment.created_at,
        "deployedOn": deployed_on,
    }


def _process_assignments_and_progress(
    active_assignments: list[FrameworkAssignment],
    deployment_frameworks: list[DeploymentFramework],
    package_merges: dict[str, PackageMerge],
) -> dict[str, Any]:
    controls_configured = 0
    controls_total = 0
    setup_progress_by_framework = []
    deployed_frameworks = []
    assigned_frameworks_list = []

    for assignment in active_assignments:
        fw_configured, fw_total, _, progress_data = _calculate_framework_progress(
            deployment_frameworks, package_merges, assignment
        )
        controls_configured += fw_configured
        controls_total += fw_total
        setup_progress_by_framework.append(progress_data)

        deployed_info = _get_deployed_framework_info(deployment_frameworks, assignment)
        if deployed_info:
            deployed_frameworks.append(deployed_info)

        finalization = assignment.finalization or {}
        assigned_frameworks_list.append(
            {
                "id": str(assignment.id) if assignment and getattr(assignment, "id", None) else None,
                "code": assignment.framework_code,
                "name": assignment.framework_name,
                "version": assignment.framework_version,
                "assignmentStatus": assignment.status,
                "finalizationStatus": ("finalized" if _get(finalization, "isFinalized") else "pending"),
                "assignedAt": assignment.created_at,
            }
        )

    assigned_frameworks_list.sort(
        key=lambda a: a["assignedAt"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    return {
        "controlsConfigured": controls_configured,
        "controlsTotal": controls_total,
        "setupProgressByFramework": setup_progress_by_framework,
        "deployedFrameworks": deployed_frameworks,
        "assignedFrameworksList": assigned_frameworks_list[:10],
    }


def _add_activity_entry(
    recent_activity: list[dict],
    activity_id: str,
    message: str,
    actor: str,
    timestamp: datetime | None,
) -> None:
    """Generic helper to add an activity entry."""
    if timestamp:
        recent_activity.append(
            {
                "id": activity_id,
                "message": message,
                "actor": actor,
                "timeAgo": _get_time_ago(timestamp),
                "timestamp": timestamp,
            }
        )


def _get_assignment_actor(users: dict[str, User], user_id: str | None, default: str) -> tuple[str, str]:
    """Get actor name and email from user ID."""
    if not user_id:
        return default, f"{default.lower()}@example.com"
    user = users.get(str(user_id))
    if not user:
        return default, f"{default.lower()}@example.com"
    return user.name, user.email


def _add_assignment_created_activity(
    assignment: FrameworkAssignment,
    users: dict[str, User],
    recent_activity: list[dict],
) -> None:
    """Add assignment created activity."""
    assignment_info = assignment.assignment or {}
    assigned_by_id = _get(assignment_info, "assignedBy")
    assigned_by = users.get(str(assigned_by_id)) if assigned_by_id else None
    assign_date = _get(assignment_info, "assignedAt") or assignment.created_at
    
    if assign_date:
        name = assigned_by.name if assigned_by else "Admin"
        email = assigned_by.email if assigned_by else "admin@example.com"
        _add_activity_entry(
            recent_activity,
            f"assign-{assignment.id}",
            f"{name} assigned framework {assignment.framework_version}",
            email,
            assign_date,
        )


def _add_assignment_revoked_activity(
    assignment: FrameworkAssignment,
    users: dict[str, User],
    recent_activity: list[dict],
) -> None:
    """Add assignment revoked activity."""
    revocation = assignment.revocation or {}
    revoked_by_id = _get(revocation, "revokedBy")
    revoked_by = users.get(str(revoked_by_id)) if revoked_by_id else None
    revoke_date = _get(revocation, "revokedAt") or assignment.updated_at
    
    if assignment.status == "revoked" and revoke_date:
        email = revoked_by.email if revoked_by else "admin@example.com"
        _add_activity_entry(
            recent_activity,
            f"revoke-{assignment.id}",
            f"Framework {assignment.framework_version} was revoked",
            email,
            revoke_date,
        )


def _add_assignment_finalized_activity(
    assignment: FrameworkAssignment,
    users: dict[str, User],
    recent_activity: list[dict],
) -> None:
    """Add assignment finalized activity."""
    finalization = assignment.finalization or {}
    if _get(finalization, "isFinalized"):
        finalized_by_id = _get(finalization, "finalizedBy")
        finalized_by = users.get(str(finalized_by_id)) if finalized_by_id else None
        email = finalized_by.email if finalized_by else "system@example.com"
        _add_activity_entry(
            recent_activity,
            f"final-{assignment.id}",
            f"Framework {assignment.framework_version} finalized",
            email,
            _get(finalization, "finalizedAt"),
        )


def _add_assignment_activity(
    assignment: FrameworkAssignment,
    users: dict[str, User],
    recent_activity: list[dict],
) -> None:
    """Add assignment-related activity entries."""
    _add_assignment_created_activity(assignment, users, recent_activity)
    _add_assignment_revoked_activity(assignment, users, recent_activity)
    _add_assignment_finalized_activity(assignment, users, recent_activity)


def _add_framework_activity_entry(
    df: DeploymentFramework,
    recent_activity: list[dict],
    pkg: dict,
    event_type: str,
    message: str,
    actor: str,
    timestamp: datetime | None,
) -> None:
    """Helper to add framework activity entries."""
    if timestamp:
        recent_activity.append(
            {
                "id": f"{event_type}-{df.id}-{_get(pkg, 'packageVersion')}",
                "message": message,
                "actor": actor,
                "timeAgo": _get_time_ago(timestamp),
                "timestamp": timestamp,
            }
        )


def _add_package_created_activity(
    df: DeploymentFramework,
    pkg: dict,
    recent_activity: list[dict],
    uploaded_by: User | None,
) -> None:
    """Add package created activity."""
    package_version = _get(pkg, "packageVersion")
    trigger = _get(pkg, "trigger")
    pkg_created = _get(pkg, "createdAt")
    
    if pkg_created:
        patch_type = f" ({trigger} patch)" if trigger else ""
        _add_framework_activity_entry(
            df, recent_activity, pkg,
            f"pkg-created-{df.id}",
            f"Package {package_version}{patch_type} uploaded in {df.framework_version or df.framework_name}",
            uploaded_by.email if uploaded_by else "User",
            pkg_created
        )


def _add_package_review_activities(
    df: DeploymentFramework,
    pkg: dict,
    users: dict[str, User],
    recent_activity: list[dict],
    uploaded_by: User | None,
) -> None:
    """Add package review-related activities."""
    package_version = _get(pkg, "packageVersion")
    expert_review = _get(pkg, "expertReview") or {}
    assigned_expert = _get(expert_review, "assignedExpert")
    expert = users.get(str(assigned_expert)) if assigned_expert else None
    expert_name = (expert.name if expert else None) or (expert.email if expert else None) or "Expert"

    requested_at = _get(expert_review, "requestedAt")
    if expert_review and requested_at:
        _add_framework_activity_entry(
            df, recent_activity, pkg,
            f"pkg-review-req-{df.id}",
            f"Package {package_version} requested review from expert {expert_name}",
            uploaded_by.email if uploaded_by else "User",
            requested_at
        )

    reviewed_at = _get(expert_review, "reviewedAt")
    review_status = _get(expert_review, "status")
    if expert_review and reviewed_at and review_status in ("approved", "returned"):
        _add_framework_activity_entry(
            df, recent_activity, pkg,
            f"pkg-review-res-{df.id}",
            f"Expert {expert_name} {review_status} package {package_version}",
            expert.email if expert else "Expert",
            reviewed_at
        )


def _add_package_live_activity(
    df: DeploymentFramework,
    pkg: dict,
    recent_activity: list[dict],
) -> None:
    """Add package live deployment activity."""
    package_version = _get(pkg, "packageVersion")
    if _get(pkg, "status") == "live":
        live_date = _get(pkg, "updatedAt") or _get(pkg, "createdAt")
        _add_framework_activity_entry(
            df, recent_activity, pkg,
            f"pkg-live-{df.id}",
            f"Deployment framework package {package_version} deployed (live)",
            "System",
            live_date
        )


def _add_package_activity(
    df: DeploymentFramework,
    pkg: dict,
    users: dict[str, User],
    recent_activity: list[dict],
    uploaded_by: User | None,
) -> None:
    """Add package-related activity entries."""
    _add_package_created_activity(df, pkg, recent_activity, uploaded_by)
    _add_package_review_activities(df, pkg, users, recent_activity, uploaded_by)
    _add_package_live_activity(df, pkg, recent_activity)


def _add_framework_activities(
    deployment_frameworks: list[DeploymentFramework],
    users: dict[str, User],
    recent_activity: list[dict],
) -> None:
    """Add framework-related activity entries."""
    for df in deployment_frameworks:
        uploaded_by = users.get(str(df.uploaded_by)) if df.uploaded_by else None
        if df.created_at:
            recent_activity.append(
                {
                    "id": f"df-created-{df.id}",
                    "message": f"Deployment framework {df.framework_version or df.framework_name} uploaded",
                    "actor": uploaded_by.email if uploaded_by else "User",
                    "timeAgo": _get_time_ago(df.created_at),
                    "timestamp": df.created_at,
                }
            )

        for pkg in df.packages or []:
            _add_package_activity(df, pkg, users, recent_activity, uploaded_by)


def _add_user_activity(user: User, recent_activity: list[dict]) -> None:
    """Add user-related activity entries."""
    if user.created_at:
        recent_activity.append(
            {
                "id": f"user-created-{user.id}",
                "message": f"User {user.name} joined as {user.role}",
                "actor": user.email,
                "timeAgo": _get_time_ago(user.created_at),
                "timestamp": user.created_at,
            }
        )
    if user.updated_at and user.created_at and (user.updated_at - user.created_at).total_seconds() > 1:
        action = "deactivated" if user.is_active is False else "updated"
        recent_activity.append(
            {
                "id": f"user-updated-{user.id}",
                "message": f"User profile {user.name} was {action}",
                "actor": user.email,
                "timeAgo": _get_time_ago(user.updated_at),
                "timestamp": user.updated_at,
            }
        )


def _add_customer_activity(customer: Customer | None, recent_activity: list[dict]) -> None:
    """Add customer-related activity entries."""
    if not customer:
        return
    if customer.created_at:
        recent_activity.append(
            {
                "id": f"cust-created-{customer.id}",
                "message": f"Customer account {customer.name} created",
                "actor": "System",
                "timeAgo": _get_time_ago(customer.created_at),
                "timestamp": customer.created_at,
            }
        )
    if (
        customer.updated_at
        and customer.created_at
        and (customer.updated_at - customer.created_at).total_seconds() > 1
    ):
        recent_activity.append(
            {
                "id": f"cust-updated-{customer.id}",
                "message": f"Customer profile {customer.name} was updated",
                "actor": "System",
                "timeAgo": _get_time_ago(customer.updated_at),
                "timestamp": customer.updated_at,
            }
        )


def _get_activity_suffix(info: dict) -> str:
    """Get suffix for system activity messages."""
    if not info:
        return ""
    trigger = _get(info["pkg"], "trigger")
    patch_type = f" ({trigger} patch)" if trigger else ""
    fw_label = info["df"].framework_version or info["df"].framework_name
    return f" for Package {_get(info['pkg'], 'packageVersion')}{patch_type} in {fw_label}"


def _add_document_extraction_activities(
    document_extractions: list[DocumentExtraction],
    recent_activity: list[dict],
) -> None:
    """Add document extraction activities."""
    for dex in document_extractions:
        if dex.created_at:
            ai_status = _get(dex.ai_extraction, "status") or "completed"
            _add_activity_entry(
                recent_activity,
                f"dex-{dex.id}",
                f"Document AI extraction {ai_status}",
                "AI Engine",
                dex.created_at,
            )


def _add_comparison_activities(
    package_comparisons: list[PackageComparison],
    pc_map: dict[str, dict],
    recent_activity: list[dict],
) -> None:
    """Add package comparison activities."""
    for pc in package_comparisons:
        if pc.created_at:
            suffix = _get_activity_suffix(pc_map.get(str(pc.id)))
            status = _get(pc.comparison, "status") or "started"
            _add_activity_entry(
                recent_activity,
                f"pc-{pc.id}",
                f"Package comparison {status}{suffix}",
                "System",
                pc.created_at,
            )


def _add_gap_analysis_activities(
    package_gap_analyses: list[PackageGapAnalysis],
    pga_map: dict[str, dict],
    recent_activity: list[dict],
) -> None:
    """Add gap analysis activities."""
    for pga in package_gap_analyses:
        if pga.created_at:
            suffix = _get_activity_suffix(pga_map.get(str(pga.id)))
            status = _get(pga.gap_analysis, "status") or "started"
            _add_activity_entry(
                recent_activity,
                f"pga-{pga.id}",
                f"Gap analysis {status}{suffix}",
                "System",
                pga.created_at,
            )


def _add_merge_activities(
    package_merges: list[PackageMerge],
    pm_map: dict[str, dict],
    recent_activity: list[dict],
) -> None:
    """Add package merge activities."""
    for pm in package_merges:
        if pm.created_at:
            suffix = _get_activity_suffix(pm_map.get(str(pm.id)))
            status = _get(pm.merge_extraction, "status") or "started"
            _add_activity_entry(
                recent_activity,
                f"pm-{pm.id}",
                f"Package merge {status}{suffix}",
                "System",
                pm.created_at,
            )


def _build_system_maps(
    deployment_frameworks: list[DeploymentFramework],
) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    """Build maps for system activities."""
    pc_map: dict[str, dict] = {}
    pga_map: dict[str, dict] = {}
    pm_map: dict[str, dict] = {}

    for df in deployment_frameworks:
        for pkg in df.packages or []:
            comparison = _get(pkg, "comparison")
            gap_analysis = _get(pkg, "gapAnalysis")
            merge_document = _get(pkg, "mergeDocument")
            if comparison:
                pc_map[str(comparison)] = {"df": df, "pkg": pkg}
            if gap_analysis:
                pga_map[str(gap_analysis)] = {"df": df, "pkg": pkg}
            if merge_document:
                pm_map[str(merge_document)] = {"df": df, "pkg": pkg}

    return pc_map, pga_map, pm_map


def _add_system_activities(
    deployment_frameworks: list[DeploymentFramework],
    document_extractions: list[DocumentExtraction],
    package_comparisons: list[PackageComparison],
    package_gap_analyses: list[PackageGapAnalysis],
    package_merges: list[PackageMerge],
    recent_activity: list[dict],
) -> None:
    """Add system-related activity entries."""
    pc_map, pga_map, pm_map = _build_system_maps(deployment_frameworks)

    _add_document_extraction_activities(document_extractions, recent_activity)
    _add_comparison_activities(package_comparisons, pc_map, recent_activity)
    _add_gap_analysis_activities(package_gap_analyses, pga_map, recent_activity)
    _add_merge_activities(package_merges, pm_map, recent_activity)


def _normalize_timestamp(value: Any) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)
    if getattr(value, "tzinfo", None) is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def _fetch_document_extractions(session, file_hashes: set) -> list[DocumentExtraction]:
    """Fetch document extractions for given file hashes."""
    if not file_hashes:
        return []
    return list(
        (await session.execute(
            select(DocumentExtraction).where(DocumentExtraction.file_hash.in_(list(file_hashes)))
        ))
        .scalars()
        .all()
    )


async def _fetch_package_analyses(session, framework_ids: list) -> tuple:
    """Fetch package comparisons, gap analyses, and merges."""
    if not framework_ids:
        return [], [], []
    
    comparisons = list(
        (await session.execute(
            select(PackageComparison).where(PackageComparison.framework_id.in_(framework_ids))
        ))
        .scalars()
        .all()
    )
    gap_analyses = list(
        (await session.execute(
            select(PackageGapAnalysis).where(PackageGapAnalysis.framework_id.in_(framework_ids))
        ))
        .scalars()
        .all()
    )
    merges = list(
        (await session.execute(
            select(PackageMerge).where(PackageMerge.framework_id.in_(framework_ids))
        ))
        .scalars()
        .all()
    )
    return comparisons, gap_analyses, merges


def _collect_user_ids_from_assignments(assignments: list[FrameworkAssignment]) -> set[str]:
    """Collect user IDs from assignments."""
    user_ids: set[str] = set()
    for a in assignments:
        assigned_by = _get(a.assignment, "assignedBy")
        revoked_by = _get(a.revocation, "revokedBy")
        finalized_by = _get(a.finalization, "finalizedBy")
        if assigned_by:
            user_ids.add(str(assigned_by))
        if revoked_by:
            user_ids.add(str(revoked_by))
        if finalized_by:
            user_ids.add(str(finalized_by))
    return user_ids


def _collect_user_ids_from_frameworks(deployment_frameworks: list[DeploymentFramework]) -> set[str]:
    """Collect user IDs from deployment frameworks."""
    user_ids: set[str] = set()
    for df in deployment_frameworks:
        if df.uploaded_by:
            user_ids.add(str(df.uploaded_by))
        for pkg in df.packages or []:
            expert_review = _get(pkg, "expertReview") or {}
            assigned_expert = _get(expert_review, "assignedExpert")
            if assigned_expert:
                user_ids.add(str(assigned_expert))
    return user_ids


def _collect_activity_user_ids(
    assignments: list[FrameworkAssignment],
    deployment_frameworks: list[DeploymentFramework],
) -> set[str]:
    """Collect all user IDs needed for activity display."""
    user_ids = _collect_user_ids_from_assignments(assignments)
    user_ids.update(_collect_user_ids_from_frameworks(deployment_frameworks))
    return user_ids


@router.get("/analytics")
async def get_customer_admin_dashboard(
    ctx: Annotated[RequestContext, Depends(get_context)],
):
    try:
        tenant_id = ctx.tenant_id
        user = ctx.user

        async with session_scope() as session:
            users = list(
                (await session.execute(
                    select(User).where(User.tenant_id == tenant_id, User.id != user.id)
                ))
                .scalars()
                .all()
            )
            customer = (
                await session.execute(
                    select(Customer).where(Customer.tenant_id == tenant_id)
                )
            ).scalar_one_or_none()
            deployment_frameworks = list(
                (await session.execute(
                    select(DeploymentFramework).where(DeploymentFramework.tenant_id == tenant_id)
                ))
                .scalars()
                .all()
            )
            assignments = list(
                (await session.execute(
                    select(FrameworkAssignment).where(
                        or_(
                            FrameworkAssignment.tenant_id == tenant_id,
                            FrameworkAssignment.customer_id == str(getattr(user, "customer_id", None) or "")
                            if getattr(user, "customer_id", None)
                            else FrameworkAssignment.tenant_id == tenant_id
                        )
                    )
                ))
                .scalars()
                .all()
            )

            framework_ids = [df.id for df in deployment_frameworks]
            file_hashes = {
                _get(doc, "fileHash")
                for df in deployment_frameworks
                for pkg in (df.packages or [])
                for doc in (_get(pkg, "documents") or [])
                if _get(doc, "fileHash")
            }

            document_extractions = await _fetch_document_extractions(session, file_hashes)
            package_comparisons, package_gap_analyses, package_merges = await _fetch_package_analyses(
                session, framework_ids
            )

            package_merges_map = {str(pm.id): pm for pm in package_merges}

            active_assignments = [a for a in assignments if a.status == "assigned"]
            user_stats = _process_user_stats(users)
            progress = _process_assignments_and_progress(
                active_assignments, deployment_frameworks, package_merges_map
            )

            user_ids = _collect_activity_user_ids(assignments, deployment_frameworks)
            activity_users_map: dict[str, User] = {}
            if user_ids:
                fetched = (
                    (await session.execute(
                        select(User).where(User.id.in_(list(user_ids)))
                    ))
                    .scalars()
                    .all()
                )
                activity_users_map = {str(u.id): u for u in fetched}

            recent_activity: list[dict[str, Any]] = []
            for assignment in assignments:
                _add_assignment_activity(assignment, activity_users_map, recent_activity)
            _add_framework_activities(deployment_frameworks, activity_users_map, recent_activity)
            for user_obj in users:
                _add_user_activity(user_obj, recent_activity)
            _add_customer_activity(customer, recent_activity)
            _add_system_activities(
                deployment_frameworks,
                document_extractions,
                package_comparisons,
                package_gap_analyses,
                package_merges,
                recent_activity,
            )

            recent_activity.sort(key=lambda a: _normalize_timestamp(a["timestamp"]), reverse=True)
            recent_activity = recent_activity[:20]

            controls_total = progress["controlsTotal"]
            controls_configured = progress["controlsConfigured"]

            response_data = {
                "stats": {
                    "totalProfiles": user_stats["totalProfiles"],
                    "deploymentFrameworks": len(deployment_frameworks),
                    "assignedFrameworks": len(active_assignments),
                    "controlsConfigured": controls_configured,
                    "controlsTotal": controls_total,
                },
                "profilesByRole": user_stats["profilesByRole"],
                "setupProgress": {
                    "configured": controls_configured,
                    "total": controls_total,
                    "percentage": (
                        round((controls_configured / controls_total) * 100) if controls_total > 0 else 0
                    ),
                },
                "setupProgressByFramework": progress["setupProgressByFramework"],
                "deployedFrameworks": progress["deployedFrameworks"],
                "assignedFrameworks": progress["assignedFrameworksList"],
                "recentActivity": recent_activity,
            }

        return success(response_data, "Customer dashboard analytics retrieved successfully")
    except Exception:
        logger.exception("Error fetching customer admin dashboard data")
        return server_error("Failed to retrieve customer dashboard analytics")