"""Gap Analysis Configuration API — CRUD for thresholds and settings."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import GapThresholdConfig
from vora_shared.responses import error, not_found, server_error, success

logger = logging.getLogger(__name__)
router = APIRouter(tags=["config"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ThresholdsRequest(BaseModel):
    """Request model for updating thresholds."""

    implemented_threshold: float = 75.0
    partially_implemented_threshold: float = 50.0
    implemented_label: str = "Implemented"
    partially_implemented_label: str = "Partially Implemented"
    not_implemented_label: str = "Not Implemented"
    description: str | None = None


class ThresholdsResponse(BaseModel):
    """Response model for thresholds data."""

    id: str
    implemented_threshold: float
    partially_implemented_threshold: float
    not_implemented_threshold: float
    implemented_label: str
    partially_implemented_label: str
    not_implemented_label: str
    description: str | None = None
    is_active: bool
    createdAt: str | None = None
    updatedAt: str | None = None


# ---------------------------------------------------------------------------
# GET /config/thresholds — Get current active thresholds
# ---------------------------------------------------------------------------


@router.get("/thresholds")
async def get_thresholds():
    """Get current active gap analysis thresholds."""
    try:
        async with session_scope() as session:
            config = (
                await session.execute(select(GapThresholdConfig).where(GapThresholdConfig.is_active == True))
            ).scalar_one_or_none()

            if not config:
                # Return defaults if not configured
                return success(
                    message="Thresholds (using defaults)",
                    data={
                        "implemented_threshold": 75.0,
                        "partially_implemented_threshold": 50.0,
                        "not_implemented_threshold": 0.0,
                        "implemented_label": "Implemented",
                        "partially_implemented_label": "Partially Implemented",
                        "not_implemented_label": "Not Implemented",
                        "is_active": True,
                        "isDefault": True,
                    },
                )

            return success(
                message="Thresholds retrieved successfully",
                data={
                    "id": config.id,
                    "implemented_threshold": config.implemented_threshold,
                    "partially_implemented_threshold": config.partially_implemented_threshold,
                    "not_implemented_threshold": config.not_implemented_threshold,
                    "implemented_label": config.implemented_label,
                    "partially_implemented_label": config.partially_implemented_label,
                    "not_implemented_label": config.not_implemented_label,
                    "description": config.description,
                    "is_active": config.is_active,
                    "createdAt": config.createdAt.isoformat() if config.createdAt else None,
                    "updatedAt": config.updatedAt.isoformat() if config.updatedAt else None,
                    "isDefault": False,
                },
            )
    except Exception as exc:
        logger.exception("get_thresholds error")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# POST /config/thresholds — Create thresholds
# ---------------------------------------------------------------------------


@router.post("/thresholds")
async def create_thresholds(request: ThresholdsRequest):
    """Create gap analysis thresholds configuration."""
    try:
        async with session_scope() as session:
            # Deactivate any existing active config
            existing_active = (
                await session.execute(select(GapThresholdConfig).where(GapThresholdConfig.is_active == True))
            ).scalar_one_or_none()

            if existing_active:
                existing_active.is_active = False
                session.add(existing_active)

            config = GapThresholdConfig(
                id=new_id(),
                is_active=True,
                implemented_threshold=float(request.implemented_threshold),
                partially_implemented_threshold=float(request.partially_implemented_threshold),
                implemented_label=request.implemented_label,
                partially_implemented_label=request.partially_implemented_label,
                not_implemented_label=request.not_implemented_label,
                description=request.description,
            )
            session.add(config)
            await session.commit()

            logger.info(
                f"[CONFIG] Created thresholds: "
                f"high={request.implemented_threshold}, medium={request.partially_implemented_threshold}"
            )

            return success(
                message="Thresholds created successfully",
                data={
                    "id": config.id,
                    "implemented_threshold": config.implemented_threshold,
                    "partially_implemented_threshold": config.partially_implemented_threshold,
                    "not_implemented_threshold": config.not_implemented_threshold,
                    "implemented_label": config.implemented_label,
                    "partially_implemented_label": config.partially_implemented_label,
                    "not_implemented_label": config.not_implemented_label,
                    "description": config.description,
                    "is_active": config.is_active,
                    "createdAt": config.createdAt.isoformat(),
                },
                status_code=201,
            )
    except Exception as exc:
        logger.exception("create_thresholds error")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# PUT /config/thresholds/{config_id} — Update thresholds
# ---------------------------------------------------------------------------


@router.put("/thresholds/{config_id}")
async def update_thresholds(config_id: str, request: ThresholdsRequest):
    """Update gap analysis thresholds configuration."""
    try:
        async with session_scope() as session:
            config = await session.get(GapThresholdConfig, config_id)

            if not config:
                return not_found("Thresholds configuration not found.")

            old_high = config.implemented_threshold
            old_medium = config.partially_implemented_threshold

            config.implemented_threshold = float(request.implemented_threshold)
            config.partially_implemented_threshold = float(request.partially_implemented_threshold)
            config.implemented_label = request.implemented_label
            config.partially_implemented_label = request.partially_implemented_label
            config.not_implemented_label = request.not_implemented_label
            config.description = request.description
            config.updatedAt = _utcnow()
            session.add(config)
            await session.commit()

            logger.info(
                f"[CONFIG] Updated thresholds: "
                f"high={old_high}→{request.implemented_threshold}, "
                f"medium={old_medium}→{request.partially_implemented_threshold}"
            )

            return success(
                message="Thresholds updated successfully",
                data={
                    "id": config.id,
                    "implemented_threshold": config.implemented_threshold,
                    "partially_implemented_threshold": config.partially_implemented_threshold,
                    "not_implemented_threshold": config.not_implemented_threshold,
                    "implemented_label": config.implemented_label,
                    "partially_implemented_label": config.partially_implemented_label,
                    "not_implemented_label": config.not_implemented_label,
                    "description": config.description,
                    "is_active": config.is_active,
                    "updatedAt": config.updatedAt.isoformat(),
                },
            )
    except Exception as exc:
        logger.exception("update_thresholds error")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# DELETE /config/thresholds/{config_id} — Delete thresholds config
# ---------------------------------------------------------------------------


@router.delete("/thresholds/{config_id}")
async def delete_thresholds(config_id: str):
    """Delete thresholds configuration."""
    try:
        async with session_scope() as session:
            config = await session.get(GapThresholdConfig, config_id)

            if not config:
                return error("Thresholds configuration not found.")

            await session.delete(config)
            await session.commit()

            logger.info(f"[CONFIG] Deleted thresholds config: {config_id}")

            return success(message="Thresholds configuration deleted successfully")
    except Exception as exc:
        logger.exception("delete_thresholds error")
        return server_error(str(exc))


# ---------------------------------------------------------------------------
# GET /config/thresholds/list/all — List all threshold configs
# ---------------------------------------------------------------------------


@router.get("/thresholds/list/all")
async def list_thresholds():
    """List all threshold configurations."""
    try:
        async with session_scope() as session:
            configs = (
                (
                    await session.execute(
                        select(GapThresholdConfig).order_by(GapThresholdConfig.createdAt.desc())
                    )
                )
                .scalars()
                .all()
            )

            items = []
            for config in configs:
                items.append(
                    {
                        "id": config.id,
                        "implemented_threshold": config.implemented_threshold,
                        "partially_implemented_threshold": config.partially_implemented_threshold,
                        "not_implemented_threshold": config.not_implemented_threshold,
                        "implemented_label": config.implemented_label,
                        "partially_implemented_label": config.partially_implemented_label,
                        "not_implemented_label": config.not_implemented_label,
                        "description": config.description,
                        "is_active": config.is_active,
                        "createdAt": config.createdAt.isoformat() if config.createdAt else None,
                        "updatedAt": config.updatedAt.isoformat() if config.updatedAt else None,
                    }
                )

            return success(
                message=f"Retrieved {len(items)} threshold configurations",
                data=items,
            )
    except Exception as exc:
        logger.exception("list_thresholds error")
        return server_error(str(exc))
