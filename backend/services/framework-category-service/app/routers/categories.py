from typing import Annotated

from app.helpers import code_exists, fetch_users_by_ids
from app.validation import FieldError, validate_create_category, validate_update_category
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import delete, or_, select
from vora_shared import data_format
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.database import session_scope
from vora_shared.ids import is_valid_id
from vora_shared.messages import MESSAGES
from vora_shared.models import FrameworkAccess, FrameworkCategory, User
from vora_shared.query_builder import apply_sort, paginate_stmt
from vora_shared.responses import error, paginated, success

router = APIRouter(tags=["framework-categories"])


def _format_category(category: FrameworkCategory, users_by_id: dict[str, User]) -> dict:
    created_by_id = str(category.created_by) if category.created_by else None
    updated_by_id = str(category.updated_by) if category.updated_by else None
    return {
        "id": str(category.id),
        "code": category.code,
        "frameworkCategoryName": category.framework_category_name,
        "description": category.description,
        "isActive": category.is_active,
        "createdAt": category.createdAt,
        "updatedAt": category.updatedAt,
        "createdBy": data_format.format_user_ref(users_by_id.get(created_by_id), category.created_by),
        "updatedBy": data_format.format_user_ref(users_by_id.get(updated_by_id), category.updated_by),
    }


@router.post("")
async def create_framework_category(
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    body: Annotated[dict, Body()] = {},
):
    try:
        fields = validate_create_category(body)
    except FieldError as exc:
        return error(exc.message, 400, exc.field, exc.value)

    if await code_exists(fields["code"]):
        return error(MESSAGES["FRAMEWORK_CATEGORY_CODE_EXISTS"], 400, "code")

    async with session_scope() as session:
        category = FrameworkCategory(
            code=fields["code"],
            framework_category_name=fields["frameworkCategoryName"],
            description=fields["description"] or "",
            is_active=True,
            created_by=str(auth.user.id),
        )
        session.add(category)
        await session.flush()
        category_id = str(category.id)

    return success({"id": category_id}, MESSAGES["FRAMEWORK_CATEGORY_CREATED"], 201)


@router.get("")
async def get_all_framework_categories(
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    page: Annotated[int | None, Query()] = None,
    limit: Annotated[int | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    is_active: Annotated[str | None, Query(alias="isActive")] = None,
):
    async with session_scope() as session:
        stmt = select(FrameworkCategory)
        if is_active is not None:
            stmt = stmt.where(FrameworkCategory.is_active.is_(is_active == "true"))

        if search:
            or_conditions = [
                FrameworkCategory.framework_category_name.ilike(f"%{search}%"),
                FrameworkCategory.code.ilike(f"%{search}%"),
                FrameworkCategory.description.ilike(f"%{search}%"),
            ]
            matching_users = (
                (
                    await session.execute(
                        select(User).where(
                            or_(
                                User.name.ilike(f"%{search}%"),
                                User.email.ilike(f"%{search}%"),
                            )
                        )
                    )
                )
                .scalars()
                .all()
            )
            user_ids = [u.id for u in matching_users]
            if user_ids:
                or_conditions.append(FrameworkCategory.created_by.in_(user_ids))
                or_conditions.append(FrameworkCategory.updated_by.in_(user_ids))
            stmt = stmt.where(or_(*or_conditions))

        stmt = apply_sort(FrameworkCategory, stmt, "created_at", "desc", ["created_at"])
        documents, pagination = await paginate_stmt(session, stmt, page=page, limit=limit or 10)

        user_ids_needed: set[str] = set()
        for doc in documents:
            if doc.created_by:
                user_ids_needed.add(str(doc.created_by))
            if doc.updated_by:
                user_ids_needed.add(str(doc.updated_by))

    users_by_id = await fetch_users_by_ids(user_ids_needed)
    data = [await _format_category(doc, users_by_id) for doc in documents]

    if data:
        message = MESSAGES["FRAMEWORK_CATEGORIES_SUCCESS"]
    elif search or is_active is not None:
        message = MESSAGES["NO_CATEGORIES_SEARCH"]
    else:
        message = MESSAGES["NO_CATEGORIES_FIRST"]

    return paginated(data, pagination, message)


@router.get("/{id}")
async def get_framework_category_by_id(
    id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    if not is_valid_id(id):
        return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

    async with session_scope() as session:
        category = await session.get(FrameworkCategory, id)
        if not category:
            return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)
        user_ids = {str(uid) for uid in (category.created_by, category.updated_by) if uid}

    users_by_id = await fetch_users_by_ids(user_ids)

    return success(
        {"category": await _format_category(category, users_by_id)},
        MESSAGES["FRAMEWORK_CATEGORY_SUCCESS"],
    )


@router.put("/{id}")
async def update_framework_category(
    id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    body: Annotated[dict, Body()] = {},
):
    try:
        fields = validate_update_category(body)
    except FieldError as exc:
        return error(exc.message, 400, exc.field, exc.value)

    if not is_valid_id(id):
        return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

    async with session_scope() as session:
        category = await session.get(FrameworkCategory, id)
        if not category:
            return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

        new_code = fields.get("code")
        if new_code and new_code != category.code:
            dup = (
                await session.execute(
                    select(FrameworkCategory).where(
                        FrameworkCategory.code == new_code,
                        FrameworkCategory.id != id,
                    )
                )
            ).scalar_one_or_none()
            if dup:
                return error(MESSAGES["FRAMEWORK_CATEGORY_CODE_EXISTS"], 400, "code")

        category.updated_by = str(auth.user.id)
        if "code" in fields:
            category.code = fields["code"]
        if "frameworkCategoryName" in fields:
            category.framework_category_name = fields["frameworkCategoryName"]
        if "description" in fields:
            category.description = fields["description"]
        if "isActive" in fields:
            category.is_active = fields["isActive"]
        category_id = str(category.id)

    return success({"id": category_id}, MESSAGES["FRAMEWORK_CATEGORY_UPDATED"])


@router.delete("/{id}")
async def delete_framework_category(
    id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    if not is_valid_id(id):
        return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

    async with session_scope() as session:
        category = await session.get(FrameworkCategory, id)
        if not category:
            return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

        delete_result = await session.execute(
            delete(FrameworkAccess).where(FrameworkAccess.frameworkCode == category.code)
        )
        deleted_count = delete_result.rowcount or 0
        await session.delete(category)

    message = MESSAGES["FRAMEWORK_CATEGORY_DELETED_WITH_ACCESS"].replace("{count}", str(deleted_count))

    return success(
        {"id": str(id), "deletedAccessRecords": deleted_count},
        message,
    )
