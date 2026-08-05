"""Port of deployment-framework-service-main/src/services/data-formatter.service.js.

Nested JSONB refs are plain string ids. Callers pass pre-fetched maps
(str(id) -> document). Use `hydrate_maps()` to build these maps in bulk.
"""

import math
from typing import Any

from app.helpers.deployment_framework_helpers import coerce_packages
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from vora_shared import data_format
from vora_shared.models import (
    DeploymentFramework,
    DocumentExtraction,
    FrameworkPackageDocument,
    PackageComparison,
    PackageGapAnalysis,
    PackageMerge,
    PackageVersion,
    User,
)
from vora_shared.models.document_extraction import AiExtractionInfo


async def hydrate_maps(
    session: AsyncSession, frameworks: list[DeploymentFramework]
) -> dict[str, dict[str, Any]]:
    """Batch-fetches every referenced User/DocumentExtraction/Comparison/Gap/Merge
    document for a list of frameworks and returns id-keyed lookup maps."""

    user_ids: set[str] = set()
    extraction_ids: set[str] = set()
    comparison_ids: set[str] = set()
    gap_ids: set[str] = set()
    merge_ids: set[str] = set()
    assigned_framework_ids: set[str] = set()

    for fw in frameworks:
        if fw.uploadedBy:
            user_ids.add(str(fw.uploadedBy))
        if fw.assignedFrameworkId:
            assigned_framework_ids.add(str(fw.assignedFrameworkId))
        for pkg in coerce_packages(fw.packages):
            if pkg.expertReview and pkg.expertReview.assignedExpert:
                user_ids.add(str(pkg.expertReview.assignedExpert))
            if pkg.comparison:
                comparison_ids.add(str(pkg.comparison))
            if pkg.gapAnalysis:
                gap_ids.add(str(pkg.gapAnalysis))
            if pkg.mergeDocument:
                merge_ids.add(str(pkg.mergeDocument))
            for doc in pkg.documents or []:
                if doc.aiExtraction:
                    extraction_ids.add(str(doc.aiExtraction))

    async def _fetch(model, ids):
        if not ids:
            return {}
        docs = (await session.execute(select(model).where(model.id.in_(list(ids))))).scalars().all()
        return {str(d.id): d for d in docs}

    users = await _fetch(User, user_ids)
    extractions = await _fetch(DocumentExtraction, extraction_ids)
    comparisons = await _fetch(PackageComparison, comparison_ids)
    gaps = await _fetch(PackageGapAnalysis, gap_ids)
    merges = await _fetch(PackageMerge, merge_ids)
    assigned_frameworks = await _fetch(DeploymentFramework, assigned_framework_ids)

    return {
        "users": users,
        "extractions": extractions,
        "comparisons": comparisons,
        "gaps": gaps,
        "merges": merges,
        "assignedFrameworks": assigned_frameworks,
    }


def format_uploaded_by(framework: Any, users: dict[str, User]) -> dict[str, Any]:
    user = users.get(str(framework.uploadedBy)) if framework.uploadedBy else None
    return data_format.format_user_ref(user, framework.uploadedBy)


def format_expert_review(expert_review: Any | None, users: dict[str, User]) -> dict[str, Any] | None:
    if not expert_review:
        return None
    expert = users.get(str(expert_review.assignedExpert)) if expert_review.assignedExpert else None
    return {
        "status": expert_review.status,
        "assignedExpert": data_format.format_user_ref(expert) if expert else None,
        "requestedAt": expert_review.requestedAt,
        "reviewedAt": expert_review.reviewedAt,
        "comments": expert_review.comments,
    }


def _as_ai(raw: Any) -> AiExtractionInfo | None:
    if not raw:
        return None
    if isinstance(raw, AiExtractionInfo):
        return raw
    if isinstance(raw, dict):
        return AiExtractionInfo.model_validate(raw)
    return None


