import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from app.schemas.admin import CreateUserRequest, UpdateUserRequest
from app.schemas.customer import CreateCustomerRequest, UpdateCustomerRequest
from app.utils.formatting import (
    created_by_type,
    created_by_user_id,
    customer_dict,
    customer_summary,
    merge_address,
    sanitize_user,
    user_admin_dict,
)
from app.utils.temp_password import generate_temp_password
from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from sqlalchemy import delete, or_, select
from sqlalchemy.orm.attributes import flag_modified
from vora_shared import messages as msg
from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.avatar_uploads import AvatarUploadError, delete_avatar_file, save_avatar
from vora_shared.database import session_scope
from vora_shared.email import load_template, send_email
from vora_shared.ids import is_valid_id
from vora_shared.models.customer import AddressBlock, Customer, CustomerAddress, CustomerCreatedBy
from vora_shared.models.framework_access import FrameworkAccess
from vora_shared.models.user import User, UserAddress, UserCreatedBy
from vora_shared.query_builder import apply_search_filter, apply_sort, paginate_stmt
from vora_shared.responses import error, forbidden, paginated, success
from vora_shared.security import hash_password

router = APIRouter()
logger = logging.getLogger(__name__)

import vora_shared

TEMPLATES_DIR = Path(vora_shared.__file__).resolve().parent / "templates"

TENANT_SCOPED_ROLES = {"customer-admin", "user", "auditor", "internal-expert"}
RESTRICTED_ROLES_FOR_CUSTOMER_ADMIN = {"admin", "customer-admin", "expert"}


def _address_from_blocks(permanent, temporary) -> dict:
    return UserAddress(
        permanentAddress=AddressBlock(**(permanent.model_dump(exclude_none=True) if permanent else {})),
        temporaryAddress=AddressBlock(**(temporary.model_dump(exclude_none=True) if temporary else {})),
    ).model_dump(mode="json")


async def _batch_fetch_creators(session, docs: list) -> dict:
    creator_ids = {created_by_user_id(d.createdBy) for d in docs}
    creator_ids.discard(None)
    if not creator_ids:
        return {}
    result = await session.execute(select(User).where(User.id.in_(list(creator_ids))))
    return {u.id: u for u in result.scalars().all()}


def _user_by_tenant_stmt(tenant_id: str | None, *extra):
    stmt = select(User)
    if tenant_id:
        stmt = stmt.where(User.tenantId == tenant_id)
    for clause in extra:
        stmt = stmt.where(clause)
    return stmt


def _validate_customer_admin_permission(user: User, current_user_id: str) -> bool:
    """Validate if customer-admin has permission to access/modify a user."""
    return (
        created_by_type(user.createdBy) == "customer-admin"
        and created_by_user_id(user.createdBy) == current_user_id
    )


def _apply_customer_updates(customer: Customer, body: UpdateCustomerRequest):
    """Apply updates to customer object."""
    if body.name is not None:
        customer.name = body.name
    if body.isActive is not None:
        customer.isActive = body.isActive
    if body.avatar is not None:
        customer.avatar = body.avatar
    if body.email is not None:
        customer.email = body.email
    if body.phone is not None:
        customer.phone = body.phone
    if body.secondaryPhone is not None:
        customer.secondaryPhone = body.secondaryPhone
    if body.address:
        customer.address = merge_address(
            customer.address,
            body.address.permanentAddress,
            body.address.temporaryAddress,
        )
        flag_modified(customer, "address")
    customer.updatedAt = datetime.now(timezone.utc)


def _apply_user_updates(user: User, body: UpdateUserRequest):
    """Apply updates to user object."""
    if body.name:
        user.name = body.name
    if body.role:
        user.role = body.role
    if body.designation is not None:
        user.designation = body.designation
    if body.secondaryPhone is not None:
        user.secondaryPhone = body.secondaryPhone
    if body.phone and body.phone != user.phone:
        user.phone = body.phone
    if body.permanentAddress or body.temporaryAddress:
        user.address = merge_address(user.address, body.permanentAddress, body.temporaryAddress)
        flag_modified(user, "address")
    user.updatedAt = datetime.now(timezone.utc)


