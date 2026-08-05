"""Port of deployment-document-service-main/src/routes/deployment-document.routes.js
+ src/controllers/deployment-document.controller.js."""

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.services import data_formatter
from vora_shared import file_storage, query_builder
from vora_shared.database import session_scope
from vora_shared.ids import is_valid_id, new_id
from vora_shared.models import DeploymentDocument, DeploymentDocumentFileVersion, DeploymentFramework, User
from vora_shared.responses import error, paginated, success
from vora_shared.security import RequestContext, get_context

router = APIRouter()

BUSINESS_MESSAGES = {
    "DOCUMENT_ACCESS_DENIED": "You don't have permission to access this document",
    "DOCUMENT_RETRIEVED_SUCCESS": "Document retrieved successfully",
    "DEPLOYMENT_DOCUMENTS_RETRIEVED": "Deployment documents retrieved successfully",
    "USER_DOCUMENTS_RETRIEVED": "Your documents retrieved successfully",
    "NO_DOCUMENTS_MATCH_CRITERIA": (
        "No documents match your search criteria. Try adjusting your filters."
    ),
    "NO_DEPLOYMENT_DOCUMENTS": "No documents found in your deployment",
    "NO_USER_DOCUMENTS": (
        "You haven't uploaded any documents yet. Upload your first document to get started."
    ),
}

