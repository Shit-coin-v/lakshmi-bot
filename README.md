# Lakshmi Bot

Backend + Telegram-боты + мобильное приложение для программы лояльности.

## Быстрый старт

```bash
cp .env.example .env
# Заполни .env — BOT_TOKEN, SECRET_KEY, пароли, REDIS_PASSWORD

make build
make setup   # миграции + collectstatic
make up
```

## Структура

| Директория | Описание |
|---|---|
| `backend/` | Django REST API (gunicorn, celery) |
| `bots/customer_bot/` | Telegram-бот для клиентов |
| `bots/courier_bot/` | Telegram-бот для курьеров (round-robin назначение) |
| `bots/picker_bot/` | Telegram-бот для сборщиков |
| `shared/` | Общий код между backend и bots |
| `mobile/flutter_app/` | Flutter мобильное приложение |
| `infra/` | Dockerfile, nginx, redis, observability |
| `scripts/` | Утилиты: миграции, бэкапы, инициализация |
| `docs/` | Архитектура, деплой, аудит |

## Основные команды

```bash
make up              # Запуск всех сервисов
make down            # Остановка
make logs            # Логи
make test            # Тесты (285+)
make migrate         # Миграции
make backup          # Бэкап PostgreSQL + Metabase
make shell           # bash в контейнере app
```

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [Деплой](docs/DEPLOYMENT.md)
- [Аудит безопасности](docs/FULL_AUDIT_2026_02_07.md)
