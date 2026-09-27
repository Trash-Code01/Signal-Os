#!/bin/bash
echo "=== Devacia Lead OS Backend Container Starting ==="
echo "Port: ${PORT:-8000}"

# Run Alembic migrations safely without halting container startup if schema is already up to date
if [ -f "alembic.ini" ]; then
    echo "Applying database migrations..."
    alembic upgrade head || echo "Notice: Alembic step finished with code $?, proceeding to app startup..."
fi

# Start Celery worker in background if Redis is configured
if [ -n "${REDIS_URL:-}" ]; then
    echo "Starting Celery worker in background..."
    celery -A worker.celery_app worker --loglevel=info -P threads -Q devacia_queue,celery &
else
    echo "REDIS_URL not configured; running in standalone mode."
fi

echo "Launching Uvicorn on 0.0.0.0:${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
