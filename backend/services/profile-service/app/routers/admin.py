import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm.attributes import flag_modified

from vora_shared.auth import AuthenticatedUser, authenticate
from vora_shared.database import session_scope
from vora_shared.email import load_template, send_email
from vora_shared.ids import is_valid_id
from vora_shared.models.customer import AddressBlock, Customer, CustomerAddress, CustomerCreatedBy
from vora_shared.models.user import User, UserAddress, UserCreatedBy
from vora_shared.query_builder import apply_search_filter, apply_sort, paginate_stmt
from vora_shared.responses import error, forbidden, paginated, success
from vora_shared.security import hash_password

from vora_shared import messages as msg
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

router = APIRouter(tags=["admin"])
logger = logging.getLogger(__name__)

import vora_shared

TEMPLATES_DIR = Path(vora_shared.__file__).resolve().parent / "templates"

TENANT_SCOPED_ROLES = {"customer-admin", "user", "auditor", "internal-expert"}
RESTRICTED_ROLES_FOR_CUSTOMER_ADMIN = {"admin", "customer-admin", "expert"}


def _address_from_blocks(permanent, temporary) -> dict:
    return UserAddress(
        permanentAddress=AddressBlock(
            **(permanent.model_dump(exclude_none=True) if permanent else {})
        ),
        temporaryAddress=AddressBlock(
            **(temporary.model_dump(exclude_none=True) if temporary else {})
        ),
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


# ------------------------------------------------------------------------
# Customer management
# ------------------------------------------------------------------------


@router.post("/customers")
async def create_customer(body: CreateCustomerRequest, ctx: AuthenticatedUser = Depends(authenticate)):
    async with session_scope() as session:
        if (
            await session.execute(select(Customer).where(Customer.email == body.email))
        ).scalar_one_or_none():
            return error("Email already exists", 400, field="email")
        if body.phone and (
            await session.execute(select(Customer).where(Customer.phone == body.phone))
        ).scalar_one_or_none():
            return error("Customer with this phone number already exists", 400, field="phone")

        tenant_id = f"tenant_{secrets.token_hex(8)}"
        while (
            await session.execute(select(Customer).where(Customer.tenantId == tenant_id))
        ).scalar_one_or_none():
            tenant_id = f"tenant_{secrets.token_hex(8)}"

        address = CustomerAddress(
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
        )

        now = datetime.now(timezone.utc)
        new_customer = Customer(
            tenantId=tenant_id,
            name=body.name,
            email=body.email,
            phone=body.phone,
            secondaryPhone=body.secondaryPhone,
            avatar=body.avatar,
            address=address.model_dump(mode="json"),
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

    return success(result, "Customer created successfully")


@router.get("/customers")
async def get_all_customers(
    page: int = Query(1),
    limit: int = Query(10),
    search: str | None = Query(None),
    isActive: str | None = Query(None),
    sortBy: str | None = Query(None),
    sortOrder: str | None = Query(None),
    ctx: AuthenticatedUser = Depends(authenticate),
):
    allowed_sort_fields = ["name", "email", "tenantId", "createdAt", "updatedAt"]
    allowed_search_fields = ["name", "email", "tenantId", "phone"]

    async with session_scope() as session:
        stmt = select(Customer)
        if isActive is not None:
            stmt = stmt.where(Customer.isActive.is_(isActive.lower() == "true"))
        stmt = apply_search_filter(Customer, search, allowed_search_fields, stmt)
        stmt = apply_sort(Customer, stmt, sortBy, sortOrder, allowed_sort_fields)
        data, pagination = await paginate_stmt(session, stmt, page=page, limit=limit)

        creators = await _batch_fetch_creators(session, data)
        result = [
            customer_dict(c, creators.get(created_by_user_id(c.createdBy))) for c in data
        ]

    return paginated(result, pagination, "Customers retrieved successfully")


@router.get("/customers/{id}")
async def get_customer_by_id(
    id: str,
    page: int = Query(1),
    limit: int = Query(10),
    search: str | None = Query(None),
    isActive: str | None = Query(None),
    sortBy: str | None = Query(None),
    sortOrder: str | None = Query(None),
    ctx: AuthenticatedUser = Depends(authenticate),
):
    if not is_valid_id(id):
        return error("Customer not found", 404)

    allowed_sort_fields = ["name", "email", "createdAt", "updatedAt"]
    allowed_search_fields = ["name", "email"]

    async with session_scope() as session:
        customer = await session.get(Customer, id)
        if not customer:
            return error("Customer not found", 404)

        creator = None
        creator_id = created_by_user_id(customer.createdBy)
        if creator_id:
            creator = await session.get(User, creator_id)

        users_stmt = select(User).where(User.tenantId == customer.tenantId)
        if isActive is not None:
            users_stmt = users_stmt.where(User.isActive.is_(isActive.lower() == "true"))
        users_stmt = apply_search_filter(User, search, allowed_search_fields, users_stmt)
        users_stmt = apply_sort(User, users_stmt, sortBy, sortOrder, allowed_sort_fields)
        users_data, users_pagination = await paginate_stmt(
            session, users_stmt, page=page, limit=limit
        )

        customer_details = customer_dict(customer, creator)
        customer_details["users"] = {
            "data": [sanitize_user(u) for u in users_data],
            "pagination": users_pagination,
        }

    return success(customer_details, "Customer details retrieved successfully")


@router.patch("/customers/{id}")
async def update_customer(
    id: str,
    body: UpdateCustomerRequest,
    ctx: AuthenticatedUser = Depends(authenticate),
):
    if not is_valid_id(id):
        return error("Customer not found", 404)

    async with session_scope() as session:
        customer = await session.get(Customer, id)
        if not customer:
            return error("Customer not found", 404)

        if body.email and body.email != customer.email:
            existing = (
                await session.execute(select(Customer).where(Customer.email == body.email))
            ).scalar_one_or_none()
            if existing and str(existing.id) != id:
                return error("Email already exists", 400, field="email")

        if body.phone and body.phone != customer.phone:
            existing = (
                await session.execute(select(Customer).where(Customer.phone == body.phone))
            ).scalar_one_or_none()
            if existing and str(existing.id) != id:
                return error(
                    "Customer with this phone number already exists", 400, field="phone"
                )

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

        creator = None
        creator_id = created_by_user_id(customer.createdBy)
        if creator_id:
            creator = await session.get(User, creator_id)
        result = customer_dict(customer, creator)

    return success(result, "Customer updated successfully")


@router.patch("/customers/{id}/toggle-status")
async def toggle_customer_status(id: str, ctx: AuthenticatedUser = Depends(authenticate)):
    if not is_valid_id(id):
        return error("Customer not found", 404)

    async with session_scope() as session:
        customer = await session.get(Customer, id)
        if not customer:
            return error("Customer not found", 404)

        customer.isActive = not customer.isActive
        customer.updatedAt = datetime.now(timezone.utc)

        creator = None
        creator_id = created_by_user_id(customer.createdBy)
        if creator_id:
            creator = await session.get(User, creator_id)
        result = customer_dict(customer, creator)
        action = "activated" if customer.isActive else "deactivated"

    return success(result, f"Customer {action} successfully")


@router.delete("/customers/{id}")
async def delete_customer(id: str, ctx: AuthenticatedUser = Depends(authenticate)):
    if not is_valid_id(id):
        return error("Customer not found", 404)

    async with session_scope() as session:
        customer = await session.get(Customer, id)
        if not customer:
            return error("Customer not found", 404)
        await session.delete(customer)

    return success(None, "Customer deleted successfully")


# ------------------------------------------------------------------------
# Admin user management
# ------------------------------------------------------------------------


@router.post("/create")
async def create_user(body: CreateUserRequest, ctx: AuthenticatedUser = Depends(authenticate)):
    current_role = ctx.user.role
    creator_tenant_id = ctx.tenant_id

    if current_role == "customer-admin" and body.role in RESTRICTED_ROLES_FOR_CUSTOMER_ADMIN:
        return error(
            msg.role_restriction(
                current_role, "custom roles (excluding admin, customer-admin, expert)"
            ),
            403,
        )

    if current_role == "admin" and body.role in TENANT_SCOPED_ROLES and not body.tenantId:
        return error(f"Tenant ID is required for {body.role} role", 400, field="tenantId")

    if current_role == "admin":
        new_tenant_id = body.tenantId if body.role in TENANT_SCOPED_ROLES else None
    else:
        new_tenant_id = creator_tenant_id

    async with session_scope() as session:
        email_stmt = _user_by_tenant_stmt(new_tenant_id, User.email == body.email)
        if (await session.execute(email_stmt)).scalar_one_or_none():
            return error(msg.EMAIL_ALREADY_EXISTS, 400, field="email")

        if body.phone:
            phone_stmt = _user_by_tenant_stmt(new_tenant_id, User.phone == body.phone)
            if (await session.execute(phone_stmt)).scalar_one_or_none():
                return error(
                    "User with this phone number already exists", 400, field="phone"
                )

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
            createdBy=UserCreatedBy(
                type=created_by_type_val, userId=ctx.user.id
            ).model_dump(mode="json"),
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
        logger.error("Failed to send temporary password email to %s", user_email)
        return success(
            {"id": user_id, "tenantId": tenant},
            msg.USER_CREATED_EMAIL_FAILED,
        )

    return success({"id": user_id, "tenantId": tenant}, msg.USER_CREATED)


def _render_temp_password_email(name: str, email: str, temp_password: str) -> str:
    return load_template(
        TEMPLATES_DIR,
        "temp-password",
        {"userName": name, "userEmail": email, "tempPassword": temp_password},
    )


@router.patch("/{id}")
async def update_user(id: str, body: UpdateUserRequest, ctx: AuthenticatedUser = Depends(authenticate)):
    current_user = ctx.user
    current_role = current_user.role
    tenant_id = ctx.tenant_id

    if not is_valid_id(id):
        return error("User not found", 404, field="user")

    async with session_scope() as session:
        user = (
            await session.execute(_user_by_tenant_stmt(tenant_id, User.id == id))
        ).scalar_one_or_none()
        if not user:
            return error("User not found", 404, field="user")

        current_id_str = str(current_user.id)
        target_id_str = str(user.id)
        new_role = body.role

        if current_id_str == target_id_str and new_role and new_role != current_user.role:
            return error(msg.cannot_change_own_role(current_user.role), 400)

        if current_role == "customer-admin":
            if not (
                created_by_type(user.createdBy) == "customer-admin"
                and created_by_user_id(user.createdBy) == current_id_str
            ):
                return error(msg.ONLY_UPDATE_CREATED_USERS, 403)

            if new_role and new_role != user.role and new_role in RESTRICTED_ROLES_FOR_CUSTOMER_ADMIN:
                return error(
                    msg.role_assignment_restriction(
                        current_role, "custom roles (excluding admin, customer-admin, expert)"
                    ),
                    403,
                )

        if current_role == "admin":
            if (
                user.role == "admin"
                and new_role
                and new_role != "admin"
                and current_id_str != target_id_str
            ):
                return error(msg.CANNOT_CHANGE_ADMIN_ROLE, 400)

        if body.phone and body.phone != user.phone:
            existing_phone = (
                await session.execute(
                    _user_by_tenant_stmt(tenant_id, User.phone == body.phone)
                )
            ).scalar_one_or_none()
            if existing_phone and str(existing_phone.id) != id:
                return error(
                    "User with this phone number already exists", 400, field="phone"
                )

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
            user.address = merge_address(
                user.address, body.permanentAddress, body.temporaryAddress
            )
            flag_modified(user, "address")
        user.updatedAt = datetime.now(timezone.utc)
        result = {
            "id": str(user.id),
            "tenantId": str(user.tenantId) if user.tenantId else None,
        }

    return success(result, "User updated successfully")


@router.get("/all-users")
async def get_all_users(
    page: int = Query(1),
    limit: int = Query(10),
    search: str | None = Query(None),
    isActive: str | None = Query(None),
    role: str | None = Query(None),
    sortBy: str | None = Query(None),
    sortOrder: str | None = Query(None),
    ctx: AuthenticatedUser = Depends(authenticate),
):
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
        if isActive is not None:
            stmt = stmt.where(User.isActive.is_(isActive.lower() == "true"))

        if search:
            creator_stmt = select(User.id).where(
                or_(
                    User.name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )
            if current_role != "admin":
                creator_stmt = creator_stmt.where(User.tenantId == tenant_id)
            creator_ids = [
                row[0] for row in (await session.execute(creator_stmt)).all()
            ]

            search_conditions = [
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.role.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%"),
            ]
            if creator_ids:
                search_conditions.append(
                    User.createdBy["userId"].astext.in_(creator_ids)
                )
            stmt = stmt.where(or_(*search_conditions))

        stmt = apply_sort(User, stmt, sortBy, sortOrder, allowed_sort_fields)
        data, pagination = await paginate_stmt(session, stmt, page=page, limit=limit)

        creators = await _batch_fetch_creators(session, data)
        users_list = [
            user_admin_dict(u, creators.get(created_by_user_id(u.createdBy))) for u in data
        ]

    message = msg.USER_LIST_RETRIEVED
    if not users_list:
        message = (
            msg.NO_USERS_MATCH_CRITERIA
            if (search or isActive or role)
            else msg.NO_USERS_AVAILABLE
        )

    return paginated(users_list, pagination, message)


@router.get("/{id}")
async def get_user_by_id(id: str, ctx: AuthenticatedUser = Depends(authenticate)):
    current_role = ctx.user.role
    tenant_id = ctx.tenant_id

    if not is_valid_id(id):
        return error("User not found", 404, field="user")

    async with session_scope() as session:
        user = (
            await session.execute(_user_by_tenant_stmt(tenant_id, User.id == id))
        ).scalar_one_or_none()
        if not user:
            return error("User not found", 404, field="user")

        if current_role == "customer-admin":
            if not (
                created_by_type(user.createdBy) == "customer-admin"
                and created_by_user_id(user.createdBy) == str(ctx.user.id)
            ):
                return error(msg.ONLY_VIEW_CREATED_USERS, 403)

        creator = None
        creator_id = created_by_user_id(user.createdBy)
        if creator_id:
            creator = await session.get(User, creator_id)

        response_data = user_admin_dict(user, creator)
        response_data["customer"] = None
        if user.tenantId:
            customer = (
                await session.execute(
                    select(Customer).where(Customer.tenantId == user.tenantId)
                )
            ).scalar_one_or_none()
            response_data["customer"] = customer_summary(customer)

    return success(response_data, "User detail retrieved successfully")


@router.patch("/{id}/toggle-status")
async def toggle_user_status(id: str, ctx: AuthenticatedUser = Depends(authenticate)):
    current_role = ctx.user.role
    if current_role not in ("admin", "customer-admin"):
        return forbidden("Forbidden: only admin or customer can access.")

    tenant_id = ctx.tenant_id

    if str(ctx.user.id) == id:
        return error(msg.cannot_change_own_status(current_role), 400)

    if not is_valid_id(id):
        return error("User not found", 404, field="user")

    async with session_scope() as session:
        user = (
            await session.execute(_user_by_tenant_stmt(tenant_id, User.id == id))
        ).scalar_one_or_none()
        if not user:
            return error("User not found", 404, field="user")

        if current_role == "customer-admin":
            if not (
                created_by_type(user.createdBy) == "customer-admin"
                and created_by_user_id(user.createdBy) == str(ctx.user.id)
            ):
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
    return success(result, action)


@router.delete("/{id}")
async def delete_user(id: str, ctx: AuthenticatedUser = Depends(authenticate)):
    current_role = ctx.user.role
    tenant_id = ctx.tenant_id

    if str(ctx.user.id) == id:
        return error(msg.cannot_delete_own_account(current_role), 400)

    if not is_valid_id(id):
        return error("User not found", 404, field="user")

    async with session_scope() as session:
        user = (
            await session.execute(_user_by_tenant_stmt(tenant_id, User.id == id))
        ).scalar_one_or_none()
        if not user:
            return error("User not found", 404, field="user")

        if current_role == "customer-admin":
            if not (
                created_by_type(user.createdBy) == "customer-admin"
                and created_by_user_id(user.createdBy) == str(ctx.user.id)
            ):
                return error(msg.ONLY_DELETE_CREATED_USERS, 403)

        result = {
            "id": str(user.id),
            "tenantId": str(user.tenantId) if user.tenantId else None,
        }
        await session.delete(user)

    return success(result, msg.USER_DELETED)
