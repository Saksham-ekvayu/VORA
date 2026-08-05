"""Port of deployment-framework-service-main/src/services/analysis-websocket.service.js.

Unified WebSocket client for sequential package merge -> comparison -> gap
analysis, using `websockets` + asyncio instead of Node's `ws` + callbacks.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import websockets
from app.helpers.deployment_framework_helpers import coerce_packages
from vora_shared.database import session_scope

logger = logging.getLogger("analysis_websocket")


def _ws_base_url_analysis() -> str:
    return os.environ.get("AI_WEBSOCKET_URL", "ws://192.168.1.30:7000")


STATUS_MAP = {
    "connected": "connected",
    "started": "started",
    "processing": "processing",
    "completed": "completed",
    "failed": "failed",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts) -> datetime:
    if not ts:
        return _utcnow()
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return _utcnow()


def _blob_get(blob: Any, key: str, default: Any = None) -> Any:
    if blob is None:
        return default
    if isinstance(blob, dict):
        return blob.get(key, default)
    return getattr(blob, key, default)


def _set_merge_fields(merge, *, status: str, payload: dict[str, Any], pkg=None) -> None:
    data = dict(merge.mergeExtraction or {})
    data["status"] = status
    data["timestamp"] = _parse_ts(payload.get("timestamp")).isoformat()
    data["message"] = payload.get("message")
    if status == "merged":
        data["controls_data"] = payload.get("controls_data") or []
        merge_history = payload.get("mergeHistory") or []
        if merge_history and pkg is not None:
            source_documents = []
            for h in merge_history:
                matching_doc = next(
                    (d for d in (pkg.documents or []) if str(d.fileId) == str(h.get("fileId"))),
                    None,
                )
                source_documents.append(
                    {
                        "fileId": h.get("fileId"),
                        "fileHash": matching_doc.fileHash if matching_doc else None,
                        "originalFileName": h.get("fileName")
                        or (matching_doc.originalFileName if matching_doc else None),
                        "mergedAt": _parse_ts(h.get("mergedAt")).isoformat(),
                    }
                )
            merge.sourceDocuments = source_documents
    merge.mergeExtraction = data


# ─── Merge ──────────────────────────────────────────────────────────────────


async def start_merge(deployment_framework_id: str, package_version: str) -> None:
    from vora_shared.models import DeploymentFramework, PackageMerge

    url = (
        f"{_ws_base_url_analysis()}/api/extract/ws/package-merge/{deployment_framework_id}/{package_version}"
    )

    async def _update_merge(status: str, payload: dict[str, Any]) -> None:
        async with session_scope() as session:
            framework = await session.get(DeploymentFramework, str(deployment_framework_id))
            packages = coerce_packages(framework.packages if framework else [])
            pkg = next((p for p in packages if p.packageVersion == package_version), None)
            if not pkg or not pkg.mergeDocument:
                return
            merge = await session.get(PackageMerge, str(pkg.mergeDocument))
            if not merge:
                return
            _set_merge_fields(merge, status=status, payload=payload, pkg=pkg)

    async def on_message(event: str, payload: dict[str, Any]) -> None:
        try:
            if event == "merge_processing":
                await _update_merge(payload.get("status") or "processing", payload)
            elif event in ("merge_not_found", "merge_not_ready"):
                message = (
                    "Unable to reach the AI extraction service. Please try again later."
                    if event == "merge_not_found"
                    else "The AI merge service is not ready yet. Please try again in a moment."
                )
                await _update_merge("failed", {**payload, "message": message})
                raise _CloseConnection()
            elif event == "merge_completed":
                await _update_merge("merged", payload)
                raise _CloseConnection()
            elif event == "merge_failed":
                await _update_merge("failed", payload)
                raise _CloseConnection()
        except _CloseConnection:
            raise
        except Exception as exc:
            logger.error("[Merge WS] Error handling message: %s", exc)

    await _run_with_close_guard(url, on_message)

    try:
        async with session_scope() as session:
            framework = await session.get(DeploymentFramework, str(deployment_framework_id))
            packages = coerce_packages(framework.packages if framework else [])
            pkg = next((p for p in packages if p.packageVersion == package_version), None)
            if pkg and pkg.mergeDocument:
                merge = await session.get(PackageMerge, str(pkg.mergeDocument))
                if merge and _blob_get(merge.mergeExtraction, "status") not in ("merged", "failed"):
                    _set_merge_fields(
                        merge,
                        status="failed",
                        payload={"message": "WebSocket disconnected unexpectedly"},
                        pkg=pkg,
                    )
    except Exception as exc:
        logger.error("[Merge WS] Error updating failed status on close: %s", exc)


# ─── Comparison ─────────────────────────────────────────────────────────────


async def start_comparison(deployment_framework_id: str, package_version: str) -> None:
    from vora_shared.models import DeploymentFramework, PackageComparison

    url = (
        f"{_ws_base_url_analysis()}/api/comparison/ws/comparison/{deployment_framework_id}/{package_version}"
    )

    async def _update_comparison(status: str, payload: dict[str, Any]) -> None:
        async with session_scope() as session:
            framework = await session.get(DeploymentFramework, str(deployment_framework_id))
            packages = coerce_packages(framework.packages if framework else [])
            pkg = next((p for p in packages if p.packageVersion == package_version), None)
            if not pkg or not pkg.comparison:
                return
            comparison = await session.get(PackageComparison, str(pkg.comparison))
            if not comparison:
                return
            data = dict(comparison.comparison or {})
            data["status"] = status
            data["timestamp"] = _parse_ts(payload.get("timestamp")).isoformat()
            data["message"] = payload.get("message")
            if status == "completed":
                data["comparison_time_seconds"] = payload.get("comparison_time_seconds")
                data["comparison_result"] = payload.get("comparison_result") or []
            comparison.comparison = data

    async def on_message(event: str, payload: dict[str, Any]) -> None:
        try:
            db_status = STATUS_MAP.get(payload.get("status"), payload.get("status"))
            if event in ("connected", "started", "processing"):
                await _update_comparison(db_status, payload)
            elif event == "completed":
                await _update_comparison("completed", payload)
                raise _CloseConnection()
            elif event == "failed":
                await _update_comparison("failed", payload)
                raise _CloseConnection()
        except _CloseConnection:
            raise
        except Exception as exc:
            logger.error("[Comparison WS] Error handling message: %s", exc)

    await _run_with_close_guard(url, on_message)

    try:
        async with session_scope() as session:
            framework = await session.get(DeploymentFramework, str(deployment_framework_id))
            packages = coerce_packages(framework.packages if framework else [])
            pkg = next((p for p in packages if p.packageVersion == package_version), None)
            if pkg and pkg.comparison:
                comparison = await session.get(PackageComparison, str(pkg.comparison))
                if comparison and _blob_get(comparison.comparison, "status") not in ("completed", "failed"):
                    data = dict(comparison.comparison or {})
                    data["status"] = "failed"
                    data["message"] = "WebSocket disconnected unexpectedly"
                    comparison.comparison = data
    except Exception as exc:
        logger.error("[Comparison WS] Error updating failed status on close: %s", exc)


# ─── Gap Analysis ───────────────────────────────────────────────────────────


async def start_gap_analysis(deployment_framework_id: str, package_version: str) -> None:
    from vora_shared.models import DeploymentFramework, PackageGapAnalysis

    url = f"{_ws_base_url_analysis()}/api/deployment-gap/ws/gap/{deployment_framework_id}/{package_version}"

    async def _update_gap(status: str, payload: dict[str, Any]) -> None:
        async with session_scope() as session:
            framework = await session.get(DeploymentFramework, str(deployment_framework_id))
            packages = coerce_packages(framework.packages if framework else [])
            pkg = next((p for p in packages if p.packageVersion == package_version), None)
            if not pkg or not pkg.gapAnalysis:
                return
            gap = await session.get(PackageGapAnalysis, str(pkg.gapAnalysis))
            if not gap:
                return
            data = dict(gap.gapAnalysis or {})
            data["status"] = status
            data["timestamp"] = _parse_ts(payload.get("timestamp")).isoformat()
            data["message"] = payload.get("message")
            if status == "completed":
                data["deployment_gap_results"] = payload.get("deployment_gap_results") or []
            gap.gapAnalysis = data

    async def on_message(event: str, payload: dict[str, Any]) -> None:
        try:
            db_status = STATUS_MAP.get(payload.get("status"), payload.get("status"))
            if event in ("connected", "gap_started", "gap_processing"):
                await _update_gap(db_status, payload)
            elif event == "gap_completed":
                await _update_gap("completed", payload)
                raise _CloseConnection()
            elif event == "gap_failed":
                await _update_gap("failed", payload)
                raise _CloseConnection()
        except _CloseConnection:
            raise
        except Exception as exc:
            logger.error("[Gap WS] Error handling message: %s", exc)

    await _run_with_close_guard(url, on_message)

    try:
        async with session_scope() as session:
            framework = await session.get(DeploymentFramework, str(deployment_framework_id))
            packages = coerce_packages(framework.packages if framework else [])
            pkg = next((p for p in packages if p.packageVersion == package_version), None)
            if pkg and pkg.gapAnalysis:
                gap = await session.get(PackageGapAnalysis, str(pkg.gapAnalysis))
                if gap and _blob_get(gap.gapAnalysis, "status") not in ("completed", "failed"):
                    data = dict(gap.gapAnalysis or {})
                    data["status"] = "failed"
                    data["message"] = "WebSocket disconnected unexpectedly"
                    gap.gapAnalysis = data
    except Exception as exc:
        logger.error("[Gap WS] Error updating failed status on close: %s", exc)


class _CloseConnection(Exception):
    """Raised by a message handler to signal the socket should be closed."""


async def _run_with_close_guard(url: str, on_message) -> None:
    try:
        async with websockets.connect(url, open_timeout=10) as ws:
            async for raw in ws:
                try:
                    parsed = json.loads(raw)
                except (ValueError, TypeError):
                    logger.warning("Received non-JSON WebSocket message: %s", raw)
                    continue
                event = parsed.get("event")
                payload = parsed.get("data")
                if not event or not payload:
                    continue
                try:
                    await on_message(event, payload)
                except _CloseConnection:
                    return
    except Exception as exc:
        logger.error("Analysis WebSocket connection error: %s", exc)


# ─── Orchestration ──────────────────────────────────────────────────────────


async def run_analysis(deployment_framework_id: str, package_version: str) -> None:
    from vora_shared.models import DeploymentFramework, PackageComparison, PackageMerge

    try:
        await start_merge(deployment_framework_id, package_version)

        async with session_scope() as session:
            fresh_framework = await session.get(DeploymentFramework, str(deployment_framework_id))
            packages = coerce_packages(fresh_framework.packages if fresh_framework else [])
            fresh_package = next((p for p in packages if p.packageVersion == package_version), None)
            merge_status = None
            if fresh_package and fresh_package.mergeDocument:
                merge = await session.get(PackageMerge, str(fresh_package.mergeDocument))
                merge_status = _blob_get(merge.mergeExtraction if merge else None, "status")

        if merge_status != "merged":
            logger.warning(
                "[Analysis] Merge did not complete successfully (status: %s). Skipping comparison and gap analysis.",
                merge_status,
            )
            return

        await start_comparison(deployment_framework_id, package_version)

        async with session_scope() as session:
            fresh_framework = await session.get(DeploymentFramework, str(deployment_framework_id))
            packages = coerce_packages(fresh_framework.packages if fresh_framework else [])
            fresh_package = next((p for p in packages if p.packageVersion == package_version), None)
            comparison_status = None
            if fresh_package and fresh_package.comparison:
                comparison = await session.get(PackageComparison, str(fresh_package.comparison))
                comparison_status = _blob_get(comparison.comparison if comparison else None, "status")

        if comparison_status != "completed":
            logger.warning(
                "[Analysis] Comparison did not complete successfully (status: %s). Skipping gap analysis.",
                comparison_status,
            )
            return

        await start_gap_analysis(deployment_framework_id, package_version)
    except Exception as exc:
        logger.error("[Analysis] Error running analysis chain: %s", exc)
