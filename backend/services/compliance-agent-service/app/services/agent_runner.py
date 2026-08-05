"""Async ingest processing stub (OCR/LLM simplified from Shaili ai-agent1)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import EvidenceOutput, UploadedFile

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def process_ingest(payload: dict[str, Any]) -> None:
    """Mark uploaded file processed and write a placeholder EvidenceOutput row."""
    file_id = payload.get("file_id") or payload.get("uploaded_file_id")
    filename = payload.get("filename") or "unknown"
    control_id = payload.get("control_id") or payload.get("agent_name") or "placeholder"
    document_uuid = payload.get("id") or payload.get("document_uuid") or file_id

    logger.info(
        "process_ingest start | file_id=%s | filename=%s | control_id=%s",
        file_id,
        filename,
        control_id,
    )

    try:
        async with session_scope() as session:
            uploaded: UploadedFile | None = None
            if file_id:
                uploaded = await session.get(UploadedFile, str(file_id))
            if uploaded is None and document_uuid:
                uploaded = (
                    await session.execute(
                        select(UploadedFile)
                        .where(UploadedFile.ref_id == str(document_uuid))
                        .limit(1)
                    )
                ).scalar_one_or_none()

            meta = dict((uploaded.meta if uploaded else None) or {})
            meta.update(
                {
                    "status": "processed",
                    "processed_at": _utcnow_iso(),
                    "agent_name": control_id,
                }
            )
            if uploaded:
                uploaded.meta = meta
                flag_modified(uploaded, "meta")
                file_id = uploaded.id
                filename = uploaded.filename or filename

            output_doc = {
                "document_uuid": document_uuid,
                "filename": filename,
                "file_id": file_id,
                "currentFileVersion": payload.get("currentFileVersion") or "1.0.0",
                "user_id": payload.get("user_id") or meta.get("user_id"),
                "tenantId": payload.get("tenantId") or meta.get("tenantId"),
                "user_name": payload.get("user_name") or meta.get("user_name"),
                "user_email": payload.get("user_email") or meta.get("user_email"),
                "user_role": payload.get("user_role") or meta.get("user_role"),
                "frameworkCode": payload.get("frameworkCode") or meta.get("frameworkCode"),
                "frameworkName": payload.get("frameworkName") or meta.get("frameworkName"),
                "frameworkId": payload.get("frameworkId") or meta.get("frameworkId"),
                "frameworkVersion": payload.get("frameworkVersion")
                or meta.get("frameworkVersion"),
                "source": payload.get("source") or meta.get("source") or "Load Service",
                "fileVersions": [
                    {
                        "fileVersion": payload.get("currentFileVersion") or "1.0.0",
                        "status": "stub_processed",
                        "processed_at": _utcnow_iso(),
                        "data": {
                            str(control_id): {
                                "control_id": control_id,
                                "status": "placeholder",
                                "summary": (
                                    "Stub evidence output — full OCR/LLM pipeline "
                                    "not run in this port."
                                ),
                                "filename": filename,
                            }
                        },
                    }
                ],
            }

            existing = (
                await session.execute(
                    select(EvidenceOutput)
                    .where(EvidenceOutput.control_id == str(control_id))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if existing:
                existing.output = output_doc
                flag_modified(existing, "output")
            else:
                session.add(
                    EvidenceOutput(
                        id=new_id(),
                        control_id=str(control_id),
                        output=output_doc,
                    )
                )

        logger.info(
            "process_ingest complete | file_id=%s | control_id=%s",
            file_id,
            control_id,
        )
    except Exception as exc:
        logger.exception("process_ingest failed | error=%s", exc)
        if file_id:
            try:
                async with session_scope() as session:
                    uploaded = await session.get(UploadedFile, str(file_id))
                    if uploaded:
                        meta = dict(uploaded.meta or {})
                        meta["status"] = "failed"
                        meta["error"] = str(exc)
                        uploaded.meta = meta
                        flag_modified(uploaded, "meta")
            except Exception:
                logger.exception("failed to mark UploadedFile as failed")
