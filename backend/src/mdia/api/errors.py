"""Domain errors to HTTP, in one place. Routes never build an error response.

Every handler answers with :class:`ErrorOut`, so a client has one shape to parse
whatever went wrong.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from mdia.core.errors import MdiaError, NotFoundError, ValidationError
from mdia.schemas.errors import ErrorCode, ErrorOut, FieldErrorOut

if TYPE_CHECKING:
    from collections.abc import Sequence

log = structlog.get_logger(__name__)

# What a client is told when the cause is ours and the detail is not theirs to read.
SERVER_MESSAGE = "Something went wrong on our side. Try again in a moment."

# Attached to every route so the generated client knows the shape of a failure.
RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"model": ErrorOut, "description": "Not found"},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorOut, "description": "Invalid input"},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorOut, "description": "Server error"},
}


def register(app: FastAPI) -> None:
    """Install the handlers. Order matters: the most specific error class first."""

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return _response(status.HTTP_404_NOT_FOUND, "not_found", str(exc))

    @app.exception_handler(ValidationError)
    async def _validation(_: Request, exc: ValidationError) -> JSONResponse:
        return _response(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_input", str(exc))

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_input",
            "Some of what was sent could not be read.",
            fields=_fields(exc.errors()),
        )

    @app.exception_handler(MdiaError)
    async def _domain(_: Request, exc: MdiaError) -> JSONResponse:
        log.error("domain.error", error=str(exc), kind=type(exc).__name__)
        return _response(status.HTTP_500_INTERNAL_SERVER_ERROR, "server_error", SERVER_MESSAGE)

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled.error", kind=type(exc).__name__)
        return _response(status.HTTP_500_INTERNAL_SERVER_ERROR, "server_error", SERVER_MESSAGE)


def _response(
    status_code: int,
    code: ErrorCode,
    message: str,
    *,
    fields: list[FieldErrorOut] | None = None,
) -> JSONResponse:
    body = ErrorOut(code=code, message=message, fields=fields or [])
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _fields(errors: Sequence[Any]) -> list[FieldErrorOut]:
    """Pydantic's location tuples as the field names a form would recognise."""
    found: dict[str, str] = {}
    for error in errors:
        location = [str(part) for part in error.get("loc", ()) if part not in {"body", "query"}]
        name = location[-1] if location else "request"
        message = str(error.get("msg", "")).removeprefix("Value error, ")
        found.setdefault(name, message)
    return [FieldErrorOut(field=field, message=message) for field, message in found.items()]
