#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'

GUNICORN_WORKERS=${GUNICORN_WORKERS:-3}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-60}
ENABLE_TELEGRAM_BOT=${ENABLE_TELEGRAM_BOT:-false}

echo "Applying database migrations..."
python backend/manage.py migrate --noinput

echo "Collecting static files..."
python backend/manage.py collectstatic --noinput

gunicorn \
  --bind 0.0.0.0:8000 \
  --workers "$GUNICORN_WORKERS" \
  --timeout "$GUNICORN_TIMEOUT" \
  --access-logfile - \
  --error-logfile - \
  backend.wsgi:application &
gunicorn_pid=$!

trap 'kill -TERM $gunicorn_pid 2>/dev/null || true' EXIT

wait "$gunicorn_pid"
