"""Port of framework.helper.js."""

from __future__ import annotations

import json
import re
from typing import Any

from vora_shared.models.framework import (
    ControlItem,
    DeploymentPoint,
    FileVersionEntry,
    Framework,
    Section,
)
from app.services import data_formatter

BUSINESS_MESSAGES = {
    "EXPERT_FRAMEWORKS_SUCCESS": "Your frameworks retrieved successfully",
    "NO_FRAMEWORKS_SEARCH": "No frameworks match your search criteria. Try adjusting your filters.",
    "NO_FRAMEWORKS_UPLOADED": "You haven't uploaded any frameworks yet. Upload your first framework to get started.",
    "VERSION_NOT_FOUND": "Version {version} not found in this framework",
    "VERSION_NO_CONTROLS": "Version {version} does not have any controls",
    "SECTION_NOT_FOUND": "Section with ID {sectionId} not found in version {version}",
    "CONTROL_ID_ALREADY_EXISTS": "A control with ID {controlId} already exists in this version",
    "CONTROL_NOT_FOUND": "Control with ID {controlId} not found in version {version}",
    "CONTROL_ADDED_SUCCESS": "Control added successfully to section {sectionId} in version {version}",
    "CONTROL_UPDATED_SUCCESS": "Control {controlId} updated successfully in version {version}",
    "CONTROL_DELETED_SUCCESS": "Control {controlId} deleted successfully from version {version}",
}


def format_message(template: str, **replacements: Any) -> str:
    message = template
    for key, value in replacements.items():
        message = message.replace(f"{{{key}}}", str(value))
    return message


def parse_upload_metadata(metadata_input: Any) -> dict:
    if isinstance(metadata_input, str):
        return json.loads(metadata_input)
    if isinstance(metadata_input, dict):
        return metadata_input
    return {}


def get_next_version(current_version: str | None) -> str:
    if not current_version:
        return "1.0.0"
    parts = current_version.split(".")
    try:
        major = int(parts[0])
    except (IndexError, ValueError):
        major = 1
    try:
        minor = int(parts[1])
    except (IndexError, ValueError):
        minor = 0
    return f"{major}.{minor + 1}.0"


def update_framework_metadata(metadata: dict, framework: Framework) -> None:
    """Port of updateFrameworkMetadata in framework.helper.js."""
    if metadata.get("frameworkName"):
        framework.frameworkName = metadata["frameworkName"]
    if metadata.get("frameworkCode"):
        framework.frameworkCode = metadata["frameworkCode"]
    if metadata.get("frameworkVersion"):
        framework.frameworkVersion = metadata["frameworkVersion"]
    if metadata.get("frameworkCategoryId"):
        framework.frameworkCategoryId = str(metadata["frameworkCategoryId"])


def parse_file_versions(framework: Framework) -> list[FileVersionEntry]:
    return [FileVersionEntry.model_validate(v) for v in (framework.fileVersions or [])]


def dump_file_versions(versions: list[FileVersionEntry]) -> list[dict]:
    return [v.model_dump(mode="json") for v in versions]


def approval_status(framework: Framework) -> str:
    approval = framework.approval or {}
    if isinstance(approval, dict):
        return approval.get("status") or "pending"
    return getattr(approval, "status", None) or "pending"


def approval_by(framework: Framework) -> str | None:
    approval = framework.approval or {}
    if isinstance(approval, dict):
        return approval.get("by")
    return getattr(approval, "by", None)


def approval_date(framework: Framework):
    approval = framework.approval or {}
    if isinstance(approval, dict):
        return approval.get("date")
    return getattr(approval, "date", None)


def approval_remark(framework: Framework) -> str | None:
    approval = framework.approval or {}
    if isinstance(approval, dict):
        return approval.get("remark")
    return getattr(approval, "remark", None)


def transform_framework_doc(doc: Framework, uploaded_by_user=None) -> dict:
    current = get_current_file_version_data(doc)
    return {
        "id": str(doc.id) if doc and getattr(doc, "id", None) else None,
        "frameworkName": doc.frameworkName,
        "frameworkVersion": doc.frameworkVersion,
        "frameworkCode": doc.frameworkCode,
        "frameworkCategoryId": str(doc.frameworkCategoryId) if doc and getattr(doc, "frameworkCategoryId", None) else None,
        "currentFileVersion": doc.currentFileVersion,
        "fileInfo": {
            "fileId": str(current.fileId) if current and getattr(current, "fileId", None) else None,
            "originalFileName": current.originalFileName if current else "Unknown",
            "fileSize": data_formatter.format_file_size(
                current.fileSize if current else 0
            ),
            "fileType": current.fileType if current else "pdf",
        },
        "uploadedBy": data_formatter.format_uploaded_by(uploaded_by_user, doc.uploadedBy),
        "aiExtraction": {
            "status": (current.aiExtraction.status if current and current.aiExtraction else None),
        },
        "approval": {"status": approval_status(doc)},
        "createdAt": doc.createdAt,
        "updatedAt": doc.updatedAt,
    }


def get_framework_message(
    data_length: int, search: str | None, ai_status: str | None, approval_status_filter: str | None
) -> str:
    if data_length > 0:
        return BUSINESS_MESSAGES["EXPERT_FRAMEWORKS_SUCCESS"]
    if search or ai_status or approval_status_filter:
        return BUSINESS_MESSAGES["NO_FRAMEWORKS_SEARCH"]
    return BUSINESS_MESSAGES["NO_FRAMEWORKS_UPLOADED"]


def get_next_section_id(existing_sections: list[Section]) -> str:
    max_num = 0
    for section in existing_sections or []:
        if not section.id:
            continue
        match = re.match(r"^SEC-(\d+)$", section.id)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"SEC-{max_num + 1:02d}"


def resolve_new_section(new_section: str, controls_data: list[Section]) -> dict:
    trimmed = new_section.strip()
    if not trimmed:
        return {"error": {"message": "newSection name cannot be empty", "statusCode": 400}}

    existing = next(
        (s for s in controls_data if (s.name or "").strip().lower() == trimmed.lower()),
        None,
    )
    if existing:
        return {
            "error": {
                "message": f'Section with name "{trimmed}" already exists',
                "statusCode": 409,
            }
        }

    new_section_id = get_next_section_id(controls_data)
    if any(s.id == new_section_id for s in controls_data):
        return {
            "error": {
                "message": f'Generated Section ID "{new_section_id}" already exists',
                "statusCode": 409,
            }
        }

    cleaned = re.sub(r"^Section\s*[-:]*\s*", "", trimmed, flags=re.IGNORECASE)
    code_match = re.match(r"^([a-zA-Z]\.\d+(?:\.\d+)*|\d+(?:\.\d+)*|[a-zA-Z0-9]\b)", cleaned)
    section_prefix = code_match.group(1) if code_match else new_section_id

    return {
        "sectionIdToUse": new_section_id,
        "sectionPrefix": section_prefix,
        "nextControlNum": 1,
    }


def resolve_existing_section(
    section_id: str, controls_data: list[Section], file_version: str
) -> dict:
    if len(controls_data) == 0:
        return {
            "error": {
                "message": format_message(
                    BUSINESS_MESSAGES["VERSION_NO_CONTROLS"], version=file_version
                ),
                "statusCode": 404,
            }
        }

    section = next((s for s in controls_data if s.id == section_id), None)
    if not section:
        return {
            "error": {
                "message": format_message(
                    BUSINESS_MESSAGES["SECTION_NOT_FOUND"],
                    sectionId=section_id,
                    version=file_version,
                ),
                "statusCode": 404,
            }
        }

    existing_controls = section.controls or []
    if existing_controls:
        section_prefix = ".".join(existing_controls[0].id.split(".")[:2])
    else:
        section_prefix = section.id

    return {
        "section": section,
        "sectionIdToUse": section.id,
        "sectionPrefix": section_prefix,
        "nextControlNum": len(existing_controls) + 1,
    }


def resolve_section_and_ids(
    new_section: str | None,
    section_id: str | None,
    controls_data: list[Section],
    file_version: str,
) -> dict:
    if new_section:
        return resolve_new_section(new_section, controls_data)
    return resolve_existing_section(section_id, controls_data, file_version)


def get_current_file_version_data(framework: Framework) -> FileVersionEntry | None:
    for fv in parse_file_versions(framework):
        if fv.fileVersion == framework.currentFileVersion:
            return fv
    return None


def is_valid_control_weightage(control: ControlItem) -> bool:
    return (
        control.weightage is not None
        and isinstance(control.weightage, (int, float))
        and 1 <= control.weightage <= 10
    )


def find_invalid_control_weightage(current_file_version_data) -> ControlItem | None:
    if (
        not current_file_version_data
        or not current_file_version_data.aiExtraction
        or not current_file_version_data.aiExtraction.controls
    ):
        return None

    for section in current_file_version_data.aiExtraction.controls.controls_data:
        for control in section.controls or []:
            if not is_valid_control_weightage(control):
                return control
    return None


def update_deployment_points_to_approved(current_file_version_data) -> None:
    if (
        not current_file_version_data
        or not current_file_version_data.aiExtraction
        or not current_file_version_data.aiExtraction.controls
    ):
        return
    for section in current_file_version_data.aiExtraction.controls.controls_data:
        for control in section.controls or []:
            for dp in control.deployment_points or []:
                dp.status = "approved"


def build_deployment_points(raw_points: list[dict] | None) -> list[DeploymentPoint]:
    points = []
    for idx, dp in enumerate(raw_points or []):
        name = (dp.get("name") or "").strip()
        if not name:
            continue
        points.append(
            DeploymentPoint(
                id=dp.get("id") or f"DP-{idx + 1:03d}",
                name=name,
                status=dp.get("status") or "pending",
                path=dp.get("path") or "",
                weightage=dp.get("weightage") if dp.get("weightage") is not None else 0,
                remark=dp.get("remark") or "",
            )
        )
    return points


def apply_approved_versions(framework: Framework, current: FileVersionEntry) -> None:
    """Write mutated current version (with approved DPs) back onto framework JSONB."""
    versions = parse_file_versions(framework)
    for i, fv in enumerate(versions):
        if fv.fileVersion == current.fileVersion:
            versions[i] = current
            break
    framework.fileVersions = dump_file_versions(versions)
