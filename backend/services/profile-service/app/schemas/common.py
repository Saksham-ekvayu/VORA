from pydantic import BaseModel


class AddressBlockIn(BaseModel):
    country: str | None = None
    state: str | None = None
    city: str | None = None
    locality: str | None = None


class AddressIn(BaseModel):
    permanentAddress: AddressBlockIn | None = None
    temporaryAddress: AddressBlockIn | None = None
