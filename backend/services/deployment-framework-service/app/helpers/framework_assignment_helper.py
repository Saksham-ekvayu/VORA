"""Port of deployment-framework-service-main/src/helpers/framework-assignment.helper.js."""

import re
from datetime import datetime, timezone
from typing import Any

from vora_shared.models.framework_assignment import (
    AssignmentControl,
    AssignmentCustomization,
    AssignmentDeploymentPoint,
    AssignmentFileVersion,
    AssignmentFinalization,
    AssignmentInfo,
    AssignmentRevocation,
    AssignmentSection,
)
from vora_shared.models.user import User


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


def coerce_file_versions(file_versions: list[Any] | None) -> list[AssignmentFileVersion]:
    result: list[AssignmentFileVersion] = []
    for fv in file_versions or []:
        if isinstance(fv, AssignmentFileVersion):
            result.append(fv)
            continue
        data = dict(fv) if isinstance(fv, dict) else fv
        if isinstance(data, dict) and isinstance(data.get("aiExtraction"), list):
            data["aiExtraction"] = [
                AssignmentSection.model_validate(s) if isinstance(s, dict) else s
                for s in data["aiExtraction"]
            ]
        result.append(AssignmentFileVersion.model_validate(data))
    return result


def dump_file_versions(file_versions: list[Any] | None) -> list[dict[str, Any]]:
    return [dump_model(fv) for fv in (file_versions or [])]


def as_assignment_info(raw: Any) -> AssignmentInfo:
    if isinstance(raw, AssignmentInfo):
        return raw
    return AssignmentInfo.model_validate(raw or {})


def as_revocation(raw: Any) -> AssignmentRevocation:
    if isinstance(raw, AssignmentRevocation):
        return raw
    return AssignmentRevocation.model_validate(raw or {})


def as_finalization(raw: Any) -> AssignmentFinalization:
    if isinstance(raw, AssignmentFinalization):
        return raw
    return AssignmentFinalization.model_validate(raw or {})


def format_user_ref(user_ref: User | Any | None) -> dict[str, Any] | None:
    if not user_ref:
        return None
    if isinstance(user_ref, User):
        return {
            "id": str(user_ref.id) if user_ref and getattr(user_ref, "id", None) else None,
            "name": user_ref.name,
            "email": user_ref.email,
            "role": user_ref.role,
            "avatar": user_ref.avatar,
        }
    return {"id": user_ref, "name": None, "email": None, "role": None, "avatar": None}


def format_customer(customer: Any | None) -> dict[str, Any] | None:
    if not customer:
        return None
    is_populated = hasattr(customer, "name")
    if is_populated:
        return {
            "id": str(customer.id) if customer and getattr(customer, "id", None) else None,
            "tenantId": getattr(customer, "tenantId", None),
            "name": getattr(customer, "name", None),
            "email": getattr(customer, "email", None),
            "phone": getattr(customer, "phone", None),
            "isActive": getattr(customer, "isActive", None),
            "avatar": getattr(customer, "avatar", None),
        }
    return {
        "id": customer,
        "tenantId": None,
        "name": None,
        "email": None,
        "phone": None,
        "isActive": None,
        "avatar": None,
    }


def format_assignment(assignment: Any | None, assigned_by_user: User | None = None) -> dict[str, Any] | None:
    info = as_assignment_info(assignment) if assignment is not None else None
    if not info or not info.assignedAt:
        return None
    return {"assignedBy": format_user_ref(assigned_by_user or info.assignedBy), "assignedAt": info.assignedAt}


def format_revocation(revocation: Any | None, revoked_by_user: User | None = None) -> dict[str, Any] | None:
    info = as_revocation(revocation) if revocation is not None else None
    if not info or not info.revokedAt:
        return None
    return {"revokedBy": format_user_ref(revoked_by_user or info.revokedBy), "revokedAt": info.revokedAt}


def format_deployment_point(dp: AssignmentDeploymentPoint) -> dict[str, Any]:
    return {
        "id": str(dp.id) if dp and getattr(dp, "id", None) else None,
        "name": dp.name,
        "status": dp.status,
        "path": dp.path or "",
        "weightage": {
            "framework_weightage": dp.weightage.framework_weightage if dp.weightage else 0,
            "customer_weightage": dp.weightage.customer_weightage if dp.weightage else 0,
        },
        "score": dp.score or 0,
        "remark": dp.remark or "",
    }