_MIME_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
    "txt": "text/plain",
    "csv": "text/csv",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _g(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _coerce_file_versions(file_versions: list[Any] | None) -> list[DeploymentDocumentFileVersion]:
    result: list[DeploymentDocumentFileVersion] = []
    for v in file_versions or []:
        if isinstance(v, DeploymentDocumentFileVersion):
            result.append(v)
        else:
            result.append(DeploymentDocumentFileVersion.model_validate(v))
    return result


def _dump_file_versions(file_versions: list[Any] | None) -> list[dict[str, Any]]:
    out = []
    for v in file_versions or []:
        if hasattr(v, "model_dump"):
            out.append(v.model_dump(mode="json"))
        else:
            out.append(v)
    return out


@router.get("/")
async def get_all_documents(
    ctx: RequestContext = Depends(get_context),
    page: int | None = Query(default=None),
    limit: int = Query(default=10),
    search: str | None = Query(default=None),
    sortBy: str | None = Query(default=None),
    sortOrder: str | None = Query(default=None),
):
    tenant_id = ctx.tenant_id
    user = ctx.user

    base_filters = [DeploymentDocument.tenantId == tenant_id]
    if user.role == "user":
        base_filters.append(DeploymentDocument.uploadedBy == str(user.id))

    allowed_sort_fields = [
        "createdAt",
        "updatedAt",
        "documentName",
        "documentType",
        "fileSize",
        "originalFileName",
    ]

    async with session_scope() as session:

        async def transform(doc: DeploymentDocument) -> dict:
            versions = _coerce_file_versions(doc.fileVersions)
            current_version = next(
                (v for v in versions if v.fileVersion == doc.currentFileVersion), None
            )
            fw = (
                await session.get(DeploymentFramework, str(doc.deploymentFrameworkId))
                if doc.deploymentFrameworkId
                else None
            )
            uploaded_by_user = await session.get(User, str(doc.uploadedBy)) if doc.uploadedBy else None

            return {
                "id": str(doc.id) if doc and getattr(doc, "id", None) else None,
                "documentName": doc.documentName,
                "currentFileVersion": doc.currentFileVersion,
                "documentType": current_version.documentType if current_version else "pdf",
                "deploymentFramework": (
                    {
                        "id": str(fw.id) if fw and getattr(fw, "id", None) else None,
                        "frameworkName": fw.frameworkName,
                        "frameworkCode": fw.frameworkCode,
                        "frameworkVersion": fw.frameworkVersion,
                    }
                    if fw
                    else None
                ),
                "controlId": str(doc.controlId) if doc and getattr(doc, "controlId", None) else None,
                "controlName": doc.controlName,
                "deploymentPoint": doc.deploymentPoint,
                "fileInfo": {
                    "versionFileId": str(current_version.fileId)
                    if current_version and getattr(current_version, "fileId", None)
                    else None,
                    "originalFileName": (
                        current_version.originalFileName if current_version else "Unknown"
                    ),
                    "fileSize": data_formatter.format_file_size(
                        current_version.fileSize if current_version else 0
                    ),
                    "fileType": current_version.documentType if current_version else "pdf",
                },
                "uploadedBy": data_formatter.format_uploaded_by(uploaded_by_user, doc.uploadedBy),
                "aiUpload": {
                    "status": (
                        (current_version.aiUpload or {}).get("status")
                        if current_version and isinstance(current_version.aiUpload, dict)
                        else None
                    )
                },
                "createdAt": doc.createdAt,
                "updatedAt": doc.updatedAt,
            }

        result = await query_builder.paginate_with_search(
            session,
            DeploymentDocument,
            page=page,
            limit=limit,
            search=search,
            search_fields=["documentName"],
            base_filters=base_filters,
            sort_by=sortBy,
            sort_order=sortOrder,
            allowed_sort_fields=allowed_sort_fields,
            user_search={"tenant_id": tenant_id, "field_name": "uploadedBy"},
            transform=transform,
        )

        message = (
            BUSINESS_MESSAGES["DEPLOYMENT_DOCUMENTS_RETRIEVED"]
            if user.role == "customer-admin"
            else BUSINESS_MESSAGES["USER_DOCUMENTS_RETRIEVED"]
        )
        if not result["data"]:
            if search:
                message = BUSINESS_MESSAGES["NO_DOCUMENTS_MATCH_CRITERIA"]
            else:
                message = (
                    BUSINESS_MESSAGES["NO_DEPLOYMENT_DOCUMENTS"]
                    if user.role == "customer-admin"
                    else BUSINESS_MESSAGES["NO_USER_DOCUMENTS"]
                )

        return paginated(result["data"], result["pagination"], message)


@router.get("/{id}")
async def get_document_by_id(id: str, ctx: RequestContext = Depends(get_context)):
    if not is_valid_id(id):
        return error("Invalid document ID", 400)

    async with session_scope() as session:
        document = await session.get(DeploymentDocument, str(id))
        if not document:
            return error("Document not found", 404)

        if document.tenantId != ctx.tenant_id:
            return error("Document not found", 404)

        uploaded_by_user = await session.get(User, str(document.uploadedBy)) if document.uploadedBy else None

        if ctx.role == "user":
            if str(document.uploadedBy) != str(ctx.user.id):
                return error(BUSINESS_MESSAGES["DOCUMENT_ACCESS_DENIED"], 403)

        versions = _coerce_file_versions(document.fileVersions)
        formatted_versions = [
            {
                "fileVersion": v.fileVersion,
                "fileId": str(v.fileId) if v and getattr(v, "fileId", None) else None,
                "fileUrl": v.fileUrl,
                "fileHash": v.fileHash,
                "originalFileName": v.originalFileName,
                "fileSize": data_formatter.format_file_size(v.fileSize),
                "documentType": v.documentType,
                "uploadedAt": v.uploadedAt,
                "uploadedBy": data_formatter.format_uploaded_by(uploaded_by_user, document.uploadedBy),
                "aiUpload": v.aiUpload,
            }
            for v in versions
        ]
        formatted_versions.reverse()

        fw = (
            await session.get(DeploymentFramework, str(document.deploymentFrameworkId))
            if document.deploymentFrameworkId
            else None
        )

        response_data = {
            "document": {
                "id": str(document.id) if document and getattr(document, "id", None) else None,
                "documentName": document.documentName,
                "currentFileVersion": document.currentFileVersion,
                "deploymentFramework": (
                    {
                        "id": str(fw.id) if fw and getattr(fw, "id", None) else None,
                        "frameworkName": fw.frameworkName,
                        "frameworkCode": fw.frameworkCode,
                        "frameworkVersion": fw.frameworkVersion,
                    }
                    if fw
                    else None
                ),
                "controlId": str(document.controlId)
                if document and getattr(document, "controlId", None)
                else None,
                "controlName": document.controlName,
                "deploymentPoint": document.deploymentPoint,
                "fileVersions": formatted_versions,
                "createdAt": document.createdAt,
                "updatedAt": document.updatedAt,
            }
        }

        return success(response_data, BUSINESS_MESSAGES["DOCUMENT_RETRIEVED_SUCCESS"])


@router.delete("/{id}")
async def delete_document(id: str, ctx: RequestContext = Depends(get_context)):
    if not is_valid_id(id):
        return error("Invalid document ID", 400)

    async with session_scope() as session:
        document = (
            await session.execute(
                select(DeploymentDocument).where(
                    DeploymentDocument.id == str(id),
                    DeploymentDocument.tenantId == ctx.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not document:
            return error("Deployment document not found", 404)

        for version in _coerce_file_versions(document.fileVersions):
            try:
                file_storage.delete_file(version.fileUrl)
            except Exception:
                pass

        await session.delete(document)
        return success(None, "Document deleted successfully")


@router.put("/{id}")
async def update_document(
    id: str,
    ctx: RequestContext = Depends(get_context),
    documentName: str | None = Form(default=None),
    deploymentFrameworkId: str | None = Form(default=None),
    controlId: str | None = Form(default=None),
    controlName: str | None = Form(default=None),
    deploymentPoint: str | None = Form(default=None),
):
    if not is_valid_id(id):
        return error("Invalid document ID", 400)

    async with session_scope() as session:
        document = (
            await session.execute(
                select(DeploymentDocument).where(
                    DeploymentDocument.id == str(id),
                    DeploymentDocument.tenantId == ctx.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not document:
            return error("Deployment document not found", 404)

        if documentName and documentName != document.documentName:
            existing_name = (
                await session.execute(
                    select(DeploymentDocument).where(
                        DeploymentDocument.tenantId == ctx.tenant_id,
                        DeploymentDocument.documentName == documentName,
                    )
                )
            ).scalar_one_or_none()
            if existing_name and str(existing_name.id) != str(document.id):
                return error(f'A document named "{documentName}" already exists.', 400)
            document.documentName = documentName

        if deploymentFrameworkId is not None:
            document.deploymentFrameworkId = str(deploymentFrameworkId) if deploymentFrameworkId else None
        if controlId is not None:
            document.controlId = controlId or None
        if controlName is not None:
            document.controlName = controlName or None
        if deploymentPoint is not None:
            document.deploymentPoint = deploymentPoint or None

        document.updatedAt = _utcnow()
        return success(
            {
                "id": document.id,
                "documentName": document.documentName,
                "deploymentFrameworkId": document.deploymentFrameworkId,
                "controlId": document.controlId,
                "controlName": document.controlName,
                "deploymentPoint": document.deploymentPoint,
                "updatedAt": document.updatedAt,
            },
            "Document updated successfully",
        )


@router.post("/upload", status_code=201)
async def upload_deployment_document(
    ctx: RequestContext = Depends(get_context),
    file: UploadFile = File(...),
    documentName: str | None = Form(default=None),
    documentId: str | None = Form(default=None),
    deploymentFrameworkId: str | None = Form(default=None),
    controlId: str | None = Form(default=None),
    controlName: str | None = Form(default=None),
    deploymentPoint: str | None = Form(default=None),
    currentFileVersion: str | None = Form(default=None),
):
    tenant_id = ctx.tenant_id
    user_id = ctx.user.id

    if not file:
        return error("No file uploaded", 400)

    if not documentName and not documentId:
        return error("Document name or existing Document ID is required", 400)

    if not file_storage.is_valid_deployment_file_type(file.filename or ""):
        allowed = ", ".join(file_storage.get_allowed_deployment_file_types())
        return error(f"Invalid file type. Allowed types: {allowed}", 400)

    document_id_for_path = documentId or f"temp-{int(_utcnow().timestamp() * 1000)}"
    path_info = file_storage.generate_deployment_file_path(
        file.filename or "file", document_id_for_path, tenant_id, "document"
    )

    buffer = await file.read()
    if not file_storage.save_file(buffer, path_info.absolute_path):
        return error("Failed to save file", 500)

    file_hash = file_storage.calculate_file_hash(path_info.absolute_path)
    file_version = currentFileVersion or "1.0.0"
    file_id = new_id()
    document_type = (file.filename or "").rsplit(".", 1)[-1].lower()

    file_version_model = DeploymentDocumentFileVersion(
        fileVersion=file_version,
        fileId=file_id,
        fileUrl=path_info.absolute_path,
        fileHash=file_hash,
        originalFileName=file.filename or "file",
        fileSize=len(buffer),
        documentType=document_type,  # type: ignore[arg-type]
        uploadedAt=_utcnow(),
        aiUpload=None,
    )

    async with session_scope() as session:
        document: DeploymentDocument | None = None
        if documentId and is_valid_id(documentId):
            document = (
                await session.execute(
                    select(DeploymentDocument).where(
                        DeploymentDocument.id == str(documentId),
                        DeploymentDocument.tenantId == tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if document:
                if documentName and documentName != document.documentName:
                    existing_name = (
                        await session.execute(
                            select(DeploymentDocument).where(
                                DeploymentDocument.tenantId == tenant_id,
                                DeploymentDocument.documentName == documentName,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing_name and str(existing_name.id) != str(document.id):
                        try:
                            file_storage.delete_file(path_info.absolute_path)
                        except Exception:
                            pass
                        return error(f'A document named "{documentName}" already exists.', 400)
                    document.documentName = documentName
                versions = _coerce_file_versions(document.fileVersions)
                versions.append(file_version_model)
                document.fileVersions = _dump_file_versions(versions)
                document.currentFileVersion = file_version
                document.updatedAt = _utcnow()

        if not document:
            name_to_check = documentName or file.filename
            existing_document = (
                await session.execute(
                    select(DeploymentDocument).where(
                        DeploymentDocument.tenantId == tenant_id,
                        DeploymentDocument.documentName == name_to_check,
                    )
                )
            ).scalar_one_or_none()
            if existing_document:
                try:
                    file_storage.delete_file(path_info.absolute_path)
                except Exception:
                    pass
                return error(
                    f'A document named "{name_to_check}" already exists. Please choose a different name.',
                    400,
                )

            document = DeploymentDocument(
                tenantId=tenant_id,
                documentName=name_to_check or "document",
                fileVersions=_dump_file_versions([file_version_model]),
                currentFileVersion=file_version,
                uploadedBy=str(user_id),
                deploymentFrameworkId=str(deploymentFrameworkId) if deploymentFrameworkId else None,
                controlId=controlId or None,
                controlName=controlName or None,
                deploymentPoint=deploymentPoint or None,
            )
            session.add(document)
            await session.flush()

        return success(
            {
                "documentId": str(document.id) if document and getattr(document, "id", None) else None,
                "fileId": file_id,
                "fileName": file.filename,
                "fileSize": len(buffer),
                "fileVersion": file_version,
                "documentName": document.documentName,
                "uploadUrl": file_version_model.fileUrl,
            },
            "Document uploaded successfully",
            201,
        )


@router.get("/{documentId}/files")
async def get_document_files(documentId: str, ctx: RequestContext = Depends(get_context)):
    if not is_valid_id(documentId):
        return error("Invalid document ID", 400)

    async with session_scope() as session:
        document = (
            await session.execute(
                select(DeploymentDocument).where(
                    DeploymentDocument.id == str(documentId),
                    DeploymentDocument.tenantId == ctx.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not document:
            return error("Deployment document not found", 404)

        versions = _coerce_file_versions(document.fileVersions)
        files = [
            {
                "id": v.fileId,
                "fileName": v.originalFileName,
                "fileSize": v.fileSize,
                "fileVersion": v.fileVersion,
                "documentType": v.documentType,
                "uploadedAt": v.uploadedAt,
                "fileUrl": v.fileUrl,
                "isCurrentVersion": v.fileVersion == document.currentFileVersion,
                "aiUpload": v.aiUpload,
            }
            for v in versions
        ]
        files.sort(key=lambda f: f["uploadedAt"] or _utcnow(), reverse=True)

        return success(
            {
                "documentId": str(document.id) if document and getattr(document, "id", None) else None,
                "documentName": document.documentName,
                "currentFileVersion": document.currentFileVersion,
                "files": files,
            },
            "Files retrieved successfully",
        )


@router.get("/{documentId}/files/{fileId}")
async def get_document_file_by_id(
    documentId: str, fileId: str, ctx: RequestContext = Depends(get_context)
):
    if not is_valid_id(documentId):
        return error("Invalid document ID", 400)

    async with session_scope() as session:
        document = (
            await session.execute(
                select(DeploymentDocument).where(
                    DeploymentDocument.id == str(documentId),
                    DeploymentDocument.tenantId == ctx.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not document:
            return error("Deployment document not found", 404)

        versions = _coerce_file_versions(document.fileVersions)
        file_version = next((v for v in versions if str(v.fileId) == fileId), None)
        if not file_version:
            return error("File not found", 404)

        uploaded_by_user = await session.get(User, str(document.uploadedBy)) if document.uploadedBy else None

        return success(
            {
                "documentId": str(document.id) if document and getattr(document, "id", None) else None,
                "documentName": document.documentName,
                **file_version.model_dump(mode="json"),
                "isCurrentVersion": file_version.fileVersion == document.currentFileVersion,
                "uploadedBy": (
                    {
                        "id": str(uploaded_by_user.id)
                        if uploaded_by_user and getattr(uploaded_by_user, "id", None)
                        else None,
                        "name": uploaded_by_user.name,
                        "email": uploaded_by_user.email,
                    }
                    if uploaded_by_user
                    else document.uploadedBy
                ),
            },
            "File retrieved successfully",
        )


@router.get("/{documentId}/files/{fileId}/download")
async def download_document_file(
    documentId: str, fileId: str, ctx: RequestContext = Depends(get_context)
):
    if not is_valid_id(documentId):
        return error("Invalid document ID", 400)

    async with session_scope() as session:
        document = (
            await session.execute(
                select(DeploymentDocument).where(
                    DeploymentDocument.id == str(documentId),
                    DeploymentDocument.tenantId == ctx.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not document:
            return error("Deployment document not found", 404)

        versions = _coerce_file_versions(document.fileVersions)
        file_version = next((v for v in versions if str(v.fileId) == fileId), None)
        if not file_version:
            return error("File not found", 404)

        file_path = os.path.abspath(file_version.fileUrl)
        if not file_storage.file_exists(file_path):
            return error("File on disk not found", 404)

        return FileResponse(
            file_path,
            media_type="application/octet-stream",
            filename=file_version.originalFileName,
            content_disposition_type="attachment",
        )


@router.get("/{documentId}/files/{fileId}/preview")
async def preview_document_file(
    documentId: str, fileId: str, ctx: RequestContext = Depends(get_context)
):
    if not is_valid_id(documentId):
        return error("Invalid document ID", 400)

    async with session_scope() as session:
        document = (
            await session.execute(
                select(DeploymentDocument).where(
                    DeploymentDocument.id == str(documentId),
                    DeploymentDocument.tenantId == ctx.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not document:
            return error("Deployment document not found", 404)

        versions = _coerce_file_versions(document.fileVersions)
        file_version = next((v for v in versions if str(v.fileId) == fileId), None)
        if not file_version:
            return error("File not found", 404)

        actual_file_path = os.path.abspath(file_version.fileUrl)
        if not file_storage.file_exists(actual_file_path):
            return error("File on disk not found", 404)

        ext = (file_version.documentType or "").lower()
        mime = _MIME_TYPES.get(ext, "application/octet-stream")

        return FileResponse(
            actual_file_path,
            media_type=mime,
            filename=file_version.originalFileName,
            content_disposition_type="inline",
        )


@router.delete("/{documentId}/files/{fileId}")
async def delete_document_file(
    documentId: str, fileId: str, ctx: RequestContext = Depends(get_context)
):
    if not is_valid_id(documentId):
        return error("Invalid document ID", 400)

    async with session_scope() as session:
        document = (
            await session.execute(
                select(DeploymentDocument).where(
                    DeploymentDocument.id == str(documentId),
                    DeploymentDocument.tenantId == ctx.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not document:
            return error("Deployment document not found", 404)

        versions = _coerce_file_versions(document.fileVersions)
        file_index = next((i for i, v in enumerate(versions) if str(v.fileId) == fileId), -1)
        if file_index == -1:
            return error("File not found", 404)

        file_version = versions[file_index]

        if len(versions) == 1:
            return error("Cannot delete the only file version. Delete the entire document instead.", 400)

        if file_version.fileVersion == document.currentFileVersion:
            return error("Cannot delete the current file version.", 400)

        try:
            file_storage.delete_file(file_version.fileUrl)
        except Exception:
            pass

        versions.pop(file_index)
        document.fileVersions = _dump_file_versions(versions)
        document.updatedAt = _utcnow()
        return success(None, "File deleted successfully")
