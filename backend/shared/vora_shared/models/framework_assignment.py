"""`framework_assignments` table — owning service: deployment-framework-service."""

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


class AssignmentWeightage(BaseModel):
    framework_weightage: float = 0
    customer_weightage: float = 0


class AssignmentCustomization(BaseModel):
    source: Literal["system", "custom"] = "system"
    addedBy: str | None = None
    addedAt: datetime | None = None
    updatedAt: datetime | None = None
    is_applicable: bool = True
    weightage: AssignmentWeightage = Field(
        default_factory=lambda: AssignmentWeightage(framework_weightage=10, customer_weightage=10)
    )


class AssignmentDeploymentPoint(BaseModel):
    id: str
    name: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    path: str = ""
    weightage: AssignmentWeightage = Field(default_factory=AssignmentWeightage)
    score: float = 0
    remark: str = ""


class AssignmentControl(BaseModel):
    id: str
    name: str
    description: str = ""
    deployment_points: list[AssignmentDeploymentPoint] = Field(default_factory=list)
    customization: AssignmentCustomization = Field(default_factory=AssignmentCustomization)


class AssignmentSection(BaseModel):
    id: str
    name: str
    controls: list[AssignmentControl] = Field(default_factory=list)


class AssignmentFileVersion(BaseModel):
    fileVersion: str
    fileId: str
    fileUrl: str
    fileHash: str
    originalFileName: str
    fileSize: int
    fileType: str | None = None
    uploadedAt: datetime = Field(default_factory=_utcnow)
    aiExtraction: str | list[AssignmentSection] | None = None


class AssignmentInfo(BaseModel):
    assignedBy: str | None = None
    assignedAt: datetime | None = None


class AssignmentRevocation(BaseModel):
    revokedBy: str | None = None
    revokedAt: datetime | None = None


class AssignmentFinalization(BaseModel):
    isFinalized: bool = False
    finalizedBy: str | None = None
    finalizedAt: datetime | None = None


class FrameworkAssignment(Base):
    __tablename__ = "framework_assignments"
    __table_args__ = (
        Index(
            "ix_fa_tenant_customer_ver",
            "tenantId",
            "customerId",
            "frameworkVersion",
            unique=True,
        ),
        Index("ix_fa_tenant_customer_status", "tenantId", "customerId", "status"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    tenantId: Mapped[str] = mapped_column(String, nullable=False)
    customerId: Mapped[str] = mapped_column(String(24), nullable=False)
    frameworkId: Mapped[str] = mapped_column(String(24), nullable=False)
    frameworkCode: Mapped[str] = mapped_column(String, nullable=False)
    frameworkName: Mapped[str | None] = mapped_column(String, nullable=True)
    frameworkVersion: Mapped[str | None] = mapped_column(String, nullable=True)
    frameworkCategoryId: Mapped[str | None] = mapped_column(String, nullable=True)
    uploadedBy: Mapped[str | None] = mapped_column(String(24), nullable=True)
    currentFileVersion: Mapped[str] = mapped_column(String, nullable=False, default="1.0.0")
    fileVersions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String, nullable=False, default="assigned")
    assignment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    revocation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    finalization: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
