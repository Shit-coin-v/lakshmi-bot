.PHONY: build up down logs shell migrate collectstatic setup test test-backend test-bot test-shared test-frontend backup help init

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
	@echo "  make test          - Run all tests (backend, bot, shared, frontend)"
	@echo "  make test-backend  - Run Django backend tests"
	@echo "  make test-bot      - Run bot pytest tests"
	@echo "  make test-shared   - Run shared module pytest tests"
	@echo "  make test-frontend - Run Flutter frontend tests"
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

test: test-backend test-bot test-shared test-frontend

test-backend:
	docker compose run --rm -e DJANGO_SETTINGS_MODULE=settings_test app python backend/manage.py test

test-bot:
	docker compose run --rm customer_bot sh -c 'pip install --quiet --target /tmp/deps pytest && PYTHONPATH=/tmp/deps:$$PYTHONPATH python -m pytest tests/ -v'

test-shared:
	@docker compose run --rm -e DJANGO_SETTINGS_MODULE=settings_test app sh -c 'pip install --quiet --target /tmp/deps pytest && PYTHONPATH=/tmp/deps:$$PYTHONPATH python -m pytest shared/ -v; ret=$$?; [ $$ret -eq 0 ] || [ $$ret -eq 5 ] || exit $$ret'

test-frontend:
	@if [ -d mobile/flutter_app/test ] && command -v flutter >/dev/null 2>&1; then \
		cd mobile/flutter_app && flutter test; \
	else \
		echo "Skipping frontend tests: Flutter SDK or test/ not found"; \
	fi

init:
	@test -f .env && echo ".env already exists, skipping" || (cp .env.example .env && echo "Created .env from .env.example — edit it with your values")

backup:
	docker compose exec db pg_dump -U lakshmi lakshmi | gzip > backup_$$(date +%Y%m%d_%H%M%S).sql.gz
