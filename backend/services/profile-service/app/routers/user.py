from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select

from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.database import session_scope
from vora_shared.models.customer import Customer
from vora_shared.models.user import User
from vora_shared.responses import error, success

from vora_shared import messages as msg
from app.schemas.user import ProfileUpdateRequest
from app.utils.formatting import (
    address_dict,
    created_by_user_id,
    customer_summary,
    format_created_by,
    merge_address,
)
from app.utils.uploads import AvatarUploadError, delete_avatar_file, save_avatar

router = APIRouter(tags=["profile"])


async def require_customer_admin(
    ctx: AuthenticatedUser = Depends(authenticate),
) -> AuthenticatedUser:
    if ctx.user.role != "customer-admin":
        raise HTTPException(
            403,
            {
                "message": "Access denied. Required role(s): customer-admin",
                "field": "role",
            },
        )
    return ctx


@router.get("/my-profile")
async def get_profile(ctx: AuthenticatedUser = Depends(authenticate)):
    user = ctx.user

    if not user.isActive:
        return error(msg.USER_ACCOUNT_DEACTIVATED, 400, field="user")

    creator = None
    creator_id = created_by_user_id(user.createdBy)
    async with session_scope() as session:
        if creator_id:
            creator = await session.get(User, str(creator_id))

        customer = None
        if user.tenantId:
            customer = (
                await session.execute(
                    select(Customer).where(Customer.tenantId == user.tenantId)
                )
            ).scalar_one_or_none()

    response_data = {
        "tenantId": str(user.tenantId) if user and getattr(user, "tenantId", None) else None,
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "designation": user.designation,
        "phone": user.phone,
        "secondaryPhone": user.secondaryPhone or None,
        "avatar": user.avatar or None,
        "address": address_dict(user.address),
        "isEmailVerified": user.isEmailVerified,
        "createdAt": user.createdAt,
        "updatedAt": user.updatedAt,
        "createdBy": format_created_by(user.createdBy, creator),
        "customer": customer_summary(customer),
    }

    return success(response_data, msg.PROFILE_RETRIEVED)


@router.patch("/update")
async def edit_profile(body: ProfileUpdateRequest, ctx: AuthenticatedUser = Depends(authenticate)):
    if body.name is not None and body.name.strip() == "":
        return error(msg.NAME_CANNOT_BE_EMPTY, 400, field="name")

    user = ctx.user
    tenant_id = ctx.tenant_id

    has_changes = False
    if body.name is not None and body.name != user.name:
        has_changes = True
    if body.phone is not None and body.phone != user.phone:
        has_changes = True
    if body.secondaryPhone is not None:
        has_changes = True
    if body.permanentAddress is not None or body.temporaryAddress is not None:
        has_changes = True

    if not has_changes:
        return error(msg.NO_CHANGES_DETECTED, 400)

    async with session_scope() as session:
        db_user = await session.get(User, str(user.id))
        if not db_user:
            return error(msg.USER_ACCOUNT_DEACTIVATED, 400, field="user")

        if body.phone and body.phone != db_user.phone:
            phone_stmt = select(User).where(User.phone == body.phone)
            if tenant_id:
                phone_stmt = phone_stmt.where(User.tenantId == tenant_id)
            existing_phone_user = (await session.execute(phone_stmt)).scalar_one_or_none()
            if existing_phone_user and str(existing_phone_user.id) != str(user.id):
                return error(msg.PHONE_ALREADY_EXISTS, 400, field="phone")

        if body.name is not None and body.name != db_user.name:
            db_user.name = body.name
        if body.phone is not None and body.phone != db_user.phone:
            db_user.phone = body.phone
        if body.secondaryPhone is not None:
            db_user.secondaryPhone = body.secondaryPhone
        if body.permanentAddress is not None or body.temporaryAddress is not None:
            db_user.address = merge_address(
                db_user.address, body.permanentAddress, body.temporaryAddress
            )
        db_user.updatedAt = datetime.now(timezone.utc)
        tenant = str(db_user.tenantId) if db_user.tenantId else None
        user_id = str(db_user.id)

    return success({"id": user_id, "tenantId": tenant}, msg.PROFILE_UPDATED)


@router.post("/avatar")
async def update_avatar(
    avatar: UploadFile | None = File(default=None),
    ctx: AuthenticatedUser = Depends(authenticate),
):
    if avatar is None:
        return error(msg.AVATAR_REQUIRED, 400, field="avatar")

    user = ctx.user

    try:
        avatar_url = await save_avatar(avatar, str(user.id))
    except AvatarUploadError as exc:
        return error(exc.message, 400, field="avatar")

    async with session_scope() as session:
        db_user = await session.get(User, str(user.id))
        if not db_user:
            return error(msg.USER_ACCOUNT_DEACTIVATED, 400, field="user")
        old_avatar = db_user.avatar
        db_user.avatar = avatar_url
        db_user.updatedAt = datetime.now(timezone.utc)
        user_id = str(db_user.id)

    delete_avatar_file(old_avatar)

    return success({"id": user_id, "avatar": avatar_url}, msg.AVATAR_UPDATED)


@router.post("/customers/my/avatar")
async def update_customer_avatar(
    avatar: UploadFile | None = File(default=None),
    ctx: AuthenticatedUser = Depends(require_customer_admin),
):
    if avatar is None:
        return error(msg.AVATAR_REQUIRED, 400, field="avatar")

    tenant_id = ctx.tenant_id

    try:
        avatar_url = await save_avatar(avatar, f"customer-{tenant_id}")
    except AvatarUploadError as exc:
        return error(exc.message, 400, field="avatar")

    async with session_scope() as session:
        current_customer = (
            await session.execute(select(Customer).where(Customer.tenantId == tenant_id))
        ).scalar_one_or_none()
        if not current_customer:
            return error("Customer not found", 404, field="customer")

        old_avatar = current_customer.avatar
        current_customer.avatar = avatar_url
        current_customer.updatedAt = datetime.now(timezone.utc)
        customer_id = str(current_customer.id)

    delete_avatar_file(old_avatar)

    return success(
        {"id": customer_id, "avatar": avatar_url},
        msg.AVATAR_UPDATED,
    )
