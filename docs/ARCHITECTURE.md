# Архитектура проекта

> **Обновлено:** 2026-04-25

---

## Стек

| Компонент | Технология |
|-----------|-----------|
| Backend | Django 5.2 + DRF 3.15, Python 3.12 |
| Задачи | Celery 5.5 (worker + beat), Redis 7 |
| БД | PostgreSQL 17 |
| Боты | aiogram 3.13 (`customer_bot`, `courier_bot`, `picker_bot`) |
| Mobile | Flutter (Dart) |
| Платежи | ЮKassa (СБП hold/capture, refund) |
| Push | FCM (Firebase Cloud Messaging) |
| Инфраструктура | Docker Compose, Nginx 1.27 |
| Мониторинг | Prometheus, Grafana, Loki, Promtail |
| Аналитика | Metabase |
| CI | GitHub Actions (lint + tests + Docker build) |

---

## Структура репозитория

```
lakshmi-bot/
├── docker-compose.yml             # Базовый compose (dev и prod)
├── docker-compose.prod.yml        # Production-оверлей (resource limits, backup)
├── Makefile                       # build/up/test/migrate/backup и пр.
├── .github/workflows/ci.yml       # Lint → tests (backend, bot, flutter) → docker-build
│
├── scripts/
│   ├── migrate.sh                 # python manage.py migrate --noinput
│   ├── collectstatic.sh
│   ├── backup_db.sh               # Ручной бэкап PostgreSQL + Metabase H2
│   ├── backup_cron.sh             # Бэкап с ротацией (BACKUP_RETENTION_DAYS, по умолчанию 7)
│   └── init_dev.sh                # Bootstrap dev-окружения
│
├── infra/
│   ├── docker/
│   │   ├── backend/Dockerfile     # python:3.12-slim, Gunicorn
│   │   └── bots/
│   │       ├── Dockerfile         # customer_bot
│   │       ├── Dockerfile.courier
│   │       └── Dockerfile.picker
│   ├── nginx/
│   │   ├── nginx.conf             # security headers, проксирование Grafana/Metabase, static/media
│   │   ├── rate-limit.conf        # zone api 20 r/s burst 40, zone onec 50 r/s burst 100
│   │   └── Dockerfile             # nginx:1.27-alpine
│   ├── redis/redis.conf           # Пароль + protected-mode
│   └── observability/
│       ├── grafana/
│       │   ├── datasources.yaml
│       │   ├── dashboards.yaml
│       │   └── json/lakshmi-operations.json
│       ├── prometheus.yml         # scrape app:8000/metrics, rule_files: alerts.yml
│       ├── alerts.yml             # ServiceDown, HighErrorRate, CeleryQueueBacklog
│       ├── loki-config.yaml
│       └── promtail-config.yaml
│
├── backend/
│   ├── settings.py                # Production-settings
│   ├── settings_test.py           # SQLite, eager Celery, LocMemCache
│   ├── celeryapp.py               # Celery app + beat-schedule (8 задач)
│   ├── requirements.txt
│   ├── requirements-dev.txt       # pytest, ruff
│   ├── entrypoint.sh              # Gunicorn (миграции вынесены)
│   │
│   └── apps/
│       ├── common/                # health, security (require_onec_auth), middleware, permissions, authentication (JWT)
│       ├── api/                   # Корневые urls, OneCClientMap, ReceiptDedup, AppConfigView
│       ├── main/                  # Product, CustomUser, BroadcastMessage, NewsletterDelivery
│       ├── orders/                # Order, OrderItem, OrderItemChange, CourierProfile, PickerProfile, RoundRobinCursor
│       ├── loyalty/               # Transaction, ReferralReward, BonusHistoryView, ReferralInfo/List
│       ├── notifications/         # Notification, CustomerDevice, FCM push, beat-задачи
│       ├── accounts/              # Email-авторизация: JWT, регистрация, merge аккаунтов
│       ├── bot_api/               # Service API для ботов: заказы, персонал, статусы
│       ├── analytics/             # AnalyticsEvent (session_start/end, screen_view, cart_*, search, promo_click)
│       ├── campaigns/             # CustomerSegment, Campaign, CampaignRule, CustomerCampaignAssignment, CampaignRewardLog
│       ├── rfm/                   # CustomerRFMProfile, CustomerBonusTier, CustomerRFMHistory, RFMSegmentSyncLog
│       ├── showcase/              # ProductRanking (global + personal), urls под /api/showcase/
│       └── integrations/
│           ├── onec/              # 1C ERP: чеки, клиенты, товары, категории, остатки, заказы, RFM-sync
│           ├── payments/          # ЮKassa: СБП hold/capture, webhook, expire, refund
│           └── delivery/          # Заглушка
│
├── bots/
│   ├── customer_bot/
│   ├── courier_bot/               # Round-robin назначение
│   └── picker_bot/                # 3-step flow сборщика
│
├── shared/                        # Общий код backend ↔ боты
│   ├── clients/
│   │   ├── onec_client.py         # Async aiohttp-клиент 1C
│   │   └── backend_client.py      # Бот → Backend
│   ├── broadcast/                 # Django ORM sender для рассылок
│   ├── bot_utils/                 # access, cleanup, retry
│   ├── dto/
│   ├── config/
│   └── referral.py                # Реферальная логика (общая для backend и ботов)
│
├── mobile/flutter_app/
│
└── docs/
    ├── ARCHITECTURE.md            # Этот файл
    ├── DEPLOYMENT.md
    ├── 1c-integration-code.md     # Готовый BSL-код для интеграции с 1С
    ├── backend/                   # Дополнительные backend-доки
    └── plans/                     # Исторические спецификации
```

