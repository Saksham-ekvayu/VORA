"""Port of framework-access.controller.js + framework-access.routes.js."""

from __future__ import annotations
from typing import Annotated

from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared import data_format, messages as msg
from app.services import authorization
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from vora_shared.database import session_scope
from vora_shared.models import FrameworkAccess, FrameworkCategory, User
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import error, paginated, success

router = APIRouter(tags=["framework-access"])


def _nested_user_id(blob: dict | None, key: str) -> str | None:
    if not blob or not isinstance(blob, dict):
        return None
    return blob.get(key)


async def _get_matching_user_ids(session, pattern: str) -> list[str]:
    """Get user IDs matching search pattern."""
    return list(
        (
            await session.execute(
                select(User.id).where(
                    or_(User.name.ilike(pattern), User.email.ilike(pattern))
                )
            )
        )
        .scalars()
        .all()
    )


async def _get_matching_category_ids(session, pattern: str) -> list[str]:
    """Get category IDs matching search pattern."""
    return list(
        (
            await session.execute(
                select(FrameworkCategory.id).where(
                    or_(
                        FrameworkCategory.code.ilike(pattern),
                        FrameworkCategory.frameworkCategoryName.ilike(pattern),
                        FrameworkCategory.description.ilike(pattern),
                    )
                )
            )
        )
        .scalars()
        .all()
    )


def _build_search_conditions(
    pattern: str, matching_user_ids: list[str], matching_category_ids: list[str]
) -> list:
    """Build search conditions for framework access query."""
    conditions = [FrameworkAccess.frameworkCode.ilike(pattern)]
    
    if matching_user_ids:
        conditions.extend(
            [
                FrameworkAccess.approval["approvedBy"].astext.in_(matching_user_ids),
                FrameworkAccess.rejection["rejectedBy"].astext.in_(matching_user_ids),
                FrameworkAccess.revocation["revokedBy"].astext.in_(matching_user_ids),
            ]
        )
    
    if matching_category_ids:
        conditions.append(
            FrameworkAccess.frameworkCategoryId.in_(matching_category_ids)
        )
    
    return conditions


def _apply_sorting(stmt, sort_by: str | None, sort_order: str | None):
    """Apply sorting to the query."""
    sort_field = "createdAt"
    allowed_sort_fields = {"createdAt", "frameworkCode", "status"}
    if sort_by in allowed_sort_fields:
        sort_field = sort_by
    
    col = getattr(FrameworkAccess, sort_field)
    if (sort_order or "desc").lower() == "asc":
        return stmt.order_by(col.asc())
    return stmt.order_by(col.desc())


