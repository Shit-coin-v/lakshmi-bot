# Lakshmi Bot

Backend + Telegram-боты + мобильное приложение для программы лояльности.

## Быстрый старт

```bash
cp backend/.env.example backend/.env
# Отредактируй backend/.env — заполни BOT_TOKEN, SECRET_KEY, пароли

make build
make setup   # миграции + collectstatic
make up
```

## Структура

| Директория | Описание |
|---|---|
| `backend/` | Django REST API (gunicorn, celery) |
| `bots/` | Telegram-боты (customer, courier, picker) |
| `shared/` | Общий код между backend и bots |
| `mobile/flutter_app/` | Flutter мобильное приложение |
| `infra/` | Dockerfile'ы, nginx, observability |
| `scripts/` | Утилиты: миграции, бэкапы, инициализация |
| `docs/` | Архитектура, деплой, аудит безопасности |

## Основные команды

```bash
make up              # Запуск всех сервисов
make down            # Остановка
make logs            # Логи
make test            # Тесты
make migrate         # Миграции
make backup          # Бэкап PostgreSQL
make shell           # bash в контейнере app
```

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [Деплой](docs/DEPLOYMENT.md)
- [Безопасность](docs/SECURITY_AUDIT.md)
