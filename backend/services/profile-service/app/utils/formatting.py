"""Mirrors `data-formatter.service.js` from profile-service-main."""

from typing import Any

from vora_shared.models.customer import Customer
from vora_shared.models.user import User


def _cb_get(created_by: Any, key: str, default=None):
    if created_by is None:
        return default
    if isinstance(created_by, dict):
        return created_by.get(key, default)
    return getattr(created_by, key, default)


def format_created_by(created_by: Any, creator: User | None = None) -> dict:
    ctype = _cb_get(created_by, "type") or "self"

    if ctype == "self":
        return {"type": "self", "user": None}

    if ctype in ("admin", "customer-admin"):
        if creator is not None:
            return {
                "type": ctype,
                "user": {
                    "id": str(creator.id),
                    "name": creator.name or f"Unknown {ctype}",
                    "email": creator.email or "N/A",
                    "role": getattr(creator, "role", ctype) or ctype,
                    "avatar": getattr(creator, "avatar", None),
                },
            }

        user_id = _cb_get(created_by, "userId")
        if user_id:
            return {
                "type": ctype,
                "user": {
                    "id": str(user_id),
                    "name": f"Unknown {ctype}",
                    "email": "N/A",
                    "role": ctype,
                    "avatar": None,
                },
            }

    return {"type": ctype or "unknown", "user": None}


def default_address_block() -> dict:
    return {"country": None, "state": None, "city": None, "locality": None}


def _block_dict(block: Any) -> dict:
    if block is None:
        return default_address_block()
    if isinstance(block, dict):
        return {**default_address_block(), **block}
    if hasattr(block, "model_dump"):
        return block.model_dump()
    return default_address_block()


def address_dict(address: Any) -> dict:
    if address is None:
        return {
            "permanentAddress": default_address_block(),
            "temporaryAddress": default_address_block(),
        }
    if isinstance(address, dict):
        return {
            "permanentAddress": _block_dict(address.get("permanentAddress")),
            "temporaryAddress": _block_dict(address.get("temporaryAddress")),
        }
    return {
        "permanentAddress": _block_dict(getattr(address, "permanentAddress", None)),
        "temporaryAddress": _block_dict(getattr(address, "temporaryAddress", None)),
    }


def merge_address(
    existing: Any,
    permanent: Any = None,
    temporary: Any = None,
) -> dict:
    """Deep-merge address block updates into a JSONB-friendly dict."""
    addr = address_dict(existing)
    if permanent is not None:
        updates = (
            permanent.model_dump(exclude_unset=True) if hasattr(permanent, "model_dump") else dict(permanent)
        )
        addr["permanentAddress"] = {**addr["permanentAddress"], **updates}
    if temporary is not None:
        updates = (
            temporary.model_dump(exclude_unset=True) if hasattr(temporary, "model_dump") else dict(temporary)
        )
        addr["temporaryAddress"] = {**addr["temporaryAddress"], **updates}
    return addr


def customer_summary(customer: Customer | None) -> dict | None:
    if not customer:
        return None
    return {
        "id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "secondaryPhone": customer.secondaryPhone,
        "avatar": customer.avatar,
        "address": address_dict(customer.address),
    }


def customer_dict(customer: Customer, creator: User | None = None) -> dict:
    """Curated customer representation used for create/update/toggle/list."""
    return {
        "id": str(customer.id),
        "tenantId": str(customer.tenantId) if customer and getattr(customer, "tenantId", None) else None,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "secondaryPhone": customer.secondaryPhone,
        "isActive": customer.isActive,
        "avatar": customer.avatar,
        "address": address_dict(customer.address),
        "createdBy": format_created_by(customer.createdBy, creator),
        "createdAt": customer.createdAt,
        "updatedAt": customer.updatedAt,
    }


def sanitize_user(user: User) -> dict:
    """Public-safe user fields (no password/otp/tokenVersion)."""
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "designation": user.designation,
        "isActive": user.isActive,
        "isEmailVerified": user.isEmailVerified,
        "avatar": user.avatar,
        "createdAt": user.createdAt,
        "updatedAt": user.updatedAt,
    }


def user_admin_dict(user: User, creator: User | None = None) -> dict:
    """Matches the `transform` callback in `admin.controller.js#getAllUsers`."""
    return {
        "id": str(user.id),
        "tenantId": str(user.tenantId) if user and getattr(user, "tenantId", None) else None,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "designation": user.designation,
        "phone": user.phone,
        "secondaryPhone": user.secondaryPhone,
        "avatar": user.avatar,
        "address": address_dict(user.address),
        "createdBy": format_created_by(user.createdBy, creator),
        "isEmailVerified": user.isEmailVerified,
        "isActive": user.isActive,
        "createdAt": user.createdAt,
        "updatedAt": user.updatedAt,
    }


def created_by_user_id(created_by: Any) -> str | None:
    uid = _cb_get(created_by, "userId")
    return str(uid) if uid else None


def created_by_type(created_by: Any) -> str | None:
    return _cb_get(created_by, "type")
