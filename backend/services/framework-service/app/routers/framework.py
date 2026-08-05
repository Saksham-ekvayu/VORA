"""Port of framework.controller.js + framework.routes.js."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy import String, cast, func, or_, select, text
from sqlalchemy.exc import IntegrityError

from vora_shared import file_storage
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import Customer, FrameworkAssignment, FrameworkCategory, User
from vora_shared.models.framework import (
    AiExtraction,
    Approval,
    ControlItem,
    Controls,
    FileVersionEntry,
    Framework,
    Section,
)
from vora_shared.models.framework_assignment import AssignmentInfo
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import error, paginated, success

from app.dependencies import current_user
from app.helpers import framework_helper
from app.helpers.report_helper import generate_framework_report_pdf
from app.helpers.user_formatter import get_user_data
from app.schemas.framework import (
    AddControlBody,
    AssignFrameworkToCustomerBody,
    RejectFrameworkBody,
    UpdateControlBody,
    UpdateControlWeightageBody,
)
from app.services import data_formatter
from app.services.ai_service import AiServiceError, ai_service
from app.services.ai_websocket_service import ai_websocket_service

router = APIRouter(tags=["framework"])

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx"}
MAX_FILE_SIZE = 10 * 1024 * 1024
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
PREVIEW_MIME_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
    "txt": "text/plain",
    "csv": "text/csv",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


async def _validate_upload(file: UploadFile | None) -> tuple[bytes | None, str | None]:
    """Returns (file_bytes, error_message). error_message is None on success."""
    if file is None or not file.filename:
        return None, "No file uploaded"
    extension = _ext(file.filename)
    if extension not in ALLOWED_EXTENSIONS:
        return None, f"Invalid file type. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return None, "File size too large. Maximum size is 10MB"
    return content, None


async def _load_user(user_id) -> User | None:
    if not user_id:
        return None
    try:
        async with session_scope() as session:
            return await session.get(User, str(user_id))
    except Exception:
        return None


def _apply_ai_status_filter(stmt, ai_status: str | None):
    if not ai_status:
        return stmt
    return stmt.where(
        text(
            """EXISTS (
                SELECT 1
                FROM jsonb_array_elements(frameworks."fileVersions") AS elem
                WHERE elem->>'fileVersion' = frameworks."currentFileVersion"
                  AND elem->'aiExtraction'->>'status' = :ai_status
            )"""
        ).bindparams(ai_status=ai_status)
    )


# ─── Categories ───────────────────────────────────────────────────────────────


@router.get("/categories/available")
async def get_available_categories(
    user: User = Depends(current_user),
    page: int = Query(1),
    limit: int = Query(10),
    search: str | None = Query(default=None),
    isActive: str | None = Query(default=None),
    accessStatus: str | None = Query(default=None),
    sortBy: str | None = Query(default=None),
    sortOrder: str | None = Query(default=None),
):
    from vora_shared.models import FrameworkAccess

    page_num = clamp_page(page)
    limit_num = clamp_limit(limit)

    async with session_scope() as session:
        expert_requests = (
            await session.execute(
                select(FrameworkAccess).where(FrameworkAccess.expertId == user.id)
            )
        ).scalars().all()
        requested_map = {
            str(req.frameworkCategoryId): {"hasRequested": True, "status": req.status}
            for req in expert_requests
        }

        stmt = select(FrameworkCategory)
        if isActive is not None:
            stmt = stmt.where(FrameworkCategory.isActive.is_(isActive.lower() == "true"))

        if accessStatus:
            if accessStatus == "not_requested":
                requested_ids = [req.frameworkCategoryId for req in expert_requests]
                if requested_ids:
                    stmt = stmt.where(FrameworkCategory.id.notin_(requested_ids))
            else:
                matching_ids = [
                    req.frameworkCategoryId
                    for req in expert_requests
                    if req.status == accessStatus
                ]
                if matching_ids:
                    stmt = stmt.where(FrameworkCategory.id.in_(matching_ids))
                else:
                    stmt = stmt.where(text("false"))

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    FrameworkCategory.frameworkCategoryName.ilike(pattern),
                    FrameworkCategory.code.ilike(pattern),
                    FrameworkCategory.description.ilike(pattern),
                )
            )

        sort_field = "createdAt"
        if sortBy in {"createdAt", "frameworkCategoryName", "code"}:
            sort_field = sortBy
        col = getattr(FrameworkCategory, sort_field)
        if (sortOrder or "desc").lower() == "asc":
            stmt = stmt.order_by(col.asc())
        else:
            stmt = stmt.order_by(col.desc())

        total = (
            await session.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
        ).scalar_one()
        categories = list(
            (
                await session.execute(stmt.offset((page_num - 1) * limit_num).limit(limit_num))
            ).scalars().all()
        )

        creator_ids = {c.createdBy for c in categories if c.createdBy}
        creators_by_id = {}
        if creator_ids:
            creators = (
                await session.execute(select(User).where(User.id.in_(list(creator_ids))))
            ).scalars().all()
            creators_by_id = {u.id: u for u in creators}

        data = []
        for category in categories:
            request_info = requested_map.get(str(category.id), {"hasRequested": False, "status": None})
            data.append(
                {
                    "id": str(category.id),
                    "code": category.code,
                    "frameworkCategoryName": category.frameworkCategoryName,
                    "description": category.description,
                    "isActive": category.isActive,
                    "createdBy": get_user_data(creators_by_id.get(category.createdBy), category.createdBy),
                    "createdAt": category.createdAt,
                    "updatedAt": category.updatedAt,
                    "hasRequested": request_info["hasRequested"],
                    "requestStatus": request_info["status"],
                }
            )

    message = "Available framework categories retrieved successfully"
    if not data:
        message = (
            "No framework categories match your search criteria. Try adjusting your search terms."
            if search
            else "No framework categories are currently available. Please contact your administrator."
        )

    return paginated(data, build_pagination_meta(page_num, limit_num, total), message)


# ─── Listing ──────────────────────────────────────────────────────────────────


@router.get("/all-frameworks")
async def get_all_frameworks(
    user: User = Depends(current_user),
    page: int = Query(1),
    limit: int = Query(10),
    search: str | None = Query(default=None),
    aiStatus: str | None = Query(default=None),
    approvalStatus: str | None = Query(default=None),
    sortBy: str | None = Query(default=None),
    sortOrder: str | None = Query(default=None),
):
    page_num = clamp_page(page)
    limit_num = clamp_limit(limit)

    async with session_scope() as session:
        stmt = select(Framework)
        if approvalStatus in {"pending", "approved", "rejected"}:
            stmt = stmt.where(Framework.approval["status"].astext == approvalStatus)

        stmt = _apply_ai_status_filter(stmt, aiStatus)

        if search:
            pattern = f"%{search}%"
            search_conditions = [
                Framework.frameworkName.ilike(pattern),
                Framework.frameworkCode.ilike(pattern),
                Framework.frameworkVersion.ilike(pattern),
                cast(Framework.fileVersions, String).ilike(pattern),
            ]
            matching_user_ids = list(
                (
                    await session.execute(
                        select(User.id).where(
                            or_(User.name.ilike(pattern), User.email.ilike(pattern))
                        )
                    )
                ).scalars().all()
            )
            if matching_user_ids:
                search_conditions.append(Framework.uploadedBy.in_(matching_user_ids))
            stmt = stmt.where(or_(*search_conditions))

        allowed_sort_fields = {
            "createdAt", "updatedAt", "frameworkName", "frameworkCode",
        }
        sort_field = "createdAt"
        if sortBy in allowed_sort_fields:
            sort_field = sortBy
        col = getattr(Framework, sort_field)
        if (sortOrder or "desc").lower() == "asc":
            stmt = stmt.order_by(col.asc())
        else:
            stmt = stmt.order_by(col.desc())

        total = (
            await session.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
        ).scalar_one()
        docs = list(
            (
                await session.execute(stmt.offset((page_num - 1) * limit_num).limit(limit_num))
            ).scalars().all()
        )

        uploader_ids = {d.uploadedBy for d in docs}
        uploaders_by_id = {}
        if uploader_ids:
            uploaders = (
                await session.execute(select(User).where(User.id.in_(list(uploader_ids))))
            ).scalars().all()
            uploaders_by_id = {u.id: u for u in uploaders}

        data = [
            framework_helper.transform_framework_doc(doc, uploaders_by_id.get(doc.uploadedBy))
            for doc in docs
        ]

    message = framework_helper.get_framework_message(len(data), search, aiStatus, approvalStatus)
    return paginated(data, build_pagination_meta(page_num, limit_num, total), message)


# ─── Single framework ─────────────────────────────────────────────────────────


@router.get("/{id}")
async def get_framework_by_id(id: str, user: User = Depends(current_user)):
    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error("Framework not found", 404)

        uploaded_by_user = await session.get(User, str(framework.uploadedBy)) if framework.uploadedBy else None
        approved_by_id = framework_helper.approval_by(framework)
        approved_by_user = await session.get(User, str(approved_by_id)) if approved_by_id else None

        versions = framework_helper.parse_file_versions(framework)
        formatted_versions = [
            {
                "fileVersion": v.fileVersion,
                "fileId": str(v.fileId) if v and getattr(v, "fileId", None) else None,
                "fileUrl": v.fileUrl,
                "fileHash": v.fileHash,
                "originalFileName": v.originalFileName,
                "fileSize": data_formatter.format_file_size(v.fileSize),
                "fileType": v.fileType,
                "uploadedAt": v.uploadedAt,
                "aiExtraction": v.aiExtraction.model_dump(mode="json") if v.aiExtraction else None,
            }
            for v in reversed(versions)
        ]

        response_data = {
            "id": str(framework.id),
            "frameworkName": framework.frameworkName,
            "frameworkVersion": framework.frameworkVersion,
            "frameworkCode": framework.frameworkCode,
            "frameworkCategoryId": str(framework.frameworkCategoryId) if framework.frameworkCategoryId else None,
            "currentFileVersion": framework.currentFileVersion,
            "fileVersions": formatted_versions,
            "uploadedBy": data_formatter.format_uploaded_by(uploaded_by_user, framework.uploadedBy),
            "approval": {
                "status": framework_helper.approval_status(framework),
                "by": get_user_data(approved_by_user, approved_by_id) if approved_by_id else None,
                "date": framework_helper.approval_date(framework),
                "remark": framework_helper.approval_remark(framework),
            },
            "createdAt": framework.createdAt,
            "updatedAt": framework.updatedAt,
        }

    return success(response_data, "Framework retrieved successfully")


@router.get("/{id}/download-report")
async def download_framework_report(id: str, user: User = Depends(current_user)):
    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error("Framework not found", 404)

        approved_by_id = framework_helper.approval_by(framework)
        approved_by_user = await session.get(User, str(approved_by_id)) if approved_by_id else None
        pdf_bytes = generate_framework_report_pdf(framework, approved_by_user)

        safe_name = re.sub(r"[^a-zA-Z0-9]", "_", framework.frameworkName)
        filename = f"{safe_name}_report.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{id}/approve")
async def approve_framework(id: str, user: User = Depends(current_user)):
    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error("Framework not found", 404)

        if str(framework.uploadedBy) != str(user.id):
            return error("Only the user who uploaded the framework can approve it.", 403)

        if framework_helper.approval_status(framework) == "approved":
            return error("Framework is already approved", 400)

        current = framework_helper.get_current_file_version_data(framework)
        if not current or not current.aiExtraction:
            return error("Framework must be uploaded to AI before approval", 400)

        ai_status = current.aiExtraction.status
        if ai_status == "processing":
            return error("Framework AI processing is in progress. Please wait for completion", 409)
        if ai_status == "failed":
            return error("Framework AI processing failed", 409)

        invalid_control = framework_helper.find_invalid_control_weightage(current)
        if invalid_control:
            label = invalid_control.id or invalid_control.name
            return error(
                f"Control '{label}' must have a valid weightage between 1 and 10 before approval",
                400,
            )

        framework_helper.update_deployment_points_to_approved(current)
        framework_helper.apply_approved_versions(framework, current)
        approval = Approval(status="approved", by=user.id, date=_now(), remark=None)
        framework.approval = approval.model_dump(mode="json")
        framework.updatedAt = _now()
        await session.flush()

        approval_payload = {
            "status": approval.status,
            "by": {"id": str(user.id), "name": user.name, "email": user.email},
            "date": approval.date,
        }
        framework_id = str(framework.id)

    try:
        response = await ai_service.update_framework_approval_status(
            framework_id,
            {
                "status": approval_payload["status"],
                "timestamp": approval_payload["date"],
                "reason": None,
            },
        )
        print("✅ Framework approve successfully from AI service", response)
    except AiServiceError as exc:
        print("❌ Failed to approve framework from AI service", exc)

    return success(
        {"framework": {"id": framework_id, "approval": approval_payload}},
        "Framework approved successfully",
    )


@router.post("/{id}/reject")
async def reject_framework(
    id: str,
    body: RejectFrameworkBody,
    user: User = Depends(current_user),
):
    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error("Framework not found", 404)

        if framework_helper.approval_status(framework) == "rejected":
            return error("Framework is already rejected", 400)

        approval = Approval(
            status="rejected",
            by=user.id,
            date=_now(),
            remark=body.rejectionReason or "No reason provided",
        )
        framework.approval = approval.model_dump(mode="json")
        framework.updatedAt = _now()
        await session.flush()

        response_payload = {
            "framework": {
                "id": str(framework.id),
                "approval": {
                    "status": approval.status,
                    "by": {"id": str(user.id), "name": user.name, "email": user.email},
                    "date": approval.date,
                    "remark": approval.remark,
                },
            }
        }

    return success(response_payload, "Framework rejected successfully")


# ─── Assignment ───────────────────────────────────────────────────────────────


@router.post("/assign-framework-to-customer")
async def assign_framework_to_customer(
    body: AssignFrameworkToCustomerBody,
    user: User = Depends(current_user),
):
    if not body.customerId or not body.tenantId or not body.frameworkIds:
        return error(
            "customerId, tenantId, and frameworkIds (non-empty array) are required fields.",
            400,
        )

    async with session_scope() as session:
        customer = (
            await session.execute(
                select(Customer).where(
                    Customer.id == str(body.customerId),
                    Customer.tenantId == body.tenantId,
                )
            )
        ).scalar_one_or_none()
        if not customer:
            return error("Customer organization not found.", 404)
        if not customer.isActive:
            return error("Customer organization is not active.", 404)

        framework_ids = [str(fid) for fid in body.frameworkIds]
        frameworks = list(
            (
                await session.execute(select(Framework).where(Framework.id.in_(framework_ids)))
            ).scalars().all()
        )
        if not frameworks:
            return error("Frameworks not found", 404)
        if len(frameworks) != len(framework_ids):
            return error("One or more provided framework IDs are invalid.", 400)

        unapproved = [
            f for f in frameworks if framework_helper.approval_status(f) != "approved"
        ]
        if unapproved:
            names = ", ".join(f.frameworkName for f in unapproved)
            return error(f"Cannot assign unapproved frameworks: {names}", 400)

        for fw in frameworks:
            existing = (
                await session.execute(
                    select(FrameworkAssignment).where(
                        FrameworkAssignment.customerId == str(body.customerId),
                        FrameworkAssignment.frameworkId == fw.id,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                existing.status = "assigned"
                existing.updatedAt = _now()
            else:
                session.add(
                    FrameworkAssignment(
                        tenantId=body.tenantId,
                        customerId=str(body.customerId),
                        frameworkId=fw.id,
                        frameworkCode=fw.frameworkCode,
                        frameworkName=fw.frameworkName,
                        frameworkVersion=fw.frameworkVersion,
                        frameworkCategoryId=fw.frameworkCategoryId,
                        uploadedBy=fw.uploadedBy,
                        currentFileVersion=fw.currentFileVersion or "1.0.0",
                        fileVersions=list(fw.fileVersions or []),
                        status="assigned",
                        assignment=AssignmentInfo(
                            assignedBy=user.id, assignedAt=_now()
                        ).model_dump(mode="json"),
                        revocation={},
                        finalization={"isFinalized": False},
                    )
                )

    return success(
        {
            "customerId": str(body.customerId),
            "tenantId": str(body.tenantId),
            "frameworkIds": body.frameworkIds,
            "assignedBy": str(user.id) if user and getattr(user, "id", None) else None,
        },
        "Framework(s) successfully assigned to customer.",
    )


# ─── Upload / update / delete ─────────────────────────────────────────────────


@router.post("/upload")
async def upload_framework(
    metadata: str = Form(...),
    file: UploadFile | None = File(default=None),
    user: User = Depends(current_user),
):
    try:
        meta = framework_helper.parse_upload_metadata(metadata)
    except Exception as exc:
        return error(f"Invalid metadata JSON format: {exc}", 400)

    framework_name = meta.get("frameworkName")
    framework_code = meta.get("frameworkCode")
    framework_version = meta.get("frameworkVersion")
    framework_category_id = meta.get("frameworkCategoryId")

    content, err_msg = await _validate_upload(file)
    if err_msg:
        return error(err_msg, 400)

    if not framework_category_id:
        return error("Invalid framework category ID format", 400)

    path_info = file_storage.generate_framework_file_path(
        file.filename, str(user.id), framework_version or "1.0.0"
    )
    if not file_storage.save_file(content, path_info.absolute_path):
        return error("Failed to save file", 500)

    file_hash = file_storage.calculate_bytes_hash(content)
    file_id = new_id()

    file_version = FileVersionEntry(
        fileVersion="1.0.0",
        fileId=file_id,
        fileUrl=str(path_info.absolute_path),
        fileHash=file_hash,
        originalFileName=file.filename,
        fileSize=len(content),
        fileType=_ext(file.filename),
        uploadedAt=_now(),
        aiExtraction=AiExtraction(status="pending"),
    )

    framework = Framework(
        frameworkName=framework_name or "Untitled Framework",
        frameworkVersion=framework_version or "1.0.0",
        frameworkCategoryId=str(framework_category_id),
        frameworkCode=framework_code,
        uploadedBy=user.id,
        currentFileVersion="1.0.0",
        fileVersions=[file_version.model_dump(mode="json")],
        approval=Approval().model_dump(mode="json"),
    )

    try:
        async with session_scope() as session:
            session.add(framework)
            await session.flush()
            await session.refresh(framework)
            response_data = {
                "id": str(framework.id),
                "frameworkName": framework.frameworkName,
                "frameworkVersion": framework.frameworkVersion,
                "frameworkCode": framework.frameworkCode,
                "currentFileVersion": framework.currentFileVersion,
                "fileInfo": {
                    "originalFileName": file.filename,
                    "fileSize": data_formatter.format_file_size(len(content)),
                    "fileType": _ext(file.filename),
                    "fileUrl": file_storage.get_file_url(path_info.filename),
                },
                "uploadedBy": data_formatter.format_uploaded_by(user, user.id),
                "approval": framework.approval,
                "createdAt": framework.createdAt,
            }
    except IntegrityError:
        return error(
            f"A framework with this version ({framework.frameworkVersion}) already exists.",
            409,
        )

    return success(response_data, "Framework created successfully")


@router.put("/{id}")
async def update_framework(
    id: str,
    metadata: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    user: User = Depends(current_user),
):
    content, err_msg = await _validate_upload(file)
    if err_msg:
        return error(err_msg, 400)

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error("Framework not found", 404)

        if str(framework.uploadedBy) != str(user.id):
            return error("You don't have permission to update this framework", 403)

        versions = framework_helper.parse_file_versions(framework)
        file_hash = file_storage.calculate_bytes_hash(content)
        duplicate = next((v for v in versions if v.fileHash == file_hash), None)
        if duplicate:
            return error(
                f"This file has already been uploaded as version {duplicate.fileVersion}. "
                "Please upload a different file.",
                409,
            )

        path_info = file_storage.generate_framework_file_path(
            file.filename, str(user.id), framework.frameworkVersion
        )
        if not file_storage.save_file(content, path_info.absolute_path):
            return error("Failed to save file", 500)

        new_version = framework_helper.get_next_version(framework.currentFileVersion)
        versions.append(
            FileVersionEntry(
                fileVersion=new_version,
                fileId=new_id(),
                fileUrl=str(path_info.absolute_path),
                fileHash=file_hash,
                originalFileName=file.filename,
                fileSize=len(content),
                fileType=_ext(file.filename),
                uploadedAt=_now(),
                aiExtraction=AiExtraction(status="pending"),
            )
        )
        framework.fileVersions = framework_helper.dump_file_versions(versions)
        framework.currentFileVersion = new_version

        if metadata:
            try:
                meta = framework_helper.parse_upload_metadata(metadata)
            except Exception as exc:
                return error(f"Invalid metadata JSON format: {exc}", 400)
            framework_helper.update_framework_metadata(meta, framework)

        framework.updatedAt = _now()
        await session.flush()

        response_data = {
            "id": str(framework.id),
            "frameworkName": framework.frameworkName,
            "frameworkVersion": framework.frameworkVersion,
            "frameworkCode": framework.frameworkCode,
            "currentFileVersion": framework.currentFileVersion,
            "updatedAt": framework.updatedAt,
        }

    return success(response_data, "Framework updated successfully")


@router.delete("/{id}")
async def delete_framework(id: str, user: User = Depends(current_user)):
    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error("Framework not found", 404)

        if str(framework.uploadedBy) != str(user.id):
            return error("You don't have permission to delete this framework", 403)

        if framework_helper.approval_status(framework) == "approved":
            return error("Cannot delete approved framework", 403)

        versions = framework_helper.parse_file_versions(framework)
        for version in versions:
            if version.fileUrl:
                file_storage.delete_file(version.fileUrl)

        framework_id = framework.id
        await session.delete(framework)

    try:
        response = await ai_service.delete_framework(str(id))
        print("✅ Framework deleted successfully from AI service", response)
    except AiServiceError as exc:
        print("❌ Failed to delete framework from AI service", exc)

    return success({"id": str(framework_id)}, "Framework deleted successfully")


# ─── Files ────────────────────────────────────────────────────────────────────


@router.get("/{frameworkId}/files")
async def get_framework_files(frameworkId: str, user: User = Depends(current_user)):
    async with session_scope() as session:
        framework = await session.get(Framework, str(frameworkId))
        if not framework:
            return error("Framework not found", 404)

        if str(framework.uploadedBy) != str(user.id):
            return error("You don't have permission to access these files", 403)

        versions = framework_helper.parse_file_versions(framework)
        files = [
            {
                "id": idx + 1,
                "fileId": str(v.fileId) if v and getattr(v, "fileId", None) else None,
                "fileName": v.originalFileName,
                "fileSize": v.fileSize,
                "fileType": v.fileType,
                "fileVersion": v.fileVersion,
                "uploadedAt": v.uploadedAt,
                "fileUrl": v.fileUrl,
                "isCurrentVersion": v.fileVersion == framework.currentFileVersion,
            }
            for idx, v in enumerate(versions)
        ]

        response_data = {
            "frameworkId": str(framework.id),
            "frameworkName": framework.frameworkName,
            "files": files,
        }

    return success(response_data, "Framework files retrieved successfully")


@router.get("/{frameworkId}/files/{fileId}")
async def get_framework_file_by_id(
    frameworkId: str, fileId: str, user: User = Depends(current_user)
):
    async with session_scope() as session:
        framework = await session.get(Framework, str(frameworkId))
        if not framework:
            return error("Framework not found", 404)

        if str(framework.uploadedBy) != str(user.id):
            return error("You don't have permission to access this file", 403)

        versions = framework_helper.parse_file_versions(framework)
        file_version = next((v for v in versions if str(v.fileId) == fileId), None)
        if not file_version:
            return error("File not found", 404)

        response_data = {
            "frameworkId": str(framework.id),
            "frameworkName": framework.frameworkName,
            "file": {
                "fileId": str(file_version.fileId) if file_version and getattr(file_version, "fileId", None) else None,
                "fileName": file_version.originalFileName,
                "fileSize": file_version.fileSize,
                "fileType": file_version.fileType,
                "fileVersion": file_version.fileVersion,
                "uploadedAt": file_version.uploadedAt,
                "fileUrl": file_version.fileUrl,
                "isCurrentVersion": file_version.fileVersion == framework.currentFileVersion,
            },
        }

    return success(response_data, "Framework file retrieved successfully")


@router.get("/{frameworkId}/files/{fileId}/download")
async def download_framework_file(frameworkId: str, fileId: str):
    async with session_scope() as session:
        framework = await session.get(Framework, str(frameworkId))
        if not framework:
            return error("Framework not found", 404)

        versions = framework_helper.parse_file_versions(framework)
        file_version = next((v for v in versions if str(v.fileId) == fileId), None)
        if not file_version:
            return error("File not found", 404)

        file_bytes = file_storage.read_file(file_version.fileUrl)
        if file_bytes is None:
            return error("File not found on disk", 404)

        content_type = CONTENT_TYPES.get(file_version.fileType, "application/octet-stream")
        original_name = file_version.originalFileName

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{original_name}"',
            "Content-Length": str(len(file_bytes)),
        },
    )


@router.get("/{frameworkId}/files/{fileId}/preview")
async def preview_framework_file(
    frameworkId: str, fileId: str, user: User = Depends(current_user)
):
    async with session_scope() as session:
        framework = await session.get(Framework, str(frameworkId))
        if not framework:
            return error("Framework not found", 404)

        versions = framework_helper.parse_file_versions(framework)
        file_version = next((v for v in versions if str(v.fileId) == fileId), None)
        if not file_version:
            return error("File version not found", 404)

        actual_path = file_storage.resolve_actual_file_path(file_version.fileUrl, str(user.id))
        if not actual_path or not file_storage.file_exists(actual_path):
            return error("File on disk not found", 404)

        file_bytes = file_storage.read_file(actual_path)
        ext = (file_version.fileType or "").lower()
        mime = PREVIEW_MIME_TYPES.get(ext, "application/octet-stream")
        original_name = file_version.originalFileName

    return Response(
        content=file_bytes,
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{original_name}"'},
    )


@router.delete("/{frameworkId}/files/{fileId}")
async def delete_framework_file(
    frameworkId: str, fileId: str, user: User = Depends(current_user)
):
    async with session_scope() as session:
        framework = await session.get(Framework, str(frameworkId))
        if not framework:
            return error("Framework not found", 404)

        if str(framework.uploadedBy) != str(user.id):
            return error("You don't have permission to delete this file", 403)

        if framework_helper.approval_status(framework) == "approved":
            return error("Cannot delete files from approved framework", 403)

        versions = framework_helper.parse_file_versions(framework)
        idx = next((i for i, v in enumerate(versions) if str(v.fileId) == fileId), None)
        if idx is None:
            return error("File not found", 404)

        file_version = versions[idx]
        file_storage.delete_file(file_version.fileUrl)

        versions.pop(idx)
        framework.fileVersions = framework_helper.dump_file_versions(versions)

        if file_version.fileVersion == framework.currentFileVersion:
            framework.currentFileVersion = versions[-1].fileVersion if versions else None

        framework.updatedAt = _now()
        await session.flush()

        response_data = {
            "frameworkId": str(framework.id) if framework and getattr(framework, "id", None) else None,
            "frameworkName": framework.frameworkName,
            "frameworkCategoryId": str(framework.frameworkCategoryId) if framework and getattr(framework, "frameworkCategoryId", None) else None,
            "frameworkCode": framework.frameworkCode,
            "uploadedBy": str(framework.uploadedBy) if framework and getattr(framework, "uploadedBy", None) else None,
            "currentFileVersion": framework.currentFileVersion,
            "fileVersions": framework.fileVersions,
            "approval": framework.approval,
            "updatedAt": framework.updatedAt,
        }

    try:
        response = await ai_service.delete_framework_file(str(frameworkId), fileId)
        print("✅ Framework file deleted successfully from AI service", response)
    except AiServiceError as exc:
        print("❌ Failed to delete framework file from AI service", exc)

    return success(response_data, "Framework retrieved successfully")


@router.post("/{frameworkId}/files/{fileId}/ai-upload")
async def upload_framework_to_ai(frameworkId: str, fileId: str):
    async with session_scope() as session:
        framework = await session.get(Framework, str(frameworkId))
        if not framework:
            return error("Framework not found", 404)

        versions = framework_helper.parse_file_versions(framework)
        file_version = next((v for v in versions if str(v.fileId) == fileId), None)
        if not file_version:
            return error("File version not found", 404)

        actual_path = file_storage.resolve_actual_file_path(
            file_version.fileUrl, str(framework.uploadedBy)
        )
        if not actual_path or not file_storage.file_exists(actual_path):
            return error("File on disk not found", 404)

        # Keep ORM object for AI payload mapping (dict-aware in ai_service)
        framework_for_ai = framework

    asyncio.create_task(_safe_start_extraction(str(frameworkId), fileId))

    response = None
    try:
        response = await ai_service.upload_framework(framework_for_ai, actual_path)
        print("✅ Framework upload successfully from AI service", response)
    except AiServiceError as exc:
        print("❌ Failed to upload framework from AI service", exc)

    return success(response, "Successfully uploaded framework to AI")


async def _safe_start_extraction(framework_id: str, file_id: str) -> None:
    try:
        await ai_websocket_service.start_extraction(framework_id, file_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[AI WS] startExtraction error: {exc}")


# ─── Control CRUD ─────────────────────────────────────────────────────────────


@router.post("/{id}/file-versions/{fileVersion}/controls")
async def add_framework_control(
    id: str,
    fileVersion: str,
    body: AddControlBody,
    user: User = Depends(current_user),
):
    if (not body.sectionId and not body.newSection) or not body.name:
        return error("sectionId or newSection, and name are required", 400)

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error("Framework not found", 404)

        if str(framework.uploadedBy) != str(user.id):
            return error("You don't have permission to modify this framework", 403)

        if framework_helper.approval_status(framework) == "approved":
            return error("Cannot edit controls in approved frameworks", 403)

        versions = framework_helper.parse_file_versions(framework)
        file_version_doc = next(
            (fv for fv in versions if fv.fileVersion == fileVersion), None
        )
        if not file_version_doc:
            return error(f"Version {fileVersion} not found in this framework", 404)

        if not file_version_doc.aiExtraction:
            return error("AI Extraction data not found for this version", 400)

        if not file_version_doc.aiExtraction.controls:
            file_version_doc.aiExtraction.controls = Controls()

        controls_data = file_version_doc.aiExtraction.controls.controls_data

        result = framework_helper.resolve_section_and_ids(
            body.newSection, body.sectionId, controls_data, fileVersion
        )
        if "error" in result:
            return error(result["error"]["message"], result["error"]["statusCode"])

        section = result.get("section")
        section_id_to_use = result["sectionIdToUse"]
        section_prefix = result["sectionPrefix"]
        next_control_num = result["nextControlNum"]

        new_control_id = f"{section_prefix}.{next_control_num}"

        all_controls = [c for s in controls_data for c in (s.controls or [])]
        if any(c.id == new_control_id for c in all_controls):
            return error(f"A control with ID {new_control_id} already exists in this version", 409)

        built_points = framework_helper.build_deployment_points(
            [dp.model_dump() for dp in body.deployment_points]
        )

        new_control = ControlItem(
            id=new_control_id,
            name=body.name.strip(),
            description=(body.description or "").strip(),
            deployment_points=built_points,
        )

        if body.newSection:
            new_section_obj = Section(
                id=section_id_to_use, name=body.newSection.strip(), controls=[new_control]
            )
            controls_data.append(new_section_obj)
            file_version_doc.aiExtraction.controls.total_sections = len(controls_data)
        else:
            section.controls.append(new_control)

        file_version_doc.aiExtraction.controls.total_controls = sum(
            len(s.controls or []) for s in controls_data
        )

        framework.fileVersions = framework_helper.dump_file_versions(versions)
        framework.updatedAt = _now()
        await session.flush()

        control_payload = new_control.model_dump(mode="json")

    try:
        response = await ai_service.add_framework_control(
            str(id),
            fileVersion,
            {
                "sectionId": str(body.sectionId) if body and getattr(body, "sectionId", None) else None,
                "newSection": body.newSection,
                "name": body.name,
                "description": body.description,
                "deployment_points": [dp.model_dump() for dp in body.deployment_points],
            },
        )
        print("✅ Framework control add successfully from AI service", response)
    except AiServiceError as exc:
        print("❌ Failed to add framework control from AI service", exc)

    return success(
        {
            "control": control_payload,
            "sectionId": section_id_to_use,
            "fileVersion": fileVersion,
        },
        f"Control added successfully to section {section_id_to_use} in version {fileVersion}",
    )


@router.patch("/{id}/file-versions/{fileVersion}/controls/{controlId}")
async def update_framework_control(
    id: str,
    fileVersion: str,
    controlId: str,
    body: UpdateControlBody,
    user: User = Depends(current_user),
):
    if not body.name and body.description is None and body.deployment_points is None:
        return error(
            "At least one of name, description, or deployment_points must be provided", 400
        )

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error("Framework not found", 404)

        if str(framework.uploadedBy) != str(user.id):
            return error("You don't have permission to modify this framework", 403)

        if framework_helper.approval_status(framework) == "approved":
            return error("Cannot edit controls in approved frameworks", 403)

        versions = framework_helper.parse_file_versions(framework)
        file_version_doc = next(
            (fv for fv in versions if fv.fileVersion == fileVersion), None
        )
        if not file_version_doc:
            return error(f"Version {fileVersion} not found in this framework", 404)

        controls = file_version_doc.aiExtraction.controls if file_version_doc.aiExtraction else None
        if not controls or not controls.controls_data:
            return error(f"Version {fileVersion} does not have any controls", 404)

        target_control = None
        for section in controls.controls_data:
            target_control = next((c for c in (section.controls or []) if c.id == controlId), None)
            if target_control:
                break

        if not target_control:
            return error(f"Control with ID {controlId} not found in version {fileVersion}", 404)

        if body.name:
            target_control.name = body.name.strip()
        if body.description is not None:
            target_control.description = body.description.strip()
        if body.deployment_points is not None:
            target_control.deployment_points = framework_helper.build_deployment_points(
                [dp.model_dump() for dp in body.deployment_points]
            )

        framework.fileVersions = framework_helper.dump_file_versions(versions)
        framework.updatedAt = _now()
        await session.flush()

        control_payload = target_control.model_dump(mode="json")
        control_name = target_control.name
        control_description = target_control.description
        control_dps = [dp.model_dump() for dp in target_control.deployment_points]

    try:
        response = await ai_service.update_framework_control(
            str(id),
            fileVersion,
            controlId,
            {
                "name": control_name,
                "description": control_description,
                "deployment_points": control_dps,
            },
        )
        print("✅ Framework control updated successfully from AI service", response)
    except AiServiceError as exc:
        print("❌ Failed to update framework control from AI service", exc)

    return success(
        {"control": control_payload, "fileVersion": fileVersion},
        f"Control {controlId} updated successfully in version {fileVersion}",
    )


@router.patch("/{id}/file-versions/{fileVersion}/controls/{controlId}/weightage")
async def update_framework_control_weightage(
    id: str,
    fileVersion: str,
    controlId: str,
    body: UpdateControlWeightageBody,
    user: User = Depends(current_user),
):
    if body.weightage is None or body.weightage < 0:
        return error("Valid weightage must be provided", 400)

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error("Framework not found", 404)

        if str(framework.uploadedBy) != str(user.id):
            return error("You don't have permission to modify this framework", 403)

        if framework_helper.approval_status(framework) == "approved":
            return error("Cannot edit controls in approved frameworks", 403)

        versions = framework_helper.parse_file_versions(framework)
        file_version_doc = next(
            (fv for fv in versions if fv.fileVersion == fileVersion), None
        )
        if not file_version_doc:
            return error(f"Version {fileVersion} not found in this framework", 404)

        controls = file_version_doc.aiExtraction.controls if file_version_doc.aiExtraction else None
        if not controls or not controls.controls_data:
            return error(f"Version {fileVersion} does not have any controls", 404)

        target_control = None
        for section in controls.controls_data:
            target_control = next((c for c in (section.controls or []) if c.id == controlId), None)
            if target_control:
                break

        if not target_control:
            return error(f"Control with ID {controlId} not found in version {fileVersion}", 404)

        target_control.weightage = body.weightage

        framework.fileVersions = framework_helper.dump_file_versions(versions)
        framework.updatedAt = _now()
        await session.flush()

        control_payload = target_control.model_dump(mode="json")

    return success(
        {"control": control_payload, "fileVersion": fileVersion},
        "Control weightage updated successfully",
    )


@router.delete("/{id}/file-versions/{fileVersion}/controls/{controlId}")
async def delete_framework_control(
    id: str,
    fileVersion: str,
    controlId: str,
    user: User = Depends(current_user),
):
    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error("Framework not found", 404)

        if str(framework.uploadedBy) != str(user.id):
            return error("You don't have permission to modify this framework", 403)

        if framework_helper.approval_status(framework) == "approved":
            return error("Cannot delete controls from approved frameworks", 403)

        versions = framework_helper.parse_file_versions(framework)
        file_version_doc = next(
            (fv for fv in versions if fv.fileVersion == fileVersion), None
        )
        if not file_version_doc:
            return error(f"Version {fileVersion} not found in this framework", 404)

        controls = file_version_doc.aiExtraction.controls if file_version_doc.aiExtraction else None
        if not controls or not controls.controls_data:
            return error(f"Version {fileVersion} does not have any controls", 404)

        deleted = False
        controls_data = controls.controls_data
        for s_idx in range(len(controls_data) - 1, -1, -1):
            section = controls_data[s_idx]
            c_idx = next(
                (i for i, c in enumerate(section.controls or []) if c.id == controlId), None
            )
            if c_idx is not None:
                section.controls.pop(c_idx)
                deleted = True
                if not section.controls:
                    controls_data.pop(s_idx)
                    controls.total_sections = len(controls_data)
                break

        if not deleted:
            return error(f"Control with ID {controlId} not found in version {fileVersion}", 404)

        controls.total_controls = sum(len(s.controls or []) for s in controls_data)

        framework.fileVersions = framework_helper.dump_file_versions(versions)
        framework.updatedAt = _now()
        await session.flush()

    try:
        response = await ai_service.delete_framework_control(str(id), fileVersion, controlId)
        print("✅ Framework control deleted successfully from AI service", response)
    except AiServiceError as exc:
        print("❌ Failed to delete framework control from AI service", exc)

    return success(
        {"controlId": controlId, "fileVersion": fileVersion},
        f"Control {controlId} deleted successfully from version {fileVersion}",
    )
