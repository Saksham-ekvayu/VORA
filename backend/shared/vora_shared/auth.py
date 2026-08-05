import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
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


def decode_unverified(token: str) -> dict[str, Any] | None:
    return jwt.decode(token, options={"verify_signature": False})


async def get_tenant_id(
    x_tenant_id: str | None = Header(default=None, alias="x-tenant-id"),
) -> str | None:
    return x_tenant_id


async def require_auth(
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


async def authenticate(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    header_tenant_id: str | None = Depends(get_tenant_id),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    """JWT auth against shared Postgres `users` table."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please login to continue.")

    token = credentials.credentials
    try:
        unverified = decode_unverified(token)
    except jwt.PyJWTError:
        unverified = None
    if not unverified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session is invalid. Please login again.")

    tenant_id = unverified.get("tenantId") or None

    try:
        payload = verify_token(token, tenant_id, settings)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please login again."
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Your session is invalid. Please login again."
        ) from exc

    if header_tenant_id and payload.get("tenantId") != header_tenant_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session is invalid. Please login again.")

    user_id = payload.get("sub")
    user: User | None = None
    if user_id:
        async with session_scope() as session:
            result = await session.execute(select(User).where(User.id == str(user_id)))
            user = result.scalar_one_or_none()
            if user is not None:
                # Detach-friendly: keep attrs loaded after session closes
                session.expunge(user)

    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session is invalid. Please login again.")

    if not user.isActive:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            {
                "message": "Your account has been deactivated. Please contact administrator.",
                "field": "account",
            },
        )

    token_version = payload.get("tokenVersion")
    if token_version is not None and user.tokenVersion != token_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please login again.")

    return AuthenticatedUser(user=user, tenant_id=tenant_id)
