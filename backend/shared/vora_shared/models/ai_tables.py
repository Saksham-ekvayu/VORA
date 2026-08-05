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


class ExtractionResult(Base):
    __tablename__ = "extraction_results"
    __table_args__ = (
        Index("ix_extraction_results_ref", "ref_id"),
        Index("ix_extraction_results_resource", "resource_type", "ref_id"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    ref_id: Mapped[str] = mapped_column(String(24), nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    package_version: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ExtractionHashRegistry(Base):
    __tablename__ = "extraction_hash_registry"
    __table_args__ = (Index("ix_extraction_hash", "file_hash", unique=True),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    file_hash: Mapped[str] = mapped_column(String, nullable=False)
    extraction_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class MergeHashRegistry(Base):
    __tablename__ = "merge_hash_registry"
    __table_args__ = (Index("ix_merge_hash", "hash_key", unique=True),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    hash_key: Mapped[str] = mapped_column(String, nullable=False)
    merge_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


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
    __table_args__ = (
        Index("ix_comparison_jobs_df", "deployment_framework_id", "package_version"),
    )

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
    __table_args__ = (
        Index("ix_comparison_results_df", "deployment_framework_id", "package_version"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    deployment_framework_id: Mapped[str] = mapped_column(String(24), nullable=False)
    package_version: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class DeploymentGapJob(Base):
    __tablename__ = "deployment_gap_jobs"
    __table_args__ = (
        Index("ix_gap_jobs_df", "deployment_framework_id", "package_version"),
    )

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


class AgentMapping(Base):
    __tablename__ = "agent_mappings"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AgentControl(Base):
    __tablename__ = "agent_controls"
    __table_args__ = (Index("ix_agent_controls_control", "control_id"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    control_id: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
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


class LoadDocument(Base):
    """Generic documents uploaded via load-document-service."""

    __tablename__ = "load_documents"
    __table_args__ = (Index("ix_load_documents_tenant", "tenant_id"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    tenant_id: Mapped[str | None] = mapped_column(String, nullable=True)
    document_name: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False, default="document")
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
