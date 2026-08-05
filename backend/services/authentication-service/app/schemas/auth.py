from pydantic import BaseModel, field_validator

from vora_shared.validators import (
    validate_email,
    validate_otp,
    validate_password,
    validate_phone,
)


class RegisterRequest(BaseModel):
    """Matches Node's `registerValidation` — role is NOT accepted from the
    client; `auth.controller.js#register` always creates role="user"."""

    name: str
    email: str
    password: str
    phone: str

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        from vora_shared.validators import validate_name

        return validate_name(v, required=True)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return validate_phone(v, required=True)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Password is required")
        return v


class OtpVerifyRequest(BaseModel):
    email: str
    otp: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("otp")
    @classmethod
    def _otp(cls, v: str) -> str:
        return validate_otp(v)


class EmailOnlyRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return validate_email(v)


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("otp")
    @classmethod
    def _otp(cls, v: str) -> str:
        return validate_otp(v)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password(v)


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str

    @field_validator("currentPassword")
    @classmethod
    def _current(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Current password is required")
        return v

    @field_validator("newPassword")
    @classmethod
    def _new(cls, v: str) -> str:
        return validate_password(v)
