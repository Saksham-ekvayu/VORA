from app.schemas.common import AddressBlockIn
from pydantic import BaseModel, field_validator, model_validator
from vora_shared.validators import validate_name, validate_phone, validate_role


class CreateUserRequest(BaseModel):
    """Matches Node's `createUserValidation`: name/email/role required, phone
    optional, tenantId required only when role == "customer-admin"."""

    name: str
    email: str
    role: str
    phone: str | None = None
    secondaryPhone: str | None = None
    designation: str | None = None
    tenantId: str | None = None
    permanentAddress: AddressBlockIn | None = None
    temporaryAddress: AddressBlockIn | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return validate_name(v, required=True)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        from vora_shared.validators import validate_email

        return validate_email(v)

    @field_validator("role")
    @classmethod
    def _role(cls, v: str) -> str:
        return validate_role(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return validate_phone(v, required=False)

    @model_validator(mode="after")
    def _tenant_required_for_customer_admin(self) -> "CreateUserRequest":
        if self.role == "customer-admin" and not (self.tenantId or "").strip():
            raise ValueError("Tenant ID is required for customer-admin role")
        return self


class UpdateUserRequest(BaseModel):
    """Matches Node's `updateUserValidation`: name + role required, phone
    optional (mirrors the Node validation chain even though the controller
    itself treats every field as optional when building the update)."""

    name: str
    role: str
    phone: str | None = None
    secondaryPhone: str | None = None
    designation: str | None = None
    permanentAddress: AddressBlockIn | None = None
    temporaryAddress: AddressBlockIn | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return validate_name(v, required=True)

    @field_validator("role")
    @classmethod
    def _role(cls, v: str) -> str:
        return validate_role(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return validate_phone(v, required=False)
