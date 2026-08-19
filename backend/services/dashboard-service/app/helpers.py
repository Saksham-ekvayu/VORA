"""Ports of Node's dashboard-filter.helper.js and admin-dashboard aggregation helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Select, func, select
from vora_shared.database import session_scope
from vora_shared.models import (
    Customer,
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
        total_framework_categories,
        total_approved_framework_access,
        total_assigned_frameworks,
        total_customers,
    ) = await asyncio.gather(
        _count_model(Framework, start_date, end_date),
        _count_model(DeploymentFramework, start_date, end_date),
        _count_model(FrameworkCategory, start_date, end_date),
        _count_model(FrameworkAccess, start_date, end_date, status="approved"),
        _count_model(FrameworkAssignment, start_date, end_date, status="assigned"),
        _count_model(Customer, start_date, end_date),
    )

    return {
        "totalFrameworks": total_frameworks,
        "totalDeploymentFrameworks": total_deployment_frameworks,
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


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Helper to safely get attributes or dictionary keys."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default) if hasattr(obj, key) else default


def extract_custom_controls(fw_assignment_id: str | None, assignments: list[FrameworkAssignment]) -> dict[str, bool]:
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
                    "is_extra": custom_controls.get(ctrl_id, False)
                }
    return expected_controls


def extract_actual_implemented(gap_results: list[Any]) -> dict[str, int]:
    """Extract actual implemented counts from current gapAnalysis."""
    actual_implemented = {}
    for result in gap_results:
        ctrl_id = _get(result, "assigned_framework_control_id")
        if not ctrl_id:
            continue
        if ctrl_id not in actual_implemented:
            actual_implemented[ctrl_id] = 0
        
        status = str(_get(result, "implementation_status") or "").lower()
        if status in ["implemented", "compliant", "passed", "fully implemented"]:
            actual_implemented[ctrl_id] += 1
            
    return actual_implemented


def extract_historical_implemented(
    df_id: str,
    current_created_at: datetime | None,
    historical_gap_analyses: list[Any]
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


def _evaluate_trend(ctrl_id: str, req_dps: int, failing_percentage: int, prev_actual_implemented: dict[str, int] | None) -> str:
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


def _create_active_gap(
    ctrl_id: str,
    expected: dict,
    req_dps: int,
    impl_dps: int,
    prev_actual_implemented: dict[str, int] | None,
    ga: Any,
    fw_name: str,
    fw_version: str
) -> dict:
    failing_percentage = 100
    if req_dps > 0:
        failing_percentage = round(((req_dps - impl_dps) / req_dps) * 100)
    
    trend = _evaluate_trend(ctrl_id, req_dps, failing_percentage, prev_actual_implemented)
        
    return {
        "id": ctrl_id,
        "framework": fw_name,
        "version": fw_version,
        "control": expected["name"],
        "description": expected["description"],
        "instances": req_dps,
        "failing": failing_percentage, 
        "lastNC": ga.createdAt.isoformat() if ga and ga.createdAt else None,
        "trend": trend
    }


def evaluate_controls(
    expected_controls: dict[str, Any],
    actual_implemented: dict[str, int],
    prev_actual_implemented: dict[str, int] | None,
    ga: Any,
    fw_name: str,
    fw_version: str
) -> tuple[int, int, int, int, int, int, int, list[dict], int]:
    """Evaluate controls against implemented DPs and return aggregated metrics."""
    fw_total_controls = 0
    fw_passing_controls = 0
    fw_total_dps = 0
    fw_implemented_dps = 0
    fw_extra_controls = 0
    fw_critical_gaps = 0
    fw_active_gaps = []
    fw_prev_implemented_dps = 0

    for ctrl_id, expected in expected_controls.items():
        fw_total_controls += 1
        if expected["is_extra"]:
            fw_extra_controls += 1
        
        req_dps = expected["required_dps"]
        impl_dps = actual_implemented.get(ctrl_id, 0)
        prev_impl = prev_actual_implemented.get(ctrl_id, 0) if prev_actual_implemented is not None else 0
        
        fw_total_dps += req_dps
        fw_implemented_dps += min(impl_dps, req_dps)
        fw_prev_implemented_dps += min(prev_impl, req_dps)
        
        if req_dps > 0 and impl_dps >= req_dps:
            fw_passing_controls += 1
        else:
            fw_critical_gaps += 1
            fw_active_gaps.append(
                _create_active_gap(
                    ctrl_id, expected, req_dps, impl_dps, 
                    prev_actual_implemented, ga, fw_name, fw_version
                )
            )

    return (
        fw_total_controls,
        fw_passing_controls,
        fw_total_dps,
        fw_implemented_dps,
        fw_extra_controls,
        fw_critical_gaps,
        fw_active_gaps,
        fw_prev_implemented_dps
    )
