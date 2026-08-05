"""Compliance agent service routes — Postgres, no RabbitMQ / Mongo."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from vora_shared.config import get_settings
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import AgentPrompt, EvidenceOutput, UploadedFile
from vora_shared.responses import error, success

from app.services.agent_runner import process_ingest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["compliance-agent"])

DEFAULT_AGENTS = [
    ("Access Control Agent", "Evaluate access control evidence against the control requirements."),
    ("Change Management Agent", "Assess change management documentation and approvals."),
    ("Incident Response Agent", "Review incident response evidence and timelines."),
    ("Logging & Monitoring Agent", "Validate logging and monitoring coverage."),
]

ALLOWED_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".docx", ".doc")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _ensure_default_agents() -> list[str]:
    async with session_scope() as session:
        rows = (await session.execute(select(AgentPrompt))).scalars().all()
        if not rows:
            for name, prompt in DEFAULT_AGENTS:
                session.add(AgentPrompt(id=new_id(), name=name, prompt=prompt, meta={}))
            await session.flush()
            rows = (await session.execute(select(AgentPrompt))).scalars().all()
        return [r.name for r in rows]


def _uploaded_to_dict(row: UploadedFile) -> dict[str, Any]:
    meta = row.meta or {}
    return {
        "file_id": row.id,
        "id": row.id,
        "ref_id": row.ref_id,
        "filename": row.filename,
        "file_path": row.file_path,
        "s3_url": row.s3_url,
        "agent_name": meta.get("agent_name"),
        "status": meta.get("status", "uploaded"),
        "uuid": row.ref_id or row.id,
        "resourceType": meta.get("resourceType"),
        "user_id": meta.get("user_id"),
        "tenantId": meta.get("tenantId"),
        "user_name": meta.get("user_name"),
        "user_email": meta.get("user_email"),
        "user_role": meta.get("user_role"),
        "frameworkCode": meta.get("frameworkCode"),
        "frameworkName": meta.get("frameworkName"),
        "frameworkId": meta.get("frameworkId"),
        "frameworkVersion": meta.get("frameworkVersion"),
        "timestamp": row.createdAt,
        "meta": meta,
    }


def _evidence_to_dict(row: EvidenceOutput) -> dict[str, Any]:
    output = dict(row.output or {})
    if "control_id" not in output and row.control_id:
        output["control_id"] = row.control_id
    output.setdefault("id", row.id)
    return output


@router.get("/health")
async def health_check():
    return success(
        message="Service is healthy",
        data={"status": "healthy", "service": "compliance-agent-service"},
    )


@router.get("/agents")
async def list_agents():
    try:
        agents = await _ensure_default_agents()
        return success(
            message=f"Returned {len(agents)} agents",
            data={"agents": agents, "total": len(agents)},
        )
    except Exception as exc:
        logger.exception("GET /agents failed: %s", exc)
        return error(str(exc), 500)


@router.get("/uploads")
async def list_uploads():
    try:
        async with session_scope() as session:
            rows = (
                await session.execute(
                    select(UploadedFile).order_by(UploadedFile.createdAt.desc())
                )
            ).scalars().all()
            formatted = [_uploaded_to_dict(r) for r in rows]
        return success(
            message=f"Returned {len(formatted)} uploads",
            data={"total": len(formatted), "uploads": formatted},
        )
    except Exception as exc:
        logger.exception("GET /uploads failed: %s", exc)
        return error(str(exc), 500)


@router.get("/output")
async def get_all_output():
    try:
        async with session_scope() as session:
            rows = (
                await session.execute(
                    select(EvidenceOutput).order_by(EvidenceOutput.createdAt.desc())
                )
            ).scalars().all()
            data = [_evidence_to_dict(r) for r in rows]
        return success(
            message=f"Returned {len(data)} evidence documents",
            data={"total_files": len(data), "data": data},
        )
    except Exception as exc:
        logger.exception("GET /output failed: %s", exc)
        return error(str(exc), 500)


@router.get("/output/{control_id}")
async def get_output_by_control(control_id: str):
    try:
        async with session_scope() as session:
            row = (
                await session.execute(
                    select(EvidenceOutput)
                    .where(EvidenceOutput.control_id == control_id)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if not row:
                # Fallback: scan JSONB for nested control keys
                all_rows = (await session.execute(select(EvidenceOutput))).scalars().all()
                for candidate in all_rows:
                    output = candidate.output or {}
                    for fv in output.get("fileVersions") or []:
                        data = (fv or {}).get("data") or {}
                        if control_id in data:
                            row = candidate
                            break
                    if row:
                        break
            if not row:
                return error(f"No evidence found for control '{control_id}'", 404)
            return success(
                message=f"Found evidence for control '{control_id}'",
                data=_evidence_to_dict(row),
            )
    except Exception as exc:
        logger.exception("GET /output/%s failed: %s", control_id, exc)
        return error(str(exc), 500)


@router.get("/status")
async def status():
    try:
        agents = await _ensure_default_agents()
    except Exception as exc:
        logger.error("GET /status | agents fetch failed: %s", exc)
        agents = []

    try:
        async with session_scope() as session:
            count = (
                await session.execute(select(func.count()).select_from(EvidenceOutput))
            ).scalar_one()
    except Exception as exc:
        logger.error("GET /status | evidence count failed: %s", exc)
        count = 0

    settings = get_settings()
    evidence_folder = os.environ.get(
        "UPLOAD_DIR", getattr(settings, "upload_dir", None) or "uploads"
    )
    return success(
        message="Service status",
        data={
            "status": "running",
            "evidence_folder": evidence_folder,
            "available_agents": agents,
            "evidence_files": count,
            "allowed_filetypes": list(ALLOWED_EXTENSIONS),
        },
    )


@router.post("/ingest")
async def ingest(request: Request):
    """Called by load-document-service after a successful generic document upload."""
    try:
        body = await request.json()
    except Exception:
        return error("Invalid JSON body", 400)

    if not isinstance(body, dict):
        return error("Payload must be a JSON object", 400)

    filename = body.get("filename") or "unknown"
    filepath = body.get("filepath") or body.get("file_path")
    ref_id = body.get("id") or body.get("document_uuid")
    meta_in = body.get("meta") if isinstance(body.get("meta"), dict) else {}

    meta: dict[str, Any] = {
        "status": "uploaded",
        "resourceType": body.get("resourceType") or "deployment-document",
        "file_hash": body.get("file_hash"),
        "source": body.get("source") or meta_in.get("source") or "Load Service",
        "agent_name": body.get("agent_name") or meta_in.get("agent_name"),
        "user_id": body.get("user_id") or meta_in.get("user_id"),
        "tenantId": body.get("tenantId") or meta_in.get("tenantId"),
        "user_name": body.get("user_name") or meta_in.get("name") or meta_in.get("user_name"),
        "user_email": body.get("user_email") or meta_in.get("email") or meta_in.get("user_email"),
        "user_role": body.get("user_role") or meta_in.get("role") or meta_in.get("user_role"),
        "frameworkCode": body.get("frameworkCode") or meta_in.get("frameworkCode"),
        "frameworkName": body.get("frameworkName") or meta_in.get("frameworkName"),
        "frameworkId": body.get("frameworkId") or meta_in.get("frameworkId"),
        "frameworkVersion": body.get("frameworkVersion") or meta_in.get("frameworkVersion"),
        "currentFileVersion": body.get("currentFileVersion") or meta_in.get("currentFileVersion"),
        "received_at": _utcnow_iso(),
    }

    async with session_scope() as session:
        uploaded = UploadedFile(
            id=new_id(),
            ref_id=str(ref_id) if ref_id else None,
            filename=str(filename),
            file_path=str(filepath) if filepath else None,
            s3_url=body.get("s3_url"),
            meta=meta,
        )
        session.add(uploaded)
        await session.flush()
        file_id = uploaded.id

    process_payload = {
        **body,
        "file_id": file_id,
        "uploaded_file_id": file_id,
        "filename": filename,
        "filepath": filepath,
        "control_id": meta.get("agent_name") or "placeholder",
        "meta": meta,
    }

    # Background stub processing (OCR/LLM omitted)
    asyncio.get_running_loop().create_task(process_ingest(process_payload))

    return success(
        message="Ingest accepted",
        status_code=202,
        data={
            "file_id": file_id,
            "filename": filename,
            "status": "accepted",
            "ref_id": ref_id,
        },
    )
