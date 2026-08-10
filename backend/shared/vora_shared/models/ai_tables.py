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


class PackageMergeTracking(Base):
    __tablename__ = "package_merge_tracking"
    __table_args__ = (
        Index(
            "ix_pkg_merge_track_df_ver",
            "deployment_framework_id",
            "package_version",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    deployment_framework_id: Mapped[str] = mapped_column(String(24), nullable=False)
    package_version: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ComparisonJob(Base):
    __tablename__ = "comparison_jobs"
    __table_args__ = (Index("ix_comparison_jobs_df", "deployment_framework_id", "package_version"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    deployment_framework_id: Mapped[str] = mapped_column(String(24), nullable=False)
    package_version: Mapped[str] = mapped_column(String, nullable=False)
    framework_assignment_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ComparisonResult(Base):
    __tablename__ = "comparison_results"
    __table_args__ = (Index("ix_comparison_results_df", "deployment_framework_id", "package_version"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    deployment_framework_id: Mapped[str] = mapped_column(String(24), nullable=False)
    package_version: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class DeploymentGapJob(Base):
    __tablename__ = "deployment_gap_jobs"
    __table_args__ = (Index("ix_gap_jobs_df", "deployment_framework_id", "package_version"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    deployment_framework_id: Mapped[str] = mapped_column(String(24), nullable=False)
    package_version: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class DeploymentGapResult(Base):
    __tablename__ = "deployment_gap_results"
    __table_args__ = (Index("ix_gap_results_df", "deployment_framework_id", "package_version"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    deployment_framework_id: Mapped[str] = mapped_column(String(24), nullable=False)
    package_version: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class GapConfig(Base):
    """Tunable gap analysis config (implementation status / thresholds)."""

    __tablename__ = "gap_config"
    __table_args__ = (Index("ix_gap_config_key", "config_key", unique=True),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    config_key: Mapped[str] = mapped_column(String, nullable=False)
    config_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


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
