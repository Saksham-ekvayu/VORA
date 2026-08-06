# Standard Library
from pathlib import Path
from typing import Annotated

# Project Imports
import vora_shared
from app.utils.temp_password import generate_temp_password

# Third-party Packages
from fastapi import Depends, HTTPException
from vora_shared import messages as msg
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.email import load_template
from vora_shared.models.customer import AddressBlock, CustomerAddress
from vora_shared.models.user import User, UserAddress, UserCreatedBy
from vora_shared.query_builder import admin_tenant_query
from vora_shared.responses import error
from vora_shared.security import hash_password

TEMPLATES_DIR = Path(vora_shared.__file__).resolve().parent / "templates"
REGEX_OPTIONS_FIELD = "$options"
REGEX_PATTERN_FIELD = "$regex"


RESTRICTED_ROLES_FOR_CUSTOMER_ADMIN = {"admin", "customer-admin", "expert"}
TENANT_SCOPED_ROLES = {"customer-admin", "user", "auditor", "internal-expert"}


def address_from_blocks(permanent, temporary) -> UserAddress:
    return UserAddress(
        permanentAddress=AddressBlock(**(permanent.model_dump(exclude_none=True) if permanent else {})),
        temporaryAddress=AddressBlock(**(temporary.model_dump(exclude_none=True) if temporary else {})),
    )


async def batch_fetch_creators(docs: list) -> dict:
    creator_ids = {d.createdBy.userId for d in docs if getattr(d, "createdBy", None) and d.createdBy.userId}
    if not creator_ids:
        return {}
    creators = {}
    async for u in User.find({"_id": {"$in": list(creator_ids)}}):
        creators[u.id] = u
    return creators


def require_customer_admin(
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)] = None,
) -> AuthenticatedUser:
    if ctx.user.role != "customer-admin":
        raise HTTPException(
            403,
            {
                "message": "Access denied. Required role(s): customer-admin",
                "field": "role",
            },
        )
    return ctx


def build_customer_address(body_address) -> CustomerAddress:
    return CustomerAddress(
        permanentAddress=AddressBlock(
            **(
                body_address.permanentAddress.model_dump(exclude_none=True)
                if body_address and body_address.permanentAddress
                else {}
            )
        ),
        temporaryAddress=AddressBlock(
            **(
                body_address.temporaryAddress.model_dump(exclude_none=True)
                if body_address and body_address.temporaryAddress
                else {}
            )
        ),
    )


def add_address_updates(address, update_data: dict) -> None:
    if not address:
        return
    if address.permanentAddress:
        for key, value in address.permanentAddress.model_dump(exclude_unset=True).items():
            update_data[f"address.permanentAddress.{key}"] = value
    if address.temporaryAddress:
        for key, value in address.temporaryAddress.model_dump(exclude_unset=True).items():
            update_data[f"address.temporaryAddress.{key}"] = value


def build_customer_update_data(body) -> dict:
    update_data: dict = {}
    if body.name is not None:
        update_data["name"] = body.name
    if body.isActive is not None:
        update_data["isActive"] = body.isActive
    if body.avatar is not None:
        update_data["avatar"] = body.avatar
    if body.email is not None:
        update_data["email"] = body.email
    if body.phone is not None:
        update_data["phone"] = body.phone
    if body.secondaryPhone is not None:
        update_data["secondaryPhone"] = body.secondaryPhone

    add_address_updates(body.address, update_data)
    return update_data


def render_temp_password_email(name: str, email: str, temp_password: str) -> str:
    return load_template(
        TEMPLATES_DIR,
        "temp-password",
        {"userName": name, "userEmail": email, "tempPassword": temp_password},
    )


def build_user_update_data(body, user) -> dict:
    update_data: dict = {}
    if body.name:
        update_data["name"] = body.name
    if body.role:
        update_data["role"] = body.role
    if body.designation is not None:
        update_data["designation"] = body.designation
    if body.secondaryPhone is not None:
        update_data["secondaryPhone"] = body.secondaryPhone
    if body.phone and body.phone != user.phone:
        update_data["phone"] = body.phone
    if body.permanentAddress:
        for key, value in body.permanentAddress.model_dump(exclude_unset=True).items():
            update_data[f"address.permanentAddress.{key}"] = value
    if body.temporaryAddress:
        for key, value in body.temporaryAddress.model_dump(exclude_unset=True).items():
            update_data[f"address.temporaryAddress.{key}"] = value
    return update_data


def build_users_filter(
    search: str | None,
    is_active: str | None,
    role: str | None,
    current_role: str,
    tenant_id: str,
    creator_ids: list,
) -> dict:
    base_filter = {} if current_role == "admin" else {"tenantId": tenant_id}
    if role:
        base_filter["role"] = role
    if is_active is not None:
        base_filter["isActive"] = is_active.lower() == "true"

    additional_filters = {}
    if search:
        search_conditions = [
            {"name": {REGEX_PATTERN_FIELD: search, REGEX_OPTIONS_FIELD: "i"}},
            {"email": {REGEX_PATTERN_FIELD: search, REGEX_OPTIONS_FIELD: "i"}},
            {"role": {REGEX_PATTERN_FIELD: search, REGEX_OPTIONS_FIELD: "i"}},
            {"phone": {REGEX_PATTERN_FIELD: search, REGEX_OPTIONS_FIELD: "i"}},
        ]
        if creator_ids:
            search_conditions.append({"createdBy.userId": {"$in": creator_ids}})
        additional_filters["$or"] = search_conditions

    return {**base_filter, **additional_filters}


