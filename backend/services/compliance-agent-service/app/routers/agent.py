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
from vora_shared.models import AgentPrompt, DeploymentDocument, EvidenceOutput, UploadedFile
from vora_shared.responses import error, success

logger = logging.getLogger(__name__)

router = APIRouter(tags=["compliance-agent"])

DEFAULT_AGENTS = [
    ("Organizational Controls Agent", "Evaluate general organizational policies and procedures."),
    ("People Controls Agent", "Review human resources security and training procedures."),
    ("Physical Controls Agent", "Assess physical security, entry logs, and secure areas."),
    ("Access Control Agent", "Evaluate access control evidence against the control requirements."),
    ("Logging & Monitoring Agent", "Validate logging, alert monitoring, and audit trails coverage."),
    ("Network Security Agent", "Assess network security, firewall rules, and traffic filtering controls."),
    ("Secure Development Agent", "Review software development life cycle security and source controls."),
    ("Technical Controls Agent", "Assess miscellaneous system configuration and endpoint protection controls."),
    ("Leadership Agent", "Review leadership quality goals and management alignment."),
    ("Planning Agent", "Validate operational planning, risk management, and system mapping."),
    ("Support & Resources Agent", "Evaluate infrastructure, competence, and documented resources."),
    ("Operational Controls Agent", "Assess change management and operational control parameters."),
    ("Performance Evaluation Agent", "Verify internal audits, management reviews, and customer satisfaction logs."),
    ("Change Management Agent", "Assess change management documentation and approvals."),
    ("Incident Response Agent", "Review incident response evidence and timelines."),
    ("General Compliance Agent", "Review general compliance guidelines and audits."),
]

from vora_shared.file_storage import ALLOWED_EXTENSIONS


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _ensure_default_agents() -> list[str]:
    async with session_scope() as session:
        rows = (await session.execute(select(AgentPrompt))).scalars().all()
        existing_names = {r.name for r in rows}
        
        added = False
        for name, prompt in DEFAULT_AGENTS:
            if name not in existing_names:
                session.add(AgentPrompt(id=new_id(), name=name, prompt=prompt, meta={}))
                added = True
                
        if added:
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


@router.get("/agents")
async def list_agents():
    try:
        logger.info("[LIST-AGENTS] Fetching available agents")
        agents = await _ensure_default_agents()
        logger.info(f"[LIST-AGENTS] Retrieved {len(agents)} agents")
        return success(
            message=f"Returned {len(agents)} agents",
            data={"agents": agents, "total": len(agents)},
        )
    except Exception as exc:
        logger.exception(f"[LIST-AGENTS] Error: {exc}")
        logger.exception("GET /agents failed: %s", exc)
        return error(str(exc), 500)


@router.get("/uploads")
async def list_uploads():
    try:
        logger.info("[LIST-UPLOADS] Fetching all uploaded files")
        async with session_scope() as session:
            rows = (
                (await session.execute(select(UploadedFile).order_by(UploadedFile.createdAt.desc())))
                .scalars()
                .all()
            )
            formatted = [_uploaded_to_dict(r) for r in rows]
        logger.info(f"[LIST-UPLOADS] Retrieved {len(formatted)} uploads")
        return success(
            message=f"Returned {len(formatted)} uploads",
            data={"total": len(formatted), "uploads": formatted},
        )
    except Exception as exc:
        logger.exception(f"[LIST-UPLOADS] Error: {exc}")
        logger.exception("GET /uploads failed: %s", exc)
        return error(str(exc), 500)


