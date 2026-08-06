from datetime import datetime, timedelta
from typing import Annotated

from app.helpers import (
    apply_date_filters,
    build_response_data,
    calculate_role_stats,
    filter_array_by_date,
    format_recent_users,
    generate_chart_labels,
    get_effective_start_date,
    get_model_counts,
    populate_chart_data,
    to_naive_utc,
    utcnow,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.database import session_scope
from vora_shared.messages import MESSAGES
from vora_shared.models import Customer, User
from vora_shared.responses import error, success

router = APIRouter(tags=["dashboard-admin"])


@router.get("/analytics")
async def get_admin_dashboard_analytics(
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    start_date: Annotated[datetime | None, Query(alias="startDate")] = None,
    end_date: Annotated[datetime | None, Query(alias="endDate")] = None,
):
    try:
        start_date_utc = to_naive_utc(start_date)
        end_date_utc = to_naive_utc(end_date)

        async with session_scope() as session:
            user_stmt = select(User).where(User.id != auth.user.id)
            user_stmt = apply_date_filters(user_stmt, User, start_date_utc, end_date_utc)
            all_users = list((await session.execute(user_stmt)).scalars().all())

            customer_stmt = select(Customer)
            customer_stmt = apply_date_filters(customer_stmt, Customer, start_date_utc, end_date_utc)
            customers = list((await session.execute(customer_stmt)).scalars().all())

        model_counts = await get_model_counts(start_date_utc, end_date_utc)

        role_stats = calculate_role_stats(all_users)
        recent_created_users = format_recent_users(all_users)

        chart_end_date = end_date_utc or utcnow().replace(tzinfo=None)
        chart_start_date = start_date_utc or (chart_end_date - timedelta(days=29))

        chart_labels = generate_chart_labels(chart_start_date, chart_end_date)
        recent_users = filter_array_by_date(all_users, chart_start_date, chart_end_date)

        chart_data = populate_chart_data(recent_users, chart_labels)

        stats = {
            "totalUsers": len(all_users),
            "totalCustomers": model_counts["totalCustomers"],
            "totalFrameworks": model_counts["totalFrameworks"],
            "totalDeploymentFrameworks": model_counts["totalDeploymentFrameworks"],
            "totalDeploymentDocuments": model_counts["totalDeploymentDocuments"],
            "totalFrameworkCategories": model_counts["totalFrameworkCategories"],
            "totalApprovedFrameworkAccess": model_counts["totalApprovedFrameworkAccess"],
            "totalAssignedFrameworks": model_counts["totalAssignedFrameworks"],
            "usersByRole": role_stats,
        }

        response_data = build_response_data(stats, chart_labels, chart_data, recent_created_users, customers)

        return success(response_data, MESSAGES["DASHBOARD_ANALYTICS_SUCCESS"])
    except Exception:
        return error(MESSAGES["DASHBOARD_ANALYTICS_FAILED"], 500)