def get_creator_search_query(search: str, current_role: str, tenant_id: str) -> dict:
    if current_role == "admin":
        return {
            "$or": [
                {"name": {REGEX_PATTERN_FIELD: search, REGEX_OPTIONS_FIELD: "i"}},
                {"email": {REGEX_PATTERN_FIELD: search, REGEX_OPTIONS_FIELD: "i"}},
            ]
        }
    return {
        "tenantId": tenant_id,
        "$or": [
            {"name": {REGEX_PATTERN_FIELD: search, REGEX_OPTIONS_FIELD: "i"}},
            {"email": {REGEX_PATTERN_FIELD: search, REGEX_OPTIONS_FIELD: "i"}},
        ],
    }


async def validate_and_build_user(body, ctx):
    current_role = ctx.user.role
    creator_tenant_id = ctx.tenant_id

    if current_role == "customer-admin" and body.role in RESTRICTED_ROLES_FOR_CUSTOMER_ADMIN:
        return (
            error(
                msg.role_restriction(current_role, "custom roles (excluding admin, customer-admin, expert)"),
                403,
            ),
            None,
            None,
        )

    if current_role == "admin" and body.role in TENANT_SCOPED_ROLES and not body.tenantId:
        return error(f"Tenant ID is required for {body.role} role", 400, field="tenantId"), None, None

    if current_role == "admin" and body.role in TENANT_SCOPED_ROLES:
        new_tenant_id = body.tenantId
    elif current_role == "admin":
        new_tenant_id = None
    else:
        new_tenant_id = creator_tenant_id

    if await User.find_one(admin_tenant_query(new_tenant_id, {"email": body.email})):
        return error(msg.EMAIL_ALREADY_EXISTS, 400, field="email"), None, None

    if body.phone and await User.find_one(admin_tenant_query(new_tenant_id, {"phone": body.phone})):
        return error(msg.PHONE_ALREADY_EXISTS, 400, field="phone"), None, None

    temp_password = generate_temp_password(12)
    hashed_password = hash_password(temp_password)

    new_user = User(
        tenantId=new_tenant_id,
        name=body.name,
        email=body.email,
        password=hashed_password,
        role=body.role,
        designation=body.designation,
        phone=body.phone,
        secondaryPhone=body.secondaryPhone,
        isEmailVerified=True,
        isActive=True,
        tokenVersion=0,
        address=address_from_blocks(body.permanentAddress, body.temporaryAddress),
        createdBy=UserCreatedBy(type=current_role, userId=ctx.user.id),
    )
    return None, new_user, temp_password


def validate_user_roles(body, user, current_role: str, current_id_str: str, target_id_str: str):
    new_role = body.role

    if current_id_str == target_id_str and new_role and new_role != current_role:
        return error(msg.cannot_change_own_role(current_role), 400)

    if current_role == "customer-admin" and not (
        user.createdBy
        and user.createdBy.type == "customer-admin"
        and str(user.createdBy.userId) == current_id_str
    ):
        return error(msg.ONLY_UPDATE_CREATED_USERS, 403)

    if (
        current_role == "customer-admin"
        and new_role
        and new_role != user.role
        and new_role in RESTRICTED_ROLES_FOR_CUSTOMER_ADMIN
    ):
        return error(
            msg.role_assignment_restriction(
                current_role, "custom roles (excluding admin, customer-admin, expert)"
            ),
            403,
        )

    if (
        current_role == "admin"
        and user.role == "admin"
        and new_role
        and new_role != "admin"
        and current_id_str != target_id_str
    ):
        return error(msg.CANNOT_CHANGE_ADMIN_ROLE, 400)

    return None


async def validate_user_update(body, user, ctx, target_id_str: str):
    current_user = ctx.user
    current_role = current_user.role
    tenant_id = ctx.tenant_id
    current_id_str = str(current_user.id)

    role_error = validate_user_roles(body, user, current_role, current_id_str, target_id_str)
    if role_error:
        return role_error

    if body.phone and body.phone != user.phone:
        existing_phone = await User.find_one(admin_tenant_query(tenant_id, {"phone": body.phone}))
        if existing_phone and str(existing_phone.id) != target_id_str:
            return error(msg.PHONE_ALREADY_EXISTS, 400, field="phone")

    return None


def build_profile_update_data(body, user) -> dict:
    update_data: dict = {}
    if body.name is not None and body.name != user.name:
        update_data["name"] = body.name
    if body.phone is not None and body.phone != user.phone:
        update_data["phone"] = body.phone
    if body.secondaryPhone is not None:
        update_data["secondaryPhone"] = body.secondaryPhone
    if body.permanentAddress is not None:
        for key, value in body.permanentAddress.model_dump(exclude_unset=True).items():
            update_data[f"address.permanentAddress.{key}"] = value
    if body.temporaryAddress is not None:
        for key, value in body.temporaryAddress.model_dump(exclude_unset=True).items():
            update_data[f"address.temporaryAddress.{key}"] = value
    return update_data
