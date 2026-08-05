"""Password hashing helpers & Context security."""

import bcrypt
import re
from dataclasses import dataclass
from fastapi import Depends, Header, HTTPException, status
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.models.user import User

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False

from vora_shared import messages as msg

_TENANT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

@dataclass
class RequestContext:
    user: User
    tenant_id: str | None

    @property
    def role(self) -> str:
        return self.user.role

def _tenant_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"message": message, "field": "tenantId"},
    )

async def get_context(
    auth: AuthenticatedUser = Depends(authenticate),
    x_tenant_id: str | None = Header(default=None, alias="x-tenant-id"),
) -> RequestContext:
    role = auth.user.role
    header_tenant_id = x_tenant_id

    if role in ("admin", "expert"):
        tenant_id = header_tenant_id.strip() if header_tenant_id else None
        return RequestContext(user=auth.user, tenant_id=tenant_id)

    if not header_tenant_id:
        raise _tenant_error(msg.TENANT_ID_REQUIRED)

    if not isinstance(header_tenant_id, str) or len(header_tenant_id.strip()) == 0:
        raise _tenant_error(msg.TENANT_ID_INVALID_FORMAT)

    trimmed = header_tenant_id.strip()

    if not _TENANT_ID_RE.match(trimmed):
        raise _tenant_error(msg.TENANT_ID_INVALID_CHARS)

    if len(trimmed) < 3 or len(trimmed) > 50:
        raise _tenant_error(msg.TENANT_ID_LENGTH)

    if auth.tenant_id and auth.tenant_id != trimmed:
        raise _tenant_error(msg.TENANT_ID_MISMATCH)

    return RequestContext(user=auth.user, tenant_id=trimmed)

def require_roles(*roles: str):
    async def _dep(ctx: RequestContext = Depends(get_context)) -> RequestContext:
        if ctx.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return ctx

    return _dep
