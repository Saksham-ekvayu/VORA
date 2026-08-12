# VORA Platform — Architecture Notes

## Overview
FastAPI microservices for compliance / GRC platform (VORA). Migrated from Node.js → Python, preserving the Node-style `{success, message, data}` response envelope.

## Topology
- **API Gateway** (`gateway/main.py`) — FastAPI reverse proxy; maps `/api/*` prefixes → localhost services on ports 7001-7009
- **Services** (each is its own FastAPI app under `services/<name>-service/app/`):
  - authentication (7001), profile (7002), dashboard (7003)
  - framework-category (7004), framework (7005), deployment-framework (7006)
  - extract-controls (7007), compliance-agent (7008), ai-analysis (7009)
- **shared** (`shared/vora_shared/`) — installed as editable package `vora-shared`; imported as `from vora_shared import …`

## Cross-Cutting Infrastructure
- **DB**: Postgres via SQLAlchemy 2.x async (`asyncpg`); schema managed by Alembic (`shared/alembic/`)
- **IDs**: 24-char hex (`vora_shared.ids.new_id`) — mimics Mongo ObjectId
- **Auth**: JWT (HS256) with per-tenant secret (`vora_shared.auth`); `tokenVersion` field on User for forced logout
- **Tenant model**: `X-TENANT-ID` header; admin/expert bypass, others require it (`vora_shared.security.get_context`)
- **Response envelope**: `{success, message, data?, pagination?, field?, value?, errors?}` (`vora_shared.responses`)
- **Validation**: Pydantic `field_validator`s in `app/schemas/` using helpers from `vora_shared.validators`
- **Messages**: All user-facing strings live in `vora_shared.messages` (flat `*_SUCCESS` constants + `MESSAGES` / `BUSINESS_MESSAGES` / `VALIDATION_MESSAGES` dicts)
- **Pagination**: `vora_shared.query_builder` — `paginate_stmt`, `paginate_with_search`, `apply_sort`, `apply_search_filter`
- **Email**: `vora_shared.email.send_email` + templates in `shared/vora_shared/templates/`
- **File uploads**: `vora_shared.file_storage` writes to `shared/uploads/{file,avatar}/…`
- **Settings**: Pydantic Settings via `vora_shared.config.get_settings()` (lru_cached, reads `shared/vora_shared/.env` + `.env`)

## Service Skeleton (every service)
```
services/<name>-service/
  app/
    __init__.py
    main.py            # create_vora_app + lifespan + connect_db + include_router
    routers/           # APIRouter per resource
      <resource>.py
    helpers/           # (optional) business-logic helpers extracted from routers
      helpers.py
    schemas/           # Pydantic request/response models (where needed)
    validations/       # (optional) manual validators mimicking express-validator
```
Router pattern: `Annotated[AuthenticatedUser, Depends(authenticate)]` → body validation via `field_validator` or custom `FieldError` → `async with session_scope()` → `vora_shared.responses.success()` / `paginated()` / `error()`.

## Key Conventions (from docs/Rules.md)
1. Always reuse existing utilities — never duplicate (e.g., `PasswordHasher.hash`, `paginate_stmt`)
2. No hardcoded messages — use `Messages.*` or `MESSAGES["…"]`
3. Common API response shape — `success()`, `paginated()`, `error()`
4. Functions < 30–40 lines, cognitive complexity ≤ 15
5. Early returns over nesting
6. Centralized constants, no magic numbers
7. Imports ordered: stdlib → third-party → project
8. No wildcard imports; remove unused
9. Helpers live in `helpers/helpers.py`, not routers
10. Config via `settings.X` — never `os.getenv` inside random files
11. Log + re-raise on unexpected errors (never bare `except Exception: pass`)
12. No TODOs, no commented-out code

## Frontend
React + Vite + Tailwind, organized under `frontend/src/{components, pages, routes, services, hooks, context, layout, lib, utils, data}`. See `frontend/docs/Api_Report.md` for the API contract.

## Scripts
- `scripts/batch/*.bat` (Windows) and `scripts/shell/*.sh` (Unix) — create venvs, install deps, run all services, format, lint
- `scripts/create_venvs.py` / `remove_venvs.py` — cross-platform Python equivalents