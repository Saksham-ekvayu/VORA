"""ObjectId-compatible 24-char hex primary keys."""

from __future__ import annotations

import secrets
import time


def new_id() -> str:
    """Generate a 24-char hex id (same length as Mongo ObjectId)."""
    # 8 hex chars from unix time + 16 random hex chars
    ts = format(int(time.time()), "08x")[-8:]
    return ts + secrets.token_hex(8)


def is_valid_id(value: str | None) -> bool:
    if not value or not isinstance(value, str):
        return False
    if len(value) != 24:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False
