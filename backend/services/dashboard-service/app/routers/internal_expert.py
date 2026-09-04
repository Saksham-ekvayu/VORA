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

from ..helpers import calculate_package_health

router = APIRouter(tags=["internal-expert-dashboard"])
logger = logging.getLogger(__name__)


def _extract_metrics_and_status(status: str) -> str:
    status_lower = status.lower()
    if status_lower in ["requested"]:
        return "pendingReview"
    elif status_lower == "approved":
        return "approved"
    elif status_lower in ["rejected", "returned"]:
        return "returned"
    return "inReview"


def _process_package(
    pkg, df, user_id, uploader, gas_by_id, merges_by_id, metrics, start_date=None, end_date=None
):
    if not isinstance(pkg, dict):
        return None
    expert_review = pkg.get("expertReview", {})
    if expert_review.get("assignedExpert") != str(user_id):
        return None

    req_at = expert_review.get("requestedAt") or pkg.get("createdAt")

    if start_date and str(req_at) < start_date:
        return None
    if end_date and str(req_at) > end_date:
        return None

    status = expert_review.get("status", "pending")
    metric_key = _extract_metrics_and_status(status)
    metrics[metric_key] += 1

    health = 0
    ga_id = pkg.get("gapAnalysis")
    merge_id = pkg.get("mergeDocument")
    if ga_id and merge_id and ga_id in gas_by_id and merge_id in merges_by_id:
        ga_doc = gas_by_id[ga_id]
        ga_results = ga_doc.gapAnalysis.get("deployment_gap_results", []) if ga_doc.gapAnalysis else []
        health = calculate_package_health(ga_results)

    return {
        "id": str(df.id),
        "frameworkName": df.frameworkName,
        "frameworkVersion": df.frameworkVersion,
        "packageVersion": pkg.get("packageVersion", "1.0.0"),
        "packageStatus": pkg.get("status", "pending"),
        "reviewStatus": status,
        "requestedBy": {
            "id": str(uploader.id) if uploader else "",
            "name": uploader.name if uploader else "Unknown",
            "email": uploader.email if uploader else "",
            "avatar": uploader.avatar if uploader else "",
        },
        "requestedAt": req_at,
        "health": health,
    }


def _extract_package_ids(dfs, user_id: str) -> tuple[set, set]:
    ga_ids = set()
    merge_ids = set()

    # Flatten valid packages
    valid_pkgs = (pkg for df in dfs for pkg in df.packages if isinstance(pkg, dict))

    for pkg in valid_pkgs:
        if pkg.get("expertReview", {}).get("assignedExpert") != user_id:
            continue

        if ga_id := pkg.get("gapAnalysis"):
            ga_ids.add(ga_id)

        if merge_id := pkg.get("mergeDocument"):
            merge_ids.add(merge_id)

    return ga_ids, merge_ids


async def _fetch_related_entities(session, dfs) -> dict:
    user_ids = {df.uploadedBy for df in dfs}
    users_by_id = {}
    if user_ids:
        users = (await session.execute(select(User).where(User.id.in_(list(user_ids))))).scalars().all()
        users_by_id = {str(u.id): u for u in users}

    return users_by_id


async def _fetch_gap_and_merge_data(session, ga_ids: set, merge_ids: set) -> tuple[dict, dict]:
    merges = []
    if merge_ids:
        merges = (
            (
                await session.execute(
                    select(DeploymentPackageMerge).where(DeploymentPackageMerge.id.in_(list(merge_ids)))
                )
            )
            .scalars()
            .all()
        )

    gas = []
    if ga_ids:
        gas = (
            (await session.execute(select(PackageGapAnalysis).where(PackageGapAnalysis.id.in_(list(ga_ids)))))
            .scalars()
            .all()
        )

    return {str(m.id): m for m in merges}, {str(g.id): g for g in gas}


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
            text("packages @> CAST(:match AS jsonb)").bindparams(
                match=f'[{{"expertReview": {{"assignedExpert": "{user.id}"}}}}]'
            )
        )
        dfs = list((await session.execute(stmt)).scalars().all())

        review_requests = []
        metrics = {
            "pendingReview": 0,
            "inReview": 0,
            "approved": 0,
            "returned": 0,
        }

        users_by_id = await _fetch_related_entities(session, dfs)
        ga_ids, merge_ids = _extract_package_ids(dfs, str(user.id))
        merges_by_id, gas_by_id = await _fetch_gap_and_merge_data(session, ga_ids, merge_ids)

        for df in dfs:
            uploader = users_by_id.get(str(df.uploadedBy))
            for pkg in df.packages:
                req = _process_package(
                    pkg, df, user.id, uploader, gas_by_id, merges_by_id, metrics, start_date, end_date
                )
                if req:
                    review_requests.append(req)

    return success(
        {
            "metrics": metrics,
            "reviewRequests": sorted(
                review_requests, key=lambda x: str(x.get("requestedAt", "")), reverse=True
            ),
        },
        "Dashboard data retrieved successfully",
    )
