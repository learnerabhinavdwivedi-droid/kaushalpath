#!/usr/bin/env bash
# Render build script for KaushalPath backend
set -o errexit

echo "==> [Render Build] Upgrading pip..."
python -m pip install --upgrade pip

echo "==> [Render Build] Installing backend dependencies..."
pip install -r backend/requirements.txt

echo "==> [Render Build] Running Alembic database migrations..."
cd backend
alembic upgrade head
cd ..

echo "==> [Render Build] Seeding database and building retrieval index..."
python scripts/seed_all.py

echo "==> [Render Build] Build completed successfully!"
