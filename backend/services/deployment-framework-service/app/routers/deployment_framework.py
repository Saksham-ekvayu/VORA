"""Port of deployment-framework-service-main/src/routes/deployment-framework.routes.js
+ src/controllers/deployment-framework.controller.js (excluding assignment/dashboard routes,
which live in framework_assignment.py / dashboard.py)."""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Annotated, Any

from app.helpers import deployment_framework_helpers as helpers
from app.helpers.deployment_framework_helpers import coerce_packages, dump_packages
from app.helpers.reports.deployment_framework_report import generate_deployment_framework_report_pdf
from app.services import (
    data_formatter,
    package_builder,
)
from fastapi import APIRouter, Body, Depends, File, Form, Path, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import delete, select
from vora_shared import file_storage, query_builder
from vora_shared.database import session_scope
from vora_shared.ids import is_valid_id, new_id
from vora_shared.messages import BUSINESS_MESSAGES, FRAMEWORK_MESSAGES
from vora_shared.models import (
    DeploymentFramework,
    PackageComparison,
    PackageGapAnalysis,
    PackageMerge,
    User,
)
from vora_shared.responses import error, forbidden, paginated, success
from vora_shared.security import RequestContext, get_context

logger = logging.getLogger("deployment_framework_router")

router = APIRouter(tags=["deployment-framework"])

_RESOURCE_DEPLOYMENT_FRAMEWORK = "Deployment framework"
_RESOURCE_PACKAGE_VERSION = "Package version"


def not_found(resource: str = "Resource"):
    return error(f"{resource} not found", 404)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _blob_get(blob: Any, key: str, default: Any = None) -> Any:
    if blob is None:
        return default
    if isinstance(blob, dict):
        return blob.get(key, default)
    return getattr(blob, key, default)


def _expert_assigned(pkg, user_id: str) -> bool:
    er = pkg.expertReview
    if not er or not er.assignedExpert:
        return False
    return str(er.assignedExpert) == str(user_id) and er.status != "pending"


def _filter_for_internal_expert(all_docs: list[Any], user_id: str) -> list[Any]:
    filtered = []
    for doc in all_docs:
        packages = coerce_packages(doc.packages)
        assigned = [p for p in packages if _expert_assigned(p, str(user_id))]
        if assigned:
            doc.packages = dump_packages(assigned)
            latest = helpers.get_latest_package(assigned)
            if latest:
                doc.currentPackageVersion = latest.packageVersion
            filtered.append(doc)
    return filtered


def _filter_for_user(all_docs: list[Any]) -> list[Any]:
    filtered = []
    for doc in all_docs:
        packages = coerce_packages(doc.packages)
        current = next(
            (p for p in packages if p.packageVersion == doc.currentPackageVersion),
            packages[0] if packages else None,
        )
        if current and current.expertReview and current.expertReview.status == "approved":
            filtered.append(doc)
    return filtered


def _get_list_response_message(
    user_role: str,
    has_data: bool,
    search: str | None,
    ai_extraction_status: str | None,
    request_review_status: str | None,
) -> str:
    if has_data:
        return (
            BUSINESS_MESSAGES["DEPLOYMENT_FRAMEWORKS_RETRIEVED"]
            if user_role == "internal-expert"
            else BUSINESS_MESSAGES["USER_FRAMEWORKS_RETRIEVED"]
        )
    if search or ai_extraction_status or request_review_status:
        return BUSINESS_MESSAGES["NO_FRAMEWORKS_MATCH_CRITERIA"]
    return (
        BUSINESS_MESSAGES["NO_FRAMEWORKS_FOR_REVIEW"]
        if user_role == "internal-expert"
        else BUSINESS_MESSAGES["NO_USER_FRAMEWORKS"]
    )


# ─── GET / (list) ───────────────────────────────────────────────────────────


