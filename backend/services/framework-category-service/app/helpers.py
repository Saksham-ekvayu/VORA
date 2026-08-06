"""Ports of Node's src/helpers/*.helper.js for framework-category-service."""

import re

from sqlalchemy import select
from vora_shared.database import session_scope
from vora_shared.models import FrameworkCategory, User


def to_title_case(value: str) -> str:
    """Mirrors Node's toTitleCase: lowercase everything, then capitalize each word."""
    return re.sub(r"\b\w", lambda m: m.group().upper(), value.lower())

async def code_exists(code: str, exclude_id: str | None = None) -> bool:
    """Mirrors helpers/framework-category-query.helper.js#codeExists."""
    async with session_scope() as session:
        stmt = select(FrameworkCategory).where(FrameworkCategory.code == code.lower())
        if exclude_id:
            stmt = stmt.where(FrameworkCategory.id != str(exclude_id))
        existing = (await session.execute(stmt)).scalar_one_or_none()
        return existing is not None


async def fetch_users_by_ids(ids: set) -> dict[str, User]:
    id_list = [str(i) for i in ids if i]
    if not id_list:
        return {}
    async with session_scope() as session:
        users = (await session.execute(select(User).where(User.id.in_(id_list)))).scalars().all()
        return {str(u.id): u for u in users}