def format_control(control: AssignmentControl) -> dict[str, Any]:
    customization_data = None
    if control.customization:
        customization_data = {
            "source": control.customization.source or "system",
            "addedBy": control.customization.addedBy,
            "addedAt": control.customization.addedAt,
            "updatedAt": control.customization.updatedAt,
            "is_applicable": (
                control.customization.is_applicable
                if control.customization.is_applicable is not None
                else True
            ),
            "weightage": {
                "framework_weightage": control.customization.weightage.framework_weightage or 0,
                "customer_weightage": control.customization.weightage.customer_weightage or 0,
            },
        }

    return {
        "id": str(control.id) if control and getattr(control, "id", None) else None,
        "name": control.name,
        "description": control.description or "",
        "deployment_points": [format_deployment_point(dp) for dp in (control.deployment_points or [])],
        "customization": customization_data,
    }


def format_section(section: AssignmentSection) -> dict[str, Any]:
    return {
        "id": str(section.id) if section and getattr(section, "id", None) else None,
        "name": section.name,
        "controls": [format_control(c) for c in (section.controls or [])],
    }


def format_file_version(file: Any) -> dict[str, Any]:
    fv = file if isinstance(file, AssignmentFileVersion) else AssignmentFileVersion.model_validate(file)
    return {
        "fileVersion": fv.fileVersion,
        "fileId": str(fv.fileId) if fv and getattr(fv, "fileId", None) else None,
        "fileUrl": fv.fileUrl,
        "fileHash": fv.fileHash,
        "originalFileName": fv.originalFileName,
        "fileSize": fv.fileSize,
        "fileType": fv.fileType,
        "uploadedAt": fv.uploadedAt,
        "aiExtraction": (
            [format_section(s) for s in fv.aiExtraction] if isinstance(fv.aiExtraction, list) else None
        ),
    }


def format_assignment_response(
    doc: Any, customer: Any | None, finalized_by_user: User | None, assigned_by_user: User | None = None, revoked_by_user: User | None = None
) -> dict[str, Any]:
    fin = as_finalization(doc.finalization)
    return {
        "id": str(doc.id) if doc and getattr(doc, "id", None) else None,
        "tenantId": str(doc.tenantId) if doc and getattr(doc, "tenantId", None) else None,
        "frameworkId": str(doc.frameworkId) if doc and getattr(doc, "frameworkId", None) else None,
        "frameworkCode": doc.frameworkCode,
        "frameworkName": doc.frameworkName,
        "frameworkVersion": doc.frameworkVersion,
        "frameworkCategoryId": (
            str(doc.frameworkCategoryId) if doc and getattr(doc, "frameworkCategoryId", None) else None
        ),
        "customer": format_customer(customer),
        "status": doc.status,
        "assignment": format_assignment(doc.assignment, assigned_by_user),
        "revocation": format_revocation(doc.revocation, revoked_by_user),
        "finalization": {
            "isFinalized": fin.isFinalized if fin else False,
            "finalizedBy": format_user_ref(finalized_by_user),
            "finalizedAt": fin.finalizedAt if fin else None,
        },
        "assignedAt": doc.createdAt,
    }


def format_assignment_detail_response(
    doc: Any, customer: Any | None, uploaded_by_user: User | None, finalized_by_user: User | None, assigned_by_user: User | None = None, revoked_by_user: User | None = None
) -> dict[str, Any]:
    fin = as_finalization(doc.finalization)
    file_versions = coerce_file_versions(doc.fileVersions)
    return {
        "id": str(doc.id) if doc and getattr(doc, "id", None) else None,
        "tenantId": str(doc.tenantId) if doc and getattr(doc, "tenantId", None) else None,
        "frameworkId": str(doc.frameworkId) if doc and getattr(doc, "frameworkId", None) else None,
        "frameworkCode": doc.frameworkCode,
        "frameworkName": doc.frameworkName,
        "frameworkVersion": doc.frameworkVersion,
        "currentFileVersion": doc.currentFileVersion,
        "customer": format_customer(customer),
        "uploadedBy": format_user_ref(uploaded_by_user),
        "status": doc.status,
        "fileVersions": [format_file_version(f) for f in reversed(file_versions)],
        "assignment": format_assignment(doc.assignment, assigned_by_user),
        "revocation": format_revocation(doc.revocation, revoked_by_user),
        "finalization": {
            "isFinalized": fin.isFinalized if fin else False,
            "finalizedBy": format_user_ref(finalized_by_user),
            "finalizedAt": fin.finalizedAt if fin else None,
        },
        "createdAt": doc.createdAt,
        "updatedAt": doc.updatedAt,
    }


