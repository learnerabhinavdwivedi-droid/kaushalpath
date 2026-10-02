"""FastAPI application entrypoint (Phase 0 skeleton only).

Adds: request-id middleware, CORS, /health and /meta/model-version.
No business logic, DB or ML here yet (PHASE_0.md "DO NOT").
"""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger, request_id_var

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("kaushalpath")

app = FastAPI(
    title=settings.app_name,
    version="0.0.0-phase0",
    description=(
        "AI career counselling + family decision support "
        "for vocational education (SIH 2026, PSID 26241)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a request id (honour incoming X-Request-ID), bind it to logs."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        logger.info(
            "%s %s -> %s in %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - start) * 1000,
        )
        return response


app.add_middleware(RequestIdMiddleware)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness probe. Acceptance gate: returns {"status":"ok"}."""
    return {"status": "ok", "env": settings.app_env}


@app.get("/meta/model-version", tags=["health"])
async def model_version() -> dict[str, str]:
    return {"model_version": settings.model_version}
