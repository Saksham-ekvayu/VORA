"""Port of deployment-framework-service-main/src/routes/deployment-framework.routes.js
+ src/controllers/deployment-framework.controller.js (excluding assignment/dashboard routes,
which live in framework_assignment.py / dashboard.py)."""

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, select

from app.helpers import deployment_framework_helpers as helpers
from app.helpers.deployment_framework_helpers import coerce_packages, dump_packages
from app.helpers.reports.deployment_framework_report import generate_deployment_framework_report_pdf
from app.services import ai_service, ai_websocket_service, analysis_websocket_service, data_formatter, package_builder
from vora_shared import query_builder
from vora_shared.database import session_scope
from vora_shared.ids import is_valid_id, new_id
from vora_shared.messages import BUSINESS_MESSAGES, FRAMEWORK_MESSAGES
from vora_shared.models import (
    DeploymentFramework,
    DocumentExtraction,
    PackageComparison,
    PackageGapAnalysis,
    PackageMerge,
    User,
)
from vora_shared.models.document_extraction import AiExtractionInfo
from vora_shared.responses import error, forbidden, paginated, success
from vora_shared.security import RequestContext, get_context

logger = logging.getLogger("deployment_framework_router")

router = APIRouter(tags=["deployment-framework"])


def not_found(resource: str = "Resource"):
    return error(f"{resource} not found", 404)


_PACKAGE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _blob_get(blob: Any, key: str, default: Any = None) -> Any:
    if blob is None:
        return default
    if isinstance(blob, dict):
        return blob.get(key, default)
    return getattr(blob, key, default)


async def _sync_deployment_package_with_ai(framework: DeploymentFramework, package_data: Any) -> dict[str, Any]:
    documents = package_data.documents if hasattr(package_data, "documents") else package_data.get("documents", [])
    if not documents:
        return {"skipped": True, "reason": "No documents in package"}

    file_paths = [
        helpers.get_upload_file_path(doc.fileUrl if hasattr(doc, "fileUrl") else doc.get("fileUrl"))
        for doc in documents
    ]
    for path, doc in zip(file_paths, documents):
        original_name = doc.originalFileName if hasattr(doc, "originalFileName") else doc.get("originalFileName")
        if not path or not os.path.exists(path):
            raise RuntimeError(f"File not found on disk for AI sync: {original_name}")

    package_version = (
        package_data.packageVersion if hasattr(package_data, "packageVersion") else package_data.get("packageVersion")
    )
    response = await ai_service.upload_deployment_framework(framework, documents, file_paths, package_version)
    logger.info("Deployment framework package %s synced to AI service", package_version)
    return {"synced": True, "response": response}


def _expert_assigned(pkg, user_id: str) -> bool:
    er = pkg.expertReview
    if not er or not er.assignedExpert:
        return False
    return str(er.assignedExpert) == str(user_id) and er.status != "pending"


# ─── GET / (list) ───────────────────────────────────────────────────────────


@router.get("/")
async def get_deployment_frameworks(
    ctx: RequestContext = Depends(get_context),
    page: int | None = Query(default=None),
    limit: int = Query(default=10),
    search: str | None = Query(default=None),
    sortBy: str | None = Query(default=None),
    sortOrder: str | None = Query(default=None),
    aiExtractionStatus: str | None = Query(default=None),
    requestReviewStatus: str | None = Query(default=None),
):
    user = ctx.user
    tenant_id = ctx.tenant_id
    allowed_sort_fields = ["createdAt", "updatedAt", "frameworkName", "fileType", "fileSize", "originalFileName"]

    async with session_scope() as session:
        base_filters = []
        if user.role == "internal-expert":
            pass
        else:
            base_filters.append(DeploymentFramework.tenantId == tenant_id)

        # Role filters that need JSONB inspection are applied in Python, then paginated manually.
        stmt = select(DeploymentFramework)
        for f in base_filters:
            stmt = stmt.where(f)
        all_docs = list((await session.execute(stmt)).scalars().all())

        if user.role == "internal-expert":
            filtered = []
            for doc in all_docs:
                packages = coerce_packages(doc.packages)
                assigned = [p for p in packages if _expert_assigned(p, str(user.id))]
                if assigned:
                    doc.packages = dump_packages(assigned)
                    latest = helpers.get_latest_package(assigned)
                    if latest:
                        doc.currentPackageVersion = latest.packageVersion
                    filtered.append(doc)
            all_docs = filtered
        elif user.role == "user":
            filtered = []
            for doc in all_docs:
                packages = coerce_packages(doc.packages)
                current = next(
                    (p for p in packages if p.packageVersion == doc.currentPackageVersion),
                    packages[0] if packages else None,
                )
                if current and current.expertReview and current.expertReview.status == "approved":
                    filtered.append(doc)
            all_docs = filtered

        if search:
            term = search.lower()
            all_docs = [
                d
                for d in all_docs
                if term in (d.frameworkName or "").lower() or term in (d.frameworkVersion or "").lower()
            ]

        sort_field = sortBy if sortBy in allowed_sort_fields else "createdAt"
        reverse = (sortOrder or "").lower() != "asc"
        all_docs.sort(key=lambda d: getattr(d, sort_field, None) or d.createdAt, reverse=reverse)

        maps = await data_formatter.hydrate_maps(session, all_docs)
        formatted = [data_formatter.format_deployment_framework_list_item(doc, maps) for doc in all_docs]

        if aiExtractionStatus:
            formatted = [
                d for d in formatted if (d.get("aiExtraction") or {}).get("status") == aiExtractionStatus
            ]
        if requestReviewStatus:
            formatted = [
                d for d in formatted if (d.get("requestReview") or {}).get("status") == requestReviewStatus
            ]

        page_num = query_builder.clamp_page(page)
        limit_num = query_builder.clamp_limit(limit)
        total = len(formatted)
        start = (page_num - 1) * limit_num
        result = {
            "data": formatted[start : start + limit_num],
            "pagination": query_builder.build_pagination_meta(page_num, limit_num, total),
        }

        message = (
            BUSINESS_MESSAGES["DEPLOYMENT_FRAMEWORKS_RETRIEVED"]
            if user.role == "internal-expert"
            else BUSINESS_MESSAGES["USER_FRAMEWORKS_RETRIEVED"]
        )
        if not result["data"]:
            if search or aiExtractionStatus or requestReviewStatus:
                message = BUSINESS_MESSAGES["NO_FRAMEWORKS_MATCH_CRITERIA"]
            else:
                message = (
                    BUSINESS_MESSAGES["NO_FRAMEWORKS_FOR_REVIEW"]
                    if user.role == "internal-expert"
                    else BUSINESS_MESSAGES["NO_USER_FRAMEWORKS"]
                )

        return paginated(result["data"], result["pagination"], message)


