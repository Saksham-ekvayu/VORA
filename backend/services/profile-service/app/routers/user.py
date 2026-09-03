import logging
from datetime import datetime, timezone
from typing import Annotated

from app.schemas.user import ProfileUpdateRequest
from app.utils.formatting import (
    address_dict,
    created_by_user_id,
    customer_summary,
    format_created_by,
    merge_address,
)
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from vora_shared import messages as msg
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.avatar_uploads import AvatarUploadError, delete_avatar_file, save_avatar
from vora_shared.database import session_scope
from vora_shared.models.customer import Customer
from vora_shared.models.user import User
from vora_shared.responses import error, success

router = APIRouter(tags=["profile"])
logger = logging.getLogger(__name__)


def require_customer_admin(
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
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
async def get_profile(ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[GET-PROFILE] Profile request | user_id: {ctx.user.id}")
    user = ctx.user

    if not user.isActive:
        logger.warning(f"[GET-PROFILE] Inactive user attempted profile access: {ctx.user.id}")
        return error(msg.USER_ACCOUNT_DEACTIVATED, 400, field="user")

    creator = None
    creator_id = created_by_user_id(user.createdBy)
    async with session_scope() as session:
        if creator_id:
            creator = await session.get(User, str(creator_id))

        customer = None
        if user.tenantId:
            customer = (
                await session.execute(select(Customer).where(Customer.tenantId == user.tenantId))
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

    logger.info(f"[GET-PROFILE] Profile retrieved successfully | user_id: {ctx.user.id}")
    return success(response_data, msg.PROFILE_RETRIEVED)


@router.patch("/update")
async def edit_profile(
    body: Annotated[ProfileUpdateRequest, Body()], ctx: Annotated[AuthenticatedUser, Depends(authenticate)]
):
    logger.info(
        f"[PATCH-PROFILE] Update profile request | user_id: {ctx.user.id} | fields: name={body.name} | phone={body.phone}"
    )
    # Validate name
    if body.name is not None and body.name.strip() == "":
        logger.warning(f"[PATCH-PROFILE] Validation failed | user_id: {ctx.user.id} | reason: name_is_empty")
        return error(msg.NAME_CANNOT_BE_EMPTY, 400, field="name")

    user = ctx.user
    tenant_id = ctx.tenant_id

    # Check if there are any changes
    if not _has_profile_changes(body, user):
        return error(msg.NO_CHANGES_DETECTED, 400)

    async with session_scope() as session:
        db_user = await session.get(User, str(user.id))
        if not db_user:
            return error(msg.USER_ACCOUNT_DEACTIVATED, 400, field="user")

        # Validate phone uniqueness
        if body.phone and body.phone != db_user.phone:
            phone_check = await _check_phone_exists(session, body.phone, tenant_id, str(user.id))
            if phone_check:
                return phone_check

        # Apply updates
        _apply_profile_updates(db_user, body)
        db_user.updatedAt = datetime.now(timezone.utc)

        tenant = str(db_user.tenantId) if db_user.tenantId else None
        user_id = str(db_user.id)

    logger.info(f"[PATCH-PROFILE] Profile updated | user_id: {ctx.user.id} | tenant: {tenant}")
    return success({"id": user_id, "tenantId": tenant}, msg.PROFILE_UPDATED)


def _has_profile_changes(body: ProfileUpdateRequest, user: User) -> bool:
    """Check if any profile fields have changed."""
    if body.name is not None and body.name != user.name:
        return True
    if body.phone is not None and body.phone != user.phone:
        return True
    if body.secondaryPhone is not None and body.secondaryPhone != user.secondaryPhone:
        return True
    if body.permanentAddress is not None or body.temporaryAddress is not None:
        return True
    return False


async def _check_phone_exists(session, phone: str, tenant_id: str, user_id: str):
    """Check if phone number already exists for another user."""
    phone_stmt = select(User).where(User.phone == phone)
    if tenant_id:
        phone_stmt = phone_stmt.where(User.tenantId == tenant_id)

    existing_phone_user = (await session.execute(phone_stmt)).scalar_one_or_none()
    if existing_phone_user and str(existing_phone_user.id) != user_id:
        return error(msg.PHONE_ALREADY_EXISTS, 400, field="phone")
    return None


def _apply_profile_updates(db_user: User, body: ProfileUpdateRequest):
    """Apply profile updates to the user object."""
    if body.name is not None and body.name != db_user.name:
        db_user.name = body.name

    if body.phone is not None and body.phone != db_user.phone:
        db_user.phone = body.phone

    if body.secondaryPhone is not None and body.secondaryPhone != db_user.secondaryPhone:
        db_user.secondaryPhone = body.secondaryPhone

    if body.permanentAddress is not None or body.temporaryAddress is not None:
        db_user.address = merge_address(db_user.address, body.permanentAddress, body.temporaryAddress)


@router.post("/avatar")
async def update_avatar(
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
    avatar: Annotated[UploadFile | None, File()] = None,
):
    logger.info(
        f"[POST-AVATAR] Avatar upload request | user_id: {ctx.user.id} | filename: {avatar.filename if avatar else 'None'}"
    )
    if avatar is None:
        logger.warning(f"[POST-AVATAR] Validation failed | user_id: {ctx.user.id} | reason: avatar_required")
        return error(msg.AVATAR_REQUIRED, 400, field="avatar")

    user = ctx.user

    try:
        avatar_url = await save_avatar(avatar, str(user.id))
        logger.info(f"[POST-AVATAR] Avatar saved | user_id: {ctx.user.id} | url: {avatar_url}")
    except AvatarUploadError as exc:
        logger.exception(f"[POST-AVATAR] Error | user_id: {ctx.user.id} | error: {exc.message}")
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

    logger.info(f"[POST-AVATAR] Avatar updated | user_id: {ctx.user.id} | avatar_url: {avatar_url}")
    return success({"id": user_id, "avatar": avatar_url}, msg.AVATAR_UPDATED)


@router.post("/customers/my/avatar")
async def update_customer_avatar(
    ctx: Annotated[AuthenticatedUser, Depends(require_customer_admin)],
    avatar: Annotated[UploadFile | None, File()] = None,
):
    logger.info(
        f"[POST-CUSTOMER-AVATAR] Avatar upload request | user_id: {ctx.user.id} | tenant: {ctx.tenant_id} | filename: {avatar.filename if avatar else 'None'}"
    )
    if avatar is None:
        logger.warning(
            f"[POST-CUSTOMER-AVATAR] Validation failed | user_id: {ctx.user.id} | reason: avatar_required"
        )
        return error(msg.AVATAR_REQUIRED, 400, field="avatar")

    tenant_id = ctx.tenant_id

    try:
        avatar_url = await save_avatar(avatar, f"customer-{tenant_id}")
        logger.info(f"[POST-CUSTOMER-AVATAR] Avatar saved | tenant_id: {tenant_id} | url: {avatar_url}")
    except AvatarUploadError as exc:
        logger.exception(f"[POST-CUSTOMER-AVATAR] Error | tenant_id: {tenant_id} | error: {exc.message}")
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

    logger.info(
        f"[POST-CUSTOMER-AVATAR] Customer avatar updated | tenant_id: {ctx.tenant_id} | customer_id: {customer_id}"
    )
    return success(
        {"id": customer_id, "avatar": avatar_url},
        msg.AVATAR_UPDATED,
    )
