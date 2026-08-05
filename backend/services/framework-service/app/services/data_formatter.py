"""Port of data-formatter.service.js."""

from __future__ import annotations

from typing import Any

from vora_shared.models import User


def format_file_size(num_bytes: int | None) -> str:
    if not num_bytes:
        return "0 Bytes"
    sizes = ["Bytes", "KB", "MB", "GB", "TB"]
    k = 1024
    i = 0
    value = float(num_bytes)
    while value >= k and i < len(sizes) - 1:
        value /= k
        i += 1
    return f"{round(value, 2)} {sizes[i]}"


def format_user_ref(user: User | None, fallback_id: Any = None) -> dict:
    if user is not None:
        return {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "avatar": user.avatar,
        }
    return {
        "id": str(fallback_id) if fallback_id else None,
        "name": "Deleted User",
        "email": "N/A",
        "role": "N/A",
        "avatar": None,
        "isDeleted": True,
    }


def format_uploaded_by(uploaded_by_user: User | None, uploaded_by_id: Any) -> dict:
    return format_user_ref(uploaded_by_user, uploaded_by_id)
