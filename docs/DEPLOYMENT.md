# Deployment Guide

## Требования

- Docker >= 24.0
- Docker Compose >= 2.20
- GNU Make

## Переменные окружения

Скопируйте шаблон и заполните значения:

```bash
cp .env.example .env
```

Обязательные переменные:

| Переменная | Описание |
|------------|----------|
| `SECRET_KEY` | Django secret key (сгенерировать: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `POSTGRES_DB` | Имя базы данных |
| `POSTGRES_USER` | Пользователь БД |
| `POSTGRES_PASSWORD` | Пароль БД |
| `POSTGRES_HOST` | Хост БД (в Docker: `db`) |
| `BOT_TOKEN` | Telegram Bot API токен |
| `INTEGRATION_API_KEY` | API-ключ для 1C интеграции |
| `CELERY_BROKER_URL` | URL брокера Celery (в Docker: `redis://redis:6379/0`) |

## Первый запуск (dev)

```bash
# 1. Сборка контейнеров
make build

# 2. Миграции и статика
make setup

# 3. Запуск всех сервисов
make up

# 4. Проверка логов
make logs
```

Сервисы будут доступны:

| Сервис | URL |
|--------|-----|
| Django API | http://localhost:8000/api/ |
| Django Admin | http://localhost:8000/admin/ |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Metabase | http://localhost:3001 |

## Production деплой

```bash
# Сборка и запуск с production-оверлеем
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile setup run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Production-оверлей (`docker-compose.prod.yml`) добавляет:
- Nginx на портах 80/443
- 2 реплики Celery worker
- Увеличенные лимиты логов

## Команды Makefile

```
make build          — Сборка Docker-контейнеров
make up             — Запуск всех сервисов
make down           — Остановка всех сервисов
make logs           — Просмотр логов (follow)
make shell          — Bash-сессия в контейнере app
make setup          — Миграции + статика (первый запуск)
make migrate        — Только миграции
make collectstatic  — Только сбор статики
make test           — Запуск тестов (settings_test.py)
make backup         — Бэкап PostgreSQL в gzip
```

## Архитектура сервисов

```
nginx (порт 80/443) ──► app (Gunicorn, порт 8000)
                         ├── celery_worker (фоновые задачи)
                         ├── celery_beat (периодические задачи)
                         └── customer_bot (Telegram бот)

db (PostgreSQL 17) ◄── все сервисы выше
redis (Redis 7)    ◄── celery_worker, celery_beat

Мониторинг:
  promtail ──► loki ──► grafana
  prometheus ──────────► grafana
```

## Миграции

Миграции вынесены из `entrypoint.sh` в отдельный сервис (`migrate`) с профилем `setup`. Это устраняет race conditions при масштабировании и гарантирует однократное выполнение.

```bash
# Выполнить миграции вручную
make migrate

# Создать новую миграцию
docker compose exec app python backend/manage.py makemigrations
```

## Бэкапы

```bash
# Ручной бэкап
make backup

# Автоматический бэкап (cron)
# Добавить в crontab:
# 0 3 * * * cd /path/to/lakshmi-bot && make backup
```

Бэкапы сохраняются в текущую директорию: `backup_YYYYMMDD_HHMMSS.sql.gz`

## Обновление

```bash
git pull
make build
make migrate
docker compose restart
```
