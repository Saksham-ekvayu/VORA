"""Port of expert-dashboard.controller.js."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.database import session_scope
from vora_shared.models import FrameworkAccess, FrameworkCategory, User
from vora_shared.models.framework import Framework
from vora_shared.responses import success

router = APIRouter(tags=["expert-dashboard"])

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _approval_status(fw: Framework) -> str | None:
    approval = fw.approval or {}
    if isinstance(approval, dict):
        return approval.get("status")
    return getattr(approval, "status", None)


def _approval_by(fw: Framework) -> str | None:
    approval = fw.approval or {}
    if isinstance(approval, dict):
        return approval.get("by")
    return getattr(approval, "by", None)


def _approval_date(fw: Framework):
    approval = fw.approval or {}
    if isinstance(approval, dict):
        return approval.get("date")
    return getattr(approval, "date", None)


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


def _generate_upload_trend(frameworks: list[Framework], start_date: str | None, end_date: str | None) -> list[dict]:
    trend_end = datetime.fromisoformat(end_date) if end_date else datetime.now(timezone.utc).replace(tzinfo=None)
    trend_start = (
        datetime.fromisoformat(start_date)
        if start_date
        else _subtract_months(trend_end, 5)
    )

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
            1
            for fw in frameworks
            if fw.createdAt and month_start <= _naive(fw.createdAt) < month_end
        )
        label = (
            f"{MONTH_NAMES[month_date.month - 1]} {month_date.year}"
            if len(months) > 12
            else MONTH_NAMES[month_date.month - 1]
        )
        result.append({"month": label, "uploads": uploads})
    return result


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _add_month(d: datetime) -> datetime:
    if d.month == 12:
        return datetime(d.year + 1, 1, 1)
    return datetime(d.year, d.month + 1, 1)


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
            "uploadedBy": (users_by_id.get(fw.uploadedBy).name if users_by_id.get(fw.uploadedBy) else "Unknown"),
            "date": _fmt_date(fw.createdAt),
            "status": _title_case(_approval_status(fw)),
        }
        for fw in sorted_fw
    ]


def _format_approved_frameworks(frameworks: list[Framework], users_by_id: dict) -> list[dict]:
    approved = [fw for fw in frameworks if _approval_status(fw) == "approved"]

    def _sort_key(f: Framework):
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

    approved.sort(key=_sort_key, reverse=True)
    approved = approved[:5]
    return [
        {
            "id": str(fw.id) if fw and getattr(fw, "id", None) else None,
            "frameworkName": fw.frameworkName,
            "frameworkCode": fw.frameworkCode or "",
            "frameworkVersion": fw.frameworkVersion or "",
            "approvedBy": (
                users_by_id.get(_approval_by(fw)).name
                if _approval_by(fw) and users_by_id.get(_approval_by(fw))
                else "Unknown"
            ),
            "date": _fmt_date(_approval_date(fw) or fw.updatedAt),
            "status": "Approved",
        }
        for fw in approved
    ]


@router.get("/analytics")
async def get_expert_dashboard_analytics(
    auth: AuthenticatedUser = Depends(authenticate),
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
):
    user = auth.user

    async with session_scope() as session:
        fw_stmt = select(Framework).where(Framework.uploadedBy == user.id)
        fw_stmt = _apply_date_filter(fw_stmt, Framework, startDate, endDate)
        frameworks = list((await session.execute(fw_stmt)).scalars().all())

        access_stmt = select(FrameworkAccess).where(FrameworkAccess.expertId == user.id)
        access_stmt = _apply_date_filter(access_stmt, FrameworkAccess, startDate, endDate)
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
            users = (
                await session.execute(select(User).where(User.id.in_(list(user_ids))))
            ).scalars().all()
            users_by_id = {u.id: u for u in users}

    total_uploads = len(frameworks)
    approved_uploads = sum(1 for fw in frameworks if _approval_status(fw) == "approved")
    approval_progress = round((approved_uploads / total_uploads) * 100) if total_uploads else 0

    return success(
        {
            "stats": {
                "totalCategories": total_categories,
                "totalUploads": total_uploads,
                "approvedUploads": approved_uploads,
                "approvalProgress": approval_progress,
            },
            "uploadTrend": _generate_upload_trend(frameworks, startDate, endDate),
            "accessStatus": _build_access_status_counts(access_records),
            "recentUploads": _format_recent_uploads(frameworks, users_by_id),
            "approvedFrameworks": _format_approved_frameworks(frameworks, users_by_id),
        },
        "Expert dashboard data retrieved successfully",
    )
