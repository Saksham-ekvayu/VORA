"""Port of expert-dashboard.controller.js."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.database import session_scope
from vora_shared.models import FrameworkAccess, FrameworkCategory, User
from vora_shared.models.framework import Framework
from vora_shared.responses import success

router = APIRouter(tags=["expert-dashboard"])
logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def _get_approval_field(fw: Framework, field: str) -> str | None:
    """Get a field from the approval object safely."""
    approval = fw.approval or {}
    if isinstance(approval, dict):
        return approval.get(field)
    return getattr(approval, field, None)


def _approval_status(fw: Framework) -> str | None:
    return _get_approval_field(fw, "status")


def _approval_by(fw: Framework) -> str | None:
    return _get_approval_field(fw, "by")


def _approval_date(fw: Framework):
    return _get_approval_field(fw, "date")


def _apply_date_filter(stmt, model, start_date: str | None, end_date: str | None):
    if start_date:
        stmt = stmt.where(model.createdAt >= datetime.fromisoformat(start_date))
    if end_date:
        stmt = stmt.where(model.createdAt <= datetime.fromisoformat(end_date))
    return stmt


def _title_case(value: str | None) -> str:
    if not value:
        return "Pending"
    return value[0].upper() + value[1:].lower()


def _fmt_date(value) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    if not hasattr(value, "strftime"):
        return str(value)
    return f"{MONTH_NAMES[value.month - 1]} {value.day}, {value.year}"


def _subtract_months(d: datetime, months: int) -> datetime:
    total = d.year * 12 + (d.month - 1) - months
    year, month = divmod(total, 12)
    return datetime(year, month + 1, 1)


def _add_month(d: datetime) -> datetime:
    if d.month == 12:
        return datetime(d.year + 1, 1, 1)
    return datetime(d.year, d.month + 1, 1)


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _generate_upload_trend(
    frameworks: list[Framework], start_date: str | None, end_date: str | None
) -> list[dict]:
    trend_end = (
        datetime.fromisoformat(end_date) if end_date else datetime.now(timezone.utc).replace(tzinfo=None)
    )
    trend_start = datetime.fromisoformat(start_date) if start_date else _subtract_months(trend_end, 5)

    start_month = datetime(trend_start.year, trend_start.month, 1)
    end_month = datetime(trend_end.year, trend_end.month, 1)

    months = []
    cursor = start_month
    while cursor <= end_month:
        months.append(cursor)
        cursor = _add_month(cursor)

    result = []
    for month_date in months:
        month_start = datetime(month_date.year, month_date.month, 1)
        month_end = _add_month(month_start)
        uploads = sum(
            1 for fw in frameworks if fw.createdAt and month_start <= _naive(fw.createdAt) < month_end
        )
        label = (
            f"{MONTH_NAMES[month_date.month - 1]} {month_date.year}"
            if len(months) > 12
            else MONTH_NAMES[month_date.month - 1]
        )
        result.append({"month": label, "uploads": uploads})
    return result


def _build_access_status_counts(access_records: list) -> dict:
    counts = {"approved": 0, "pending": 0, "rejected": 0, "revoked": 0}
    for record in access_records:
        status = record.status or "pending"
        if status in counts:
            counts[status] += 1
    return counts


def _format_recent_uploads(frameworks: list[Framework], users_by_id: dict) -> list[dict]:
    sorted_fw = sorted(
        frameworks,
        key=lambda f: f.createdAt or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )[:5]
    return [
        {
            "id": str(fw.id) if fw and getattr(fw, "id", None) else None,
            "frameworkName": fw.frameworkName,
            "frameworkCode": fw.frameworkCode or "",
            "frameworkVersion": fw.frameworkVersion or "",
            "uploadedBy": (
                users_by_id.get(fw.uploadedBy).name if users_by_id.get(fw.uploadedBy) else "Unknown"
            ),
            "date": _fmt_date(fw.createdAt),
            "status": _title_case(_approval_status(fw)),
        }
        for fw in sorted_fw
    ]


def _get_approved_frameworks(frameworks: list[Framework]) -> list[Framework]:
    """Filter and return only approved frameworks."""
    return [fw for fw in frameworks if _approval_status(fw) == "approved"]


def _get_approval_sort_key(f: Framework):
    """Get sort key for approved frameworks based on approval date."""
    date_val = _approval_date(f) or f.updatedAt
    if isinstance(date_val, str):
        try:
            date_val = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except ValueError:
            date_val = datetime.min.replace(tzinfo=timezone.utc)
    if date_val is None:
        date_val = datetime.min.replace(tzinfo=timezone.utc)
    if getattr(date_val, "tzinfo", None) is None:
        date_val = date_val.replace(tzinfo=timezone.utc)
    return date_val


def _sort_approved_frameworks(approved: list[Framework]) -> list[Framework]:
    """Sort approved frameworks by approval date descending."""
    approved.sort(key=_get_approval_sort_key, reverse=True)
    return approved[:5]


def _get_approver_name(fw: Framework, users_by_id: dict) -> str:
    """Get the approver's name for a framework."""
    approver_id = _approval_by(fw)
    if approver_id and users_by_id.get(approver_id):
        return users_by_id[approver_id].name
    return "Unknown"


