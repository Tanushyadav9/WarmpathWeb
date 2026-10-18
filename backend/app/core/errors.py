"""
backend/app/core/errors.py - Unified error representation and exception handlers.
Contract format: {"error": {"code": "...", "message": "...", "details": {...}}}
"""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class PortNotReady(AppError):
    def __init__(self, port_name: str):
        super().__init__(
            code="port_not_ready",
            message=f"Service port '{port_name}' is not ready.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"port": port_name},
        )


class ModuleNotImplemented(AppError):
    def __init__(self, endpoint: str):
        super().__init__(
            code="module_not_implemented",
            message=f"Endpoint '{endpoint}' is scaffolded and pending module implementation.",
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            details={"endpoint": endpoint},
        )


import logging
import uuid
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("warmpath.errors")


def error_response(code: str, message: str, status_code: int, details: Optional[Dict[str, Any]] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


def _sanitize_pydantic_error_item(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize_pydantic_error_item(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_pydantic_error_item(v) for v in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    sanitized_errors = [_sanitize_pydantic_error_item(err) for err in exc.errors()]
    return error_response(
        code="validation_error",
        message="Input validation failed. Please check the submitted fields.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"errors": sanitized_errors},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return error_response(
        code=f"http_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
        details={},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches all unexpected exceptions. Logs full traceback internally
    with a correlation request ID, and returns a safe sanitized response
    that NEVER exposes internal stack traces or database errors to users.
    """
    request_id = request.headers.get("X-Request-ID") or getattr(request.state, "request_id", None) or str(uuid.uuid4())
    logger.error("Unhandled exception for request %s: %s", request_id, exc, exc_info=True)

    return error_response(
        code="internal_server_error",
        message="An unexpected error occurred. Please contact support quoting your request ID.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details={"request_id": str(request_id)},
    )

