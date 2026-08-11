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
        Index("ix_deployment_package_merge_created", "createdAt"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    fileHashes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    controls: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
