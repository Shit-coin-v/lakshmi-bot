# Deployment Guide

> Обновлено: 2026-04-25

## Требования

- Docker >= 24.0
- Docker Compose >= 2.20
- GNU Make
- Внешний reverse-proxy с SSL (Cloudflare, Caddy и т.д.) — nginx-контейнер слушает HTTP

## Переменные окружения

Скопируйте шаблон и заполните значения:

```bash
make init   # либо: cp .env.example .env
```

### Обязательные

| Переменная | Назначение |
|------------|-----------|
| `SECRET_KEY` | Django secret. Сгенерировать: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_PORT` | PostgreSQL. В Docker `POSTGRES_HOST=db` |
| `REDIS_PASSWORD` | Пароль Redis (используется в healthcheck и URL) |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | `redis://:${REDIS_PASSWORD}@redis:6379/0` |
| `BOT_TOKEN` | Токен `customer_bot` |
| `INTEGRATION_API_KEY` | API-ключ 1С интеграции (`X-Api-Key`). Используется и для `ONEC_API_KEY`, если последний не задан |
| `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` | Учётка Grafana |

### Сильно рекомендованные (production)

| Переменная | Назначение |
|------------|-----------|
| `COURIER_BOT_TOKEN` | Токен `courier_bot` |
| `PICKER_BOT_TOKEN` | Токен `picker_bot` |
| `ONEC_ALLOW_IPS` | IP whitelist для `/onec/*`. **Пустое значение в production = deny all (403).** Поддерживает wildcard `192.168.1.*` |
| `ONEC_ORDER_URL` | URL HTTP-сервиса 1С для приёма заказов (Lakshmi → 1С) |
| `FIREBASE_SERVICE_ACCOUNT_JSON` или `FIREBASE_SERVICE_ACCOUNT_PATH` | FCM-ключи для push-уведомлений |
| `PUBLIC_BASE_URL` | Базовый URL (нужен Grafana/Metabase для root_url) |
| `SERVER_NAME` | `server_name` в nginx (по умолчанию `_`) |

### Дополнительные / опциональные