@router.get("/")
async def get_deployment_frameworks(
    ctx: Annotated[RequestContext, Depends(get_context)],
    page: Annotated[int | None, Query(default=None)] = None,
    limit: Annotated[int, Query(default=10)] = 10,
    search: Annotated[str | None, Query(default=None)] = None,
    sort_by: Annotated[str | None, Query(alias="sortBy", default=None)] = None,
    sort_order: Annotated[str | None, Query(alias="sortOrder", default=None)] = None,
    ai_extraction_status: Annotated[str | None, Query(alias="aiExtractionStatus", default=None)] = None,
    request_review_status: Annotated[str | None, Query(alias="requestReviewStatus", default=None)] = None,
):
    user = ctx.user
    tenant_id = ctx.tenant_id
    allowed_sort_fields = [
        "createdAt",
        "updatedAt",
        "frameworkName",
        "fileType",
        "fileSize",
        "originalFileName",
    ]

    async with session_scope() as session:
        base_filters = []
        if user.role != "internal-expert":
            base_filters.append(DeploymentFramework.tenantId == tenant_id)

        stmt = select(DeploymentFramework)
        for f in base_filters:
            stmt = stmt.where(f)
        all_docs = list((await session.execute(stmt)).scalars().all())

        if user.role == "internal-expert":
            all_docs = _filter_for_internal_expert(all_docs, str(user.id))
        elif user.role == "user":
            all_docs = _filter_for_user(all_docs)

        if search:
            term = search.lower()
            all_docs = [
                d
                for d in all_docs
                if term in (d.frameworkName or "").lower() or term in (d.frameworkVersion or "").lower()
            ]

        sort_field = sort_by if sort_by in allowed_sort_fields else "createdAt"
        reverse = (sort_order or "").lower() != "asc"
        all_docs.sort(key=lambda d: getattr(d, sort_field, None) or d.createdAt, reverse=reverse)

        maps = await data_formatter.hydrate_maps(session, all_docs)
        formatted = [data_formatter.format_deployment_framework_list_item(doc, maps) for doc in all_docs]

        if ai_extraction_status:
            formatted = [
                d for d in formatted if (d.get("aiExtraction") or {}).get("status") == ai_extraction_status
            ]
        if request_review_status:
            formatted = [
                d for d in formatted if (d.get("requestReview") or {}).get("status") == request_review_status
            ]

        page_num = query_builder.clamp_page(page)
        limit_num = query_builder.clamp_limit(limit)
        total = len(formatted)
        start = (page_num - 1) * limit_num
        result = {
            "data": formatted[start : start + limit_num],
            "pagination": query_builder.build_pagination_meta(page_num, limit_num, total),
        }

        message = _get_list_response_message(
            user.role, bool(result["data"]), search, ai_extraction_status, request_review_status
        )

        return paginated(result["data"], result["pagination"], message)


# ─── GET /client-controls ───────────────────────────────────────────────────


def _get_live_package(framework: Any) -> Any | None:
    packages = coerce_packages(framework.packages)
    return next((p for p in packages if p.status == "live"), None)


def _format_client_control(fw: Any, live_package: Any, merge: Any | None) -> dict[str, Any]:
    controls_data = _blob_get(merge.mergeExtraction if merge else None, "controls_data") or []
    return {
        "frameworkId": str(fw.id) if fw and getattr(fw, "id", None) else None,
        "frameworkName": fw.frameworkName,
        "frameworkVersion": fw.frameworkVersion,
        "packageVersion": live_package.packageVersion,
        "controls": controls_data or [],
    }


@router.get("/client-controls")
async def get_deployment_framework_package_client_controls(
    ctx: Annotated[RequestContext, Depends(get_context)],
):
    async with session_scope() as session:
        frameworks = list(
            (
                await session.execute(
                    select(DeploymentFramework).where(DeploymentFramework.tenantId == ctx.tenant_id)
                )
            )
            .scalars()
            .all()
        )
        merge_ids = []
        live_by_fw = []
        for fw in frameworks:
            live_package = _get_live_package(fw)
            if not live_package:
                continue
            live_by_fw.append((fw, live_package))
            if live_package.mergeDocument:
                merge_ids.append(str(live_package.mergeDocument))

        merges: dict[str, PackageMerge] = {}
        if merge_ids:
            rows = (
                (await session.execute(select(PackageMerge).where(PackageMerge.id.in_(merge_ids))))
                .scalars()
                .all()
            )
            merges = {str(m.id): m for m in rows}

        client_controls = []
        for fw, live_package in live_by_fw:
            merge = merges.get(str(live_package.mergeDocument)) if live_package.mergeDocument else None
            client_controls.append(_format_client_control(fw, live_package, merge))

        return success(client_controls, "Client controls retrieved successfully")