# ─── GET /client-controls ───────────────────────────────────────────────────


@router.get("/client-controls")
async def get_deployment_framework_package_client_controls(ctx: RequestContext = Depends(get_context)):
    async with session_scope() as session:
        frameworks = list(
            (
                await session.execute(
                    select(DeploymentFramework).where(DeploymentFramework.tenantId == ctx.tenant_id)
                )
            ).scalars().all()
        )
        merge_ids = []
        live_by_fw = []
        for fw in frameworks:
            packages = coerce_packages(fw.packages)
            live_package = next((p for p in packages if p.status == "live"), None)
            if not live_package:
                continue
            live_by_fw.append((fw, live_package))
            if live_package.mergeDocument:
                merge_ids.append(str(live_package.mergeDocument))

        merges: dict[str, PackageMerge] = {}
        if merge_ids:
            rows = (
                await session.execute(select(PackageMerge).where(PackageMerge.id.in_(merge_ids)))
            ).scalars().all()
            merges = {str(m.id): m for m in rows}

        client_controls = []
        for fw, live_package in live_by_fw:
            merge = merges.get(str(live_package.mergeDocument)) if live_package.mergeDocument else None
            controls_data = _blob_get(merge.mergeExtraction if merge else None, "controls_data") or []
            client_controls.append(
                {
                    "frameworkId": str(fw.id) if fw and getattr(fw, "id", None) else None,
                    "frameworkName": fw.frameworkName,
                    "frameworkVersion": fw.frameworkVersion,
                    "packageVersion": live_package.packageVersion,
                    "controls": controls_data or [],
                }
            )

        return success(client_controls, "Client controls retrieved successfully")


# ─── PATCH /:id/deployment-points ───────────────────────────────────────────


