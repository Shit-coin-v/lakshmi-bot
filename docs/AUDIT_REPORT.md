# Технический аудит проекта lakshmi-bot

**Дата**: 2026-02-07
**Версия**: 2.0
**Аудиторы**: Architecture Agent, DevOps Agent, Code & Security Agent
**Координатор**: Lead Agent
**Метод**: Статический анализ кодовой базы (ветка `dev`, commit `9909730`)

---

## Содержание

1. [Executive Summary](#executive-summary)
2. [Critical — блокирует production / рост](#1-critical--блокирует-production--рост)
3. [Important — технический долг](#2-important--технический-долг)
4. [Optional — улучшения](#3-optional--улучшения)
5. [Сильные стороны проекта](#сильные-стороны-проекта)
6. [Оценки по областям](#оценки-по-областям)

---

## Executive Summary

Проект lakshmi-bot — retail-tech платформа (Django 5.2 + DRF, Celery, PostgreSQL 17, Redis, Telegram bot на aiogram 3, Flutter mobile app, интеграция с 1C). Инфраструктура: 12 Docker-сервисов с observability стеком (Prometheus, Grafana, Loki).

**Общая оценка: проект имеет качественную базу, но НЕ готов к production** без устранения критических проблем безопасности и инфраструктурных пробелов.

Ключевые блокеры:
- **Все публичные API endpoints без аутентификации** — IDOR-уязвимости на заказах, профилях, уведомлениях
- **Отсутствие CI/CD** — нет автоматизированного пайплайна тестирования и деплоя
- **Нет network isolation** — все 12 сервисов в одной Docker-сети
- **Redis без пароля и persistence** — данные теряются, доступ без аутентификации

Найдено: **7 Critical**, **12 Important**, **16 Optional** проблем.

---

## 1. Critical — блокирует production / рост

### C1. IDOR на всех публичных API endpoints
| | |
|---|---|
| **Область** | Security / API |
| **Файлы** | `backend/apps/orders/views.py`, `backend/apps/main/views.py`, `backend/apps/notifications/views.py` |
| **Суть** | `permission_classes = [AllowAny]` на всех пользовательских endpoints: `OrderCreateView`, `OrderDetailView`, `OrderListUserView`, `OrderCancelView`, `CustomerProfileView`, `SendMessageAPIView`. Перебор pk (1, 2, 3...) даёт полный доступ ко всем данным. |
| **Вектор атаки** | Любой может: создать заказ от имени другого customer, просмотреть/отменить чужие заказы, изменить профиль, отправить Telegram-сообщение от имени бота |
| **Рекомендация** | Добавить аутентификацию (JWT/token привязанный к telegram_id) + проверку ownership на каждом endpoint. Как минимум — `ApiKeyPermission` + фильтрация по authenticated user |

### C2. SendMessageAPIView — спам от имени бота
| | |
|---|---|
| **Область** | Security |
| **Файл** | `backend/apps/main/views.py:28` |
| **Суть** | Эндпоинт без аутентификации позволяет отправить Telegram-сообщение произвольному пользователю с произвольным текстом (HTML parse_mode). Нет rate limiting. Синхронный `requests.post()` блокирует Django worker |
| **Рекомендация** | Обязательная аутентификация + throttling + перевести на Celery task |

### C3. Отсутствие CI/CD
| | |
|---|---|
| **Область** | DevOps |
| **Суть** | Нет `.github/workflows/`, нет pipeline для тестов, lint, сборки образов, деплоя. Makefile покрывает только локальные операции |
| **Рекомендация** | Создать GitHub Actions: lint (ruff/flake8) → test → build images → push to registry → deploy |

### C4. Нет Docker network isolation
| | |
|---|---|
| **Область** | DevOps / Security |
| **Файл** | `docker-compose.yml` |
| **Суть** | Все 12+ сервисов в одной default-сети. Metabase, Grafana, Prometheus могут напрямую обращаться к DB, Redis, app |
| **Рекомендация** | Сегментация: `frontend` (nginx, app), `backend` (app, db, redis, celery_*), `monitoring` (prometheus, grafana, loki), `analytics` (metabase, db) |

### C5. Redis без пароля, volume и конфигурации
| | |
|---|---|
| **Область** | DevOps / Security |
| **Файл** | `docker-compose.yml` |
| **Суть** | Нет `requirepass` — любой контейнер в сети подключается без аутентификации. Нет volume — данные теряются при перезапуске. `infra/redis/redis.conf` существует (maxmemory 256mb), но НЕ смонтирован в compose |
| **Рекомендация** | Подключить redis.conf через volume, добавить пароль, добавить persistent volume |

### C6. IP whitelist bypass через несовпадение заголовков
| | |
|---|---|
| **Область** | Security |
| **Файл** | `backend/apps/common/security.py` |
| **Суть** | `_client_ip()` (строка 19, для логов) читает `HTTP_X_FORWARDED_FOR` первым. `_ip_allowed()` (строка 42, для авторизации) читает `HTTP_X_REAL_IP` первым. При несовпадении заголовков IP whitelist может быть обойдён. Также: пустой whitelist (`ONEC_ALLOW_IPS=""`) пропускает все IP (строка 39-40: `if not rules: return True`) |
| **Рекомендация** | Использовать единую функцию `_client_ip()` в обоих местах. Рассмотреть fail-closed при пустом whitelist для production |

### C7. Race condition в PurchaseAPIView
| | |
|---|---|
| **Область** | Code Quality |
| **Файл** | `backend/apps/loyalty/views.py:42-53` |
| **Суть** | Read-modify-write без атомарности: `customer.total_spent = (customer.total_spent or D("0")) + data["total"]` (строка 44), `customer.purchase_count = (customer.purchase_count or 0) + 1` (строка 45), затем `customer.save(update_fields=[...])`. Нет `select_for_update()`, нет `F()` expressions. При параллельных запросах от 1С — lost update. Для сравнения: `onec_receipt` использует `F()` expressions корректно |
| **Рекомендация** | `CustomUser.objects.filter(pk=customer.pk).update(total_spent=F('total_spent') + data['total'], ...)` |

---

## 2. Important — технический долг

### I1. Дублирование моделей Django ORM / SQLAlchemy
| | |
|---|---|
| **Область** | Архитектура |
| **Файлы** | `backend/apps/main/models.py` (Django, 413 строк) + `bots/customer_bot/database/models.py` (SQLAlchemy, 375 строк) |
| **Суть** | Полное зеркало 12 таблиц. SQLAlchemy-модели уже отстали: нет полей `Order.onec_guid`, `Order.sync_status`, `Order.payment_method`, `Order.fulfillment_type`, `CustomUser.phone/email/avatar` |
| **Рекомендация** | Рассмотреть переход бота на Django ORM через `asgiref.sync_to_async` или добавить CI-проверку соответствия моделей |

### I2. Монолитный main/models.py — 12 моделей в одном файле
| | |
|---|---|
| **Область** | Архитектура |
| **Файл** | `backend/apps/main/models.py` |
| **Суть** | Product, CustomUser, CustomerDevice, Notification, Order, OrderItem, Transaction, BroadcastMessage, BotActivity, NewsletterDelivery, NewsletterOpenEvent — всё в одном файле. `apps/orders/models.py` и `apps/loyalty/models.py` — пустые re-export фасады |
| **Рекомендация** | Разнести модели по приложениям-владельцам |

### I3. Монолитный receipt.py — 441 строка
| | |
|---|---|
| **Область** | Code Quality |
| **Файл** | `backend/apps/integrations/onec/receipt.py` |
| **Суть** | Одна функция с ручным JSON-парсингом, бонусной аллокацией, дедупликацией и обновлением агрегатов. Высокая когнитивная нагрузка, сложно тестировать изолированно |
| **Рекомендация** | Разбить на: валидация → бонусная аллокация → создание транзакций → обновление агрегатов |

### I4. Celery: birthday task без retry/timeout/acks_late
| | |
|---|---|
| **Область** | Code Quality / Reliability |
| **Файл** | `backend/apps/notifications/tasks.py:17` |
| **Суть** | `requests.post()` без timeout (бесконечный по умолчанию), нет `bind=True`, нет `max_retries`. `BOT_TOKEN` и `BASE_URL` вычисляются при импорте модуля (строки 13-14): если BOT_TOKEN=None → URL будет `botNone/sendMessage`. При crash worker-а задача теряется (нет `acks_late`). Exception в цикле `for user in birthday_users` ловится индивидуально — но если `requests.post` зависнет, worker заблокирован навсегда |
| **Рекомендация** | `bind=True, max_retries=3, acks_late=True`, `timeout=5` в requests.post(), lazy чтение BOT_TOKEN через `settings.TELEGRAM_BOT_TOKEN` |

### I5. Нет resource limits на Docker-контейнерах
| | |
|---|---|
| **Область** | DevOps |
| **Файл** | `docker-compose.yml` |
| **Суть** | Celery worker без ограничений памяти может съесть всю RAM. Metabase известен утечками. Нет `deploy.resources.limits` |
| **Рекомендация** | Задать `mem_limit` и `cpus` для каждого сервиса |

### I6. Нет SSL/TLS termination в nginx
| | |
|---|---|
| **Область** | DevOps / Security |
| **Файл** | `infra/nginx/conf.d/default.conf` |
| **Суть** | Nginx слушает только port 80. HTTPS не настроен. Предполагается внешний reverse proxy, но это не задокументировано |
| **Рекомендация** | Добавить SSL termination или задокументировать внешний proxy |

### I7. Observability: нет alerting, мало scrape targets
| | |
|---|---|
| **Область** | DevOps |
| **Суть** | Prometheus скрейпит только Django. Нет: redis-exporter, postgres-exporter, celery-exporter, nginx stub_status, node exporter. Нет Alertmanager — если сервис упадёт, никто не узнает. Нет дашбордов Grafana (только datasources). Loki без persistent volume |
| **Рекомендация** | Добавить exporters, Alertmanager с правилами, провизионировать базовые дашборды |

### I8. Нет пагинации на list endpoints
| | |
|---|---|
| **Область** | Архитектура / Performance |
| **Файлы** | `NotificationViewSet.list()`, `ProductListView` |
| **Суть** | Возвращают ВСЕ записи без limit/offset. При росте каталога и истории — деградация производительности |
| **Рекомендация** | Добавить `PageNumberPagination` в `DEFAULT_PAGINATION_CLASS` |

### I9. N+1 query в OrderListSerializer
| | |
|---|---|
| **Область** | Performance |
| **Файл** | `backend/apps/orders/serializers.py:70` |
| **Суть** | `items_count = serializers.IntegerField(source='items.count')` — отдельный COUNT для каждого заказа |
| **Рекомендация** | `annotate(items_count=Count('items'))` в queryset |

### I10. `Transaction.receipt_line` NOT NULL без default
| | |
|---|---|
| **Область** | Code Quality |
| **Файл** | `backend/apps/main/models.py:278` |
| **Суть** | Обязательное поле, но `PurchaseAPIView` (legacy) не передаёт его → `IntegrityError` |
| **Рекомендация** | `null=True` или убрать legacy endpoint |

### I11. Dockerfiles без multi-stage build и .dockerignore
| | |
|---|---|
| **Область** | DevOps |
| **Файлы** | `infra/docker/backend/Dockerfile`, `infra/docker/bots/Dockerfile` |
| **Суть** | `build-essential` остаётся в runtime-образе (+200-300 МБ). Нет `.dockerignore` — копируются `__pycache__`, `.pyc`, `.env` |
| **Рекомендация** | Multi-stage build: builder для pip install, clean slim для runtime. Создать `.dockerignore` |

### I12. PostgreSQL: нет автобэкапов, init.sql не подключён
| | |
|---|---|
| **Область** | DevOps |
| **Суть** | `infra/postgres/init.sql` (CREATE EXTENSION uuid-ossp) не смонтирован в compose. Бэкап только ручной через `make backup`. Нет tuning (shared_buffers, work_mem) |
| **Рекомендация** | Подключить init.sql, настроить cron/контейнер для автобэкапов, добавить базовый tuning |

---

## 3. Optional — улучшения

### O1. Монолитный run.py бота (345 строк)
Все хэндлеры в одном файле. Aiogram 3 поддерживает Router для модульности — не используется.
**Рекомендация**: Разделить на роутеры (registration, qr, broadcast, bonuses).

### O2. `onec_orders_pending` меняет статус при GET
GET-запрос меняет `status` с `new` на `assembly` — нарушение HTTP-семантики.
**Рекомендация**: Переделать на POST.

### O3. `datetime.utcnow()` deprecated
Используется повсеместно в bot models и run.py. Deprecated в Python 3.12+.
**Рекомендация**: `datetime.now(timezone.utc)`.

### O4. Нет timeout в shared/clients/onec_client.py
`aiohttp` запрос без timeout — при зависании 1C запрос блокируется бесконечно.
**Рекомендация**: `aiohttp.ClientTimeout(total=10)`.

### O5. Нет DRF throttling
Публичные endpoints без rate limiting.
**Рекомендация**: Настроить `DEFAULT_THROTTLE_CLASSES` и `DEFAULT_THROTTLE_RATES`.

### O6. Prometheus /metrics без ограничения доступа
Endpoint раскрывает внутренние метрики. Nginx ограничивает доступ для некоторых путей, но `/metrics` в Django доступен напрямую.
**Рекомендация**: Ограничить через middleware или nginx.

### O7. `asyncio.run()` в Celery broadcast task
Создаёт новый event loop каждый раз. Работает в prefork, но сломается в gevent/eventlet. Нет `soft_time_limit`.
**Рекомендация**: Добавить `soft_time_limit` / `time_limit`.

### O8. Нет gzip compression в nginx
API-ответы и статика не сжимаются.
**Рекомендация**: `gzip on` с настройкой типов.

### O9. `nginx:latest` — непредсказуемый тег
**Рекомендация**: Фиксировать версию (напр. `nginx:1.27-alpine`).

### O10. Celery beat без singleton-механизма
При `--scale celery_beat=2` будут дубли задач.
**Рекомендация**: `--pidfile` или `DatabaseScheduler` с advisory lock.

### O11. Нет составного индекса Order(customer, -created_at)
`OrderListUserView` фильтрует по customer + сортирует по created_at. Без индекса — full table scan при росте.

### O12. N+1 в broadcast: Notification создаётся по одному в цикле
**Рекомендация**: `bulk_create` для массовых операций.

### O13. Все URL в одном файле apps/api/urls.py (45 паттернов)
**Рекомендация**: Разделить по приложениям с namespaces.

### O14. NotificationViewSet: ручная проверка API key вместо DRF permission
`NotificationViewSet` имеет `permission_classes = []`, `authentication_classes = []` и вызывает `_check_api_key()` вручную в каждом методе (строки 25-28, 31, 45, 98, 109). Тот же паттерн в `UpdateFCMTokenView` и `PushRegisterView`.
**Рекомендация**: Вынести `ApiKeyPermission` в `permission_classes` на уровне класса.

### O15. `NotificationViewSet.list()` — int() без try/except
`user_id = int(user_id)` на строке 39 — при нечисловом input вернёт 500 вместо 400.
**Рекомендация**: Обернуть в try/except или валидировать через serializer.

### O16. `settings_prod.py` не используется
`DJANGO_SETTINGS_MODULE=settings` во всех сервисах. Production-настройки не подключаются.
**Рекомендация**: Использовать `settings_prod.py` для production или убрать файл.

---

## Сильные стороны проекта

### Архитектура
- Плоская структура `backend/` без вложенности — чистый `PYTHONPATH`
- Миграции вынесены из entrypoint в `--profile setup` — нет race conditions
- `shared/` пакет для общего кода между backend и bots
- `shared/clients/onec_client.py` — generic клиент без привязки к Django/bot
- Разделение `shared/broadcast/helpers.py` (чистые функции) и `django_sender.py` (ORM-зависимое)

### Security
- `compare_digest()` для timing-safe сравнения API ключей
- IP whitelist с wildcard-поддержкой для 1C endpoints
- Идемпотентность: `X-Idempotency-Key`, `select_for_update`, receipt_guid дедупликация
- `SECRET_KEY` валидируется в production (`ImproperlyConfigured`)
- HSTS/SSL/Secure cookies правильно привязаны к `DEBUG=False`
- Logging без PII, без `print()` statements

### DevOps
- Healthchecks с `condition: service_healthy` на ключевых сервисах
- Logging с ротацией (`json-file`, `max-size`, `max-file`)
- Observability порты на `127.0.0.1` — не exposed наружу
- Non-root пользователь в Dockerfiles
- Makefile с полным набором команд — низкий порог входа

### Code Quality
- Полноценная валидация через DRF сериализаторы
- 17+ тестовых файлов, хорошее покрытие 1C эндпоинтов
- Celery retry с backoff для критичных задач
- Broadcast система с dual-channel, idempotent delivery, rate limit handling

---

## Оценки по областям

| Область | Оценка | Ключевая проблема |
|---------|--------|-------------------|
| **API Security** | 2/10 | AllowAny на всех public endpoints, IDOR |
| **1C Integration Security** | 8/10 | Хорошо, кроме IP header mismatch |
| **Django Architecture** | 5/10 | Модели в одном файле, re-export фасады |
| **DRF Patterns** | 5/10 | Валидация хорошая, но auth/permissions отсутствуют |
| **Celery** | 6/10 | Retry есть, но нет DLQ, timeout, acks_late |
| **Bot Architecture** | 5/10 | Работает, но дублирование моделей и монолит |
| **Shared Code** | 7/10 | Хорошее разделение, но не pip-пакет |
| **Dockerfiles** | 6/10 | Хорошая база, нет multi-stage |
| **docker-compose** | 7/10 | Healthchecks, profiles, но нет networks/limits |
| **Observability** | 5/10 | Стек есть, но нет alerting и дашбордов |
| **CI/CD** | 0/10 | Полностью отсутствует |
| **Testing** | 6/10 | Есть тесты 1C, но нет покрытия API/bot |

### Итоговая оценка: **5/10**

Проект имеет добротную инженерную базу (идемпотентность, security для 1C, healthchecks, observability стек), но **критические дыры в API security** и **отсутствие CI/CD** блокируют production-деплой.

---

## Roadmap (рекомендуемый порядок)

### Фаза 1 — Security (1-2 недели)
1. Аутентификация на публичных API endpoints (C1, C2, C3)
2. Единый IP-источник в security.py (C6)
3. Race condition fix в PurchaseAPIView (C7)
4. Redis password + config (C5)

### Фаза 2 — Infrastructure (1-2 недели)
5. CI/CD pipeline: lint → test → build → deploy (C3)
6. Docker network isolation (C4)
7. Multi-stage Dockerfiles + .dockerignore (I11)
8. SSL termination (I6)

### Фаза 3 — Reliability (1-2 недели)
9. Celery tasks hardening: timeout, acks_late, DLQ (I4)
10. Pagination на list endpoints (I8)
11. Resource limits на контейнерах (I5)
12. PostgreSQL auto-backups + init.sql (I12)

### Фаза 4 — Tech Debt (2-4 недели)
13. Разнести модели по приложениям (I2)
14. Решить дублирование Django/SQLAlchemy (I1)
15. Рефакторинг receipt.py (I3)
16. Alertmanager + дашборды Grafana (I7)

---

*Отчёт подготовлен на основе статического анализа кодовой базы без запуска проекта.*