# ─── PATCH /:id/deployment-points ───────────────────────────────────────────


def _update_deployment_point_path(
    controls_data: list[Any], section_id: str | None, control_id: str, point_id: str, path_value: str
) -> bool:
    for section in controls_data:
        if section_id and section.get("id") != section_id:
            continue
        control = next((c for c in (section.get("controls") or []) if c.get("id") == control_id), None)
        if not control:
            continue
        dp = next(
            (d for d in (control.get("deployment_points") or []) if d.get("id") == point_id),
            None,
        )
        if not dp:
            continue
        dp["path"] = path_value
        return True
    return False


@router.patch("/{id}/deployment-points")
async def update_deployment_package_point_path(
    id: str,
    ctx: Annotated[RequestContext, Depends(get_context)],
    body: Annotated[dict[str, Any], Body(...)],
):
    control_id = body.get("controlId")
    point_id = body.get("pointId")
    path_value = body.get("path")
    package_version = body.get("packageVersion")
    section_id = body.get("sectionId")

    if not control_id or not point_id or not package_version or path_value is None:
        return error(
            "packageVersion, controlId, pointId and path are required fields in the request body",
            400,
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
            return not_found(_RESOURCE_DEPLOYMENT_FRAMEWORK)

        packages = coerce_packages(framework.packages)
        target_package = next((p for p in packages if p.packageVersion == package_version), None)
        if not target_package:
            return not_found(_RESOURCE_PACKAGE_VERSION)

        if not target_package.mergeDocument:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["PACKAGE_MERGE_DOCUMENT_NOT_FOUND"])

        package_merge = (
            await session.execute(
                select(PackageMerge).where(
                    PackageMerge.id == str(target_package.mergeDocument),
                    PackageMerge.frameworkId == str(framework.id),
                )
            )
        ).scalar_one_or_none()
        if not package_merge:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["PACKAGE_MERGE_DOCUMENT_NOT_FOUND"])

        merge_data = dict(package_merge.mergeExtraction or {})
        controls_data = list(merge_data.get("controls_data") or [])

        point_found = _update_deployment_point_path(
            controls_data, section_id, control_id, point_id, path_value
        )

        if not point_found:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["CONTROL_OR_DEPLOYMENT_POINT_NOT_FOUND"])

        merge_data["controls_data"] = controls_data
        package_merge.mergeExtraction = merge_data

        return success(
            {
                "frameworkId": (str(framework.id) if framework and getattr(framework, "id", None) else None),
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
async def get_deployment_framework_by_id(id: str, ctx: Annotated[RequestContext, Depends(get_context)]):
    user = ctx.user
    async with session_scope() as session:
        framework = await session.get(DeploymentFramework, str(id))
        if not framework:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"])

        if user.role != "expert" and framework.tenantId != ctx.tenant_id:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"])

        packages = coerce_packages(framework.packages)
        if user.role in ("expert", "internal-expert"):
            assigned_packages = [p for p in packages if _expert_assigned(p, str(user.id))]
            if not assigned_packages:
                return not_found(FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"])
            framework.packages = dump_packages(assigned_packages)
            latest = helpers.get_latest_package(assigned_packages)
            if latest:
                framework.currentPackageVersion = latest.packageVersion
        else:
            current_package = helpers.get_current_package(framework)
            if user.role == "user" and (
                not current_package
                or not current_package.expertReview
                or current_package.expertReview.status != "approved"
            ):
                return error(BUSINESS_MESSAGES["FRAMEWORK_ACCESS_DENIED"], 403)

        maps = await data_formatter.hydrate_maps(session, [framework])
        response_data = data_formatter.format_deployment_framework(framework, maps, True)
        return success(response_data, BUSINESS_MESSAGES["FRAMEWORK_RETRIEVED_SUCCESS"])


# ─── GET /:id/packages/:packageVersion ──────────────────────────────────────


def _validate_package_access(user_role: str, user_id: str, found_package: Any) -> JSONResponse | None:
    if user_role == "internal-expert":
        assigned_expert_id = (
            str(found_package.expertReview.assignedExpert)
            if found_package.expertReview and found_package.expertReview.assignedExpert
            else None
        )
        is_not_pending = (
            found_package.expertReview.status != "pending" if found_package.expertReview else False
        )
        if assigned_expert_id != str(user_id) or not is_not_pending:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"])
    elif user_role == "user":
        if not found_package.expertReview or found_package.expertReview.status != "approved":
            return error(BUSINESS_MESSAGES["FRAMEWORK_ACCESS_DENIED"], 403)
    return None


@router.get("/{id}/packages/{packageVersion}")
async def get_deployment_framework_package_by_version(
    id: str,
    package_version: Annotated[str, Path(alias="packageVersion")],
    ctx: Annotated[RequestContext, Depends(get_context)],
):
    user = ctx.user
    async with session_scope() as session:
        framework = await session.get(DeploymentFramework, str(id))
        if not framework:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"])

        if user.role != "expert" and framework.tenantId != ctx.tenant_id:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"])

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == package_version), None)
        if not found_package:
            return not_found(_RESOURCE_PACKAGE_VERSION)

        validation_error = _validate_package_access(user.role, str(user.id), found_package)
        if validation_error:
            return validation_error

        framework.packages = dump_packages([found_package])
        framework.currentPackageVersion = package_version

        maps = await data_formatter.hydrate_maps(session, [framework])
        response_data = data_formatter.format_deployment_framework(framework, maps, False)
        return success(response_data, BUSINESS_MESSAGES["FRAMEWORK_RETRIEVED_SUCCESS"])


# ─── PUT /:id (update / new patch) ──────────────────────────────────────────


async def _process_uploaded_files(files: list[UploadFile]) -> list[dict[str, Any]] | JSONResponse:
    file_entries = []
    for f in files:
        content = await f.read()
        validation = file_storage.validate_uploaded_file(f.filename or "", len(content))
        if not validation.get("isValid"):
            return error(validation.get("message"), validation.get("status"))
        file_entries.append({"filename": f.filename or "file", "content": content})
    return file_entries


def _check_missing_files(new_package_documents: list[Any]) -> JSONResponse | None:
    missing_file_docs = [
        d
        for d in new_package_documents
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
    return None


@router.put("/{id}")
async def update_deployment_framework(
    id: str,
    ctx: Annotated[RequestContext, Depends(get_context)],
    files: Annotated[list[UploadFile], File(default=[])] = [],
    metadata: Annotated[str | None, Form(default=None)] = None,
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
                )
                .scalars()
                .all()
            )
            framework = None
            for fw in candidates:
                if helpers.find_framework_document(fw, id):
                    framework = fw
                    break

        if not framework:
            return not_found(_RESOURCE_DEPLOYMENT_FRAMEWORK)

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
            return error(FRAMEWORK_SERVICE_MESSAGES["INVALID_PATCH_TYPE"], 400)

        try:
            file_entries = await _process_uploaded_files(files)
            if isinstance(file_entries, JSONResponse):
                return file_entries

            if patch_type == "minor":
                result = package_builder.build_minor_patch(framework, file_entries, document_updates)
            else:
                result = package_builder.build_major_patch(framework, file_entries, document_updates)

            uploaded_files_map = {f["filename"]: f["content"] for f in file_entries}
            save_result = helpers.save_uploaded_files_for_package(
                framework, uploaded_files_map, result, str(ctx.user.id)
            )
            if save_result.get("error"):
                return error(f"Failed to save file: {save_result['filename']}", 500)

            missing_files_error = _check_missing_files(result["newPackage"]["documents"])
            if missing_files_error:
                return missing_files_error

            validation = package_builder.validate_package(result["newPackage"])
            if not validation["isValid"]:
                return error(f"Package validation failed: {', '.join(validation['errors'])}", 400)

            from vora_shared.models.deployment_framework import (
                FrameworkPackageDocument,
                PackageVersion,
            )

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

            return success(
                {
                    "id": (str(framework.id) if framework and getattr(framework, "id", None) else None),
                    "frameworkId": (
                        str(framework.frameworkId)
                        if framework and getattr(framework, "frameworkId", None)
                        else None
                    ),
                    "frameworkName": framework.frameworkName,
                    "frameworkCode": framework.frameworkCode,
                    "frameworkVersion": framework.frameworkVersion,
                    "currentPackageVersion": framework.currentPackageVersion,
                    "packageVersion": new_package.packageVersion,
                    "patchType": patch_type,
                    "documentsCount": len(new_package.documents),
                    "updatedAt": framework.updatedAt,
                },
                f"Framework {patch_type} patch created successfully",
            )
        except Exception as exc:
            logger.exception("Framework update error")
            return error(str(exc), 500)


# ─── DELETE /:id ─────────────────────────────────────────────────────────────


@router.delete("/{id}")
async def delete_deployment_framework(id: str, ctx: Annotated[RequestContext, Depends(get_context)]):
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
            return not_found(_RESOURCE_DEPLOYMENT_FRAMEWORK)

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
                logger.exception("Failed to delete file %s: %s", file_url, exc)

        try:
            await session.execute(delete(PackageMerge).where(PackageMerge.frameworkId == str(framework.id)))
            await session.execute(
                delete(PackageComparison).where(PackageComparison.frameworkId == str(framework.id))
            )
            await session.execute(
                delete(PackageGapAnalysis).where(PackageGapAnalysis.frameworkId == str(framework.id))
            )
        except Exception as db_error:
            logger.exception("Failed to delete associated merges, comparisons and gap analyses: %s", db_error)

        await session.delete(framework)
        return success(None, "Framework deleted successfully")


# ─── POST /upload ────────────────────────────────────────────────────────────


@router.post("/upload", status_code=201)
async def upload_deployment_framework(
    ctx: Annotated[RequestContext, Depends(get_context)],
    file: Annotated[list[UploadFile] | None, File(default=None)] = None,
    files: Annotated[list[UploadFile] | None, File(default=None)] = None,
    metadata: Annotated[str | None, Form(default=None)] = None,
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
        return error(FRAMEWORK_SERVICE_MESSAGES["AT_LEAST_ONE_FILE_REQUIRED"], 400)

    version = meta.get("fileVersion") or "1.0.0"

    process_result = await helpers.process_uploaded_files(
        all_files, framework_id, str(user_id), framework_version
    )
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
            assignedFrameworkId=(str(assigned_framework_id) if assigned_framework_id else new_framework_id),
            frameworkCategoryId=framework_category_id,
            frameworkCode=framework_code,
            frameworkVersion=framework_version,
            currentPackageVersion=version,
            packages=dump_packages([package_version_model]),
            uploadedBy=str(user_id),
        )
        session.add(deployment_framework)
        await session.flush()

        return success(
            {
                "frameworkId": (
                    str(deployment_framework.id)
                    if deployment_framework and getattr(deployment_framework, "id", None)
                    else None
                ),
                "fileIds": [d.fileId for d in document_models],
                "fileNames": [d.originalFileName for d in document_models],
                "packageVersion": version,
                "frameworkName": deployment_framework.frameworkName,
                "uploadUrls": [d.fileUrl for d in document_models],
            },
            "File uploaded successfully",
            201,
        )


# ─── GET /:frameworkId/files/:fileId/preview ────────────────────────────────


@router.get("/{frameworkId}/files/{fileId}/preview")
async def preview_framework_file(
    framework_id: Annotated[str, Path(alias="frameworkId")],
    file_id: Annotated[str, Path(alias="fileId")],
    ctx: Annotated[RequestContext, Depends(get_context)],
):
    async with session_scope() as session:
        framework = await session.get(DeploymentFramework, str(framework_id))
        if not framework or not helpers.find_framework_document(framework, file_id):
            return not_found(FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"])

        document = helpers.find_framework_document(framework, file_id)
        if not document:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["DOCUMENT_NOT_FOUND"])

        actual_file_path = helpers.get_upload_file_path(document.fileUrl)
        if not actual_file_path or not os.path.exists(actual_file_path):
            return not_found(FRAMEWORK_SERVICE_MESSAGES["FILE_ON_DISK_NOT_FOUND"])

        mime = helpers.MIME_TYPES.get(str(document.fileType).lower(), "application/octet-stream")
        return FileResponse(
            actual_file_path,
            media_type=mime,
            filename=document.originalFileName,
            content_disposition_type="inline",
        )


# ─── GET /:frameworkId/files/:fileId/download ───────────────────────────────


@router.get("/{frameworkId}/files/{fileId}/download")
async def download_framework_file(
    framework_id: Annotated[str, Path(alias="frameworkId")],
    file_id: Annotated[str, Path(alias="fileId")],
    ctx: Annotated[RequestContext, Depends(get_context)],
):
    async with session_scope() as session:
        framework = await session.get(DeploymentFramework, str(framework_id))
        if not framework or not helpers.find_framework_document(framework, file_id):
            return not_found(FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"])

        document = helpers.find_framework_document(framework, file_id)
        if not document:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["DOCUMENT_NOT_FOUND"])

        actual_file_path = helpers.get_upload_file_path(document.fileUrl)
        if not actual_file_path or not os.path.exists(actual_file_path):
            return not_found(FRAMEWORK_SERVICE_MESSAGES["FILE_ON_DISK_NOT_FOUND"])

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
    framework_id: Annotated[str, Path(alias="frameworkId")],
    package_version: Annotated[str, Path(alias="packageVersion")],
    ctx: Annotated[RequestContext, Depends(get_context)],
):
    tenant_id = ctx.tenant_id

    async with session_scope() as session:
        framework = (
            await session.execute(
                select(DeploymentFramework).where(
                    DeploymentFramework.id == str(framework_id),
                    DeploymentFramework.tenantId == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not framework:
            return not_found(_RESOURCE_DEPLOYMENT_FRAMEWORK)

        packages = coerce_packages(framework.packages)
        package_index = next((i for i, p in enumerate(packages) if p.packageVersion == package_version), -1)
        if package_index == -1:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["PACKAGE_NOT_FOUND"])

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
                logger.exception("Failed to delete package file from disk: %s", exc)

        packages.pop(package_index)

        if is_deleting_current:
            latest_package = helpers.get_latest_package(packages)
            if latest_package:
                framework.currentPackageVersion = latest_package.packageVersion

        framework.packages = dump_packages(packages)
        framework.updatedAt = _utcnow()
        return success(
            {"currentPackageVersion": framework.currentPackageVersion},
            "Package deleted successfully",
        )


# ─── GET /:id/packages/:packageVersion/report ───────────────────────────────


def _validate_report_statuses(found_package: Any, maps: dict[str, Any]) -> JSONResponse | None:
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
    return None


@router.get("/{id}/packages/{packageVersion}/report")
async def download_deployment_framework_report(
    id: str,
    package_version: Annotated[str, Path(alias="packageVersion")],
    ctx: Annotated[RequestContext, Depends(get_context)],
):
    user = ctx.user
    async with session_scope() as session:
        stmt = select(DeploymentFramework).where(DeploymentFramework.id == str(id))
        if user.role not in ("expert", "internal-expert"):
            stmt = stmt.where(DeploymentFramework.tenantId == ctx.tenant_id)

        framework = (await session.execute(stmt)).scalar_one_or_none()
        if not framework:
            return not_found(_RESOURCE_DEPLOYMENT_FRAMEWORK)

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == package_version), None)
        if not found_package:
            return not_found(_RESOURCE_PACKAGE_VERSION)

        maps = await data_formatter.hydrate_maps(session, [framework])
        validation_error = _validate_report_statuses(found_package, maps)
        if validation_error:
            return validation_error

        package_dict = data_formatter.format_package(found_package, maps, exclude_details=False)
        pdf_bytes = generate_deployment_framework_report_pdf(framework, package_dict)
        filename = (
            f"{re.sub(r'[^a-zA-Z0-9]', '_', framework.frameworkName or 'framework')}_"
            f"{package_version.replace('.', '_')}_report.pdf"
        )

        from fastapi import Response

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


