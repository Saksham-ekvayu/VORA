"""Async extraction / merge runners — no RabbitMQ; driven by WebSocket connect."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    DeploymentFramework,
    DocumentExtraction,
    ExtractionResult,
    Framework,
    PackageMerge,
    PackageMergeTracking,
)

logger = logging.getLogger(__name__)

MSG_EXTRACTION_COMPLETED = "Extraction completed"
MSG_EXTRACTION_IN_PROGRESS = "Extraction in progress"
MSG_DOCUMENT_UPLOADED = "Document uploaded"

SendCb = Callable[[dict[str, Any]], Awaitable[None]]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


def _mock_controls(label: str = "Extracted Controls") -> list[dict[str, Any]]:
    """Simplified mock controls matching expected section/control shape."""
    section_id = new_id()
    controls = []
    for i, name in enumerate(
        ("Access Control Policy", "Data Retention Requirement", "Incident Response Plan"),
        start=1,
    ):
        controls.append(
            {
                "id": new_id(),
                "name": f"{name}",
                "description": f"Mock {label.lower()} control #{i}: {name}",
                "deployment_points": [
                    {
                        "id": new_id(),
                        "name": f"DP-{i}",
                        "status": "pending",
                        "path": "",
                        "weightage": 10,
                        "remark": "",
                    }
                ],
            }
        )
    return [{"id": section_id, "name": label, "controls": controls}]


def _controls_payload(controls_data: list[dict[str, Any]]) -> dict[str, Any]:
    total_controls = sum(len(s.get("controls") or []) for s in controls_data if isinstance(s, dict))
    return {
        "total_controls": total_controls,
        "total_sections": len(controls_data),
        "controls_data": controls_data,
    }


def _status_history(
    uploaded: str, processing: str, completed: str | None = None, failed: str | None = None
) -> dict[str, Any]:
    history = [
        {"status": "uploaded", "timestamp": uploaded, "message": "Document uploaded"},
        {"status": "processing", "timestamp": processing, "message": "Extraction in progress"},
    ]
    if failed:
        history.append({"status": "failed", "timestamp": failed, "message": "Extraction failed"})
        return {
            "processing_time_seconds": 0,
            "completed_at": failed,
            "history": history,
        }
    completed = completed or _iso()
    history.append({"status": "completed", "timestamp": completed, "message": MSG_EXTRACTION_COMPLETED})
    try:
        start = datetime.fromisoformat(uploaded.replace("Z", "+00:00"))
        end = datetime.fromisoformat(completed.replace("Z", "+00:00"))
        elapsed = max(0.0, (end - start).total_seconds())
    except Exception:  # noqa: BLE001
        elapsed = 1.0
    return {
        "processing_time_seconds": elapsed,
        "completed_at": completed,
        "history": history,
    }


def _find_file_version(file_versions: list[Any], file_id: str) -> tuple[int | None, dict | None]:
    for i, fv in enumerate(file_versions or []):
        if not isinstance(fv, dict):
            continue
        if str(fv.get("fileId")) == str(file_id):
            return i, dict(fv)
    return None, None


async def _upsert_extraction_result(
    *,
    ref_id: str,
    resource_type: str,
    file_id: str | None,
    package_version: str | None,
    status: str,
    result: dict[str, Any],
) -> str:
    async with session_scope() as session:
        stmt = select(ExtractionResult).where(
            ExtractionResult.ref_id == ref_id,
            ExtractionResult.resource_type == resource_type,
        )
        if file_id:
            stmt = stmt.where(ExtractionResult.file_id == str(file_id))
        if package_version:
            stmt = stmt.where(ExtractionResult.package_version == package_version)
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = ExtractionResult(
                id=new_id(),
                ref_id=ref_id,
                resource_type=resource_type,
                file_id=str(file_id) if file_id else None,
                package_version=package_version,
                status=status,
                result=result,
                meta={},
            )
            session.add(row)
        else:
            row.status = status
            row.result = result
            row.updatedAt = _utcnow()
        await session.flush()
        return row.id


async def _update_framework_ai_status(
    session: Any, framework_id: str, file_id: str, status_data: dict[str, Any], replace: bool = False
) -> None:
    fw = await session.get(Framework, framework_id)
    if not fw:
        return
    versions = list(fw.fileVersions or [])
    idx, fv = _find_file_version(versions, file_id)
    if idx is None or fv is None:
        return

    if replace:
        fv["aiExtraction"] = status_data
    else:
        ai = dict(fv.get("aiExtraction") or {})
        ai.update(status_data)
        fv["aiExtraction"] = ai

    versions[idx] = fv
    fw.fileVersions = versions


async def run_framework_extraction(framework_id: str, file_id: str) -> None:
    """Load Framework, update fileVersions[].aiExtraction, push WS progress."""
    framework_id = str(framework_id).strip()
    file_id = str(file_id).strip()
    uploaded_ts = _iso()

    try:
        async with session_scope() as session:
            await _update_framework_ai_status(
                session,
                framework_id,
                file_id,
                {
                    "status": "uploaded",
                    "timestamp": uploaded_ts,
                    "message": MSG_DOCUMENT_UPLOADED,
                },
            )

        processing_ts = _iso()
        async with session_scope() as session:
            await _update_framework_ai_status(
                session,
                framework_id,
                file_id,
                {
                    "status": "processing",
                    "timestamp": processing_ts,
                    "message": MSG_EXTRACTION_IN_PROGRESS,
                },
            )

        # Simulated / mock extraction pipeline
        controls_data = _mock_controls(label="Framework Controls")
        controls = _controls_payload(controls_data)
        completed_ts = _iso()
        history = _status_history(uploaded_ts, processing_ts, completed_ts)

        async with session_scope() as session:
            await _update_framework_ai_status(
                session,
                framework_id,
                file_id,
                {
                    "status": "extracted",
                    "timestamp": completed_ts,
                    "message": MSG_EXTRACTION_COMPLETED,
                    "statusHistory": {
                        "processingTimeSeconds": history["processing_time_seconds"],
                        "completedAt": history["completed_at"],
                        "history": [
                            {
                                "status": ("extracted" if h["status"] == "completed" else h["status"]),
                                "timestamp": h["timestamp"],
                                "message": h.get("message"),
                            }
                            for h in history["history"]
                        ],
                    },
                    "controls": controls,
                },
                replace=True,
            )

        await _upsert_extraction_result(
            ref_id=framework_id,
            resource_type="framework",
            file_id=file_id,
            package_version=None,
            status="extracted",
            result={
                "status": "extracted",
                "controls": controls,
                "status_history": history,
                "fileVersions": [
                    {
                        "fileId": file_id,
                        "aiUpload": {
                            "status": "extracted",
                            "controls": controls,
                            "status_history": history,
                            "processing_time_seconds": history["processing_time_seconds"],
                        },
                    }
                ],
            },
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("run_framework_extraction failed | id=%s", framework_id)
        fail_ts = _iso()
        try:
            async with session_scope() as session:
                await _update_framework_ai_status(
                    session,
                    framework_id,
                    file_id,
                    {
                        "status": "failed",
                        "timestamp": fail_ts,
                        "message": str(exc),
                    },
                )
        except Exception:  # noqa: BLE001
            pass


async def _get_or_create_doc_extraction(
    session, file_hash: str, existing_id: str | None
) -> DocumentExtraction:
    if existing_id:
        row = await session.get(DocumentExtraction, str(existing_id))
        if row:
            return row
    if file_hash:
        row = (
            await session.execute(select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash))
        ).scalar_one_or_none()
        if row:
            return row
    row = DocumentExtraction(id=new_id(), fileHash=file_hash or new_id(), aiExtraction={})
    session.add(row)
    await session.flush()
    return row


def _find_package_and_doc(
    df: DeploymentFramework, pkg_ver: str, file_id: str
) -> tuple[list[Any], int | None, list[Any], int | None]:
    packages = list(df.packages or [])
    pkg_idx = next(
        (i for i, p in enumerate(packages) if isinstance(p, dict) and p.get("packageVersion") == pkg_ver),
        None,
    )
    if pkg_idx is None:
        return packages, None, [], None

    pkg = dict(packages[pkg_idx])
    documents = [dict(d) if isinstance(d, dict) else d for d in (pkg.get("documents") or [])]
    doc_idx = next(
        (i for i, d in enumerate(documents) if isinstance(d, dict) and str(d.get("fileId")) == file_id),
        None,
    )
    return packages, pkg_idx, documents, doc_idx


async def _update_deployment_ai_status(
    session: Any, df_id: str, pkg_ver: str, file_id: str, status_data: dict[str, Any]
) -> None:
    df = await session.get(DeploymentFramework, df_id)
    if not df:
        return

    packages, pkg_idx, documents, doc_idx = _find_package_and_doc(df, pkg_ver, file_id)
    if pkg_idx is None or doc_idx is None:
        return

    pkg = dict(packages[pkg_idx])
    doc = documents[doc_idx]
    file_hash = str(doc.get("fileHash") or "")
    existing_ai = doc.get("aiExtraction")
    existing_id = existing_ai if isinstance(existing_ai, str) else None

    extraction = await _get_or_create_doc_extraction(session, file_hash, existing_id)
    extraction.aiExtraction = status_data

    doc["aiExtraction"] = extraction.id
    documents[doc_idx] = doc
    pkg["documents"] = documents
    packages[pkg_idx] = pkg
    df.packages = packages


async def run_deployment_extraction(df_id: str, pkg_ver: str, file_id: str) -> None:
    """Load DeploymentFramework, update DocumentExtraction + packages JSONB, push WS."""
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()
    file_id = str(file_id).strip()
    uploaded_ts = _iso()

    try:
        async with session_scope() as session:
            await _update_deployment_ai_status(
                session,
                df_id,
                pkg_ver,
                file_id,
                {
                    "status": "uploaded",
                    "timestamp": uploaded_ts,
                    "message": MSG_DOCUMENT_UPLOADED,
                },
            )

        processing_ts = _iso()
        async with session_scope() as session:
            await _update_deployment_ai_status(
                session,
                df_id,
                pkg_ver,
                file_id,
                {
                    "status": "processing",
                    "timestamp": processing_ts,
                    "message": MSG_EXTRACTION_IN_PROGRESS,
                },
            )

        controls_data = _mock_controls(label="Deployment Controls")
        controls = _controls_payload(controls_data)
        completed_ts = _iso()
        history = _status_history(uploaded_ts, processing_ts, completed_ts)

        async with session_scope() as session:
            await _update_deployment_ai_status(
                session,
                df_id,
                pkg_ver,
                file_id,
                {
                    "status": "extracted",
                    "timestamp": completed_ts,
                    "message": MSG_EXTRACTION_COMPLETED,
                    "statusHistory": [history],
                    "controls": [controls],
                },
            )

        await _upsert_extraction_result(
            ref_id=df_id,
            resource_type="deployment-framework",
            file_id=file_id,
            package_version=pkg_ver,
            status="extracted",
            result={
                "status": "extracted",
                "controls": controls,
                "status_history": history,
                "package_version": pkg_ver,
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("run_deployment_extraction failed | id=%s", df_id)


def _extract_from_list(ai_list: list[Any]) -> list[dict[str, Any]]:
    for item in ai_list:
        if isinstance(item, dict) and "controls_data" in item:
            return item.get("controls_data") or []
    return ai_list if all(isinstance(x, dict) and "controls" in x for x in ai_list) else []


def _extract_from_dict(ai_dict: dict[str, Any]) -> list[dict[str, Any]]:
    controls = ai_dict.get("controls")
    if isinstance(controls, dict):
        return controls.get("controls_data") or controls.get("controls") or []
    if isinstance(controls, list):
        if controls and isinstance(controls[0], dict) and "controls_data" in controls[0]:
            return controls[0].get("controls_data") or []
        return controls
    return ai_dict.get("controls_data") or []


def _extract_controls_from_ai(ai: Any) -> list[dict[str, Any]]:
    if not ai:
        return []
    if isinstance(ai, list):
        return _extract_from_list(ai)
    if isinstance(ai, dict):
        return _extract_from_dict(ai)
    return []


async def _process_package_documents(
    documents: list[Any], session: Any
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    merged_sections: list[dict[str, Any]] = []
    file_hashes: list[str] = []
    source_documents: list[dict[str, Any]] = []
    merge_history: list[dict[str, Any]] = []

    for doc in documents:
        if not isinstance(doc, dict):
            continue
        file_hashes.append(str(doc.get("fileHash") or ""))
        source_documents.append(
            {
                "fileId": str(doc.get("fileId")),
                "fileHash": doc.get("fileHash"),
                "originalFileName": doc.get("originalFileName"),
                "mergedAt": _iso(),
            }
        )
        merge_history.append(
            {
                "fileId": str(doc.get("fileId")),
                "fileName": doc.get("originalFileName"),
                "mergedAt": _iso(),
            }
        )

        ai_ref = doc.get("aiExtraction")
        ai_payload: Any = None
        if isinstance(ai_ref, str):
            extraction = await session.get(DocumentExtraction, ai_ref)
            if extraction:
                ai_payload = extraction.aiExtraction
        elif isinstance(ai_ref, dict):
            ai_payload = ai_ref

        sections = _extract_controls_from_ai(ai_payload)
        for section in sections:
            if isinstance(section, dict):
                merged_sections.append(dict(section))

    return merged_sections, file_hashes, source_documents, merge_history


async def _upsert_package_merge_records(
    session: Any,
    df_id: str,
    pkg_ver: str,
    file_hashes: list[str],
    source_documents: list[dict[str, Any]],
    merge_history: list[dict[str, Any]],
    merged_sections: list[dict[str, Any]],
    merge_extraction: dict[str, Any],
) -> str:
    pm_row = (
        await session.execute(select(PackageMerge).where(PackageMerge.frameworkId == df_id))
    ).scalar_one_or_none()
    if pm_row is None:
        pm_row = PackageMerge(
            id=new_id(),
            frameworkId=df_id,
            fileHashes=file_hashes,
            sourceDocuments=source_documents,
            mergeExtraction=merge_extraction,
        )
        session.add(pm_row)
    else:
        pm_row.fileHashes = file_hashes
        pm_row.sourceDocuments = source_documents
        pm_row.mergeExtraction = merge_extraction
        pm_row.updatedAt = _utcnow()

    track = (
        await session.execute(
            select(PackageMergeTracking).where(
                PackageMergeTracking.deployment_framework_id == df_id,
                PackageMergeTracking.package_version == pkg_ver,
            )
        )
    ).scalar_one_or_none()

    track_data = {
        "mergeHistory": merge_history,
        "controls_data": merged_sections,
        "mergeRefId": None,
    }
    if track is None:
        track = PackageMergeTracking(
            id=new_id(),
            deployment_framework_id=df_id,
            package_version=pkg_ver,
            status="merged",
            data=track_data,
        )
        session.add(track)
    else:
        track.status = "merged"
        track.data = track_data
        track.updatedAt = _utcnow()

    await session.flush()
    track_data["mergeRefId"] = pm_row.id
    track.data = track_data
    return pm_row.id


async def run_package_merge(df_id: str, pkg_ver: str) -> None:
    """Merge extracted document controls for a package; upsert PackageMerge* rows."""
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()

    try:
        async with session_scope() as session:
            df = await session.get(DeploymentFramework, df_id)
            if not df:
                return

            packages = list(df.packages or [])
            pkg = next(
                (p for p in packages if isinstance(p, dict) and p.get("packageVersion") == pkg_ver),
                None,
            )
            if not pkg:
                return

            documents = pkg.get("documents") or []
            merged_sections, file_hashes, source_documents, merge_history = await _process_package_documents(
                documents, session
            )

            if not merged_sections:
                # Fallback mock merge so downstream comparison can proceed in demos
                merged_sections = _mock_controls(label="Merged Package Controls")

            merge_extraction = {
                "status": "merged",
                "timestamp": _iso(),
                "message": "Package merge completed",
                "controls_data": merged_sections,
            }

            pm_row_id = await _upsert_package_merge_records(
                session,
                df_id,
                pkg_ver,
                file_hashes,
                source_documents,
                merge_history,
                merged_sections,
                merge_extraction,
            )

            # Annotate package with mergedControls for convenience
            packages = list(df.packages or [])
            for i, p in enumerate(packages):
                if isinstance(p, dict) and p.get("packageVersion") == pkg_ver:
                    p = dict(p)
                    p["mergedControls"] = {
                        "controls": merged_sections,
                        "controls_data": merged_sections,
                    }
                    p["mergeDocument"] = pm_row_id
                    packages[i] = p
                    break
            df.packages = packages

    except Exception:  # noqa: BLE001
        logger.exception("run_package_merge failed | id=%s pkg=%s", df_id, pkg_ver)