@router.get("/output")
async def get_all_output():
    try:
        logger.info("[GET-OUTPUT] Fetching all evidence outputs")
        async with session_scope() as session:
            rows = (
                (await session.execute(select(EvidenceOutput).order_by(EvidenceOutput.createdAt.desc())))
                .scalars()
                .all()
            )
            data = [_evidence_to_dict(r) for r in rows]
        logger.info(f"[GET-OUTPUT] Retrieved {len(data)} evidence documents")
        return success(
            message=f"Returned {len(data)} evidence documents",
            data={"total_files": len(data), "data": data},
        )
    except Exception as exc:
        logger.exception(f"[GET-OUTPUT] Error: {exc}")
        logger.exception("GET /output failed: %s", exc)
        return error(str(exc), 500)


@router.get("/output/by-document")
async def get_output_by_document():
    """Get compliance results grouped by document (file). Each file with all its 93 controls."""
    try:
        logger.info("[GET-OUTPUT-BY-DOC] Fetching evidence outputs grouped by document")
        async with session_scope() as session:
            rows = (
                (await session.execute(select(EvidenceOutput).order_by(EvidenceOutput.createdAt.desc())))
                .scalars()
                .all()
            )
            
            # Group by document_uuid
            grouped = {}
            for row in rows:
                output = row.output or {}
                doc_uuid = output.get("document_uuid", "unknown")
                filename = output.get("filename", "unknown")
                
                if doc_uuid not in grouped:
                    grouped[doc_uuid] = {
                        "document_uuid": doc_uuid,
                        "filename": filename,
                        "frameworkCode": output.get("frameworkCode"),
                        "frameworkName": output.get("frameworkName"),
                        "frameworkVersion": output.get("frameworkVersion"),
                        "user_id": output.get("user_id"),
                        "tenantId": output.get("tenantId"),
                        "controls": []
                    }
                
                # Add this control to the document group
                grouped[doc_uuid]["controls"].append({
                    "control_id": row.control_id,
                    "output": output
                })
            
            # Convert to list
            documents = list(grouped.values())
            logger.info(f"[GET-OUTPUT-BY-DOC] Grouped {len(rows)} controls into {len(documents)} documents")
            
            return success(
                message=f"Returned {len(documents)} documents with their compliance results",
                data={
                    "total_documents": len(documents),
                    "documents": documents
                },
            )
    except Exception as exc:
        logger.exception(f"[GET-OUTPUT-BY-DOC] Error: {exc}")
        return error(str(exc), 500)


async def _find_evidence_by_control_in_jsonb(session, control_id: str):
    all_rows = (await session.execute(select(EvidenceOutput))).scalars().all()
    for candidate in all_rows:
        output = candidate.output or {}
        for fv in output.get("fileVersions") or []:
            data = (fv or {}).get("data") or {}
            if control_id in data:
                return candidate
    return None


@router.get("/output/{control_id}")
async def get_output_by_control(control_id: str):
    try:
        logger.info(f"[GET-OUTPUT-CONTROL] Fetching output for control | control_id={control_id}")
        async with session_scope() as session:
            row = (
                await session.execute(
                    select(EvidenceOutput).where(EvidenceOutput.control_id == control_id).limit(1)
                )
            ).scalar_one_or_none()
            if not row:
                row = await _find_evidence_by_control_in_jsonb(session, control_id)
            if not row:
                logger.warning(f"[GET-OUTPUT-CONTROL] No evidence found | control_id={control_id}")
                return error(f"No evidence found for control '{control_id}'", 404)
            logger.info(f"[GET-OUTPUT-CONTROL] Found evidence | control_id={control_id}")
            return success(
                message=f"Found evidence for control '{control_id}'",
                data=_evidence_to_dict(row),
            )
    except Exception as exc:
        logger.exception(f"[GET-OUTPUT-CONTROL] Error for control {control_id}: {exc}")
        logger.exception("GET /output/%s failed: %s", control_id, exc)
        return error(str(exc), 500)


