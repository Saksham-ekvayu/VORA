"""`package_merges` table."""

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


class MergeDeploymentPoint(BaseModel):
    id: str
    name: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    path: str = ""
    weightage: float = 10
    remark: str = ""


class MergeControlItem(BaseModel):
    id: str
    name: str
    description: str = ""
    deployment_points: list[MergeDeploymentPoint] = Field(default_factory=list)


class MergeSection(BaseModel):
    id: str
    name: str
    controls: list[MergeControlItem] = Field(default_factory=list)


class SourceDocument(BaseModel):
    fileId: str
    fileHash: str | None = None
    originalFileName: str
    mergedAt: datetime | None = None


class MergeExtraction(BaseModel):
    status: Literal["pending", "processing", "merged", "failed"] = "pending"
    timestamp: datetime | None = None
    message: str | None = None
    controls_data: list[MergeSection] = Field(default_factory=list)


class PackageMerge(Base):
    __tablename__ = "package_merges"
    __table_args__ = (Index("ix_pkg_merge_framework", "frameworkId"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    frameworkId: Mapped[str] = mapped_column(String(24), nullable=False)
    fileHashes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    sourceDocuments: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    mergeExtraction: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