def format_document(
    doc: FrameworkPackageDocument | dict,
    extractions: dict[str, DocumentExtraction],
    exclude_details: bool = False,
) -> dict[str, Any] | None:
    if not doc:
        return None
    if isinstance(doc, dict):
        doc = FrameworkPackageDocument.model_validate(doc)
    extraction = extractions.get(str(doc.aiExtraction)) if doc.aiExtraction else None
    ai = _as_ai(extraction.aiExtraction) if extraction else None

    return {
        "fileId": str(doc.fileId) if doc and getattr(doc, "fileId", None) else None,
        "fileUrl": doc.fileUrl,
        "fileHash": doc.fileHash,
        "originalFileName": doc.originalFileName,
        "fileSize": doc.fileSize,
        "fileType": doc.fileType,
        "fileVersion": doc.fileVersion,
        "aiExtraction": (
            {
                "status": ai.status,
                "timestamp": ai.timestamp,
                "message": ai.message,
                **({} if exclude_details else {"statusHistory": ai.statusHistory, "controls": ai.controls}),
            }
            if ai
            else None
        ),
        "replicated": doc.replicated,
        "uploadedAt": doc.uploadedAt,
    }


def _json_status(blob: Any, key: str = "status") -> Any:
    if blob is None:
        return None
    if isinstance(blob, dict):
        return blob.get(key)
    return getattr(blob, key, None)


def format_package(
    pkg: PackageVersion | dict, maps: dict[str, dict[str, Any]], exclude_details: bool = False
) -> dict[str, Any] | None:
    if not pkg:
        return None
    if isinstance(pkg, dict):
        pkg = PackageVersion.model_validate(pkg)

    extractions = maps.get("extractions", {})
    users = maps.get("users", {})
    comparison = maps.get("comparisons", {}).get(str(pkg.comparison)) if pkg.comparison else None
    gap = maps.get("gaps", {}).get(str(pkg.gapAnalysis)) if pkg.gapAnalysis else None
    merge = maps.get("merges", {}).get(str(pkg.mergeDocument)) if pkg.mergeDocument else None

    comp_data = comparison.comparison if comparison else None
    gap_data = gap.gapAnalysis if gap else None
    merge_data = merge.mergeExtraction if merge else None

    def _get(blob, key, default=None):
        if blob is None:
            return default
        if isinstance(blob, dict):
            return blob.get(key, default)
        return getattr(blob, key, default)

    return {
        "packageVersion": pkg.packageVersion,
        "type": pkg.type,
        "trigger": pkg.trigger,
        "status": pkg.status,
        "documents": [format_document(doc, extractions, exclude_details) for doc in (pkg.documents or [])],
        "gapAnalysis": (
            {
                "status": _get(gap_data, "status"),
                "message": _get(gap_data, "message"),
                "timestamp": _get(gap_data, "timestamp"),
                **(
                    {}
                    if exclude_details
                    else {"deployment_gap_results": _get(gap_data, "deployment_gap_results") or []}
                ),
            }
            if gap_data
            else {
                "status": "pending",
                "message": None,
                "timestamp": None,
                **({} if exclude_details else {"deployment_gap_results": []}),
            }
        ),
        "comparison": (
            {
                "status": _get(comp_data, "status"),
                "message": _get(comp_data, "message"),
                "timestamp": _get(comp_data, "timestamp"),
                "comparison_time_seconds": _get(comp_data, "comparison_time_seconds"),
                **(
                    {}
                    if exclude_details
                    else {"comparison_result": _get(comp_data, "comparison_result") or []}
                ),
            }
            if comp_data
            else {
                "status": "pending",
                "message": None,
                "timestamp": None,
                "comparison_time_seconds": None,
                **({} if exclude_details else {"comparison_result": []}),
            }
        ),
        "mergeDocument": (
            {
                "status": _get(merge_data, "status"),
                "message": _get(merge_data, "message"),
                "timestamp": _get(merge_data, "timestamp"),
                **(
                    {}
                    if exclude_details
                    else {
                        "controls_data": _get(merge_data, "controls_data") or [],
                        "sourceDocuments": (merge.sourceDocuments if merge else []) or [],
                    }
                ),
            }
            if merge_data
            else {
                "status": "pending",
                "message": None,
                "timestamp": None,
                **({} if exclude_details else {"controls_data": [], "sourceDocuments": []}),
            }
        ),
        "expertReview": format_expert_review(pkg.expertReview, users),
        "createdAt": pkg.createdAt,
        "updatedAt": pkg.updatedAt,
    }