# ─── POST /:id/request-review ───────────────────────────────────────────────


@router.post("/{id}/request-review")
async def request_expert_review(
    id: str, ctx: Annotated[RequestContext, Depends(get_context)], body: Annotated[dict[str, Any], Body(...)]
):
    user = ctx.user
    tenant_id = ctx.tenant_id
    package_version = body.get("packageVersion")
    expert_id = body.get("expertId")

    if user.role != "auditor":
        return forbidden("Only auditors can request expert reviews")

    if not package_version:
        return error(FRAMEWORK_SERVICE_MESSAGES["PACKAGE_VERSION_REQUIRED"], 400)
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
            return not_found(_RESOURCE_DEPLOYMENT_FRAMEWORK)

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == package_version), None)
        if not found_package:
            return not_found(_RESOURCE_PACKAGE_VERSION)

        if found_package.expertReview and found_package.expertReview.status != "pending":
            return error(FRAMEWORK_MESSAGES["REVIEW_ALREADY_REQUESTED"], 400)

        expert_user = (
            await session.execute(select(User).where(User.id == str(expert_id), User.isActive.is_(True)))
        ).scalar_one_or_none()
        if not expert_user:
            return not_found(FRAMEWORK_MESSAGES["EXPERT_NOT_FOUND"])

        if expert_user.role != "internal-expert":
            return error(FRAMEWORK_SERVICE_MESSAGES["ASSIGNED_USER_MUST_BE_INTERNAL_EXPERT"], 400)

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
                "frameworkId": (str(framework.id) if framework and getattr(framework, "id", None) else None),
                "packageVersion": package_version,
                "expertReview": {
                    "status": found_package.expertReview.status,
                    "assignedExpert": {
                        "id": (
                            str(expert_user.id) if expert_user and getattr(expert_user, "id", None) else None
                        ),
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


def _apply_review_action(
    action: str,
    framework: Any,
    packages: list[Any],
    found_package: Any,
    package_version: str,
    comments: str | None,
) -> None:
    if action == "approve":
        for pkg in packages:
            if pkg.status == "live" and pkg.packageVersion != package_version:
                pkg.status = "superseded"
                pkg.updatedAt = _utcnow()

        found_package.type = "deployed"
        found_package.status = "live"
        found_package.expertReview.status = "approved"
        found_package.expertReview.reviewedAt = _utcnow()
        found_package.expertReview.comments = comments
        found_package.updatedAt = _utcnow()
        framework.currentPackageVersion = package_version
    else:
        found_package.type = "pre-release"
        found_package.status = "returned"
        found_package.expertReview.status = "rejected"
        found_package.expertReview.reviewedAt = _utcnow()
        found_package.expertReview.comments = comments
        found_package.updatedAt = _utcnow()


@router.patch("/{id}/packages/{packageVersion}/review")
async def review_deployment_package(
    id: str,
    package_version: Annotated[str, Path(alias="packageVersion")],
    ctx: Annotated[RequestContext, Depends(get_context)],
    body: Annotated[dict[str, Any], Body(...)],
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
            return not_found(_RESOURCE_DEPLOYMENT_FRAMEWORK)

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == package_version), None)
        if not found_package:
            return not_found(_RESOURCE_PACKAGE_VERSION)

        if not found_package.expertReview or found_package.expertReview.status != "requested":
            return error(FRAMEWORK_MESSAGES["REVIEW_NOT_REQUESTED"], 400)

        assigned_expert_id = (
            str(found_package.expertReview.assignedExpert)
            if found_package.expertReview.assignedExpert
            else None
        )
        if assigned_expert_id != str(user.id):
            return forbidden(FRAMEWORK_MESSAGES["ONLY_ASSIGNED_FRAMEWORKS"])

        _apply_review_action(action, framework, packages, found_package, package_version, comments)

        framework.packages = dump_packages(packages)
        framework.updatedAt = _utcnow()

        message = (
            FRAMEWORK_MESSAGES["FRAMEWORK_APPROVED"]
            if action == "approve"
            else FRAMEWORK_MESSAGES["FRAMEWORK_RETURNED"]
        )
        return success(
            {
                "frameworkId": (str(framework.id) if framework and getattr(framework, "id", None) else None),
                "packageVersion": package_version,
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


def _update_comparison_review_remark(
    results: list[Any], assigned_control_id: str, deployment_control_id: str, comment: str | None
) -> bool:
    for section in results:
        controls = (
            section.get("controls") if isinstance(section, dict) else getattr(section, "controls", None)
        )
        for c in controls or []:
            c_assigned = (
                c.get("assigned_framework_control_id")
                if isinstance(c, dict)
                else getattr(c, "assigned_framework_control_id", None)
            )
            c_deploy = (
                c.get("deployment_framework_control_id")
                if isinstance(c, dict)
                else getattr(c, "deployment_framework_control_id", None)
            )
            if c_assigned == assigned_control_id and c_deploy == deployment_control_id:
                if isinstance(c, dict):
                    c["reviewComment"] = comment or ""
                else:
                    c.reviewComment = comment or ""
                return True
    return False


@router.post("/{id}/packegeVersion/{packegeVersion}/add-comparison-review-remark")
async def add_review_remark(
    id: str,
    package_version: Annotated[str, Path(alias="packegeVersion")],
    ctx: Annotated[RequestContext, Depends(get_context)],
    body: Annotated[dict[str, Any], Body(...)],
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
            return not_found(_RESOURCE_DEPLOYMENT_FRAMEWORK)

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == package_version), None)
        if not found_package:
            return not_found(_RESOURCE_PACKAGE_VERSION)

        if not found_package.comparison:
            return error(FRAMEWORK_SERVICE_MESSAGES["COMPARISON_NOT_COMPLETED_FOR_PACKAGE"], 400)

        package_comparison = await session.get(PackageComparison, str(found_package.comparison))
        if not package_comparison:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["PACKAGE_COMPARISON_DATA_NOT_FOUND"])

        comp = dict(package_comparison.comparison or {})
        results = list(comp.get("comparison_result") or [])
        control_found = _update_comparison_review_remark(
            results, assigned_control_id, deployment_control_id, comment
        )

        if not control_found:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["CONTROL_ALIGNMENT_NOT_FOUND_COMPARISON"])

        comp["comparison_result"] = results
        package_comparison.comparison = comp
        return success({"reviewComment": comment}, "Review remark added successfully")


