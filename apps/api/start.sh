#!/bin/bash
set -euo pipefail

echo "=== Devacia Lead OS Backend Starting ==="
echo "Release: ${RENDER_GIT_COMMIT:-local} (starting API and campaign worker together)"
PORT="${PORT:-8000}"

# Uvicorn's startup hooks initialize/upgrade the schema before accepting traffic.
# Do not run Alembic concurrently: both paths alter the same auth/tenant tables,
# which can race or deadlock and prevent the API from becoming ready.
# Run any operator-requested Alembic upgrade separately, with writers stopped.

if [ "${ENVIRONMENT:-}" = "production" ] && [ -z "${REDIS_URL:-}" ]; then
    echo "ERROR: REDIS_URL is required for production campaign processing."
    exit 1
fi

if [ -z "${REDIS_URL:-}" ]; then
    exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
fi

# Supervise both processes. A healthy API must not conceal a dead worker.
celery -A worker.celery_app worker --loglevel=info -P threads --concurrency=2 -Q devacia_queue,celery &
worker_pid=$!
uvicorn main:app --host 0.0.0.0 --port "${PORT}" &
api_pid=$!
cleanup() {
    kill "$worker_pid" "$api_pid" 2>/dev/null || true
    wait "$worker_pid" "$api_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 143' TERM INT
# Check both children, including one that exits before supervision begins.
while kill -0 "$worker_pid" 2>/dev/null && kill -0 "$api_pid" 2>/dev/null; do
    sleep 1
done
echo "API or campaign worker exited; restarting the service."
exit 1
