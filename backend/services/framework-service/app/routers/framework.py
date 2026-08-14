"""Port of framework.controller.js + framework.routes.js."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Annotated

from app.helpers import framework_helper
from app.helpers.report_helper import generate_framework_report_pdf
from app.schemas.framework import (
    AddControlBody,
    AssignFrameworkToCustomerBody,
    RejectFrameworkBody,
    UpdateControlBody,
    UpdateControlWeightageBody,
)
from fastapi import APIRouter, Depends, File, Form
from fastapi import Path as ApiPath
from fastapi import Query, Response, UploadFile
from sqlalchemy import String, cast, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from vora_shared import data_format, file_storage
from vora_shared import messages as msg
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import Customer, DocumentExtraction, FrameworkAssignment, FrameworkCategory, User
from vora_shared.models.document_extraction import ExtractionControlItem as ControlItem
from vora_shared.models.document_extraction import ExtractionSection as Section
from vora_shared.models.framework import (
    Approval,
    FileVersionEntry,
    Framework,
)
from vora_shared.models.framework_assignment import AssignmentInfo
from vora_shared.query_builder import build_pagination_meta, clamp_limit, clamp_page
from vora_shared.responses import error, paginated, success

router = APIRouter(tags=["framework"])
logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _validate_upload(file: UploadFile | None) -> tuple[bytes | None, str | None]:
    """Returns (file_bytes, error_message). error_message is None on success."""
    if file is None or not file.filename:
        return None, "No file uploaded"
    content = await file.read()
    validation = file_storage.validate_uploaded_file(file.filename, len(content))
    if not validation.get("isValid"):
        return None, validation.get("message")
    return content, None


def _apply_ai_status_filter(stmt, ai_status: str | None):
    if not ai_status:
        return stmt
    return stmt.where(text("""EXISTS (
                SELECT 1
                FROM jsonb_array_elements(frameworks."fileVersions") AS elem
                LEFT JOIN document_extractions de ON de.id = elem->>'aiExtraction'
                WHERE elem->>'fileVersion' = frameworks."currentFileVersion"
                  AND (
                     de."aiExtraction"->>'status' = :ai_status
                     OR (jsonb_typeof(elem->'aiExtraction') = 'object' AND elem->'aiExtraction'->>'status' = :ai_status)
                  )
            )""").bindparams(ai_status=ai_status))


def _apply_category_access_filter(stmt, access_status: str | None, expert_requests):
    if not access_status:
        return stmt

    if access_status == "not_requested":
        requested_ids = [req.frameworkCategoryId for req in expert_requests]
        return stmt.where(FrameworkCategory.id.notin_(requested_ids)) if requested_ids else stmt

    matching_ids = [req.frameworkCategoryId for req in expert_requests if req.status == access_status]
    return stmt.where(FrameworkCategory.id.in_(matching_ids)) if matching_ids else stmt.where(text("false"))


def _apply_category_sort(stmt, sort_by: str | None, sort_order: str | None):
    sort_field = sort_by if sort_by in {"createdAt", "frameworkCategoryName", "code"} else "createdAt"
    col = getattr(FrameworkCategory, sort_field)
    return stmt.order_by(col.asc() if (sort_order or "desc").lower() == "asc" else col.desc())


def _apply_framework_approval_filter(stmt, approval_status: str | None):
    if approval_status in {"pending", "approved", "rejected"}:
        return stmt.where(Framework.approval["status"].astext == approval_status)
    return stmt


async def _apply_framework_search_filter(stmt, search: str | None, session):
    if not search:
        return stmt

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
                select(User.id).where(or_(User.name.ilike(pattern), User.email.ilike(pattern)))
            )
        )
        .scalars()
        .all()
    )
    if matching_user_ids:
        search_conditions.append(Framework.uploadedBy.in_(matching_user_ids))
    return stmt.where(or_(*search_conditions))


def _apply_framework_sort(stmt, sort_by: str | None, sort_order: str | None):
    allowed_sort_fields = {
        "createdAt",
        "updatedAt",
        "frameworkName",
        "frameworkCode",
    }
    sort_field = sort_by if sort_by in allowed_sort_fields else "createdAt"
    col = getattr(Framework, sort_field)
    return stmt.order_by(col.asc() if (sort_order or "desc").lower() == "asc" else col.desc())


async def _load_users_by_id(session, user_ids):
    if not user_ids:
        return {}

    users = (await session.execute(select(User).where(User.id.in_(list(user_ids))))).scalars().all()
    return {u.id: u for u in users}


def _find_control_in_sections(controls_data, control_id: str):
    for section in controls_data:
        target_control = next((c for c in (section.controls or []) if c.id == control_id), None)
        if target_control:
            return target_control
    return None


async def _load_editable_framework_version(
    session,
    framework_id: str,
    file_version: str,
    user: User,
    approved_message: str,
):
    framework = await session.get(Framework, str(framework_id))
    if not framework:
        return None, None, None, error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

    if str(framework.uploadedBy) != str(user.id):
        return (
            None,
            None,
            None,
            error(msg.FRAMEWORK_SERVICE_MESSAGES["YOU_DON_T_HAVE_PERMISSION_TO_MODIFY_THIS"], 403),
        )

    if framework_helper.approval_status(framework) == "approved":
        return None, None, None, error(approved_message, 403)

    versions = framework_helper.parse_file_versions(framework)
    file_version_doc = next((fv for fv in versions if fv.fileVersion == file_version), None)
    if not file_version_doc:
        return None, None, None, error(f"Version {file_version} not found in this framework", 404)

    return framework, versions, file_version_doc, None


def _delete_control_from_sections(controls_data, control_id: str) -> bool:
    for s_idx in range(len(controls_data) - 1, -1, -1):
        section = controls_data[s_idx]
        c_idx = next((i for i, c in enumerate(section.controls or []) if c.id == control_id), None)
        if c_idx is None:
            continue

        section.controls.pop(c_idx)
        if not section.controls:
            controls_data.pop(s_idx)
        return True

    return False


# ─── Categories ───────────────────────────────────────────────────────────────


@router.get("/categories/available")
async def get_available_categories(
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
    page: Annotated[int, Query()] = 1,
    limit: Annotated[int, Query()] = 10,
    search: Annotated[str | None, Query()] = None,
    is_active: Annotated[str | None, Query(alias="isActive")] = None,
    access_status: Annotated[str | None, Query(alias="accessStatus")] = None,
    sort_by: Annotated[str | None, Query(alias="sortBy")] = None,
    sort_order: Annotated[str | None, Query(alias="sortOrder")] = None,
):
    logger.info(
        f"[GET-CATEGORIES] Fetching available categories | user_id={ctx.user.id} | page={page} | limit={limit} | search={search} | isActive={is_active} | accessStatus={access_status}"
    )
    user = ctx.user
    from vora_shared.models import FrameworkAccess

    page_num = clamp_page(page)
    limit_num = clamp_limit(limit)

    async with session_scope() as session:
        expert_requests = (
            (await session.execute(select(FrameworkAccess).where(FrameworkAccess.expertId == user.id)))
            .scalars()
            .all()
        )
        requested_map = {
            str(req.frameworkCategoryId): {"hasRequested": True, "status": req.status}
            for req in expert_requests
        }

        stmt = select(FrameworkCategory)
        if is_active is not None:
            stmt = stmt.where(FrameworkCategory.isActive.is_(is_active.lower() == "true"))

        stmt = _apply_category_access_filter(stmt, access_status, expert_requests)

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    FrameworkCategory.frameworkCategoryName.ilike(pattern),
                    FrameworkCategory.code.ilike(pattern),
                    FrameworkCategory.description.ilike(pattern),
                )
            )

        stmt = _apply_category_sort(stmt, sort_by, sort_order)

        total = (
            await session.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
        ).scalar_one()
        categories = list(
            (await session.execute(stmt.offset((page_num - 1) * limit_num).limit(limit_num))).scalars().all()
        )

        creator_ids = {c.createdBy for c in categories if c.createdBy}
        creators_by_id = {}
        if creator_ids:
            creators = (
                (await session.execute(select(User).where(User.id.in_(list(creator_ids))))).scalars().all()
            )
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
                    "createdBy": data_format.format_user_ref(
                        creators_by_id.get(category.createdBy), category.createdBy
                    ),
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
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
    page: Annotated[int, Query()] = 1,
    limit: Annotated[int, Query()] = 10,
    search: Annotated[str | None, Query()] = None,
    ai_status: Annotated[str | None, Query(alias="aiStatus")] = None,
    approval_status: Annotated[str | None, Query(alias="approvalStatus")] = None,
    sort_by: Annotated[str | None, Query(alias="sortBy")] = None,
    sort_order: Annotated[str | None, Query(alias="sortOrder")] = None,
):
    logger.info(
        f"[LIST-FRAMEWORKS] Fetching all frameworks | user_id={ctx.user.id} | page={page} | limit={limit}"
    )
    page_num = clamp_page(page)
    limit_num = clamp_limit(limit)

    async with session_scope() as session:
        stmt = select(Framework)
        stmt = _apply_framework_approval_filter(stmt, approval_status)
        stmt = _apply_ai_status_filter(stmt, ai_status)
        stmt = await _apply_framework_search_filter(stmt, search, session)
        stmt = _apply_framework_sort(stmt, sort_by, sort_order)

        total = (
            await session.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
        ).scalar_one()
        docs = list(
            (await session.execute(stmt.offset((page_num - 1) * limit_num).limit(limit_num))).scalars().all()
        )

        uploaders_by_id = await _load_users_by_id(session, {d.uploadedBy for d in docs})

        doc_ids = []
        for d in docs:
            curr = framework_helper.get_current_file_version_data(d)
            if curr and curr.aiExtraction and isinstance(curr.aiExtraction, str):
                doc_ids.append(curr.aiExtraction)
        doc_extractions = {}
        if doc_ids:
            exts = (
                (await session.execute(select(DocumentExtraction).where(DocumentExtraction.id.in_(doc_ids))))
                .scalars()
                .all()
            )
            doc_extractions = {e.id: e for e in exts}

        data = [
            framework_helper.transform_framework_doc(
                doc, uploaders_by_id.get(doc.uploadedBy), doc_extractions
            )
            for doc in docs
        ]

    message = framework_helper.get_framework_message(len(data), search, ai_status, approval_status)
    return paginated(data, build_pagination_meta(page_num, limit_num, total), message)


# ─── Single framework ─────────────────────────────────────────────────────────


@router.get("/{id}")
async def get_framework_by_id(id: str, ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[GET-FRAMEWORK] Fetching framework | id={id} | user_id={ctx.user.id}")

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            logger.warning(f"[GET-FRAMEWORK] Framework not found: {id}")
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        uploaded_by_user = (
            await session.get(User, str(framework.uploadedBy)) if framework.uploadedBy else None
        )
        approved_by_id = framework_helper.approval_by(framework)
        approved_by_user = await session.get(User, str(approved_by_id)) if approved_by_id else None

        versions = framework_helper.parse_file_versions(framework)

        doc_ids = [v.aiExtraction for v in versions if v.aiExtraction and isinstance(v.aiExtraction, str)]
        doc_extractions = {}
        if doc_ids:
            exts = (
                (await session.execute(select(DocumentExtraction).where(DocumentExtraction.id.in_(doc_ids))))
                .scalars()
                .all()
            )
            doc_extractions = {e.id: e for e in exts}

        formatted_versions = [
            {
                "fileVersion": v.fileVersion,
                "fileId": str(v.fileId) if v and getattr(v, "fileId", None) else None,
                "fileUrl": v.fileUrl,
                "fileHash": v.fileHash,
                "originalFileName": v.originalFileName,
                "fileSize": data_format.format_file_size(v.fileSize),
                "fileType": v.fileType,
                "uploadedAt": v.uploadedAt,
                "aiExtraction": (
                    doc_extractions[v.aiExtraction].aiExtraction
                    if isinstance(v.aiExtraction, str) and v.aiExtraction in doc_extractions
                    else (v.aiExtraction if isinstance(v.aiExtraction, dict) else None)
                ),
            }
            for v in reversed(versions)
        ]

        response_data = {
            "id": str(framework.id),
            "frameworkName": framework.frameworkName,
            "frameworkVersion": framework.frameworkVersion,
            "frameworkCode": framework.frameworkCode,
            "frameworkCategoryId": (
                str(framework.frameworkCategoryId) if framework.frameworkCategoryId else None
            ),
            "currentFileVersion": framework.currentFileVersion,
            "fileVersions": formatted_versions,
            "uploadedBy": data_format.format_uploaded_by(uploaded_by_user, framework.uploadedBy),
            "approval": {
                "status": framework_helper.approval_status(framework),
                "by": (
                    data_format.format_user_ref(approved_by_user, approved_by_id) if approved_by_id else None
                ),
                "date": framework_helper.approval_date(framework),
                "remark": framework_helper.approval_remark(framework),
            },
            "createdAt": framework.createdAt,
            "updatedAt": framework.updatedAt,
        }

    return success(response_data, msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_RETRIEVED_SUCCESSFULLY"])


@router.get("/{id}/download-report")
async def download_framework_report(id: str, ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[DOWNLOAD-FRAMEWORK-REPORT] Download request | id={id} | user_id={ctx.user.id}")

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        approved_by_id = framework_helper.approval_by(framework)
        approved_by_user = await session.get(User, str(approved_by_id)) if approved_by_id else None

        versions = framework_helper.parse_file_versions(framework)
        doc_ids = [v.aiExtraction for v in versions if v.aiExtraction and isinstance(v.aiExtraction, str)]
        doc_extractions = {}
        if doc_ids:
            exts = (
                (await session.execute(select(DocumentExtraction).where(DocumentExtraction.id.in_(doc_ids))))
                .scalars()
                .all()
            )
            doc_extractions = {e.id: e for e in exts}

        pdf_bytes = generate_framework_report_pdf(framework, approved_by_user, doc_extractions)

        safe_name = re.sub(r"[^a-zA-Z0-9]", "_", framework.frameworkName)
        filename = f"{safe_name}_report.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{id}/approve")
async def approve_framework(id: str, ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[APPROVE-FRAMEWORK] Approval request | id={id} | user_id={ctx.user.id}")
    user = ctx.user

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            logger.warning(f"[APPROVE-FRAMEWORK] Framework not found: {id}")
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        current, doc_extraction, ai, val_error_msg, val_status = (
            await framework_helper.validate_framework_approval_readiness(session, framework, user)
        )
        if val_error_msg:
            return error(val_error_msg, val_status)

        invalid_control = framework_helper.find_invalid_control_weightage(
            current, doc_extraction, legacy_ai=ai
        )
        if invalid_control:
            label = invalid_control.id or invalid_control.name
            return error(
                f"Control '{label}' must have a valid weightage between 1 and 10 before approval",
                400,
            )

        framework_helper.apply_approved_versions(framework, current)

        # Change all pending deployment points to approved
        await framework_helper.approve_all_deployment_points(session, framework)
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

    return success(
        {"framework": {"id": framework_id, msg.FRAMEWORK_SERVICE_MESSAGES["APPROVAL"]: approval_payload}},
        "Framework approved successfully",
    )


@router.post("/{id}/reject")
async def reject_framework(
    id: str,
    body: RejectFrameworkBody,
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(
        f"[REJECT-FRAMEWORK] Rejection request | id={id} | user_id={ctx.user.id} | reason={body.reason[:50] if body.reason else ''}"
    )
    user = ctx.user

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        if framework_helper.approval_status(framework) == "rejected":
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_IS_ALREADY_REJECTED"], 400)

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

    return success(response_payload, msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_REJECTED_SUCCESSFULLY"])


# ─── Assignment ───────────────────────────────────────────────────────────────


@router.post("/assign-framework-to-customer")
async def assign_framework_to_customer(
    body: AssignFrameworkToCustomerBody,
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(
        f"[ASSIGN-FRAMEWORK] Assignment request | customerId={body.customerId} | tenantId={body.tenantId} | frameworkIds={body.frameworkIds} | user_id={ctx.user.id}"
    )
    user = ctx.user

    if not body.customerId or not body.tenantId or not body.frameworkIds:
        return error(
            msg.FRAMEWORK_SERVICE_MESSAGES["CUSTOMERID_TENANTID_AND_FRAMEWORKIDS_NON"],
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
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["CUSTOMER_ORGANIZATION_NOT_FOUND"], 404)
        if not customer.isActive:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["CUSTOMER_ORGANIZATION_IS_NOT_ACTIVE"], 404)

        framework_ids = [str(fid) for fid in body.frameworkIds]
        frameworks = list(
            (await session.execute(select(Framework).where(Framework.id.in_(framework_ids)))).scalars().all()
        )
        if not frameworks:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORKS_NOT_FOUND"], 404)
        if len(frameworks) != len(framework_ids):
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["ONE_OR_MORE_PROVIDED_FRAMEWORK_IDS_ARE_I"], 400)

        unapproved = [f for f in frameworks if framework_helper.approval_status(f) != "approved"]
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
                # Update assignment time without clearing revocation
                existing.assignment = AssignmentInfo(assignedBy=user.id, assignedAt=_now()).model_dump(
                    mode="json"
                )
                flag_modified(existing, "assignment")
                # Hydrate missing controls if they are still strings
                new_file_versions = await framework_helper.hydrate_assignment_file_versions(
                    session, existing.fileVersions
                )
                existing.fileVersions = new_file_versions
                flag_modified(existing, "fileVersions")
            else:
                new_file_versions = await framework_helper.hydrate_assignment_file_versions(
                    session, fw.fileVersions
                )

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
                        fileVersions=new_file_versions,
                        status="assigned",
                        assignment=AssignmentInfo(assignedBy=user.id, assignedAt=_now()).model_dump(
                            mode="json"
                        ),
                        revocation={},
                        finalization={"isFinalized": False},
                    )
                )

    return success(
        {
            "customerId": str(body.customerId),
            msg.FRAMEWORK_SERVICE_MESSAGES["TENANTID"]: str(body.tenantId),
            "frameworkIds": body.frameworkIds,
            "assignedBy": str(user.id) if user and getattr(user, "id", None) else None,
        },
        "Framework(s) successfully assigned to customer.",
    )


# ─── Upload / update / delete ─────────────────────────────────────────────────


@router.post("/upload")
async def upload_framework(
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
    metadata: Annotated[str, Form()],
    file: Annotated[UploadFile | None, File()] = None,
):
    logger.info(
        f"[UPLOAD-FRAMEWORK] Upload request | user_id={ctx.user.id} | file={file.filename if file else 'none'} | filename={file.filename if file else 'N/A'}"
    )
    user = ctx.user

    try:
        meta = framework_helper.parse_upload_metadata(metadata)
    except Exception as exc:
        logger.error(f"[UPLOAD-FRAMEWORK] Invalid metadata | error={exc}")
        return error(f"Invalid metadata JSON format: {exc}", 400)

    framework_name = meta.get("frameworkName")
    framework_code = meta.get("frameworkCode")
    framework_version = meta.get("frameworkVersion")
    framework_category_id = meta.get("frameworkCategoryId")

    content, err_msg = await _validate_upload(file)
    if err_msg:
        return error(err_msg, 400)

    if not framework_category_id:
        return error(msg.FRAMEWORK_SERVICE_MESSAGES["INVALID_FRAMEWORK_CATEGORY_ID_FORMAT"], 400)

    path_info = file_storage.generate_framework_file_path(
        file.filename, str(user.id), framework_version or "1.0.0"
    )
    if not file_storage.save_file(content, path_info.absolute_path):
        return error(msg.FRAMEWORK_SERVICE_MESSAGES["FAILED_TO_SAVE_FILE"], 500)

    file_hash = file_storage.calculate_bytes_hash(content)
    file_id = new_id()

    file_version = FileVersionEntry(
        fileVersion="1.0.0",
        fileId=file_id,
        fileUrl=str(path_info.absolute_path),
        fileHash=file_hash,
        originalFileName=file.filename,
        fileSize=len(content),
        fileType=file_storage.normalize_file_type(getattr(file, "content_type", None), file.filename),
        uploadedAt=_now(),
        aiExtraction=None,
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
            # Create DocumentExtraction if not exists
            doc_extraction = (
                await session.execute(
                    select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash)
                )
            ).scalar_one_or_none()
            if not doc_extraction:
                doc_extraction = DocumentExtraction(
                    id=new_id(),
                    fileHash=file_hash,
                    aiExtraction={
                        "status": "pending",
                        "message": None,
                        "timestamp": None,
                        "statusHistory": None,
                        "controls": None,
                    },
                )
                session.add(doc_extraction)
                await session.flush()

            file_version.aiExtraction = doc_extraction.id
            framework.fileVersions = [file_version.model_dump(mode="json")]

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
                    "fileSize": data_format.format_file_size(len(content)),
                    "fileType": file_storage.normalize_file_type(
                        getattr(file, "content_type", None), file.filename
                    ),
                    "fileUrl": file_storage.get_file_url(path_info.filename),
                },
                "uploadedBy": data_format.format_uploaded_by(user, user.id),
                "approval": framework.approval,
                "createdAt": framework.createdAt,
            }
    except IntegrityError:
        return error(
            f"A framework with this version ({framework.frameworkVersion}) already exists.",
            409,
        )

    return success(response_data, msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_CREATED_SUCCESSFULLY"])


@router.put("/{id}")
async def update_framework(
    id: str,
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
    metadata: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
):
    logger.info(f"[UPDATE-FRAMEWORK] Update request | id={id} | user_id={ctx.user.id}")
    user = ctx.user

    content, err_msg = await _validate_upload(file)
    if err_msg:
        return error(err_msg, 400)

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        if str(framework.uploadedBy) != str(user.id):
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["YOU_DON_T_HAVE_PERMISSION_TO_UPDATE_THIS"], 403)

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
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FAILED_TO_SAVE_FILE"], 500)

        new_version = framework_helper.get_next_version(framework.currentFileVersion)
        versions.append(
            FileVersionEntry(
                fileVersion=new_version,
                fileId=new_id(),
                fileUrl=str(path_info.absolute_path),
                fileHash=file_hash,
                originalFileName=file.filename,
                fileSize=len(content),
                fileType=file_storage.normalize_file_type(getattr(file, "content_type", None), file.filename),
                uploadedAt=_now(),
                aiExtraction=None,
            )
        )

        # Create DocumentExtraction if not exists
        doc_extraction = (
            await session.execute(select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash))
        ).scalar_one_or_none()
        if not doc_extraction:
            doc_extraction = DocumentExtraction(
                id=new_id(),
                fileHash=file_hash,
                aiExtraction={
                    "status": "pending",
                    "message": None,
                    "timestamp": None,
                    "statusHistory": None,
                    "controls": None,
                },
            )
            session.add(doc_extraction)
            await session.flush()

        versions[-1].aiExtraction = doc_extraction.id
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

    return success(response_data, msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_UPDATED_SUCCESSFULLY"])


@router.delete("/{id}")
async def delete_framework(id: str, ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[DELETE-FRAMEWORK] Delete request | id={id} | user_id={ctx.user.id}")
    user = ctx.user

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        if str(framework.uploadedBy) != str(user.id):
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["YOU_DON_T_HAVE_PERMISSION_TO_DELETE_THIS"], 403)

        if framework_helper.approval_status(framework) == "approved":
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["CANNOT_DELETE_APPROVED_FRAMEWORK"], 403)

        versions = framework_helper.parse_file_versions(framework)
        for version in versions:
            if version.fileUrl:
                file_storage.delete_file(version.fileUrl)

        framework_id = framework.id
        await session.delete(framework)

    return success(
        {"id": str(framework_id)}, msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_DELETED_SUCCESSFULLY"]
    )


# ─── Files ────────────────────────────────────────────────────────────────────


@router.get("/{frameworkId}/files")
async def get_framework_files(
    framework_id: Annotated[str, ApiPath(alias="frameworkId")],
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(
        f"[GET-FRAMEWORK-FILES] Fetching framework files | framework_id={framework_id} | user_id={ctx.user.id}"
    )
    user = ctx.user

    async with session_scope() as session:
        framework = await session.get(Framework, str(framework_id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        if str(framework.uploadedBy) != str(user.id):
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["YOU_DON_T_HAVE_PERMISSION_TO_ACCESS_THES"], 403)

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

    return success(response_data, msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_FILES_RETRIEVED_SUCCESSFULLY"])


@router.get("/{frameworkId}/files/{fileId}")
async def get_framework_file_by_id(
    framework_id: Annotated[str, ApiPath(alias="frameworkId")],
    file_id: Annotated[str, ApiPath(alias="fileId")],
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(
        f"[GET-FRAMEWORK-FILE] Fetching framework file | framework_id={framework_id} | file_id={file_id} | user_id={ctx.user.id}"
    )
    user = ctx.user

    async with session_scope() as session:
        framework = await session.get(Framework, str(framework_id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        if str(framework.uploadedBy) != str(user.id):
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["YOU_DON_T_HAVE_PERMISSION_TO_ACCESS_THIS"], 403)

        versions = framework_helper.parse_file_versions(framework)
        file_version = next((v for v in versions if str(v.fileId) == file_id), None)
        if not file_version:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FILE_NOT_FOUND"], 404)

        response_data = {
            "frameworkId": str(framework.id),
            "frameworkName": framework.frameworkName,
            "file": {
                "fileId": (
                    str(file_version.fileId)
                    if file_version and getattr(file_version, "fileId", None)
                    else None
                ),
                "fileName": file_version.originalFileName,
                "fileSize": file_version.fileSize,
                "fileType": file_version.fileType,
                "fileVersion": file_version.fileVersion,
                "uploadedAt": file_version.uploadedAt,
                "fileUrl": file_version.fileUrl,
                "isCurrentVersion": file_version.fileVersion == framework.currentFileVersion,
            },
        }

    return success(response_data, msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_FILE_RETRIEVED_SUCCESSFULLY"])


@router.get("/{frameworkId}/files/{fileId}/download")
async def download_framework_file(
    framework_id: Annotated[str, ApiPath(alias="frameworkId")],
    file_id: Annotated[str, ApiPath(alias="fileId")],
):
    logger.info(
        f"[DOWNLOAD-FRAMEWORK-FILE] Download request | framework_id={framework_id} | file_id={file_id}"
    )

    async with session_scope() as session:
        framework = await session.get(Framework, str(framework_id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        versions = framework_helper.parse_file_versions(framework)
        file_version = next((v for v in versions if str(v.fileId) == file_id), None)
        if not file_version:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FILE_NOT_FOUND"], 404)

        file_bytes = file_storage.read_file(file_version.fileUrl)
        if file_bytes is None:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FILE_NOT_FOUND_ON_DISK"], 404)

        content_type = file_storage.CONTENT_TYPES.get(file_version.fileType, "application/octet-stream")
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
    framework_id: Annotated[str, ApiPath(alias="frameworkId")],
    file_id: Annotated[str, ApiPath(alias="fileId")],
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(
        f"[PREVIEW-FRAMEWORK-FILE] Preview request | framework_id={framework_id} | file_id={file_id} | user_id={ctx.user.id}"
    )
    user = ctx.user

    async with session_scope() as session:
        framework = await session.get(Framework, str(framework_id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        versions = framework_helper.parse_file_versions(framework)
        file_version = next((v for v in versions if str(v.fileId) == file_id), None)
        if not file_version:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FILE_VERSION_NOT_FOUND"], 404)

        actual_path = file_storage.resolve_actual_file_path(file_version.fileUrl, str(user.id))
        if not actual_path or not file_storage.file_exists(actual_path):
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FILE_ON_DISK_NOT_FOUND"], 404)

        file_bytes = file_storage.read_file(actual_path)
        ext = (file_version.fileType or "").lower()
        mime = file_storage.PREVIEW_MIME_TYPES.get(ext, "application/octet-stream")
        original_name = file_version.originalFileName

    return Response(
        content=file_bytes,
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{original_name}"'},
    )


@router.delete("/{frameworkId}/files/{fileId}")
async def delete_framework_file(
    framework_id: Annotated[str, ApiPath(alias="frameworkId")],
    file_id: Annotated[str, ApiPath(alias="fileId")],
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(
        f"[DELETE-FRAMEWORK-FILE] Delete request | framework_id={framework_id} | file_id={file_id} | user_id={ctx.user.id}"
    )
    user = ctx.user

    async with session_scope() as session:
        framework = await session.get(Framework, str(framework_id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        if str(framework.uploadedBy) != str(user.id):
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["YOU_DON_T_HAVE_PERMISSION_TO_DELETE_THIS"], 403)

        if framework_helper.approval_status(framework) == "approved":
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["CANNOT_DELETE_FILES_FROM_APPROVED_FRAMEW"], 403)

        versions = framework_helper.parse_file_versions(framework)
        idx = next((i for i, v in enumerate(versions) if str(v.fileId) == file_id), None)
        if idx is None:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FILE_NOT_FOUND"], 404)

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
            "frameworkCategoryId": (
                str(framework.frameworkCategoryId)
                if framework and getattr(framework, "frameworkCategoryId", None)
                else None
            ),
            "frameworkCode": framework.frameworkCode,
            "uploadedBy": (
                str(framework.uploadedBy) if framework and getattr(framework, "uploadedBy", None) else None
            ),
            "currentFileVersion": framework.currentFileVersion,
            "fileVersions": framework.fileVersions,
            "approval": framework.approval,
            "updatedAt": framework.updatedAt,
        }

    return success(response_data, msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_RETRIEVED_SUCCESSFULLY"])


# ─── Control CRUD ─────────────────────────────────────────────────────────────


@router.post("/{id}/file-versions/{fileVersion}/controls")
async def add_framework_control(
    id: str,
    file_version: Annotated[str, ApiPath(alias="fileVersion")],
    body: AddControlBody,
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(
        f"[ADD-CONTROL] Adding control | id={id} | file_version={file_version} | user_id={ctx.user.id}"
    )
    user = ctx.user

    if (not body.sectionId and not body.newSection) or not body.name:
        logger.warning("[ADD-CONTROL] Invalid request | missing sectionId/newSection or name")
        return error(msg.FRAMEWORK_SERVICE_MESSAGES["SECTIONID_OR_NEWSECTION_AND_NAME_ARE_REQ"], 400)

    async with session_scope() as session:
        framework, versions, file_version_doc, load_error = await _load_editable_framework_version(
            session,
            id,
            file_version,
            user,
            msg.FRAMEWORK_SERVICE_MESSAGES["CANNOT_EDIT_CONTROLS_IN_APPROVED_FRAMEWO"],
        )
        if load_error:
            return load_error

        controls, doc_ext, ai_data, load_err_msg, load_status = await framework_helper.load_ai_controls(
            session, file_version_doc
        )
        if load_err_msg:
            return error(load_err_msg, load_status)

        controls_data = controls.controls_data

        result = framework_helper.resolve_section_and_ids(
            body.newSection, body.sectionId, controls_data, file_version
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
            controls.total_sections = len(controls_data)
        else:
            section.controls.append(new_control)

        controls.total_controls = sum(len(s.controls or []) for s in controls_data)

        framework_helper.save_ai_controls(session, file_version_doc, controls, doc_ext, ai_data)

        framework.fileVersions = framework_helper.dump_file_versions(versions)
        framework.updatedAt = _now()
        await session.flush()

        control_payload = new_control.model_dump(mode="json")

    return success(
        {
            "control": control_payload,
            msg.FRAMEWORK_SERVICE_MESSAGES["SECTIONID"]: section_id_to_use,
            "fileVersion": file_version,
        },
        f"Control added successfully to section {section_id_to_use} in version {file_version}",
    )


@router.patch("/{id}/file-versions/{fileVersion}/controls/{controlId}")
async def update_framework_control(
    id: str,
    file_version: Annotated[str, ApiPath(alias="fileVersion")],
    control_id: Annotated[str, ApiPath(alias="controlId")],
    body: UpdateControlBody,
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(
        f"[UPDATE-CONTROL] Updating control | id={id} | file_version={file_version} | control_id={control_id} | user_id={ctx.user.id}"
    )
    user = ctx.user

    if not body.name and body.description is None and body.deployment_points is None:
        return error(msg.FRAMEWORK_SERVICE_MESSAGES["AT_LEAST_ONE_OF_NAME_DESCRIPTION_OR_DEPL"], 400)

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        if str(framework.uploadedBy) != str(user.id):
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["YOU_DON_T_HAVE_PERMISSION_TO_MODIFY_THIS"], 403)

        if framework_helper.approval_status(framework) == "approved":
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["CANNOT_EDIT_CONTROLS_IN_APPROVED_FRAMEWO"], 403)

        versions = framework_helper.parse_file_versions(framework)
        file_version_doc = next((fv for fv in versions if fv.fileVersion == file_version), None)
        if not file_version_doc:
            return error(f"Version {file_version} not found in this framework", 404)

        controls, doc_ext, ai_data, load_err_msg, load_status = await framework_helper.load_ai_controls(
            session, file_version_doc
        )
        if load_err_msg:
            return error(load_err_msg, load_status)
        if not controls or not controls.controls_data:
            return error(f"Version {file_version} does not have any controls", 404)

        target_control = _find_control_in_sections(controls.controls_data, control_id)
        if not target_control:
            return error(f"Control with ID {control_id} not found in version {file_version}", 404)

        if body.name:
            target_control.name = body.name.strip()
        if body.description is not None:
            target_control.description = body.description.strip()
        if body.deployment_points is not None:
            target_control.deployment_points = framework_helper.build_deployment_points(
                [dp.model_dump() for dp in body.deployment_points]
            )

        framework_helper.save_ai_controls(session, file_version_doc, controls, doc_ext, ai_data)

        framework.fileVersions = framework_helper.dump_file_versions(versions)
        framework.updatedAt = _now()
        await session.flush()

        control_payload = target_control.model_dump(mode="json")

    return success(
        {"control": control_payload, msg.FRAMEWORK_SERVICE_MESSAGES["FILEVERSION"]: file_version},
        f"Control {control_id} updated successfully in version {file_version}",
    )


@router.patch("/{id}/file-versions/{fileVersion}/controls/{controlId}/weightage")
async def update_framework_control_weightage(
    id: str,
    file_version: Annotated[str, ApiPath(alias="fileVersion")],
    control_id: Annotated[str, ApiPath(alias="controlId")],
    body: UpdateControlWeightageBody,
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(
        f"[UPDATE-CONTROL-WEIGHTAGE] Updating control weightage | id={id} | file_version={file_version} | control_id={control_id} | weightage={body.weightage} | user_id={ctx.user.id}"
    )
    user = ctx.user

    if body.weightage is None or body.weightage < 0:
        return error(msg.FRAMEWORK_SERVICE_MESSAGES["VALID_WEIGHTAGE_MUST_BE_PROVIDED"], 400)

    async with session_scope() as session:
        framework = await session.get(Framework, str(id))
        if not framework:
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["FRAMEWORK_NOT_FOUND"], 404)

        if str(framework.uploadedBy) != str(user.id):
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["YOU_DON_T_HAVE_PERMISSION_TO_MODIFY_THIS"], 403)

        if framework_helper.approval_status(framework) == "approved":
            return error(msg.FRAMEWORK_SERVICE_MESSAGES["CANNOT_EDIT_CONTROLS_IN_APPROVED_FRAMEWO"], 403)

        versions = framework_helper.parse_file_versions(framework)
        file_version_doc = next((fv for fv in versions if fv.fileVersion == file_version), None)
        if not file_version_doc:
            return error(f"Version {file_version} not found in this framework", 404)

        controls, doc_ext, ai_data, load_err_msg, load_status = await framework_helper.load_ai_controls(
            session, file_version_doc
        )
        if load_err_msg:
            return error(load_err_msg, load_status)
        if not controls or not controls.controls_data:
            return error(f"Version {file_version} does not have any controls", 404)

        target_control = _find_control_in_sections(controls.controls_data, control_id)
        if not target_control:
            return error(f"Control with ID {control_id} not found in version {file_version}", 404)

        target_control.weightage = body.weightage

        framework_helper.save_ai_controls(session, file_version_doc, controls, doc_ext, ai_data)

        framework.fileVersions = framework_helper.dump_file_versions(versions)
        framework.updatedAt = _now()
        await session.flush()

        control_payload = target_control.model_dump(mode="json")

    return success(
        {"control": control_payload, msg.FRAMEWORK_SERVICE_MESSAGES["FILEVERSION"]: file_version},
        "Control weightage updated successfully",
    )


@router.delete("/{id}/file-versions/{fileVersion}/controls/{controlId}")
async def delete_framework_control(
    id: str,
    file_version: Annotated[str, ApiPath(alias="fileVersion")],
    control_id: Annotated[str, ApiPath(alias="controlId")],
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(
        f"[DELETE-CONTROL] Deleting control | id={id} | file_version={file_version} | control_id={control_id} | user_id={ctx.user.id}"
    )
    user = ctx.user

    async with session_scope() as session:
        framework, versions, file_version_doc, load_error = await _load_editable_framework_version(
            session,
            id,
            file_version,
            user,
            msg.FRAMEWORK_SERVICE_MESSAGES["CANNOT_DELETE_CONTROLS_FROM_APPROVED_FRA"],
        )
        if load_error:
            return load_error

        controls, doc_ext, ai_data, load_err_msg, load_status = await framework_helper.load_ai_controls(
            session, file_version_doc
        )
        if load_err_msg:
            return error(load_err_msg, load_status)
        if not controls or not controls.controls_data:
            return error(f"Version {file_version} does not have any controls", 404)

        controls_data = controls.controls_data
        if not _delete_control_from_sections(controls_data, control_id):
            return error(f"Control with ID {control_id} not found in version {file_version}", 404)

        controls.total_sections = len(controls_data)
        controls.total_controls = sum(len(s.controls or []) for s in controls_data)

        framework_helper.save_ai_controls(session, file_version_doc, controls, doc_ext, ai_data)

        framework.fileVersions = framework_helper.dump_file_versions(versions)
        framework.updatedAt = _now()
        await session.flush()

    return success(
        {"controlId": control_id, msg.FRAMEWORK_SERVICE_MESSAGES["FILEVERSION"]: file_version},
        f"Control {control_id} deleted successfully from version {file_version}",
    )
