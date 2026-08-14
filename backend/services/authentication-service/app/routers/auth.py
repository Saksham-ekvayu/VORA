import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any

import vora_shared
from app.schemas.auth import (
    ChangePasswordRequest,
    EmailOnlyRequest,
    LoginRequest,
    OtpVerifyRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from vora_shared import messages as msg
from vora_shared.auth import AuthenticatedUser, authenticate, sign_token
from vora_shared.database import session_scope
from vora_shared.email import generate_otp, load_template, send_email
from vora_shared.models.user import User, UserCreatedBy, UserOtp
from vora_shared.responses import error, success
from vora_shared.security import hash_password, verify_password

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(vora_shared.__file__).resolve().parent / "templates"


def _public_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
    }


def _otp_dict(otp: UserOtp | None) -> dict[str, Any] | None:
    if otp is None:
        return None
    return otp.model_dump(mode="json")


def _parse_otp(raw: dict[str, Any] | None) -> UserOtp | None:
    if not raw:
        return None
    return UserOtp.model_validate(raw)


async def _invalidate_tokens(user_id: str, *, password: str | None = None) -> None:
    """Bump tokenVersion so previously issued JWTs become invalid."""
    async with session_scope() as session:
        user = await session.get(User, user_id)
        if not user:
            return
        user.tokenVersion += 1
        user.updatedAt = datetime.now(timezone.utc)
        if password is not None:
            user.password = password


@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    logger.info(f"[REGISTER] New registration attempt for email: {body.email}")
    async with session_scope() as session:
        existing_user = (
            await session.execute(select(User).where(User.email == body.email))
        ).scalar_one_or_none()
        if existing_user:
            if not existing_user.isActive:
                logger.warning(f"[REGISTER] Attempt to register with deactivated account: {body.email}")
                return error(msg.ACCOUNT_DEACTIVATED, 400, field="email")
            logger.warning(f"[REGISTER] User already exists: {body.email}")
            return error(msg.USER_ALREADY_EXISTS, 400, field="email")

        if body.phone:
            phone_user = (
                await session.execute(select(User).where(User.phone == body.phone))
            ).scalar_one_or_none()
            if phone_user:
                if not phone_user.isActive:
                    logger.warning(f"[REGISTER] Phone belongs to deactivated account: {body.phone}")
                    return error(msg.ACCOUNT_DEACTIVATED, 400, field="phone")
                logger.warning(f"[REGISTER] Phone number already exists: {body.phone}")
                return error("Phone number already exists", 400, field="phone")

        otp = generate_otp()
        otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
        hashed_password = hash_password(body.password)

        user_count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
        assigned_role = "admin" if user_count == 0 else "user"

        new_user = User(
            tenantId=None,
            name=body.name,
            email=body.email,
            password=hashed_password,
            phone=body.phone,
            role=assigned_role,
            createdBy=UserCreatedBy(type="self", userId=None).model_dump(mode="json"),
            otp=_otp_dict(UserOtp(code=otp, expiresAt=otp_expiry)),
            address={},
        )
        session.add(new_user)
        await session.flush()
        user_name = new_user.name
        user_email = body.email
        user_id = new_user.id
        logger.info(f"[REGISTER] User created in DB: {user_id} | email: {user_email} | role: {assigned_role}")

    email_sent = await send_email(
        user_email,
        msg.EMAIL_SUBJECT_REGISTRATION,
        load_template(TEMPLATES_DIR, "registration-otp", {"otp": otp, "userName": user_name}),
    )
    if not email_sent:
        logger.error(f"[REGISTER] Failed to send OTP email for: {user_email}")
        async with session_scope() as session:
            doomed = await session.get(User, user_id)
            if doomed:
                await session.delete(doomed)
        return error(msg.EMAIL_SEND_FAILED, 500)

    logger.info(f"[REGISTER] Registration successful for: {user_email}")
    return success(
        {"email": body.email},
        "Registration created successfully. Please verify your email.",
        201,
    )


