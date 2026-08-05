from datetime import datetime, timezone

from app.helpers import fetch_users_by_ids, get_user_data
from app.validation import FieldError, validate_assign_access
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm.attributes import flag_modified
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


async def _format_access_record(
    record: FrameworkAccess,
    users_by_id: dict[str, User],
    categories_by_id: dict[str, FrameworkCategory],
) -> dict:
    category = categories_by_id.get(str(record.frameworkCategoryId))
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
        "expert": get_user_data(users_by_id.get(str(record.expertId)), record.expertId),
        "frameworkCategory": (
            {
                "frameworkId": str(category.id),
                "frameworkCode": category.code,
                "frameworkCategoryName": category.frameworkCategoryName,
                "description": category.description,
                "isActive": category.isActive,
            }
            if category
            else None
        ),
        "status": record.status,
        "requestedBy": str(record.requestedBy) if record and getattr(record, "requestedBy", None) else None,
        "rejection": (
            {
                "rejectedBy": get_user_data(users_by_id.get(rejected_by_id), rejected_by_id),
                "rejectedAt": _json_get(record.rejection, "rejectedAt"),
            }
            if rejected_by_id
            else None
        ),
        "revocation": (
            {
                "revokedBy": get_user_data(users_by_id.get(revoked_by_id), revoked_by_id),
                "revokedAt": _json_get(record.revocation, "revokedAt"),
            }
            if revoked_by_id
            else None
        ),
        "approval": (
            {
                "approvedBy": get_user_data(users_by_id.get(approved_by_id), approved_by_id),
                "approvedAt": _json_get(record.approval, "approvedAt"),
            }
            if approved_by_id
            else None
        ),
        "createdAt": record.createdAt,
        "updatedAt": record.updatedAt,
    }


async def _batch_format(records: list[FrameworkAccess]) -> list[dict]:
    user_ids: set[str] = set()
    category_ids: set[str] = set()
    for r in records:
        if r.expertId:
            user_ids.add(str(r.expertId))
        approved_by = _json_get(r.approval, "approvedBy")
        rejected_by = _json_get(r.rejection, "rejectedBy")
        revoked_by = _json_get(r.revocation, "revokedBy")
        if approved_by:
            user_ids.add(str(approved_by))
        if rejected_by:
            user_ids.add(str(rejected_by))
        if revoked_by:
            user_ids.add(str(revoked_by))
        if r.frameworkCategoryId:
            category_ids.add(str(r.frameworkCategoryId))

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
                        FrameworkCategory.frameworkCategoryName.ilike(f"%{search}%"),
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

    conditions = [FrameworkAccess.frameworkCode.ilike(f"%{search}%")]
    if user_ids:
        conditions += [
            FrameworkAccess.expertId.in_(user_ids),
            FrameworkAccess.approval["approvedBy"].astext.in_(user_ids),
            FrameworkAccess.rejection["rejectedBy"].astext.in_(user_ids),
            FrameworkAccess.revocation["revokedBy"].astext.in_(user_ids),
        ]
    if category_ids:
        conditions.append(FrameworkAccess.frameworkCategoryId.in_(category_ids))
    return conditions


@router.get("")
async def get_framework_access_list(
    page: int | None = Query(None),
    limit: int | None = Query(None),
    status: str = Query("all"),
    expertId: str | None = Query(None),
    frameworkCode: str | None = Query(None),
    search: str | None = Query(None),
    sortBy: str | None = Query(None),
    sortOrder: str | None = Query(None),
    auth: AuthenticatedUser = Depends(authenticate),
):
    if status and status != "all" and status not in VALID_STATUSES:
        return error(
            format_message(MESSAGES["INVALID_STATUS"], statuses=", ".join(VALID_STATUSES)),
            400,
        )

    if expertId and not is_valid_id(expertId):
        return error(
            format_message(MESSAGES["INVALID_OBJECT_ID"], field="expertId", value=expertId),
            400,
        )

    allowed_sort = [
        "createdAt",
        "updatedAt",
        "frameworkCode",
        "status",
    ]

    async with session_scope() as session:
        stmt = select(FrameworkAccess)
        if status and status != "all":
            stmt = stmt.where(FrameworkAccess.status == status)
        if expertId:
            stmt = stmt.where(FrameworkAccess.expertId == expertId)
        if frameworkCode:
            stmt = stmt.where(FrameworkAccess.frameworkCode == frameworkCode.lower())
        if search:
            conditions = await _search_or_conditions(session, search)
            stmt = stmt.where(or_(*conditions))

        stmt = apply_sort(FrameworkAccess, stmt, sortBy, sortOrder, allowed_sort, default_sort="createdAt")
        documents, pagination = await paginate_stmt(session, stmt, page=page or 1, limit=limit or 10)

    data = await _batch_format(documents)

    if not data:
        if search:
            message = MESSAGES["NO_ACCESS_SEARCH"]
        elif status and status != "all":
            message = format_message(MESSAGES["NO_ACCESS_STATUS"], status=status)
        elif expertId:
            message = MESSAGES["NO_ACCESS_EXPERT"]
        elif frameworkCode:
            message = MESSAGES["NO_ACCESS_FRAMEWORK_CODE"]
        else:
            message = MESSAGES["NO_ACCESS_RECORDS"]
    else:
        message = MESSAGES["FRAMEWORK_ACCESS_SUCCESS"]

    return paginated(data, pagination, message)


