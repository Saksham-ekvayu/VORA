"""`package_comparisons` table."""

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


class ComparisonDeploymentPoint(BaseModel):
    id: str
    point: str


class ComparisonResultItem(BaseModel):
    deployment_framework_control_id: str
    deployment_framework_control_name: str
    deployment_framework_control_description: str = ""
    deployment_framework_deployment_points: list[ComparisonDeploymentPoint] = Field(default_factory=list)
    assigned_framework_control_id: str
    assigned_framework_control_name: str
    assigned_framework_control_description: str = ""
    assigned_framework_deployment_points: list[ComparisonDeploymentPoint] = Field(default_factory=list)
    comparison_score: float = 0
    reviewComment: str = ""


class ComparisonSection(BaseModel):
    id: str
    name: str
    controls: list[ComparisonResultItem] = Field(default_factory=list)


class ComparisonData(BaseModel):
    status: Literal["pending", "connected", "started", "processing", "completed", "failed"] = "pending"
    message: str | None = None
    timestamp: datetime | None = None
    comparison_time_seconds: float | None = None
    comparison_result: list[ComparisonSection] = Field(default_factory=list)


class PackageComparison(Base):
    __tablename__ = "package_comparisons"
    __table_args__ = (Index("ix_pkg_comp_framework", "frameworkId"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    frameworkId: Mapped[str] = mapped_column(String(24), nullable=False)
    fileHashes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    comparison: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
