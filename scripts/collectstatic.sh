#!/usr/bin/env bash
# Collect static files for production
# Usage: ./scripts/collectstatic.sh
# Or via docker: docker compose run --rm app ./scripts/collectstatic.sh

set -euo pipefail

cd "$(dirname "$0")/../backend"

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Static files collected successfully."