# ─── POST /:id/packegeVersion/:packegeVersion/add-gap-review-remark ─────────


@router.post("/{id}/packegeVersion/{packegeVersion}/add-gap-review-remark")
async def add_gap_review_remark(
    id: str,
    package_version: Annotated[str, Path(alias="packegeVersion")],
    ctx: Annotated[RequestContext, Depends(get_context)],
    body: Annotated[dict[str, Any], Body(...)],
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
            return not_found(_RESOURCE_DEPLOYMENT_FRAMEWORK)

        packages = coerce_packages(framework.packages)
        found_package = next((p for p in packages if p.packageVersion == package_version), None)
        if not found_package:
            return not_found(_RESOURCE_PACKAGE_VERSION)

        if not found_package.gapAnalysis:
            return error(FRAMEWORK_SERVICE_MESSAGES["GAP_ANALYSIS_NOT_COMPLETED_FOR_PACKAGE"], 400)

        package_gap_analysis = await session.get(PackageGapAnalysis, str(found_package.gapAnalysis))
        if not package_gap_analysis:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["PACKAGE_GAP_ANALYSIS_DATA_NOT_FOUND"])

        gap = dict(package_gap_analysis.gapAnalysis or {})
        results = list(gap.get("deployment_gap_results") or [])

        point_found = helpers.update_gap_review_comment(
            results,
            assigned_control_id,
            assigned_point_id,
            deployment_control_id,
            deployment_point_id,
            comment,
        )
        if not point_found:
            return not_found(FRAMEWORK_SERVICE_MESSAGES["POINT_ALIGNMENT_NOT_FOUND_GAP_ANALYSIS"])

        gap["deployment_gap_results"] = results
        package_gap_analysis.gapAnalysis = gap
        return success({"reviewComment": comment}, "Gap review remark added successfully")