@router.patch("/{id}/deployment-points")
async def update_deployment_package_point_path(
    id: str,
    ctx: RequestContext = Depends(get_context),
    body: dict[str, Any] = Body(...),
):
    control_id = body.get("controlId")
    point_id = body.get("pointId")
    path_value = body.get("path")
    package_version = body.get("packageVersion")
    section_id = body.get("sectionId")

    if not control_id or not point_id or not package_version or path_value is None:
        return error(
            "packageVersion, controlId, pointId and path are required fields in the request body", 400
        )

    async with session_scope() as session:
        framework = (
            await session.execute(
                select(DeploymentFramework).where(
                    DeploymentFramework.id == str(id),
                    DeploymentFramework.tenantId == ctx.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not framework:
            return not_found("Deployment framework")

        packages = coerce_packages(framework.packages)
        target_package = next((p for p in packages if p.packageVersion == package_version), None)
        if not target_package:
            return not_found("Package version")

        if not target_package.mergeDocument:
            return not_found("Package merge document")

        package_merge = (
            await session.execute(
                select(PackageMerge).where(
                    PackageMerge.id == str(target_package.mergeDocument),
                    PackageMerge.frameworkId == str(framework.id),
                )
            )
        ).scalar_one_or_none()
        if not package_merge:
            return not_found("Package merge document")

        merge_data = dict(package_merge.mergeExtraction or {})
        controls_data = list(merge_data.get("controls_data") or [])
        point_found = False
        for section in controls_data:
            if section_id and section.get("id") != section_id:
                continue
            control = next((c for c in (section.get("controls") or []) if c.get("id") == control_id), None)
            if not control:
                continue
            dp = next((d for d in (control.get("deployment_points") or []) if d.get("id") == point_id), None)
            if not dp:
                continue
            dp["path"] = path_value
            point_found = True
            break

        if not point_found:
            return not_found("Control or deployment point")

        merge_data["controls_data"] = controls_data
        package_merge.mergeExtraction = merge_data

        return success(
            {
                "frameworkId": str(framework.id) if framework and getattr(framework, "id", None) else None,
                "packageVersion": package_version,
                "sectionId": section_id,
                "controlId": control_id,
                "pointId": point_id,
                "path": path_value,
            },
            "Deployment point path updated successfully",
        )


# ─── GET /:id ────────────────────────────────────────────────────────────────


@router.get("/{id}")
async def get_deployment_framework_by_id(id: str, ctx: RequestContext = Depends(get_context)):
    user = ctx.user
    async with session_scope() as session:
        framework = await session.get(DeploymentFramework, str(id))
        if not framework:
            return not_found("Framework")

        if user.role != "expert" and framework.tenantId != ctx.tenant_id:
            return not_found("Framework")

        packages = coerce_packages(framework.packages)
        if user.role in ("expert", "internal-expert"):
            assigned_packages = [p for p in packages if _expert_assigned(p, str(user.id))]
            if not assigned_packages:
                return not_found("Framework")
            framework.packages = dump_packages(assigned_packages)
            latest = helpers.get_latest_package(assigned_packages)
            if latest:
                framework.currentPackageVersion = latest.packageVersion
        else:
            current_package = helpers.get_current_package(framework)
            if user.role == "user":
                if (
                    not current_package
                    or not current_package.expertReview
                    or current_package.expertReview.status != "approved"
                ):
                    return error(BUSINESS_MESSAGES["FRAMEWORK_ACCESS_DENIED"], 403)

        maps = await data_formatter.hydrate_maps(session, [framework])
        response_data = data_formatter.format_deployment_framework(framework, maps, True)
        return success(response_data, BUSINESS_MESSAGES["FRAMEWORK_RETRIEVED_SUCCESS"])


# ─── GET /:id/packages/:packageVersion ──────────────────────────────────────


@router.get("/{id}/packages/{packageVersion}")
async def get_deployment_framework_package_by_version(
    id: str, packageVersion: str, ctx: RequestContext = Depends(get_context)
):
    user = ctx.user
    async with session_scope() as session:
        framework = await session.get(DeploymentFramework, str(id))
        if not framework:
            return not_found("Framework")

        if user.role != "expert" and framework.tenantId != ctx.tenant_id:
            return not_found("Framework")

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == packageVersion), None)
        if not found_package:
            return not_found("Package version")

        if user.role == "internal-expert":
            assigned_expert_id = (
                str(found_package.expertReview.assignedExpert)
                if found_package.expertReview and found_package.expertReview.assignedExpert
                else None
            )
            is_not_pending = found_package.expertReview.status != "pending" if found_package.expertReview else False
            if assigned_expert_id != str(user.id) or not is_not_pending:
                return not_found("Framework")
        elif user.role == "user":
            if not found_package.expertReview or found_package.expertReview.status != "approved":
                return error(BUSINESS_MESSAGES["FRAMEWORK_ACCESS_DENIED"], 403)

        framework.packages = dump_packages([found_package])
        framework.currentPackageVersion = packageVersion

        maps = await data_formatter.hydrate_maps(session, [framework])
        response_data = data_formatter.format_deployment_framework(framework, maps, False)
        return success(response_data, BUSINESS_MESSAGES["FRAMEWORK_RETRIEVED_SUCCESS"])


# ─── PUT /:id (update / new patch) ──────────────────────────────────────────


@router.put("/{id}")
async def update_deployment_framework(
    id: str,
    ctx: RequestContext = Depends(get_context),
    files: list[UploadFile] = File(default=[]),
    metadata: str | None = Form(default=None),
):
    tenant_id = ctx.tenant_id

    async with session_scope() as session:
        if is_valid_id(id):
            framework = (
                await session.execute(
                    select(DeploymentFramework).where(
                        DeploymentFramework.id == str(id),
                        DeploymentFramework.tenantId == tenant_id,
                    )
                )
            ).scalar_one_or_none()
        else:
            # Legacy path: treat as nested fileId lookup inside packages JSONB
            candidates = list(
                (
                    await session.execute(
                        select(DeploymentFramework).where(DeploymentFramework.tenantId == tenant_id)
                    )
                ).scalars().all()
            )
            framework = None
            for fw in candidates:
                if helpers.find_framework_document(fw, id):
                    framework = fw
                    break

        if not framework:
            return not_found("Deployment framework")

        meta_dict: dict[str, Any] = {}
        if metadata:
            import json

            try:
                meta_dict = json.loads(metadata)
            except (ValueError, TypeError):
                meta_dict = {}

        document_updates = helpers.parse_document_updates(meta_dict.get("documents"))

        patch_type = meta_dict.get("patchType", "minor")
        if patch_type not in ("minor", "major"):
            return error("Invalid patch type. Must be 'minor' or 'major'", 400)

        try:
            file_entries = [{"filename": f.filename or "file", "content": await f.read()} for f in files]

            if patch_type == "minor":
                result = package_builder.build_minor_patch(framework, file_entries, document_updates)
            else:
                result = package_builder.build_major_patch(framework, file_entries, document_updates)

            uploaded_files_map = {f["filename"]: f["content"] for f in file_entries}
            save_result = helpers.save_uploaded_files_for_package(framework, uploaded_files_map, result, tenant_id)
            if save_result.get("error"):
                return error(f"Failed to save file: {save_result['filename']}", 500)

            missing_file_docs = [
                d
                for d in result["newPackage"]["documents"]
                if not d.get("replicated") and (not d.get("fileUrl") or not d.get("fileHash"))
            ]
            if missing_file_docs:
                missing_names = ", ".join(
                    str(d.get("originalFileName") or d.get("fileId")) for d in missing_file_docs
                )
                return error(
                    f"Missing uploaded file data for add/replace document(s): {missing_names}. "
                    "Add operations require file upload in the same multipart request.",
                    400,
                )

            validation = package_builder.validate_package(result["newPackage"])
            if not validation["isValid"]:
                return error(f"Package validation failed: {', '.join(validation['errors'])}", 400)

            from vora_shared.models.deployment_framework import FrameworkPackageDocument, PackageVersion

            new_documents = [FrameworkPackageDocument(**d) for d in result["newPackage"]["documents"]]
            await helpers.ensure_document_extraction_refs(session, new_documents)
            result["newPackage"]["documents"] = [d.model_dump(mode="json") for d in new_documents]

            await helpers.ensure_package_analysis_refs(session, result["newPackage"], framework.id)

            new_package = PackageVersion(**result["newPackage"])
            packages = coerce_packages(framework.packages)
            packages.append(new_package)
            framework.packages = dump_packages(packages)
            framework.currentPackageVersion = new_package.packageVersion

            if meta_dict.get("frameworkName"):
                framework.frameworkName = meta_dict["frameworkName"]
            if meta_dict.get("frameworkCode"):
                framework.frameworkCode = meta_dict["frameworkCode"]
            if meta_dict.get("frameworkVersion"):
                framework.frameworkVersion = meta_dict["frameworkVersion"]
            if meta_dict.get("frameworkId"):
                framework.frameworkId = meta_dict["frameworkId"]

            framework.updatedAt = _utcnow()

            ai_sync: dict[str, Any] = {"synced": False}
            try:
                ai_sync = await _sync_deployment_package_with_ai(framework, new_package)
            except Exception as ai_error:
                ai_sync = {"synced": False, "error": str(ai_error)}
                logger.warning(
                    "Failed to sync deployment framework package %s to AI service: %s",
                    new_package.packageVersion,
                    ai_error,
                )

            return success(
                {
                    "id": str(framework.id) if framework and getattr(framework, "id", None) else None,
                    "frameworkId": str(framework.frameworkId)
                    if framework and getattr(framework, "frameworkId", None)
                    else None,
                    "frameworkName": framework.frameworkName,
                    "frameworkCode": framework.frameworkCode,
                    "frameworkVersion": framework.frameworkVersion,
                    "currentPackageVersion": framework.currentPackageVersion,
                    "packageVersion": new_package.packageVersion,
                    "patchType": patch_type,
                    "documentsCount": len(new_package.documents),
                    "aiSync": ai_sync,
                    "updatedAt": framework.updatedAt,
                },
                f"Framework {patch_type} patch created successfully",
            )
        except Exception as exc:
            logger.exception("Framework update error")
            return error(str(exc), 500)


# ─── DELETE /:id ─────────────────────────────────────────────────────────────


@router.delete("/{id}")
async def delete_deployment_framework(id: str, ctx: RequestContext = Depends(get_context)):
    tenant_id = ctx.tenant_id
    user = ctx.user

    async with session_scope() as session:
        framework = (
            await session.execute(
                select(DeploymentFramework).where(
                    DeploymentFramework.id == str(id),
                    DeploymentFramework.tenantId == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not framework:
            return not_found("Deployment framework")

        is_owner = str(framework.uploadedBy) == str(user.id)
        is_admin = user.role == "admin"
        if not is_owner and not is_admin:
            return forbidden("You don't have permission to delete this framework")

        packages = coerce_packages(framework.packages)
        file_urls = {doc.fileUrl for pkg in packages for doc in (pkg.documents or []) if doc.fileUrl}
        for file_url in file_urls:
            try:
                file_path = helpers.get_upload_file_path(file_url)
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as exc:
                logger.error("Failed to delete file %s: %s", file_url, exc)

        try:
            await ai_service.delete_deployment_framework(str(framework.id))
            logger.info("Successfully deleted deployment framework from AI service")
        except Exception as ai_error:
            logger.warning("Failed to delete deployment framework from AI service: %s", ai_error)

        try:
            await session.execute(delete(PackageMerge).where(PackageMerge.frameworkId == str(framework.id)))
            await session.execute(
                delete(PackageComparison).where(PackageComparison.frameworkId == str(framework.id))
            )
            await session.execute(
                delete(PackageGapAnalysis).where(PackageGapAnalysis.frameworkId == str(framework.id))
            )
        except Exception as db_error:
            logger.warning(
                "Failed to delete associated merges, comparisons and gap analyses: %s", db_error
            )

        await session.delete(framework)
        return success(None, "Framework deleted successfully")


# ─── POST /upload ────────────────────────────────────────────────────────────


@router.post("/upload", status_code=201)
async def upload_deployment_framework(
    ctx: RequestContext = Depends(get_context),
    file: list[UploadFile] | None = File(default=None),
    files: list[UploadFile] | None = File(default=None),
    metadata: str | None = Form(default=None),
):
    import json

    meta: dict[str, Any] = {}
    if metadata:
        try:
            meta = json.loads(metadata)
        except (ValueError, TypeError):
            meta = {}

    framework_name = meta.get("frameworkName")
    framework_id = meta.get("frameworkId")
    assigned_framework_id = meta.get("assignedFrameworkId")
    framework_category_id = meta.get("frameworkCategoryId")
    framework_code = meta.get("frameworkCode")
    framework_version = meta.get("frameworkVersion")

    tenant_id = ctx.tenant_id
    user_id = ctx.user.id

    all_files: list[UploadFile] = [*(file or []), *(files or [])]
    if not all_files:
        return error("At least one file is required", 400)

    version = meta.get("fileVersion") or "1.0.0"

    process_result = await helpers.process_uploaded_files(all_files, framework_id, tenant_id, version)
    if process_result.get("error"):
        return error(process_result["error"]["message"], process_result["error"]["status"])

    document_data_array = process_result["documentDataArray"]

    from vora_shared.models.deployment_framework import FrameworkPackageDocument, PackageVersion

    async with session_scope() as session:
        document_models = [FrameworkPackageDocument(**d) for d in document_data_array]
        await helpers.ensure_document_extraction_refs(session, document_models)

        package_data: dict[str, Any] = {
            "packageVersion": version,
            "type": "pre-release",
            "trigger": "Initial package draft",
            "status": "pending",
            "documents": [d.model_dump(mode="json") for d in document_models],
            "expertReview": {"status": "pending"},
        }

        new_framework_id = new_id()
        await helpers.ensure_package_analysis_refs(session, package_data, new_framework_id)

        existing_framework = await helpers.check_existing_framework(
            session, tenant_id, framework_version, framework_id, framework_code
        )
        if existing_framework:
            return error(
                f"A deployment framework for this framework version ({framework_version}) already exists.",
                409,
            )

        package_version_model = PackageVersion(**package_data)

        deployment_framework = DeploymentFramework(
            id=new_framework_id,
            tenantId=tenant_id,
            frameworkName=framework_name,
            frameworkId=framework_id,
            assignedFrameworkId=str(assigned_framework_id) if assigned_framework_id else new_framework_id,
            frameworkCategoryId=framework_category_id,
            frameworkCode=framework_code,
            frameworkVersion=framework_version,
            currentPackageVersion=version,
            packages=dump_packages([package_version_model]),
            uploadedBy=str(user_id),
        )
        session.add(deployment_framework)
        await session.flush()

        ai_sync: dict[str, Any] = {"synced": False}
        try:
            ai_sync = await _sync_deployment_package_with_ai(deployment_framework, package_version_model)
        except Exception as ai_error:
            ai_sync = {"synced": False, "error": str(ai_error)}
            logger.warning(
                "Failed to sync deployment framework package %s to AI service: %s", version, ai_error
            )

        return success(
            {
                "frameworkId": str(deployment_framework.id)
                if deployment_framework and getattr(deployment_framework, "id", None)
                else None,
                "fileIds": [d.fileId for d in document_models],
                "fileNames": [d.originalFileName for d in document_models],
                "packageVersion": version,
                "frameworkName": deployment_framework.frameworkName,
                "uploadUrls": [d.fileUrl for d in document_models],
                "aiSync": ai_sync,
            },
            "File uploaded successfully",
            201,
        )


# ─── GET /:frameworkId/files/:fileId/preview ────────────────────────────────


@router.get("/{frameworkId}/files/{fileId}/preview")
async def preview_framework_file(frameworkId: str, fileId: str, ctx: RequestContext = Depends(get_context)):
    async with session_scope() as session:
        framework = await session.get(DeploymentFramework, str(frameworkId))
        if not framework or not helpers.find_framework_document(framework, fileId):
            return not_found("Framework")

        document = helpers.find_framework_document(framework, fileId)
        if not document:
            return not_found("Document")

        actual_file_path = helpers.get_upload_file_path(document.fileUrl)
        if not actual_file_path or not os.path.exists(actual_file_path):
            return not_found("File on disk")

        mime = helpers.MIME_TYPES.get(str(document.fileType).lower(), "application/octet-stream")
        return FileResponse(
            actual_file_path,
            media_type=mime,
            filename=document.originalFileName,
            content_disposition_type="inline",
        )


# ─── GET /:frameworkId/files/:fileId/download ───────────────────────────────


@router.get("/{frameworkId}/files/{fileId}/download")
async def download_framework_file(frameworkId: str, fileId: str, ctx: RequestContext = Depends(get_context)):
    async with session_scope() as session:
        framework = await session.get(DeploymentFramework, str(frameworkId))
        if not framework or not helpers.find_framework_document(framework, fileId):
            return not_found("Framework")

        document = helpers.find_framework_document(framework, fileId)
        if not document:
            return not_found("Document")

        actual_file_path = helpers.get_upload_file_path(document.fileUrl)
        if not actual_file_path or not os.path.exists(actual_file_path):
            return not_found("File on disk")

        mime = helpers.MIME_TYPES.get(str(document.fileType).lower(), "application/octet-stream")
        return FileResponse(
            actual_file_path,
            media_type=mime,
            filename=document.originalFileName,
            content_disposition_type="attachment",
        )


# ─── DELETE /:frameworkId/packages/:packageVersion ──────────────────────────


@router.delete("/{frameworkId}/packages/{packageVersion}")
async def delete_deployment_framework_package(
    frameworkId: str, packageVersion: str, ctx: RequestContext = Depends(get_context)
):
    tenant_id = ctx.tenant_id

    async with session_scope() as session:
        framework = (
            await session.execute(
                select(DeploymentFramework).where(
                    DeploymentFramework.id == str(frameworkId),
                    DeploymentFramework.tenantId == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not framework:
            return not_found("Deployment framework")

        packages = coerce_packages(framework.packages)
        package_index = next((i for i, p in enumerate(packages) if p.packageVersion == packageVersion), -1)
        if package_index == -1:
            return not_found("Package")

        package_to_delete = packages[package_index]

        if len(packages) == 1:
            return error("Cannot delete the only package. Delete the entire framework instead.", 400)

        is_deleting_current = package_to_delete.packageVersion == framework.currentPackageVersion

        remaining_file_urls = {
            doc.fileUrl
            for i, pkg in enumerate(packages)
            if i != package_index
            for doc in (pkg.documents or [])
            if doc.fileUrl
        }
        file_urls_to_delete = {
            doc.fileUrl
            for doc in (package_to_delete.documents or [])
            if doc.fileUrl and doc.fileUrl not in remaining_file_urls
        }

        from vora_shared import file_storage

        for file_url in file_urls_to_delete:
            try:
                absolute_path = helpers.get_upload_file_path(file_url)
                if absolute_path:
                    file_storage.delete_file(absolute_path)
            except Exception as exc:
                logger.error("Failed to delete package file from disk: %s", exc)

        try:
            await ai_service.delete_package_version(frameworkId, packageVersion)
        except Exception as ai_error:
            logger.warning("Failed to delete package version from AI service: %s", ai_error)

        packages.pop(package_index)

        if is_deleting_current:
            latest_package = helpers.get_latest_package(packages)
            if latest_package:
                framework.currentPackageVersion = latest_package.packageVersion

        framework.packages = dump_packages(packages)
        framework.updatedAt = _utcnow()
        return success({"currentPackageVersion": framework.currentPackageVersion}, "Package deleted successfully")


# ─── POST /:frameworkId/packages/:packageVersion/files/:fileId/ai-upload ────


@router.post("/{frameworkId}/packages/{packageVersion}/files/{fileId}/ai-upload")
async def upload_deployment_framework_to_ai(
    frameworkId: str, packageVersion: str, fileId: str, ctx: RequestContext = Depends(get_context)
):
    tenant_id = ctx.tenant_id

    async with session_scope() as session:
        framework = (
            await session.execute(
                select(DeploymentFramework).where(
                    DeploymentFramework.id == str(frameworkId),
                    DeploymentFramework.tenantId == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not framework:
            return not_found("Deployment framework")

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == packageVersion), None)
        if not found_package:
            return not_found("Package version")

        found_doc = next((d for d in (found_package.documents or []) if str(d.fileId) == fileId), None)
        if not found_doc:
            return not_found("File version")

        actual_file_path = helpers.get_upload_file_path(found_doc.fileUrl)
        if not actual_file_path or not os.path.exists(actual_file_path):
            return not_found("File on disk")

        existing_extraction = None
        if found_doc.aiExtraction:
            existing_extraction = await session.get(DocumentExtraction, str(found_doc.aiExtraction))
        if not existing_extraction:
            existing_extraction = (
                await session.execute(
                    select(DocumentExtraction).where(DocumentExtraction.fileHash == found_doc.fileHash)
                )
            ).scalar_one_or_none()

        if existing_extraction:
            ai = AiExtractionInfo.model_validate(existing_extraction.aiExtraction or {})
            if ai.status == "extracted":
                found_doc.aiExtraction = existing_extraction.id
                found_doc.replicated = True
                framework.packages = dump_packages(packages)
                return success(
                    {"reused": True, "fileHash": found_doc.fileHash},
                    "AI extraction already exists for this file and was reused",
                )

        extraction_id = await helpers.ensure_document_extraction_ref(session, found_doc)
        if not extraction_id:
            return error("Unable to prepare AI extraction record for this file.", 500)

        framework.packages = dump_packages(packages)

        asyncio.create_task(
            ai_websocket_service.start_extraction(frameworkId, found_package.packageVersion, fileId)
        )

        try:
            response = await ai_service.upload_deployment_framework(
                framework,
                found_doc,
                helpers.get_upload_file_path(found_doc.fileUrl),
                found_package.packageVersion,
            )
            logger.info("Deployment framework uploaded successfully to AI service")
        except Exception as exc:
            logger.error("Failed to upload deployment framework to AI service: %s", exc)
            return error(str(exc), 500)

        return success(response, "Deployment framework file upload to AI initiated")


# ─── POST /:deploymentFrameworkId/packages/:packageVersion/run-analysis ─────


@router.post("/{deploymentFrameworkId}/packages/{packageVersion}/run-analysis")
async def run_deployment_framework_analysis(
    deploymentFrameworkId: str, packageVersion: str, ctx: RequestContext = Depends(get_context)
):
    tenant_id = ctx.tenant_id

    async with session_scope() as session:
        framework = (
            await session.execute(
                select(DeploymentFramework).where(
                    DeploymentFramework.id == str(deploymentFrameworkId),
                    DeploymentFramework.tenantId == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not framework:
            return not_found("Deployment framework")

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == packageVersion), None)
        if not found_package:
            return not_found("Package version")

        docs = found_package.documents or []
        all_extracted = bool(docs)
        for doc in docs:
            if not doc.aiExtraction:
                all_extracted = False
                break
            extraction = await session.get(DocumentExtraction, str(doc.aiExtraction))
            if not extraction:
                all_extracted = False
                break
            ai = AiExtractionInfo.model_validate(extraction.aiExtraction or {})
            if ai.status != "extracted":
                all_extracted = False
                break

        if not all_extracted:
            return error("Cannot run analysis. All documents in the package must be AI extracted first.", 400)

        asyncio.create_task(analysis_websocket_service.run_analysis(deploymentFrameworkId, packageVersion))
        return success(None, "Analysis initiated successfully")


# ─── GET /:id/packages/:packageVersion/report ───────────────────────────────


@router.get("/{id}/packages/{packageVersion}/report")
async def download_deployment_framework_report(
    id: str, packageVersion: str, ctx: RequestContext = Depends(get_context)
):
    user = ctx.user
    async with session_scope() as session:
        stmt = select(DeploymentFramework).where(DeploymentFramework.id == str(id))
        if user.role not in ("expert", "internal-expert"):
            stmt = stmt.where(DeploymentFramework.tenantId == ctx.tenant_id)

        framework = (await session.execute(stmt)).scalar_one_or_none()
        if not framework:
            return not_found("Deployment framework")

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == packageVersion), None)
        if not found_package:
            return not_found("Package version")

        maps = await data_formatter.hydrate_maps(session, [framework])
        merge = maps["merges"].get(str(found_package.mergeDocument)) if found_package.mergeDocument else None
        comparison = maps["comparisons"].get(str(found_package.comparison)) if found_package.comparison else None
        gap = maps["gaps"].get(str(found_package.gapAnalysis)) if found_package.gapAnalysis else None

        merge_status = _blob_get(merge.mergeExtraction if merge else None, "status") or "pending"
        comparison_status = _blob_get(comparison.comparison if comparison else None, "status") or "pending"
        gap_status = _blob_get(gap.gapAnalysis if gap else None, "status") or "pending"

        if merge_status != "merged":
            return error(FRAMEWORK_MESSAGES["MERGE_DOCUMENT_NOT_COMPLETED"], 400)
        if comparison_status != "completed":
            return error(FRAMEWORK_MESSAGES["COMPARISON_NOT_COMPLETED"], 400)
        if gap_status != "completed":
            return error(FRAMEWORK_MESSAGES["GAP_ANALYSIS_NOT_COMPLETED"], 400)

        package_dict = data_formatter.format_package(found_package, maps, exclude_details=False)
        pdf_bytes = generate_deployment_framework_report_pdf(framework, package_dict)
        filename = (
            f"{re.sub(r'[^a-zA-Z0-9]', '_', framework.frameworkName or 'framework')}_"
            f"{packageVersion.replace('.', '_')}_report.pdf"
        )

        from fastapi import Response

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


# ─── POST /:id/request-review ───────────────────────────────────────────────


@router.post("/{id}/request-review")
async def request_expert_review(id: str, ctx: RequestContext = Depends(get_context), body: dict[str, Any] = Body(...)):
    user = ctx.user
    tenant_id = ctx.tenant_id
    package_version = body.get("packageVersion")
    expert_id = body.get("expertId")

    if user.role != "auditor":
        return forbidden("Only auditors can request expert reviews")

    if not package_version:
        return error("Package version is required", 400)
    if not expert_id:
        return error(FRAMEWORK_MESSAGES["EXPERT_ID_REQUIRED"], 400)

    async with session_scope() as session:
        framework = (
            await session.execute(
                select(DeploymentFramework).where(
                    DeploymentFramework.id == str(id),
                    DeploymentFramework.tenantId == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not framework:
            return not_found("Deployment framework")

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == package_version), None)
        if not found_package:
            return not_found("Package version")

        if found_package.expertReview and found_package.expertReview.status != "pending":
            return error(FRAMEWORK_MESSAGES["REVIEW_ALREADY_REQUESTED"], 400)

        expert_user = (
            await session.execute(
                select(User).where(User.id == str(expert_id), User.isActive.is_(True))
            )
        ).scalar_one_or_none()
        if not expert_user:
            return not_found(FRAMEWORK_MESSAGES["EXPERT_NOT_FOUND"])

        if expert_user.role != "internal-expert":
            return error("Assigned user must be an internal-expert", 400)

        if expert_user.tenantId != tenant_id:
            return forbidden("Expert not exist in your organization")

        from vora_shared.models.deployment_framework import ExpertReview

        found_package.expertReview = ExpertReview(
            status="requested",
            assignedExpert=expert_user.id,
            requestedAt=_utcnow(),
            reviewedAt=None,
            comments=None,
        )
        found_package.type = "in-review"
        framework.packages = dump_packages(packages)
        framework.updatedAt = _utcnow()

        return success(
            {
                "frameworkId": str(framework.id) if framework and getattr(framework, "id", None) else None,
                "packageVersion": package_version,
                "expertReview": {
                    "status": found_package.expertReview.status,
                    "assignedExpert": {
                        "id": str(expert_user.id) if expert_user and getattr(expert_user, "id", None) else None,
                        "name": expert_user.name,
                        "email": expert_user.email,
                        "role": expert_user.role,
                        "avatar": expert_user.avatar,
                    },
                    "requestedAt": found_package.expertReview.requestedAt,
                },
            },
            FRAMEWORK_MESSAGES["REVIEW_REQUESTED"],
        )


# ─── PATCH /:id/packages/:packageVersion/review ─────────────────────────────


@router.patch("/{id}/packages/{packageVersion}/review")
async def review_deployment_package(
    id: str, packageVersion: str, ctx: RequestContext = Depends(get_context), body: dict[str, Any] = Body(...)
):
    user = ctx.user
    tenant_id = ctx.tenant_id
    action = body.get("action")
    comments = body.get("comments")

    if user.role != "internal-expert":
        return forbidden("Only internal experts can review deployment packages")

    async with session_scope() as session:
        framework = (
            await session.execute(
                select(DeploymentFramework).where(
                    DeploymentFramework.id == str(id),
                    DeploymentFramework.tenantId == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not framework:
            return not_found("Deployment framework")

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == packageVersion), None)
        if not found_package:
            return not_found("Package version")

        if not found_package.expertReview or found_package.expertReview.status != "requested":
            return error(FRAMEWORK_MESSAGES["REVIEW_NOT_REQUESTED"], 400)

        assigned_expert_id = (
            str(found_package.expertReview.assignedExpert) if found_package.expertReview.assignedExpert else None
        )
        if assigned_expert_id != str(user.id):
            return forbidden(FRAMEWORK_MESSAGES["ONLY_ASSIGNED_FRAMEWORKS"])

        if action == "approve":
            for pkg in packages:
                if pkg.status == "live" and pkg.packageVersion != packageVersion:
                    pkg.status = "superseded"
                    pkg.updatedAt = _utcnow()

            found_package.type = "deployed"
            found_package.status = "live"
            found_package.expertReview.status = "approved"
            found_package.expertReview.reviewedAt = _utcnow()
            found_package.expertReview.comments = comments
            found_package.updatedAt = _utcnow()
            framework.currentPackageVersion = packageVersion
        else:
            found_package.type = "pre-release"
            found_package.status = "returned"
            found_package.expertReview.status = "rejected"
            found_package.expertReview.reviewedAt = _utcnow()
            found_package.expertReview.comments = comments
            found_package.updatedAt = _utcnow()

        framework.packages = dump_packages(packages)
        framework.updatedAt = _utcnow()

        message = (
            FRAMEWORK_MESSAGES["FRAMEWORK_APPROVED"] if action == "approve" else FRAMEWORK_MESSAGES["FRAMEWORK_RETURNED"]
        )
        return success(
            {
                "frameworkId": str(framework.id) if framework and getattr(framework, "id", None) else None,
                "packageVersion": packageVersion,
                "type": found_package.type,
                "status": found_package.status,
                "expertReview": {
                    "status": found_package.expertReview.status,
                    "reviewedAt": found_package.expertReview.reviewedAt,
                    "comments": found_package.expertReview.comments,
                },
            },
            message,
        )


# ─── POST /:id/packegeVersion/:packegeVersion/add-comparison-review-remark ──


@router.post("/{id}/packegeVersion/{packegeVersion}/add-comparison-review-remark")
async def add_review_remark(
    id: str, packegeVersion: str, ctx: RequestContext = Depends(get_context), body: dict[str, Any] = Body(...)
):
    user = ctx.user
    tenant_id = ctx.tenant_id
    assigned_control_id = body.get("assignedControlId")
    deployment_control_id = body.get("deploymentControlId")
    comment = body.get("comment")

    if user.role != "internal-expert":
        return forbidden("Only internal experts can add review remarks")

    async with session_scope() as session:
        framework = (
            await session.execute(
                select(DeploymentFramework).where(
                    DeploymentFramework.id == str(id),
                    DeploymentFramework.tenantId == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not framework:
            return not_found("Deployment framework")

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == packegeVersion), None)
        if not found_package:
            return not_found("Package version")

        if not found_package.comparison:
            return error("Comparison not completed or not found for this package version", 400)

        package_comparison = await session.get(PackageComparison, str(found_package.comparison))
        if not package_comparison:
            return not_found("Package comparison data")

        comp = dict(package_comparison.comparison or {})
        results = list(comp.get("comparison_result") or [])
        control_found = False
        for section in results:
            controls = section.get("controls") if isinstance(section, dict) else getattr(section, "controls", None)
            for c in controls or []:
                c_assigned = c.get("assigned_framework_control_id") if isinstance(c, dict) else c.assigned_framework_control_id
                c_deploy = c.get("deployment_framework_control_id") if isinstance(c, dict) else c.deployment_framework_control_id
                if c_assigned == assigned_control_id and c_deploy == deployment_control_id:
                    if isinstance(c, dict):
                        c["reviewComment"] = comment or ""
                    else:
                        c.reviewComment = comment or ""
                    control_found = True
                    break
            if control_found:
                break

        if not control_found:
            return not_found("Control alignment not found in comparison results")

        comp["comparison_result"] = results
        package_comparison.comparison = comp
        return success({"reviewComment": comment}, "Review remark added successfully")


# ─── POST /:id/packegeVersion/:packegeVersion/add-gap-review-remark ─────────


@router.post("/{id}/packegeVersion/{packegeVersion}/add-gap-review-remark")
async def add_gap_review_remark(
    id: str, packegeVersion: str, ctx: RequestContext = Depends(get_context), body: dict[str, Any] = Body(...)
):
    user = ctx.user
    tenant_id = ctx.tenant_id
    assigned_control_id = body.get("assignedControlId")
    assigned_point_id = body.get("assignedPointId")
    deployment_control_id = body.get("deploymentControlId")
    deployment_point_id = body.get("deploymentPointId")
    comment = body.get("comment")

    if user.role != "internal-expert":
        return forbidden("Only internal experts can add review remarks")

    async with session_scope() as session:
        framework = (
            await session.execute(
                select(DeploymentFramework).where(
                    DeploymentFramework.id == str(id),
                    DeploymentFramework.tenantId == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not framework:
            return not_found("Deployment framework")

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == packegeVersion), None)
        if not found_package:
            return not_found("Package version")

        if not found_package.gapAnalysis:
            return error("Gap analysis not completed or not found for this package version", 400)

        package_gap_analysis = await session.get(PackageGapAnalysis, str(found_package.gapAnalysis))
        if not package_gap_analysis:
            return not_found("Package gap analysis data")

        gap = dict(package_gap_analysis.gapAnalysis or {})
        results = list(gap.get("deployment_gap_results") or [])

        point_found = helpers.update_gap_review_comment(
            results, assigned_control_id, assigned_point_id, deployment_control_id, deployment_point_id, comment
        )
        if not point_found:
            return not_found("Point alignment not found in gap analysis results")

        gap["deployment_gap_results"] = results
        package_gap_analysis.gapAnalysis = gap
        return success({"reviewComment": comment}, "Gap review remark added successfully")
