"""Port of deployment-framework-service-main/src/services/package-builder.service.js.

Works with plain dicts shaped like the `PackageVersion` / `FrameworkPackageDocument`
Pydantic models; callers dump nested models to JSONB-friendly dicts before persisting.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.services import version_service
from vora_shared.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _g(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def get_ai_extraction_ref(ai_extraction: Any) -> Any:
    if not ai_extraction:
        return None
    return ai_extraction


def create_package(
    package_version: str,
    *,
    type: str = "pre-release",
    trigger: str = "Package update",
    status: str = "pending",
    documents: list[dict] | None = None,
    gap_analysis: Any = None,
    comparison: Any = None,
    expert_review: dict | None = None,
) -> dict[str, Any]:
    pkg: dict[str, Any] = {
        "packageVersion": package_version,
        "type": type,
        "trigger": trigger,
        "status": status,
        "documents": documents or [],
        "createdAt": _utcnow(),
        "updatedAt": _utcnow(),
    }
    if gap_analysis is not None:
        pkg["gapAnalysis"] = gap_analysis
    if comparison is not None:
        pkg["comparison"] = comparison
    if expert_review is not None:
        pkg["expertReview"] = expert_review
    return pkg


def _find_document_history(framework: Any, original_file_name: str) -> list[Any]:
    """Flat list of every prior document with the same original filename, across all packages."""
    return [
        doc
        for pkg in (framework.packages or [])
        for doc in (_g(pkg, "documents") or [])
        if _g(doc, "originalFileName") == original_file_name
    ]


def _occurrence_based_version(document_history: list[Any]) -> str:
    """Bump the version once per prior occurrence of this filename."""
    version = _g(document_history[0], "fileVersion") or "1.0.0"
    try:
        version_service.parse_version(version)
    except ValueError:
        version = "1.0.0"
    for _ in document_history[1:]:
        version = version_service.increment_file_patch(version)
    return version


def _latest_document_version(document_history: list[Any]) -> str:
    """Highest valid semver among prior fileVersions, defaulting to '1.0.0'."""
    latest = "1.0.0"
    for doc in document_history:
        ver = _g(doc, "fileVersion") or "1.0.0"
        try:
            version_service.parse_version(ver)
            if version_service.compare_versions(ver, latest) > 0:
                latest = ver
        except ValueError:
            pass
    return latest


def resolve_document_file_version(framework: Any, document_data: dict[str, Any]) -> str:
    original_file_name = document_data.get("originalFileName")
    file_hash = document_data.get("fileHash")

    if not original_file_name or not file_hash:
        return document_data.get("fileVersion") or "1.0.0"

    document_history = _find_document_history(framework, original_file_name)
    if not document_history:
        return "1.0.0"

    occurrence_version = _occurrence_based_version(document_history)
    latest_version = _latest_document_version(document_history)

    base_version = (
        latest_version
        if version_service.compare_versions(latest_version, occurrence_version) >= 0
        else occurrence_version
    )

    return version_service.increment_file_patch(base_version)


def _version_sort_key(v: str) -> tuple[int, int, int]:
    try:
        parsed = version_service.parse_version(v)
        return (parsed["major"], parsed["minor"], parsed["patch"])
    except ValueError:
        return (0, 0, 0)


def replicate_documents(
    source_documents: list[Any], updates: list[dict] | None = None, framework: Any = None
) -> list[dict[str, Any]]:
    updates = updates or []

    replicated_docs = []
    for doc in source_documents:
        latest_version = resolve_document_file_version(
            framework if framework is not None else _FakeFramework(source_documents),
            {"originalFileName": _g(doc, "originalFileName"), "fileHash": _g(doc, "fileHash")},
        )
        file_id = _g(doc, "fileId")
        replicated_docs.append(
            {
                "fileId": str(file_id) if file_id is not None else None,
                "fileVersion": latest_version,
                "originalFileName": _g(doc, "originalFileName"),
                "fileSize": _g(doc, "fileSize"),
                "fileHash": _g(doc, "fileHash"),
                "fileType": _g(doc, "fileType"),
                "fileUrl": _g(doc, "fileUrl"),
                "aiExtraction": get_ai_extraction_ref(_g(doc, "aiExtraction")),
                "replicated": True,
                "uploadedAt": _g(doc, "uploadedAt") or _utcnow(),
            }
        )

    return apply_document_updates(replicated_docs, updates)


class _FakeFramework:
    """Mirrors Node's `framework || { packages: [{ documents: sourceDocuments }] }` fallback."""

    def __init__(self, source_documents):
        self.packages = [_FakePackage(source_documents)]


class _FakePackage:
    def __init__(self, documents):
        self.documents = documents


def matches_update(doc: dict[str, Any], update: dict[str, Any]) -> bool:
    if update.get("fileId"):
        return str(doc.get("fileId")) == str(update["fileId"])
    return bool(update.get("originalFileName") and doc.get("originalFileName") == update["originalFileName"])


def create_document_from_update(update: dict[str, Any]) -> dict[str, Any]:
    return {
        "fileId": update.get("fileId") or new_id(),
        "fileVersion": update.get("fileVersion") or "1.0.0",
        "originalFileName": update.get("originalFileName"),
        "fileSize": update.get("fileSize"),
        "fileHash": update.get("fileHash"),
        "fileType": update.get("fileType"),
        "fileUrl": update.get("fileUrl"),
        "aiExtraction": get_ai_extraction_ref(update.get("aiExtraction")),
        "replicated": update.get("replicated") or False,
        "uploadedAt": update.get("uploadedAt") or _utcnow(),
    }


