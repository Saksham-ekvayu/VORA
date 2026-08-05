"""SQLAlchemy pagination / search helpers (Postgres)."""

from __future__ import annotations

import inspect
import math
from typing import Any, Callable, Sequence, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from vora_shared.models.user import User

T = TypeVar("T")


async def find_by_id_or_fail(
    session: AsyncSession,
    model: type[T],
    doc_id: str,
    resource_name: str = "Resource",
) -> T:
    result = await session.execute(select(model).where(model.id == doc_id))  # type: ignore[attr-defined]
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource_name} not found"
        )
    return document


def _ilike_filters(model: type, search_term: str, search_fields: list[str]) -> list:
    conditions = []
    for field in search_fields:
        col = getattr(model, field, None)
        if col is not None:
            conditions.append(col.ilike(f"%{search_term}%"))
    return conditions


async def build_search_filter_with_user(
    session: AsyncSession,
    model: type,
    search_term: str | None,
    search_fields: list[str],
    tenant_id: str | None,
    user_field_name: str | list[str],
    stmt: Select,
) -> Select:
    if not search_term:
        return stmt

    conditions = _ilike_filters(model, search_term, search_fields)

    user_stmt = select(User.id).where(
        or_(
            User.name.ilike(f"%{search_term}%"),
            User.email.ilike(f"%{search_term}%"),
        )
    )
    if tenant_id:
        user_stmt = user_stmt.where(User.tenantId == tenant_id)
    user_rows = await session.execute(user_stmt)
    matching_user_ids = [row[0] for row in user_rows.all()]
    if matching_user_ids:
        field_names = (
            user_field_name if isinstance(user_field_name, list) else [user_field_name]
        )
        for field_name in field_names:
            col = getattr(model, field_name, None)
            if col is not None:
                conditions.append(col.in_(matching_user_ids))

    if conditions:
        stmt = stmt.where(or_(*conditions))
    return stmt


def apply_search_filter(model: type, search_term: str | None, search_fields: list[str], stmt: Select) -> Select:
    if not search_term or not search_fields:
        return stmt
    conditions = _ilike_filters(model, search_term, search_fields)
    if conditions:
        stmt = stmt.where(or_(*conditions))
    return stmt


def apply_sort(
    model: type,
    stmt: Select,
    sort_by: str | None,
    sort_order: str | None,
    allowed_sort_fields: list[str],
    default_sort: str = "createdAt",
) -> Select:
    field_name = sort_by if sort_by and sort_by in allowed_sort_fields else default_sort
    col = getattr(model, field_name, None)
    if col is None:
        return stmt
    if (sort_order or "").lower() == "asc":
        return stmt.order_by(col.asc())
    return stmt.order_by(col.desc())


def clamp_page(page: int | str | None) -> int:
    try:
        return max(1, int(page))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 1


def clamp_limit(limit: int | str | None, default: int = 10, max_limit: int = 100) -> int:
    try:
        value = int(limit)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        value = default
    return max(1, min(max_limit, value))


def build_pagination_meta(page: int, limit: int, total: int) -> dict[str, Any]:
    total_pages = math.ceil(total / limit) if limit else 0
    return {
        "currentPage": page,
        "totalPages": total_pages,
        "totalItems": total,
        "itemsPerPage": limit,
        "hasNextPage": page < total_pages,
        "hasPrevPage": page > 1,
    }


async def paginate_stmt(
    session: AsyncSession,
    stmt: Select,
    *,
    page: int | str | None = 1,
    limit: int | str | None = 10,
) -> tuple[list, dict[str, Any]]:
    page_num = clamp_page(page)
    limit_num = clamp_limit(limit)
    skip = (page_num - 1) * limit_num

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    rows = await session.execute(stmt.offset(skip).limit(limit_num))
    documents = list(rows.scalars().all())
    return documents, build_pagination_meta(page_num, limit_num, total)


async def paginate_with_search(
    session: AsyncSession,
    model: type,
    *,
    page: Any = 1,
    limit: Any = 10,
    search: str | None = None,
    search_fields: list[str] | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    allowed_sort_fields: list[str] | None = None,
    base_filters: Sequence | None = None,
    user_search: dict[str, Any] | None = None,
    transform: Callable | None = None,
) -> dict[str, Any]:
    search_fields = search_fields or []
    allowed_sort_fields = allowed_sort_fields or []

    stmt: Select = select(model)
    for f in base_filters or []:
        stmt = stmt.where(f)

    if user_search is not None:
        stmt = await build_search_filter_with_user(
            session,
            model,
            search,
            search_fields,
            user_search.get("tenant_id"),
            user_search.get("field_name", "uploadedBy"),
            stmt,
        )
    else:
        stmt = apply_search_filter(model, search, search_fields, stmt)

    stmt = apply_sort(model, stmt, sort_by, sort_order, allowed_sort_fields)

    documents, pagination = await paginate_stmt(session, stmt, page=page, limit=limit)

    if transform:
        if inspect.iscoroutinefunction(transform):
            data = [await transform(doc) for doc in documents]
        else:
            data = [transform(doc) for doc in documents]
    else:
        data = documents

    return {"data": data, "pagination": pagination}


# ---- Compatibility shims used by older call sites ----

def build_search_filter(
    search_term: str | None,
    search_fields: list[str],
    additional_filters: dict[str, Any],
) -> dict[str, Any]:
    return {**additional_filters, "_search": search_term, "_search_fields": search_fields}


def build_sort_object(
    sort_by: str | None,
    sort_order: str | None,
    allowed_sort_fields: list[str],
    default_sort: tuple[str, int] = ("createdAt", -1),
) -> list[tuple[str, int]]:
    if not sort_by or sort_by not in allowed_sort_fields:
        return [default_sort]
    order = 1 if (sort_order or "").lower() == "asc" else -1
    return [(sort_by, order)]


def build_filter(
    search: str | None,
    search_fields: list[str],
    *,
    base_filter: dict[str, Any] | None = None,
    additional_filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {**(base_filter or {}), **(additional_filters or {}), "_search": search, "_search_fields": search_fields}


def self_tenant_query(tenant_id: str | None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"tenantId": tenant_id, **(extra or {})}


def admin_tenant_query(tenant_id: str | None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    extra = dict(extra or {})
    if not tenant_id:
        return extra
    return {"tenantId": tenant_id, **extra}


def resolve_sort(
    sort_by: str | None,
    sort_order: str | None,
    allowed_fields: list[str],
    default: str = "-createdAt",
) -> str:
    if sort_by and sort_by in allowed_fields:
        prefix = "+" if (sort_order or "").lower() == "asc" else "-"
        return f"{prefix}{sort_by}"
    return default


# Legacy aliases
paginate = paginate_stmt
