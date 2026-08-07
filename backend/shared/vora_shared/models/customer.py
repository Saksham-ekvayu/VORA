"""`customers` table — owning service: profile-service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Index, String, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from vora_shared.database import Base
from vora_shared.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AddressBlock(BaseModel):
    country: str | None = None
    state: str | None = None
    city: str | None = None
    locality: str | None = None


class CustomerAddress(BaseModel):
    permanentAddress: AddressBlock = Field(default_factory=AddressBlock)
    temporaryAddress: AddressBlock = Field(default_factory=AddressBlock)


class CustomerCreatedBy(BaseModel):
    type: str = "admin"
    userId: str | None = None


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_tenant", "tenantId", unique=True),
        Index("ix_customers_email", "email", unique=True),
        Index("ix_customers_active", "isActive"),
        Index("ix_customers_created", "createdAt"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    tenantId: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    secondaryPhone: Mapped[str | None] = mapped_column(String, nullable=True)
    isActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    avatar: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdBy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