def _format_single_approved_framework(fw: Framework, users_by_id: dict) -> dict:
    """Format a single approved framework."""
    return {
        "id": str(fw.id) if fw and getattr(fw, "id", None) else None,
        "frameworkName": fw.frameworkName,
        "frameworkCode": fw.frameworkCode or "",
        "frameworkVersion": fw.frameworkVersion or "",
        "approvedBy": _get_approver_name(fw, users_by_id),
        "date": _fmt_date(_approval_date(fw) or fw.updatedAt),
        "status": "Approved",
    }


def _format_approved_frameworks(frameworks: list[Framework], users_by_id: dict) -> list[dict]:
    """Format approved frameworks for the dashboard."""
    approved = _get_approved_frameworks(frameworks)
    approved = _sort_approved_frameworks(approved)
    return [_format_single_approved_framework(fw, users_by_id) for fw in approved]


@router.get("/analytics")
async def get_expert_dashboard_analytics(
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    start_date: Annotated[str | None, Query(alias="startDate")] = None,
    end_date: Annotated[str | None, Query(alias="endDate")] = None,
):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[EXPERT-ANALYTICS] Dashboard request | user_id={auth.user.id} | start_date={start_date} | end_date={end_date}")
    
    user = auth.user

    async with session_scope() as session:
        fw_stmt = select(Framework).where(Framework.uploadedBy == user.id)
        fw_stmt = _apply_date_filter(fw_stmt, Framework, start_date, end_date)
        frameworks = list((await session.execute(fw_stmt)).scalars().all())

        access_stmt = select(FrameworkAccess).where(FrameworkAccess.expertId == user.id)
        access_stmt = _apply_date_filter(access_stmt, FrameworkAccess, start_date, end_date)
        access_records = list((await session.execute(access_stmt)).scalars().all())

        total_categories = (
            await session.execute(select(func.count()).select_from(FrameworkCategory))
        ).scalar_one()

        user_ids = {fw.uploadedBy for fw in frameworks}
        for fw in frameworks:
            by_id = _approval_by(fw)
            if by_id:
                user_ids.add(by_id)
        users_by_id = {}
        if user_ids:
            users = (await session.execute(select(User).where(User.id.in_(list(user_ids))))).scalars().all()
            users_by_id = {u.id: u for u in users}

    total_uploads = len(frameworks)
    approved_uploads = sum(1 for fw in frameworks if _approval_status(fw) == "approved")
    approval_progress = round((approved_uploads / total_uploads) * 100) if total_uploads else 0

    logger.info(f"[EXPERT-ANALYTICS] Dashboard loaded | uploads={total_uploads} | approved={approved_uploads} | progress={approval_progress}%")
    return success(
        {
            "stats": {
                "totalCategories": total_categories,
                "totalUploads": total_uploads,
                "approvedUploads": approved_uploads,
                "approvalProgress": approval_progress,
            },
            "uploadTrend": _generate_upload_trend(frameworks, start_date, end_date),
            "accessStatus": _build_access_status_counts(access_records),
            "recentUploads": _format_recent_uploads(frameworks, users_by_id),
            "approvedFrameworks": _format_approved_frameworks(frameworks, users_by_id),
        },
        "Expert dashboard data retrieved successfully",
    )
