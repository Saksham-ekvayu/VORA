"""`package_gap_analyses` table."""

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


class GapAnalysisData(BaseModel):
    status: Literal["pending", "connected", "started", "processing", "completed", "failed"] = "pending"
    message: str | None = None
    timestamp: datetime | None = None
    deployment_gap_results: Any = Field(default_factory=list)


class PackageGapAnalysis(Base):
    __tablename__ = "package_gap_analyses"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    deploymentFrameworkId: Mapped[str | None] = mapped_column(String(24), nullable=True)
    fileHashes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    gapAnalysis: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class GapThresholdConfig(Base):
    """Configurable thresholds for gap analysis — implemented/partially_implemented/not_implemented."""

    __tablename__ = "gap_threshold_config"
    __table_args__ = (Index("ix_gap_threshold_unique", "is_active", unique=True),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    is_active: Mapped[bool] = mapped_column(default=True)
    implemented_threshold: Mapped[float] = mapped_column(default=75.0)
    partially_implemented_threshold: Mapped[float] = mapped_column(default=50.0)
    not_implemented_threshold: Mapped[float] = mapped_column(default=0.0)
    implemented_label: Mapped[str] = mapped_column(String, default="Implemented")
    partially_implemented_label: Mapped[str] = mapped_column(String, default="Partially Implemented")
    not_implemented_label: Mapped[str] = mapped_column(String, default="Not Implemented")
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
