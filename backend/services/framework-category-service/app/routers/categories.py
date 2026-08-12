from typing import Annotated

from app.helpers.helpers import code_exists, fetch_users_by_ids
from app.validations.validation import (
    FieldError,
    validate_create_category,
    validate_update_category,
)
import logging
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import delete, or_, select
from vora_shared import data_format, file_storage
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.database import session_scope
from vora_shared.ids import is_valid_id
from vora_shared.messages import MESSAGES
from vora_shared.models import (
    DeploymentFramework,
    Framework,
    FrameworkAccess,
    FrameworkAssignment,
    FrameworkCategory,
    User,
)
from vora_shared.query_builder import apply_sort, paginate_stmt
from vora_shared.responses import error, paginated, success

router = APIRouter(tags=["framework-categories"])
logger = logging.getLogger(__name__)


def _format_category(category: FrameworkCategory, users_by_id: dict[str, User]) -> dict:
    created_by_id = str(category.createdBy) if category.createdBy else None
    updated_by_id = str(category.updatedBy) if category.updatedBy else None
    return {
        "id": str(category.id),
        "code": category.code,
        "frameworkCategoryName": category.frameworkCategoryName,
        "description": category.description,
        "isActive": category.isActive,
        "createdAt": category.createdAt,
        "updatedAt": category.updatedAt,
        "createdBy": data_format.format_user_ref(users_by_id.get(created_by_id), category.createdBy),
        "updatedBy": data_format.format_user_ref(users_by_id.get(updated_by_id), category.updatedBy),
    }


@router.post("")
async def create_framework_category(
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    body: Annotated[dict, Body()] = {},
):
    logger.info(f"[CREATE-CATEGORY] Request started | user_id={auth.user.id} | name={body.get('frameworkCategoryName')} | code={body.get('code')}")
    try:
        fields = validate_create_category(body)
    except FieldError as exc:
        logger.warning(f"[CREATE-CATEGORY] Validation failed | field={exc.field} | reason={exc.message}")
        return error(exc.message, 400, exc.field, exc.value)

    if await code_exists(fields["code"]):
        logger.warning(f"[CREATE-CATEGORY] Code already exists | code={fields['code']}")
        return error(MESSAGES["FRAMEWORK_CATEGORY_CODE_EXISTS"], 400, "code")

    async with session_scope() as session:
        category = FrameworkCategory(
            code=fields["code"],
            frameworkCategoryName=fields["frameworkCategoryName"],
            description=fields.get("description", ""),
            isActive=True,
            createdBy=str(auth.user.id),
        )
        session.add(category)
        await session.flush()
        category_id = str(category.id)

    logger.info(f"[CREATE-CATEGORY] ✅ Created | category_id={category_id} | code={fields['code']} | user_id={auth.user.id}")
    return success({"id": category_id}, MESSAGES["FRAMEWORK_CATEGORY_CREATED"], 201)


