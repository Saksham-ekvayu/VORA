from datetime import datetime, timezone
from typing import Annotated

from app.helpers import fetch_users_by_ids
from app.validation import FieldError, validate_assign_access
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm.attributes import flag_modified
from vora_shared import data_format
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.database import session_scope
from vora_shared.ids import is_valid_id
from vora_shared.messages import MESSAGES, VALID_STATUSES, format_message
from vora_shared.models import FrameworkAccess, FrameworkCategory, User
from vora_shared.models.framework_access import ApprovalInfo, RejectionInfo, RevocationInfo
from vora_shared.query_builder import apply_sort, paginate_stmt
from vora_shared.responses import error, paginated, success

router = APIRouter(tags=["framework-access"])


def _json_get(obj, key: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _format_access_record(
    record: FrameworkAccess,
    users_by_id: dict[str, User],
    categories_by_id: dict[str, FrameworkCategory],
) -> dict:
    category = categories_by_id.get(str(record.framework_category_id))
    rejected_by_id = _json_get(record.rejection, "rejectedBy")
    revoked_by_id = _json_get(record.revocation, "revokedBy")
    approved_by_id = _json_get(record.approval, "approvedBy")
    if rejected_by_id:
        rejected_by_id = str(rejected_by_id)
    if revoked_by_id:
        revoked_by_id = str(revoked_by_id)
    if approved_by_id:
        approved_by_id = str(approved_by_id)

    return {
        "id": str(record.id),
        "expert": data_format.format_user_ref(users_by_id.get(str(record.expert_id)), record.expert_id),
        "frameworkCategory": (
            {
                "frameworkId": str(category.id),
                "frameworkCode": category.code,
                "frameworkCategoryName": category.framework_category_name,
                "description": category.description,
                "isActive": category.is_active,
            }
            if category
            else None
        ),
        "status": record.status,
        "requestedBy": str(record.requested_by) if record and getattr(record, "requested_by", None) else None,
        "rejection": (
            {
                "rejectedBy": data_format.format_user_ref(users_by_id.get(rejected_by_id), rejected_by_id),
                "rejectedAt": _json_get(record.rejection, "rejectedAt"),
            }
            if rejected_by_id
            else None
        ),
        "revocation": (
            {
                "revokedBy": data_format.format_user_ref(users_by_id.get(revoked_by_id), revoked_by_id),
                "revokedAt": _json_get(record.revocation, "revokedAt"),
            }
            if revoked_by_id
            else None
        ),
        "approval": (
            {
                "approvedBy": data_format.format_user_ref(users_by_id.get(approved_by_id), approved_by_id),
                "approvedAt": _json_get(record.approval, "approvedAt"),
            }
            if approved_by_id
            else None
        ),
        "createdAt": record.created_at,
        "updatedAt": record.updated_at,
    }


async def _batch_format(records: list[FrameworkAccess]) -> list[dict]:
    user_ids: set[str] = set()
    category_ids: set[str] = set()
    for r in records:
        if r.expert_id:
            user_ids.add(str(r.expert_id))
        approved_by = _json_get(r.approval, "approvedBy")
        rejected_by = _json_get(r.rejection, "rejectedBy")
        revoked_by = _json_get(r.revocation, "revokedBy")
        if approved_by:
            user_ids.add(str(approved_by))
        if rejected_by:
            user_ids.add(str(rejected_by))
        if revoked_by:
            user_ids.add(str(revoked_by))
        if r.framework_category_id:
            category_ids.add(str(r.framework_category_id))

    users_by_id = await fetch_users_by_ids(user_ids)
    categories_by_id: dict[str, FrameworkCategory] = {}
    if category_ids:
        async with session_scope() as session:
            categories = (
                (
                    await session.execute(
                        select(FrameworkCategory).where(FrameworkCategory.id.in_(list(category_ids)))
                    )
                )
                .scalars()
                .all()
            )
            categories_by_id = {str(c.id): c for c in categories}

    return [await _format_access_record(r, users_by_id, categories_by_id) for r in records]


async def _search_or_conditions(session, search: str) -> list:
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
    matching_categories = (
        (
            await session.execute(
                select(FrameworkCategory).where(
                    or_(
                        FrameworkCategory.code.ilike(f"%{search}%"),
                        FrameworkCategory.framework_category_name.ilike(f"%{search}%"),
                        FrameworkCategory.description.ilike(f"%{search}%"),
                    )
                )
            )
        )
        .scalars()
        .all()
    )

    user_ids = [u.id for u in matching_users]
    category_ids = [c.id for c in matching_categories]

    conditions = [FrameworkAccess.framework_code.ilike(f"%{search}%")]
    if user_ids:
        conditions += [
            FrameworkAccess.expert_id.in_(user_ids),
            FrameworkAccess.approval["approvedBy"].astext.in_(user_ids),
            FrameworkAccess.rejection["rejectedBy"].astext.in_(user_ids),
            FrameworkAccess.revocation["revokedBy"].astext.in_(user_ids),
        ]
    if category_ids:
        conditions.append(FrameworkAccess.framework_category_id.in_(category_ids))
    return conditions


def _validate_status(status: str) -> tuple[bool, str | None]:
    """Validate status parameter and return error message if invalid."""
    if status and status != "all" and status not in VALID_STATUSES:
        return False, format_message(MESSAGES["INVALID_STATUS"], statuses=", ".join(VALID_STATUSES))
    return True, None


def _validate_expert_id(expert_id: str | None) -> tuple[bool, str | None]:
    """Validate expert ID and return error message if invalid."""
    if expert_id and not is_valid_id(expert_id):
        return False, format_message(MESSAGES["INVALID_OBJECT_ID"], field="expertId", value=expert_id)
    return True, None


def _build_access_list_query(stmt, status: str, expert_id: str | None, framework_code: str | None):
    """Build the base query for framework access list."""
    if status and status != "all":
        stmt = stmt.where(FrameworkAccess.status == status)
    if expert_id:
        stmt = stmt.where(FrameworkAccess.expert_id == expert_id)
    if framework_code:
        stmt = stmt.where(FrameworkAccess.framework_code == framework_code.lower())
    return stmt


def _get_access_list_message(
    data: list, search: str | None, status: str, expert_id: str | None, framework_code: str | None
) -> str:
    """Determine appropriate message for access list response."""
    if not data:
        if search:
            return MESSAGES["NO_ACCESS_SEARCH"]
        if status and status != "all":
            return format_message(MESSAGES["NO_ACCESS_STATUS"], status=status)
        if expert_id:
            return MESSAGES["NO_ACCESS_EXPERT"]
        if framework_code:
            return MESSAGES["NO_ACCESS_FRAMEWORK_CODE"]
        return MESSAGES["NO_ACCESS_RECORDS"]
    return MESSAGES["FRAMEWORK_ACCESS_SUCCESS"]


@router.get("")
async def get_framework_access_list(
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    page: Annotated[int | None, Query()] = None,
    limit: Annotated[int | None, Query()] = None,
    status: Annotated[str, Query()] = "all",
    expert_id: Annotated[str | None, Query(alias="expertId")] = None,
    framework_code: Annotated[str | None, Query(alias="frameworkCode")] = None,
    search: Annotated[str | None, Query()] = None,
    sort_by: Annotated[str | None, Query(alias="sortBy")] = None,
    sort_order: Annotated[str | None, Query(alias="sortOrder")] = None,
):
    # Validate parameters
    is_valid, error_msg = _validate_status(status)
    if not is_valid:
        return error(error_msg, 400)

    is_valid, error_msg = _validate_expert_id(expert_id)
    if not is_valid:
        return error(error_msg, 400)

    allowed_sort = [
        "createdAt",
        "updatedAt",
        "frameworkCode",
        "status",
    ]

    async with session_scope() as session:
        stmt = select(FrameworkAccess)
        stmt = _build_access_list_query(stmt, status, expert_id, framework_code)

        if search:
            conditions = await _search_or_conditions(session, search)
            stmt = stmt.where(or_(*conditions))

        stmt = apply_sort(FrameworkAccess, stmt, sort_by, sort_order, allowed_sort, default_sort="createdAt")
        documents, pagination = await paginate_stmt(session, stmt, page=page or 1, limit=limit or 10)

    data = await _batch_format(documents)
    message = _get_access_list_message(data, search, status, expert_id, framework_code)

    return paginated(data, pagination, message)


@router.get("/user/{user_id}")
async def get_framework_access_by_user_id(
    user_id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    page: Annotated[int | None, Query()] = None,
    limit: Annotated[int | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    sort_by: Annotated[str | None, Query(alias="sortBy")] = None,
    sort_order: Annotated[str | None, Query(alias="sortOrder")] = None,
):
    if not is_valid_id(user_id):
        return error(MESSAGES["EXPERT_NOT_FOUND"], 404)

    async with session_scope() as session:
        expert = await session.get(User, user_id)
        if not expert:
            return error(MESSAGES["EXPERT_NOT_FOUND"], 404)

        stmt = select(FrameworkAccess).where(FrameworkAccess.expert_id == user_id)
        if status and status != "all":
            if status not in VALID_STATUSES:
                return error(
                    format_message(MESSAGES["INVALID_STATUS"], statuses=", ".join(VALID_STATUSES)),
                    400,
                )
            stmt = stmt.where(FrameworkAccess.status == status)

        if search:
            conditions = await _search_or_conditions(session, search)
            stmt = stmt.where(or_(*conditions))

        stmt = apply_sort(
            FrameworkAccess,
            stmt,
            sort_by or "createdAt",
            sort_order or "desc",
            ["createdAt", "updatedAt", "frameworkCode", "status"],
        )
        documents, pagination = await paginate_stmt(session, stmt, page=page or 1, limit=limit or 10)

    data = await _batch_format(documents)
    message = MESSAGES["NO_ACCESS_EXPERT"] if not data else MESSAGES["FRAMEWORK_ACCESS_SUCCESS"]

    return paginated(data, pagination, message)


@router.get("/{id}")
async def get_framework_access_by_id(
    id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    if not is_valid_id(id):
        return error(MESSAGES["FRAMEWORK_ACCESS_NOT_FOUND"], 404)

    async with session_scope() as session:
        record = await session.get(FrameworkAccess, id)
        if not record:
            return error(MESSAGES["FRAMEWORK_ACCESS_NOT_FOUND"], 404)

    formatted = (await _batch_format([record]))[0]
    return success(formatted, MESSAGES["FRAMEWORK_ACCESS_RECORD_SUCCESS"])


# Helper functions for assign_framework_access
def _validate_assign_inputs(expert_id_raw, framework_category_ids_raw):
    """Validate expert ID and category IDs."""
    if not is_valid_id(str(expert_id_raw)):
        return None, format_message(MESSAGES["INVALID_OBJECT_ID"], field="expertId", value=expert_id_raw)

    expert_id = str(expert_id_raw)
    category_ids: list[str] = []

    for raw_id in framework_category_ids_raw:
        sid = str(raw_id)
        if not is_valid_id(sid):
            return None, format_message(
                MESSAGES["INVALID_OBJECT_ID"], field="frameworkCategoryIds", value=raw_id
            )
        category_ids.append(sid)

    return expert_id, category_ids


async def _validate_expert_and_categories(session, expert_id: str, category_ids: list[str]):
    """Validate expert exists and is active, and all categories exist and are active."""
    expert = await session.get(User, expert_id)
    if not expert:
        return None, None, MESSAGES["EXPERT_NOT_FOUND"]
    if not expert.is_active:
        return None, None, MESSAGES["EXPERT_NOT_ACTIVE"]

    framework_categories = (
        (await session.execute(select(FrameworkCategory).where(FrameworkCategory.id.in_(category_ids))))
        .scalars()
        .all()
    )

    if len(framework_categories) != len(category_ids):
        found_ids = {str(c.id) for c in framework_categories}
        missing_ids = [i for i in category_ids if i not in found_ids]
        return None, None, f"{MESSAGES['FRAMEWORK_CATEGORIES_NOT_FOUND_PREFIX']}: {', '.join(missing_ids)}"

    inactive = [c for c in framework_categories if not c.is_active]
    if inactive:
        return None, None, MESSAGES["FRAMEWORK_CATEGORY_INACTIVE"]

    return expert, framework_categories, None


async def _create_or_update_access_record(session, expert_id: str, category, auth_user_id: str, now):
    """Create or update a single access record."""
    existing = (
        await session.execute(
            select(FrameworkAccess).where(
                FrameworkAccess.expert_id == expert_id,
                FrameworkAccess.framework_category_id == category.id,
            )
        )
    ).scalar_one_or_none()

    if existing:
        if existing.status == "approved":
            return {
                "frameworkCategoryId": str(category.id),
                "frameworkCode": category.code,
                "status": "already_approved",
                "message": MESSAGES["ALREADY_HAS_ACCESS"],
            }, None

        existing.status = "approved"
        existing.requested_by = "admin"
        existing.approval = ApprovalInfo(approved_by=auth_user_id, approved_at=now).model_dump(mode="json")
        flag_modified(existing, "approval")
        access_record = existing
        is_update = True
    else:
        access_record = FrameworkAccess(
            expert_id=expert_id,
            framework_category_id=category.id,
            framework_code=category.code,
            status="approved",
            requested_by="admin",
            approval=ApprovalInfo(approved_by=auth_user_id, approved_at=now).model_dump(mode="json"),
        )
        session.add(access_record)
        await session.flush()
        is_update = False

    result = {
        "id": str(access_record.id),
        "frameworkCategoryId": str(access_record.framework_category_id),
        "frameworkCode": access_record.framework_code,
        "status": "assigned",
        "isUpdate": is_update,
    }
    return result, None


def _build_assign_response(results: list[dict], errors: list[dict], expert_id: str, category_ids: list[str]):
    """Build the response for assign_framework_access."""
    success_count = sum(1 for r in results if r["status"] == "assigned")
    already_approved_count = sum(1 for r in results if r["status"] == "already_approved")

    if success_count > 0 and already_approved_count == 0 and len(errors) == 0:
        success_message = (
            MESSAGES["FRAMEWORK_ACCESS_ASSIGNED"]
            if success_count == 1
            else f"{success_count} framework access permissions assigned successfully"
        )
    else:
        parts = []
        if success_count > 0:
            parts.append(f"{success_count} assigned successfully")
        if already_approved_count > 0:
            parts.append(f"{already_approved_count} already had access")
        if errors:
            parts.append(f"{len(errors)} failed")
        success_message = f"Framework access update completed: {', '.join(parts)}"

    return {
        "expertId": expert_id,
        "totalRequested": len(category_ids),
        "successfulAssignments": success_count,
        "alreadyApproved": already_approved_count,
        "errors": len(errors),
        "results": results,
        "errorDetails": errors,
    }, success_message


@router.post("/assign")
async def assign_framework_access(
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
    body: Annotated[dict, Body()] = {},
):
    try:
        expert_id_raw, framework_category_ids_raw = validate_assign_access(body)
    except FieldError as exc:
        return error(exc.message, 400)

    # Validate inputs
    expert_id, category_ids = _validate_assign_inputs(expert_id_raw, framework_category_ids_raw)
    if expert_id is None:
        return error(category_ids, 400)  # category_ids holds error message here

    async with session_scope() as session:
        # Validate expert and categories
        framework_categories, error_msg = await _validate_expert_and_categories(
            session, expert_id, category_ids
        )
        if error_msg:
            return error(error_msg, 404 if "not found" in error_msg.lower() else 400)

        # Process each category
        results: list[dict] = []
        errors: list[dict] = []
        now = datetime.now(timezone.utc)
        auth_user_id = str(auth.user.id)

        for category in framework_categories:
            try:
                result, err = await _create_or_update_access_record(
                    session, expert_id, category, auth_user_id, now
                )
                if result:
                    results.append(result)
                if err:
                    errors.append(err)
            except Exception as exc:  # pragma: no cover
                errors.append(
                    {
                        "frameworkCategoryId": str(category.id),
                        "frameworkCode": category.code,
                        "error": str(exc),
                    }
                )

    # Build and return response
    response_data, success_message = _build_assign_response(results, errors, expert_id, category_ids)
    return success(response_data, success_message)


@router.put("/approve/{id}")
async def approve_framework_access(
    id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    if not is_valid_id(id):
        return error(MESSAGES["FRAMEWORK_ACCESS_REQUEST_NOT_FOUND"], 404)

    async with session_scope() as session:
        record = await session.get(FrameworkAccess, id)
        if not record:
            return error(MESSAGES["FRAMEWORK_ACCESS_REQUEST_NOT_FOUND"], 404)
        if record.status != "pending":
            return error(MESSAGES["ACCESS_ALREADY_PROCESSED"], 400)

        record.status = "approved"
        record.approval = ApprovalInfo(
            approved_by=str(auth.user.id),
            approved_at=datetime.now(timezone.utc),
        ).model_dump(mode="json")
        flag_modified(record, "approval")
        record_id = str(record.id)

    return success({"id": record_id}, MESSAGES["FRAMEWORK_ACCESS_APPROVED"])


@router.put("/reject/{id}")
async def reject_framework_access(
    id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    if not is_valid_id(id):
        return error(MESSAGES["FRAMEWORK_ACCESS_REQUEST_NOT_FOUND"], 404)

    async with session_scope() as session:
        record = await session.get(FrameworkAccess, id)
        if not record:
            return error(MESSAGES["FRAMEWORK_ACCESS_REQUEST_NOT_FOUND"], 404)
        if record.status != "pending":
            return error(MESSAGES["ACCESS_ALREADY_PROCESSED"], 400)

        record.status = "rejected"
        record.rejection = RejectionInfo(
            rejected_by=str(auth.user.id),
            rejected_at=datetime.now(timezone.utc),
        ).model_dump(mode="json")
        flag_modified(record, "rejection")
        record_id = str(record.id)

    return success({"id": record_id}, MESSAGES["FRAMEWORK_ACCESS_REJECTED"])


@router.put("/revoke/{expert_id}/{framework_category_id}")
async def revoke_framework_access(
    expert_id: str,
    framework_category_id: str,
    auth: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    if not is_valid_id(expert_id):
        return error(MESSAGES["EXPERT_NOT_FOUND"], 404)
    if not is_valid_id(framework_category_id):
        return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

    async with session_scope() as session:
        expert = (
            await session.execute(select(User).where(User.id == expert_id, User.is_active.is_(True)))
        ).scalar_one_or_none()
        if not expert:
            return error(MESSAGES["EXPERT_NOT_FOUND"], 404)

        category = await session.get(FrameworkCategory, framework_category_id)
        if not category:
            return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

        record = (
            await session.execute(
                select(FrameworkAccess).where(
                    FrameworkAccess.expert_id == expert_id,
                    FrameworkAccess.framework_category_id == framework_category_id,
                )
            )
        ).scalar_one_or_none()
        if not record:
            return error(MESSAGES["ACCESS_RECORD_NOT_FOUND"], 404)

        if record.status != "approved":
            return error(MESSAGES["ONLY_APPROVED_CAN_REVOKE"], 400)

        record.status = "revoked"
        record.revocation = RevocationInfo(
            revoked_by=str(auth.user.id),
            revoked_at=datetime.now(timezone.utc),
        ).model_dump(mode="json")
        flag_modified(record, "revocation")
        result = {
            "id": str(record.id),
            "expertId": str(record.expert_id),
            "frameworkCode": record.framework_code,
            "status": record.status,
        }

    return success(result, MESSAGES["FRAMEWORK_ACCESS_REVOKED"])
