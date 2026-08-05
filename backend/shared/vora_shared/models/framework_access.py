"""`framework_category_access` table — owning service: framework-category-service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vora_shared.database import Base
from vora_shared.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApprovalInfo(BaseModel):
    approvedBy: str | None = None
    approvedAt: datetime | None = None


class RejectionInfo(BaseModel):
    rejectedBy: str | None = None
    rejectedAt: datetime | None = None


class RevocationInfo(BaseModel):
    revokedBy: str | None = None
    revokedAt: datetime | None = None


class FrameworkAccess(Base):
    __tablename__ = "framework_category_access"
    __table_args__ = (
        Index("ix_fca_expert_code", "expertId", "frameworkCode", unique=True),
        Index("ix_fca_expert_status", "expertId", "status"),
        Index("ix_fca_code_status", "frameworkCode", "status"),
        Index("ix_fca_created", "createdAt"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    expertId: Mapped[str] = mapped_column(String(24), nullable=False)
    frameworkCategoryId: Mapped[str] = mapped_column(String(24), nullable=False)
    frameworkCode: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    requestedBy: Mapped[str] = mapped_column(String, nullable=False)
    approval: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rejection: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    revocation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
