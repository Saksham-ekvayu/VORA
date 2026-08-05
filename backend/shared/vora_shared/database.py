"""Async SQLAlchemy engine / session for the shared Postgres `vora` database."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Declarative base for all shared models."""


async def connect_db(database_url: str, *_args: Any, **_kwargs: Any) -> None:
    """Create engine, session factory, and ensure tables exist.

    Extra positional/keyword args are ignored for Beanie-era call compatibility
    (`connect_db(uri, [Model, ...])`).
    """
    global _engine, _session_factory
    if _engine is not None:
        return

    _engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    import vora_shared.models  # noqa: F401

    # Tables are now managed by Alembic migrations instead of create_all on startup
    # async with _engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)


async def disconnect_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not connected — call connect_db() first")
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an AsyncSession."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for non-Depends call sites (auth, helpers)."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
