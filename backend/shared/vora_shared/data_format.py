import math
from typing import Any


def format_file_size(num_bytes: int | float | None) -> str:
    if not num_bytes or num_bytes <= 0:
        return "0 Bytes"
    sizes = ["Bytes", "KB", "MB", "GB", "TB", "PB"]
    i = math.floor(math.log(num_bytes) / math.log(1024))
    # Ensure we don't go out of bounds for extremely large numbers
    i = min(i, len(sizes) - 1)
    return f"{round((num_bytes / (1024 ** i)) * 100) / 100} {sizes[i]}"


def format_user_ref(user: Any | None, fallback_id: Any = None) -> dict:
    if user is not None:
        return {
            "id": str(user.id) if getattr(user, "id", None) else None,
            "name": getattr(user, "name", "Unknown"),
            "email": getattr(user, "email", "N/A"),
            "role": getattr(user, "role", "N/A"),
            "avatar": getattr(user, "avatar", None),
        }
    return {
        "id": str(fallback_id) if fallback_id else None,
        "name": "Deleted User",
        "email": "N/A",
        "role": "N/A",
        "avatar": None,
        "isDeleted": True,
    }


def format_uploaded_by(uploaded_by_user: Any | None, uploaded_by_id: Any = None) -> dict:
    return format_user_ref(uploaded_by_user, uploaded_by_id)
