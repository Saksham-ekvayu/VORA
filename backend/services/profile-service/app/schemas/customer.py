from app.schemas.common import AddressIn
from pydantic import BaseModel, field_validator
from vora_shared.validators import validate_customer_name, validate_customer_phone, validate_email


class CreateCustomerRequest(BaseModel):
    name: str
    email: str
    phone: str | None = None
    secondaryPhone: str | None = None
    avatar: str | None = None
    address: AddressIn | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return validate_customer_name(v, required=True)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return validate_customer_phone(v, required=False)


class UpdateCustomerRequest(BaseModel):
    """Matches Node's `updateCustomerValidation` (only name/phone validated;
    email/isActive/avatar/address pass through unvalidated, same as Node)."""

    name: str | None = None
    isActive: bool | None = None
    avatar: str | None = None
    email: str | None = None
    phone: str | None = None
    secondaryPhone: str | None = None
    address: AddressIn | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return validate_customer_name(v, required=False)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return validate_customer_phone(v, required=False)
