"""Ports of Node's dashboard-filter.helper.js and admin-dashboard aggregation helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Select, func, select
from vora_shared.database import session_scope
from vora_shared.models import (
    Customer,
    DeploymentDocument,
    DeploymentFramework,
    Framework,
    FrameworkAccess,
    FrameworkAssignment,
    FrameworkCategory,
    User,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def to_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def apply_date_filters(
    stmt: Select,
    model: type,
    start_date: datetime | None,
    end_date: datetime | None,
) -> Select:
    start = to_aware_utc(start_date)
    end = to_aware_utc(end_date)
    created_at = getattr(model, "createdAt")
    if start is not None:
        stmt = stmt.where(created_at >= start)
    if end is not None:
        stmt = stmt.where(created_at <= end)
    return stmt


def filter_array_by_date(
    data: list[Any], start_date: datetime | None, end_date: datetime | None
) -> list[Any]:
    if not start_date and not end_date:
        return data

    start = to_aware_utc(start_date)
    end = to_aware_utc(end_date)

    def in_range(item: Any) -> bool:
        item_date = item.createdAt
        if item_date is None:
            return False
        item_date = to_aware_utc(item_date)
        if start and item_date < start:
            return False
        if end and item_date > end:
            return False
        return True

    return [item for item in data if in_range(item)]


def get_effective_start_date(default_start: datetime, user_start_date: datetime | None) -> datetime:
    if not user_start_date:
        return default_start
    return user_start_date if user_start_date > default_start else default_start


async def _count_model(model: type, start_date: datetime | None, end_date: datetime | None, **extra) -> int:
    async with session_scope() as session:
        stmt = select(func.count()).select_from(model)
        stmt = apply_date_filters(stmt, model, start_date, end_date)
        for key, value in extra.items():
            stmt = stmt.where(getattr(model, key) == value)
        return (await session.execute(stmt)).scalar_one()


async def get_model_counts(start_date: datetime | None, end_date: datetime | None) -> dict[str, int]:
    (
        total_frameworks,
        total_deployment_frameworks,
        total_deployment_documents,
        total_framework_categories,
        total_approved_framework_access,
        total_assigned_frameworks,
        total_customers,
    ) = await asyncio.gather(
        _count_model(Framework, start_date, end_date),
        _count_model(DeploymentFramework, start_date, end_date),
        _count_model(DeploymentDocument, start_date, end_date),
        _count_model(FrameworkCategory, start_date, end_date),
        _count_model(FrameworkAccess, start_date, end_date, status="approved"),
        _count_model(FrameworkAssignment, start_date, end_date, status="assigned"),
        _count_model(Customer, start_date, end_date),
    )

    return {
        "totalFrameworks": total_frameworks,
        "totalDeploymentFrameworks": total_deployment_frameworks,
        "totalDeploymentDocuments": total_deployment_documents,
        "totalFrameworkCategories": total_framework_categories,
        "totalApprovedFrameworkAccess": total_approved_framework_access,
        "totalAssignedFrameworks": total_assigned_frameworks,
        "totalCustomers": total_customers,
    }


def calculate_role_stats(all_users: list[User]) -> dict[str, int]:
    role_stats: dict[str, int] = {
        "admin": 0,
        "customer-admin": 0,
        "expert": 0,
        "user": 0,
    }
    for user in all_users:
        role_stats[user.role] = role_stats.get(user.role, 0) + 1
    return role_stats


def format_recent_users(all_users: list[User]) -> list[dict[str, Any]]:
    sorted_by_date = sorted(
        all_users,
        key=lambda u: u.createdAt or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return [
        {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "avatar": user.avatar,
            "createdAt": user.createdAt,
        }
        for user in sorted_by_date[:5]
    ]


def generate_chart_labels(start_date: datetime | None = None, end_date: datetime | None = None) -> list[str]:
    end = end_date or utcnow()
    start = start_date or (end - timedelta(days=29))

    start_aware = to_aware_utc(start)
    end_aware = to_aware_utc(end)

    delta = (end_aware.date() - start_aware.date()).days
    if delta < 0:
        return []

    return [(start_aware + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(delta + 1)]


def initialize_chart_data(chart_labels: list[str]) -> dict[str, int]:
    return dict.fromkeys(chart_labels, 0)


def get_creation_type(user: User) -> str:
    created_by = user.createdBy
    if not created_by:
        return "self"
    if isinstance(created_by, str):
        return created_by
    if isinstance(created_by, dict):
        return created_by.get("type") or "self"
    return getattr(created_by, "type", None) or "self"


def populate_chart_data(recent_users: list[User], chart_labels: list[str]) -> dict[str, dict[str, int]]:
    total_data = initialize_chart_data(chart_labels)

    label_set = set(chart_labels)
    for user in recent_users:
        if not user.createdAt:
            continue
        date_label = to_aware_utc(user.createdAt).strftime("%Y-%m-%d")
        if date_label not in label_set:
            continue
        total_data[date_label] += 1

    return {
        "totalData": total_data,
    }


def get_chart_values(chart_labels: list[str], data: dict[str, int]) -> list[int]:
    return [data[label] for label in chart_labels]


def build_response_data(
    stats: dict[str, Any],
    chart_labels: list[str],
    chart_data: dict[str, dict[str, int]],
    recent_created_users: list[dict[str, Any]],
    customers: list[Customer],
) -> dict[str, Any]:
    return {
        "stats": stats,
        "charts": {
            "userCreation": {
                "labels": chart_labels,
                "total": get_chart_values(chart_labels, chart_data["totalData"]),
            }
        },
        "recentCreatedUsers": recent_created_users,
        "customers": [
            {
                "id": str(c.id),
                "tenantId": str(c.tenantId) if c and getattr(c, "tenantId", None) else None,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "secondaryPhone": c.secondaryPhone,
                "isActive": c.isActive,
                "createdAt": c.createdAt,
                "avatar": c.avatar,
            }
            for c in customers
        ],
    }


# Back-compat aliases used by admin router during migration
def build_date_filter(
    start_date: datetime | None,
    end_date: datetime | None,
    base_filter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "start_date": start_date,
        "end_date": end_date,
        **(base_filter or {}),
    }


def build_admin_user_filter(
    admin_user_id: str, start_date: datetime | None, end_date: datetime | None
) -> dict[str, Any]:
    return {
        "exclude_user_id": str(admin_user_id),
        "start_date": start_date,
        "end_date": end_date,
    }
