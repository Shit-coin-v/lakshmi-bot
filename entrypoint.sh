#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'

GUNICORN_WORKERS=${GUNICORN_WORKERS:-3}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-60}
ENABLE_TELEGRAM_BOT=${ENABLE_TELEGRAM_BOT:-true}

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

bot_pid=""
if [[ "${ENABLE_TELEGRAM_BOT,,}" == "true" ]]; then
  echo "Starting Telegram bot..."
  pushd src >/dev/null
  python run.py &
  bot_pid=$!
  popd >/dev/null
  trap '[[ -n "$bot_pid" ]] && kill -TERM $bot_pid 2>/dev/null || true; kill -TERM $gunicorn_pid 2>/dev/null || true' EXIT
fi

if [[ -n "$bot_pid" ]]; then
  wait -n "$gunicorn_pid" "$bot_pid"
else
  wait "$gunicorn_pid"
fi
