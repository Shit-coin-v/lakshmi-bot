#!/usr/bin/env bash
# Initialize development environment
# Usage: ./scripts/init_dev.sh

set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Initializing development environment ==="

# Check for .env file
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "Creating .env from .env.example..."
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        echo "Created .env - please update with your settings"
    else
        echo "WARNING: .env.example not found"
    fi
else
    echo ".env already exists"
fi

# Build containers
echo ""
echo "Building Docker containers..."
docker compose -f "$PROJECT_ROOT/docker-compose.yml" build

# Start database
echo ""
echo "Starting database..."
docker compose -f "$PROJECT_ROOT/docker-compose.yml" up -d db redis

# Wait for database to be healthy
echo ""
echo "Waiting for database to be ready..."
sleep 5

# Run migrations
echo ""
echo "Running migrations..."
docker compose -f "$PROJECT_ROOT/docker-compose.yml" run --rm app python backend/manage.py migrate --noinput

# Collect static
echo ""
echo "Collecting static files..."
docker compose -f "$PROJECT_ROOT/docker-compose.yml" run --rm app python backend/manage.py collectstatic --noinput

echo ""
echo "=== Development environment initialized ==="
echo ""
echo "Start all services with:"
echo "  docker compose up -d"
echo ""
echo "Or start specific services:"
echo "  docker compose up -d app celery_worker"
