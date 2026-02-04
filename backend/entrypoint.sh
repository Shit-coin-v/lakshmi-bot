#!/usr/bin/env bash
# Simplified entrypoint - migrations and collectstatic are run separately
# Use: make migrate && make collectstatic before starting

set -euo pipefail

if [ $# -gt 0 ]; then
  exec "$@"
fi

GUNICORN_WORKERS=${GUNICORN_WORKERS:-3}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-60}

exec gunicorn \
  --bind 0.0.0.0:8000 \
  --workers "$GUNICORN_WORKERS" \
  --timeout "$GUNICORN_TIMEOUT" \
  --access-logfile - \
  --error-logfile - \
  wsgi:application
