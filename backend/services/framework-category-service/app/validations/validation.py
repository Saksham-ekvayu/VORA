"""Manual re-implementations of express-validator chains from
src/validations/framework-category.validation.js and framework-access.validation.js.

Node's `ValidationErrorFormatter.handleValidationErrors` surfaces only the FIRST
validation failure as `{success, message, field, value}` — these helpers
replicate that exact "first failing field, in declared order" behaviour.
"""

import re
from typing import Any

from app.helpers.helpers import to_title_case
from vora_shared.messages import VALIDATION_MESSAGES as VM

CODE_RE = re.compile(r"^[a-z0-9_]+$")
SPACES_ONLY_RE = re.compile(r"^\s+$")


class FieldError(Exception):
    def __init__(self, message: str, field: str, value: Any = None):
        super().__init__(message)
        self.message = message
        self.field = field
        self.value = value


def _validate_code(value: Any, required: bool) -> str | None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if required:
            raise FieldError(VM["FRAMEWORK_CODE_REQUIRED"], "code", value)
        return None
    normalized = str(value).strip().lower()
    if not (2 <= len(normalized) <= 100):
        raise FieldError(VM["FRAMEWORK_CODE_LENGTH"], "code", value)
    if not CODE_RE.match(normalized):
        raise FieldError(VM["FRAMEWORK_CODE_INVALID_CHARS"], "code", value)
    if normalized.startswith("_") or normalized.endswith("_"):
        raise FieldError(VM["FRAMEWORK_CODE_UNDERSCORE"], "code", value)
    return normalized


def _validate_name(value: Any, required: bool) -> str | None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if required:
            raise FieldError(VM["FRAMEWORK_NAME_REQUIRED"], "frameworkCategoryName", value)
        return None
    raw = str(value)
    if SPACES_ONLY_RE.match(raw):
        raise FieldError(VM["FRAMEWORK_NAME_SPACES_ONLY"], "frameworkCategoryName", value)
    trimmed = raw.strip()
    if not (2 <= len(trimmed) <= 200):
        raise FieldError(VM["FRAMEWORK_NAME_LENGTH"], "frameworkCategoryName", value)
    return to_title_case(trimmed)


def _validate_description(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if len(raw) > 1000:
        raise FieldError(VM["DESCRIPTION_TOO_LONG"], "description", value)
    return raw


def _validate_is_active(value: Any) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise FieldError(VM["IS_ACTIVE_BOOLEAN"], "isActive", value)
    return value


def validate_create_category(body: dict[str, Any]) -> dict[str, Any]:
    """Raises FieldError on first invalid field; returns normalized fields."""
    code = _validate_code(body.get("code"), required=True)
    name = _validate_name(body.get("frameworkCategoryName"), required=True)
    description = _validate_description(body.get("description"))
    is_active = _validate_is_active(body.get("isActive"))
    return {
        "code": code,
        "frameworkCategoryName": name,
        "description": description,
        "isActive": is_active,
    }


def validate_update_category(body: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if "code" in body and body["code"] is not None:
        result["code"] = _validate_code(body.get("code"), required=False)
    if "frameworkCategoryName" in body and body["frameworkCategoryName"] is not None:
        result["frameworkCategoryName"] = _validate_name(body.get("frameworkCategoryName"), required=False)
    if "description" in body and body["description"] is not None:
        result["description"] = _validate_description(body.get("description"))
    if "isActive" in body and body["isActive"] is not None:
        result["isActive"] = _validate_is_active(body.get("isActive"))
    return result


def validate_assign_access(body: dict[str, Any]) -> tuple[str, list[str]] | None:
    """Mirrors validateAssignFrameworkAccessInput. Returns (message) via FieldError
    with no `field` (Node's manual checks call ResponseFormatter.error without a
    field argument here)."""
    expert_id = body.get("expertId")
    framework_category_ids = body.get("frameworkCategoryIds")

    if not expert_id:
        raise FieldError("Expert ID is required", field="")
    if framework_category_ids is None:
        raise FieldError("At least one framework category must be selected", field="")
    if not isinstance(framework_category_ids, list):
        raise FieldError("Framework category IDs must be provided as an array", field="")
    if len(framework_category_ids) == 0:
        raise FieldError("At least one framework category must be selected", field="")

    return expert_id, framework_category_ids
