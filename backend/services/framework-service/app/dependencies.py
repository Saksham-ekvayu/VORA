"""Auth dependencies for framework-service routes.

Delegates to vora_shared.auth.authenticate, which mirrors Node's
auth.middleware.js#authenticateToken (decode → verify → load user → check
isActive/tokenVersion) against the shared `users` collection.
"""

from fastapi import Depends
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.models import User

__all__ = ["AuthenticatedUser", "authenticate", "current_user", "current_auth"]


async def current_auth(auth: AuthenticatedUser = Depends(authenticate)) -> AuthenticatedUser:
    return auth


async def current_user(auth: AuthenticatedUser = Depends(authenticate)) -> User:
    return auth.user
