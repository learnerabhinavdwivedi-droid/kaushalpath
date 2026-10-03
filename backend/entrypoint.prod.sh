#!/bin/sh
# Production container entrypoint (Phase 9 deployment).
#
# Applies migrations before serving so a freshly-started container is
# schema-correct against the shared volume, then hands off to uvicorn with
# process-management left to the orchestrator (no --reload, no dev flags).
set -e

echo "[entrypoint] applying migrations (alembic upgrade head)..."
alembic upgrade head

echo "[entrypoint] starting API on :${PORT:-8000}"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
