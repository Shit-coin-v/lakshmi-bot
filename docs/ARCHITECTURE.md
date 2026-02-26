# Архитектура проекта

> **Обновлено:** 2026-02-26

---

## Стек

| Компонент | Технология |
|-----------|-----------|
| Backend | Django 5.2 + DRF 3.15, Python 3.12 |
| Задачи | Celery 5.5 (worker + beat), Redis 7 |
| БД | PostgreSQL 17 |
| Боты | aiogram 3.13 (customer, courier, picker) |
| Мобильное приложение | Flutter (Dart) |
| Платежи | ЮKassa (СБП, hold/capture) |
| Инфраструктура | Docker Compose, Nginx 1.27 |
| Мониторинг | Prometheus, Grafana, Loki, Promtail |
| Аналитика | Metabase |
| CI | GitHub Actions (lint + test + build) |

---

## Структура репозитория

```
lakshmi-bot/
├── docker-compose.yml            # Dev-конфигурация
├── docker-compose.prod.yml       # Production-оверлей (resource limits, replicas)
├── Makefile                      # make build/up/test/migrate/backup
├── .github/workflows/            # CI pipeline
│
├── scripts/
│   ├── migrate.sh                # Миграции (вынесены из entrypoint)
│   ├── collectstatic.sh
│   ├── backup_db.sh              # Бэкап PostgreSQL + Metabase
│   └── init_dev.sh
│
├── infra/
│   ├── docker/
│   │   ├── backend/Dockerfile    # python:3.12-slim
│   │   └── bots/
│   │       ├── Dockerfile           # customer_bot
│   │       ├── Dockerfile.courier
│   │       └── Dockerfile.picker
│   ├── nginx/
│   │   ├── nginx.conf            # Rate limiting, security headers
│   │   └── Dockerfile            # nginx:1.27-alpine
│   ├── redis/redis.conf          # Пароль + protected-mode
│   └── observability/
│       ├── grafana/datasources.yaml
│       ├── prometheus/
│       │   ├── prometheus.yml
│       │   └── alerts.yml        # ServiceDown, HighErrorRate, CeleryBacklog
│       ├── loki/loki-config.yaml
│       └── promtail/promtail-config.yaml
│
├── backend/                      # Django-приложение
│   ├── settings.py               # Основные настройки
│   ├── settings_test.py          # SQLite, eager Celery, LocMemCache
│   ├── celeryapp.py              # Celery app + beat schedule
│   ├── requirements.txt          # Production-зависимости
│   ├── requirements-dev.txt      # Dev: pytest, ruff
│   ├── entrypoint.sh             # Gunicorn (без миграций)
│   │
│   └── apps/
│       ├── main/                 # Product, CustomUser, BroadcastMessage, NewsletterDelivery
│       ├── orders/               # Order, OrderItem, CourierProfile, PickerProfile, RoundRobinCursor
│       ├── loyalty/              # Transaction (покупки, бонусы)
│       ├── notifications/        # Notification, CustomerDevice, push-задачи
│       ├── accounts/             # Email-авторизация: JWT, регистрация, merge аккаунтов
│       ├── bot_api/              # API для ботов: заказы, персонал, статусы
│       ├── common/               # security, permissions, middleware, health
│       └── integrations/
│           ├── onec/             # 1C ERP: sync клиентов/товаров, чеки, заказы
│           ├── payments/         # ЮKassa: СБП hold/capture, webhook, expire
│           └── delivery/         # Заглушка (не реализовано)
│
├── bots/
│   ├── customer_bot/             # Клиентский Telegram-бот
│   ├── courier_bot/              # Бот курьера (round-robin назначение)
│   └── picker_bot/               # Бот сборщика (3-step flow)
│
├── shared/                       # Общий код между backend и bots
│   ├── clients/
│   │   ├── onec_client.py        # Async HTTP-клиент 1C (aiohttp)
│   │   └── backend_client.py     # Бот → Backend HTTP-клиент
│   ├── broadcast/                # Django ORM sender для рассылок
│   ├── bot_utils/                # Общие утилиты ботов: access, cleanup, retry
│   ├── dto/
│   └── config/
│
├── mobile/flutter_app/           # Flutter мобильное приложение
│
└── docs/
    ├── ARCHITECTURE.md           # Этот файл
    ├── DEPLOYMENT.md             # Инструкции по деплою
    ├── FULL_AUDIT_2026_02_07.md  # Аудит безопасности v3.0 (39 задач — все закрыты)
    └── plans/                    # Исторические спецификации и планы
```

