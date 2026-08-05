"""Port of ai-websocket.service.js.

Manages per-framework WebSocket connections to the AI extraction service.
Each call to `start_extraction` opens a dedicated WS connection for one
framework file, listens for extraction events, persists results to Postgres,
and closes the socket when done (or after a 5 minute timeout).

WS URL pattern: ws://<host>/api/extract/ws/framework/<frameworkId>/fileid/<fileId>
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import websockets
from websockets.exceptions import ConnectionClosed

from vora_shared.config import get_settings
from vora_shared.database import session_scope
from vora_shared.models.framework import (
    AiExtraction,
    Controls,
    Framework,
    StatusHistory,
    StatusHistoryEntry,
)

WS_EVENTS = {
    "EXTRACTION_UPLOADED": "extraction_uploaded",
    "EXTRACTION_PROCESSING": "extraction_processing",
    "EXTRACTION_COMPLETED": "extraction_completed",
    "EXTRACTION_FAILED": "extraction_failed",
}

STATUS_MAP = {
    "uploaded": "uploaded",
    "processing": "processing",
    "completed": "extracted",
    "failed": "failed",
}

EXTRACTION_TIMEOUT_SECONDS = 5 * 60

AI_EXTRACTION_TIMEOUT_MESSAGE = (
    "Framework extraction is taking longer than expected. "
    "Please try re-uploading the framework."
)
AI_EXTRACTION_CONNECTION_FAILED_MESSAGE = (
    "Unable to reach the AI extraction service. Please try again later."
)
AI_EXTRACTION_UNEXPECTED_DISCONNECT_MESSAGE = (
    "The connection to the AI extraction service was lost unexpectedly. "
    "Please try re-uploading the framework."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return _now()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return _now()


def _find_fv_index(file_versions: list, file_id: str) -> int | None:
    for i, fv in enumerate(file_versions or []):
        fv_id = fv.get("fileId") if isinstance(fv, dict) else getattr(fv, "fileId", None)
        if str(fv_id) == str(file_id):
            return i
    return None


def _ensure_ai_extraction(fv: dict) -> dict:
    ai = fv.get("aiExtraction")
    if not isinstance(ai, dict):
        ai = AiExtraction().model_dump(mode="json")
        fv["aiExtraction"] = ai
    return ai


class AiWebSocketService:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}

    def _key(self, framework_id: str, file_id: str) -> str:
        return f"{framework_id}:{file_id}"

    async def start_extraction(self, framework_id: str, file_id: str) -> None:
        settings = get_settings()
        base_url = settings.ai_websocket_url
        if not base_url:
            raise RuntimeError("AI_WEBSOCKET_URL is not set in environment")

        key = self._key(framework_id, file_id)
        if key in self._tasks and not self._tasks[key].done():
            return

        task = asyncio.create_task(self._run(base_url, framework_id, file_id, key))
        self._tasks[key] = task

    def close_extraction(self, framework_id: str, file_id: str) -> None:
        key = self._key(framework_id, file_id)
        task = self._tasks.pop(key, None)
        if task and not task.done():
            task.cancel()

    def close_all(self) -> None:
        for key, task in list(self._tasks.items()):
            if not task.done():
                task.cancel()
            self._tasks.pop(key, None)
        print("🔌 [AI WS] Disconnected manually")

    async def _run(self, base_url: str, framework_id: str, file_id: str, key: str) -> None:
        url = f"{base_url}/api/extract/ws/framework/{framework_id}/fileid/{file_id}"
        print(f"🔌 [AI WS] Connecting to {url}...")

        extraction_settled = False
        close_code: int | None = None
        try:
            async with websockets.connect(url, open_timeout=10) as ws:
                print("✅ [AI WS] Connected")
                try:
                    async with asyncio.timeout(EXTRACTION_TIMEOUT_SECONDS):
                        async for raw_message in ws:
                            settled = await self._handle_message(
                                raw_message, framework_id, file_id
                            )
                            if settled:
                                extraction_settled = True
                                break
                except TimeoutError:
                    print(
                        f"Extraction timeout (5 minutes) reached for connection: {key}"
                    )
                    await self._mark_failed(
                        framework_id, file_id, AI_EXTRACTION_TIMEOUT_MESSAGE
                    )
                    extraction_settled = True
        except ConnectionClosed as exc:
            close_code = exc.rcvd.code if exc.rcvd else None
        except (OSError, asyncio.TimeoutError) as exc:
            print(f"❌ [AI WS] Connection error: {exc}")
        finally:
            self._tasks.pop(key, None)
            print(f"⚠️ [AI WS] Disconnected (code={close_code}, reason=none)")
            if not extraction_settled:
                error_message = (
                    AI_EXTRACTION_CONNECTION_FAILED_MESSAGE
                    if close_code == 1006 or close_code is None
                    else AI_EXTRACTION_UNEXPECTED_DISCONNECT_MESSAGE
                )
                print(
                    f"[AI WS] Unexpected close for {key} — marking extraction as failed. {error_message}"
                )
                await self._mark_failed(framework_id, file_id, error_message)

    async def _update_file_version_ai(
        self, framework_id: str, file_id: str, updater
    ) -> bool:
        async with session_scope() as session:
            framework = await session.get(Framework, str(framework_id))
            if not framework:
                return False
            versions = list(framework.fileVersions or [])
            idx = _find_fv_index(versions, file_id)
            if idx is None:
                return False
            fv = dict(versions[idx]) if not isinstance(versions[idx], dict) else dict(versions[idx])
            updater(fv)
            versions[idx] = fv
            framework.fileVersions = versions
            return True

    async def _mark_failed(self, framework_id: str, file_id: str, message: str) -> None:
        try:
            def _apply(fv: dict) -> None:
                ai = _ensure_ai_extraction(fv)
                ai["status"] = "failed"
                ai["timestamp"] = _now().isoformat()
                ai["message"] = message

            await self._update_file_version_ai(framework_id, file_id, _apply)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to update timeout status in DB: {exc}")

    async def _handle_message(self, data, framework_id: str, file_id: str) -> bool:
        try:
            parsed = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            print(f"[AI WS] Received non-JSON message: {data}")
            return False

        event = parsed.get("event")
        payload = parsed.get("data")
        if not event or not payload:
            return False

        if event in (
            WS_EVENTS["EXTRACTION_UPLOADED"],
            WS_EVENTS["EXTRACTION_PROCESSING"],
        ):
            await self._on_status_update(framework_id, file_id, payload)
            return False

        if event == WS_EVENTS["EXTRACTION_COMPLETED"]:
            await self._on_extraction_completed(framework_id, file_id, payload)
            return True

        if event == WS_EVENTS["EXTRACTION_FAILED"]:
            await self._on_extraction_failed(framework_id, file_id, payload)
            return True

        return False

    async def _on_status_update(self, framework_id: str, file_id: str, payload: dict) -> None:
        try:
            db_status = STATUS_MAP.get(payload.get("status"), payload.get("status"))

            def _apply(fv: dict) -> None:
                ai = _ensure_ai_extraction(fv)
                ai["status"] = db_status
                ai["timestamp"] = _parse_dt(payload.get("timestamp")).isoformat()
                ai["message"] = payload.get("message")

            ok = await self._update_file_version_ai(framework_id, file_id, _apply)
            if ok:
                print(
                    f"✅ [AI WS] Status : {db_status} for framework {framework_id}, version {file_id}"
                )
        except Exception as exc:  # noqa: BLE001
            print(f"❌ [AI WS] Error updating status: {exc}")

    async def _on_extraction_completed(
        self, framework_id: str, file_id: str, payload: dict
    ) -> None:
        try:
            raw_history = (payload.get("status_history") or {}).get("history") or []
            history_entries = [
                StatusHistoryEntry(
                    status=STATUS_MAP.get(h.get("status"), h.get("status")),
                    timestamp=_parse_dt(h.get("timestamp")),
                    message=h.get("message"),
                )
                for h in raw_history
            ]

            status_history_payload = payload.get("status_history") or {}
            status_history = StatusHistory(
                processingTimeSeconds=status_history_payload.get(
                    "processing_time_seconds"
                ),
                completedAt=_parse_dt(status_history_payload.get("completed_at")),
                history=history_entries,
            )

            controls_payload = payload.get("controls")
            controls = Controls(**controls_payload) if controls_payload else None

            extraction = AiExtraction(
                status="extracted",
                timestamp=_parse_dt(payload.get("timestamp")),
                message=payload.get("message"),
                statusHistory=status_history,
                controls=controls,
            )

            def _apply(fv: dict) -> None:
                fv["aiExtraction"] = extraction.model_dump(mode="json")

            ok = await self._update_file_version_ai(framework_id, file_id, _apply)
            if ok:
                db_status = STATUS_MAP.get(payload.get("status"), payload.get("status"))
                print(
                    f"✅ [AI WS] Status : {db_status} for framework {framework_id}, version {file_id}"
                )
        except Exception as exc:  # noqa: BLE001
            print(f"❌ [AI WS] Error saving extraction results: {exc}")

    async def _on_extraction_failed(
        self, framework_id: str, file_id: str, payload: dict
    ) -> None:
        try:
            def _apply(fv: dict) -> None:
                ai = _ensure_ai_extraction(fv)
                ai["status"] = "failed"
                ai["timestamp"] = _parse_dt(payload.get("timestamp")).isoformat()
                ai["message"] = payload.get("message")

            ok = await self._update_file_version_ai(framework_id, file_id, _apply)
            if ok:
                db_status = STATUS_MAP.get(payload.get("status"), payload.get("status"))
                print(
                    f"❌ [AI WS] Status : {db_status} for framework {framework_id}, "
                    f"version {file_id}, error {payload.get('message', 'unknown')}"
                )
        except Exception as exc:  # noqa: BLE001
            print(f"❌ [AI WS] Error saving extraction error: {exc}")


ai_websocket_service = AiWebSocketService()
