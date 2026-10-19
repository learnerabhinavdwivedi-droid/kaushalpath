#!/usr/bin/env bash
# Render startup script for KaushalPath backend
set -e

# In case the database was not seeded or is on a fresh persistent disk
if [ ! -f "backend/kaushalpath.db" ]; then
    echo "==> [Render Start] Database not found. Running migrations and seed pipeline..."
    cd backend && alembic upgrade head && cd ..
    python scripts/seed_all.py
fi

echo "==> [Render Start] Starting Uvicorn API server on port ${PORT:-8000}..."
exec uvicorn app.main:app \
    --app-dir backend \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
