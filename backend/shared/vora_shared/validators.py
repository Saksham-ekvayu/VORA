"""Reusable field validators mirroring the express-validator rules used by
`authentication-service-main` and `profile-service-main` (see
`user.validation.js` / `customer.validation.js` in both Node services).

Each function raises `ValueError` on failure so it can be used directly
inside Pydantic `field_validator`s — FastAPI turns those into 422s which
`vora_shared.responses.request_validation_exception_handler` reformats into
the Node-style `{success, message, field}` envelope.
"""

import re

_NAME_RE = re.compile(r"^[A-Za-z]+(?:[ '\-][A-Za-z]+)*$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$")
_OTP_RE = re.compile(r"^\d{6}$")
_PHONE_STRIP_RE = re.compile(r"[\s\-()+]")


def capitalize_name(name: str) -> str:
    return re.sub(r"\b\w", lambda m: m.group().upper(), name.lower())


def validate_name(
    value: str | None, required: bool = True, *, min_len: int = 2, max_len: int = 50
) -> str | None:
    if value is None or value.strip() == "":
        if required:
            raise ValueError("Name is required")
        return value
    value = value.strip()
    if len(value) < min_len or len(value) > max_len:
        raise ValueError(f"Name must be between {min_len} and {max_len} characters")
    if not _NAME_RE.match(value):
        raise ValueError("Name can only contain letters, spaces, hyphens, and apostrophes")
    return capitalize_name(value)


def validate_customer_name(value: str | None, required: bool = True) -> str | None:
    if value is None or value.strip() == "":
        if required:
            raise ValueError("Customer name is required")
        return value
    value = value.strip()
    if len(value) < 2 or len(value) > 100:
        raise ValueError("Customer name must be between 2 and 100 characters")
    return value


def validate_email(value: str) -> str:
    if value is None:
        raise ValueError("Email is required")
    value = value.strip().lower()
    if not value:
        raise ValueError("Email is required")
    if not _EMAIL_RE.match(value):
        raise ValueError("Please enter a valid email, Ex: john@gmail.com")
    return value


def validate_password(value: str, field_label: str = "Password") -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{field_label} is required")
    if len(value) < 8:
        raise ValueError(f"{field_label} must be at least 8 characters long")
    if not re.search(r"[A-Z]", value):
        raise ValueError(f"{field_label} must contain at least one uppercase letter")
    if not re.search(r"[a-z]", value):
        raise ValueError(f"{field_label} must contain at least one lowercase letter")
    if not re.search(r"\d", value):
        raise ValueError(f"{field_label} must contain at least one number")
    if not re.search(r"[@$!%*#?&]", value):
        raise ValueError(f"{field_label} must contain at least one special character")
    return value


def sanitize_phone(value: str) -> str:
    return _PHONE_STRIP_RE.sub("", value)


def validate_phone(value: str | None, required: bool = True) -> str | None:
    if not value or not value.strip():
        if required:
            raise ValueError("Phone number is required")
        return value
    cleaned = sanitize_phone(value.strip())
    if not cleaned.isdigit():
        raise ValueError("Phone number must contain only digits")
    if len(cleaned) < 10 or len(cleaned) > 15:
        raise ValueError("Phone number must be between 10 and 15 digits")
    last10 = cleaned[-10:]
    if len(set(last10)) == 1:
        raise ValueError("Phone number cannot contain repeated digits")
    return cleaned


def validate_customer_phone(value: str | None, required: bool = False) -> str | None:
    if not value or not value.strip():
        if required:
            raise ValueError("Phone number is required")
        return value
    cleaned = sanitize_phone(value.strip())
    if not cleaned.isdigit():
        raise ValueError("Phone number must contain only digits")
    if len(cleaned) < 7 or len(cleaned) > 15:
        raise ValueError("Phone number must be between 7 and 15 digits")
    return cleaned


def validate_otp(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("OTP is required")
    if not _OTP_RE.match(value):
        raise ValueError("OTP must be exactly 6 digits")
    return value


def validate_role(value: str) -> str:
    value = (value or "").strip().lower()
    if not value:
        raise ValueError("Role is required")
    if len(value) < 1 or len(value) > 50:
        raise ValueError("Role must be between 1 and 50 characters")
    return value
