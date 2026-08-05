"""WebSocket connection manager for gap analysis progress."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
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

    async def disconnect(self, identifier: str, websocket: WebSocket) -> None:
        async with self.connection_lock:
            if identifier in self.active_connections:
                self.active_connections[identifier].discard(websocket)

    async def send_json(self, identifier: str, message: dict[str, Any]) -> None:
        await self.send_update(identifier, message)

    async def send_update(self, identifier: str, message: dict[str, Any]) -> None:
        async with self.connection_lock:
            connections = self.active_connections.get(identifier)
            if connections:
                disconnected: set[WebSocket] = set()
                for connection in list(connections):
                    try:
                        await connection.send_json(message)
                    except Exception as exc:  # noqa: BLE001
                        logger.error("Failed to send WS message: %s", exc)
                        disconnected.add(connection)
                for conn in disconnected:
                    connections.discard(conn)
            else:
                self.pending_messages.setdefault(identifier, []).append(message)


manager = ConnectionManager()
