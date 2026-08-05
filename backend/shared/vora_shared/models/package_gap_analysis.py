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
    __table_args__ = (Index("ix_pkg_gap_framework", "frameworkId"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    frameworkId: Mapped[str] = mapped_column(String(24), nullable=False)
    fileHashes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    gapAnalysis: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