@router.get("/user/{userId}")
async def get_framework_access_by_user_id(
    userId: str,
    page: int | None = Query(None),
    limit: int | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    sortBy: str | None = Query(None),
    sortOrder: str | None = Query(None),
    auth: AuthenticatedUser = Depends(authenticate),
):
    if not is_valid_id(userId):
        return error(MESSAGES["EXPERT_NOT_FOUND"], 404)

    async with session_scope() as session:
        expert = await session.get(User, userId)
        if not expert:
            return error(MESSAGES["EXPERT_NOT_FOUND"], 404)

        stmt = select(FrameworkAccess).where(FrameworkAccess.expertId == userId)
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
            sortBy or "createdAt",
            sortOrder or "desc",
            ["createdAt", "updatedAt", "frameworkCode", "status"],
        )
        documents, pagination = await paginate_stmt(session, stmt, page=page or 1, limit=limit or 10)

    data = await _batch_format(documents)
    message = MESSAGES["NO_ACCESS_EXPERT"] if not data else MESSAGES["FRAMEWORK_ACCESS_SUCCESS"]

    return paginated(data, pagination, message)


@router.get("/{id}")
async def get_framework_access_by_id(
    id: str,
    auth: AuthenticatedUser = Depends(authenticate),
):
    if not is_valid_id(id):
        return error(MESSAGES["FRAMEWORK_ACCESS_NOT_FOUND"], 404)

    async with session_scope() as session:
        record = await session.get(FrameworkAccess, id)
        if not record:
            return error(MESSAGES["FRAMEWORK_ACCESS_NOT_FOUND"], 404)

    formatted = (await _batch_format([record]))[0]
    return success(formatted, MESSAGES["FRAMEWORK_ACCESS_RECORD_SUCCESS"])