---

## Авторизация

Три механизма, разделены по зонам:

| Механизм | Где используется | Заголовок | Ответ при ошибке |
|----------|-----------------|-----------|-----------------|
| `@require_onec_auth` | 1C endpoints (`/onec/*`) | `X-Api-Key` + IP whitelist | 401 |
| `ApiKeyPermission` | Backend-to-backend (push, SendMessage) | `X-Api-Key` | 403 |
| `TelegramUserPermission` | Customer-facing endpoints | `X-Telegram-User-Id` | 403 |
| JWT (PyJWT) | Email-авторизация (`/api/auth/*`) | `Authorization: Bearer <token>` | 401 |

---

## Поток заказа

```
Клиент (Flutter) → POST /api/orders/create/
  ├── cash/card_courier → Order(new) → 1C + push сборщикам
  └── sbp → ЮKassa hold → webhook → Order(new) → 1C + push сборщикам

Сборщик (picker_bot):
  new → accepted → assembly → ready
  ready + самовывоз → completed

Курьер (courier_bot, round-robin назначение):
  ready + доставка → delivery → arrived → completed
  completed → ЮKassa capture (если СБП)

Отмена на любом этапе → cancel + ЮKassa refund (если СБП)
```

Статусы: `new → accepted → assembly → ready → delivery → arrived → completed` (+ `canceled`)

---

## Celery-задачи

| Задача | Расписание | Описание |
|--------|-----------|----------|
| `send_order_to_onec` | По событию | Отправка заказа в 1C (retry с jitter) |
| `broadcast_send_task` | По событию | Рассылка через Telegram (async_to_sync) |
| `send_telegram_message_task` | По событию | Одиночное сообщение в Telegram |
| `send_birthday_congratulations` | Beat (ежедневно) | Поздравления с ДР |
| `expire_pending_payments` | Beat (каждые 5 мин) | Отмена неоплаченных СБП-платежей |
| `redispatch_unassigned_orders` | Beat (каждые 2 мин) | Назначение курьера на нераспределённые заказы |
| `rollback_stuck_assembly_orders` | Beat (каждые 5 мин) | Откат застрявших заказов в `new` |

---

## Docker-сервисы

| Сервис | Образ | Описание |
|--------|-------|----------|
| `app` | backend/Dockerfile | Django + Gunicorn |
| `celery_worker` | backend/Dockerfile | Celery worker (max-tasks-per-child=1000) |
| `celery_beat` | backend/Dockerfile | Celery beat (DatabaseScheduler) |
| `customer_bot` | bots/Dockerfile | Клиентский Telegram-бот |
| `courier_bot` | bots/Dockerfile.courier | Бот курьера |
| `picker_bot` | bots/Dockerfile.picker | Бот сборщика |
| `db` | postgres:17 | PostgreSQL |
| `redis` | redis:7 | Брокер Celery + кэш (с паролем) |
| `nginx` | nginx:1.27-alpine | Reverse proxy (prod) |
| `prometheus` | prom/prometheus | Метрики |
| `grafana` | grafana/grafana | Дашборды |
| `loki` | grafana/loki | Логи |
| `promtail` | grafana/promtail | Сбор логов |
| `metabase` | metabase/metabase | Аналитика (H2 DB) |

---

## Сети Docker (production)

| Сеть | Сервисы |
|------|---------|
| `frontend` | nginx |
| `backend` | app, celery_worker, celery_beat, db, redis, боты |
| `monitoring` | prometheus, grafana, loki, promtail |

---

## Ключевые решения

- **Два 1C-клиента** (async в ботах + sync в Celery) — осознанный split, разные retry-стратегии
- **`store_id` как Integer** (не FK) — внешний ID из 1C, модель Store не нужна
- **Round-robin курьеров** — `RoundRobinCursor` с `select_for_update`, event-driven + beat fallback
- **Broadcast через Django ORM** — SQLAlchemy удалена, единый канал
- **Header-based пагинация** — тело ответа = массив, мета в заголовках `X-Total-Count`, `Link`
- **SSL на внешнем proxy** — Nginx слушает порт 80, SSL termination на Cloudflare/Caddy
