#!/usr/bin/env bash
# Render build script for the FastAPI backend.
# Runs on every deploy before the start command.
set -e

echo "==> Installing dependencies with pip..."
pip install uv
uv sync --no-dev

echo "==> Running database migrations..."
uv run alembic upgrade head

echo "==> Seeding initial data (skipped if already seeded)..."
uv run python -m src.migration.seed || echo "Seed skipped (data may already exist)"

echo "==> Build complete."
