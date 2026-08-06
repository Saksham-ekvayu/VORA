"""Port of deployment-framework-service-main/src/helpers/deployment-framework.helpers.js.

RabbitMQ event publishing functions have been dropped per the porting rules.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import package_builder, version_service
from fastapi import UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from vora_shared import file_storage
from vora_shared.ids import new_id
from vora_shared.models.deployment_framework import FrameworkPackageDocument, PackageVersion


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _g(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def dump_model(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [dump_model(x) for x in obj]
    if isinstance(obj, dict):
        return {k: dump_model(v) for k, v in obj.items()}
    return obj


def coerce_packages(packages: list[Any] | None) -> list[PackageVersion]:
    result: list[PackageVersion] = []
    for p in packages or []:
        if isinstance(p, PackageVersion):
            result.append(p)
        else:
            result.append(PackageVersion.model_validate(p))
    return result


def dump_packages(packages: list[Any] | None) -> list[dict[str, Any]]:
    return [dump_model(p) for p in (packages or [])]


def coerce_documents(documents: list[Any] | None) -> list[FrameworkPackageDocument]:
    result: list[FrameworkPackageDocument] = []
    for d in documents or []:
        if isinstance(d, FrameworkPackageDocument):
            result.append(d)
        else:
            result.append(FrameworkPackageDocument.model_validate(d))
    return result


def normalize_document_action(action: str | None) -> str | None:
    normalized = str(action or "").lower().strip()
    if normalized == "delete":
        return "remove"
    if normalized in ("replicate", "replace", "add", "remove"):
        return normalized
    return None


def parse_document_updates(raw_documents: list[dict] | None) -> list[dict]:
    if not raw_documents:
        return []
    result = []
    for doc in raw_documents:
        action = normalize_document_action(doc.get("action"))
        if not action:
            continue
        ai_extraction = doc.get("aiExtraction")
        if isinstance(ai_extraction, dict):
            ai_extraction = ai_extraction.get("_id") or ai_extraction.get("id")
        result.append(
            {
                "action": action,
                "fileId": doc.get("fileId"),
                "originalFileName": doc.get("originalFileName"),
                "fileSize": doc.get("fileSize"),
                "fileType": file_storage.normalize_file_type(
                    doc.get("fileType"), doc.get("originalFileName")
                ),
                "fileVersion": doc.get("fileVersion"),
                "fileUrl": doc.get("fileUrl"),
                "fileHash": doc.get("fileHash"),
                "aiExtraction": ai_extraction,
                "replicated": doc.get("replicated"),
            }
        )
    return result


def get_current_package(framework: Any):
    if not framework or not framework.packages:
        return None
    packages = coerce_packages(framework.packages)
    return next(
        (p for p in packages if p.packageVersion == framework.currentPackageVersion),
        packages[0] if packages else None,
    )


def get_upload_file_path(file_url: str | None) -> str | None:
    if not file_url or file_url.startswith("/api/"):
        return None
    relative = (
        file_url.replace("/uploads/", "", 1) if file_url.startswith("/uploads/") else file_url.lstrip("/")
    )
    return str((Path(file_storage.UPLOAD_BASE_PATH) / relative).resolve())


def find_framework_document(framework: Any, file_id: str):
    for pkg in coerce_packages(framework.packages):
        for doc in pkg.documents or []:
            if str(doc.fileId) == str(file_id):
                return doc
    return None


async def create_pending_extraction(session: AsyncSession, file_hash: str | None):
    from vora_shared.models import DocumentExtraction

    if not file_hash:
        return None
    existing = (
        await session.execute(select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash))
    ).scalar_one_or_none()
    if existing:
        return existing
    extraction = DocumentExtraction(fileHash=file_hash, aiExtraction={})
    session.add(extraction)
    await session.flush()
    return extraction


async def ensure_document_extraction_ref(session: AsyncSession, doc: Any):
    from vora_shared.models import DocumentExtraction
    from vora_shared.models.document_extraction import AiExtractionInfo

    if not doc:
        return None

    ai_ref = _g(doc, "aiExtraction")
    if ai_ref:
        existing = await session.get(DocumentExtraction, str(ai_ref))
        if existing:
            return existing.id
        if isinstance(doc, dict):
            doc["aiExtraction"] = None
        else:
            doc.aiExtraction = None

    extraction = await create_pending_extraction(session, _g(doc, "fileHash"))
    if not extraction:
        return None

    if isinstance(doc, dict):
        doc["aiExtraction"] = extraction.id
    else:
        doc.aiExtraction = extraction.id

    ai = AiExtractionInfo.model_validate(extraction.aiExtraction or {})
    if ai.status == "extracted":
        if isinstance(doc, dict):
            doc["replicated"] = True
        else:
            doc.replicated = True
    return extraction.id


async def ensure_document_extraction_refs(session: AsyncSession, documents: list[Any]) -> list[Any]:
    for doc in documents or []:
        await ensure_document_extraction_ref(session, doc)
    return documents


def get_latest_package(packages: list[Any]) -> Any | None:
    if not packages:
        return None
    coerced = coerce_packages(packages)
    return max(
        coerced,
        key=lambda p: _version_sort_key(p.packageVersion),
    )


def _version_sort_key(v: str) -> tuple[int, int, int]:
    try:
        parsed = version_service.parse_version(v)
        return (parsed["major"], parsed["minor"], parsed["patch"])
    except ValueError:
        return (0, 0, 0)


def process_and_save_file(content: bytes, filename: str, user_id: str, version: str) -> dict[str, Any] | None:
    path_info = file_storage.generate_deployment_file_path(filename, user_id, "deployment-framework", version)

    if not file_storage.save_file(content, path_info.absolute_path):
        return None

    file_hash = file_storage.calculate_file_hash(path_info.absolute_path)

    return {
        "fileId": new_id(),
        "fileVersion": version,
        "fileUrl": f"/uploads/{path_info.relative_path.replace(chr(92), '/')}",
        "fileHash": file_hash,
        "originalFileName": filename,
        "fileSize": len(content),
        "fileType": filename.rsplit(".", 1)[-1].lower(),
        "aiExtraction": None,
        "replicated": False,
        "uploadedAt": _utcnow(),
    }


async def process_uploaded_files(files: list[UploadFile], user_id: str, version: str) -> dict[str, Any]:
    document_data_array = []
    for file in files:
        content = await file.read()

        document_data = process_and_save_file(content, file.filename or "file", user_id, version)
        if not document_data:
            return {"error": {"message": f"Failed to save file: {file.filename}", "status": 500}}
        document_data_array.append(document_data)
    return {"documentDataArray": document_data_array}


def save_uploaded_files_for_package(
    framework: Any, uploaded_files_map: dict[str, bytes], result: dict[str, Any], user_id: str
) -> dict[str, Any]:
    if not uploaded_files_map:
        return {"success": True}

    remaining = dict(uploaded_files_map)
    version = framework.frameworkVersion if hasattr(framework, "frameworkVersion") else None

    for doc in result["newPackage"]["documents"]:
        if not doc.get("replicated"):
            content = remaining.get(doc["originalFileName"])
            if content is not None:
                path_info = file_storage.generate_deployment_file_path(
                    doc["originalFileName"], user_id, "deployment-framework", version
                )
                if not file_storage.save_file(content, path_info.absolute_path):
                    return {"error": True, "filename": doc["originalFileName"]}

                doc["fileHash"] = file_storage.calculate_file_hash(path_info.absolute_path)
                doc["fileUrl"] = f"/uploads/{path_info.relative_path.replace(chr(92), '/')}"
                doc["fileVersion"] = package_builder.resolve_document_file_version(framework, doc)

                remaining.pop(doc["originalFileName"], None)
    return {"success": True}


async def check_existing_framework(
    session: AsyncSession,
    tenant_id: str,
    framework_version: str | None,
    framework_id: str | None,
    framework_code: str | None,
):
    from vora_shared.models import DeploymentFramework

    if not (framework_id or framework_code) or not framework_version:
        return None

    conditions = []
    if framework_id:
        conditions.append(DeploymentFramework.frameworkId == framework_id)
    if framework_code:
        conditions.append(DeploymentFramework.frameworkCode == framework_code)

    stmt = select(DeploymentFramework).where(
        DeploymentFramework.tenantId == tenant_id,
        DeploymentFramework.frameworkVersion == framework_version,
        or_(*conditions),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


def _field(doc: Any, key: str, default: Any = None) -> Any:
    """Reads `key` from `doc`, whether it's a dict or a Pydantic model instance."""
    return _g(doc, key, default)


