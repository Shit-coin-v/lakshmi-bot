#!/usr/bin/env bash
# Apply database migrations
# Usage: ./scripts/migrate.sh
# Or via docker: docker compose run --rm app ./scripts/migrate.sh

set -euo pipefail

cd "$(dirname "$0")/../backend"

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Migrations completed successfully."
