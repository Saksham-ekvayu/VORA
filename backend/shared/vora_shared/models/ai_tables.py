"""AI pipeline tables (formerly per-service Mongo collections in Shaili)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from vora_shared.database import Base
from vora_shared.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentPrompt(Base):
    __tablename__ = "agent_prompts"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class EvidenceOutput(Base):
    __tablename__ = "evidence_output"
    __table_args__ = (Index("ix_evidence_control", "control_id"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    control_id: Mapped[str | None] = mapped_column(String, nullable=True)
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    __table_args__ = (Index("ix_uploaded_files_ref", "ref_id"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    ref_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    s3_url: Mapped[str | None] = mapped_column(String, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
