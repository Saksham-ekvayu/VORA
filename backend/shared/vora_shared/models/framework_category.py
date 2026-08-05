"""`framework_categories` table — owning service: framework-category-service."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from vora_shared.database import Base
from vora_shared.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FrameworkCategory(Base):
    __tablename__ = "framework_categories"
    __table_args__ = (
        Index("ix_framework_categories_code", "code", unique=True),
        Index("ix_framework_categories_active", "isActive"),
        Index("ix_framework_categories_created", "createdAt"),
        Index("ix_framework_categories_created_by", "createdBy"),
        Index("ix_framework_categories_updated_by", "updatedBy"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String, nullable=False)
    frameworkCategoryName: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    isActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    createdBy: Mapped[str] = mapped_column(String(24), nullable=False)
    updatedBy: Mapped[str | None] = mapped_column(String(24), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
