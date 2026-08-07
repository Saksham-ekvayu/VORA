"""Port of framework-authorization.service.js — expert access authorization."""

from __future__ import annotations

from sqlalchemy import select
from vora_shared import messages as msg
from vora_shared.database import session_scope
from vora_shared.models import FrameworkAccess, FrameworkCategory


class FrameworkAuthorizationError(Exception):
    pass


async def has_approved_access(expert_id, framework_category_id) -> bool:
    if not expert_id or not framework_category_id:
        return False
    if not await is_valid_framework_category_id(framework_category_id):
        return False
    async with session_scope() as session:
        access = (
            await session.execute(
                select(FrameworkAccess).where(
                    FrameworkAccess.expertId == str(expert_id),
                    FrameworkAccess.frameworkCategoryId == str(framework_category_id),
                    FrameworkAccess.status == "approved",
                )
            )
        ).scalar_one_or_none()
        return access is not None


async def is_valid_framework_category_id(framework_category_id) -> bool:
    if not framework_category_id:
        return False
    try:
        async with session_scope() as session:
            category = (
                await session.execute(
                    select(FrameworkCategory).where(
                        FrameworkCategory.id == str(framework_category_id),
                        FrameworkCategory.isActive.is_(True),
                    )
                )
            ).scalar_one_or_none()
    except Exception:
        return False
    return category is not None


async def is_valid_framework_code(framework_code: str) -> bool:
    if not framework_code:
        return False
    async with session_scope() as session:
        category = (
            await session.execute(
                select(FrameworkCategory).where(
                    FrameworkCategory.code == framework_code.lower(),
                    FrameworkCategory.isActive.is_(True),
                )
            )
        ).scalar_one_or_none()
        return category is not None


async def get_available_frameworks() -> list[dict]:
    async with session_scope() as session:
        categories = (
            (
                await session.execute(
                    select(FrameworkCategory)
                    .where(FrameworkCategory.isActive.is_(True))
                    .order_by(FrameworkCategory.frameworkCategoryName.asc())
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": str(category.id) if category and getattr(category, "id", None) else None,
                "code": category.code,
                "frameworkCategoryName": category.frameworkCategoryName,
                "description": category.description,
            }
            for category in categories
        ]


async def get_expert_approved_framework_codes(expert_id) -> list[str]:
    if not expert_id:
        return []
    try:
        async with session_scope() as session:
            approved = (
                (
                    await session.execute(
                        select(FrameworkAccess).where(
                            FrameworkAccess.expertId == str(expert_id),
                            FrameworkAccess.status == "approved",
                        )
                    )
                )
                .scalars()
                .all()
            )
            return [access.frameworkCode for access in approved]
    except Exception as exc:  # noqa: BLE001
        print(f"Error getting expert approved framework codes: {exc}")
        return []