def get_next_section_id(existing_sections: list[AssignmentSection]) -> str:
    max_num = 0
    for s in existing_sections or []:
        if not s.id:
            continue
        match = re.match(r"^SEC-(\d+)$", s.id)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    return f"SEC-{max_num + 1:02d}"


def extract_section_prefix(section_name: str, fallback_id: str) -> str:
    cleaned = re.sub(r"^Section\s*[-:]*\s*", "", section_name, flags=re.IGNORECASE)
    match = re.match(r"^([A-Z]\.\d+(?:\.\d+)*|\d+(?:\.\d+)*|[A-Z0-9]\b)", cleaned, flags=re.IGNORECASE)
    return match.group(1) if match else fallback_id


def build_deployment_points(
    deployment_points: list[dict[str, Any]] | None,
) -> list[AssignmentDeploymentPoint]:
    result = []
    for idx, dp in enumerate([dp for dp in (deployment_points or []) if (dp.get("name") or "").strip()]):
        result.append(
            AssignmentDeploymentPoint(
                id=f"DP-{idx + 1:03d}",
                name=dp["name"].strip(),
                status="pending",
                path="",
                score=0,
                remark="",
            )
        )
    return result


def create_new_control(
    control_id: str,
    name: str,
    description: str,
    deployment_points: list[AssignmentDeploymentPoint],
    user_id: Any,
) -> AssignmentControl:
    return AssignmentControl(
        id=control_id,
        name=name.strip(),
        description=description.strip(),
        deployment_points=deployment_points,
        customization=AssignmentCustomization(
            source="custom",
            addedBy=str(user_id) if user_id is not None else None,
            addedAt=_utcnow(),
            is_applicable=True,
        ),
    )


def handle_new_section(new_section: str, controls_data: list[AssignmentSection]) -> dict[str, Any]:
    trimmed_new_section = new_section.strip()
    if not trimmed_new_section:
        return {"error": "New section name is required"}

    existing_section = next(
        (s for s in controls_data if s.name and s.name.strip().lower() == trimmed_new_section.lower()),
        None,
    )
    if existing_section:
        return {"error": f'A section named "{trimmed_new_section}" already exists.', "status": 409}

    new_section_id = get_next_section_id(controls_data)
    if any(s.id == new_section_id for s in controls_data):
        return {"error": f"Section ID {new_section_id} already exists.", "status": 409}

    section_prefix = extract_section_prefix(trimmed_new_section, new_section_id)

    return {
        "sectionIdToUse": new_section_id,
        "sectionPrefix": section_prefix,
        "nextControlNum": 1,
        "sectionName": trimmed_new_section,
    }


def handle_existing_section(
    section_id: str, controls_data: list[AssignmentSection], file_version: str
) -> dict[str, Any]:
    if not controls_data:
        return {"error": f"No controls found for version {file_version}", "status": 404}

    section = next((s for s in controls_data if s.id == section_id), None)
    if not section:
        return {
            "error": f"Section {section_id} not found in version {file_version}",
            "status": 404,
        }

    existing_controls = section.controls or []
    section_prefix = ".".join(existing_controls[0].id.split(".")[:2]) if existing_controls else section.id

    return {
        "section": section,
        "sectionIdToUse": section.id,
        "sectionPrefix": section_prefix,
        "nextControlNum": len(existing_controls) + 1,
    }