async def _apply_search_filter(stmt, search: str, session):
    or_conditions = [
        FrameworkCategory.frameworkCategoryName.ilike(f"%{search}%"),
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
        or_conditions.append(FrameworkCategory.createdBy.in_(user_ids))
        or_conditions.append(FrameworkCategory.updatedBy.in_(user_ids))
    return stmt.where(or_(*or_conditions))


def _get_paginated_message(data, search, is_active):
    if data:
        return MESSAGES["FRAMEWORK_CATEGORIES_SUCCESS"]
    if search or is_active is not None:
        return MESSAGES["NO_CATEGORIES_SEARCH"]
    return MESSAGES["NO_CATEGORIES_FIRST"]


@router.get("")
async def get_all_framework_categories(
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    page: Annotated[int | None, Query()] = None,
    limit: Annotated[int | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    is_active: Annotated[str | None, Query(alias="isActive")] = None,
):
    logger.info(f"[GET-CATEGORIES] Request started | user_id={auth.user.id} | page={page} | limit={limit} | is_active={is_active}")
    async with session_scope() as session:
        stmt = select(FrameworkCategory)
        if is_active is not None:
            stmt = stmt.where(FrameworkCategory.isActive.is_(is_active == "true"))

        if search:
            stmt = await _apply_search_filter(stmt, search, session)

        stmt = apply_sort(FrameworkCategory, stmt, "createdAt", "desc", ["createdAt"])
        documents, pagination = await paginate_stmt(session, stmt, page=page, limit=limit or 10)

        user_ids_needed: set[str] = set()
        for doc in documents:
            if doc.createdBy:
                user_ids_needed.add(str(doc.createdBy))
            if doc.updatedBy:
                user_ids_needed.add(str(doc.updatedBy))
        users_by_id = await fetch_users_by_ids(user_ids_needed)
    data = [_format_category(doc, users_by_id) for doc in documents]

    message = _get_paginated_message(data, search, is_active)

    logger.info(f"[GET-CATEGORIES] ✅ Retrieved | count={len(data)} | total={pagination['total']} | user_id={auth.user.id}")
    return paginated(data, pagination, message)


@router.get("/{id}")
async def get_framework_category_by_id(
    id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(f"[GET-CATEGORY] Request started | user_id={auth.user.id} | category_id={id}")
    if not is_valid_id(id):
        logger.warning(f"[GET-CATEGORY] Invalid ID | category_id={id}")
        return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

    async with session_scope() as session:
        category = await session.get(FrameworkCategory, id)
        if not category:
            logger.warning(f"[GET-CATEGORY] Not found | category_id={id}")
            return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)
        user_ids = {str(uid) for uid in (category.createdBy, category.updatedBy) if uid}

    users_by_id = await fetch_users_by_ids(user_ids)

    logger.info(f"[GET-CATEGORY] ✅ Retrieved | category_id={id} | user_id={auth.user.id}")
    return success(
        {"category": _format_category(category, users_by_id)},
        MESSAGES["FRAMEWORK_CATEGORY_SUCCESS"],
    )


@router.put("/{id}")
async def update_framework_category(
    id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    body: Annotated[dict, Body()] = {},
):
    logger.info(f"[PUT-CATEGORY] Request started | user_id={auth.user.id} | category_id={id}")
    try:
        fields = validate_update_category(body)
    except FieldError as exc:
        logger.warning(f"[PUT-CATEGORY] Validation failed | field={exc.field} | reason={exc.message}")
        return error(exc.message, 400, exc.field, exc.value)

    if not is_valid_id(id):
        logger.warning(f"[PUT-CATEGORY] Invalid ID | category_id={id}")
        return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

    async with session_scope() as session:
        category = await session.get(FrameworkCategory, id)
        if not category:
            logger.warning(f"[PUT-CATEGORY] Not found | category_id={id}")
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
                logger.warning(f"[PUT-CATEGORY] Code already exists | code={new_code}")
                return error(MESSAGES["FRAMEWORK_CATEGORY_CODE_EXISTS"], 400, "code")

        category.updatedBy = str(auth.user.id)
        if "code" in fields:
            category.code = fields["code"]
        if "frameworkCategoryName" in fields:
            category.frameworkCategoryName = fields["frameworkCategoryName"]
        if "description" in fields:
            category.description = fields["description"]
        if "isActive" in fields:
            category.isActive = fields["isActive"]
        category_id = str(category.id)

    logger.info(f"[PUT-CATEGORY] ✅ Updated | category_id={id} | code={category.code} | user_id={auth.user.id}")
    return success({"id": category_id}, MESSAGES["FRAMEWORK_CATEGORY_UPDATED"])


def _delete_physical_file(file_url: str | None, user_id: str | None):
    if not file_url:
        return
    actual_path = None
    if user_id:
        actual_path = file_storage.resolve_actual_file_path(file_url, user_id)
    if actual_path:
        file_storage.delete_file(actual_path)
    else:
        file_storage.delete_file(file_url)


def _cascade_framework_files(frameworks_to_delete):
    for fw in frameworks_to_delete:
        for version in fw.fileVersions:
            if isinstance(version, dict):
                _delete_physical_file(version.get("fileUrl"), fw.uploadedBy)


def _cascade_deployment_framework_files(deployment_frameworks_to_delete):
    for df in deployment_frameworks_to_delete:
        for pkg in df.packages:
            if isinstance(pkg, dict):
                for doc in pkg.get("documents", []):
                    if isinstance(doc, dict):
                        _delete_physical_file(doc.get("fileUrl"), df.uploadedBy)


def _cascade_assignment_files(assignments_to_delete):
    for fa in assignments_to_delete:
        for version in fa.fileVersions:
            if isinstance(version, dict):
                _delete_physical_file(version.get("fileUrl"), fa.uploadedBy)


@router.delete("/{id}")
async def delete_framework_category(
    id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(f"[DELETE-CATEGORY] Request started | user_id={auth.user.id} | category_id={id}")
    if not is_valid_id(id):
        logger.warning(f"[DELETE-CATEGORY] Invalid ID | category_id={id}")
        return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

    async with session_scope() as session:
        category = await session.get(FrameworkCategory, id)
        if not category:
            logger.warning(f"[DELETE-CATEGORY] Not found | category_id={id}")
            return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

        # 1. Cascade physical file deletions for Frameworks
        frameworks_to_delete = (
            (await session.execute(select(Framework).where(Framework.frameworkCategoryId == id)))
            .scalars()
            .all()
        )
        _cascade_framework_files(frameworks_to_delete)
        logger.info(f"[DELETE-CATEGORY] Cascaded delete | frameworks={len(frameworks_to_delete)}")

        # 2. Cascade physical file deletions for DeploymentFrameworks
        deployment_frameworks_to_delete = (
            (
                await session.execute(
                    select(DeploymentFramework).where(DeploymentFramework.frameworkCategoryId == id)
                )
            )
            .scalars()
            .all()
        )
        _cascade_deployment_framework_files(deployment_frameworks_to_delete)
        logger.info(f"[DELETE-CATEGORY] Cascaded delete | deployment_frameworks={len(deployment_frameworks_to_delete)}")

        # 3. Cascade physical file deletions for FrameworkAssignments
        assignments_to_delete = (
            (
                await session.execute(
                    select(FrameworkAssignment).where(FrameworkAssignment.frameworkCategoryId == id)
                )
            )
            .scalars()
            .all()
        )
        _cascade_assignment_files(assignments_to_delete)
        logger.info(f"[DELETE-CATEGORY] Cascaded delete | assignments={len(assignments_to_delete)}")

        # 4. Perform database deletions
        await session.execute(
            delete(FrameworkAssignment).where(FrameworkAssignment.frameworkCategoryId == id)
        )
        await session.execute(
            delete(DeploymentFramework).where(DeploymentFramework.frameworkCategoryId == id)
        )
        await session.execute(delete(Framework).where(Framework.frameworkCategoryId == id))

        delete_result = await session.execute(
            delete(FrameworkAccess).where(FrameworkAccess.frameworkCode == category.code)
        )
        deleted_count = delete_result.rowcount or 0
        logger.info(f"[DELETE-CATEGORY] Cascaded delete | access_records={deleted_count}")
        await session.delete(category)

    message = MESSAGES["FRAMEWORK_CATEGORY_DELETED_WITH_ACCESS"].replace("{count}", str(deleted_count))

    logger.info(f"[DELETE-CATEGORY] ✅ Deleted | category_id={id} | access_count={deleted_count} | user_id={auth.user.id}")
    return success(
        {"id": str(id), "deletedAccessRecords": deleted_count},
        message,
    )
