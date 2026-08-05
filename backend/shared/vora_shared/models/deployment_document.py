"""`deployment_documents` table — owning service: deployment-document-service."""

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


class DeploymentDocumentFileVersion(BaseModel):
    fileVersion: str
    fileId: str
    fileUrl: str
    fileHash: str
    originalFileName: str
    fileSize: int
    documentType: Literal["pdf", "doc", "docx", "xls", "xlsx"]
    uploadedAt: datetime = Field(default_factory=_utcnow)
    aiUpload: Any = None


class DeploymentDocument(Base):
    __tablename__ = "deployment_documents"
    __table_args__ = (
        Index("ix_dd_tenant_uploader", "tenantId", "uploadedBy"),
        Index("ix_dd_tenant_created", "tenantId", "createdAt"),
        Index("ix_dd_tenant_name", "tenantId", "documentName", unique=True),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    tenantId: Mapped[str] = mapped_column(String, nullable=False)
    documentName: Mapped[str] = mapped_column(String, nullable=False)
    uploadedBy: Mapped[str] = mapped_column(String(24), nullable=False)
    deploymentFrameworkId: Mapped[str | None] = mapped_column(String(24), nullable=True)
    controlId: Mapped[str | None] = mapped_column(String, nullable=True)
    controlName: Mapped[str | None] = mapped_column(String, nullable=True)
    deploymentPoint: Mapped[str | None] = mapped_column(String, nullable=True)
    currentFileVersion: Mapped[str] = mapped_column(String, nullable=False, default="1.0.0")
    fileVersions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
