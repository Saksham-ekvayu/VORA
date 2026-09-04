from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.database import session_scope
from vora_shared.models import (
    DeploymentFramework,
    DeploymentPackageMerge,
    FrameworkAssignment,
    PackageGapAnalysis,
    User,
)
from vora_shared.responses import success

from ..helpers import (
    extract_actual_implemented,
    extract_custom_controls,
    extract_expected_controls,
)

router = APIRouter(tags=["internal-expert-dashboard"])
logger = logging.getLogger(__name__)


@router.get("/analytics")
async def get_internal_expert_dashboard_analytics(
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    start_date: Annotated[str | None, Query(alias="startDate")] = None,
    end_date: Annotated[str | None, Query(alias="endDate")] = None,
):
    logger.info(
        f"[INTERNAL-EXPERT-ANALYTICS] Dashboard request | user_id={auth.user.id} | start_date={start_date} | end_date={end_date}"
    )

    user = auth.user

    async with session_scope() as session:
        # Fetch DeploymentFrameworks where any package has expertReview.assignedExpert == current user id
        stmt = select(DeploymentFramework).where(
            text("packages @> CAST(:match AS jsonb)").bindparams(match=f'[{{"expertReview": {{"assignedExpert": "{user.id}"}}}}]')
        )
        dfs = list((await session.execute(stmt)).scalars().all())

        review_requests = []
        metrics = {
            "pendingReview": 0,
            "inReview": 0,
            "approved": 0,
            "returned": 0,
        }

        user_ids = {df.uploadedBy for df in dfs}
        users_by_id = {}
        if user_ids:
            users = (await session.execute(select(User).where(User.id.in_(list(user_ids))))).scalars().all()
            users_by_id = {str(u.id): u for u in users}

        ga_ids = set()
        merge_ids = set()
        assignment_ids = set()

        for df in dfs:
            assignment_ids.add(df.assignedFrameworkId)
            for pkg in df.packages:
                if isinstance(pkg, dict):
                    expert_review = pkg.get("expertReview", {})
                    if expert_review.get("assignedExpert") == str(user.id):
                        if pkg.get("gapAnalysis"):
                            ga_ids.add(pkg["gapAnalysis"])
                        if pkg.get("mergeDocument"):
                            merge_ids.add(pkg["mergeDocument"])

        merges = []
        if merge_ids:
            merges = (await session.execute(select(DeploymentPackageMerge).where(DeploymentPackageMerge.id.in_(list(merge_ids))))).scalars().all()

        gas = []
        if ga_ids:
            gas = (await session.execute(select(PackageGapAnalysis).where(PackageGapAnalysis.id.in_(list(ga_ids))))).scalars().all()

        assignments = []
        if assignment_ids:
            assignments = (await session.execute(select(FrameworkAssignment).where(FrameworkAssignment.id.in_(list(assignment_ids))))).scalars().all()

        merges_by_id = {str(m.id): m for m in merges}
        gas_by_id = {str(g.id): g for g in gas}

        for df in dfs:
            uploader = users_by_id.get(str(df.uploadedBy))
            custom_controls = extract_custom_controls(str(df.assignedFrameworkId), assignments)

            for pkg in df.packages:
                if not isinstance(pkg, dict):
                    continue
                expert_review = pkg.get("expertReview", {})
                if expert_review.get("assignedExpert") != str(user.id):
                    continue

                status = expert_review.get("status", "pending")
                status_lower = status.lower()

                # Calculate metrics
                if status_lower in ["requested"]:
                    metrics["pendingReview"] += 1
                elif status_lower in ["pending", "in_review"]:
                    metrics["inReview"] += 1
                elif status_lower == "approved":
                    metrics["approved"] += 1
                elif status_lower in ["rejected", "returned"]:
                    metrics["returned"] += 1
                else:
                    metrics["inReview"] += 1 # fallback

                # Format status for UI
                ui_status = "In Review" if status_lower in ["pending", "in_review"] else status.capitalize()
                if status_lower == "requested":
                    ui_status = "Pending"
                elif status_lower == "rejected":
                    ui_status = "Returned"

                # Compute health
                health = 0
                ga_id = pkg.get("gapAnalysis")
                merge_id = pkg.get("mergeDocument")

                if ga_id and merge_id and ga_id in gas_by_id and merge_id in merges_by_id:
                    merge_doc = merges_by_id[merge_id]
                    ga_doc = gas_by_id[ga_id]

                    ga_results = ga_doc.gapAnalysis.get("deployment_gap_results", []) if ga_doc.gapAnalysis else []

                    total_dps = len(ga_results)
                    impl_dps = sum(
                        1
                        for result in ga_results
                        if str(result.get("implementation_status") or "").lower()
                        in ["implemented", "compliant", "passed", "fully implemented"]
                    )

                    if total_dps > 0:
                        health = round((impl_dps / total_dps) * 100)

                req_at = expert_review.get("requestedAt") or pkg.get("createdAt")

                review_requests.append({
                    "id": str(df.id),
                    "frameworkName": df.frameworkName,
                    "frameworkVersion": df.frameworkVersion,
                    "packageVersion": pkg.get("packageVersion", "1.0.0"),
                    "packageStatus": pkg.get("status", "pending"),
                    "requestedBy": {
                        "id": str(uploader.id) if uploader else "",
                        "name": uploader.name if uploader else "Unknown",
                        "email": uploader.email if uploader else "",
                        "avatar": uploader.avatar if uploader else "",
                    },
                    "requestedAt": req_at,
                    "status": ui_status,
                    "health": health,
                })

    return success({
        "metrics": metrics,
        "reviewRequests": sorted(review_requests, key=lambda x: str(x.get("requestedAt", "")), reverse=True)
    }, "Dashboard data retrieved successfully")
