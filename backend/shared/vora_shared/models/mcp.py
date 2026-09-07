from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from vora_shared.database import Base


# =========================================
# PROCESSED FILES TABLE
# =========================================
class ProcessedFile(Base):
    __tablename__ = "processed_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(  # type: ignore[type-arg]
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# =========================================
# SOURCE CONFIG TABLE
# =========================================
class SourceConfig(Base):
    __tablename__ = "source_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    control_name: Mapped[str] = mapped_column(String, nullable=False)
    dp_name: Mapped[str] = mapped_column(String, nullable=False)
    organization_name: Mapped[str] = mapped_column(String, nullable=False)

    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String, nullable=True)

    is_active: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[DateTime] = mapped_column(  # type: ignore[type-arg]
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    credentials: Mapped[list["SourceCredential"]] = relationship(
        back_populates="source_config",
        cascade="all, delete-orphan",
    )


# =========================================
# SOURCE CREDENTIALS TABLE
# =========================================
class SourceCredential(Base):
    __tablename__ = "source_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    source_config_id: Mapped[int] = mapped_column(
        ForeignKey("source_configs.id"),
        nullable=False,
    )

    config_json: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(  # type: ignore[type-arg]
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source_config: Mapped["SourceConfig"] = relationship(back_populates="credentials")