---

## Авторизация

Четыре механизма, разделены по зонам:

| Механизм | Где используется | Заголовок | Ответ при ошибке |
|----------|-----------------|-----------|------------------|
| `@require_onec_auth` (apps/common/security.py) | endpoints `/onec/*` | `X-Api-Key` + опциональный IP whitelist `ONEC_ALLOW_IPS` | 401 / 403 |
| `ApiKeyPermission` (apps/common/permissions.py) | service-to-service (push, SendMessage) | `X-Api-Key` / `X-Onec-Auth` | 403 |
| `TelegramUserPermission` / `CustomerPermission` | клиентские endpoints | `X-Telegram-User-Id` (или JWT в `CustomerPermission`, флаг `ALLOW_TELEGRAM_HEADER_AUTH`) | 403 |
| JWT `JWTAuthentication` (apps/common/authentication.py) | мобильное приложение `/api/auth/*` | `Authorization: Bearer <token>` | 401 |

JWT: HS256 на Django `SECRET_KEY`, access — 30 мин, refresh — 7 дней. HMAC-подписи не используются.

В production пустой `ONEC_ALLOW_IPS` = «запретить всё» (403). Поддерживаются wildcard-маски (`192.168.1.*`).

### CRM API (для менеджеров)

- Префикс: `/api/crm/*`
- Авторизация: **session-cookie** (`sessionid`) через `SessionAuthentication`
- Permission: `IsCRMStaff` — только пользователи `django.contrib.auth.User` с `is_staff=True`
- CSRF: `csrftoken` cookie + `X-CSRFToken` header для не-GET (read-only в M1, под мутации в M3)
- Endpoints:
  - `POST /api/crm/auth/login/` — вход (email + password)
  - `POST /api/crm/auth/logout/` — выход
  - `GET  /api/crm/auth/me/` — текущий пользователь
  - `GET  /api/crm/dashboard/` — KPI + RFM + activeCampaigns + 14d daily
  - `GET  /api/crm/clients/` — список клиентов (фильтры: q, segment)
  - `GET  /api/crm/clients/<card_id>/` — детальная карточка
  - `GET  /api/crm/orders/` — список заказов (фильтры: status, purchaseType)
  - `GET  /api/crm/campaigns/` — список кампаний (фильтр: status)
  - `GET  /api/crm/broadcasts/history/` — история рассылок
  - `GET  /api/crm/categories/` — список категорий
  - `GET  /api/crm/categories/<slug>/` — категория + SKU
  - `GET  /api/crm/abc-xyz/` — матрица распределения SKU (стаб в M1, реальная аналитика — M2/M5)