@router.post("/assign")
async def assign_framework_access(
    body: dict = Body(default={}),
    auth: AuthenticatedUser = Depends(authenticate),
):
    try:
        expert_id_raw, framework_category_ids_raw = validate_assign_access(body)
    except FieldError as exc:
        return error(exc.message, 400)

    if not is_valid_id(str(expert_id_raw)):
        return error(
            format_message(MESSAGES["INVALID_OBJECT_ID"], field="expertId", value=expert_id_raw),
            400,
        )
    expert_id = str(expert_id_raw)

    category_ids: list[str] = []
    for raw_id in framework_category_ids_raw:
        sid = str(raw_id)
        if not is_valid_id(sid):
            return error(
                format_message(MESSAGES["INVALID_OBJECT_ID"], field="frameworkCategoryIds", value=raw_id),
                400,
            )
        category_ids.append(sid)

    async with session_scope() as session:
        expert = await session.get(User, expert_id)
        if not expert:
            return error(MESSAGES["EXPERT_NOT_FOUND"], 404)
        if not expert.isActive:
            return error(MESSAGES["EXPERT_NOT_ACTIVE"], 404)

        framework_categories = (
            (await session.execute(select(FrameworkCategory).where(FrameworkCategory.id.in_(category_ids))))
            .scalars()
            .all()
        )

        if len(framework_categories) != len(category_ids):
            found_ids = {str(c.id) for c in framework_categories}
            missing_ids = [i for i in category_ids if i not in found_ids]
            return error(
                f"{MESSAGES['FRAMEWORK_CATEGORIES_NOT_FOUND_PREFIX']}: {', '.join(missing_ids)}",
                404,
            )

        inactive = [c for c in framework_categories if not c.isActive]
        if inactive:
            return error(MESSAGES["FRAMEWORK_CATEGORY_INACTIVE"], 404)

        results: list[dict] = []
        errors: list[dict] = []
        now = datetime.now(timezone.utc)

        for category in framework_categories:
            try:
                existing = (
                    await session.execute(
                        select(FrameworkAccess).where(
                            FrameworkAccess.expertId == expert_id,
                            FrameworkAccess.frameworkCategoryId == category.id,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    if existing.status == "approved":
                        results.append(
                            {
                                "frameworkCategoryId": str(category.id),
                                "frameworkCode": category.code,
                                "status": "already_approved",
                                "message": MESSAGES["ALREADY_HAS_ACCESS"],
                            }
                        )
                        continue

                    existing.status = "approved"
                    existing.requestedBy = "admin"
                    existing.approval = ApprovalInfo(approvedBy=str(auth.user.id), approvedAt=now).model_dump(
                        mode="json"
                    )
                    flag_modified(existing, "approval")
                    access_record = existing
                    is_update = True
                else:
                    access_record = FrameworkAccess(
                        expertId=expert_id,
                        frameworkCategoryId=category.id,
                        frameworkCode=category.code,
                        status="approved",
                        requestedBy="admin",
                        approval=ApprovalInfo(approvedBy=str(auth.user.id), approvedAt=now).model_dump(
                            mode="json"
                        ),
                    )
                    session.add(access_record)
                    await session.flush()
                    is_update = False

                results.append(
                    {
                        "id": str(access_record.id),
                        "frameworkCategoryId": str(access_record.frameworkCategoryId),
                        "frameworkCode": access_record.frameworkCode,
                        "status": "assigned",
                        "isUpdate": is_update,
                    }
                )
            except Exception as exc:  # pragma: no cover
                errors.append(
                    {
                        "frameworkCategoryId": str(category.id),
                        "frameworkCode": category.code,
                        "error": str(exc),
                    }
                )

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

    return success(
        {
            "expertId": expert_id,
            "totalRequested": len(category_ids),
            "successfulAssignments": success_count,
            "alreadyApproved": already_approved_count,
            "errors": len(errors),
            "results": results,
            "errorDetails": errors,
        },
        success_message,
    )


@router.put("/approve/{id}")
async def approve_framework_access(
    id: str,
    auth: AuthenticatedUser = Depends(authenticate),
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
            approvedBy=str(auth.user.id),
            approvedAt=datetime.now(timezone.utc),
        ).model_dump(mode="json")
        flag_modified(record, "approval")
        record_id = str(record.id)

    return success({"id": record_id}, MESSAGES["FRAMEWORK_ACCESS_APPROVED"])


@router.put("/reject/{id}")
async def reject_framework_access(
    id: str,
    auth: AuthenticatedUser = Depends(authenticate),
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
            rejectedBy=str(auth.user.id),
            rejectedAt=datetime.now(timezone.utc),
        ).model_dump(mode="json")
        flag_modified(record, "rejection")
        record_id = str(record.id)

    return success({"id": record_id}, MESSAGES["FRAMEWORK_ACCESS_REJECTED"])


@router.put("/revoke/{expertId}/{frameworkCategoryId}")
async def revoke_framework_access(
    expertId: str,
    frameworkCategoryId: str,
    auth: AuthenticatedUser = Depends(authenticate),
):
    if not is_valid_id(expertId):
        return error(MESSAGES["EXPERT_NOT_FOUND"], 404)
    if not is_valid_id(frameworkCategoryId):
        return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

    async with session_scope() as session:
        expert = (
            await session.execute(select(User).where(User.id == expertId, User.isActive.is_(True)))
        ).scalar_one_or_none()
        if not expert:
            return error(MESSAGES["EXPERT_NOT_FOUND"], 404)

        category = await session.get(FrameworkCategory, frameworkCategoryId)
        if not category:
            return error(MESSAGES["FRAMEWORK_CATEGORY_NOT_FOUND"], 404)

        record = (
            await session.execute(
                select(FrameworkAccess).where(
                    FrameworkAccess.expertId == expertId,
                    FrameworkAccess.frameworkCategoryId == frameworkCategoryId,
                )
            )
        ).scalar_one_or_none()
        if not record:
            return error(MESSAGES["ACCESS_RECORD_NOT_FOUND"], 404)

        if record.status != "approved":
            return error(MESSAGES["ONLY_APPROVED_CAN_REVOKE"], 400)

        record.status = "revoked"
        record.revocation = RevocationInfo(
            revokedBy=str(auth.user.id),
            revokedAt=datetime.now(timezone.utc),
        ).model_dump(mode="json")
        flag_modified(record, "revocation")
        result = {
            "id": str(record.id),
            "expertId": str(record.expertId),
            "frameworkCode": record.frameworkCode,
            "status": record.status,
        }

    return success(result, MESSAGES["FRAMEWORK_ACCESS_REVOKED"])
