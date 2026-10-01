#!/bin/bash
set -euo pipefail

echo "=== Devacia Lead OS Backend Starting ==="
PORT="${PORT:-8000}"

# Uvicorn's startup hooks initialize/upgrade the schema before accepting traffic.
# Do not run Alembic concurrently: both paths alter the same auth/tenant tables,
# which can race or deadlock and prevent the API from becoming ready.
# Run any operator-requested Alembic upgrade separately, with writers stopped.

# Start Celery worker in background if Redis is configured
if [ -n "${REDIS_URL:-}" ]; then
    echo "Starting Celery worker in background..."
    celery -A worker.celery_app worker --loglevel=info -P threads -Q devacia_queue,celery &
fi

echo "Launching Uvicorn on 0.0.0.0:${PORT}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
