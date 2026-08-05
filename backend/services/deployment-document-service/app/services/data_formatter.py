"""Port of deployment-document-service-main/src/services/data-formatter.service.js."""

import math
from typing import Any

from vora_shared.models.user import User


def format_file_size(num_bytes: int | float | None) -> str:
    if not num_bytes:
        return "0 Bytes"
    k = 1024
    sizes = ["Bytes", "KB", "MB", "GB", "TB"]
    i = math.floor(math.log(num_bytes) / math.log(k))
    return f"{round((num_bytes / (k ** i)), 2)} {sizes[i]}"


def format_uploaded_by(uploaded_by: User | None, fallback_id: Any = None) -> dict[str, Any]:
    if uploaded_by is not None:
        return {
            "id": str(uploaded_by.id) if uploaded_by and getattr(uploaded_by, "id", None) else None,
            "name": uploaded_by.name,
            "email": uploaded_by.email,
            "role": uploaded_by.role,
            "avatar": uploaded_by.avatar,
        }
    return {
        "id": fallback_id,
        "name": "Deleted User",
        "email": "N/A",
        "role": "N/A",
        "avatar": None,
        "isDeleted": True,
    }
