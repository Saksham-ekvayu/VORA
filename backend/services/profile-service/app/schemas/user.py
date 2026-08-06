from app.schemas.common import AddressBlockIn
from pydantic import BaseModel, field_validator
from vora_shared.validators import validate_name, validate_phone


class ProfileUpdateRequest(BaseModel):
    """Schema for updating a user's own profile."""

    name: str | None = None
    phone: str | None = None
    secondaryPhone: str | None = None
    permanentAddress: AddressBlockIn | None = None
    temporaryAddress: AddressBlockIn | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return validate_name(v, required=False)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return validate_phone(v, required=False)
