"""FastAPI application entrypoint (Phase 0 skeleton only).

Adds: request-id middleware, CORS, /health and /meta/model-version.
No business logic, DB or ML here yet (PHASE_0.md "DO NOT").
"""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.api.routes import admin as admin_routes
from app.api.routes import assessment as assessment_routes
from app.api.routes import auth as auth_routes
from app.api.routes import counsellor as counsellor_routes
from app.api.routes import feedback as feedback_routes
from app.api.routes import outcomes as outcomes_routes
from app.api.routes import conversations as conversations_routes
from app.api.routes import recommend as recommend_routes
from app.api.routes import roadmap as roadmap_routes
from app.api.routes import rooms as rooms_routes
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger, request_id_var
from app.core.middleware import SecurityHeadersMiddleware
from app.core.rate_limit import limiter
from app.db.session import engine

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("kaushalpath")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "AI career counselling + family decision support "
        "for vocational education (SIH 2026, PSID 26241)."
    ),
    # Swagger/OpenAPI is a dev tool; hidden in prod unless explicitly re-enabled.
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    # Explicit verbs/headers rather than '*' — tighter when credentials are on.
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(SecurityHeadersMiddleware)


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

app.include_router(auth_routes.router)
app.include_router(assessment_routes.router)
app.include_router(recommend_routes.router)
app.include_router(rooms_routes.router)
app.include_router(roadmap_routes.router)
app.include_router(counsellor_routes.router)
app.include_router(feedback_routes.router)
app.include_router(outcomes_routes.router)
app.include_router(conversations_routes.router)
app.include_router(admin_routes.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness probe. Acceptance gate: returns {"status":"ok"}."""
    return {"status": "ok", "env": settings.app_env}


@app.get("/health/ready", tags=["health"])
async def readiness() -> JSONResponse:
    """Readiness probe: confirms the DB is reachable before serving traffic.

    Returns 503 (not a bare exception) when the dependency is down so an
    orchestrator can hold the pod out of rotation.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - depends on infra failure
        logger.exception("Readiness check failed: DB unreachable")
        return JSONResponse(status_code=503, content={"status": "unavailable", "db": "down"})
    return JSONResponse(content={"status": "ready", "db": "up"})


@app.get("/meta/model-version", tags=["health"])
async def model_version() -> dict[str, str]:
    return {"model_version": settings.model_version}