def collect_existing_controls(
    ai_extraction: list[AssignmentSection], control_ids: list[str]
) -> list[AssignmentControl]:
    existing_controls = []
    for section in ai_extraction or []:
        for control in section.controls or []:
            if control.id in control_ids:
                existing_controls.append(control)
    return existing_controls


def update_controls_applicability(controls: list[AssignmentControl], is_applicable: bool) -> None:
    for control in controls:
        if not control.customization:
            control.customization = AssignmentCustomization()
        control.customization.is_applicable = is_applicable
        control.customization.updatedAt = _utcnow()


def format_control_ids_for_display(control_ids: list[str]) -> str:
    if len(control_ids) > 3:
        return f"{', '.join(control_ids[:3])}, ..."
    return ", ".join(control_ids)


def find_assigned_control(sections: list[AssignmentSection], control_id: str) -> AssignmentControl | None:
    for section in sections or []:
        found = next((c for c in (section.controls or []) if c.id == control_id), None)
        if found:
            return found
    return None


def delete_control_from_section(
    controls_data: list[AssignmentSection], control_id: str, file_version: str
) -> dict[str, Any]:
    for s_idx, section in enumerate(controls_data):
        idx = next((i for i, c in enumerate(section.controls or []) if c.id == control_id), -1)
        if idx != -1:
            target_control = section.controls[idx]
            if not target_control.customization or target_control.customization.source != "custom":
                return {
                    "error": "Only custom controls can be deleted.",
                    "status": 403,
                }

            section.controls.pop(idx)
            if not section.controls:
                controls_data.pop(s_idx)
            return {"success": True}

    return {
        "error": f"Control {control_id} not found in version {file_version}",
        "status": 404,
    }


def resolve_status_label(assignment_status: str | None, finalization_status: str | None) -> str:
    if assignment_status == "revoked":
        return "Revoked"
    if finalization_status == "finalized":
        return "Finalized"
    if finalization_status == "pending":
        return "Pending"
    return "Assigned"


def build_assignment_base_filters(
    tenant_id: str | None, assignment_status: str | None, finalization_status: str | None
) -> dict[str, Any]:
    """Returns SQLAlchemy filter clauses (not Mongo dict filters)."""
    from sqlalchemy import or_
    from vora_shared.models import FrameworkAssignment

    filters = []

    if tenant_id:
        filters.append(FrameworkAssignment.tenantId == tenant_id)

    if assignment_status:
        if assignment_status not in ("assigned", "revoked"):
            return {"invalidField": "assignmentStatus"}
        filters.append(FrameworkAssignment.status == assignment_status)

    if finalization_status:
        if finalization_status not in ("finalized", "pending"):
            return {"invalidField": "finalizationStatus"}
        if finalization_status == "finalized":
            filters.append(FrameworkAssignment.finalization["isFinalized"].as_boolean().is_(True))
        else:
            filters.append(
                or_(
                    FrameworkAssignment.finalization["isFinalized"].as_boolean().is_(False),
                    FrameworkAssignment.finalization["isFinalized"].as_boolean().is_(None),
                )
            )

    return {"filters": filters}


# Backward-compatible alias used by older call sites
def build_assignment_base_filter(
    tenant_id: str | None, assignment_status: str | None, finalization_status: str | None
) -> dict[str, Any]:
    return build_assignment_base_filters(tenant_id, assignment_status, finalization_status)


def is_valid_customer_weightage(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 1 <= value <= 10


def _get_invalid_weightage_info(section: Any, control: Any) -> dict[str, Any] | None:
    value = (
        control.customization.weightage.customer_weightage
        if control.customization and control.customization.weightage
        else None
    )
    if not is_valid_customer_weightage(value):
        return {
            "section": section.name,
            "control": control.name,
            "controlId": (str(control.id) if control and getattr(control, "id", None) else None),
            "customer_weightage": value,
        }
    return None


def collect_invalid_weightage_controls(file_versions: list[Any]) -> list[dict[str, Any]]:
    invalid = []
    for file_version in coerce_file_versions(file_versions):
        for section in file_version.aiExtraction or []:
            for control in section.controls or []:
                invalid_info = _get_invalid_weightage_info(section, control)
                if invalid_info:
                    invalid.append(invalid_info)
    return invalid
