#!/bin/bash
echo "Running database migrations..."
alembic upgrade head
echo "Running seed script..."
python seed.py
echo "Starting Celery worker in background..."
celery -A worker.celery_app worker --loglevel=info -P threads &
echo "Starting Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
