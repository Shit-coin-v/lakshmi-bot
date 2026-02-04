.PHONY: build up down logs shell migrate collectstatic setup test backup help init

# Default target
help:
	@echo "Available commands:"
	@echo "  make build         - Build all Docker containers"
	@echo "  make up            - Start all services"
	@echo "  make down          - Stop all services"
	@echo "  make logs          - Follow logs from all services"
	@echo "  make shell         - Open bash shell in app container"
	@echo "  make setup         - Run migrations and collect static (first-time setup)"
	@echo "  make migrate       - Run database migrations"
	@echo "  make collectstatic - Collect static files"
	@echo "  make test          - Run Django tests"
	@echo "  make init          - Create .env from .env.example (first time)"
	@echo "  make backup        - Backup PostgreSQL database"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose exec app bash

# Setup tasks using dedicated containers (no race conditions on scaling)
setup: migrate collectstatic
	@echo "Setup complete!"

migrate:
	docker compose --profile setup run --rm migrate

collectstatic:
	docker compose --profile setup run --rm collectstatic

test:
	docker compose run --rm -e DJANGO_SETTINGS_MODULE=settings_test app python backend/manage.py test

init:
	@test -f .env && echo ".env already exists, skipping" || (cp .env.example .env && echo "Created .env from .env.example — edit it with your values")

backup:
	docker compose exec db pg_dump -U lakshmi lakshmi | gzip > backup_$$(date +%Y%m%d_%H%M%S).sql.gz
