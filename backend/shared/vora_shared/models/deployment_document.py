"""deployment_document table — owning service: deployment-docuement-service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from vora_shared.database import Base
from vora_shared.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class DeploymentFrameworkDocument(BaseModel):
    fileId: str
    fileUrl: str
    fileHash: str
    originalFileName: str
    fileSize: int
    fileType: Literal["pdf", "doc", "docx"]
    fileVersion: str
    aiExtraction: str | None = None
    uploadedAt: datetime = Field(default_factory=_utcnow)

class DeploymentDocument(Base):
    __tablename__ = "deployment_documents"
    __table_args__ = (
        Index("ix_dd_tenant_uploader", "tenantId", "uploadedBy"),
        Index("ix_dd_tenant_created", "tenantId", "createdAt"),
        Index("ix_dd_df_id", "deploymentFrameworkId"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    tenantId: Mapped[str] = mapped_column(String, nullable=False)
    deploymentFrameworkId: Mapped[str] = mapped_column(String(24), nullable=False)
    frameworkName: Mapped[str] = mapped_column(String, nullable=False)
    frameworkCode: Mapped[str | None] = mapped_column(String, nullable=True)
    frameworkVersion: Mapped[str | None] = mapped_column(String, nullable=True)
    uploadedBy: Mapped[str] = mapped_column(String(24), nullable=False)
    document: Mapped[DeploymentFrameworkDocument] = mapped_column(JSONB, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)