"""Port of framework-assignment routes embedded in deployment-framework.routes.js
+ src/controllers/framework-assignment.controller.js."""

import logging
from datetime import datetime, timezone
from typing import Any

from app.helpers import framework_assignment_helper as helper
from app.helpers.framework_assignment_helper import (
    as_finalization,
    coerce_file_versions,
    dump_file_versions,
    dump_model,
)
from app.helpers.reports.framework_assignment_report import generate_framework_assignment_report_pdf
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from vora_shared import query_builder
from vora_shared.database import session_scope
from vora_shared.messages import BUSINESS_MESSAGES, format_message
from vora_shared.models import Customer, FrameworkAssignment, User
from vora_shared.responses import error, success
from vora_shared.security import RequestContext, get_context

logger = logging.getLogger("framework_assignment_router")

router = APIRouter(tags=["framework-assignment"])


def not_found(resource: str = "Resource"):
    return error(f"{resource} not found", 404)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _hydrate_user_refs(session, assignments: list[FrameworkAssignment]) -> dict[str, User]:
    ids: set[str] = set()
    for a in assignments:
        assigned_by = helper.as_assignment_info(a.assignment).assignedBy if a.assignment else None
        revoked_by = helper.as_revocation(a.revocation).revokedBy if a.revocation else None
        finalized_by = as_finalization(a.finalization).finalizedBy if a.finalization else None
        if assigned_by:
            ids.add(str(assigned_by))
        if revoked_by:
            ids.add(str(revoked_by))
        if finalized_by:
            ids.add(str(finalized_by))
        if a.uploadedBy:
            ids.add(str(a.uploadedBy))
    if not ids:
        return {}
    users = (await session.execute(select(User).where(User.id.in_(list(ids))))).scalars().all()
    return {str(u.id): u for u in users}


async def _hydrate_customers(session, assignments: list[FrameworkAssignment]) -> dict[str, Customer]:
    ids = {str(a.customerId) for a in assignments if a.customerId}
    if not ids:
        return {}
    customers = (await session.execute(select(Customer).where(Customer.id.in_(list(ids))))).scalars().all()
    return {str(c.id): c for c in customers}


# ─── GET /assignments ────────────────────────────────────────────────────────


@router.get("/assignments")
async def get_all_framework_assignments(
    ctx: RequestContext = Depends(get_context),
    search: str | None = Query(default=None),
    assignmentStatus: str | None = Query(default=None),
    finalizationStatus: str | None = Query(default=None),
    page: int | None = Query(default=None),
    limit: int = Query(default=10),
    sortBy: str | None = Query(default=None),
    sortOrder: str | None = Query(default=None),
):
    tenant_id = ctx.tenant_id

    filter_result = helper.build_assignment_base_filters(tenant_id, assignmentStatus, finalizationStatus)
    if filter_result.get("invalidField") == "assignmentStatus":
        return error(BUSINESS_MESSAGES["INVALID_ASSIGNMENT_STATUS_FILTER"], 400)
    if filter_result.get("invalidField") == "finalizationStatus":
        return error(BUSINESS_MESSAGES["INVALID_FINALIZATION_STATUS_FILTER"], 400)

    allowed_sort_fields = ["createdAt", "updatedAt", "frameworkCode"]

    async with session_scope() as session:
        base_filters = filter_result["filters"]
        preview_stmt = select(FrameworkAssignment)
        for f in base_filters:
            preview_stmt = preview_stmt.where(f)
        preview_docs = list((await session.execute(preview_stmt)).scalars().all())
        users = await _hydrate_user_refs(session, preview_docs)
        customers = await _hydrate_customers(session, preview_docs)

        def transform(doc: FrameworkAssignment) -> dict[str, Any]:
            customer = customers.get(str(doc.customerId)) if doc.customerId else None
            fin = as_finalization(doc.finalization)
            finalized_by = users.get(str(fin.finalizedBy)) if fin and fin.finalizedBy else None
            return helper.format_assignment_response(doc, customer, finalized_by)

        result = await query_builder.paginate_with_search(
            session,
            FrameworkAssignment,
            page=page,
            limit=limit,
            search=search,
            search_fields=["frameworkCode", "frameworkName", "frameworkVersion"],
            base_filters=base_filters,
            sort_by=sortBy,
            sort_order=sortOrder,
            allowed_sort_fields=allowed_sort_fields,
            user_search={"tenant_id": tenant_id, "field_name": "customerId"},
            transform=transform,
        )

        status_label = helper.resolve_status_label(assignmentStatus, finalizationStatus)
        message = format_message(BUSINESS_MESSAGES["ASSIGNED_FRAMEWORKS_RETRIEVED"], status=status_label)

        if not result["data"]:
            message = (
                BUSINESS_MESSAGES["NO_ASSIGNED_FRAMEWORKS_SEARCH"]
                if search
                else format_message(BUSINESS_MESSAGES["NO_ASSIGNED_FRAMEWORKS"], status=status_label.lower())
            )

        from vora_shared.responses import paginated

        return paginated(result["data"], result["pagination"], message)