@router.get("/status")
async def status():
    try:
        logger.info("[STATUS] Checking service status")
        agents = await _ensure_default_agents()
        logger.info(f"[STATUS] Agents initialized: {len(agents)}")
    except Exception as exc:
        logger.exception(f"[STATUS] Agents fetch failed: {exc}")
        agents = []

    compliance_count = 0
    uploaded_count = 0
    try:
        async with session_scope() as session:
            compliance_count = (await session.execute(select(func.count()).select_from(EvidenceOutput))).scalar_one()
            uploaded_count = (await session.execute(select(func.count()).select_from(UploadedFile))).scalar_one()
        logger.info(f"[STATUS] Database counts | compliance_records={compliance_count} | uploaded_files={uploaded_count}")
    except Exception as exc:
        logger.exception(f"[STATUS] Database counts query failed: {exc}")

    settings = get_settings()
    evidence_folder = os.environ.get("UPLOAD_DIR", getattr(settings, "upload_dir", None) or "uploads")
    return success(
        message="Service status",
        data={
            "status": "running",
            "evidence_folder": evidence_folder,
            "available_agents": agents,
            "uploaded_files_count": uploaded_count,
            "compliance_records_count": compliance_count,
            "allowed_filetypes": list(ALLOWED_EXTENSIONS),
        },
    )



from app.services.agent_runner import evaluate_compliance_task


@router.post("/evaluate/{dd_id}")
async def evaluate_compliance_by_id(dd_id: str):
    logger.info(f"[API] Manual compliance evaluation requested for DeploymentDocument: {dd_id}")
    asyncio.create_task(evaluate_compliance_task(dd_id))
    return success(
        message="Compliance evaluation started in background",
        data={"dd_id": dd_id, "status": "processing"},
    )


@router.post("/evaluate")
async def evaluate_compliance(request: Request):
    dd_id = None
    try:
        body_bytes = await request.body()
        if body_bytes.strip():
            body = await request.json()
            dd_id = body.get("dd_id")
    except Exception:
        return error("Invalid JSON body", 400)

    if not dd_id:
        try:
            async with session_scope() as session:
                latest_dd = (
                    await session.execute(
                        select(DeploymentDocument).order_by(DeploymentDocument.createdAt.desc()).limit(1)
                    )
                ).scalars().first()
                
                if latest_dd:
                    dd_id = latest_dd.id
                    logger.info(f"[API] No dd_id provided. Auto-selected the latest DeploymentDocument: {dd_id}")
                else:
                    return error("No DeploymentDocument found in database to evaluate compliance.", 404)
        except Exception as exc:
            logger.exception(f"[API] Failed to retrieve latest DeploymentDocument: {exc}")
            return error(f"Failed to auto-select document: {str(exc)}", 500)

    logger.info(f"[API] Compliance evaluation requested via body for DeploymentDocument: {dd_id}")
    asyncio.create_task(evaluate_compliance_task(dd_id))
    return success(
        message="Compliance evaluation started in background",
        data={"dd_id": dd_id, "status": "processing"},
    )


@router.post("/evaluate-all")
async def evaluate_all_compliance():
    """Evaluate compliance for ALL deployment documents in the system."""
    try:
        async with session_scope() as session:
            all_dds = (
                await session.execute(
                    select(DeploymentDocument).order_by(DeploymentDocument.createdAt.desc())
                )
            ).scalars().all()
            
            if not all_dds:
                return error("No DeploymentDocuments found in database to evaluate compliance.", 404)
            
            logger.info(f"[API-ALL] Starting compliance evaluation for ALL {len(all_dds)} DeploymentDocuments")
            
            # Spawn task for each document
            for dd in all_dds:
                asyncio.create_task(evaluate_compliance_task(dd.id))
            
            return success(
                message=f"Compliance evaluation started in background for {len(all_dds)} documents",
                data={
                    "total_documents": len(all_dds),
                    "status": "processing",
                    "document_ids": [dd.id for dd in all_dds]
                },
            )
    except Exception as exc:
        logger.exception(f"[API-ALL] Failed to start bulk evaluation: {exc}")
        return error(f"Failed to start bulk evaluation: {str(exc)}", 500)

