"""WebSocket connection manager for real-time extraction status updates."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time status updates (async-safe)."""

    def __init__(self) -> None:
        self.active_connections: dict[str, set[WebSocket]] = {}
        self.connection_lock = asyncio.Lock()
        self.pending_messages: dict[str, list[dict[str, Any]]] = {}

    async def connect(self, identifier: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.connection_lock:
            if identifier not in self.active_connections:
                self.active_connections[identifier] = set()
            self.active_connections[identifier].add(websocket)

            if identifier in self.pending_messages:
                for msg in self.pending_messages[identifier]:
                    try:
                        await websocket.send_json(msg)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Could not send pending message: %s", exc)
                del self.pending_messages[identifier]

        conn_count = len(self.active_connections.get(identifier, set()))
        logger.info(
            "WebSocket connected | identifier=%s | active=%s", identifier, conn_count
        )

    async def disconnect(self, identifier: str, websocket: WebSocket) -> None:
        async with self.connection_lock:
            if identifier in self.active_connections:
                self.active_connections[identifier].discard(websocket)
        logger.info("WebSocket disconnected | identifier=%s", identifier)

    async def send_json(self, identifier: str, message: dict[str, Any]) -> None:
        """Alias used by runners / routers."""
        await self.send_update(identifier, message)

    async def send_update(self, identifier: str, message: dict[str, Any]) -> None:
        async with self.connection_lock:
            connections = self.active_connections.get(identifier)
            if connections:
                disconnected: set[WebSocket] = set()
                event_type = message.get("event", "unknown")
                logger.info(
                    "Sending %s to %s connection(s) | identifier=%s",
                    event_type,
                    len(connections),
                    identifier,
                )
                for connection in list(connections):
                    try:
                        await connection.send_json(message)
                    except Exception as exc:  # noqa: BLE001
                        logger.error("Failed to send WS message: %s", exc)
                        disconnected.add(connection)
                for conn in disconnected:
                    connections.discard(conn)
            else:
                if identifier not in self.pending_messages:
                    self.pending_messages[identifier] = []
                self.pending_messages[identifier].append(message)
                logger.warning(
                    "Queued message (no active connections) | identifier=%s | event=%s",
                    identifier,
                    message.get("event", "unknown"),
                )

    async def push_to_framework_ws(self, ref_id: str, message: dict[str, Any]) -> int:
        prefix = f"framework:{ref_id}:"
        async with self.connection_lock:
            matched_keys = [k for k in self.active_connections if k.startswith(prefix)]
        sent = 0
        for key in matched_keys:
            try:
                await asyncio.wait_for(self.send_update(key, message), timeout=5.0)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("Error pushing to %s: %s", key, exc)
        return sent

    async def push_to_deployment_framework_ws(
        self, ref_id: str, message: dict[str, Any], file_id: str | None = None
    ) -> int:
        prefix = f"deployment-framework:{ref_id}:"
        if file_id:
            file_id = str(file_id).strip()
        async with self.connection_lock:
            matched_keys: list[str] = []
            for key in list(self.active_connections.keys()):
                if not key.startswith(prefix):
                    continue
                if file_id:
                    if key.endswith(f":{file_id}"):
                        matched_keys.append(key)
                else:
                    matched_keys.append(key)
        sent = 0
        for key in matched_keys:
            try:
                await asyncio.wait_for(self.send_update(key, message), timeout=5.0)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("Error pushing to %s: %s", key, exc)
        return sent


manager = ConnectionManager()
