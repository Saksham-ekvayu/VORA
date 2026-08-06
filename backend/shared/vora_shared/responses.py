from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def success(
    data: Any = None,
    message: str = "Operation successful",
    status_code: int = 200,
) -> JSONResponse:
    body: dict[str, Any] = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    return JSONResponse(content=jsonable_encoder(body), status_code=status_code)


def paginated(
    data: Any,
    pagination: dict[str, Any],
    message: str = "Data retrieved successfully",
    status_code: int = 200,
) -> JSONResponse:
    body: dict[str, Any] = {
        "success": True,
        "message": message,
        "data": data,
        "pagination": pagination,
    }
    return JSONResponse(content=jsonable_encoder(body), status_code=status_code)


def error(
    message: str,
    status_code: int = 400,
    field: str | None = None,
    value: Any = None,
) -> JSONResponse:
    body: dict[str, Any] = {"success": False, "message": message}
    if field:
        body["field"] = field
    if value is not None:
        body["value"] = value
    return JSONResponse(content=jsonable_encoder(body), status_code=status_code)


def unauthorized(message: str = "Unauthorized access") -> JSONResponse:
    return error(message, 401)


def forbidden(message: str = "Access forbidden") -> JSONResponse:
    return error(message, 403)


def not_found(message: str = "Resource not found") -> JSONResponse:
    return error(message, 404)


def server_error(message: str = "Internal server error") -> JSONResponse:
    return error(message, 500)


def validation_error(
    errors: list | str,
    message: str = "Validation failed",
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=jsonable_encoder(
            {
                "success": False,
                "message": message,
                "errors": errors if isinstance(errors, list) else [{"msg": errors}],
            }
        ),
    )


def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Reformat FastAPI/Starlette HTTPExceptions into the {success, message} envelope.

    `exc.detail` may be a plain string, or a dict of {message, field, value} for
    handlers that need to surface an offending field (mirrors Node's
    ResponseFormatter.error(res, message, status, field, value)).
    """
    detail = exc.detail
    if isinstance(detail, dict):
        return error(
            detail.get("message", "Error"),
            exc.status_code,
            detail.get("field"),
            detail.get("value"),
        )

    if exc.status_code == 404 and detail in (None, "Not Found"):
        message = f"Route {request.method} {request.url.path} not found"
    else:
        message = str(detail) if detail is not None else "Error"

    return error(message, exc.status_code)


def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Reformat FastAPI's 422 validation errors into Node's express-validator style
    400 {success, message, errors: [{field, message, value}]} envelope."""
    errors = []
    for err in exc.errors():
        loc = [p for p in err.get("loc", []) if p not in ("body", "query", "path")]
        raw_msg = err.get("msg", "")
        clean_msg = raw_msg.replace("Value error, ", "")
        errors.append(
            {
                "field": ".".join(str(p) for p in loc) or None,
                "message": clean_msg,
                "value": err.get("input"),
            }
        )
    main_message = errors[0]["message"] if errors else "Validation failed"
    return validation_error(errors, message=main_message)
