"""`document_extractions` table — AI extraction cache by file hash."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vora_shared.database import Base
from vora_shared.ids import new_id

ExtractionStatus = Literal["pending", "uploaded", "processing", "extracted", "failed"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ExtractionDeploymentPoint(BaseModel):
    id: str
    name: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    path: str = ""
    weightage: float = 10
    remark: str = ""


class ExtractionControlItem(BaseModel):
    id: str
    name: str
    description: str = ""
    deployment_points: list[ExtractionDeploymentPoint] = Field(default_factory=list)


class ExtractionSection(BaseModel):
    id: str
    name: str
    controls: list[ExtractionControlItem] = Field(default_factory=list)


class ExtractionControls(BaseModel):
    total_controls: int = 0
    total_sections: int = 0
    controls_data: list[ExtractionSection] = Field(default_factory=list)


class ExtractionHistoryEntry(BaseModel):
    status: ExtractionStatus
    timestamp: datetime = Field(default_factory=_utcnow)
    message: str | None = None


class ExtractionStatusHistory(BaseModel):
    processingTimeSeconds: float | None = None
    completedAt: datetime | None = None
    history: list[ExtractionHistoryEntry] = Field(default_factory=list)


class AiExtractionInfo(BaseModel):
    status: ExtractionStatus = "pending"
    timestamp: datetime | None = None
    message: str | None = None
    statusHistory: list[ExtractionStatusHistory] | None = None
    controls: list[ExtractionControls] | None = None


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"
    __table_args__ = (Index("ix_doc_extractions_hash", "fileHash", unique=True),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    fileHash: Mapped[str] = mapped_column(String, nullable=False)
    aiExtraction: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
