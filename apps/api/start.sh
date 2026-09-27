#!/bin/bash
echo "=== Devacia Lead OS Backend Starting ==="
PORT="${PORT:-8000}"

# Run alembic in background so port binding is instant and unblocked
if [ -f "alembic.ini" ]; then
    (alembic upgrade head || echo "Alembic background migration completed or skipped") &
fi

# Start Celery worker in background if Redis is configured
if [ -n "${REDIS_URL:-}" ]; then
    echo "Starting Celery worker in background..."
    celery -A worker.celery_app worker --loglevel=info -P threads -Q devacia_queue,celery &
fi

echo "Launching Uvicorn on 0.0.0.0:${PORT}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