- Rate-limit: `anon_auth` 10/min на login (общий с мобильным auth)
- Изоляция: `/api/crm/*` НЕ принимает JWT/X-Api-Key/X-Telegram-User-Id
- Источник: `backend/apps/crm_api/`

---

## Поток заказа

```
Источники заказа:
  Mobile app → POST /api/orders/create/        (cash / card_courier / sbp)
  1С        → POST /onec/order                 (привязка onec_guid)

Оплата СБП: ЮKassa hold (authorized) → Order(new) → 1С + push сборщикам
Оплата cash/card_courier: сразу Order(new) → 1С + push сборщикам

Сборщик (picker_bot):
  new → accepted → assembly → ready
  ready (самовывоз) → completed

Курьер (courier_bot, round-robin RoundRobinCursor по store_id):
  ready (доставка) → delivery → arrived → completed
  completed (СБП) → ЮKassa capture

Отмена на любом этапе → canceled + ЮKassa refund (для СБП)
```

Статусы: `new → accepted → assembly → ready → delivery → arrived → completed` (+ `canceled`).

### Reopen (canceled → new)

Из `canceled` допускается единственный обратный переход — в `new`. Это административный сценарий: заказ был ошибочно отменён (например, оператор отменил по ложному сигналу о недозвоне или курьер ошибся со статусом), и его нужно вернуть в обработку без создания нового заказа.

