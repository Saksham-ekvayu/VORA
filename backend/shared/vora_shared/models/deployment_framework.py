"""`deployment_frameworks` table — owning service: deployment-framework-service."""

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


class ExpertReview(BaseModel):
    status: Literal["pending", "requested", "approved", "rejected"] = "pending"
    assignedExpert: str | None = None
    requestedAt: datetime | None = None
    reviewedAt: datetime | None = None
    comments: str | None = None


class FrameworkPackageDocument(BaseModel):
    fileId: str
    fileUrl: str
    fileHash: str
    originalFileName: str
    fileSize: int
    fileType: Literal["pdf", "doc", "docx"]
    fileVersion: str
    aiExtraction: str | None = None
    replicated: bool = False
    uploadedAt: datetime = Field(default_factory=_utcnow)


class PackageVersion(BaseModel):
    packageVersion: str
    type: Literal["pre-release", "in-review", "deployed"]
    trigger: str | None = None
    status: Literal["pending", "returned", "live", "superseded"] = "pending"
    documents: list[FrameworkPackageDocument] = Field(default_factory=list)
    mergeDocument: str | None = None
    comparison: str | None = None
    gapAnalysis: str | None = None
    expertReview: ExpertReview = Field(default_factory=ExpertReview)
    createdAt: datetime = Field(default_factory=_utcnow)
    updatedAt: datetime = Field(default_factory=_utcnow)


class DeploymentFramework(Base):
    __tablename__ = "deployment_frameworks"
    __table_args__ = (
        Index("ix_df_tenant_uploader", "tenantId", "uploadedBy"),
        Index("ix_df_tenant_created", "tenantId", "createdAt"),
        Index("ix_df_tenant_category", "tenantId", "frameworkCategoryId"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    tenantId: Mapped[str] = mapped_column(String, nullable=False)
    assignedFrameworkId: Mapped[str] = mapped_column(String(24), nullable=False)
    frameworkId: Mapped[str | None] = mapped_column(String, nullable=True)
    frameworkName: Mapped[str] = mapped_column(String, nullable=False)
    frameworkCategoryId: Mapped[str | None] = mapped_column(String, nullable=True)
    frameworkCode: Mapped[str | None] = mapped_column(String, nullable=True)
    frameworkVersion: Mapped[str | None] = mapped_column(String, nullable=True)
    uploadedBy: Mapped[str] = mapped_column(String(24), nullable=False)
    currentPackageVersion: Mapped[str] = mapped_column(String, nullable=False, default="1.0.0")
    packages: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
