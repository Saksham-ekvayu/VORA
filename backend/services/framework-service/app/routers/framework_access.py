"""Port of framework-access.controller.js + framework-access.routes.js."""

from __future__ import annotations

from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared import data_format
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


@router.post("/{framework_category_id}/request")
async def request_framework_access(
    framework_category_id: str,
    ctx: AuthenticatedUser = Depends(authenticate),
):
    user = ctx.user

    async with session_scope() as session:
        category = await session.get(FrameworkCategory, str(framework_category_id))
        if not category:
            return error("Framework category not found", 404)
        if not category.isActive:
            return error("Framework category is not active", 400)

    try:
        access_request = await authorization.request_access(user.id, framework_category_id)
    except authorization.FrameworkAuthorizationError as exc:
        return error(str(exc), 400)

    return success(
        {
            "id": str(access_request.id) if access_request and getattr(access_request, "id", None) else None,
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
    ctx: AuthenticatedUser = Depends(authenticate),
    page: int = Query(1),
    limit: int = Query(10),
    status: str | None = Query(default=None),
    frameworkCategoryId: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sortBy: str | None = Query(default=None),
    sortOrder: str | None = Query(default=None),
):
    page_num = clamp_page(page)
    limit_num = clamp_limit(limit)

    async with session_scope() as session:
        stmt = select(FrameworkAccess).where(FrameworkAccess.expertId == user.id)
        if status:
            stmt = stmt.where(FrameworkAccess.status == status)
        if frameworkCategoryId:
            stmt = stmt.where(FrameworkAccess.frameworkCategoryId == str(frameworkCategoryId))

        if search:
            pattern = f"%{search}%"
            matching_user_ids = list(
                (
                    await session.execute(
                        select(User.id).where(or_(User.name.ilike(pattern), User.email.ilike(pattern)))
                    )
                )
                .scalars()
                .all()
            )
            matching_category_ids = list(
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

            search_conditions = [FrameworkAccess.frameworkCode.ilike(pattern)]
            if matching_user_ids:
                search_conditions.extend(
                    [
                        FrameworkAccess.approval["approvedBy"].astext.in_(matching_user_ids),
                        FrameworkAccess.rejection["rejectedBy"].astext.in_(matching_user_ids),
                        FrameworkAccess.revocation["revokedBy"].astext.in_(matching_user_ids),
                    ]
                )
            if matching_category_ids:
                search_conditions.append(FrameworkAccess.frameworkCategoryId.in_(matching_category_ids))
            stmt = stmt.where(or_(*search_conditions))

        sort_field = "createdAt"
        allowed_sort_fields = {"createdAt", "frameworkCode", "status"}
        if sortBy in allowed_sort_fields:
            sort_field = sortBy
        col = getattr(FrameworkAccess, sort_field)
        if (sortOrder or "desc").lower() == "asc":
            stmt = stmt.order_by(col.asc())
        else:
            stmt = stmt.order_by(col.desc())

        total = (
            await session.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
        ).scalar_one()
        records = list(
            (await session.execute(stmt.offset((page_num - 1) * limit_num).limit(limit_num))).scalars().all()
        )

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

        users_by_id: dict = {}
        if user_ids_needed:
            users = (
                (await session.execute(select(User).where(User.id.in_(list(user_ids_needed)))))
                .scalars()
                .all()
            )
            users_by_id = {u.id: u for u in users}

        categories_by_id: dict = {}
        if category_ids_needed:
            categories = (
                (
                    await session.execute(
                        select(FrameworkCategory).where(FrameworkCategory.id.in_(list(category_ids_needed)))
                    )
                )
                .scalars()
                .all()
            )
            categories_by_id = {c.id: c for c in categories}

        data = []
        for record in records:
            category = categories_by_id.get(record.frameworkCategoryId)
            approval = None
            approved_by = _nested_user_id(record.approval, "approvedBy")
            if approved_by:
                approval = {
                    "approvedBy": data_format.format_user_ref(users_by_id.get(approved_by), approved_by),
                    "approvedAt": (record.approval or {}).get("approvedAt"),
                }
            rejection = None
            rejected_by = _nested_user_id(record.rejection, "rejectedBy")
            if rejected_by:
                rejection = {
                    "rejectedBy": data_format.format_user_ref(users_by_id.get(rejected_by), rejected_by),
                    "rejectedAt": (record.rejection or {}).get("rejectedAt"),
                }
            revocation = None
            revoked_by = _nested_user_id(record.revocation, "revokedBy")
            if revoked_by:
                revocation = {
                    "revokedBy": data_format.format_user_ref(users_by_id.get(revoked_by), revoked_by),
                    "revokedAt": (record.revocation or {}).get("revokedAt"),
                }

            data.append(
                {
                    "id": str(record.id),
                    "frameworkCategory": (
                        {
                            "id": str(category.id),
                            "code": category.code,
                            "frameworkCategoryName": category.frameworkCategoryName,
                            "description": category.description,
                        }
                        if category
                        else None
                    ),
                    "status": record.status,
                    "requestedBy": str(record.requestedBy) if record.requestedBy else None,
                    "approval": approval,
                    "rejection": rejection,
                    "revocation": revocation,
                    "createdAt": record.createdAt,
                    "updatedAt": record.updatedAt,
                }
            )

    message = "Framework access records retrieved successfully"
    if not data:
        if search or status or frameworkCategoryId:
            message = "No framework access records match your criteria. Try adjusting your filters."
        else:
            message = (
                "You haven't requested access to any frameworks yet. "
                "Request access to start uploading frameworks."
            )

    return paginated(data, build_pagination_meta(page_num, limit_num, total), message)
