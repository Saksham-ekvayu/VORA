"""`deployment_package_merges` table — tracks package-level merge operations.

When multiple files are extracted for a deployment framework package,
this table tracks the merge operation and final merged controls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from vora_shared.database import Base
from vora_shared.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeploymentPackageMerge(Base):
    """Tracks deployment package merge operations."""

    __tablename__ = "deployment_package_merges"
    __table_args__ = (
        Index(
            "ix_deployment_package_merge_df_pkg",
            "deploymentFrameworkId",
            "packageVersion",
            unique=True,
        ),
        Index("ix_deployment_package_merge_created", "createdAt"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    deploymentFrameworkId: Mapped[str] = mapped_column(String(24), nullable=False)
    packageVersion: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    mergeKey: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fileHashes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    fileIds: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    mergeHistory: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    controls: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
