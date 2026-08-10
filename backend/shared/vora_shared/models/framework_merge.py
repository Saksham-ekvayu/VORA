"""`framework_merges` table — stores merged controls for a framework.

When multiple files are merged, the canonical merged controls are stored here.
Each framework can have multiple merges (one per unique set of file combinations).
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


class FrameworkMerge(Base):
    """Stores merged controls for a framework (canonical)."""

    __tablename__ = "framework_merges"
    __table_args__ = (
        Index(
            "ix_framework_merges_fw_merge_key",
            "frameworkId",
            "mergeKey",
            unique=True,
        ),
        Index("ix_framework_merges_framework", "frameworkId"),
        Index("ix_framework_merges_created", "createdAt"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    frameworkId: Mapped[str] = mapped_column(String(24), nullable=False)
    mergeKey: Mapped[str] = mapped_column(String(256), nullable=False)
    mergeHashes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    fileVersions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    controls: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
