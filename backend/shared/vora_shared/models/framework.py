"""`frameworks` table — owning service: framework-service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from vora_shared.database import Base
from vora_shared.ids import new_id

AiExtractionStatus = Literal["pending", "uploaded", "processing", "extracted", "failed"]
ApprovalStatus = Literal["pending", "approved", "rejected"]
DeploymentPointStatus = Literal["pending", "approved", "rejected"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeploymentPoint(BaseModel):
    id: str
    name: str
    status: DeploymentPointStatus = "pending"
    path: str = ""
    weightage: float = 10
    remark: str = ""


class ControlItem(BaseModel):
    id: str
    name: str
    description: str = ""
    deployment_points: list[DeploymentPoint] = Field(default_factory=list)
    weightage: float = 10
    remark: str = ""


class Section(BaseModel):
    id: str
    name: str
    controls: list[ControlItem] = Field(default_factory=list)


class Controls(BaseModel):
    total_controls: int = 0
    total_sections: int = 0
    controls_data: list[Section] = Field(default_factory=list)


class StatusHistoryEntry(BaseModel):
    status: AiExtractionStatus
    timestamp: datetime = Field(default_factory=_utcnow)
    message: str | None = None


class StatusHistory(BaseModel):
    processingTimeSeconds: float | None = None
    completedAt: datetime | None = None
    history: list[StatusHistoryEntry] = Field(default_factory=list)


class AiExtraction(BaseModel):
    status: AiExtractionStatus = "pending"
    timestamp: datetime | None = None
    message: str | None = None
    statusHistory: StatusHistory | None = None
    controls: Controls | None = None


class FileVersionEntry(BaseModel):
    fileId: str
    fileUrl: str
    fileHash: str
    originalFileName: str
    fileSize: int
    fileType: str
    fileVersion: str
    aiExtraction: AiExtraction | None = None
    uploadedAt: datetime = Field(default_factory=_utcnow)


class Approval(BaseModel):
    status: ApprovalStatus = "pending"
    by: str | None = None
    date: datetime | None = None
    remark: str | None = None


class Framework(Base):
    __tablename__ = "frameworks"
    __table_args__ = (
        Index(
            "ix_frameworks_uploader_cat_ver",
            "uploadedBy",
            "frameworkCategoryId",
            "frameworkVersion",
            unique=True,
        ),
        Index("ix_frameworks_uploaded_by", "uploadedBy"),
        Index("ix_frameworks_created", "createdAt"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    frameworkName: Mapped[str] = mapped_column(String, nullable=False)
    frameworkVersion: Mapped[str] = mapped_column(String, nullable=False)
    frameworkCategoryId: Mapped[str] = mapped_column(String(24), nullable=False)
    frameworkCode: Mapped[str] = mapped_column(String, nullable=False)
    uploadedBy: Mapped[str] = mapped_column(String(24), nullable=False)
    currentFileVersion: Mapped[str] = mapped_column(String, nullable=False, default="1.0.0")
    fileVersions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    approval: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