- Делается только через `update_order_status(..., new_status="new")` в коде / админке. UI клиента такой переход не показывает.
- Авто-рефанд платежа (для уже capture'нутого СБП) на reopen не реверсится — если capture был, его необходимо обработать вручную через ЮKassa-админку. Поэтому reopen имеет смысл преимущественно для заказов, в которых платёж ещё не списан (`authorized` без `captured`) либо оплата офлайн (`cash`/`card_courier`).
- Источник истины — `ALLOWED_TRANSITIONS` в `apps/orders/services.py`.

`/onec/orders/pending` (GET) атомарно переводит выбранные заказы из `new` в `assembly`.

---

## Программа лояльности

- `Transaction` — фиксация продаж и бонусов. Ключевые поля для чеков 1С: `receipt_guid`, `receipt_line`, `receipt_bonus_*`.
- Идемпотентность: `idempotency_key` (UUID) и `(receipt_guid, receipt_line)` (unique).
- `purchase_type ∈ {delivery, pickup, in_store}` — устанавливается в чеках и заказах.
- `store_id` — Integer, внешний ID магазина из 1С (модель Store не вводится).
- `ReferralReward` — реферальные начисления (`pending`/`success`/`failed`), один reward на одного `referee`.
- Гостевые чеки (без `card_id`) привязываются к пользователю с `GUEST_TELEGRAM_ID`.

### RFM (apps/rfm)

- `CustomerRFMProfile` — текущие R/F/M-скоры и `segment_label`.
- `CustomerBonusTier` — фиксация месячного тира (`champions`/`standard`) с `effective_from`/`effective_to`.
- `CustomerRFMHistory` — лог переходов между сегментами.
- `RFMSegmentSyncLog` — лог чанков синхронизации в 1С.

Расчёт ежедневно (`recalculate_all_rfm`), фиксация тиров — 1-го числа месяца (`fix_monthly_bonus_tiers`). При `ONEC_RFM_SYNC_ENABLED=true` после фиксации запускается `sync_rfm_segments_to_onec` (чанками по `ONEC_RFM_SYNC_CHUNK_SIZE`, по умолчанию 500). Названия сегментов отдаются на русском.

### Кампании (apps/campaigns)

- `CustomerSegment` — ручной или правило-ориентированный.
- `Campaign` — `audience_type ∈ {customer_segment, rfm_segment}`.
- `CampaignRule` — `reward_type ∈ {fixed_bonus, bonus_percent, fixed_plus_percent, product_discount}`.
- `CustomerCampaignAssignment`, `CampaignRewardLog` — назначения и журнал начислений.
- Триггер начисления — обработка чека (`/onec/receipt`) и реферальные события (fail-open).

### Витрина (apps/showcase)

- `ProductRanking` — глобальный рейтинг товаров и (опционально) персональный (`PERSONAL_RANKING_ENABLED`).
- Эндпоинты под `/api/showcase/`.

### Аналитика (apps/analytics)

- `AnalyticsEvent` — события клиента (session_start/end, screen_view, cart_add/remove, search, promo_click).
- Индексы: `(user, event_type)`, `created_at`. Эндпоинты под `/api/analytics/`.

---

## Celery-задачи и beat-schedule

Beat-расписание (backend/celeryapp.py):

| Задача | Расписание | Назначение |
|--------|-----------|------------|
| `send_order_to_onec` | по событию | Отправка заказа в 1С (retry 20–70 сек с jitter) |
| `broadcast_send_task` | по событию | Рассылка через Telegram (Django ORM sender) |
| `send_telegram_message_task` | по событию | Одиночное сообщение в Telegram |
| `send_birthday_congratulations` | ежедневно 09:00 (Asia/Yakutsk) | Поздравления с ДР через FCM/Telegram |
| `redispatch_unassigned_orders` | каждые 2 мин | Round-robin назначение курьера |
| `expire_pending_payments` | каждые 5 мин | Отмена просроченных СБП-платежей |
| `rollback_stuck_assembly_orders` | каждые 5 мин | Откат застрявших заказов из `assembly` в `new` |
| `recalculate_rfm_profiles` | ежедневно 03:00 | Пересчёт RFM-сегментов |
| `fix_monthly_bonus_tiers` | 1-го числа 00:05 | Месячная фиксация бонусных тиров (+ опц. sync в 1С) |
| `calculate_showcase_rankings` | ежедневно 04:00 | Глобальный рейтинг товаров (time_limit 1800s) |
| `calculate_personal_rankings` | ежедневно 04:30 | Персональные рейтинги (если `PERSONAL_RANKING_ENABLED`, time_limit 3600s) |

Scheduler — `django_celery_beat.schedulers:DatabaseScheduler`. Worker — `--max-tasks-per-child=1000`.

---

## Docker-сервисы

| Сервис | Образ | Назначение |
|--------|-------|-----------|
| `app` | infra/docker/backend/Dockerfile | Django + Gunicorn, healthcheck `/healthz/` |
| `celery_worker` | infra/docker/backend/Dockerfile | Worker, healthcheck `celery inspect ping` |
| `celery_beat` | infra/docker/backend/Dockerfile | Beat (`DatabaseScheduler`) |
| `customer_bot` | infra/docker/bots/Dockerfile | Клиентский Telegram-бот |
| `courier_bot` | infra/docker/bots/Dockerfile.courier | Бот курьера |
| `picker_bot` | infra/docker/bots/Dockerfile.picker | Бот сборщика |
| `db` | postgres:17 | PostgreSQL, healthcheck `pg_isready` |
| `redis` | redis:7 | Брокер Celery + кэш (с паролем), healthcheck `redis-cli ping` |
| `nginx` | infra/nginx/Dockerfile (1.27-alpine) | Reverse proxy, rate-limit, security headers |
| `prometheus` | prom/prometheus:v2.48.1 | Метрики (`/metrics` приложения) |
| `grafana` | grafana/grafana:10.4.3 | Дашборды (root_url из `PUBLIC_BASE_URL`/grafana/) |
| `loki` | grafana/loki:2.9.6 | Логи |
| `promtail` | grafana/promtail:2.9.6 | Сбор логов из `/var/lib/docker/containers` |
| `metabase` | metabase/metabase:v0.50.36 | Аналитика на PostgreSQL |
| `migrate` | infra/docker/backend/Dockerfile | One-off (профиль `setup`): `python manage.py migrate` |
| `collectstatic` | infra/docker/backend/Dockerfile | One-off (профиль `setup`): `collectstatic --noinput` |
| `db_backup` | postgres:17 | One-off (профиль `backup`, prod-overlay): бэкап с ротацией |

Сети: `backend` (app/celery/db/redis/боты), `monitoring` (prometheus/grafana/loki/promtail/app/nginx), `bot` (боты + app + redis).

Volumes: `static`, `media`, `pg_data`, `db_backups`, `lokidata`, `grafanadata`, `prometheusdata`, `metabase-data`, `redis_data`.

---

## Production-оверлей (`docker-compose.prod.yml`)

- `nginx` слушает 80 и 443 (SSL termination на внешнем proxy).
- Resource limits: app 2 CPU / 2 GB, celery_worker 1 CPU / 1 GB, celery_beat 0.5 / 512 MB, db 2 CPU / 2 GB, redis 0.5 / 512 MB, nginx 1 / 512 MB.
- `celery_worker` масштабируется через `--scale celery_worker=N`.
- Сервис `db_backup` (профиль `backup`) — ручной/cron-запуск с ротацией (`BACKUP_RETENTION_DAYS=7` по умолчанию).
- Увеличенные лимиты json-логов.

---

## Наблюдаемость

- **Метрики:** `app:8000/metrics` (django-prometheus middleware), Prometheus scrape interval 15s.
- **Алерты** (`infra/observability/alerts.yml`):
  - `ServiceDown` — `up == 0` в течение 1 мин (critical)
  - `HighErrorRate` — доля 5xx > 5% за 5 мин (warning)
  - `CeleryQueueBacklog` — активных задач > 50 в течение 10 мин (warning)
- **Логи:** Promtail → Loki, логи Docker-контейнеров.
- **Дашборды:** Grafana авто-провижн `lakshmi-operations.json`.
- **BI:** Metabase подключён к PostgreSQL.
- Все observability-порты слушают `127.0.0.1` (доступ — через nginx-проксирование `/grafana/`, `/metabase/`).

---

## CI (GitHub Actions, `.github/workflows/ci.yml`)

| Job | Зависит от | Что делает |
|-----|-----------|------------|
| `lint` | — | `ruff check backend/ bots/ shared/` |
| `test-backend` | lint | Django tests, `DJANGO_SETTINGS_MODULE=settings_test` |
| `test-bot` | lint | pytest по `bots/customer_bot/tests/` со service-postgres |
| `test-flutter` | lint | `flutter analyze && flutter test` |
| `docker-build` | все tests | Сборка образов app + customer_bot |

Триггеры: push в `dev`/`main`, PR в `main`.

---

## Ключевые архитектурные решения

- **Два 1C-клиента** (async aiohttp в ботах + sync requests в Celery) — осознанный split, разные retry-стратегии.
- **`store_id` как Integer** (не FK) — внешний ID из 1С, модель Store не вводится.
- **Round-robin курьеров** — `RoundRobinCursor` с `select_for_update`, event-driven + beat fallback.
- **Broadcast через Django ORM** — SQLAlchemy удалена, единый канал.
- **Header-based пагинация** — тело ответа = массив, мета в заголовках `X-Total-Count`, `Link`.
- **SSL на внешнем proxy** — Nginx слушает 80/443 (HTTP), TLS termination у Cloudflare/Caddy.
- **Идемпотентность чеков** — пара `(receipt_guid, receipt_line)` unique + `X-Idempotency-Key` (UUID) на `/onec/receipt`.
- **Гостевые чеки** — `GUEST_TELEGRAM_ID` для покупок без `card_id`.
- **Миграции вне entrypoint** — отдельный one-off сервис под профилем `setup` устраняет race conditions при scale.
- **RFM как отдельное приложение** — изолированная пересчёт-логика и отдельный sync-канал в 1С с журналом батчей.
