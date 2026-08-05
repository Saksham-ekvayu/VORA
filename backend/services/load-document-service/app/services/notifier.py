"""Fire-and-forget HTTP notify to compliance-agent-service (replaces RabbitMQ)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from vora_shared.config import get_settings

logger = logging.getLogger(__name__)


async def _post_ingest(url: str, payload: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            logger.info(
                "compliance-agent ingest notify | status=%s | url=%s",
                response.status_code,
                url,
            )
    except Exception as exc:
        logger.warning("compliance-agent ingest notify failed | error=%s", exc)


def notify_compliance_agent(payload: dict[str, Any]) -> None:
    """Schedule a non-blocking POST to compliance-agent /api/compliance-agent/ingest."""
    settings = get_settings()
    base = (settings.compliance_agent_url or "").rstrip("/")
    if not base:
        logger.warning("compliance_agent_url not configured; skip notify")
        return
    url = f"{base}/api/compliance-agent/ingest"
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_post_ingest(url, payload))
    except RuntimeError:
        asyncio.run(_post_ingest(url, payload))
