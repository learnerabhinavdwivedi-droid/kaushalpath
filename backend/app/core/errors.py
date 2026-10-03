"""Centralised error handling (Phase 9 reliability + security).

Two guarantees the earlier per-route `except Exception: HTTPException(str(e))`
pattern broke:
1. Never leak an internal exception string to the client (info disclosure);
   log the real trace server-side instead, tagged with the request id.
2. One consistent error envelope so the frontend and demo can rely on it.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, request_id_var

logger = get_logger("kaushalpath.errors")


def _envelope(status_code: int, message: str, details: object | None = None) -> JSONResponse:
    body: dict[str, object] = {
        "error": {
            "message": message,
            "status_code": status_code,
            "request_id": request_id_var.get(),
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Field names + constraint types are safe to expose; never the raw values.
        details = [
            {"field": ".".join(str(p) for p in err["loc"][1:]), "type": err["type"]}
            for err in exc.errors()
        ]
        return _envelope(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid request", details
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Full detail to logs only; the client gets a generic, traceable message.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _envelope(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error"
        )
