"""Comparison runner — similarity scoring without RabbitMQ."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    ComparisonJob,
    ComparisonResult,
    DeploymentFramework,
    DocumentExtraction,
    FrameworkAssignment,
    PackageComparison,
    PackageMerge,
    PackageMergeTracking,
)

logger = logging.getLogger(__name__)

SendCb = Callable[[dict[str, Any]], Awaitable[None]]

_st_model = None
_st_tried = False


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


def send_event(
    event_name: str, status: str, message: str, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "status": status,
        "message": message,
        "timestamp": _iso(),
    }
    if extra:
        data.update(extra)
    return {"event": event_name, "data": data}


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


def _string_similarity(a: str, b: str) -> float:
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if not a or not b:
        return 0.0
    seq = SequenceMatcher(None, a, b).ratio()
    ta, tb = _tokenize(a), _tokenize(b)
    jaccard = (len(ta & tb) / len(ta | tb)) if ta and tb else 0.0
    return round(0.6 * seq + 0.4 * jaccard, 4)


def _get_embedder():
    global _st_model, _st_tried
    if _st_tried:
        return _st_model
    _st_tried = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Loaded sentence-transformers model all-MiniLM-L6-v2")
    except Exception as exc:  # noqa: BLE001
        logger.warning("sentence-transformers unavailable, using string fallback: %s", exc)
        _st_model = None
    return _st_model


def _cosine(u: list[float], v: list[float]) -> float:
    import math

    dot = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(b * b for b in v))
    if nu == 0 or nv == 0:
        return 0.0
    return float(dot / (nu * nv))


def _similarity(a: str, b: str) -> float:
    model = _get_embedder()
    if model is None:
        return _string_similarity(a, b)
    try:
        emb = model.encode([a or "", b or ""], normalize_embeddings=True)
        return round(float(_cosine(list(emb[0]), list(emb[1]))), 4)
    except Exception:  # noqa: BLE001
        return _string_similarity(a, b)


def _flatten_controls(sections: list[Any]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for section in sections or []:
        if not isinstance(section, dict):
            continue
        section_name = section.get("name") or "Section"
        section_id = section.get("id")
        for control in section.get("controls") or []:
            if not isinstance(control, dict):
                continue
            item = dict(control)
            item["_section_id"] = section_id
            item["_section_name"] = section_name
            flat.append(item)
    return flat


def _dp_list(control: dict[str, Any]) -> list[dict[str, Any]]:
    points = []
    for dp in control.get("deployment_points") or []:
        if not isinstance(dp, dict):
            continue
        points.append(
            {
                "id": str(dp.get("id") or new_id()),
                "point": dp.get("name") or dp.get("point") or "",
            }
        )
    return points


def _control_text(control: dict[str, Any]) -> str:
    name = control.get("name") or ""
    desc = control.get("description") or ""
    return f"{name} {desc}".strip()


async def _load_merge_sections(session, df_id: str, pkg_ver: str, df: DeploymentFramework):
    track = (
        await session.execute(
            select(PackageMergeTracking).where(
                PackageMergeTracking.deployment_framework_id == df_id,
                PackageMergeTracking.package_version == pkg_ver,
            )
        )
    ).scalar_one_or_none()
    if track and isinstance(track.data, dict):
        controls = track.data.get("controls_data") or []
        if controls:
            return controls

    merge_ref = (track.data or {}).get("mergeRefId") if track else None
    if merge_ref:
        pm = await session.get(PackageMerge, str(merge_ref))
        if pm and isinstance(pm.mergeExtraction, dict):
            controls = pm.mergeExtraction.get("controls_data") or []
            if controls:
                return controls

    pm = (
        await session.execute(select(PackageMerge).where(PackageMerge.frameworkId == df_id))
    ).scalar_one_or_none()
    if pm and isinstance(pm.mergeExtraction, dict):
        controls = pm.mergeExtraction.get("controls_data") or []
        if controls:
            return controls

    for pkg in df.packages or []:
        if not isinstance(pkg, dict) or pkg.get("packageVersion") != pkg_ver:
            continue
        merged = pkg.get("mergedControls") or {}
        if isinstance(merged, dict):
            controls = merged.get("controls_data") or merged.get("controls") or []
            if controls:
                return controls
        # Fallback: pull from DocumentExtraction records
        sections: list[dict[str, Any]] = []
        for doc in pkg.get("documents") or []:
            if not isinstance(doc, dict):
                continue
            ai_ref = doc.get("aiExtraction")
            if isinstance(ai_ref, str):
                extraction = await session.get(DocumentExtraction, ai_ref)
                if not extraction:
                    continue
                ai = extraction.aiExtraction or {}
                if isinstance(ai, dict):
                    controls_block = ai.get("controls")
                    if isinstance(controls_block, dict):
                        sections.extend(controls_block.get("controls_data") or [])
                    elif isinstance(controls_block, list):
                        for item in controls_block:
                            if isinstance(item, dict) and "controls_data" in item:
                                sections.extend(item.get("controls_data") or [])
                            elif isinstance(item, dict) and "controls" in item:
                                sections.append(item)
            elif isinstance(ai_ref, dict):
                controls_block = ai_ref.get("controls") or {}
                if isinstance(controls_block, dict):
                    sections.extend(controls_block.get("controls_data") or [])
        return sections
    return []


async def _load_assignment_sections(session, assignment_id: str) -> list[dict[str, Any]]:
    fa = await session.get(FrameworkAssignment, str(assignment_id))
    if not fa:
        return []
    for fv in fa.fileVersions or []:
        if not isinstance(fv, dict):
            continue
        ai = fv.get("aiExtraction") or fv.get("aiUpload")
        if isinstance(ai, list) and ai:
            return ai
        if isinstance(ai, dict):
            return ai.get("controls_data") or ai.get("controls") or []
    return []


async def run_comparison(
    df_id: str,
    pkg_ver: str,
    send_cb: SendCb,
    framework_assignment_id: str | None = None,
) -> None:
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()
    started = _utcnow()

    try:
        await send_cb(send_event("connected", "connected", "Initial connection"))
        await send_cb(send_event("started", "started", "Processing begins"))

        async with session_scope() as session:
            df = await session.get(DeploymentFramework, df_id)
            if not df:
                await send_cb(
                    {
                        "event": "failed",
                        "data": {
                            "error": "DEPLOYMENT_FRAMEWORK_NOT_FOUND",
                            "message": f"DeploymentFramework not found with id: {df_id}",
                            "deployment_framework_id": df_id,
                            "package_version": pkg_ver,
                            "timestamp": _iso(),
                        },
                    }
                )
                return

            fa_id = framework_assignment_id or df.assignedFrameworkId or df.frameworkId
            if not fa_id:
                await send_cb(
                    {
                        "event": "failed",
                        "data": {
                            "error": "FRAMEWORK_ASSIGNMENT_ID_NOT_FOUND",
                            "message": "No assignedFrameworkId or frameworkId found",
                            "deployment_framework_id": df_id,
                            "package_version": pkg_ver,
                            "timestamp": _iso(),
                        },
                    }
                )
                return

            df_sections = await _load_merge_sections(session, df_id, pkg_ver, df)
            if not df_sections:
                await send_cb(
                    {
                        "event": "failed",
                        "data": {
                            "error": "MERGE_CONTROLS_NOT_FOUND",
                            "message": f"No merge controls found for package '{pkg_ver}'",
                            "deployment_framework_id": df_id,
                            "package_version": pkg_ver,
                            "timestamp": _iso(),
                        },
                    }
                )
                return

            assignment_sections = await _load_assignment_sections(session, str(fa_id))
            if not assignment_sections:
                await send_cb(
                    {
                        "event": "failed",
                        "data": {
                            "error": "FRAMEWORK_ASSIGNMENT_NOT_FOUND",
                            "message": f"No assignment controls for id: {fa_id}",
                            "deployment_framework_id": df_id,
                            "package_version": pkg_ver,
                            "framework_assignment_id": fa_id,
                            "timestamp": _iso(),
                        },
                    }
                )
                return

            job = ComparisonJob(
                id=new_id(),
                deployment_framework_id=df_id,
                package_version=pkg_ver,
                framework_assignment_id=str(fa_id),
                status="processing",
                data={},
            )
            session.add(job)

        await send_cb(send_event("processing", "processing", "Comparing controls", {"progress": 10}))
        await asyncio.sleep(0.05)

        df_controls = _flatten_controls(df_sections)
        fa_controls = _flatten_controls(assignment_sections)

        # Group results by assigned-framework section
        section_map: dict[str, dict[str, Any]] = {}
        for fa_ctrl in fa_controls:
            sid = str(fa_ctrl.get("_section_id") or new_id())
            if sid not in section_map:
                section_map[sid] = {
                    "id": sid,
                    "name": fa_ctrl.get("_section_name") or "Section",
                    "controls": [],
                }

            best_score = 0.0
            best_df: dict[str, Any] | None = None
            fa_text = _control_text(fa_ctrl)
            for df_ctrl in df_controls:
                score = _similarity(fa_text, _control_text(df_ctrl))
                if score > best_score:
                    best_score = score
                    best_df = df_ctrl

            best_df = best_df or {}
            section_map[sid]["controls"].append(
                {
                    "deployment_framework_control_id": str(best_df.get("id") or ""),
                    "deployment_framework_control_name": best_df.get("name") or "",
                    "deployment_framework_control_description": best_df.get("description") or "",
                    "deployment_framework_deployment_points": _dp_list(best_df),
                    "assigned_framework_control_id": str(fa_ctrl.get("id") or ""),
                    "assigned_framework_control_name": fa_ctrl.get("name") or "",
                    "assigned_framework_control_description": fa_ctrl.get("description") or "",
                    "assigned_framework_deployment_points": _dp_list(fa_ctrl),
                    "comparison_score": best_score,
                    "reviewComment": "",
                }
            )

        grouped = list(section_map.values())
        elapsed = (_utcnow() - started).total_seconds()

        comparison_payload = {
            "status": "completed",
            "message": "Comparison completed",
            "timestamp": _iso(),
            "comparison_time_seconds": elapsed,
            "comparison_result": grouped,
        }

        async with session_scope() as session:
            cr = ComparisonResult(
                id=new_id(),
                deployment_framework_id=df_id,
                package_version=pkg_ver,
                result={
                    "framework_assignment_id": str(fa_id),
                    "grouped_results": grouped,
                    "comparison_time_seconds": elapsed,
                },
            )
            session.add(cr)

            pc = (
                await session.execute(select(PackageComparison).where(PackageComparison.frameworkId == df_id))
            ).scalar_one_or_none()
            if pc is None:
                pc = PackageComparison(
                    id=new_id(),
                    frameworkId=df_id,
                    fileHashes=[],
                    comparison=comparison_payload,
                )
                session.add(pc)
            else:
                pc.comparison = comparison_payload
                pc.updatedAt = _utcnow()

            # Update job status
            jobs = (
                (
                    await session.execute(
                        select(ComparisonJob)
                        .where(
                            ComparisonJob.deployment_framework_id == df_id,
                            ComparisonJob.package_version == pkg_ver,
                        )
                        .order_by(ComparisonJob.createdAt.desc())
                    )
                )
                .scalars()
                .all()
            )
            if jobs:
                jobs[0].status = "completed"
                jobs[0].data = {"comparison_result_id": cr.id}

            # Annotate DF package
            df = await session.get(DeploymentFramework, df_id)
            if df:
                packages = list(df.packages or [])
                for i, pkg in enumerate(packages):
                    if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                        pkg = dict(pkg)
                        pkg["comparison"] = cr.id
                        packages[i] = pkg
                        break
                df.packages = packages

        await send_cb(
            send_event(
                "completed",
                "completed",
                "Comparison completed",
                {
                    "deployment_framework_id": df_id,
                    "package_version": pkg_ver,
                    "framework_assignment_id": str(fa_id),
                    "comparison_time_seconds": elapsed,
                    "comparison_result": grouped,
                },
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_comparison failed | df=%s pkg=%s", df_id, pkg_ver)
        await send_cb(send_event("failed", "failed", str(exc)))
