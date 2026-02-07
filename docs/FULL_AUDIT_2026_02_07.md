# Технический аудит проекта lakshmi-bot

**Дата**: 2026-02-07
**Версия**: 3.0
**Метод**: Статический анализ кодовой базы (ветка `dev`, commit `3fcdfd6`)
**Аудиторы**: Architect Agent, DevOps/Infra Agent, Code & Security Agent
**Координатор**: Lead Agent

---

## Содержание

1. [Executive Summary](#executive-summary)
2. [Critical — блокирует production / рост](#1-critical--блокирует-production--рост)
3. [Important — технический долг](#2-important--технический-долг)
4. [Optional — улучшения](#3-optional--улучшения)
5. [Сильные стороны проекта](#сильные-стороны-проекта)
6. [Оценки по областям](#оценки-по-областям)
7. [Статус предыдущих находок (v2.0)](#статус-предыдущих-находок-v20)

---

## Executive Summary

Проект lakshmi-bot — retail-tech платформа: Django 5.2 + DRF, Celery, PostgreSQL 17, Redis, Telegram bot (aiogram 3), Flutter mobile app, интеграция с 1C. Инфраструктура: 12+ Docker-сервисов с observability стеком (Prometheus, Grafana, Loki).

**С момента v2.0 исправлены критические проблемы**: IDOR на customer endpoints (C1), SendMessage spam (C2), IP validation (C6), race condition в покупках (C7), nullable receipt_line (I10). Добавлены три механизма авторизации: `@require_onec_auth`, `ApiKeyPermission`, `TelegramUserPermission`.

### Текущая оценка: проект значительно улучшен, но НЕ готов к production

**Оставшиеся блокеры**:
- **IDOR при создании заказа** — `OrderCreateView` принимает произвольный `customer_id`
- **Отсутствие CI/CD** — нет автоматизированного пайплайна
- **Redis без пароля и persistence** — потеря данных при рестарте
- **Нет пагинации и rate limiting** — DoS-вектор на всех list endpoints

**Найдено**: 12 Critical, 15 Important, 12 Optional

---

## 1. Critical — блокирует production / рост

### C1. IDOR при создании заказа — `OrderCreateView`
| | |
|---|---|
| **Область** | Security |
| **Файлы** | `backend/apps/orders/views.py:27-31`, `backend/apps/orders/serializers.py:110-125` |
| **Описание** | `OrderCreateSerializer` принимает `customer` как writable-поле. `TelegramUserPermission` аутентифицирует пользователя, но view не переопределяет `perform_create()` для подстановки `request.telegram_user`. Злоумышленник может создать заказ от имени другого пользователя. |
| **Рекомендация** | Переопределить `perform_create(self, serializer): serializer.save(customer=self.request.telegram_user)`. Сделать `customer` read_only в serializer. |

### C2. Redis без пароля и без persistence
| | |
|---|---|
| **Область** | Infrastructure |
| **Файлы** | `docker-compose.yml` (сервис `redis`) |
| **Описание** | `image: redis:7` без `--requirepass`. Нет volumes — при рестарте теряются Celery broker queue и results. Внутри Docker network доступен всем контейнерам. |
| **Рекомендация** | Добавить `command: redis-server --requirepass ${REDIS_PASSWORD}`, добавить persistent volume, обновить `REDIS_URL` в env. |

### C3. Отсутствие CI/CD
| | |
|---|---|
| **Область** | Infrastructure |
| **Описание** | Нет `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`. Тесты запускаются только вручную (`make test`). Нет автоматических проверок безопасности, линтинга, сканирования образов. |
| **Рекомендация** | Минимальный CI: lint (ruff) + test + docker build. |

### C4. Нет `.dockerignore`
| | |
|---|---|
| **Область** | Infrastructure / Security |
| **Описание** | Весь контекст (включая `.env`, `.git/`, media) копируется в Docker build context. `.env` с секретами может попасть в Docker layer. |
| **Рекомендация** | Создать `.dockerignore`: `.env`, `.git`, `*.pyc`, `__pycache__`, `media/`, `mobile/`. |

### C5. Отсутствие пагинации на всех list endpoints
| | |
|---|---|
| **Область** | Architecture / Security |
| **Файлы** | `backend/apps/orders/views.py:45-52`, `backend/apps/orders/views.py:18-24`, `backend/apps/notifications/views.py:30-42` |
| **Описание** | `ProductListView`, `OrderListUserView`, `NotificationViewSet.list()` — ни один не имеет пагинации. `REST_FRAMEWORK` settings не содержит `DEFAULT_PAGINATION_CLASS`. При росте данных — OOM, DoS. |
| **Рекомендация** | `DEFAULT_PAGINATION_CLASS` в settings + `PageNumberPagination(page_size=50)`. |

### C6. Отсутствие rate limiting
| | |
|---|---|
| **Область** | Security |
| **Описание** | Нет `DEFAULT_THROTTLE_CLASSES` в `REST_FRAMEWORK` settings. Нет `limit_req_zone` в nginx. `ProductListView` (AllowAny, без пагинации) — открытый DoS-вектор. |
| **Рекомендация** | DRF throttling (`AnonRateThrottle`, `UserRateThrottle`) + nginx `limit_req` на `/api/`, `/onec/`, `/admin/`. |

### C7. Promtail в `privileged: true` режиме
| | |
|---|---|
| **Область** | Infrastructure / Security |
| **Файлы** | `docker-compose.yml` (сервис `promtail`) |
| **Описание** | Контейнер имеет полный доступ к host-системе + маунтит `/var/run/docker.sock`. |
| **Рекомендация** | Убрать `privileged`, добавить только нужные capabilities или bind mount read-only. |

### C8. Нет сетевой изоляции Docker
| | |
|---|---|
| **Область** | Infrastructure |
| **Описание** | Все 12+ контейнеров в одной default network. Бот имеет прямой доступ к Redis, Prometheus, Grafana, Metabase. |
| **Рекомендация** | Минимум 3 сети: `frontend` (nginx), `backend` (app, db, redis, celery), `monitoring`. |

### C9. Notification/FCM endpoints — IDOR через `customer_id`
| | |
|---|---|
| **Область** | Security |
| **Файлы** | `backend/apps/notifications/views.py:33-42, 135-207` |
| **Описание** | `NotificationViewSet.list()` принимает `user_id` из query params. `PushRegisterView` и `UpdateFCMTokenView` принимают `customer_id` из body. При утечке API-key — чтение уведомлений и перехват push любого пользователя. |
| **Рекомендация** | Добавить `TelegramUserPermission` или ownership check на `customer_id`. |

### C10. God Model — все модели в `apps.main.models`
| | |
|---|---|
| **Область** | Architecture |
| **Файлы** | `backend/apps/main/models.py` (13 моделей), `backend/apps/orders/models.py`, `backend/apps/notifications/models.py` (re-exports) |
| **Описание** | 13 моделей из разных bounded contexts в одном файле (Product, CustomUser, Order, Transaction, BroadcastMessage, Notification...). Остальные apps — re-exports. 25 миграций в `apps/main/migrations/`. При росте команды — merge-конфликты, сложности с миграциями. |
| **Рекомендация** | Поэтапно вынести модели в соответствующие apps через `SeparateDatabaseAndState`. |

### C11. `SendMessageAPIView` — синхронный HTTP в request handler
| | |
|---|---|
| **Область** | Architecture / Reliability |
| **Файлы** | `backend/apps/main/views.py:70` |
| **Описание** | `requests.post()` к Telegram API синхронно в Django view. При задержках Telegram блокирует gunicorn worker. |
| **Рекомендация** | Перенести в Celery task. |

### C12. `.env` файл с реальным BOT_TOKEN
| | |
|---|---|
| **Область** | Security |
| **Описание** | Файл `.env` содержит `BOT_TOKEN=8555603604:AAH...`. Хотя `.gitignore` содержит `.env`, он физически присутствует. В сочетании с отсутствием `.dockerignore` — риск утечки в Docker layer. |
| **Рекомендация** | Ротировать токен через @BotFather. Убедиться что `.env` никогда не коммитился. Создать `.dockerignore`. |

---

## 2. Important — технический долг

### I1. Дублирование моделей: Django ORM + SQLAlchemy
| | |
|---|---|
| **Файлы** | `bots/customer_bot/database/models.py` |
| **Описание** | Бот дублирует 12 моделей из Django ORM в SQLAlchemy. Синхронизация ручная. Уже есть дрифт: `Order` в SQLAlchemy не имеет `payment_method`, `fulfillment_type`, `onec_guid`, `sync_status`; `Transaction` не имеет `receipt_*` полей; `CustomUser` не имеет `phone`, `email`, `avatar`. |
| **Рекомендация** | Перевести бота на REST API backend или автогенерацию моделей. |

### I2. Notification endpoints — ручная проверка auth вместо DRF
| | |
|---|---|
| **Файлы** | `backend/apps/notifications/views.py:22-28` |
| **Описание** | `NotificationViewSet`, `PushRegisterView`, `UpdateFCMTokenView` — `permission_classes = []` + ручной `_check_api_key()` вместо `permission_classes = [ApiKeyPermission]`. Легко забыть при добавлении нового action. |
| **Рекомендация** | Перейти на `permission_classes = [ApiKeyPermission]`. |

### I3. `OrderCancelView` — нет `select_for_update()`
| | |
|---|---|
| **Файлы** | `backend/apps/orders/views.py:60-88` |
| **Описание** | Race condition между параллельными запросами на отмену или между отменой и 1C sync. |
| **Рекомендация** | Добавить `select_for_update()` при получении заказа. |

### I4. `send_birthday_congratulations` — не масштабируется
| | |
|---|---|
| **Файлы** | `backend/apps/notifications/tasks.py:17-37` |
| **Описание** | Загружает всех именинников в память, синхронно отправляет через `requests.post` в цикле. Нет timeout, retry, пагинации. `BOT_TOKEN` = None если env не задан при импорте. |
| **Рекомендация** | `.iterator()`, chunked processing, timeout, retry, вынести BOT_TOKEN в settings. |

### I5. `broadcast_send_task` — нет retry
| | |
|---|---|
| **Файлы** | `backend/apps/main/tasks.py:11-34` |
| **Описание** | Нет `max_retries`, `autoretry_for`, `retry_backoff`. `asyncio.run()` при падении — task проваливается без повторной попытки. |
| **Рекомендация** | Добавить `max_retries=3`, `autoretry_for=(Exception,)`, `retry_backoff=True`. |

### I6. `pre_save` сигнал на Order — лишний SELECT
| | |
|---|---|
| **Файлы** | `backend/apps/main/signals.py:16-20` |
| **Описание** | `_order_pre_save` делает `Order.objects.get(pk=instance.pk)` при каждом сохранении для определения предыдущего статуса. При массовом 1C sync — overhead. |
| **Рекомендация** | Использовать `django-model-utils` `FieldTracker` или `__original_status` в `__init__`. |

### I7. `OrderListSerializer.items_count` — N+1
| | |
|---|---|
| **Файлы** | `backend/apps/orders/serializers.py:70` |
| **Описание** | `items_count = IntegerField(source='items.count')` — каждый заказ в списке делает отдельный `COUNT(*)`. |
| **Рекомендация** | `annotate(items_count=Count('items'))` в queryset. |

### I8. Отсутствие DB-индексов на критических запросах
| | |
|---|---|
| **Описание** | `Transaction` не имеет индекса на `customer_id`. `Order` не имеет составного индекса на `customer_id + created_at`. |
| **Рекомендация** | Добавить `db_index=True` или `Meta.indexes`. |

### I9. Нет resource limits на контейнерах
| | |
|---|---|
| **Файлы** | `docker-compose.yml`, `docker-compose.prod.yml` |
| **Описание** | Ни один контейнер не имеет `mem_limit`, `cpus`, `deploy.resources`. Один сервис может занять всю RAM/CPU. |
| **Рекомендация** | Добавить лимиты на app, celery, db. |

### I10. Нет alerting rules
| | |
|---|---|
| **Описание** | Prometheus без `alertmanager`, без `rules_files`. Нет Grafana dashboards (только datasources). При падении сервиса никто не узнает. |
| **Рекомендация** | Базовые алерты: service down, high memory, high error rate, queue length. |

### I11. Бэкапы — только ручные
| | |
|---|---|
| **Файлы** | `Makefile`, `scripts/backup_db.sh` |
| **Описание** | Ручной запуск, `db_backups` volume при `docker volume prune` теряется. Нет расписания, ротации, offsite. |
| **Рекомендация** | Cron-задача + ротация + offsite (S3). |

### I12. `load_dotenv()` в 5 файлах внутри контейнеров
| | |
|---|---|
| **Файлы** | `backend/settings.py:8`, `bots/customer_bot/run.py:18`, `bots/customer_bot/config.py:4`, `bots/customer_bot/broadcast.py:13`, `bots/customer_bot/database/models.py:30` |
| **Описание** | Docker Compose уже передаёт env через `env_file`. `load_dotenv()` может перезаписать Docker env vars. |
| **Рекомендация** | Убрать `load_dotenv()` из кода или вызывать с `override=False`. |

### I13. Нет SSL termination в nginx
| | |
|---|---|
| **Файлы** | `infra/nginx/nginx.conf` |
| **Описание** | `listen 80;` только. В prod.yml `ports: "443:443"` но nginx не слушает 443. Предполагается внешний proxy, но не документировано. |
| **Рекомендация** | Добавить SSL (certbot/acme) или документировать внешний proxy. |

### I14. `customer_sync.py` — `user.save()` без `update_fields`
| | |
|---|---|
| **Файлы** | `backend/apps/integrations/onec/customer_sync.py:140` |
| **Описание** | Полный save — race condition с параллельными обновлениями пользователя. |
| **Рекомендация** | `user.save(update_fields=[...])`. |

### I15. `newsletter_enabled` — мёртвое поле в API
| | |
|---|---|
| **Файлы** | `backend/apps/main/serializers.py:18` |
| **Описание** | Мастер-переключатель убран из broadcast flow (commit 9909730), но поле осталось в модели и API. Вводит в заблуждение клиентов. |
| **Рекомендация** | Убрать из serializer или задокументировать deprecated. |

---

## 3. Optional — улучшения

### O1. Дублирование `_onec_error()`
`backend/apps/integrations/onec/order_create.py:13-23` и `receipt.py:33-43` — копипаста. Вынести в shared utils.

### O2. Две реализации broadcast (SQLAlchemy + Django ORM)
`bots/customer_bot/broadcast.py` и `shared/broadcast/django_sender.py`. Усложняет поддержку.

### O3. `asyncio.run()` в Celery task
`backend/apps/main/tasks.py:34` — создаёт новый event loop на каждый вызов. Неэффективно при массовых рассылках.

### O4. Два 1C-клиента (async + sync)
`shared/clients/onec_client.py` (aiohttp) и `backend/apps/integrations/onec/order_sync.py` (requests). Осознанный split, но нет единой абстракции.

### O5. `store_id` на Product — Integer, не FK
`Product.store_id` — `IntegerField` без таблицы `Store`. Нет referential integrity.

### O6. `settings_prod.py` не используется
`DJANGO_SETTINGS_MODULE=settings` в обоих compose-файлах. prod-файл дублирует base settings.

### O7. Один `requirements.txt` — нет разделения dev/prod
Все зависимости (включая потенциально dev-only) идут в production образ.

### O8. Celery worker без `--max-tasks-per-child`
Нет защиты от memory leaks. Рекомендуется `--concurrency=4 --max-tasks-per-child=1000`.

### O9. Celery beat без persistent scheduler
Не использует `DatabaseScheduler`. При рестарте теряет информацию о последних запусках.

### O10. Metabase — файловая БД (H2)
`MB_DB_FILE=/metabase-data/metabase.db` — при потере volume теряется конфигурация.

### O11. Nginx Dockerfile не пиннит версию
`FROM nginx:latest` — непредсказуемые обновления. Рекомендуется `FROM nginx:1.27-alpine`.

### O12. Python 3.10 — EOL октябрь 2026
Планировать миграцию на 3.12+.

---

## Сильные стороны проекта

1. **Трёхуровневая авторизация** — `@require_onec_auth`, `ApiKeyPermission`, `TelegramUserPermission` чётко разделены по зонам. `compare_digest` для timing-safe сравнения ключей.

2. **Идемпотентность** — `X-Idempotency-Key` + `UniqueConstraint` на receipt, `NewsletterDelivery`, `select_for_update()` на заказах. Атомарность через `F()` + `Coalesce`.

3. **Observability stack** — Prometheus + Grafana + Loki + Promtail. `django-prometheus` middleware. Grafana datasources provisioned as code.

4. **Docker best practices** — non-root user, `PYTHONDONTWRITEBYTECODE`, `--no-cache-dir`, health-checks с `service_healthy`, JSON logging с ротацией, `restart: always`.

5. **Dual-channel broadcast** — FCM + Telegram с категориями подписок (promo/news/general). Идемпотентная доставка через `NewsletterDelivery`.

6. **1C-интеграция** — retry-логика (7 попыток), идемпотентность, детальная обработка ошибок (`invalid_json`, `missing_field`, `duplicate_receipt_line`, `unknown_customer`).

7. **Security headers** — HSTS, CSRF, secure cookies, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`. BrowsableAPI отключён.

8. **Shared-код** — broadcast, 1C HTTP-клиент, QR-утилиты — переиспользуется между backend и ботом.

9. **Entrypoint** — `set -euo pipefail`, `exec` для PID 1, конфигурируемые workers/timeout. Миграции вынесены — нет гонки при scaling.

10. **135 тестов** — backend (127) + bot (8), все зелёные. Покрытие security-сценариев (IDOR, auth, ownership).

---

## Оценки по областям

| Область | Оценка | Комментарий |
|---------|--------|-------------|
| Модульность Django apps | 6/10 | 7 apps, но models в одном файле |
| API design (DRF) | 7/10 | Serializers корректны, permissions есть, нет pagination/throttling |
| Авторизация | 8/10 | Три механизма, но notification endpoints обходят DRF |
| Celery | 7/10 | Retry на 1C tasks, beat настроен, broadcast без retry |
| Модели данных | 6/10 | Нормализация OK, не хватает индексов, God Model |
| Shared-код | 8/10 | Хорошо выделен, переиспользуется |
| 1C-интеграция | 8/10 | Идемпотентность, retry, валидация |
| Bot-архитектура | 5/10 | Дублирование моделей, прямой DB-доступ |
| Docker images | 8/10 | Non-root, slim, pinned deps |
| Docker Compose | 6/10 | Healthchecks есть, нет networks/limits/security |
| Nginx | 6/10 | Headers есть, нет SSL/rate-limit |
| Observability | 7/10 | Стек есть, нет алертов и dashboards |
| CI/CD | 0/10 | Отсутствует |
| Бэкапы | 3/10 | Ручные, без ротации и offsite |
| Security (код) | 7/10 | Нет injection, но IDOR на заказах, нет rate limiting |
| Тесты | 7/10 | 135 тестов, security-покрытие, но нет integration tests |
| Production readiness | 4/10 | Нужны fixes C1-C12 |

---

## Статус предыдущих находок (v2.0)

| ID (v2.0) | Описание | Статус |
|-----------|----------|--------|
| C1 | IDOR на customer endpoints | **ИСПРАВЛЕНО** (commit 3fcdfd6) — TelegramUserPermission |
| C2 | SendMessage spam | **ИСПРАВЛЕНО** (commit 3fcdfd6) — ApiKeyPermission |
| C6 | IP validation inconsistency | **ИСПРАВЛЕНО** (commit 3fcdfd6) — `_client_ip()` |
| C7 | Race condition в PurchaseAPIView | **ИСПРАВЛЕНО** (commit 3fcdfd6) — F() + Coalesce |
| I10 | Transaction.receipt_line not nullable | **ИСПРАВЛЕНО** (migration 0025) |
| C3 | Нет CI/CD | **ОТКРЫТО** → C3 в v3.0 |
| C4 | Нет Docker network isolation | **ОТКРЫТО** → C8 в v3.0 |
| C5 | Redis без пароля | **ОТКРЫТО** → C2 в v3.0 |
| I8 | Нет пагинации | **ОТКРЫТО** → C5 в v3.0 (повышен до Critical) |

---

## Roadmap (рекомендуемый порядок)

### Фаза 1 — Security (1-2 дня)
- [ ] C1: Fix IDOR в `OrderCreateView`
- [ ] C9: Fix IDOR в Notification/FCM endpoints
- [ ] C12: Ротация BOT_TOKEN + `.dockerignore`
- [ ] C4: Создать `.dockerignore`

### Фаза 2 — API Hardening (1-2 дня)
- [ ] C5: Добавить пагинацию
- [ ] C6: Добавить rate limiting (DRF + nginx)
- [ ] I2: Унифицировать permission_classes в notifications

### Фаза 3 — Infrastructure (2-3 дня)
- [ ] C2: Redis — пароль + persistence
- [ ] C7: Убрать privileged с Promtail
- [ ] C8: Docker network isolation
- [ ] C3: Минимальный CI/CD pipeline

### Фаза 4 — Architecture (1-2 недели)
- [ ] C10: Распилить God Model
- [ ] C11: SendMessage → Celery
- [ ] I1: Устранить дрифт SQLAlchemy моделей
- [ ] I3-I8: Индексы, N+1, race conditions

### Фаза 5 — Operational Excellence
- [ ] I9-I11: Resource limits, alerting, автобэкапы
- [ ] I13: SSL termination
- [ ] O1-O12: Tech debt cleanup