# ─── GET /assignments/:id ────────────────────────────────────────────────────


@router.get("/assignments/{id}")
async def get_framework_assignment_by_id(id: str, ctx: RequestContext = Depends(get_context)):
    async with session_scope() as session:
        assignment = await session.get(FrameworkAssignment, str(id))
        if not assignment:
            return not_found(BUSINESS_MESSAGES["ASSIGNMENT_NOT_FOUND"])

        users = await _hydrate_user_refs(session, [assignment])
        customers = await _hydrate_customers(session, [assignment])

        customer = customers.get(str(assignment.customerId)) if assignment.customerId else None
        uploaded_by = users.get(str(assignment.uploadedBy)) if assignment.uploadedBy else None
        fin = as_finalization(assignment.finalization)
        finalized_by = users.get(str(fin.finalizedBy)) if fin and fin.finalizedBy else None

        return success(
            helper.format_assignment_detail_response(assignment, customer, uploaded_by, finalized_by),
            format_message(BUSINESS_MESSAGES["ASSIGNED_FRAMEWORKS_RETRIEVED"], status="Assigned"),
        )


# ─── GET /assignments/:id/report ────────────────────────────────────────────


@router.get("/assignments/{id}/report")
async def download_framework_assignment_report(
    id: str, ctx: RequestContext = Depends(get_context), fileVersion: str | None = Query(default=None)
):
    tenant_id = ctx.tenant_id

    async with session_scope() as session:
        assignment = (
            await session.execute(
                select(FrameworkAssignment).where(
                    FrameworkAssignment.id == str(id),
                    FrameworkAssignment.tenantId == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not assignment:
            return not_found(BUSINESS_MESSAGES["ASSIGNMENT_NOT_FOUND"])

        users = await _hydrate_user_refs(session, [assignment])
        customers = await _hydrate_customers(session, [assignment])
        customer = customers.get(str(assignment.customerId)) if assignment.customerId else None

        info = helper.as_assignment_info(assignment.assignment)
        if info.assignedBy:
            # Report helper may expect populated user; keep id string / user object
            assignment.assignment = dump_model(
                info.model_copy(update={"assignedBy": users.get(str(info.assignedBy), info.assignedBy)})
            )

        version = fileVersion or assignment.currentFileVersion
        file_versions = coerce_file_versions(assignment.fileVersions)
        file_version = next((fv for fv in file_versions if fv.fileVersion == version), None)
        if not file_version:
            return error(format_message(BUSINESS_MESSAGES["FILE_VERSION_NOT_FOUND"], version=version), 404)

        safe_name = "_".join(
            filter(
                None,
                __import__("re")
                .sub(r"[^a-zA-Z0-9]", "_", (assignment.frameworkName or assignment.frameworkCode))
                .split("_"),
            )
        )
        filename = f"{safe_name}_assigned_v{version.replace('.', '_')}_report.pdf"

        pdf_bytes = generate_framework_assignment_report_pdf(assignment, file_version, customer)

        from fastapi import Response

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


# ─── PATCH /assignments/:frameworkId/:customerId/revoke ─────────────────────


@router.patch("/assignments/{frameworkId}/{customerId}/revoke")
async def revoke_framework_assignment(
    frameworkId: str, customerId: str, ctx: RequestContext = Depends(get_context)
):
    user = ctx.user

    async with session_scope() as session:
        assignment = (
            await session.execute(
                select(FrameworkAssignment).where(
                    FrameworkAssignment.frameworkId == str(frameworkId),
                    FrameworkAssignment.customerId == str(customerId),
                )
            )
        ).scalar_one_or_none()
        if not assignment:
            return not_found(BUSINESS_MESSAGES["ASSIGNMENT_NOT_FOUND"])

        if assignment.status == "revoked":
            return error(BUSINESS_MESSAGES["ASSIGNMENT_ALREADY_REVOKED"], 409)

        from vora_shared.models.framework_assignment import AssignmentFinalization, AssignmentRevocation

        assignment.status = "revoked"
        assignment.revocation = dump_model(AssignmentRevocation(revokedBy=str(user.id), revokedAt=_utcnow()))
        assignment.finalization = dump_model(
            AssignmentFinalization(isFinalized=False, finalizedBy=None, finalizedAt=None)
        )

        return success(
            {
                "id": str(assignment.id) if assignment and getattr(assignment, "id", None) else None,
                "tenantId": (
                    str(assignment.tenantId) if assignment and getattr(assignment, "tenantId", None) else None
                ),
                "customerId": (
                    str(assignment.customerId)
                    if assignment and getattr(assignment, "customerId", None)
                    else None
                ),
                "frameworkId": (
                    str(assignment.frameworkId)
                    if assignment and getattr(assignment, "frameworkId", None)
                    else None
                ),
                "status": assignment.status,
                "revocation": assignment.revocation,
            },
            BUSINESS_MESSAGES["ASSIGNMENT_REVOKED_SUCCESS"],
        )


# ─── Control CRUD ────────────────────────────────────────────────────────────


def _find_file_version(file_versions: list, file_version: str):
    return next((fv for fv in file_versions if fv.fileVersion == file_version), None)


@router.post("/{id}/file-versions/{fileVersion}/controls")
async def add_assigned_framework_control(
    id: str, fileVersion: str, ctx: RequestContext = Depends(get_context), body: dict[str, Any] = Body(...)
):
    user = ctx.user
    section_id = body.get("sectionId")
    new_section = body.get("newSection")
    name = body.get("name")
    description = body.get("description", "") or ""
    deployment_points = body.get("deployment_points", []) or []

    if (not section_id and not new_section) or not name:
        return error(BUSINESS_MESSAGES["SECTION_ID_NAME_REQUIRED"], 400)

    async with session_scope() as session:
        assignment = await session.get(FrameworkAssignment, str(id))
        if not assignment:
            return not_found(BUSINESS_MESSAGES["ASSIGNMENT_NOT_FOUND"])

        file_versions = coerce_file_versions(assignment.fileVersions)
        file_version_doc = _find_file_version(file_versions, fileVersion)
        if not file_version_doc:
            return error(
                format_message(BUSINESS_MESSAGES["FILE_VERSION_NOT_FOUND"], version=fileVersion), 404
            )

        fin = as_finalization(assignment.finalization)
        if fin.isFinalized:
            return error(BUSINESS_MESSAGES["CANNOT_MODIFY_FINALIZED"], 400)

        if not file_version_doc.aiExtraction:
            return error(BUSINESS_MESSAGES["AI_EXTRACTION_NOT_FOUND"], 400)

        controls_data = list(file_version_doc.aiExtraction)

        section = None
        if new_section:
            section_result = helper.handle_new_section(new_section, controls_data)
        else:
            section_result = helper.handle_existing_section(section_id, controls_data, fileVersion)
            section = section_result.get("section")

        if section_result.get("error"):
            return error(section_result["error"], section_result.get("status", 400))

        section_id_to_use = section_result["sectionIdToUse"]
        section_prefix = section_result["sectionPrefix"]
        next_control_num = section_result["nextControlNum"]
        section_name = section_result.get("sectionName")

        new_control_id = f"{section_prefix}.{next_control_num}"

        all_controls = [c for s in controls_data for c in (s.controls or [])]
        if any(c.id == new_control_id for c in all_controls):
            return error(
                format_message(BUSINESS_MESSAGES["CONTROL_ID_ALREADY_EXISTS"], controlId=new_control_id), 409
            )

        built_points = helper.build_deployment_points(deployment_points)
        new_control = helper.create_new_control(new_control_id, name, description, built_points, user.id)

        if new_section:
            from vora_shared.models.framework_assignment import AssignmentSection

            controls_data.append(
                AssignmentSection(id=section_id_to_use, name=section_name, controls=[new_control])
            )
        else:
            section.controls.append(new_control)

        file_version_doc.aiExtraction = controls_data
        assignment.fileVersions = dump_file_versions(file_versions)
        assignment.updatedAt = _utcnow()

        return success(
            {"control": dump_model(new_control), "sectionId": section_id_to_use, "fileVersion": fileVersion},
            format_message(
                BUSINESS_MESSAGES["CONTROL_ADDED_SUCCESS"], sectionId=section_id_to_use, version=fileVersion
            ),
        )


@router.put("/{id}/file-versions/{fileVersion}/controls/{controlId}")
async def update_assigned_framework_control(
    id: str,
    fileVersion: str,
    controlId: str,
    ctx: RequestContext = Depends(get_context),
    body: dict[str, Any] = Body(...),
):
    name = body.get("name")
    description = body.get("description")
    deployment_points = body.get("deployment_points")

    if not name and description is None and not deployment_points:
        return error(BUSINESS_MESSAGES["CONTROL_UPDATE_REQUIRED"], 400)

    async with session_scope() as session:
        assignment = await session.get(FrameworkAssignment, str(id))
        if not assignment:
            return not_found(BUSINESS_MESSAGES["ASSIGNMENT_NOT_FOUND"])

        file_versions = coerce_file_versions(assignment.fileVersions)
        file_version_doc = _find_file_version(file_versions, fileVersion)
        if not file_version_doc:
            return error(
                format_message(BUSINESS_MESSAGES["FILE_VERSION_NOT_FOUND"], version=fileVersion), 404
            )

        fin = as_finalization(assignment.finalization)
        if fin.isFinalized:
            return error(BUSINESS_MESSAGES["CANNOT_MODIFY_FINALIZED"], 400)

        if not file_version_doc.aiExtraction:
            return error(BUSINESS_MESSAGES["AI_EXTRACTION_NOT_FOUND"], 400)

        target_control = helper.find_assigned_control(file_version_doc.aiExtraction, controlId)
        if not target_control:
            return error(
                format_message(
                    BUSINESS_MESSAGES["CONTROL_NOT_FOUND"], controlId=controlId, version=fileVersion
                ),
                404,
            )

        if not target_control.customization or target_control.customization.source != "custom":
            return error(BUSINESS_MESSAGES["CONTROL_CUSTOM_ONLY"], 403)

        if name:
            target_control.name = name.strip()
        if description is not None:
            target_control.description = description.strip()

        if isinstance(deployment_points, list):
            from vora_shared.models.framework_assignment import AssignmentDeploymentPoint, AssignmentWeightage

            new_points = []
            for idx, dp in enumerate(deployment_points):
                if not (dp.get("name") or "").strip():
                    continue
                weightage = dp.get("weightage") or {}
                new_points.append(
                    AssignmentDeploymentPoint(
                        id=dp.get("id") or f"DP-{idx + 1:03d}",
                        name=dp["name"].strip(),
                        status=dp.get("status", "pending"),
                        path=dp.get("path", ""),
                        weightage=AssignmentWeightage(
                            framework_weightage=weightage.get("framework_weightage", 0),
                            customer_weightage=weightage.get("customer_weightage", 0),
                        ),
                        score=dp.get("score", 0),
                        remark=dp.get("remark", ""),
                    )
                )
            target_control.deployment_points = new_points

        if not target_control.customization:
            from vora_shared.models.framework_assignment import AssignmentCustomization

            target_control.customization = AssignmentCustomization()
        target_control.customization.updatedAt = _utcnow()

        assignment.fileVersions = dump_file_versions(file_versions)
        assignment.updatedAt = _utcnow()

        return success(
            {"control": dump_model(target_control), "fileVersion": fileVersion},
            format_message(
                BUSINESS_MESSAGES["CONTROL_UPDATED_SUCCESS"], controlId=controlId, version=fileVersion
            ),
        )


@router.delete("/{id}/file-versions/{fileVersion}/controls/{controlId}")
async def delete_assigned_framework_control(
    id: str, fileVersion: str, controlId: str, ctx: RequestContext = Depends(get_context)
):
    async with session_scope() as session:
        assignment = await session.get(FrameworkAssignment, str(id))
        if not assignment:
            return not_found(BUSINESS_MESSAGES["ASSIGNMENT_NOT_FOUND"])

        file_versions = coerce_file_versions(assignment.fileVersions)
        file_version_doc = _find_file_version(file_versions, fileVersion)
        if not file_version_doc:
            return error(
                format_message(BUSINESS_MESSAGES["FILE_VERSION_NOT_FOUND"], version=fileVersion), 404
            )

        fin = as_finalization(assignment.finalization)
        if fin.isFinalized:
            return error(BUSINESS_MESSAGES["CANNOT_MODIFY_FINALIZED"], 400)

        if not file_version_doc.aiExtraction:
            return error(BUSINESS_MESSAGES["AI_EXTRACTION_NOT_FOUND"], 400)

        controls_data = list(file_version_doc.aiExtraction)
        delete_result = helper.delete_control_from_section(controls_data, controlId, fileVersion)
        if delete_result.get("error"):
            return error(delete_result["error"], delete_result.get("status", 400))

        file_version_doc.aiExtraction = controls_data
        assignment.fileVersions = dump_file_versions(file_versions)
        assignment.updatedAt = _utcnow()

        return success(
            {"controlId": controlId, "fileVersion": fileVersion},
            format_message(
                BUSINESS_MESSAGES["CONTROL_DELETED_SUCCESS"], controlId=controlId, version=fileVersion
            ),
        )


@router.patch("/{id}/file-versions/{fileVersion}/controls/{controlId}/weightage")
async def update_assigned_framework_control_weightage(
    id: str,
    fileVersion: str,
    controlId: str,
    ctx: RequestContext = Depends(get_context),
    body: dict[str, Any] = Body(...),
):
    weightage = body.get("weightage")
    if not isinstance(weightage, dict):
        return error(BUSINESS_MESSAGES["CONTROL_WEIGHTAGE_INVALID"], 400)

    async with session_scope() as session:
        assignment = await session.get(FrameworkAssignment, str(id))
        if not assignment:
            return not_found(BUSINESS_MESSAGES["ASSIGNMENT_NOT_FOUND"])

        file_versions = coerce_file_versions(assignment.fileVersions)
        file_version_doc = _find_file_version(file_versions, fileVersion)
        if not file_version_doc:
            return error(
                format_message(BUSINESS_MESSAGES["FILE_VERSION_NOT_FOUND"], version=fileVersion), 404
            )

        fin = as_finalization(assignment.finalization)
        if fin.isFinalized:
            return error(BUSINESS_MESSAGES["CANNOT_MODIFY_FINALIZED"], 400)

        if not file_version_doc.aiExtraction:
            return error(BUSINESS_MESSAGES["AI_EXTRACTION_NOT_FOUND"], 400)

        target_control = helper.find_assigned_control(file_version_doc.aiExtraction, controlId)
        if not target_control:
            return error(
                format_message(
                    BUSINESS_MESSAGES["CONTROL_NOT_FOUND"], controlId=controlId, version=fileVersion
                ),
                404,
            )

        if target_control.customization and target_control.customization.is_applicable is False:
            return error(BUSINESS_MESSAGES["CONTROL_NOT_APPLICABLE_WEIGHTAGE_ERROR"], 400)

        from vora_shared.models.framework_assignment import AssignmentCustomization, AssignmentWeightage

        if not target_control.customization:
            target_control.customization = AssignmentCustomization(source="system", is_applicable=True)
        if not target_control.customization.weightage:
            target_control.customization.weightage = AssignmentWeightage()

        if weightage.get("customer_weightage") is not None:
            target_control.customization.weightage.customer_weightage = weightage["customer_weightage"]
        if weightage.get("framework_weightage") is not None:
            target_control.customization.weightage.framework_weightage = weightage["framework_weightage"]

        target_control.customization.updatedAt = _utcnow()

        assignment.fileVersions = dump_file_versions(file_versions)
        assignment.updatedAt = _utcnow()
            
        return success(
            {"control": dump_model(target_control), "fileVersion": fileVersion},
            format_message(
                BUSINESS_MESSAGES["CONTROL_WEIGHTAGE_UPDATED_SUCCESS"],
                controlId=controlId,
                version=fileVersion,
            ),
        )


@router.patch("/{id}/file-versions/{fileVersion}/controls/applicability")
async def update_control_applicability(
    id: str, fileVersion: str, ctx: RequestContext = Depends(get_context), body: dict[str, Any] = Body(...)
):
    control_ids = body.get("controlIds")
    is_applicable = body.get("is_applicable")

    if not isinstance(control_ids, list) or len(control_ids) == 0:
        return error(BUSINESS_MESSAGES["CONTROL_IDS_REQUIRED"], 400)

    if not isinstance(is_applicable, bool):
        return error(BUSINESS_MESSAGES["APPLICABILITY_REQUIRED"], 400)

    async with session_scope() as session:
        assignment = await session.get(FrameworkAssignment, str(id))
        if not assignment:
            return not_found(BUSINESS_MESSAGES["ASSIGNMENT_NOT_FOUND"])

        file_versions = coerce_file_versions(assignment.fileVersions)
        file_version_doc = _find_file_version(file_versions, fileVersion)
        if not file_version_doc:
            return error(
                format_message(BUSINESS_MESSAGES["FILE_VERSION_NOT_FOUND"], version=fileVersion), 404
            )

        fin = as_finalization(assignment.finalization)
        if fin.isFinalized:
            return error(BUSINESS_MESSAGES["CANNOT_MODIFY_FINALIZED"], 400)

        if not file_version_doc.aiExtraction:
            return error(BUSINESS_MESSAGES["AI_EXTRACTION_NOT_FOUND"], 400)

        existing_controls = helper.collect_existing_controls(file_version_doc.aiExtraction, control_ids)
        if not existing_controls:
            return error(BUSINESS_MESSAGES["NO_CONTROLS_FOUND"], 404)

        helper.update_controls_applicability(existing_controls, is_applicable)

        assignment.fileVersions = dump_file_versions(file_versions)
        assignment.updatedAt = _utcnow()
        
        display_control_id = helper.format_control_ids_for_display([c.id for c in existing_controls])
        status_label = "applicable" if is_applicable else "not applicable"

        return success(
            {
                "controlIds": [c.id for c in existing_controls],
                "fileVersion": fileVersion,
                "is_applicable": is_applicable,
            },
            format_message(
                BUSINESS_MESSAGES["CONTROL_APPLICABILITY_UPDATED_SUCCESS"],
                controlId=display_control_id,
                status=status_label,
                version=fileVersion,
            ),
        )


# ─── PATCH /assignments/:id/finalize ─────────────────────────────────────────


@router.patch("/assignments/{id}/finalize")
async def finalize_framework_assignment(id: str, ctx: RequestContext = Depends(get_context)):
    user = ctx.user

    if user.role not in ("auditor", "customer-admin"):
        return error("Access denied. You do not have permission to finalize framework versions.", 403)

    async with session_scope() as session:
        assignment = await session.get(FrameworkAssignment, str(id))
        if not assignment:
            return not_found(BUSINESS_MESSAGES["ASSIGNMENT_NOT_FOUND"])

        fin = as_finalization(assignment.finalization)
        if fin.isFinalized:
            return error("Framework assignment is already finalized.", 400)

        invalid_controls = helper.collect_invalid_weightage_controls(assignment.fileVersions)
        if invalid_controls:
            return error(
                f"Cannot finalize: {len(invalid_controls)} control(s) have an invalid customer_weightage. "
                "Each control must have a customer_weightage between 1 and 10.",
                400,
                {"invalidControls": invalid_controls},
            )

        from vora_shared.models.framework_assignment import AssignmentFinalization

        assignment.finalization = dump_model(
            AssignmentFinalization(isFinalized=True, finalizedBy=str(user.id), finalizedAt=_utcnow())
        )
        users = await _hydrate_user_refs(session, [assignment])
        customers = await _hydrate_customers(session, [assignment])
        customer = customers.get(str(assignment.customerId)) if assignment.customerId else None
        uploaded_by = users.get(str(assignment.uploadedBy)) if assignment.uploadedBy else None
        fin = as_finalization(assignment.finalization)
        finalized_by = users.get(str(fin.finalizedBy)) if fin.finalizedBy else None

        return success(
            helper.format_assignment_detail_response(assignment, customer, uploaded_by, finalized_by),
            "Framework assignment finalized successfully.",
        )
