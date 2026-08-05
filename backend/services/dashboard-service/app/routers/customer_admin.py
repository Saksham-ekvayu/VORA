"""Port of deployment-framework-service dashboard routes/controllers."""

import logging
from datetime import datetime, timezone
from typing import Any

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
        fw_configured = 0
        fw_total = 0

        dfs_for_assignment = [
            d
            for d in deployment_frameworks
            if d.assignedFrameworkId and str(d.assignedFrameworkId) == str(assignment.id)
        ]

        for df in dfs_for_assignment:
            live_package = next((p for p in (df.packages or []) if _get(p, "status") == "live"), None)
            merge_doc_id = _get(live_package, "mergeDocument") if live_package else None
            pm = package_merges.get(str(merge_doc_id)) if merge_doc_id else None

            merge_extraction = _get(pm, "mergeExtraction") if pm else None
            controls_data = _get(merge_extraction, "controls_data") if merge_extraction else []
            all_deployment_points = [
                dp
                for section in (controls_data or [])
                for control in (_get(section, "controls") or [])
                for dp in (_get(control, "deployment_points") or [])
            ]

            for dp in all_deployment_points:
                fw_total += 1
                controls_total += 1
                if (_get(dp, "path") or "").strip():
                    fw_configured += 1
                    controls_configured += 1

        percentage = round((fw_configured / fw_total) * 100) if fw_total > 0 else 0

        setup_progress_by_framework.append(
            {
                "id": str(assignment.id) if assignment and getattr(assignment, "id", None) else None,
                "frameworkName": assignment.frameworkName or assignment.frameworkCode,
                "frameworkVersion": assignment.frameworkVersion,
                "frameworkCode": assignment.frameworkCode,
                "configured": fw_configured,
                "total": fw_total,
                "percentage": percentage,
            }
        )

        df = next(
            (
                d
                for d in deployment_frameworks
                if d.assignedFrameworkId and str(d.assignedFrameworkId) == str(assignment.id)
            ),
            None,
        )
        deployed_on = None
        if df and df.packages:
            live_package = next((p for p in df.packages if _get(p, "status") == "live"), None)
            if live_package:
                deployed_on = _get(live_package, "updatedAt") or _get(live_package, "createdAt")

        assignment_info = assignment.assignment or {}
        finalization = assignment.finalization or {}

        deployed_frameworks.append(
            {
                "name": assignment.frameworkName,
                "version": assignment.frameworkVersion,
                "count": 1,
                "assignedOn": _get(assignment_info, "assignedAt") or assignment.createdAt,
                "deployedOn": deployed_on,
            }
        )

        assigned_frameworks_list.append(
            {
                "id": str(assignment.id) if assignment and getattr(assignment, "id", None) else None,
                "code": assignment.frameworkCode,
                "name": assignment.frameworkName,
                "version": assignment.frameworkVersion,
                "assignmentStatus": assignment.status,
                "finalizationStatus": ("finalized" if _get(finalization, "isFinalized") else "pending"),
                "assignedAt": assignment.createdAt,
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


def _build_assignment_activities(
    assignments: list[FrameworkAssignment], users: dict[str, User], recent_activity: list[dict]
) -> None:
    for assignment in assignments:
        assignment_info = assignment.assignment or {}
        revocation = assignment.revocation or {}
        finalization = assignment.finalization or {}

        assigned_by_id = _get(assignment_info, "assignedBy")
        assigned_by = users.get(str(assigned_by_id)) if assigned_by_id else None
        assign_date = _get(assignment_info, "assignedAt") or assignment.createdAt
        if assign_date:
            recent_activity.append(
                {
                    "id": f"assign-{assignment.id}",
                    "message": f"{assigned_by.name if assigned_by else 'Admin'} assigned framework {assignment.frameworkVersion}",
                    "actor": assigned_by.email if assigned_by else "admin@example.com",
                    "timeAgo": _get_time_ago(assign_date),
                    "timestamp": assign_date,
                }
            )

        revoked_by_id = _get(revocation, "revokedBy")
        revoked_by = users.get(str(revoked_by_id)) if revoked_by_id else None
        revoke_date = _get(revocation, "revokedAt") or assignment.updatedAt
        if assignment.status == "revoked" and revoke_date:
            recent_activity.append(
                {
                    "id": f"revoke-{assignment.id}",
                    "message": f"Framework {assignment.frameworkVersion} was revoked",
                    "actor": revoked_by.email if revoked_by else "admin@example.com",
                    "timeAgo": _get_time_ago(revoke_date),
                    "timestamp": revoke_date,
                }
            )

        if _get(finalization, "isFinalized"):
            finalized_by_id = _get(finalization, "finalizedBy")
            finalized_by = users.get(str(finalized_by_id)) if finalized_by_id else None
            recent_activity.append(
                {
                    "id": f"final-{assignment.id}",
                    "message": f"Framework {assignment.frameworkVersion} finalized",
                    "actor": finalized_by.email if finalized_by else "System",
                    "timeAgo": _get_time_ago(_get(finalization, "finalizedAt")),
                    "timestamp": _get(finalization, "finalizedAt"),
                }
            )


def _build_framework_activities(
    deployment_frameworks: list[DeploymentFramework],
    users: dict[str, User],
    recent_activity: list[dict],
) -> None:
    for df in deployment_frameworks:
        uploaded_by = users.get(str(df.uploadedBy)) if df.uploadedBy else None
        if df.createdAt:
            recent_activity.append(
                {
                    "id": f"df-created-{df.id}",
                    "message": f"Deployment framework {df.frameworkVersion or df.frameworkName} uploaded",
                    "actor": uploaded_by.email if uploaded_by else "User",
                    "timeAgo": _get_time_ago(df.createdAt),
                    "timestamp": df.createdAt,
                }
            )

        for pkg in df.packages or []:
            pkg_created = _get(pkg, "createdAt")
            package_version = _get(pkg, "packageVersion")
            trigger = _get(pkg, "trigger")
            if pkg_created:
                patch_type = f" ({trigger} patch)" if trigger else ""
                recent_activity.append(
                    {
                        "id": f"pkg-created-{df.id}-{package_version}",
                        "message": f"Package {package_version}{patch_type} uploaded in {df.frameworkVersion or df.frameworkName}",
                        "actor": uploaded_by.email if uploaded_by else "User",
                        "timeAgo": _get_time_ago(pkg_created),
                        "timestamp": pkg_created,
                    }
                )

            expert_review = _get(pkg, "expertReview") or {}
            assigned_expert = _get(expert_review, "assignedExpert")
            expert = users.get(str(assigned_expert)) if assigned_expert else None
            requested_at = _get(expert_review, "requestedAt")
            if expert_review and requested_at:
                expert_name = (
                    (expert.name if expert else None) or (expert.email if expert else None) or "Expert"
                )
                recent_activity.append(
                    {
                        "id": f"pkg-review-req-{df.id}-{package_version}",
                        "message": f"Package {package_version} requested review from expert {expert_name}",
                        "actor": uploaded_by.email if uploaded_by else "User",
                        "timeAgo": _get_time_ago(requested_at),
                        "timestamp": requested_at,
                    }
                )

            reviewed_at = _get(expert_review, "reviewedAt")
            review_status = _get(expert_review, "status")
            if expert_review and reviewed_at and review_status in ("approved", "returned"):
                expert_name = (
                    (expert.name if expert else None) or (expert.email if expert else None) or "Expert"
                )
                recent_activity.append(
                    {
                        "id": f"pkg-review-res-{df.id}-{package_version}",
                        "message": f"Expert {expert_name} {review_status} package {package_version}",
                        "actor": expert.email if expert else "Expert",
                        "timeAgo": _get_time_ago(reviewed_at),
                        "timestamp": reviewed_at,
                    }
                )

            if _get(pkg, "status") == "live":
                live_date = _get(pkg, "updatedAt") or _get(pkg, "createdAt")
                recent_activity.append(
                    {
                        "id": f"pkg-live-{df.id}-{package_version}",
                        "message": f"Deployment framework package {package_version} deployed (live)",
                        "actor": "System",
                        "timeAgo": _get_time_ago(live_date),
                        "timestamp": live_date,
                    }
                )


def _build_user_activities(users: list[User], recent_activity: list[dict]) -> None:
    for user in users:
        if user.createdAt:
            recent_activity.append(
                {
                    "id": f"user-created-{user.id}",
                    "message": f"User {user.name} joined as {user.role}",
                    "actor": user.email,
                    "timeAgo": _get_time_ago(user.createdAt),
                    "timestamp": user.createdAt,
                }
            )
        if user.updatedAt and user.createdAt and (user.updatedAt - user.createdAt).total_seconds() > 1:
            action = "deactivated" if user.isActive is False else "updated"
            recent_activity.append(
                {
                    "id": f"user-updated-{user.id}",
                    "message": f"User profile {user.name} was {action}",
                    "actor": user.email,
                    "timeAgo": _get_time_ago(user.updatedAt),
                    "timestamp": user.updatedAt,
                }
            )


def _build_customer_activities(customer: Customer | None, recent_activity: list[dict]) -> None:
    if not customer:
        return
    if customer.createdAt:
        recent_activity.append(
            {
                "id": f"cust-created-{customer.id}",
                "message": f"Customer account {customer.name} created",
                "actor": "System",
                "timeAgo": _get_time_ago(customer.createdAt),
                "timestamp": customer.createdAt,
            }
        )
    if (
        customer.updatedAt
        and customer.createdAt
        and (customer.updatedAt - customer.createdAt).total_seconds() > 1
    ):
        recent_activity.append(
            {
                "id": f"cust-updated-{customer.id}",
                "message": f"Customer profile {customer.name} was updated",
                "actor": "System",
                "timeAgo": _get_time_ago(customer.updatedAt),
                "timestamp": customer.updatedAt,
            }
        )


def _build_system_activities(
    deployment_frameworks: list[DeploymentFramework],
    document_extractions: list[DocumentExtraction],
    package_comparisons: list[PackageComparison],
    package_gap_analyses: list[PackageGapAnalysis],
    package_merges: list[PackageMerge],
    recent_activity: list[dict],
) -> None:
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

    def get_suffix(m: dict[str, dict], doc_id: Any) -> str:
        info = m.get(str(doc_id))
        if not info:
            return ""
        trigger = _get(info["pkg"], "trigger")
        patch_type = f" ({trigger} patch)" if trigger else ""
        fw_label = info["df"].frameworkVersion or info["df"].frameworkName
        return f" for Package {_get(info['pkg'], 'packageVersion')}{patch_type} in {fw_label}"

    for dex in document_extractions:
        if dex.createdAt:
            ai_status = _get(dex.aiExtraction, "status") or "completed"
            recent_activity.append(
                {
                    "id": f"dex-{dex.id}",
                    "message": f"Document AI extraction {ai_status}",
                    "actor": "AI Engine",
                    "timeAgo": _get_time_ago(dex.createdAt),
                    "timestamp": dex.createdAt,
                }
            )

    for pc in package_comparisons:
        if pc.createdAt:
            suffix = get_suffix(pc_map, pc.id)
            status = _get(pc.comparison, "status") or "started"
            recent_activity.append(
                {
                    "id": f"pc-{pc.id}",
                    "message": f"Package comparison {status}{suffix}",
                    "actor": "System",
                    "timeAgo": _get_time_ago(pc.createdAt),
                    "timestamp": pc.createdAt,
                }
            )

    for pga in package_gap_analyses:
        if pga.createdAt:
            suffix = get_suffix(pga_map, pga.id)
            status = _get(pga.gapAnalysis, "status") or "started"
            recent_activity.append(
                {
                    "id": f"pga-{pga.id}",
                    "message": f"Gap analysis {status}{suffix}",
                    "actor": "System",
                    "timeAgo": _get_time_ago(pga.createdAt),
                    "timestamp": pga.createdAt,
                }
            )

    for pm in package_merges:
        if pm.createdAt:
            suffix = get_suffix(pm_map, pm.id)
            status = _get(pm.mergeExtraction, "status") or "started"
            recent_activity.append(
                {
                    "id": f"pm-{pm.id}",
                    "message": f"Package merge {status}{suffix}",
                    "actor": "System",
                    "timeAgo": _get_time_ago(pm.createdAt),
                    "timestamp": pm.createdAt,
                }
            )


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


@router.get("/analytics")
async def get_customer_admin_dashboard(ctx: RequestContext = Depends(get_context)):
    try:
        tenant_id = ctx.tenant_id
        user = ctx.user

        async with session_scope() as session:
            users = list(
                (await session.execute(select(User).where(User.tenantId == tenant_id, User.id != user.id)))
                .scalars()
                .all()
            )
            customer = (
                await session.execute(select(Customer).where(Customer.tenantId == tenant_id))
            ).scalar_one_or_none()
            deployment_frameworks = list(
                (
                    await session.execute(
                        select(DeploymentFramework).where(DeploymentFramework.tenantId == tenant_id)
                    )
                )
                .scalars()
                .all()
            )
            assignments = list(
                (
                    await session.execute(
                        select(FrameworkAssignment).where(
                            or_(
                                FrameworkAssignment.tenantId == tenant_id,
                                FrameworkAssignment.customerId
                                == str(getattr(user, "customerId", None) or ""),
                            )
                            if getattr(user, "customerId", None)
                            else FrameworkAssignment.tenantId == tenant_id
                        )
                    )
                )
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

            document_extractions = []
            if file_hashes:
                document_extractions = list(
                    (
                        await session.execute(
                            select(DocumentExtraction).where(
                                DocumentExtraction.fileHash.in_(list(file_hashes))
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

            package_comparisons = []
            package_gap_analyses = []
            package_merges = []
            if framework_ids:
                package_comparisons = list(
                    (
                        await session.execute(
                            select(PackageComparison).where(PackageComparison.frameworkId.in_(framework_ids))
                        )
                    )
                    .scalars()
                    .all()
                )
                package_gap_analyses = list(
                    (
                        await session.execute(
                            select(PackageGapAnalysis).where(
                                PackageGapAnalysis.frameworkId.in_(framework_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                package_merges = list(
                    (
                        await session.execute(
                            select(PackageMerge).where(PackageMerge.frameworkId.in_(framework_ids))
                        )
                    )
                    .scalars()
                    .all()
                )

            package_merges_map = {str(pm.id): pm for pm in package_merges}

            active_assignments = [a for a in assignments if a.status == "assigned"]
            user_stats = _process_user_stats(users)
            progress = _process_assignments_and_progress(
                active_assignments, deployment_frameworks, package_merges_map
            )

            user_ids: set[str] = set()
            for a in assignments:
                assigned_by = _get(a.assignment, "assignedBy")
                revoked_by = _get(a.revocation, "revokedBy")
                finalized_by = _get(a.finalization, "finalizedBy")
                if assigned_by:
                    user_ids.add(assigned_by)
                if revoked_by:
                    user_ids.add(revoked_by)
                if finalized_by:
                    user_ids.add(finalized_by)
            for df in deployment_frameworks:
                if df.uploadedBy:
                    user_ids.add(df.uploadedBy)
                for pkg in df.packages or []:
                    expert_review = _get(pkg, "expertReview") or {}
                    assigned_expert = _get(expert_review, "assignedExpert")
                    if assigned_expert:
                        user_ids.add(assigned_expert)

            activity_users_map: dict[str, User] = {}
            if user_ids:
                fetched = (
                    (await session.execute(select(User).where(User.id.in_(list(user_ids))))).scalars().all()
                )
                activity_users_map = {str(u.id): u for u in fetched}

            recent_activity: list[dict[str, Any]] = []
            _build_assignment_activities(assignments, activity_users_map, recent_activity)
            _build_framework_activities(deployment_frameworks, activity_users_map, recent_activity)
            _build_user_activities(users, recent_activity)
            _build_customer_activities(customer, recent_activity)
            _build_system_activities(
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