async def _check_customer_email_exists(session, email: str, exclude_id: str = None) -> bool:
    """Check if customer email already exists."""
    stmt = select(Customer).where(Customer.email == email)
    if exclude_id:
        stmt = stmt.where(Customer.id != exclude_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _check_customer_phone_exists(session, phone: str, exclude_id: str = None) -> bool:
    """Check if customer phone already exists."""
    stmt = select(Customer).where(Customer.phone == phone)
    if exclude_id:
        stmt = stmt.where(Customer.id != exclude_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


def _build_customer_address(body: CreateCustomerRequest) -> dict:
    """Build customer address from request body."""
    return CustomerAddress(
        permanentAddress=AddressBlock(
            **(
                body.address.permanentAddress.model_dump(exclude_none=True)
                if body.address and body.address.permanentAddress
                else {}
            )
        ),
        temporaryAddress=AddressBlock(
            **(
                body.address.temporaryAddress.model_dump(exclude_none=True)
                if body.address and body.address.temporaryAddress
                else {}
            )
        ),
    ).model_dump(mode="json")


def _build_user_search_conditions(search: str, creator_ids: list):
    """Build search conditions for user query."""
    conditions = [
        User.name.ilike(f"%{search}%"),
        User.email.ilike(f"%{search}%"),
        User.role.ilike(f"%{search}%"),
        User.phone.ilike(f"%{search}%"),
    ]
    if creator_ids:
        conditions.append(User.createdBy["userId"].astext.in_(creator_ids))
    return conditions


def _validate_user_creation_permissions(
    current_role: str, body: CreateUserRequest, creator_tenant_id: str
) -> tuple[str | None, str | None]:
    """Validate user creation permissions and return tenant_id or error."""
    if current_role == "customer-admin" and body.role in RESTRICTED_ROLES_FOR_CUSTOMER_ADMIN:
        return None, error(
            msg.role_restriction(current_role, "custom roles (excluding admin, customer-admin, expert)"),
            403,
        )

    if current_role == "admin" and body.role in TENANT_SCOPED_ROLES and not body.tenantId:
        return None, error(f"Tenant ID is required for {body.role} role", 400, field="tenantId")

    if current_role == "admin":
        new_tenant_id = body.tenantId if body.role in TENANT_SCOPED_ROLES else None
    else:
        new_tenant_id = creator_tenant_id

    return new_tenant_id, None


def _validate_user_update_permissions(
    current_user: AuthenticatedUser, target_user: User, new_role: str | None
) -> tuple[bool, str | None, int | None]:
    """Validate user update permissions."""
    current_role = current_user.role
    current_id_str = str(current_user.id)
    target_id_str = str(target_user.id)

    # Can't change own role
    if current_id_str == target_id_str and new_role and new_role != current_user.role:
        return False, msg.cannot_change_own_role(current_user.role), 400

    # Customer-admin restrictions
    if current_role == "customer-admin":
        if not _validate_customer_admin_permission(target_user, current_id_str):
            return False, msg.ONLY_UPDATE_CREATED_USERS, 403
        if new_role and new_role != target_user.role and new_role in RESTRICTED_ROLES_FOR_CUSTOMER_ADMIN:
            return (
                False,
                msg.role_assignment_restriction(
                    current_role, "custom roles (excluding admin, customer-admin, expert)"
                ),
                403,
            )

    # Admin restrictions
    if (
        current_role == "admin"
        and target_user.role == "admin"
        and new_role
        and new_role != "admin"
        and current_id_str != target_id_str
    ):
        return False, msg.CANNOT_CHANGE_ADMIN_ROLE, 400

    return True, None, None


# ------------------------------------------------------------------------
# Customer management
# ------------------------------------------------------------------------


@router.post("/customers", tags=["admin/customers"])
async def create_customer(
    body: Annotated[CreateCustomerRequest, Body()],
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(f"[CREATE-CUSTOMER] Request started | user_id={ctx.user.id} | email={body.email} | name={body.name}")
    async with session_scope() as session:
        if await _check_customer_email_exists(session, body.email):
            logger.warning(f"[CREATE-CUSTOMER] Validation failed | reason: email_exists | email={body.email}")
            return error("Email already exists", 400, field="email")

        if body.phone and await _check_customer_phone_exists(session, body.phone):
            logger.warning(f"[CREATE-CUSTOMER] Validation failed | reason: phone_exists | phone={body.phone}")
            return error("Customer with this phone number already exists", 400, field="phone")

        tenant_id = f"tenant_{secrets.token_hex(8)}"
        while (
            await session.execute(select(Customer).where(Customer.tenantId == tenant_id))
        ).scalar_one_or_none():
            tenant_id = f"tenant_{secrets.token_hex(8)}"

        now = datetime.now(timezone.utc)
        new_customer = Customer(
            tenantId=tenant_id,
            name=body.name,
            email=body.email,
            phone=body.phone,
            secondaryPhone=body.secondaryPhone,
            avatar=body.avatar,
            address=_build_customer_address(body),
            createdBy=CustomerCreatedBy(
                type="admin" if ctx.user.role == "admin" else "self",
                userId=ctx.user.id,
            ).model_dump(mode="json"),
            createdAt=now,
            updatedAt=now,
        )
        session.add(new_customer)
        await session.flush()
        result = customer_dict(new_customer, ctx.user)

    logger.info(f"[CREATE-CUSTOMER] ✅ Created | customer_id={str(new_customer.id)} | tenant={tenant_id} | email={body.email}")
    return success(result, "Customer created successfully")


@router.get("/customers", tags=["admin/customers"])
async def get_all_customers(
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
    page: Annotated[int, Query()] = 1,
    limit: Annotated[int, Query()] = 10,
    search: Annotated[str | None, Query()] = None,
    is_active: Annotated[str | None, Query(alias="isActive")] = None,
    sort_by: Annotated[str | None, Query(alias="sortBy")] = None,
    sort_order: Annotated[str | None, Query(alias="sortOrder")] = None,
):
    logger.info(f"[GET-CUSTOMERS] Request started | user_id={ctx.user.id} | page={page} | limit={limit} | search={search} | is_active={is_active}")
    allowed_sort_fields = ["name", "email", "tenantId", "createdAt", "updatedAt"]
    allowed_search_fields = ["name", "email", "tenantId", "phone"]

    async with session_scope() as session:
        stmt = select(Customer)
        if is_active is not None:
            stmt = stmt.where(Customer.isActive.is_(is_active.lower() == "true"))
        stmt = apply_search_filter(Customer, search, allowed_search_fields, stmt)
        stmt = apply_sort(Customer, stmt, sort_by, sort_order, allowed_sort_fields)
        data, pagination = await paginate_stmt(session, stmt, page=page, limit=limit)

        creators = await _batch_fetch_creators(session, data)
        result = [customer_dict(c, creators.get(created_by_user_id(c.createdBy))) for c in data]

    logger.info(f"[GET-CUSTOMERS] ✅ Retrieved | count={len(result)} | total={pagination['total']} | user_id={ctx.user.id}")
    return paginated(result, pagination, "Customers retrieved successfully")


@router.get("/customers/{id}", tags=["admin/customers"])
async def get_customer_by_id(
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
    id: str,
    page: Annotated[int, Query()] = 1,
    limit: Annotated[int, Query()] = 10,
    search: Annotated[str | None, Query()] = None,
    is_active: Annotated[str | None, Query(alias="isActive")] = None,
    sort_by: Annotated[str | None, Query(alias="sortBy")] = None,
    sort_order: Annotated[str | None, Query(alias="sortOrder")] = None,
):
    logger.info(f"[GET-CUSTOMER] Request started | user_id={ctx.user.id} | customer_id={id} | page={page}")
    if not is_valid_id(id):
        logger.warning(f"[GET-CUSTOMER] Invalid ID | customer_id={id}")
        return error(msg.CUSTOMER_NOT_FOUND, 404)

    allowed_sort_fields = ["name", "email", "createdAt", "updatedAt"]
    allowed_search_fields = ["name", "email"]

    async with session_scope() as session:
        customer = await session.get(Customer, id)
        if not customer:
            logger.warning(f"[GET-CUSTOMER] Not found | customer_id={id} | user_id={ctx.user.id}")
            return error(msg.CUSTOMER_NOT_FOUND, 404)

        creator = None
        creator_id = created_by_user_id(customer.createdBy)
        if creator_id:
            creator = await session.get(User, creator_id)

        users_stmt = select(User).where(User.tenantId == customer.tenantId)
        if is_active is not None:
            users_stmt = users_stmt.where(User.isActive.is_(is_active.lower() == "true"))
        users_stmt = apply_search_filter(User, search, allowed_search_fields, users_stmt)
        users_stmt = apply_sort(User, users_stmt, sort_by, sort_order, allowed_sort_fields)
        users_data, users_pagination = await paginate_stmt(session, users_stmt, page=page, limit=limit)

        customer_details = customer_dict(customer, creator)
        customer_details["users"] = {
            "data": [sanitize_user(u) for u in users_data],
            "pagination": users_pagination,
        }

    logger.info(f"[GET-CUSTOMER] ✅ Retrieved | customer_id={id} | users_count={len(users_data)} | user_id={ctx.user.id}")
    return success(customer_details, "Customer details retrieved successfully")


@router.patch("/customers/{id}", tags=["admin/customers"])
async def update_customer(
    id: str,
    body: Annotated[UpdateCustomerRequest, Body()],
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(f"[PATCH-CUSTOMER] Update request | user_id={ctx.user.id} | customer_id={id} | email={body.email} | name={body.name}")
    if not is_valid_id(id):
        logger.warning(f"[PATCH-CUSTOMER] Invalid ID | customer_id={id}")
        return error(msg.CUSTOMER_NOT_FOUND, 404)

    async with session_scope() as session:
        customer = await session.get(Customer, id)
        if not customer:
            logger.warning(f"[PATCH-CUSTOMER] Not found | customer_id={id} | user_id={ctx.user.id}")
            return error(msg.CUSTOMER_NOT_FOUND, 404)

        if body.email and body.email != customer.email:
            if await _check_customer_email_exists(session, body.email, id):
                logger.warning(f"[PATCH-CUSTOMER] Email already exists | email={body.email}")
                return error(msg.EMAIL_ALREADY_EXISTS, 400, field="email")

        if body.phone and body.phone != customer.phone:
            if await _check_customer_phone_exists(session, body.phone, id):
                logger.warning(f"[PATCH-CUSTOMER] Phone already exists | phone={body.phone}")
                return error(msg.PHONE_ALREADY_EXISTS, 400, field="phone")

        _apply_customer_updates(customer, body)

        creator = None
        creator_id = created_by_user_id(customer.createdBy)
        if creator_id:
            creator = await session.get(User, creator_id)
        result = customer_dict(customer, creator)

    logger.info(f"[PATCH-CUSTOMER] ✅ Updated | customer_id={id} | user_id={ctx.user.id}")
    return success(result, "Customer updated successfully")


@router.patch("/customers/{id}/toggle-status", tags=["admin/customers"])
async def toggle_customer_status(id: str, ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[PATCH-CUSTOMER-STATUS] Toggle request | user_id={ctx.user.id} | customer_id={id}")
    if not is_valid_id(id):
        logger.warning(f"[PATCH-CUSTOMER-STATUS] Invalid ID | customer_id={id}")
        return error(msg.CUSTOMER_NOT_FOUND, 404)

    async with session_scope() as session:
        customer = await session.get(Customer, id)
        if not customer:
            logger.warning(f"[PATCH-CUSTOMER-STATUS] Not found | customer_id={id}")
            return error(msg.CUSTOMER_NOT_FOUND, 404)

        customer.isActive = not customer.isActive
        customer.updatedAt = datetime.now(timezone.utc)

        creator = None
        creator_id = created_by_user_id(customer.createdBy)
        if creator_id:
            creator = await session.get(User, creator_id)
        result = customer_dict(customer, creator)
        action = "activated" if customer.isActive else "deactivated"

    logger.info(f"[PATCH-CUSTOMER-STATUS] ✅ {action.upper()} | customer_id={id} | status={customer.isActive}")
    return success(result, f"Customer {action} successfully")


@router.delete("/customers/{id}", tags=["admin/customers"])
async def delete_customer(id: str, ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[DELETE-CUSTOMER] Request started | user_id={ctx.user.id} | customer_id={id}")
    if not is_valid_id(id):
        logger.warning(f"[DELETE-CUSTOMER] Invalid ID | customer_id={id}")
        return error(msg.CUSTOMER_NOT_FOUND, 404)

    async with session_scope() as session:
        customer = await session.get(Customer, id)
        if not customer:
            logger.warning(f"[DELETE-CUSTOMER] Not found | customer_id={id}")
            return error(msg.CUSTOMER_NOT_FOUND, 404)
        await session.delete(customer)

    logger.info(f"[DELETE-CUSTOMER] ✅ Deleted | customer_id={id} | user_id={ctx.user.id}")
    return success(None, "Customer deleted successfully")


@router.post("/customers/{id}/avatar", tags=["admin/customers"])
async def update_customer_avatar_by_admin(
    id: str,
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
    avatar: Annotated[UploadFile | None, File()] = None,
):
    """Admin uploads a customer avatar by customer id (from updated Mongo API)."""
    logger.info(f"[POST-CUSTOMER-AVATAR-ADMIN] Request started | user_id={ctx.user.id} | customer_id={id} | filename={avatar.filename if avatar else 'None'}")
    if avatar is None:
        logger.warning(f"[POST-CUSTOMER-AVATAR-ADMIN] Validation failed | customer_id={id} | reason: avatar_required")
        return error(msg.AVATAR_REQUIRED, 400, field="avatar")

    if not is_valid_id(id):
        logger.warning(f"[POST-CUSTOMER-AVATAR-ADMIN] Invalid ID | customer_id={id}")
        return error(msg.CUSTOMER_NOT_FOUND, 404)

    async with session_scope() as session:
        customer = await session.get(Customer, id)
        if not customer:
            logger.warning(f"[POST-CUSTOMER-AVATAR-ADMIN] Not found | customer_id={id}")
            return error(msg.CUSTOMER_NOT_FOUND, 404)

        try:
            avatar_url = await save_avatar(avatar, f"customer-{customer.tenantId}")
            logger.info(f"[POST-CUSTOMER-AVATAR-ADMIN] Avatar saved | customer_id={id} | url={avatar_url}")
        except AvatarUploadError as exc:
            logger.error(f"[POST-CUSTOMER-AVATAR-ADMIN] Error | customer_id={id} | error: {exc.message}")
            return error(exc.message, 400, field="avatar")

        old_avatar = customer.avatar
        customer.avatar = avatar_url
        customer.updatedAt = datetime.now(timezone.utc)

        creator = None
        creator_id = created_by_user_id(customer.createdBy)
        if creator_id:
            creator = await session.get(User, creator_id)
        result = customer_dict(customer, creator)

    delete_avatar_file(old_avatar)
    logger.info(f"[POST-CUSTOMER-AVATAR-ADMIN] ✅ Updated | customer_id={id} | user_id={ctx.user.id}")
    return success(result, msg.AVATAR_UPDATED)


# ------------------------------------------------------------------------
# Admin user management
# ------------------------------------------------------------------------


@router.post("/users", tags=["admin/users"])
async def create_user(
    body: Annotated[CreateUserRequest, Body()], ctx: Annotated[AuthenticatedUser, Depends(authenticate)]
):
    logger.info(f"[CREATE-USER] Request started | user_id={ctx.user.id} | role={ctx.user.role} | new_email={body.email} | new_role={body.role}")
    current_role = ctx.user.role
    creator_tenant_id = ctx.tenant_id

    # Validate permissions
    new_tenant_id, error_response = _validate_user_creation_permissions(current_role, body, creator_tenant_id)
    if error_response:
        logger.warning(f"[CREATE-USER] Permission denied | current_role={current_role} | new_role={body.role}")
        return error_response

    async with session_scope() as session:
        email_stmt = _user_by_tenant_stmt(new_tenant_id, User.email == body.email)
        if (await session.execute(email_stmt)).scalar_one_or_none():
            logger.warning(f"[CREATE-USER] Email already exists | email={body.email}")
            return error(msg.EMAIL_ALREADY_EXISTS, 400, field="email")

        if body.phone:
            phone_stmt = _user_by_tenant_stmt(new_tenant_id, User.phone == body.phone)
            if (await session.execute(phone_stmt)).scalar_one_or_none():
                logger.warning(f"[CREATE-USER] Phone already exists | phone={body.phone}")
                return error("User with this phone number already exists", 400, field="phone")

        temp_password = generate_temp_password(12)
        hashed_password = hash_password(temp_password)

        created_by_type_val = current_role if current_role in ("admin", "customer-admin", "self") else "admin"
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
            address=_address_from_blocks(body.permanentAddress, body.temporaryAddress),
            createdBy=UserCreatedBy(type=created_by_type_val, userId=ctx.user.id).model_dump(mode="json"),
        )
        session.add(new_user)
        await session.flush()
        user_id = str(new_user.id)
        tenant = str(new_user.tenantId) if new_user.tenantId else None
        user_name = new_user.name
        user_email = new_user.email

    email_sent = await send_email(
        user_email,
        f"Account Created - Welcome {user_name}",
        _render_temp_password_email(user_name, user_email, temp_password),
    )

    if not email_sent:
        logger.error(f"[CREATE-USER] Email failed | user_id={user_id} | email={user_email}")
        return success(
            {"id": user_id, "tenantId": tenant},
            msg.USER_CREATED_EMAIL_FAILED,
        )

    logger.info(f"[CREATE-USER] ✅ Created | user_id={user_id} | email={user_email} | role={body.role}")
    return success({"id": user_id, "tenantId": tenant}, msg.USER_CREATED)


def _render_temp_password_email(name: str, email: str, temp_password: str) -> str:
    return load_template(
        TEMPLATES_DIR,
        "temp-password",
        {"userName": name, "userEmail": email, "tempPassword": temp_password},
    )


@router.patch("/users/{id}", tags=["admin/users"])
async def update_user(
    id: str,
    body: Annotated[UpdateUserRequest, Body()],
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
):
    logger.info(f"[PATCH-USER] Request started | user_id={ctx.user.id} | target_user={id} | new_role={body.role}")
    current_user = ctx.user
    tenant_id = ctx.tenant_id

    if not is_valid_id(id):
        logger.warning(f"[PATCH-USER] Invalid ID | target_user={id}")
        return error(msg.USER_NOT_FOUND, 404, field="user")

    async with session_scope() as session:
        user = (await session.execute(_user_by_tenant_stmt(tenant_id, User.id == id))).scalar_one_or_none()
        if not user:
            logger.warning(f"[PATCH-USER] Not found | target_user={id} | tenant={tenant_id}")
            return error(msg.USER_NOT_FOUND, 404, field="user")

        # Validate permissions
        is_valid, error_msg, status_code = _validate_user_update_permissions(current_user, user, body.role)
        if not is_valid:
            logger.warning(f"[PATCH-USER] Permission denied | current_user={ctx.user.id} | error={error_msg}")
            return error(error_msg, status_code)

        # Check phone uniqueness
        if body.phone and body.phone != user.phone:
            existing_phone = (
                await session.execute(_user_by_tenant_stmt(tenant_id, User.phone == body.phone))
            ).scalar_one_or_none()
            if existing_phone and str(existing_phone.id) != id:
                logger.warning(f"[PATCH-USER] Phone already exists | phone={body.phone}")
                return error("User with this phone number already exists", 400, field="phone")

        _apply_user_updates(user, body)
        result = {
            "id": str(user.id),
            "tenantId": str(user.tenantId) if user.tenantId else None,
        }

    logger.info(f"[PATCH-USER] ✅ Updated | user_id={id} | role={body.role} | by={ctx.user.id}")
    return success(result, "User updated successfully")


@router.get("/users", tags=["admin/users"])
async def get_all_users(
    ctx: Annotated[AuthenticatedUser, Depends(authenticate)],
    page: Annotated[int, Query()] = 1,
    limit: Annotated[int, Query()] = 10,
    search: Annotated[str | None, Query()] = None,
    is_active: Annotated[str | None, Query(alias="isActive")] = None,
    role: Annotated[str | None, Query()] = None,
    sort_by: Annotated[str | None, Query(alias="sortBy")] = None,
    sort_order: Annotated[str | None, Query(alias="sortOrder")] = None,
):
    logger.info(f"[GET-USERS] Request started | user_id={ctx.user.id} | page={page} | limit={limit} | role={role} | is_active={is_active}")
    current_role = ctx.user.role
    tenant_id = ctx.tenant_id

    allowed_sort_fields = [
        "name",
        "email",
        "role",
        "createdAt",
        "updatedAt",
        "isEmailVerified",
        "isActive",
    ]

    async with session_scope() as session:
        stmt = select(User).where(User.id != ctx.user.id)
        if current_role != "admin":
            stmt = stmt.where(User.tenantId == tenant_id)
        if role:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.isActive.is_(is_active.lower() == "true"))

        if search:
            creator_stmt = select(User.id).where(
                or_(
                    User.name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )
            if current_role != "admin":
                creator_stmt = creator_stmt.where(User.tenantId == tenant_id)
            creator_ids = [row[0] for row in (await session.execute(creator_stmt)).all()]

            search_conditions = _build_user_search_conditions(search, creator_ids)
            stmt = stmt.where(or_(*search_conditions))

        stmt = apply_sort(User, stmt, sort_by, sort_order, allowed_sort_fields)
        data, pagination = await paginate_stmt(session, stmt, page=page, limit=limit)

        creators = await _batch_fetch_creators(session, data)
        users_list = [user_admin_dict(u, creators.get(created_by_user_id(u.createdBy))) for u in data]

    message = msg.USER_LIST_RETRIEVED
    if not users_list:
        message = msg.NO_USERS_MATCH_CRITERIA if (search or is_active or role) else msg.NO_USERS_AVAILABLE

    logger.info(f"[GET-USERS] ✅ Retrieved | count={len(users_list)} | total={pagination['total']} | user_id={ctx.user.id}")
    return paginated(users_list, pagination, message)


@router.get("/users/{id}", tags=["admin/users"])
async def get_user_by_id(id: str, ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[GET-USER] Request started | user_id={ctx.user.id} | target_user={id}")
    current_role = ctx.user.role
    tenant_id = ctx.tenant_id

    if not is_valid_id(id):
        logger.warning(f"[GET-USER] Invalid ID | target_user={id}")
        return error(msg.USER_NOT_FOUND, 404, field="user")

    async with session_scope() as session:
        user = (await session.execute(_user_by_tenant_stmt(tenant_id, User.id == id))).scalar_one_or_none()
        if not user:
            logger.warning(f"[GET-USER] Not found | target_user={id} | tenant={tenant_id}")
            return error(msg.USER_NOT_FOUND, 404, field="user")

        if current_role == "customer-admin":
            if not _validate_customer_admin_permission(user, str(ctx.user.id)):
                logger.warning(f"[GET-USER] Permission denied | current_user={ctx.user.id} | target_user={id}")
                return error(msg.ONLY_VIEW_CREATED_USERS, 403)

        creator = None
        creator_id = created_by_user_id(user.createdBy)
        if creator_id:
            creator = await session.get(User, creator_id)

        response_data = user_admin_dict(user, creator)
        response_data["customer"] = None
        if user.tenantId:
            customer = (
                await session.execute(select(Customer).where(Customer.tenantId == user.tenantId))
            ).scalar_one_or_none()
            response_data["customer"] = customer_summary(customer)

    logger.info(f"[GET-USER] ✅ Retrieved | target_user={id} | role={user.role} | by={ctx.user.id}")
    return success(response_data, "User detail retrieved successfully")


@router.patch("/users/{id}/toggle-status", tags=["admin/users"])
async def toggle_user_status(id: str, ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[PATCH-USER-STATUS] Toggle request | user_id={ctx.user.id} | target_user={id}")
    current_role = ctx.user.role
    if current_role not in ("admin", "customer-admin"):
        logger.warning(f"[PATCH-USER-STATUS] Permission denied | user_id={ctx.user.id} | role={current_role}")
        return forbidden("Forbidden: only admin or customer can access.")

    tenant_id = ctx.tenant_id

    if str(ctx.user.id) == id:
        logger.warning(f"[PATCH-USER-STATUS] Cannot change own status | user_id={ctx.user.id}")
        return error(msg.cannot_change_own_status(current_role), 400)

    if not is_valid_id(id):
        logger.warning(f"[PATCH-USER-STATUS] Invalid ID | target_user={id}")
        return error(msg.USER_NOT_FOUND, 404, field="user")

    async with session_scope() as session:
        user = (await session.execute(_user_by_tenant_stmt(tenant_id, User.id == id))).scalar_one_or_none()
        if not user:
            logger.warning(f"[PATCH-USER-STATUS] Not found | target_user={id}")
            return error(msg.USER_NOT_FOUND, 404, field="user")

        if current_role == "customer-admin":
            if not _validate_customer_admin_permission(user, str(ctx.user.id)):
                logger.warning(f"[PATCH-USER-STATUS] Permission denied | current_user={ctx.user.id} | target_user={id}")
                return error(msg.ONLY_CHANGE_STATUS_CREATED_USERS, 403)

        new_status = not user.isActive
        user.isActive = new_status
        user.updatedAt = datetime.now(timezone.utc)
        result = {
            "id": str(user.id),
            "tenantId": str(user.tenantId) if user.tenantId else None,
            "isActive": new_status,
        }

    action = msg.USER_ACTIVATED if new_status else msg.USER_DEACTIVATED
    logger.info(f"[PATCH-USER-STATUS] ✅ {action.upper()} | target_user={id} | status={new_status} | by={ctx.user.id}")
    return success(result, action)


@router.delete("/users/{id}", tags=["admin/users"])
async def delete_user(id: str, ctx: Annotated[AuthenticatedUser, Depends(authenticate)]):
    logger.info(f"[DELETE-USER] Request started | user_id={ctx.user.id} | target_user={id}")
    current_role = ctx.user.role
    tenant_id = ctx.tenant_id

    if str(ctx.user.id) == id:
        logger.warning(f"[DELETE-USER] Cannot delete own account | user_id={ctx.user.id}")
        return error(msg.cannot_delete_own_account(current_role), 400)

    if not is_valid_id(id):
        logger.warning(f"[DELETE-USER] Invalid ID | target_user={id}")
        return error(msg.USER_NOT_FOUND, 404, field="user")

    async with session_scope() as session:
        user = (await session.execute(_user_by_tenant_stmt(tenant_id, User.id == id))).scalar_one_or_none()
        if not user:
            logger.warning(f"[DELETE-USER] Not found | target_user={id}")
            return error(msg.USER_NOT_FOUND, 404, field="user")

        if current_role == "customer-admin":
            if not _validate_customer_admin_permission(user, str(ctx.user.id)):
                logger.warning(f"[DELETE-USER] Permission denied | current_user={ctx.user.id} | target_user={id}")
                return error(msg.ONLY_DELETE_CREATED_USERS, 403)

        if user.role == "expert":
            await session.execute(delete(FrameworkAccess).where(FrameworkAccess.expertId == id))

        result = {
            "id": str(user.id),
            "tenantId": str(user.tenantId) if user.tenantId else None,
        }
        await session.delete(user)

    logger.info(f"[DELETE-USER] ✅ Deleted | target_user={id} | by={ctx.user.id}")
    return success(result, msg.USER_DELETED)