async def _get_records_with_filters(
    session, user_id: str, status: str | None, framework_category_id: str | None,
    search: str | None, sort_by: str | None, sort_order: str | None,
    page_num: int, limit_num: int
) -> tuple[list, int]:
    """Get filtered and paginated records."""
    stmt = select(FrameworkAccess).where(FrameworkAccess.expertId == user_id)
    
    if status:
        stmt = stmt.where(FrameworkAccess.status == status)
    
    if framework_category_id:
        stmt = stmt.where(FrameworkAccess.frameworkCategoryId == str(framework_category_id))

    if search:
        pattern = f"%{search}%"
        matching_user_ids = await _get_matching_user_ids(session, pattern)
        matching_category_ids = await _get_matching_category_ids(session, pattern)
        search_conditions = _build_search_conditions(pattern, matching_user_ids, matching_category_ids)
        stmt = stmt.where(or_(*search_conditions))

    stmt = _apply_sorting(stmt, sort_by, sort_order)

    total = (
        await session.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    
    records = list(
        (await session.execute(stmt.offset((page_num - 1) * limit_num).limit(limit_num)))
        .scalars()
        .all()
    )
    
    return records, total


def _collect_needed_ids(records: list) -> tuple[set[str], set[str]]:
    """Collect user and category IDs needed for the response."""
    user_ids_needed: set[str] = set()
    category_ids_needed: set[str] = set()
    
    for record in records:
        approved_by = _nested_user_id(record.approval, "approvedBy")
        rejected_by = _nested_user_id(record.rejection, "rejectedBy")
        revoked_by = _nested_user_id(record.revocation, "revokedBy")
        
        if approved_by:
            user_ids_needed.add(approved_by)
        if rejected_by:
            user_ids_needed.add(rejected_by)
        if revoked_by:
            user_ids_needed.add(revoked_by)
        category_ids_needed.add(record.frameworkCategoryId)
    
    return user_ids_needed, category_ids_needed


async def _fetch_users(session, user_ids: set[str]) -> dict:
    """Fetch users by IDs."""
    if not user_ids:
        return {}
    users = (
        (await session.execute(select(User).where(User.id.in_(list(user_ids)))))
        .scalars()
        .all()
    )
    return {u.id: u for u in users}


async def _fetch_categories(session, category_ids: set[str]) -> dict:
    """Fetch categories by IDs."""
    if not category_ids:
        return {}
    categories = (
        (
            await session.execute(
                select(FrameworkCategory).where(
                    FrameworkCategory.id.in_(list(category_ids))
                )
            )
        )
        .scalars()
        .all()
    )
    return {c.id: c for c in categories}


def _build_approval_data(record, users_by_id: dict) -> dict | None:
    """Build approval data for a record."""
    approved_by = _nested_user_id(record.approval, "approvedBy")
    if not approved_by:
        return None
    return {
        "approvedBy": data_format.format_user_ref(
            users_by_id.get(approved_by), approved_by
        ),
        "approvedAt": (record.approval or {}).get("approvedAt"),
    }


def _build_rejection_data(record, users_by_id: dict) -> dict | None:
    """Build rejection data for a record."""
    rejected_by = _nested_user_id(record.rejection, "rejectedBy")
    if not rejected_by:
        return None
    return {
        "rejectedBy": data_format.format_user_ref(
            users_by_id.get(rejected_by), rejected_by
        ),
        "rejectedAt": (record.rejection or {}).get("rejectedAt"),
    }


def _build_revocation_data(record, users_by_id: dict) -> dict | None:
    """Build revocation data for a record."""
    revoked_by = _nested_user_id(record.revocation, "revokedBy")
    if not revoked_by:
        return None
    return {
        "revokedBy": data_format.format_user_ref(
            users_by_id.get(revoked_by), revoked_by
        ),
        "revokedAt": (record.revocation or {}).get("revokedAt"),
    }


def _build_framework_category_data(category) -> dict | None:
    """Build framework category data for response."""
    if not category:
        return None
    return {
        "id": str(category.id),
        "code": category.code,
        "frameworkCategoryName": category.frameworkCategoryName,
        "description": category.description,
    }


def _build_response_data(records: list, categories_by_id: dict, users_by_id: dict) -> list:
    """Build the response data list."""
    data = []
    for record in records:
        category = categories_by_id.get(record.frameworkCategoryId)
        
        data.append(
            {
                "id": str(record.id),
                "frameworkCategory": _build_framework_category_data(category),
                "status": record.status,
                "requestedBy": str(record.requestedBy) if record.requestedBy else None,
                "approval": _build_approval_data(record, users_by_id),
                "rejection": _build_rejection_data(record, users_by_id),
                "revocation": _build_revocation_data(record, users_by_id),
                "createdAt": record.createdAt,
                "updatedAt": record.updatedAt,
            }
        )
    return data


def _get_response_message(data: list, search: str | None, status: str | None, framework_category_id: str | None) -> str:
    """Get appropriate response message based on data and filters."""
    if data:
        return "Framework access records retrieved successfully"
    
    if search or status or framework_category_id:
        return "No framework access records match your criteria. Try adjusting your filters."
    
    return (
        "You haven't requested access to any frameworks yet. "
        "Request access to start uploading frameworks."
    )


@router.post("/{framework_category_id}/request")
async def request_framework_access(
    framework_category_id: str,
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    user = ctx.user

    async with session_scope() as session:
        category = await session.get(FrameworkCategory, str(framework_category_id))
        if not category:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)
        if not category.isActive:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_CATEGORY_IS_NOT_ACTIVE"], 400)

    try:
        access_request = await authorization.request_access(user.id, framework_category_id)
    except authorization.FrameworkAuthorizationError as exc:
        return error(str(exc), 400)

    return success(
        {
            msg.FRAMEWORK_SERVICE_MESSAGES["ID"]: (
                str(access_request.id)
                if access_request
                and getattr(access_request, msg.FRAMEWORK_SERVICE_MESSAGES["ID"], None)
                else None
            ),
            "frameworkCategoryId": (
                str(access_request.frameworkCategoryId)
                if access_request and getattr(access_request, "frameworkCategoryId", None)
                else None
            ),
            "frameworkCode": access_request.frameworkCode,
            "status": access_request.status,
            "requestedBy": (
                str(access_request.requestedBy)
                if access_request and getattr(access_request, "requestedBy", None)
                else None
            ),
            "createdAt": access_request.createdAt,
        },
        "Framework access request submitted successfully",
    )


@router.get("/my-access")
async def get_my_framework_access(
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
    page: Annotated[int, Query()] = 1,
    limit: Annotated[int, Query()] = 10,
    status: Annotated[str | None, Query()] = None,
    framework_category_id: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    sort_by: Annotated[str | None, Query()] = None,
    sort_order: Annotated[str | None, Query()] = None,
):
    user = ctx.user
    page_num = clamp_page(page)
    limit_num = clamp_limit(limit)

    async with session_scope() as session:
        records, total = await _get_records_with_filters(
            session, str(user.id), status, framework_category_id,
            search, sort_by, sort_order, page_num, limit_num
        )

        user_ids_needed, category_ids_needed = _collect_needed_ids(records)
        users_by_id = await _fetch_users(session, user_ids_needed)
        categories_by_id = await _fetch_categories(session, category_ids_needed)

        data = _build_response_data(records, categories_by_id, users_by_id)

    message = _get_response_message(data, search, status, framework_category_id)

    return paginated(data, build_pagination_meta(page_num, limit_num, total), message)