def apply_add_update(docs: list[dict], update: dict[str, Any]) -> list[dict]:
    existing_index = next(
        (
            i
            for i, doc in enumerate(docs)
            if update.get("originalFileName") and doc.get("originalFileName") == update["originalFileName"]
        ),
        -1,
    )
    updated_doc = create_document_from_update(update)
    if existing_index == -1:
        return [*docs, updated_doc]
    result = list(docs)
    result[existing_index] = updated_doc
    return result


def apply_replace_update(doc: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    if not matches_update(doc, update):
        return doc
    updated_doc = create_document_from_update(update)
    for field in ("fileUrl", "fileHash", "originalFileName", "fileType", "fileSize"):
        if not updated_doc.get(field) and doc.get(field):
            updated_doc[field] = doc[field]
    return updated_doc


def apply_document_updates(base_documents: list[dict], updates: list[dict] | None) -> list[dict]:
    if not updates:
        return base_documents

    result = list(base_documents)
    for update in updates:
        action = "remove" if update.get("action") == "delete" else update.get("action")
        if action == "add":
            result = apply_add_update(result, update)
        elif action == "replace":
            result = [apply_replace_update(doc, update) for doc in result]
        elif action == "remove":
            result = [doc for doc in result if not matches_update(doc, update)]
    return result


def create_document_from_file(
    file_bytes: bytes, filename: str, package_version: str = "1.0.0"
) -> dict[str, Any]:
    extension = (filename or "").rsplit(".", 1)[-1].lower()
    mime_map_ext = {"pdf": "pdf", "doc": "doc", "docx": "docx"}
    file_type = mime_map_ext.get(extension, "doc")

    file_hash = hashlib.sha256(file_bytes or b"").hexdigest()

    return {
        "fileId": new_id(),
        "fileVersion": package_version,
        "originalFileName": filename,
        "fileSize": len(file_bytes or b""),
        "fileHash": file_hash,
        "fileType": file_type,
        "fileUrl": "",
        "aiExtraction": None,
        "replicated": False,
        "uploadedAt": _utcnow(),
    }


def get_current_package(framework: Any) -> Any | None:
    if not framework or not getattr(framework, "packages", None) or not framework.currentPackageVersion:
        return None
    return next(
        (pkg for pkg in framework.packages if _g(pkg, "packageVersion") == framework.currentPackageVersion),
        None,
    )


def build_minor_patch(framework: Any, new_files: list[dict], document_updates: list[dict]) -> dict[str, Any]:
    """new_files: list of {"filename": str, "content": bytes}."""
    current_package = get_current_package(framework)
    if not current_package:
        raise ValueError("No current package found for minor patch")

    new_version = version_service.increment_minor_patch(framework.currentPackageVersion)

    replicated_docs = replicate_documents(_g(current_package, "documents") or [], document_updates, framework)

    handled_names = {
        u.get("originalFileName")
        for u in document_updates
        if u.get("action") in ("add", "replace") and u.get("originalFileName")
    }
    new_docs = [
        create_document_from_file(f["content"], f["filename"], new_version)
        for f in new_files
        if f["filename"] not in handled_names
    ]

    all_documents = [*replicated_docs, *new_docs]

    new_package = create_package(
        new_version, type="pre-release", trigger="Minor patch update", documents=all_documents
    )

    return {"newPackage": new_package}


def build_major_patch(framework: Any, new_files: list[dict], document_updates: list[dict]) -> dict[str, Any]:
    new_version = version_service.increment_major_patch(framework.currentPackageVersion)

    updated_docs = apply_document_updates([], document_updates)

    update_file_names = {
        u.get("originalFileName")
        for u in (document_updates or [])
        if u.get("action") in ("add", "replace") and u.get("originalFileName")
    }
    new_docs = [
        create_document_from_file(f["content"], f["filename"], new_version)
        for f in (new_files or [])
        if f["filename"] not in update_file_names
    ]

    all_documents = [*updated_docs, *new_docs]

    new_package = create_package(
        new_version, type="pre-release", trigger="Major patch update", documents=all_documents
    )

    return {"newPackage": new_package}


def _validate_package_documents(documents: Any, errors: list[str]) -> None:
    if isinstance(documents, list):
        for index, doc in enumerate(documents):
            if not doc.get("fileId"):
                errors.append(f"Document {index + 1}: fileId is required")
            if not doc.get("originalFileName"):
                errors.append(f"Document {index + 1}: originalFileName is required")
            if not doc.get("fileType"):
                errors.append(f"Document {index + 1}: fileType is required")
    else:
        errors.append("Documents must be an array")


def validate_package(package_data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if not package_data.get("packageVersion"):
        errors.append("Package version is required")
    else:
        try:
            version_service.is_valid_version(package_data["packageVersion"])
        except ValueError:
            errors.append("Invalid package version format")

    if not package_data.get("type"):
        errors.append("Package type is required")

    _validate_package_documents(package_data.get("documents"), errors)

    return {"isValid": len(errors) == 0, "errors": errors}
