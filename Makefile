.PHONY: build up down logs shell migrate collectstatic test backup help

# Default target
help:
	@echo "Available commands:"
	@echo "  make build        - Build all Docker containers"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Follow logs from all services"
	@echo "  make shell        - Open bash shell in app container"
	@echo "  make migrate      - Run database migrations"
	@echo "  make collectstatic - Collect static files"
	@echo "  make test         - Run Django tests"
	@echo "  make backup       - Backup PostgreSQL database"

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

migrate:
	docker compose run --rm app python backend/manage.py migrate --noinput

collectstatic:
	docker compose run --rm app python backend/manage.py collectstatic --noinput

test:
	docker compose run --rm -e DJANGO_SETTINGS_MODULE=settings_test app python backend/manage.py test

backup:
	docker compose exec db pg_dump -U lakshmi lakshmi | gzip > backup_$$(date +%Y%m%d_%H%M%S).sql.gz