@router.post("/verify-otp")
async def verify_otp(body: OtpVerifyRequest):
    logger.info(f"[VERIFY-OTP] OTP verification attempt for: {body.email}")
    async with session_scope() as session:
        user = (await session.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
        if not user:
            logger.warning(f"[VERIFY-OTP] User not found: {body.email}")
            return error(msg.USER_NOT_FOUND_EMAIL, 400, field="email")

        otp = _parse_otp(user.otp)
        if not otp or not otp.code or not otp.expiresAt:
            logger.warning(f"[VERIFY-OTP] OTP not found for: {body.email}")
            return error(msg.OTP_NOT_FOUND, 400, field="otp")

        expires_at = otp.expiresAt
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            logger.warning(f"[VERIFY-OTP] OTP expired for: {body.email}")
            return error(msg.OTP_EXPIRED, 400, field="otp")

        if otp.code != body.otp:
            logger.warning(f"[VERIFY-OTP] Invalid OTP for: {body.email}")
            return error(msg.OTP_INVALID, 400, field="otp")

        user.isEmailVerified = True
        user.isActive = True
        user.otp = None
        user.updatedAt = datetime.now(timezone.utc)
        email = user.email
        logger.info(f"[VERIFY-OTP] Email verified successfully for: {email}")

    return success({"email": email}, msg.EMAIL_VERIFIED_SUCCESS)


@router.post("/resend-otp")
async def resend_otp(body: EmailOnlyRequest):
    logger.info(f"[RESEND-OTP] OTP resend request for: {body.email}")
    otp = generate_otp()
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    async with session_scope() as session:
        user = (await session.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
        if not user:
            logger.warning(f"[RESEND-OTP] User not found: {body.email}")
            return error(msg.USER_NOT_FOUND_EMAIL, 400, field="email")
        user.otp = _otp_dict(UserOtp(code=otp, expiresAt=otp_expiry))
        user.updatedAt = datetime.now(timezone.utc)
        user_name = user.name
        user_id = user.id

    email_sent = await send_email(
        body.email,
        msg.EMAIL_SUBJECT_RESEND_OTP,
        load_template(TEMPLATES_DIR, "resend-otp", {"otp": otp, "userName": user_name}),
    )
    if not email_sent:
        logger.error(f"[RESEND-OTP] Failed to send OTP for: {body.email} | user_id: {user_id}")
        return error(msg.EMAIL_SEND_FAILED, 500)

    logger.info(f"[RESEND-OTP] OTP resent successfully to: {body.email} | user_id: {user_id}")
    return success(None, msg.OTP_SENT_SUCCESS)


@router.post("/login")
async def login(body: LoginRequest):
    logger.info(f"[LOGIN] Login attempt for email: {body.email}")
    async with session_scope() as session:
        user = (await session.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
        if not user:
            logger.warning(f"[LOGIN] User not found: {body.email}")
            return error(msg.USER_NOT_FOUND_EMAIL, 400, field="email")

        if not user.isActive:
            logger.warning(f"[LOGIN] Account deactivated: {body.email}")
            return error(msg.ACCOUNT_DEACTIVATED, 403, field="account")

        if not user.isEmailVerified:
            logger.warning(f"[LOGIN] Email not verified: {body.email}")
            return error(msg.ACCOUNT_NOT_VERIFIED, 400, field="email")

        if not verify_password(body.password, user.password):
            logger.warning(f"[LOGIN] Invalid password for: {body.email}")
            return error(msg.INVALID_CREDENTIALS, 400, field="password")

        user.tokenVersion += 1
        user.updatedAt = datetime.now(timezone.utc)
        await session.flush()

        token = sign_token(
            {
                "sub": str(user.id),
                "tenantId": str(user.tenantId) if user.tenantId else None,
                "role": user.role,
                "tokenVersion": user.tokenVersion,
            },
            user.tenantId,
        )
        public = _public_user(user)
        tenant = str(user.tenantId) if user.tenantId else None
        logger.info(f"[LOGIN] Successful login for: {body.email} | user_id: {user.id} | role: {user.role}")

    return success(
        {"token": token, "tenantId": tenant, "user": public},
        msg.LOGIN_SUCCESS,
    )


@router.post("/forgot-password")
async def forgot_password(body: EmailOnlyRequest):
    logger.info(f"[FORGOT-PASSWORD] Password reset attempt for: {body.email}")
    otp = generate_otp()
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    async with session_scope() as session:
        user = (
            await session.execute(select(User).where(User.email == body.email, User.isActive.is_(True)))
        ).scalar_one_or_none()
        if not user:
            logger.warning(f"[FORGOT-PASSWORD] User not found or inactive: {body.email}")
            return error(msg.USER_NOT_FOUND_EMAIL, 400, field="email")
        user.otp = _otp_dict(UserOtp(code=otp, expiresAt=otp_expiry, purpose="password_reset"))
        user.updatedAt = datetime.now(timezone.utc)
        user_name = user.name
        user_id = user.id

    email_sent = await send_email(
        body.email,
        msg.EMAIL_SUBJECT_PASSWORD_RESET,
        load_template(TEMPLATES_DIR, "forgot-password-otp", {"otp": otp, "userName": user_name}),
    )
    if not email_sent:
        logger.error(
            f"[FORGOT-PASSWORD] Failed to send reset OTP email for: {body.email} | user_id: {user_id}"
        )
        return error(msg.EMAIL_SEND_FAILED, 500)

    logger.info(f"[FORGOT-PASSWORD] Reset OTP sent successfully to: {body.email} | user_id: {user_id}")
    return success(None, msg.PASSWORD_RESET_OTP_SENT)


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    logger.info(f"[RESET-PASSWORD] Password reset attempt for: {body.email}")
    async with session_scope() as session:
        user = (
            await session.execute(select(User).where(User.email == body.email, User.isActive.is_(True)))
        ).scalar_one_or_none()
        if not user:
            logger.warning(f"[RESET-PASSWORD] User not found or inactive: {body.email}")
            return error(msg.USER_NOT_FOUND_EMAIL, 400, field="email")

        otp = _parse_otp(user.otp)
        if not otp or not otp.code or not otp.expiresAt:
            logger.warning(f"[RESET-PASSWORD] OTP not found for: {body.email}")
            return error(msg.OTP_NOT_FOUND, 400, field="otp")

        if otp.purpose and otp.purpose != "password_reset":
            logger.warning(
                f"[RESET-PASSWORD] Wrong OTP purpose for: {body.email} | expected: password_reset | actual: {otp.purpose}"
            )
            return error(msg.OTP_WRONG_PURPOSE, 400, field="otp")

        expires_at = otp.expiresAt
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            logger.warning(f"[RESET-PASSWORD] OTP expired for: {body.email}")
            return error(msg.OTP_EXPIRED, 400, field="otp")

        if otp.code != body.otp:
            logger.warning(f"[RESET-PASSWORD] Invalid OTP for: {body.email}")
            return error(msg.OTP_INVALID, 400, field="otp")

        if verify_password(body.password, user.password):
            logger.warning(f"[RESET-PASSWORD] New password is same as old password for: {body.email}")
            return error(msg.PASSWORD_SAME_AS_OLD, 400, field="password")

        user.password = hash_password(body.password)
        user.otp = None
        user.tokenVersion += 1
        user.updatedAt = datetime.now(timezone.utc)
        user_id = user.id

    logger.info(f"[RESET-PASSWORD] Password reset successfully for: {body.email} | user_id: {user_id}")
    return success(None, msg.PASSWORD_RESET_SUCCESS)


@router.post("/verify-email")
async def send_verification_otp(body: EmailOnlyRequest):
    logger.info(f"[VERIFY-EMAIL] Email verification OTP request for: {body.email}")
    otp = generate_otp()
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    async with session_scope() as session:
        user = (await session.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
        if not user:
            logger.warning(f"[VERIFY-EMAIL] User not found: {body.email}")
            return error(msg.USER_NOT_FOUND_EMAIL, 400, field="email")

        if not user.isActive:
            logger.warning(f"[VERIFY-EMAIL] Account deactivated: {body.email}")
            return error(msg.ACCOUNT_DEACTIVATED, 403, field="account")

        if user.isEmailVerified:
            logger.warning(f"[VERIFY-EMAIL] Email already verified: {body.email}")
            return error(msg.EMAIL_ALREADY_VERIFIED, 400, field="email")

        user.otp = _otp_dict(UserOtp(code=otp, expiresAt=otp_expiry, purpose="email_verification"))
        user.updatedAt = datetime.now(timezone.utc)
        user_name = user.name
        user_id = user.id

    email_sent = await send_email(
        body.email,
        msg.EMAIL_SUBJECT_EMAIL_VERIFICATION,
        load_template(TEMPLATES_DIR, "email-verification-otp", {"otp": otp, "userName": user_name}),
    )
    if not email_sent:
        logger.error(f"[VERIFY-EMAIL] Failed to send verification OTP for: {body.email} | user_id: {user_id}")
        return error(msg.EMAIL_SEND_FAILED, 500)

    logger.info(f"[VERIFY-EMAIL] Verification OTP sent successfully to: {body.email} | user_id: {user_id}")
    return success(None, msg.VERIFICATION_OTP_SENT)


@router.post("/logout")
async def logout(ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[LOGOUT] Logout request for user_id: {ctx.user.id}")
    await _invalidate_tokens(ctx.user.id)
    logger.info(f"[LOGOUT] User logged out successfully | user_id: {ctx.user.id}")
    return success(None, msg.LOGOUT_SUCCESS)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(f"[CHANGE-PASSWORD] Password change attempt for user_id: {ctx.user.id}")
    async with session_scope() as session:
        user = await session.get(User, ctx.user.id)
        if not user:
            logger.warning(f"[CHANGE-PASSWORD] User not found: {ctx.user.id}")
            return error(msg.USER_NOT_FOUND_EMAIL, 400)

        if not verify_password(body.currentPassword, user.password):
            logger.warning(f"[CHANGE-PASSWORD] Current password mismatch for user_id: {ctx.user.id}")
            return error(msg.PASSWORD_MISMATCH, 400, field="currentPassword")

        if verify_password(body.newPassword, user.password):
            logger.warning(f"[CHANGE-PASSWORD] New password same as old for user_id: {ctx.user.id}")
            return error(msg.PASSWORD_SAME_AS_OLD, 400, field="newPassword")

        user.password = hash_password(body.newPassword)
        user.tokenVersion += 1
        user.updatedAt = datetime.now(timezone.utc)
        user_id = ctx.user.id

    logger.info(f"[CHANGE-PASSWORD] Password changed successfully for user_id: {user_id}")
    return success(None, msg.PASSWORD_CHANGED_SUCCESS)
