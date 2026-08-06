"""Load-document-service routes — Postgres + HTTP notify (no RabbitMQ / Mongo)."""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.notifier import notify_compliance_agent
from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm.attributes import flag_modified
from vora_shared.config import get_settings
from vora_shared.database import session_scope
from vora_shared.file_storage import calculate_file_hash
from vora_shared.ids import new_id
from vora_shared.models import (
    Customer,
    DeploymentFramework,
    Framework,
    FrameworkAssignment,
    LoadDocument,
    User,
)
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import error, paginated, success

logger = logging.getLogger(__name__)

router = APIRouter(tags=["load-document"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".doc", ".xls", ".xlsx", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024


def _upload_dir() -> Path:
    settings = get_settings()
    path = Path(os.environ.get("UPLOAD_DIR", getattr(settings, "upload_dir", None) or "uploads"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ext(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def _validate_filename(filename: str | None) -> str | None:
    if not filename:
        return "No file uploaded"
    if _ext(filename) not in ALLOWED_EXTENSIONS:
        return f"Invalid file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    return None


def _safe_unlink(file_url_or_path: str | None) -> None:
    if not file_url_or_path:
        return
    try:
        if file_url_or_path.startswith("/uploads/"):
            fname = file_url_or_path.replace("/uploads/", "", 1)
            path = _upload_dir() / fname
        else:
            path = Path(file_url_or_path)
        if path.exists() and path.is_file():
            path.unlink()
    except OSError as exc:
        logger.warning("Physical file delete failed | path=%s | error=%s", file_url_or_path, exc)


def _bump_semver(version: str | None) -> str:
    try:
        parts = (version or "1.0.0").split(".")
        major = parts[0] if parts else "1"
        minor = int(parts[1]) + 1 if len(parts) > 1 else 1
        patch = parts[2] if len(parts) > 2 else "0"
        return f"{major}.{minor}.{patch}"
    except Exception:
        return "1.1.0"


def _load_doc_to_dict(doc: LoadDocument) -> dict[str, Any]:
    meta = doc.meta or {}
    return {
        "id": doc.id,
        "uuid": doc.id,
        "tenant_id": doc.tenant_id,
        "document_name": doc.document_name,
        "filename": doc.document_name,
        "resourceType": doc.resource_type,
        "file_path": doc.file_path,
        "file_hash": doc.file_hash,
        "file_exists": bool(doc.file_path and Path(doc.file_path).exists()),
        "meta": meta,
        "createdAt": doc.createdAt,
        "updatedAt": doc.updatedAt,
    }


@router.get("/health")
async def health_check():
    return success(
        message="Service is healthy",
        data={"status": "healthy", "service": "load-document-service"},
    )


@router.post("/upload")
async def upload_document(
    id: str = Form(...),
    file: UploadFile = File(...),
    frameworkName: str | None = Form(default=None),
    frameworkId: str | None = Form(default=None),
    frameworkCode: str | None = Form(default=None),
    frameworkVersion: str | None = Form(default=None),
    currentFileVersion: str | None = Form(default=None),
    fileVersions: str | None = Form(default=None),
    source: str = Form(default="local"),
    user_id: str | None = Query(default=None),
    metadata: str | None = Form(default=None),
    tenantId: str | None = Form(default=None),
):
    err = _validate_filename(file.filename)
    if err:
        return error(err, 400)

    parsed_metadata: dict[str, Any] | None = None
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError as exc:
            return error(f"Invalid metadata JSON: {exc}", 400)

    filtered_file_versions: list[dict[str, Any]] = []
    resolved_current = currentFileVersion
    if fileVersions:
        try:
            raw_versions = json.loads(fileVersions)
            if not isinstance(raw_versions, list):
                return error("fileVersions must be a list", 400)
            filtered_file_versions = [
                {"fileVersion": v.get("fileVersion")}
                for v in raw_versions
                if isinstance(v, dict) and v.get("fileVersion")
            ]
            if filtered_file_versions and not resolved_current:
                resolved_current = filtered_file_versions[-1]["fileVersion"]
        except json.JSONDecodeError as exc:
            return error(f"Invalid fileVersions JSON: {exc}", 400)

    upload_dir = _upload_dir()
    safe_name = f"{id}_{file.filename}"
    upload_path = upload_dir / safe_name
    try:
        with upload_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        logger.error("File save failed | error=%s", exc)
        return error("File upload failed", 500)
    finally:
        await file.close()

    file_size = upload_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        upload_path.unlink(missing_ok=True)
        return error("File size too large. Maximum size is 50MB", 400)

    file_hash = calculate_file_hash(upload_path)
    duplicate_id: str | None = None

    async with session_scope() as session:
        if file_hash:
            dup = (
                await session.execute(
                    select(LoadDocument).where(LoadDocument.file_hash == file_hash).limit(1)
                )
            ).scalar_one_or_none()
            if dup and dup.id != id:
                duplicate_id = dup.id

        user_info: dict[str, Any] | None = None
        resolved_tenant = tenantId
        if user_id:
            user = await session.get(User, str(user_id))
            if user:
                resolved_tenant = resolved_tenant or user.tenantId
                user_info = {
                    "user_id": user.id,
                    "tenantId": user.tenantId,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                }

        existing = await session.get(LoadDocument, id)
        meta = {
            "original_filename": file.filename,
            "file_size": file_size,
            "file_type": _ext(file.filename),
            "source": source,
            "user_id": user_id,
            "frameworkName": frameworkName,
            "frameworkId": frameworkId,
            "frameworkCode": frameworkCode,
            "frameworkVersion": frameworkVersion,
            "currentFileVersion": resolved_current,
            "fileVersions": filtered_file_versions,
            "Metadata": parsed_metadata,
        }
        if existing:
            existing.document_name = file.filename or existing.document_name
            existing.resource_type = "deployment-document"
            existing.file_path = str(upload_path)
            existing.file_hash = file_hash
            existing.tenant_id = resolved_tenant
            existing.meta = meta
            flag_modified(existing, "meta")
            doc_id = existing.id
        else:
            row = LoadDocument(
                id=id,
                tenant_id=resolved_tenant,
                document_name=file.filename or id,
                resource_type="deployment-document",
                file_path=str(upload_path),
                file_hash=file_hash,
                meta=meta,
            )
            session.add(row)
            doc_id = id

    notify_payload = {
        "id": doc_id,
        "filename": file.filename,
        "resourceType": "deployment-document",
        "file_size": file_size,
        "filepath": str(upload_path.resolve()),
        "file_path": str(upload_path.resolve()),
        "file_hash": file_hash,
        "status": "uploaded",
        "source": source,
        "frameworkName": frameworkName,
        "frameworkId": frameworkId,
        "frameworkCode": frameworkCode,
        "frameworkVersion": frameworkVersion,
        "currentFileVersion": resolved_current,
        "fileVersions": filtered_file_versions,
        "metadata": parsed_metadata,
        "meta": {
            **(user_info or {}),
            "frameworkName": frameworkName,
            "frameworkId": frameworkId,
            "frameworkCode": frameworkCode,
            "frameworkVersion": frameworkVersion,
            "currentFileVersion": resolved_current,
            "source": source,
        },
    }
    if user_info:
        notify_payload.update(
            {
                "user_id": user_info.get("user_id"),
                "tenantId": user_info.get("tenantId"),
                "user_name": user_info.get("name"),
                "user_email": user_info.get("email"),
                "user_role": user_info.get("role"),
            }
        )
    notify_compliance_agent(notify_payload)

    return success(
        message="File uploaded successfully",
        data={
            "id": doc_id,
            "resourceType": "deployment-document",
            "filename": file.filename,
            "file_hash": file_hash,
            "file_size": file_size,
            "source": source,
            "user_id": user_id,
            "frameworkName": frameworkName,
            "currentFileVersion": resolved_current,
            "fileVersions": filtered_file_versions,
            "is_duplicate": bool(duplicate_id),
            "duplicate_of_id": duplicate_id,
        },
    )


@router.get("/list")
async def list_files(page: int = 1, page_size: int = 10):
    page_num = clamp_page(page)
    limit_num = clamp_limit(page_size)
    async with session_scope() as session:
        total = (await session.execute(select(func.count()).select_from(LoadDocument))).scalar_one()
        rows = (
            (
                await session.execute(
                    select(LoadDocument)
                    .order_by(LoadDocument.createdAt.desc())
                    .offset((page_num - 1) * limit_num)
                    .limit(limit_num)
                )
            )
            .scalars()
            .all()
        )
        data = [_load_doc_to_dict(doc) for doc in rows]
    return paginated(
        data,
        build_pagination_meta(page_num, limit_num, total),
        message=f"Retrieved {len(data)} documents" if data else "No documents found",
    )


@router.delete("/delete/{identifier}")
async def delete_file(identifier: str):
    async with session_scope() as session:
        document = await session.get(LoadDocument, identifier)
        if not document:
            document = (
                await session.execute(
                    select(LoadDocument).where(LoadDocument.document_name == identifier).limit(1)
                )
            ).scalar_one_or_none()
        if not document:
            return error("Document not found", 404)

        file_path = document.file_path
        doc_id = document.id
        await session.delete(document)

    _safe_unlink(file_path)
    return success(
        message="Document deleted successfully",
        data={"status": "deleted", "id": doc_id, "identifier": identifier},
    )


@router.post("/frameworks/upload")
async def upload_framework(
    file: UploadFile = File(...),
    id: str = Form(...),
    frameworkName: str = Form(...),
    frameworkVersion: str = Form(...),
    frameworkCategoryId: str = Form(...),
    frameworkCode: str = Form(...),
    uploadedBy: str = Form(...),
    currentFileVersion: str | None = Form(default=None),
    fileVersions: str | None = Form(default=None),
    approval: str | None = Form(default=None),
):
    err = _validate_filename(file.filename)
    if err:
        return error(err, 400)

    file_id_for_path = id
    raw_fvs: list[Any] | None = None
    if fileVersions:
        try:
            raw_fvs = json.loads(fileVersions)
            if isinstance(raw_fvs, list) and raw_fvs:
                fid = raw_fvs[-1].get("fileId") if isinstance(raw_fvs[-1], dict) else None
                if fid:
                    file_id_for_path = fid
        except json.JSONDecodeError as exc:
            return error(f"Invalid fileVersions JSON: {exc}", 400)

    upload_dir = _upload_dir()
    safe_name = f"{file_id_for_path}_{file.filename}"
    upload_path = upload_dir / safe_name
    try:
        with upload_path.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except Exception as exc:
        logger.error("Framework file save failed | error=%s", exc)
        return error("File upload failed", 500)
    finally:
        await file.close()

    file_size = upload_path.stat().st_size
    file_hash = calculate_file_hash(upload_path)
    file_url = f"/uploads/{safe_name}"
    file_type_ext = _ext(file.filename).lstrip(".")
    if file_type_ext not in ("pdf", "doc", "docx"):
        file_type_ext = "pdf"

    parsed_file_versions: list[dict[str, Any]] = []
    resolved_current = currentFileVersion

    if raw_fvs is not None:
        if not isinstance(raw_fvs, list):
            return error("fileVersions must be a JSON array", 400)
        for idx, item in enumerate(raw_fvs):
            if not isinstance(item, dict):
                return error(f"fileVersions[{idx}] must be an object", 400)
            fv = dict(item)
            fv.update(
                {
                    "fileUrl": file_url,
                    "fileHash": file_hash,
                    "originalFileName": file.filename,
                    "fileSize": file_size,
                    "fileType": file_type_ext,
                    "uploadedAt": _utcnow_iso(),
                    "aiExtraction": fv.get("aiExtraction")
                    or {
                        "status": "pending",
                        "timestamp": None,
                        "message": None,
                        "statusHistory": None,
                        "controls": None,
                    },
                }
            )
            if not fv.get("fileId"):
                fv["fileId"] = new_id()
            parsed_file_versions.append(fv)
        if not resolved_current and parsed_file_versions:
            resolved_current = parsed_file_versions[-1].get("fileVersion")
    else:
        parsed_file_versions = [
            {
                "fileVersion": currentFileVersion or "1.0.0",
                "fileId": new_id(),
                "fileUrl": file_url,
                "fileHash": file_hash,
                "originalFileName": file.filename,
                "fileSize": file_size,
                "fileType": file_type_ext,
                "uploadedAt": _utcnow_iso(),
                "aiExtraction": {
                    "status": "pending",
                    "timestamp": None,
                    "message": None,
                    "statusHistory": None,
                    "controls": None,
                },
            }
        ]
        resolved_current = currentFileVersion or "1.0.0"

    parsed_approval: dict[str, Any] = {"status": "pending", "by": None, "date": None, "remark": None}
    if approval:
        try:
            parsed_approval = {**parsed_approval, **json.loads(approval)}
        except json.JSONDecodeError as exc:
            return error(f"approval invalid: {exc}", 400)

    duplicate_id: str | None = None
    async with session_scope() as session:
        if file_hash:
            all_fw = (await session.execute(select(Framework))).scalars().all()
            for fw in all_fw:
                for fv in fw.fileVersions or []:
                    if isinstance(fv, dict) and fv.get("fileHash") == file_hash and fw.id != id:
                        duplicate_id = fw.id
                        break
                if duplicate_id:
                    break

        existing = await session.get(Framework, id)
        if existing:
            new_version = _bump_semver(existing.currentFileVersion)
            if parsed_file_versions:
                parsed_file_versions[-1]["fileVersion"] = new_version
            resolved_current = new_version
            updated = list(existing.fileVersions or []) + parsed_file_versions
            existing.fileVersions = updated
            existing.currentFileVersion = new_version
            existing.frameworkName = frameworkName
            existing.frameworkVersion = frameworkVersion
            existing.frameworkCategoryId = frameworkCategoryId
            existing.frameworkCode = frameworkCode
            flag_modified(existing, "fileVersions")
            parsed_file_versions = updated
        else:
            session.add(
                Framework(
                    id=id,
                    frameworkName=frameworkName,
                    frameworkVersion=frameworkVersion,
                    frameworkCategoryId=frameworkCategoryId,
                    frameworkCode=frameworkCode,
                    uploadedBy=uploadedBy,
                    currentFileVersion=resolved_current or "1.0.0",
                    fileVersions=parsed_file_versions,
                    approval=parsed_approval,
                )
            )

    return success(
        message="Framework uploaded successfully",
        data={
            "id": id,
            "resourceType": "framework",
            "frameworkName": frameworkName,
            "frameworkVersion": frameworkVersion,
            "frameworkCategoryId": frameworkCategoryId,
            "frameworkCode": frameworkCode,
            "uploadedBy": uploadedBy,
            "currentFileVersion": resolved_current or "1.0.0",
            "fileVersions": parsed_file_versions,
            "approval": parsed_approval,
            "filename": file.filename,
            "file_size": file_size,
            "file_hash": file_hash,
            "is_duplicate": bool(duplicate_id),
            "duplicate_of_id": duplicate_id,
        },
    )


@router.delete("/frameworks/{id}")
async def delete_framework(id: str):
    async with session_scope() as session:
        fw = await session.get(Framework, id)
        if not fw:
            return error(f"Framework with id '{id}' not found.", 404)
        for fv in fw.fileVersions or []:
            if isinstance(fv, dict):
                _safe_unlink(fv.get("fileUrl"))
        await session.delete(fw)
    return success(
        message="Framework deleted successfully",
        data={"id": id, "resourceType": "framework"},
    )


@router.delete("/frameworks/{id}/file/{file_id}")
async def delete_framework_file(id: str, file_id: str):
    async with session_scope() as session:
        fw = await session.get(Framework, id)
        if not fw:
            return error(f"Framework with id '{id}' not found.", 404)
        versions = list(fw.fileVersions or [])
        if not versions:
            return error(f"Framework '{id}' has no file versions.", 404)
        matched = next((fv for fv in versions if isinstance(fv, dict) and fv.get("fileId") == file_id), None)
        if not matched:
            return error(f"File version '{file_id}' not found in framework '{id}'.", 404)
        _safe_unlink(matched.get("fileUrl"))
        updated = [fv for fv in versions if not (isinstance(fv, dict) and fv.get("fileId") == file_id)]
        fw.fileVersions = updated
        fw.currentFileVersion = updated[-1].get("fileVersion", "1.0.0") if updated else "1.0.0"
        flag_modified(fw, "fileVersions")
    return success(
        message="Framework file version deleted successfully",
        data={
            "id": id,
            "file_id": file_id,
            "resourceType": "framework",
            "delete_mode": "file_version",
        },
    )


@router.patch("/deployment-frameworks/upload")
async def upload_deployment_framework(request: Request):
    form_data = await request.form()
    id = form_data.get("id")
    uploadedBy = form_data.get("uploadedBy")
    assignedFrameworkId = form_data.get("assignedFrameworkId")
    currentPackageVersion = form_data.get("currentPackageVersion")
    packages = form_data.get("packages")
    package = form_data.get("package")
    tenantId = form_data.get("tenantId")
    frameworkName = form_data.get("frameworkName")
    frameworkId = form_data.get("frameworkId")
    frameworkCategoryId = form_data.get("frameworkCategoryId")
    frameworkCode = form_data.get("frameworkCode")
    frameworkVersion = form_data.get("frameworkVersion")

    missing = []
    if not id:
        missing.append("id")
    if not uploadedBy:
        missing.append("uploadedBy")
    if not assignedFrameworkId:
        missing.append("assignedFrameworkId")
    if not (packages or package):
        missing.append("packages|package")
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", 400)

    async with session_scope() as session:
        fa = await session.get(FrameworkAssignment, str(assignedFrameworkId))
        if not fa:
            return error(
                f"Framework assignment not found: assignedFrameworkId='{assignedFrameworkId}'",
                404,
            )
        fa_tenant = fa.tenantId
        frameworkName = frameworkName or fa.frameworkName
        frameworkId = frameworkId or fa.frameworkId
        frameworkCategoryId = frameworkCategoryId or fa.frameworkCategoryId
        frameworkCode = frameworkCode or fa.frameworkCode
        frameworkVersion = frameworkVersion or fa.frameworkVersion
        if not tenantId:
            if fa_tenant and not str(fa_tenant).startswith("pending_"):
                tenantId = fa_tenant
            else:
                user = await session.get(User, str(uploadedBy))
                tenantId = user.tenantId if user else None

    if not tenantId:
        return error("tenantId could not be resolved", 400)

    upload_dir = _upload_dir()
    file_metadata: dict[str, dict[str, Any]] = {}
    file_order: list[str] = []
    field_counts: dict[str, int] = {}

    all_file_items = [
        (k, v) for k, v in form_data.multi_items() if hasattr(v, "filename") and hasattr(v, "read")
    ]
    for field_name, file in all_file_items:
        if _validate_filename(file.filename):
            return error(f"File type not allowed: {file.filename}", 400)
        cnt = field_counts.get(field_name, 0)
        unique_field = field_name if cnt == 0 else f"{field_name}_{cnt}"
        field_counts[field_name] = cnt + 1
        file_order.append(unique_field)

        file_save_name = f"{id}_{new_id()}_{file.filename}"
        upload_path = upload_dir / file_save_name
        try:
            with upload_path.open("wb") as buf:
                shutil.copyfileobj(file.file, buf)
        except Exception as exc:
            return error(f"Could not save file {file.filename}: {exc}", 500)
        finally:
            await file.close()

        file_metadata[unique_field] = {
            "filename": file.filename,
            "path": str(upload_path.resolve()),
            "size": upload_path.stat().st_size,
            "hash": calculate_file_hash(upload_path),
            "url": f"/uploads/{file_save_name}",
            "orig_field": field_name,
        }

    try:
        if packages:
            raw_iter = json.loads(packages)
            if not isinstance(raw_iter, list):
                return error("packages must be a JSON array", 400)
        else:
            raw_single = json.loads(package)  # type: ignore[arg-type]
            if not isinstance(raw_single, dict):
                return error("package must be a JSON object", 400)
            raw_iter = [raw_single]
    except json.JSONDecodeError as exc:
        return error(f"Invalid packages/package JSON: {exc}", 400)

    parsed_packages: list[dict[str, Any]] = []
    for pkg_idx, item in enumerate(raw_iter):
        if not isinstance(item, dict):
            return error(f"packages[{pkg_idx}] must be an object", 400)
        pkg = dict(item)
        pkg.setdefault("createdAt", _utcnow_iso())
        pkg["updatedAt"] = _utcnow_iso()
        pkg.setdefault("gapAnalysis", None)
        pkg.setdefault("comparison", None)
        fallback_order = list(file_order)
        docs = list(pkg.get("documents") or [])
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            file_id = doc.get("fileId")
            file_field = doc.get("fileField")
            is_replicated = bool(doc.get("replicated"))
            matched_file = None

            if file_id and f"file_{file_id}" in file_metadata:
                matched_file = file_metadata[f"file_{file_id}"]
            if not matched_file and file_field:
                if file_field in file_metadata:
                    matched_file = file_metadata[file_field]
                else:
                    for v in file_metadata.values():
                        if v.get("orig_field") == file_field:
                            matched_file = v
                            break
            if not matched_file and not is_replicated and fallback_order:
                matched_file = file_metadata[fallback_order.pop(0)]

            if matched_file:
                file_type_ext = _ext(matched_file["filename"]).lstrip(".")
                doc["fileUrl"] = matched_file["url"]
                doc["fileHash"] = matched_file["hash"]
                doc["originalFileName"] = matched_file["filename"]
                doc["fileSize"] = matched_file["size"]
                doc["fileType"] = file_type_ext if file_type_ext in ("pdf", "doc", "docx") else "pdf"
                doc["uploadedAt"] = _utcnow_iso()
                doc.setdefault(
                    "aiExtraction",
                    {
                        "status": "pending",
                        "timestamp": None,
                        "message": None,
                        "statusHistory": None,
                        "controls": None,
                    },
                )
        pkg["documents"] = docs
        parsed_packages.append(pkg)

    operation = "CREATED"
    async with session_scope() as session:
        existing = await session.get(DeploymentFramework, str(id))
        if existing:
            operation = "UPDATED"
            existing.tenantId = str(tenantId)
            existing.assignedFrameworkId = str(assignedFrameworkId)
            existing.frameworkName = str(frameworkName or existing.frameworkName)
            existing.frameworkId = str(frameworkId) if frameworkId else existing.frameworkId
            existing.frameworkCategoryId = (
                str(frameworkCategoryId) if frameworkCategoryId else existing.frameworkCategoryId
            )
            existing.frameworkCode = str(frameworkCode) if frameworkCode else existing.frameworkCode
            existing.frameworkVersion = (
                str(frameworkVersion) if frameworkVersion else existing.frameworkVersion
            )
            existing.uploadedBy = str(uploadedBy)
            existing.currentPackageVersion = str(
                currentPackageVersion or existing.currentPackageVersion or "1.0.0"
            )

            existing_packages = list(existing.packages or [])
            existing_map = {p.get("packageVersion"): p for p in existing_packages if isinstance(p, dict)}
            merged: list[dict[str, Any]] = []
            seen: set[str] = set()
            for new_pkg in parsed_packages:
                ver = new_pkg.get("packageVersion")
                if ver in existing_map:
                    old = existing_map[ver]
                    old_docs = {
                        str(d.get("fileId") or "").strip(): d
                        for d in (old.get("documents") or [])
                        if isinstance(d, dict) and d.get("fileId")
                    }
                    for new_doc in new_pkg.get("documents") or []:
                        if not isinstance(new_doc, dict):
                            continue
                        key = str(new_doc.get("fileId") or "").strip()
                        if key and key in old_docs and new_doc.get("replicated"):
                            merged_doc = {**old_docs[key], **new_doc, "replicated": True}
                            for copy_key in (
                                "fileUrl",
                                "fileHash",
                                "originalFileName",
                                "fileSize",
                                "fileType",
                                "uploadedAt",
                                "aiExtraction",
                            ):
                                if (
                                    merged_doc.get(copy_key) in (None, "")
                                    and old_docs[key].get(copy_key) is not None
                                ):
                                    merged_doc[copy_key] = old_docs[key][copy_key]
                            old_docs[key] = merged_doc
                        elif key:
                            old_docs[key] = new_doc
                    merged_pkg = {**old, **new_pkg, "documents": list(old_docs.values())}
                    merged.append(merged_pkg)
                    seen.add(ver)
                else:
                    merged.append(new_pkg)
                    if ver:
                        seen.add(ver)
            for ver, pkg in existing_map.items():
                if ver not in seen:
                    merged.append(pkg)
            existing.packages = merged
            flag_modified(existing, "packages")
            parsed_packages = merged
        else:
            session.add(
                DeploymentFramework(
                    id=str(id),
                    tenantId=str(tenantId),
                    assignedFrameworkId=str(assignedFrameworkId),
                    frameworkId=str(frameworkId) if frameworkId else None,
                    frameworkName=str(frameworkName or "UNKNOWN"),
                    frameworkCategoryId=str(frameworkCategoryId) if frameworkCategoryId else None,
                    frameworkCode=str(frameworkCode) if frameworkCode else None,
                    frameworkVersion=str(frameworkVersion) if frameworkVersion else None,
                    uploadedBy=str(uploadedBy),
                    currentPackageVersion=str(currentPackageVersion or "1.0.0"),
                    packages=parsed_packages,
                )
            )

    return success(
        message=f"DeploymentFramework {operation.lower()} successfully",
        data={
            "id": id,
            "resourceType": "deployment-framework",
            "operation": operation,
            "tenantId": tenantId,
            "assignedFrameworkId": assignedFrameworkId,
            "frameworkName": frameworkName,
            "frameworkId": frameworkId,
            "currentPackageVersion": currentPackageVersion or "1.0.0",
            "packages": parsed_packages,
            "files_saved": len(file_metadata),
        },
    )


@router.post("/framework-assignments/upload")
async def upload_framework_assignment(
    id: str = Form(...),
    frameworkId: str = Form(...),
    customerId: str = Form(...),
    assignedBy: str = Form(...),
):
    id = id.strip()
    frameworkId = frameworkId.strip()
    customerId = customerId.strip()
    assignedBy = assignedBy.strip()

    async with session_scope() as session:
        fw = await session.get(Framework, frameworkId)
        if not fw:
            return error(f"Framework with id '{frameworkId}' not found.", 404)

        copied_file_versions: list[dict[str, Any]] = []
        for fv in fw.fileVersions or []:
            if not isinstance(fv, dict):
                continue
            raw_ai = fv.get("aiExtraction") or fv.get("aiUpload")
            copied_file_versions.append(
                {
                    "fileVersion": fv.get("fileVersion", "1.0.0"),
                    "fileId": fv.get("fileId"),
                    "fileUrl": fv.get("fileUrl"),
                    "fileHash": fv.get("fileHash"),
                    "originalFileName": fv.get("originalFileName"),
                    "fileSize": fv.get("fileSize"),
                    "fileType": fv.get("fileType"),
                    "uploadedAt": fv.get("uploadedAt"),
                    "aiExtraction": raw_ai,
                }
            )
        resolved_file_version = fw.currentFileVersion or (
            copied_file_versions[-1].get("fileVersion", "1.0.0") if copied_file_versions else "1.0.0"
        )
        framework_name = fw.frameworkName
        framework_version = fw.frameworkVersion
        framework_code = fw.frameworkCode
        framework_category_id = fw.frameworkCategoryId

        customer = await session.get(Customer, customerId)
        if customer:
            tenant_id = customer.tenantId
        else:
            tenant_id = f"pending_{customerId[:8]}"
            session.add(
                Customer(
                    id=customerId,
                    tenantId=tenant_id,
                    name="pending_sync",
                    email=f"{customerId}@pending.sync",
                )
            )

        user = await session.get(User, assignedBy)
        if not user:
            session.add(
                User(
                    id=assignedBy,
                    tenantId=tenant_id,
                    name="pending_sync",
                    email=f"{assignedBy}@pending.sync",
                    role="pending_sync",
                )
            )

        existing = await session.get(FrameworkAssignment, id)
        assignment_info = {
            "assignedBy": assignedBy,
            "assignedAt": _utcnow_iso(),
        }
        if existing:
            existing.frameworkId = frameworkId
            existing.frameworkCode = framework_code
            existing.frameworkName = framework_name
            existing.frameworkVersion = framework_version
            existing.frameworkCategoryId = framework_category_id
            existing.uploadedBy = assignedBy
            existing.currentFileVersion = resolved_file_version
            existing.fileVersions = copied_file_versions
            existing.status = "assigned"
            existing.tenantId = tenant_id
            existing.customerId = customerId
            existing.assignment = assignment_info
            flag_modified(existing, "fileVersions")
            flag_modified(existing, "assignment")
        else:
            session.add(
                FrameworkAssignment(
                    id=id,
                    tenantId=tenant_id,
                    customerId=customerId,
                    frameworkId=frameworkId,
                    frameworkCode=framework_code,
                    frameworkName=framework_name,
                    frameworkVersion=framework_version,
                    frameworkCategoryId=framework_category_id,
                    uploadedBy=assignedBy,
                    currentFileVersion=resolved_file_version,
                    fileVersions=copied_file_versions,
                    status="assigned",
                    assignment=assignment_info,
                    revocation={},
                    finalization={
                        "isFinalized": False,
                        "finalizedBy": None,
                        "finalizedAt": None,
                    },
                )
            )

    return success(
        message="FrameworkAssignment created successfully",
        data={
            "id": id,
            "resourceType": "framework-assignment",
            "frameworkId": frameworkId,
            "frameworkCode": framework_code,
            "frameworkName": framework_name,
            "frameworkVersion": framework_version,
            "frameworkCategoryId": framework_category_id,
            "customerId": customerId,
            "assignedBy": assignedBy,
            "currentFileVersion": resolved_file_version,
            "fileVersions_count": len(copied_file_versions),
        },
    )


@router.delete("/deployment-frameworks/{id}")
async def delete_deployment_framework(id: str):
    async with session_scope() as session:
        df = await session.get(DeploymentFramework, id)
        if not df:
            return error(f"DeploymentFramework not found: {id}", 404)
        for pkg in df.packages or []:
            if not isinstance(pkg, dict):
                continue
            for doc in pkg.get("documents") or []:
                if isinstance(doc, dict):
                    _safe_unlink(doc.get("fileUrl"))
        await session.delete(df)
    return success(
        message="DeploymentFramework deleted successfully",
        data={"id": id, "resourceType": "deployment-framework"},
    )


@router.delete("/deployment-frameworks/{id}/packageversion/{package_version}")
async def delete_deployment_framework_package_version(id: str, package_version: str):
    deleted_file_ids: list[str] = []
    async with session_scope() as session:
        df = await session.get(DeploymentFramework, id)
        if not df:
            return error(f"DeploymentFramework not found: {id}", 404)
        matched = None
        for pkg in df.packages or []:
            if isinstance(pkg, dict) and pkg.get("packageVersion") == package_version:
                matched = pkg
                break
        if not matched:
            return error(
                f"Package version '{package_version}' not found in deployment-framework '{id}'",
                404,
            )
        for doc in matched.get("documents") or []:
            if isinstance(doc, dict):
                if doc.get("fileId"):
                    deleted_file_ids.append(str(doc["fileId"]).strip())
                _safe_unlink(doc.get("fileUrl"))
        df.packages = [
            pkg
            for pkg in (df.packages or [])
            if not (isinstance(pkg, dict) and pkg.get("packageVersion") == package_version)
        ]
        flag_modified(df, "packages")
    return success(
        message="Package version deleted successfully",
        data={
            "id": id,
            "package_version": package_version,
            "resourceType": "deployment-framework",
            "delete_mode": "package_version",
            "deleted_files_count": len(deleted_file_ids),
            "deleted_file_ids": deleted_file_ids,
        },
    )


@router.delete("/deployment-frameworks/{framework_id}/packageversion/{package_version}/fileid/{file_id}")
async def delete_deployment_framework_file_by_package_version(
    framework_id: str,
    package_version: str,
    file_id: str,
):
    matched_file_hash: str | None = None
    async with session_scope() as session:
        df = await session.get(DeploymentFramework, framework_id)
        if not df:
            return error(f"DeploymentFramework not found: {framework_id}", 404)

        matched_doc = None
        for pkg in df.packages or []:
            if not isinstance(pkg, dict) or pkg.get("packageVersion") != package_version:
                continue
            for doc in pkg.get("documents") or []:
                if isinstance(doc, dict) and doc.get("fileId") == file_id:
                    matched_doc = doc
                    matched_file_hash = doc.get("fileHash")
                    break
            if matched_doc:
                break
        if not matched_doc:
            return error(
                f"File '{file_id}' not found in deployment-framework '{framework_id}' "
                f"package version '{package_version}'",
                404,
            )

        _safe_unlink(matched_doc.get("fileUrl"))
        packages = []
        for pkg in df.packages or []:
            if not isinstance(pkg, dict):
                packages.append(pkg)
                continue
            if pkg.get("packageVersion") != package_version:
                packages.append(pkg)
                continue
            updated_pkg = dict(pkg)
            updated_pkg["documents"] = [
                doc
                for doc in (pkg.get("documents") or [])
                if not (isinstance(doc, dict) and doc.get("fileId") == file_id)
            ]
            packages.append(updated_pkg)
        df.packages = packages
        flag_modified(df, "packages")

    return success(
        message="DeploymentFramework file deleted successfully",
        data={
            "framework_id": framework_id,
            "package_version": package_version,
            "file_id": file_id,
            "file_hash": matched_file_hash,
            "resourceType": "deployment-framework",
            "delete_mode": "package_version_file",
        },
    )
