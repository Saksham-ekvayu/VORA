"""Port of deployment-framework-service-main/src/services/ai-websocket.service.js.

Uses the `websockets` library and asyncio instead of Node's `ws` + callbacks.
Connections are tracked so duplicate extraction requests for the same
framework/package/file are ignored, mirroring the Node service.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import websockets
from sqlalchemy import select

from app.helpers.deployment_framework_helpers import coerce_packages, dump_packages
from vora_shared.database import session_scope
from vora_shared.models.document_extraction import AiExtractionInfo, ExtractionHistoryEntry, ExtractionStatusHistory

logger = logging.getLogger("ai_websocket")

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

_connections: dict[str, asyncio.Task] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ws_base_url() -> str:
    return os.environ.get("AI_WEBSOCKET_URL", "ws://192.168.1.30:7000")


async def _resolve_extraction_record(framework_id: str, package_version: str, file_id: str):
    from vora_shared.models import DeploymentFramework, DocumentExtraction

    async with session_scope() as session:
        framework = await session.get(DeploymentFramework, str(framework_id))
        if not framework:
            return None
        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == package_version), None)
        if not found_package:
            return None
        found_doc = next((d for d in found_package.documents if str(d.fileId) == str(file_id)), None)
        if not found_doc:
            return None

        if found_doc.aiExtraction:
            extraction = await session.get(DocumentExtraction, str(found_doc.aiExtraction))
            if extraction:
                return extraction

        extraction = (
            await session.execute(
                select(DocumentExtraction).where(DocumentExtraction.fileHash == found_doc.fileHash)
            )
        ).scalar_one_or_none()
        if not extraction:
            extraction = DocumentExtraction(fileHash=found_doc.fileHash, aiExtraction={})
            session.add(extraction)
            await session.flush()

        found_doc.aiExtraction = extraction.id
        framework.packages = dump_packages(packages)
        return extraction


async def _mark_timed_out(framework_id: str, package_version: str, file_id: str) -> None:
    try:
        extraction = await _resolve_extraction_record(framework_id, package_version, file_id)
        if not extraction:
            return
        async with session_scope() as session:
            row = await session.get(type(extraction), extraction.id)
            if not row:
                return
            ai = AiExtractionInfo.model_validate(row.aiExtraction or {})
            ai.status = "failed"
            ai.timestamp = _utcnow()
            ai.message = "AI took more time to extract. Please try again after some time."
            row.aiExtraction = ai.model_dump(mode="json")
    except Exception as exc:
        logger.error("Failed to update timeout status in DB: %s", exc)


async def _on_status_update(framework_id: str, package_version: str, file_id: str, payload: dict) -> None:
    try:
        extraction = await _resolve_extraction_record(framework_id, package_version, file_id)
        if not extraction:
            return
        async with session_scope() as session:
            row = await session.get(type(extraction), extraction.id)
            if not row:
                return
            ai = AiExtractionInfo.model_validate(row.aiExtraction or {})
            ai.status = STATUS_MAP.get(payload.get("status"), payload.get("status"))  # type: ignore[assignment]
            ai.timestamp = _parse_ts(payload.get("timestamp"))
            ai.message = payload.get("message")
            row.aiExtraction = ai.model_dump(mode="json")
    except Exception as exc:
        logger.error("Failed to update status on WebSocket event: %s", exc)


def _parse_ts(ts) -> datetime:
    if not ts:
        return _utcnow()
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return _utcnow()


async def _on_extraction_completed(
    framework_id: str, package_version: str, file_id: str, payload: dict
) -> None:
    try:
        extraction = await _resolve_extraction_record(framework_id, package_version, file_id)
        if not extraction:
            return

        status_history_payload = payload.get("status_history") or {}
        history_entries = [
            ExtractionHistoryEntry(
                status=STATUS_MAP.get(h.get("status"), h.get("status")),  # type: ignore[arg-type]
                timestamp=_parse_ts(h.get("timestamp")),
                message=h.get("message"),
            )
            for h in status_history_payload.get("history", [])
        ]
        status_history = ExtractionStatusHistory(
            processingTimeSeconds=status_history_payload.get("processing_time_seconds"),
            completedAt=_parse_ts(status_history_payload.get("completed_at")),
            history=history_entries,
        )

        async with session_scope() as session:
            row = await session.get(type(extraction), extraction.id)
            if not row:
                return
            ai = AiExtractionInfo.model_validate(row.aiExtraction or {})
            ai.status = "extracted"
            ai.timestamp = _parse_ts(payload.get("timestamp"))
            ai.message = payload.get("message")
            ai.statusHistory = [status_history]
            ai.controls = payload.get("controls")
            row.aiExtraction = ai.model_dump(mode="json")
    except Exception as exc:
        logger.error("Failed to save extraction data on completion: %s", exc)


async def _on_extraction_failed(
    framework_id: str, package_version: str, file_id: str, payload: dict
) -> None:
    try:
        extraction = await _resolve_extraction_record(framework_id, package_version, file_id)
        if not extraction:
            return
        async with session_scope() as session:
            row = await session.get(type(extraction), extraction.id)
            if not row:
                return
            ai = AiExtractionInfo.model_validate(row.aiExtraction or {})
            ai.status = "failed"
            ai.timestamp = _parse_ts(payload.get("timestamp"))
            ai.message = payload.get("message")
            row.aiExtraction = ai.model_dump(mode="json")
    except Exception as exc:
        logger.error("Failed to save failure state on WebSocket event: %s", exc)


async def _handle_message(raw: str, framework_id: str, package_version: str, file_id: str) -> None:
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("Received non-JSON WebSocket message: %s", raw)
        return

    event = parsed.get("event")
    payload = parsed.get("data")
    if not event or not payload:
        return

    if event in (WS_EVENTS["EXTRACTION_UPLOADED"], WS_EVENTS["EXTRACTION_PROCESSING"]):
        await _on_status_update(framework_id, package_version, file_id, payload)
    elif event == WS_EVENTS["EXTRACTION_COMPLETED"]:
        await _on_extraction_completed(framework_id, package_version, file_id, payload)
    elif event == WS_EVENTS["EXTRACTION_FAILED"]:
        await _on_extraction_failed(framework_id, package_version, file_id, payload)


async def _run_extraction(framework_id: str, package_version: str, file_id: str) -> None:
    connection_key = f"{framework_id}:{package_version}:{file_id}"
    url = f"{_ws_base_url()}/api/extract/ws/deployment-framework/{framework_id}/packageVersion/{package_version}/fileid/{file_id}"

    try:
        async with websockets.connect(url, open_timeout=10) as ws:
            logger.info("Connected to AI WebSocket service")
            try:
                async with asyncio.timeout(EXTRACTION_TIMEOUT_SECONDS):
                    async for raw in ws:
                        await _handle_message(raw, framework_id, package_version, file_id)
            except TimeoutError:
                logger.info("Extraction timeout (5 minutes) reached for connection: %s", connection_key)
                await _mark_timed_out(framework_id, package_version, file_id)
    except Exception as exc:
        logger.error("AI WebSocket connection error: %s", exc)
    finally:
        _connections.pop(connection_key, None)
        try:
            extraction = await _resolve_extraction_record(framework_id, package_version, file_id)
            if extraction:
                ai = AiExtractionInfo.model_validate(extraction.aiExtraction or {})
                if ai.status not in ("extracted", "failed"):
                    async with session_scope() as session:
                        row = await session.get(type(extraction), extraction.id)
                        if row:
                            ai = AiExtractionInfo.model_validate(row.aiExtraction or {})
                            ai.status = "failed"
                            ai.timestamp = _utcnow()
                            ai.message = "WebSocket disconnected unexpectedly"
                            row.aiExtraction = ai.model_dump(mode="json")
        except Exception as exc:
            logger.error("Error updating failed status on close: %s", exc)


async def start_extraction(framework_id: str, package_version: str, file_id: str) -> None:
    connection_key = f"{framework_id}:{package_version}:{file_id}"
    if connection_key in _connections:
        return
    task = asyncio.create_task(_run_extraction(framework_id, package_version, file_id))
    _connections[connection_key] = task