async def create_pending_merge(
    session: AsyncSession, file_hashes: list[str], framework_id: str, package_data: dict[str, Any]
):
    from vora_shared.models import PackageMerge

    if not file_hashes or not framework_id:
        return None
    existing = (
        await session.execute(
            select(PackageMerge).where(
                PackageMerge.fileHashes == file_hashes,
                PackageMerge.frameworkId == str(framework_id),
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    source_documents = [
        {
            "fileId": str(_field(doc, "fileId")) if _field(doc, "fileId") is not None else None,
            "fileHash": _field(doc, "fileHash"),
            "originalFileName": _field(doc, "originalFileName"),
            "mergedAt": None,
        }
        for doc in package_data.get("documents", [])
    ]

    merge = PackageMerge(
        frameworkId=str(framework_id),
        fileHashes=file_hashes,
        sourceDocuments=source_documents,
        mergeExtraction={},
    )
    session.add(merge)
    await session.flush()
    return merge


async def create_pending_comparison(session: AsyncSession, file_hashes: list[str], framework_id: str):
    from vora_shared.models import PackageComparison

    if not file_hashes or not framework_id:
        return None
    existing = (
        await session.execute(
            select(PackageComparison).where(
                PackageComparison.fileHashes == file_hashes,
                PackageComparison.frameworkId == str(framework_id),
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    comparison = PackageComparison(
        frameworkId=str(framework_id),
        fileHashes=file_hashes,
        comparison={},
    )
    session.add(comparison)
    await session.flush()
    return comparison


async def create_pending_gap_analysis(session: AsyncSession, file_hashes: list[str], framework_id: str):
    from vora_shared.models import PackageGapAnalysis

    if not file_hashes or not framework_id:
        return None
    existing = (
        await session.execute(
            select(PackageGapAnalysis).where(
                PackageGapAnalysis.fileHashes == file_hashes,
                PackageGapAnalysis.frameworkId == str(framework_id),
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    gap = PackageGapAnalysis(
        frameworkId=str(framework_id),
        fileHashes=file_hashes,
        gapAnalysis={},
    )
    session.add(gap)
    await session.flush()
    return gap


async def ensure_package_analysis_refs(
    session: AsyncSession, package_data: dict[str, Any], framework_id: str
) -> None:
    if not package_data or not framework_id:
        return
    file_hashes = sorted(
        {_field(doc, "fileHash") for doc in package_data.get("documents", []) if _field(doc, "fileHash")}
    )
    if not file_hashes:
        return

    merge_doc = await create_pending_merge(session, file_hashes, framework_id, package_data)
    if merge_doc:
        package_data["mergeDocument"] = merge_doc.id

    comparison_doc = await create_pending_comparison(session, file_hashes, framework_id)
    if comparison_doc:
        package_data["comparison"] = comparison_doc.id

    gap_doc = await create_pending_gap_analysis(session, file_hashes, framework_id)
    if gap_doc:
        package_data["gapAnalysis"] = gap_doc.id


def gap_point_matches(
    p: dict[str, Any],
    assigned_point_id: Any,
    deployment_control_id: Any,
    deployment_point_id: Any | None,
) -> bool:
    if str((p.get("assigned_framework_deployment_points") or {}).get("id")) != str(assigned_point_id):
        return False
    if p.get("deployment_framework_control_id") != deployment_control_id:
        return False
    if deployment_point_id and str((p.get("deployment_framework_deployment_points") or {}).get("id")) != str(
        deployment_point_id
    ):
        return False
    return True


def find_gap_point(
    results: list[dict[str, Any]],
    assigned_control_id: str,
    assigned_point_id: Any,
    deployment_control_id: Any,
    deployment_point_id: Any | None,
) -> dict[str, Any] | None:
    all_points = []
    for section in results or []:
        for control_obj in section.get("controls") or []:
            rows = control_obj.get(assigned_control_id)
            if isinstance(rows, list):
                all_points.extend(rows)

    return next(
        (
            p
            for p in all_points
            if gap_point_matches(p, assigned_point_id, deployment_control_id, deployment_point_id)
        ),
        None,
    )


def update_gap_review_comment(
    results: list[dict[str, Any]],
    assigned_control_id: str,
    assigned_point_id: Any,
    deployment_control_id: Any,
    deployment_point_id: Any | None,
    comment: str | None,
) -> bool:
    point = find_gap_point(
        results, assigned_control_id, assigned_point_id, deployment_control_id, deployment_point_id
    )
    if not point:
        return False
    point["reviewComment"] = comment or ""
    return True
