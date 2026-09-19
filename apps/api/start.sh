#!/bin/bash
set -euo pipefail
echo "Running database migrations..."
alembic upgrade head
echo "Starting Celery worker in background..."
celery -A worker.celery_app worker --loglevel=info -P threads -Q devacia_queue,celery &
echo "Starting Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
