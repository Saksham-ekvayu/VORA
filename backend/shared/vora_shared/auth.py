import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from vora_shared import messages as msg
from vora_shared.config import Settings, get_settings
from vora_shared.database import session_scope
from vora_shared.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def project_secret(settings: Settings, tenant_id: str | None) -> str:
    """Match Node JWTUtil.generateProjectSecret."""
    if not tenant_id:
        return settings.jwt_secret
    digest = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        f"{tenant_id}:{settings.jwt_project_salt}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def _parse_expires(expires_in: str) -> timedelta:
    unit = expires_in[-1]
    value = int(expires_in[:-1])
    if unit == "d":
        return timedelta(days=value)
    if unit == "h":
        return timedelta(hours=value)
    if unit == "m":
        return timedelta(minutes=value)
    return timedelta(seconds=value)


def sign_token(
    payload: dict[str, Any],
    tenant_id: str | None,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    body = {**payload}
    body.setdefault("iat", datetime.now(timezone.utc))
    body["exp"] = datetime.now(timezone.utc) + _parse_expires(settings.jwt_expires_in)
    return jwt.encode(body, project_secret(settings, tenant_id), algorithm="HS256")


def verify_token(
    token: str,
    tenant_id: str | None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    return jwt.decode(
        token,
        project_secret(settings, tenant_id),
        algorithms=["HS256"],
    )


def get_tenant_id(
    x_tenant_id: str | None = Header(default=None, alias="x-tenant-id"),
) -> str | None:
    return x_tenant_id


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    tenant_id: str | None = Depends(get_tenant_id),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    try:
        return verify_token(credentials.credentials, tenant_id, settings)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


@dataclass
class AuthenticatedUser:
    """Result of `authenticate` — mirrors Node's `req.user` + `req.tenantId`."""

    user: User
    tenant_id: str | None


def _validate_token_with_tenant_fallback(
    token: str,
    header_tenant_id: str | None,
    settings: Settings,
) -> dict[str, Any]:
    """
    Verify JWT token by trying with different tenant secrets.
    First tries with the header tenant ID, then falls back to the default secret.
    Returns the verified payload.
    """
    # Try with header tenant ID first
    if header_tenant_id:
        try:
            return verify_token(token, header_tenant_id, settings)
        except jwt.PyJWTError:
            # Continue to try with default secret
            pass

    # Try with default tenant secret (no tenant)
    try:
        return verify_token(token, None, settings)
    except jwt.PyJWTError as exc:
        # If both attempts fail, raise the error
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, msg.SESSION_INVALID) from exc


def _validate_tenant_match(header_tenant_id: str | None, payload_tenant_id: str | None):
    """Validate that header tenant ID matches payload tenant ID."""
    if header_tenant_id and payload_tenant_id != header_tenant_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, msg.SESSION_INVALID)


async def _fetch_user(user_id: str | None) -> User | None:
    """Fetch user from database by ID."""
    if not user_id:
        return None

    async with session_scope() as session:
        result = await session.execute(select(User).where(User.id == str(user_id)))
        user = result.scalar_one_or_none()
        if user is not None:
            # Detach-friendly: keep attrs loaded after session closes
            session.expunge(user)
        return user


def _validate_user(user: User | None) -> User:
    """Validate user exists and is active."""
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, msg.SESSION_INVALID)

    if not user.isActive:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            {
                "message": msg.ACCOUNT_DEACTIVATED,
                "field": "account",
            },
        )
    return user


def _validate_token_version(payload: dict[str, Any], user: User):
    """Validate token version matches user's current token version."""
    token_version = payload.get("tokenVersion")
    if token_version is not None and user.tokenVersion != token_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, msg.SESSION_EXPIRED)


async def authenticate(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    header_tenant_id: str | None = Depends(get_tenant_id),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    """JWT auth against shared Postgres `users` table."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please login to continue.")

    token = credentials.credentials

    # Step 1: Verify token signature with appropriate tenant secret
    # This tries header tenant first, then falls back to no tenant
    payload = _validate_token_with_tenant_fallback(token, header_tenant_id, settings)

    # Step 2: Validate tenant match
    _validate_tenant_match(header_tenant_id, payload.get("tenantId"))

    # Step 3: Fetch and validate user
    user = await _fetch_user(payload.get("sub"))
    user = _validate_user(user)

    # Step 4: Validate token version
    _validate_token_version(payload, user)

    # Get the tenant ID from the payload (after verification)
    tenant_id_from_payload = payload.get("tenantId") or None

    return AuthenticatedUser(user=user, tenant_id=tenant_id_from_payload)