| Переменная | Назначение |
|------------|-----------|
| `DEBUG` | По умолчанию `False` |
| `ALLOWED_HOSTS` | По умолчанию `localhost,127.0.0.1,app` |
| `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | Безопасность Django |
| `POSTGRES_SSLMODE` | SSL-режим подключения к БД |
| `ONEC_API_KEY` | Отдельный ключ для `/onec/*`, по умолчанию = `INTEGRATION_API_KEY` |
| `ONEC_ORDER_COMPLETE_URL` | URL «заказ выполнен» в 1С |
| `ONEC_BONUS_URL` | URL «начисление/списание бонуса» в 1С (по чекам) |
| `ONEC_RFM_SYNC_URL`, `ONEC_RFM_SYNC_ENABLED`, `ONEC_RFM_SYNC_CHUNK_SIZE` | Синхронизация RFM-сегментов в 1С (по умолчанию выключено, чанк 500) |
| `ONEC_BASIC_AUTH_USER`, `ONEC_BASIC_AUTH_PASSWORD` | Опц. Basic-Auth поверх API-ключа для исходящих запросов в 1С |
| `GUEST_TELEGRAM_ID` | telegram_id «гостевого» пользователя для чеков без `card_id` |
| `STORE_LOCATION` | Название магазина в `courier_bot` (по умолчанию «село Намцы») |
| `BACKEND_URL` | URL backend для ботов (по умолчанию `http://app:8000`) |
| `ALLOW_TELEGRAM_HEADER_AUTH` | Feature flag: разрешить fallback-аутентификацию по `X-Telegram-User-Id` в `CustomerPermission` |
| `PERSONAL_RANKING_ENABLED` | Включает Celery-задачу `calculate_personal_rankings` |
| `REFERRAL_BASE_URL`, `APPSTORE_URL`, `GOOGLE_PLAY_URL` | Ссылки для рефералки |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | Почта (коды подтверждения) |
| `YUKASSA_SHOP_ID`, `YUKASSA_SECRET_KEY`, `YUKASSA_RETURN_URL` | ЮKassa |
| `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT` | Тюнинг Gunicorn |
| `BACKUP_RETENTION_DAYS` | Срок хранения бэкапов (по умолчанию 7) |
| `MB_DB_TYPE`, `MB_DB_DBNAME`, `MB_DB_USER`, `MB_DB_PASS`, `MB_DB_HOST` | Metabase (по умолчанию H2) |

## Первый запуск (dev)

```bash
make init        # cp .env.example .env (пропустит, если .env уже есть)
make build       # сборка образов
make setup       # миграции + collectstatic (профиль setup)
make up          # все сервисы в фоне
make logs        # follow логов
```

| Сервис | URL (dev) |
|--------|-----------|
| Django API | http://localhost:8000/api/ |
| Django Admin | http://localhost:8000/admin/ |
| Healthcheck | http://localhost:8000/healthz/ |
| Grafana | http://localhost:3000 (или через nginx `/grafana/`) |
| Prometheus | http://localhost:9090 |
| Loki | http://localhost:3100 |
| Promtail | http://localhost:9080 |
| Metabase | http://localhost:3001 (или через nginx `/metabase/`) |

Все observability-порты по умолчанию слушают `127.0.0.1`.

## Production-деплой

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile setup run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile setup run --rm collectstatic
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Production-оверлей (`docker-compose.prod.yml`) добавляет/меняет:

- `nginx` слушает `80:80` и `443:443` (SSL termination на внешнем proxy либо вне контейнера).
- Resource limits:
  - `app`: CPU 2 / mem 2 GB (reserve 0.5 / 512 MB)
  - `celery_worker`: CPU 1 / mem 1 GB (reserve 0.25 / 256 MB)
  - `celery_beat`: CPU 0.5 / mem 512 MB
  - `db`: CPU 2 / mem 2 GB
  - `redis`: CPU 0.5 / mem 512 MB
  - `nginx`: CPU 1 / mem 512 MB
- Сервис `db_backup` с профилем `backup` (PostgreSQL + Metabase H2, ротация по `BACKUP_RETENTION_DAYS`).
- Увеличенные лимиты json-логов (`max-size: 100m`, `max-file: 10` для app).

Масштабирование Celery-worker:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale celery_worker=2
```

## Команды Makefile

| Команда | Назначение |
|---------|-----------|
| `make help` | Список целей |
| `make init` | `.env` из `.env.example` |
| `make build` | Сборка Docker-образов |
| `make up` | Запуск всех сервисов |
| `make down` | Остановка |
| `make logs` | Follow логов |
| `make shell` | Bash в контейнере `app` |
| `make setup` | Миграции + collectstatic (профиль `setup`) |
| `make migrate` | Только миграции (профиль `setup`) |
| `make collectstatic` | Только статика (профиль `setup`) |
| `make test` | Все тесты (backend + боты + shared + frontend) |
| `make test-backend` | Django тесты, `settings_test` |
| `make test-bot` | Тесты `customer_bot` |
| `make test-courier` | Тесты `courier_bot` |
| `make test-shared` | Тесты `shared/` |
| `make test-frontend` | `flutter analyze && flutter test` |
| `make backup` | Ручной бэкап PostgreSQL в gzip (текущая директория) |

## Архитектура сервисов

```
External proxy (Cloudflare/Caddy, SSL)
            │
            ▼
       nginx (80/443) ──► app (Gunicorn, :8000)
            │             ├── celery_worker  (фоновые задачи)
            │             ├── celery_beat    (DatabaseScheduler)
            │             ├── customer_bot
            │             ├── courier_bot
            │             └── picker_bot
            │
            ├──► /grafana/   ──► grafana   (:3000)
            └──► /metabase/  ──► metabase  (:3000)

db    (PostgreSQL 17) ◄── app, celery_worker, celery_beat, metabase
redis (Redis 7, password) ◄── celery_worker, celery_beat, app, боты

Observability:
  promtail ──► loki ──► grafana
  prometheus (scrape app:8000/metrics, alerts.yml) ──► grafana
```

## Healthcheck'и

| Сервис | Проба | Интервал / start_period |
|--------|-------|-------------------------|
| `app` | `curl -fsS http://127.0.0.1:8000/healthz/` | 30s / 20s |
| `db` | `pg_isready -U lakshmi -d lakshmi` | 10s |
| `redis` | `redis-cli ping` | 10s |
| `celery_worker` | `celery -A celeryapp inspect ping --timeout 10` | 30s / 30s |

`celery_beat` зависит от `celery_worker` (started, не healthy) — порядок старта важен.

## Nginx и rate limiting

`infra/nginx/nginx.conf` + `infra/nginx/rate-limit.conf`:

- Security-заголовки: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: geolocation=(), microphone=(), camera=()`.
- Rate-limit зоны:
  - `api` — 20 r/s, burst 40 (общий API)
  - `onec` — 50 r/s, burst 100 (`/onec/*`)
- Прокcирование: `/static/` (alias, expires 30d), `/media/qr/` (immutable, 1y), `/media/`, `/metrics` (только 127.0.0.1 и 172.16.0.0/12), `/grafana/`, `/metabase/` (с WebSocket upgrade), всё остальное → Django.
- `client_max_body_size 20m`.
- SSL не терминируется в nginx; SSL termination — на внешнем proxy.

## SSL/TLS

Внешний proxy должен пробрасывать заголовки:

- `X-Forwarded-Proto: https`
- `X-Forwarded-For: <client-ip>`
- `X-Forwarded-Host: <domain>`

`settings.py` обрабатывает `X-Forwarded-Proto` через `SECURE_PROXY_SSL_HEADER`. Nginx тоже читает этот заголовок.

```
Client (HTTPS) → External Proxy (TLS) → nginx (HTTP:80) → app (Gunicorn:8000)
```

## Миграции

Миграции вынесены в отдельный сервис (`migrate`) с профилем `setup`. Это устраняет race conditions при масштабировании и гарантирует однократное выполнение.

```bash
# Production: миграции вручную
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile setup run --rm migrate

# Dev
make migrate

# Создать новую миграцию
docker compose exec app python backend/manage.py makemigrations
```

## Бэкапы

Ручной бэкап (dev) — `make backup` (`pg_dump | gzip` в текущую директорию).

Production-бэкап — сервис `db_backup` с профилем `backup` (`scripts/backup_cron.sh`):

- Бэкапит PostgreSQL и Metabase H2.
- Валидирует размер бэкапа (≥ 1 KB), иначе удаляет файл и завершает с ошибкой.
- Ротация по `BACKUP_RETENTION_DAYS` (по умолчанию 7 дней).
- Сохраняет в Docker volume `db_backups`.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup run --rm db_backup
```

Cron (рекомендуется ежедневно в 02:00):

```cron
0 2 * * * cd /path/to/lakshmi-bot && docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup run --rm db_backup >> /var/log/lakshmi-backup.log 2>&1
```

## Обновление

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile setup run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile setup run --rm collectstatic
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

При необходимости перезапустить только конкретный сервис:

```bash
docker compose restart app
docker compose restart celery_worker celery_beat
```

## Наблюдаемость и алерты

- **Метрики:** `app:8000/metrics` (django-prometheus). Prometheus scrape interval 15s.
- **Логи:** Promtail монтирует `/var/lib/docker/containers` и `/var/run/docker.sock` (read-only) → Loki.
- **Дашборды:** Grafana авто-провижн из `infra/observability/grafana/json/lakshmi-operations.json`.
- **BI:** Metabase подключён к PostgreSQL.
- **Алерты Prometheus** (`infra/observability/alerts.yml`):
  - `ServiceDown` (critical) — `up == 0` 1 мин
  - `HighErrorRate` (warning) — доля 5xx > 5% за 5 мин
  - `CeleryQueueBacklog` (warning) — > 50 активных задач за 10 мин

## CI

`.github/workflows/ci.yml`. Триггеры: push в `dev`/`main`, PR в `main`.

| Job | Шаги |
|-----|------|
| `lint` | `ruff check backend/ bots/ shared/` |
| `test-backend` | Django tests на `DJANGO_SETTINGS_MODULE=settings_test` (SQLite, eager Celery) |
| `test-bot` | pytest по `bots/customer_bot/tests/` со service-postgres (lakshmi_test) |
| `test-flutter` | `flutter analyze && flutter test` |
| `docker-build` | Сборка образов app + customer_bot |

`test-*` параллельны, `docker-build` ждёт все тесты.

## Скрипты `scripts/`

| Скрипт | Назначение |
|--------|-----------|
| `migrate.sh` | `python manage.py migrate --noinput` |
| `collectstatic.sh` | `python manage.py collectstatic --noinput` |
| `backup_db.sh` | Ручной бэкап PostgreSQL + Metabase H2 в gzip |
| `backup_cron.sh` | Бэкап с валидацией размера и ротацией (для prod-сервиса `db_backup`) |
| `init_dev.sh` | Bootstrap dev: `.env`, build, db/redis, миграции, статика |