def format_deployment_framework(
    framework: Any, maps: dict[str, dict[str, Any]], exclude_details: bool = False
) -> dict[str, Any]:
    packages = coerce_packages(framework.packages)
    formatted_packages = [format_package(pkg, maps, exclude_details) for pkg in packages]
    formatted_packages.reverse()

    assigned_framework = (
        maps.get("assignedFrameworks", {}).get(str(framework.assignedFrameworkId))
        if framework.assignedFrameworkId
        else None
    )

    return {
        "id": str(framework.id) if framework and getattr(framework, "id", None) else None,
        "tenantId": str(framework.tenantId) if framework and getattr(framework, "tenantId", None) else None,
        "frameworkName": framework.frameworkName,
        "frameworkId": (
            str(framework.frameworkId) if framework and getattr(framework, "frameworkId", None) else None
        ),
        "frameworkCode": framework.frameworkCode,
        "frameworkVersion": framework.frameworkVersion,
        "currentPackageVersion": framework.currentPackageVersion,
        "packages": formatted_packages,
        "uploadedBy": format_uploaded_by(framework, maps.get("users", {})),
        "assignedFramework": (
            {
                "id": (
                    str(assigned_framework.id)
                    if assigned_framework and getattr(assigned_framework, "id", None)
                    else None
                ),
                "frameworkName": assigned_framework.frameworkName,
                "frameworkCode": assigned_framework.frameworkCode,
                "frameworkVersion": assigned_framework.frameworkVersion,
            }
            if assigned_framework
            else {}
        ),
        "createdAt": framework.createdAt,
        "updatedAt": framework.updatedAt,
    }


def derive_package_ai_extraction(
    current_package: PackageVersion | None, extractions: dict[str, DocumentExtraction]
) -> dict[str, Any] | None:
    docs = (current_package.documents if current_package else None) or []
    if not docs:
        return None

    resolved = [
        extractions[str(doc.aiExtraction)]
        for doc in docs
        if doc.aiExtraction and str(doc.aiExtraction) in extractions
    ]
    if not resolved:
        return None

    statuses = []
    for e in resolved:
        ai = _as_ai(e.aiExtraction)
        if ai and ai.status:
            statuses.append(str(ai.status).lower())

    status = "pending"
    if "failed" in statuses:
        status = "failed"
    elif "processing" in statuses:
        status = "processing"
    elif "uploaded" in statuses:
        status = "uploaded"
    elif statuses and all(s == "extracted" for s in statuses):
        status = "extracted"
    elif "extracted" in statuses:
        status = "processing"

    timestamps = []
    for e in resolved:
        ai = _as_ai(e.aiExtraction)
        if ai and ai.timestamp:
            timestamps.append(ai.timestamp)
    timestamp = max(timestamps) if timestamps else None

    return {"status": status, "timestamp": timestamp}


def format_deployment_framework_list_item(framework: Any, maps: dict[str, dict[str, Any]]) -> dict[str, Any]:
    packages = coerce_packages(framework.packages)
    current_package = next(
        (p for p in packages if p.packageVersion == framework.currentPackageVersion),
        packages[0] if packages else None,
    )

    type_counts: dict[str, int] = {}
    for doc in (current_package.documents if current_package else None) or []:
        t = doc.fileType or "unknown"
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "id": str(framework.id) if framework and getattr(framework, "id", None) else None,
        "tenantId": str(framework.tenantId) if framework and getattr(framework, "tenantId", None) else None,
        "frameworkName": framework.frameworkName,
        "frameworkId": (
            str(framework.frameworkId) if framework and getattr(framework, "frameworkId", None) else None
        ),
        "frameworkCode": framework.frameworkCode,
        "frameworkVersion": framework.frameworkVersion,
        "currentPackageVersion": framework.currentPackageVersion,
        "document": {
            "count": len(current_package.documents) if current_package else 0,
            "types": [f"{count} {t}" for t, count in type_counts.items()],
        },
        "package": {
            "type": current_package.type if current_package else None,
            "trigger": current_package.trigger if current_package else None,
            "status": current_package.status if current_package else None,
            "packageCount": len(packages),
        },
        "requestReview": format_expert_review(
            current_package.expertReview if current_package else None, maps.get("users", {})
        ),
        "aiExtraction": derive_package_ai_extraction(current_package, maps.get("extractions", {})),
        "uploadedBy": format_uploaded_by(framework, maps.get("users", {})),
        "createdAt": framework.createdAt,
    }
