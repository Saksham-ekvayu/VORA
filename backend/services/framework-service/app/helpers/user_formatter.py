"""Port of user-formatter.helper.js."""

from __future__ import annotations

from typing import Any

from vora_shared.models import User


def get_user_data(user_object: User | None, user_id: Any = None) -> dict | None:
    if not user_object and user_id:
        return {
            "id": None,
            "name": "Deleted User",
            "email": "N/A",
            "role": "N/A",
            "avatar": None,
            "isDeleted": True,
        }

    if user_object is not None and getattr(user_object, "id", None):
        return {
            "id": str(user_object.id),
            "name": user_object.name,
            "email": user_object.email,
            "role": user_object.role,
            "avatar": user_object.avatar,
            "isDeleted": False,
        }

    return None
