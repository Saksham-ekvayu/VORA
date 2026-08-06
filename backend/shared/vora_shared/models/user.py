"""`users` table — owning services: authentication + profile."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, false, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from vora_shared.database import Base
from vora_shared.ids import new_id
from vora_shared.models.customer import AddressBlock


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserAddress(BaseModel):
    permanentAddress: AddressBlock = Field(default_factory=AddressBlock)
    temporaryAddress: AddressBlock = Field(default_factory=AddressBlock)


class UserOtp(BaseModel):
    code: str | None = None
    expiresAt: datetime | None = None
    purpose: str | None = None


class UserCreatedBy(BaseModel):
    type: Literal["self", "admin", "customer-admin"] = "self"
    userId: str | None = None


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_tenant_email", "tenantId", "email", unique=True),
        Index("ix_users_email", "email", unique=True),
        Index("ix_users_tenant_phone", "tenantId", "phone"),
        Index("ix_users_tenant_role", "tenantId", "role"),
        Index("ix_users_tenant_active", "tenantId", "isActive"),
        Index("ix_users_tenant_created", "tenantId", "createdAt"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=new_id)
    tenantId: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    secondaryPhone: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    designation: Mapped[str | None] = mapped_column(String, nullable=True)
    password: Mapped[str] = mapped_column(String, nullable=False, default="")
    isEmailVerified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    isActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    otp: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tokenVersion: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    address: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdBy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "_id": self.id,
            "tenantId": self.tenantId,
            "avatar": self.avatar,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "secondaryPhone": self.secondaryPhone,
            "role": self.role,
            "designation": self.designation,
            "isEmailVerified": self.isEmailVerified,
            "isActive": self.isActive,
            "otp": self.otp,
            "tokenVersion": self.tokenVersion,
            "address": self.address,
            "createdBy": self.createdBy,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }
