"""Port of framework.helper.js."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm.attributes import flag_modified
from vora_shared import data_format
from vora_shared import messages as msg
from vora_shared.models.document_extraction import (
    DocumentExtraction,
)
from vora_shared.models.document_extraction import ExtractionControlItem as ControlItem
from vora_shared.models.document_extraction import (
    ExtractionControls,
)
from vora_shared.models.document_extraction import ExtractionDeploymentPoint as DeploymentPoint
from vora_shared.models.document_extraction import ExtractionSection as Section
from vora_shared.models.framework import (
    FileVersionEntry,
    Framework,
)


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


def _resolve_ai_status(current, doc_extractions) -> str | None:
    if not current or not current.aiExtraction:
        return None

    if isinstance(current.aiExtraction, dict):
        return current.aiExtraction.get("status")

    if doc_extractions and isinstance(current.aiExtraction, str):
        doc_ext = doc_extractions.get(current.aiExtraction)
        if doc_ext and doc_ext.aiExtraction:
            if isinstance(doc_ext.aiExtraction, dict):
                return doc_ext.aiExtraction.get("status")
            return getattr(doc_ext.aiExtraction, "status", None)
    return None


def _resolve_file_info(current) -> dict:
    if not current:
        return {
            "fileId": None,
            "originalFileName": "Unknown",
            "fileSize": data_format.format_file_size(0),
            "fileType": "pdf",
        }
    return {
        "fileId": str(current.fileId) if getattr(current, "fileId", None) else None,
        "originalFileName": current.originalFileName,
        "fileSize": data_format.format_file_size(current.fileSize),
        "fileType": current.fileType,
    }


def transform_framework_doc(doc: Framework, uploaded_by_user=None, doc_extractions=None) -> dict:
    current = get_current_file_version_data(doc)
    return {
        "id": str(doc.id) if doc.id else None,
        "frameworkName": doc.frameworkName,
        "frameworkVersion": doc.frameworkVersion,
        "frameworkCode": doc.frameworkCode,
        "frameworkCategoryId": str(doc.frameworkCategoryId) if doc.frameworkCategoryId else None,
        "currentFileVersion": doc.currentFileVersion,
        "fileInfo": _resolve_file_info(current),
        "uploadedBy": data_format.format_uploaded_by(uploaded_by_user, doc.uploadedBy),
        "aiExtraction": {
            "status": _resolve_ai_status(current, doc_extractions),
        },
        "approval": {"status": approval_status(doc)},
        "createdAt": doc.createdAt,
        "updatedAt": doc.updatedAt,
    }


def get_framework_message(
    data_length: int, search: str | None, ai_status: str | None, approval_status_filter: str | None
) -> str:
    if data_length > 0:
        return msg.BUSINESS_MESSAGES.get(
            "USER_FRAMEWORKS_RETRIEVED", "Your frameworks retrieved successfully"
        )
    if search or ai_status or approval_status_filter:
        return msg.BUSINESS_MESSAGES.get(
            "NO_FRAMEWORKS_MATCH_CRITERIA",
            "No frameworks match your search criteria. Try adjusting your filters.",
        )
    return msg.BUSINESS_MESSAGES.get(
        "NO_USER_FRAMEWORKS",
        "You haven't uploaded any frameworks yet. Upload your first framework to get started.",
    )


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
        return {
            "error": {
                "message": msg.BUSINESS_MESSAGES.get("NEW_SECTION_EMPTY", "New section name cannot be empty"),
                "statusCode": 400,
            }
        }

    existing = next(
        (s for s in controls_data if (s.name or "").strip().lower() == trimmed.lower()),
        None,
    )
    if existing:
        return {
            "error": {
                "message": msg.format_message(
                    msg.BUSINESS_MESSAGES.get(
                        "SECTION_ALREADY_EXISTS", 'Section with name "{sectionName}" already exists'
                    ),
                    sectionName=trimmed,
                ),
                "statusCode": 409,
            }
        }

    new_section_id = get_next_section_id(controls_data)
    if any(s.id == new_section_id for s in controls_data):
        return {
            "error": {
                "message": msg.format_message(
                    msg.BUSINESS_MESSAGES.get(
                        "SECTION_ID_EXISTS", 'Generated Section ID "{sectionId}" already exists'
                    ),
                    sectionId=new_section_id,
                ),
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


def resolve_existing_section(section_id: str, controls_data: list[Section], file_version: str) -> dict:
    if len(controls_data) == 0:
        return {
            "error": {
                "message": format_message(
                    msg.BUSINESS_MESSAGES.get(
                        "VERSION_NO_CONTROLS", "No controls found in version {version}"
                    ),
                    version=file_version,
                ),
                "statusCode": 404,
            }
        }

    section = next((s for s in controls_data if s.id == section_id), None)
    if not section:
        return {
            "error": {
                "message": format_message(
                    msg.BUSINESS_MESSAGES.get(
                        "SECTION_NOT_FOUND", "Section {sectionId} not found in version {version}"
                    ),
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


def _get_ai_controls_dict(current_file_version_data, doc_ext=None, legacy_ai=None) -> dict | None:
    if not current_file_version_data:
        return None

    if legacy_ai is not None:
        return legacy_ai
    if doc_ext and doc_ext.aiExtraction:
        return (
            doc_ext.aiExtraction
            if isinstance(doc_ext.aiExtraction, dict)
            else doc_ext.aiExtraction.model_dump()
        )
    return None


def find_invalid_control_weightage(
    current_file_version_data, doc_ext=None, legacy_ai=None
) -> ControlItem | None:
    ai = _get_ai_controls_dict(current_file_version_data, doc_ext, legacy_ai)
    if not ai or not ai.get("controls"):
        return None

    controls_data = ai.get("controls").get("controls_data") or []
    for section in controls_data:
        for control in section.get("controls") or []:
            c_obj = ControlItem(**control) if isinstance(control, dict) else control
            if not is_valid_control_weightage(c_obj):
                return c_obj
    return None


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


async def validate_framework_approval_readiness(session, framework, user):
    if str(framework.uploadedBy) != str(user.id):
        return (
            None,
            None,
            None,
            msg.BUSINESS_MESSAGES.get(
                "ONLY_THE_USER_WHO_UPLOADED_THE_FRAMEWORK",
                "Only the user who uploaded the framework can edit it",
            ),
            403,
        )

    if approval_status(framework) == "approved":
        return (
            None,
            None,
            None,
            msg.BUSINESS_MESSAGES.get("FRAMEWORK_IS_ALREADY_APPROVED", "Framework is already approved"),
            400,
        )

    current = get_current_file_version_data(framework)
    if not current or not current.aiExtraction:
        return (
            None,
            None,
            None,
            msg.BUSINESS_MESSAGES.get(
                "FRAMEWORK_MUST_BE_UPLOADED_TO_AI_BEFORE",
                "Framework must be uploaded to AI before approval",
            ),
            400,
        )

    if isinstance(current.aiExtraction, str):
        doc_extraction = await session.get(DocumentExtraction, current.aiExtraction)
        if not doc_extraction or not doc_extraction.aiExtraction:
            return (
                None,
                None,
                None,
                msg.BUSINESS_MESSAGES.get(
                    "FRAMEWORK_MUST_BE_UPLOADED_TO_AI_BEFORE",
                    "Framework must be uploaded to AI before approval",
                ),
                400,
            )
        ai = doc_extraction.aiExtraction
    else:
        doc_extraction = None
        ai = current.aiExtraction

    ai_status = ai.get("status") if isinstance(ai, dict) else getattr(ai, "status", None)
    if ai_status == "processing":
        return (
            None,
            None,
            None,
            msg.BUSINESS_MESSAGES.get(
                "FRAMEWORK_AI_PROCESSING_IS_IN_PROGRESS_P", "Framework AI processing is in progress"
            ),
            409,
        )
    if ai_status == "failed":
        return (
            None,
            None,
            None,
            msg.BUSINESS_MESSAGES.get("FRAMEWORK_AI_PROCESSING_FAILED", "Framework AI processing failed"),
            409,
        )

    return current, doc_extraction, ai, None, None


async def load_ai_controls(session, file_version_doc):
    if not file_version_doc.aiExtraction:
        return (
            None,
            None,
            None,
            msg.BUSINESS_MESSAGES.get(
                "AI_EXTRACTION_DATA_NOT_FOUND_FOR_THIS_VE, AI extraction data not found for this version"
            ),
            400,
        )

    doc_ext = None
    ai_data = None
    if isinstance(file_version_doc.aiExtraction, str):
        doc_ext = await session.get(DocumentExtraction, file_version_doc.aiExtraction)
        if not doc_ext or not doc_ext.aiExtraction:
            return (
                None,
                None,
                None,
                msg.BUSINESS_MESSAGES.get(
                    "AI_EXTRACTION_DATA_NOT_FOUND_FOR_THIS_VE",
                    "AI extraction data not found for this version",
                ),
                400,
            )
        ai_data = (
            doc_ext.aiExtraction
            if isinstance(doc_ext.aiExtraction, dict)
            else doc_ext.aiExtraction.model_dump()
        )
    elif isinstance(file_version_doc.aiExtraction, dict):
        ai_data = file_version_doc.aiExtraction

    if not ai_data:
        return (
            None,
            None,
            None,
            msg.BUSINESS_MESSAGES.get(
                "AI_EXTRACTION_DATA_NOT_FOUND_FOR_THIS_VE",
                "AI extraction data not found for this version",
            ),
            400,
        )

    if not ai_data.get("controls"):
        ai_data["controls"] = ExtractionControls().model_dump()

    controls = ExtractionControls(**ai_data["controls"])
    return controls, doc_ext, ai_data, None, None


def save_ai_controls(session, file_version_doc, controls, doc_ext, ai_data):
    ai_data["controls"] = controls.model_dump(mode="json")
    if doc_ext:
        doc_ext.aiExtraction = dict(ai_data)
        flag_modified(doc_ext, "aiExtraction")
        session.add(doc_ext)
    else:
        file_version_doc.aiExtraction = dict(ai_data)


def apply_approved_versions(framework: Framework, current: FileVersionEntry) -> None:
    """Write mutated current version (with approved DPs) back onto framework JSONB."""
    versions = parse_file_versions(framework)
    for i, fv in enumerate(versions):
        if fv.fileVersion == current.fileVersion:
            versions[i] = current
            break
    framework.fileVersions = dump_file_versions(versions)


def transform_extraction_to_assignment(sections: list) -> list:
    if not sections:
        return []
    # If it's already transformed, weightage will be a dict or not present at the top level
    first_sec = sections[0]
    first_ctrl = first_sec.get("controls", [{}])[0] if first_sec.get("controls") else {}
    if isinstance(first_ctrl.get("weightage"), dict) or "customization" in first_ctrl:
        return sections

    assignment_sections = []
    for sec in sections:
        new_sec = {"id": sec.get("id"), "name": sec.get("name"), "controls": []}
        for ctrl in sec.get("controls", []):
            ctrl_weightage = ctrl.get("weightage", 10.0)
            new_ctrl = {
                "id": ctrl.get("id"),
                "name": ctrl.get("name"),
                "description": ctrl.get("description", ""),
                "customization": {
                    "source": "system",
                    "is_applicable": True,
                    "weightage": {
                        "framework_weightage": ctrl_weightage,
                        "customer_weightage": ctrl_weightage,
                    },
                },
                "deployment_points": [],
            }
            for dp in ctrl.get("deployment_points", []):
                dp_weightage = dp.get("weightage", 10.0)
                new_dp = {
                    "id": dp.get("id"),
                    "name": dp.get("name"),
                    "status": dp.get("status", "pending"),
                    "path": dp.get("path", ""),
                    "remark": dp.get("remark", ""),
                    "weightage": {
                        "framework_weightage": dp_weightage,
                        "customer_weightage": dp_weightage,
                    },
                }
                new_ctrl["deployment_points"].append(new_dp)
            new_sec["controls"].append(new_ctrl)
        assignment_sections.append(new_sec)
    return assignment_sections


def _extract_controls_for_assignment(ai_extraction: Any) -> list:
    if isinstance(ai_extraction, dict):
        if "controls" in ai_extraction:
            return transform_extraction_to_assignment(ai_extraction["controls"])
        if "controls_data" in ai_extraction:
            return transform_extraction_to_assignment(ai_extraction["controls_data"])
        return []
    if isinstance(ai_extraction, list):
        return transform_extraction_to_assignment(ai_extraction)
    return []


async def hydrate_assignment_file_versions(session, file_versions: list) -> list:
    new_file_versions = []
    for fv in file_versions or []:
        fv_data = fv.model_dump() if hasattr(fv, "model_dump") else dict(fv)
        ai_ext = fv_data.get("aiExtraction")

        if isinstance(ai_ext, str):
            doc_ext = await session.get(DocumentExtraction, ai_ext)
            fv_data["aiExtraction"] = (
                _extract_controls_for_assignment(doc_ext.aiExtraction) if doc_ext else []
            )
        else:
            fv_data["aiExtraction"] = _extract_controls_for_assignment(ai_ext)

        new_file_versions.append(fv_data)
    return new_file_versions


def _approve_single_dp(dp: Any) -> None:
    if isinstance(dp, dict):
        if dp.get("status") == "pending":
            dp["status"] = "approved"
    else:
        if getattr(dp, "status", None) == "pending":
            dp.status = "approved"


def _approve_deployment_points(controls_data: list) -> None:
    for section in controls_data:
        for control in section.get("controls") or []:
            for dp in control.get("deployment_points") or []:
                _approve_single_dp(dp)


async def _approve_fv_deployment_points(session: Any, ai_ext: Any) -> None:
    if isinstance(ai_ext, str):
        doc_ext = await session.get(DocumentExtraction, ai_ext)
        if doc_ext and isinstance(doc_ext.aiExtraction, dict):
            controls_wrapper = doc_ext.aiExtraction.get("controls")
            if isinstance(controls_wrapper, dict):
                _approve_deployment_points(controls_wrapper.get("controls_data", []))
                flag_modified(doc_ext, "aiExtraction")
                session.add(doc_ext)
    elif isinstance(ai_ext, dict) and isinstance(ai_ext.get("controls"), dict):
        _approve_deployment_points(ai_ext["controls"].get("controls_data", []))


async def approve_all_deployment_points(session: Any, framework: Framework) -> None:
    """Iterate over all fileVersions and change all pending deployment points to approved."""
    if not framework.fileVersions:
        return

    for fv in framework.fileVersions:
        if isinstance(fv, dict):
            await _approve_fv_deployment_points(session, fv.get("aiExtraction"))

    flag_modified(framework, "fileVersions")
