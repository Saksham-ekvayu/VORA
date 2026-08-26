"""Comparison runner — similarity scoring without RabbitMQ."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    DeploymentFramework,
    DeploymentPackageMerge,
    DocumentExtraction,
    FrameworkAssignment,
    PackageComparison,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


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


_st_model = None
_st_lock = asyncio.Lock()


async def _get_embedder_async():
    global _st_model
    if _st_model is not None:
        return _st_model

    async with _st_lock:
        if _st_model is not None:
            return _st_model
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            from vora_shared.config import get_settings

            settings = get_settings()
            model_name = settings.sentence_transformer_model
            _st_model = await asyncio.to_thread(SentenceTransformer, model_name)
            logger.info(f"Loaded sentence-transformers model {model_name}")
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


async def _similarity(a: str, b: str) -> float:
    model = await _get_embedder_async()
    if model is None:
        return _string_similarity(a, b)
    try:
        emb = await asyncio.to_thread(model.encode, [a or "", b or ""], normalize_embeddings=True)
        return round(float(_cosine(list(emb[0]), list(emb[1]))), 4)
    except Exception:  # noqa: BLE001
        return _string_similarity(a, b)


async def _batch_encode(texts: list[str]) -> list[list[float]]:
    """Encode multiple texts in a single batch for efficiency."""
    model = await _get_embedder_async()
    if model is None:
        return [[0.0] * 384 for _ in texts]  # Fallback: dummy vectors
    try:
        embeddings = await asyncio.to_thread(model.encode, texts, normalize_embeddings=True)
        return [list(e) for e in embeddings]
    except Exception:  # noqa: BLE001
        return [[0.0] * 384 for _ in texts]


def _batch_similarity(emb_a: list[float], embeddings_b: list[list[float]]) -> tuple[float, int]:
    """Find best match and return score + index."""
    best_score = 0.0
    best_idx = -1
    for idx, emb_b in enumerate(embeddings_b):
        score = _cosine(emb_a, emb_b)
        if score > best_score:
            best_score = score
            best_idx = idx
    return round(best_score, 4), best_idx


def _flatten_controls(sections: list[Any], is_assignment: bool = False) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for section in sections or []:
        if not isinstance(section, dict):
            continue
        section_name = section.get("name") or "Section"
        section_id = section.get("id")
        for control in section.get("controls") or []:
            if not isinstance(control, dict):
                continue
            
            if is_assignment:
                customization = control.get("customization") or {}
                if not customization.get("is_applicable", True):
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


def _extract_sections_from_controls(controls_block: Any) -> list[dict[str, Any]]:
    sections = []
    if isinstance(controls_block, dict):
        sections.extend(controls_block.get("controls_data") or [])
    elif isinstance(controls_block, list):
        for item in controls_block:
            if isinstance(item, dict):
                if "controls_data" in item:
                    sections.extend(item.get("controls_data") or [])
                elif "controls" in item:
                    sections.append(item)
    return sections


async def _parse_document_extraction(session, doc: dict) -> list[dict[str, Any]]:
    ai_ref = doc.get("aiExtraction")
    if isinstance(ai_ref, str):
        extraction = await session.get(DocumentExtraction, ai_ref)
        if not extraction:
            return []
        ai = extraction.aiExtraction or {}
        if isinstance(ai, dict):
            return _extract_sections_from_controls(ai.get("controls"))
    elif isinstance(ai_ref, dict):
        return _extract_sections_from_controls(ai_ref.get("controls") or {})
    return []


async def _fallback_to_package_merge(session, pkg: dict) -> list[dict[str, Any]]:
    merge_doc_id = pkg.get("mergeDocument")
    if not merge_doc_id:
        return []

    pm = await session.get(DeploymentPackageMerge, merge_doc_id)
    if pm and isinstance(pm.controls, dict):
        return pm.controls.get("controls_data") or []
    return []


async def _get_sections_from_package(session, pkg: dict) -> list[dict[str, Any]] | None:
    merged = pkg.get("mergedControls") or {}
    if isinstance(merged, dict):
        if controls := (merged.get("controls_data") or merged.get("controls")):
            return controls

    sections: list[dict[str, Any]] = []
    for doc in pkg.get("documents") or []:
        if isinstance(doc, dict):
            sections.extend(await _parse_document_extraction(session, doc))

    if not sections:
        return await _fallback_to_package_merge(session, pkg)

    return sections


async def _load_merge_sections(session, pkg_ver: str, df: DeploymentFramework):
    for pkg in df.packages or []:
        if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
            res = await _get_sections_from_package(session, pkg)
            return res if res is not None else []
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


async def _find_best_match_batch(
    fa_controls: list[dict[str, Any]], df_controls: list[dict[str, Any]]
) -> list[tuple[float, dict[str, Any]]]:
    """Batch encode all texts and find best match for each FA control."""
    if not fa_controls or not df_controls:
        return [(0.0, {}) for _ in fa_controls]

    # Extract all texts
    fa_texts = [_control_text(ctrl) for ctrl in fa_controls]
    df_texts = [_control_text(ctrl) for ctrl in df_controls]

    # Batch encode all texts at once
    fa_embeddings = await _batch_encode(fa_texts)
    df_embeddings = await _batch_encode(df_texts)

    # Find best match for each FA control
    results = []
    for fa_idx, fa_emb in enumerate(fa_embeddings):
        score, best_idx = _batch_similarity(fa_emb, df_embeddings)
        best_df = df_controls[best_idx] if best_idx >= 0 else {}
        results.append((score, best_df))

    return results


async def _find_best_match(
    fa_ctrl: dict[str, Any], df_controls: list[dict[str, Any]]
) -> tuple[float, dict[str, Any]]:
    """Fallback single-item wrapper for backward compatibility."""
    results = await _find_best_match_batch([fa_ctrl], df_controls)
    return results[0] if results else (0.0, {})


def _build_comparison_item(
    fa_ctrl: dict[str, Any], best_df: dict[str, Any], best_score: float
) -> dict[str, Any]:
    return {
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


async def _build_comparison_results(df_sections: list, assignment_sections: list) -> list[dict[str, Any]]:
    """Build comparison results using batch encoding for efficiency."""
    df_controls = _flatten_controls(df_sections, is_assignment=False)
    fa_controls = _flatten_controls(assignment_sections, is_assignment=True)

    if not fa_controls or not df_controls:
        return []

    # Batch encode all controls once
    best_matches = await _find_best_match_batch(fa_controls, df_controls)

    # Build sections and items
    section_map: dict[str, dict[str, Any]] = {}
    for fa_ctrl, (best_score, best_df) in zip(fa_controls, best_matches):
        sid = str(fa_ctrl.get("_section_id") or new_id())
        if sid not in section_map:
            section_map[sid] = {
                "id": sid,
                "name": fa_ctrl.get("_section_name") or "Section",
                "controls": [],
            }

        item = _build_comparison_item(fa_ctrl, best_df, best_score)
        section_map[sid]["controls"].append(item)

    return list(section_map.values())


async def _update_package_comparison(
    session, comparison_id: str | None, comparison_payload: dict
) -> PackageComparison:
    logger.info("[COMPARISON-RUNNER] Updating PackageComparison record...")
    pc = None
    if comparison_id:
        pc = await session.get(PackageComparison, comparison_id)

    if pc is None:
        logger.warning(f"[COMPARISON-RUNNER] PackageComparison not found (id={comparison_id}), creating new")
        pc = PackageComparison(
            id=new_id(),
            fileHashes=[],
            comparison=comparison_payload,
        )
        session.add(pc)
    else:
        logger.info("[COMPARISON-RUNNER] Found existing PackageComparison, updating")
        pc.comparison = comparison_payload
        pc.updatedAt = _utcnow()
        session.add(pc)

    await session.flush()
    logger.info(f"[COMPARISON-RUNNER] Updated PackageComparison: {pc.id}")
    return pc


async def _update_df_package_comparison(session, df_id: str, pkg_ver: str, pc_id: str) -> None:
    logger.info("[COMPARISON-RUNNER] Updating deployment framework packages...")
    df = await session.get(DeploymentFramework, df_id)
    if df:
        packages = list(df.packages or [])
        for i, pkg in enumerate(packages):
            if isinstance(pkg, dict) and pkg.get("packageVersion") == pkg_ver:
                pkg = dict(pkg)
                pkg["comparison"] = pc_id
                packages[i] = pkg
                break
        df.packages = packages
        session.add(df)
        await session.flush()
        logger.info("[COMPARISON-RUNNER] Updated deployment framework packages")


async def _save_failure_status(comparison_id: str | None, exc: Exception):
    try:
        async with session_scope() as session:
            pc = None
            if comparison_id:
                pc = await session.get(PackageComparison, str(comparison_id))

            if pc:
                pc.comparison = {
                    "status": "failed",
                    "message": f"Comparison failed: {str(exc)}",
                    "timestamp": _iso(),
                    "comparison_time_seconds": None,
                    "comparison_result": [],
                }
                session.add(pc)
                await session.commit()
    except Exception as db_exc:
        logger.exception(f"[COMPARISON-RUNNER-ERROR] Failed to update failure status: {db_exc}")


async def run_comparison(
    df_id: str,
    pkg_ver: str,
    framework_assignment_id: str | None = None,
    comparison_id: str | None = None,
) -> None:
    df_id = str(df_id).strip()
    pkg_ver = str(pkg_ver).strip()
    started = _utcnow()

    logger.info("=" * 80)
    logger.info("[COMPARISON-RUNNER] Starting comparison processing")
    logger.info(f"  Deployment Framework ID: {df_id}")
    logger.info(f"  Package Version: {pkg_ver}")
    logger.info(f"  Framework Assignment ID: {framework_assignment_id}")
    logger.info("=" * 80)

    try:
        logger.info("[COMPARISON-RUNNER] Loading model...")
        model = await _get_embedder_async()
        if model:
            logger.info("[COMPARISON-RUNNER] Model loaded successfully")
        else:
            logger.info("[COMPARISON-RUNNER]  Using string similarity fallback (model not available)")

        logger.info("[COMPARISON-RUNNER] Fetching deployment framework...")
        async with session_scope() as session:
            df = await session.get(DeploymentFramework, df_id)
            if not df:
                logger.error(f"DeploymentFramework not found with id: {df_id}")
                return

            fa_id = framework_assignment_id or df.assignedFrameworkId or df.frameworkId
            if not fa_id:
                logger.error("No assignedFrameworkId or frameworkId found")
                return

            logger.info(f"[COMPARISON-RUNNER] Resolved framework_assignment_id: {fa_id}")
            logger.info("[COMPARISON-RUNNER] Loading deployment framework controls...")

            df_sections = await _load_merge_sections(session, pkg_ver, df)
            if not df_sections:
                logger.error(f"No merge controls found for package '{pkg_ver}'")
                return

            logger.info(f"[COMPARISON-RUNNER] Loaded {len(df_sections)} deployment framework sections")

            logger.info("[COMPARISON-RUNNER] Loading assignment framework controls...")
            assignment_sections = await _load_assignment_sections(session, str(fa_id))
            if not assignment_sections:
                logger.error(f"No assignment controls for id: {fa_id}")
                return

            logger.info(
                f"[COMPARISON-RUNNER] Loaded {len(assignment_sections)} assignment framework sections"
            )
            logger.info("[COMPARISON-RUNNER] Starting similarity scoring...")

            # Run async similarity scoring
            grouped = await _build_comparison_results(df_sections, assignment_sections)
            elapsed = (_utcnow() - started).total_seconds()

            comparison_payload = {
                "status": "completed",
                "message": "Comparison completed",
                "timestamp": _iso(),
                "comparison_time_seconds": elapsed,
                "comparison_result": grouped,
            }

            pc = await _update_package_comparison(session, comparison_id, comparison_payload)
            await _update_df_package_comparison(session, df_id, pkg_ver, pc.id)

            # Commit all changes
            logger.info("[COMPARISON-RUNNER] Committing all changes to database...")
            await session.commit()
            logger.info("[COMPARISON-RUNNER] All changes committed successfully")

            # Fresh query from database to verify update
            logger.info("[COMPARISON-RUNNER] Verifying update - fresh query from database...")
            verified_pc = await session.get(PackageComparison, pc.id)
            if verified_pc and verified_pc.comparison:
                status_in_db = verified_pc.comparison.get("status", "unknown")
                results_count = len(verified_pc.comparison.get("comparison_result", []))
                logger.info("[COMPARISON-RUNNER] Verified in database:")
                logger.info(f"  Status: {status_in_db}")
                logger.info(f"  Results count: {results_count}")
            else:
                logger.warning("[COMPARISON-RUNNER] Could not verify - record not found after commit")

        logger.info(f"{'='*80}")
        logger.info("[COMPARISON-RUNNER-SUCCESS] Comparison complete!")
        logger.info(f"  Deployment Framework ID: {df_id}")
        logger.info(f"  Package Version: {pkg_ver}")
        logger.info(f"  Framework Assignment ID: {fa_id}")
        logger.info(f"  Total Comparison Sections: {len(grouped)}")
        logger.info(f"  Processing Time: {elapsed:.2f}s")
        logger.info("[COMPARISON-RUNNER-SAVED] Data saved to: PackageComparison table")
        logger.info(f"{'='*80}")

    except Exception as exc:  # noqa: BLE001
        logger.error(f"{'='*80}")
        logger.error("[COMPARISON-RUNNER-ERROR] run_comparison failed!")
        logger.error(f"  Deployment Framework ID: {df_id}")
        logger.error(f"  Package Version: {pkg_ver}")
        logger.exception(f"  Error: {str(exc)}")
        logger.error(f"{'='*80}")
        logger.exception("run_comparison exception traceback:")
        await _save_failure_status(comparison_id, exc)
