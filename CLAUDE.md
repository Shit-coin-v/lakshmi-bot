# Lakshmi Bot — Project Rules

## Назначение проекта

Lakshmi Bot — система для офлайн-магазина с доставкой и программой лояльности.
Включает:

- мобильное приложение клиента (каталог, заказы, бонусы, рефералы);
- Telegram-боты для клиента, курьера и сборщика;
- backend для оформления заказов, начисления бонусов, RFM-сегментации;
- интеграцию с 1C (товары, остатки, чеки, клиенты, заказы);
- интеграцию с ЮKassa (СБП hold/capture, refund).

## Стек

- Backend: Django 5.2 + DRF, Python 3.12
- Очереди/планировщик: Celery 5.5 (worker + beat), Redis 7
- БД: PostgreSQL 17
- Боты: aiogram 3.13 (`customer_bot`, `courier_bot`, `picker_bot`)
- Mobile: Flutter (Dart)
- Платежи: ЮKassa (СБП, hold/capture, refund)
- Инфраструктура: Docker Compose, Nginx 1.27
- Наблюдаемость: Prometheus, Grafana, Loki, Promtail
- Аналитика: Metabase
- CI: GitHub Actions (lint + test + build)

## Структура репозитория

Источник истины — `docs/ARCHITECTURE.md`. Здесь — краткая карта для быстрой навигации.

- `backend/` — Django (gunicorn + Celery)
  - `settings.py` — production-настройки
  - `settings_test.py` — SQLite, eager Celery, LocMemCache
  - `celeryapp.py` — Celery app + beat-schedule
  - `entrypoint.sh` — Gunicorn (миграции вынесены в отдельный one-off сервис)
  - `apps/`
    - `common/` — health, `security` (`require_onec_auth`), middleware, permissions, `authentication` (JWT)
    - `api/` — корневые urls, `OneCClientMap`, `ReceiptDedup`, `AppConfigView`
    - `main/` — `Product`, `CustomUser`, `BroadcastMessage`, `NewsletterDelivery`
    - `orders/` — `Order`, `OrderItem`, `OrderItemChange`, `CourierProfile`, `PickerProfile`, `RoundRobinCursor`
    - `loyalty/` — `Transaction`, `ReferralReward`, `BonusHistoryView`, `ReferralInfo/List`
    - `notifications/` — `Notification`, `CustomerDevice`, FCM push, beat-задачи
    - `accounts/` — email-авторизация: JWT, регистрация, merge аккаунтов
    - `bot_api/` — service API для ботов: заказы, персонал, статусы
    - `analytics/` — `AnalyticsEvent` (session, screen_view, cart_*, search, promo_click)
    - `campaigns/` — `CustomerSegment`, `Campaign`, `CampaignRule`, `CustomerCampaignAssignment`, `CampaignRewardLog`
    - `rfm/` — `CustomerRFMProfile`, `CustomerBonusTier`, `CustomerRFMHistory`, `RFMSegmentSyncLog`
    - `showcase/` — `ProductRanking` (глобальный + персональный), urls под `/api/showcase/`
    - `integrations/`
      - `onec/` — 1C: чеки, клиенты, товары, категории, остатки, заказы, RFM-sync
      - `payments/` — ЮKassa: СБП hold/capture, webhook, expire, refund
      - `delivery/` — заглушка
- `bots/`
  - `customer_bot/` — клиентский Telegram-бот
  - `courier_bot/` — бот курьера (round-robin назначение)
  - `picker_bot/` — бот сборщика (3-step flow)
- `shared/` — общий код backend ↔ боты
  - `clients/onec_client.py` — async aiohttp-клиент 1C
  - `clients/backend_client.py` — бот → backend
  - `broadcast/` — Django ORM sender для рассылок
  - `bot_utils/` — access, cleanup, retry
  - `dto/`, `config/`
  - `referral.py` — общая реферальная логика
- `mobile/flutter_app/` — Flutter (Dart)
- `infra/`
  - `docker/backend/Dockerfile` — python:3.12-slim, Gunicorn
  - `docker/bots/Dockerfile`, `Dockerfile.courier`, `Dockerfile.picker`
  - `nginx/` — `nginx.conf`, `rate-limit.conf`, Dockerfile (1.27-alpine)
  - `redis/redis.conf` — пароль + protected-mode
  - `observability/` — Grafana (datasources, dashboards, json), Prometheus (`prometheus.yml`, `alerts.yml`), Loki, Promtail
- `scripts/` — `migrate.sh`, `collectstatic.sh`, `backup_db.sh`, `backup_cron.sh`, `init_dev.sh`
- `docs/`
  - `ARCHITECTURE.md` — полная архитектура (источник истины)
  - `DEPLOYMENT.md`
  - `1c-integration-code.md` — BSL-код для 1С
  - `backend/` — дополнительные backend-доки
  - `plans/` — исторические спецификации
- Корень: `docker-compose.yml` (dev и база prod), `docker-compose.prod.yml` (resource limits, backup), `Makefile`, `.github/workflows/ci.yml` (lint → tests → docker-build)

## Авторизация

Несколько механизмов, разделены по зонам — не путать:

- `@require_onec_auth` — endpoints `/onec/*` (1C). Заголовок `X-Api-Key` + IP whitelist. Ответ при ошибке: 401.
- `ApiKeyPermission` — service-to-service (push, SendMessage). Заголовок `X-Api-Key`. Ответ: 403.
- `TelegramUserPermission` — клиентские endpoints из ботов. Заголовок `X-Telegram-User-Id`. Ответ: 403.
- JWT (PyJWT) — email-авторизация мобильного приложения (`/api/auth/*`). Заголовок `Authorization: Bearer <token>`. Ответ: 401.

HMAC не используется. Не вводить HMAC/подписи без явного согласования.

## Поток заказа

Статусы: `new → accepted → assembly → ready → delivery → arrived → completed` (+ `canceled`).

- Самовывоз: `new → accepted → assembly → ready → completed` (всё ведёт сборщик).
- Доставка: `new → accepted → assembly → ready` (сборщик), далее `delivery → arrived → completed` (курьер, round-robin).
- Оплата СБП: hold при оформлении → capture при `completed` → refund при отмене.
- Источники заказа: мобильное приложение (`/api/orders/create/`) и 1C (`/onec/order`).
- Уведомления: новый заказ → сборщикам; `ready` (доставка) → курьерам.

## Программа лояльности

- `Transaction` — фиксация покупок и бонусов (включая чеки 1C: `receipt_guid`, `receipt_line`, `receipt_bonus_*`).
- `purchase_type`: `delivery` / `pickup` / `in_store`.
- `idempotency_key` (UUID, unique) и `(receipt_guid, receipt_line)` (unique) — защита от дублей.
- `store_id` — Integer, внешний идентификатор магазина из 1C, отдельная модель Store не нужна.
- `ReferralReward` — реферальные начисления, статусы `pending/success/failed`, лимит «один reward на referee».
- RFM-сегменты считаются в `apps/rfm` и синхронизируются обратно в 1C; названия сегментов на русском.

## Целостность правил Claude

Claude обязан:

- Работать строго по фактам из репозитория. Не выдумывать поля моделей, эндпоинты и параметры.
- Не менять бизнес-смысл (статусы, формулы бонусов, потоки оплаты, контракты 1C/ЮKassa) без явного разрешения.
- Перед крупными изменениями писать план и согласовывать его.
- Для API учитывать: `serializers`, `views`, `permissions`, `authentication_classes`, middleware, urls.
- Для интеграций (1C, ЮKassa, FCM) сохранять текущие контракты заголовков и payload.

## API

- Контракты должны соответствовать `serializers` + `views`. Несоответствия — баги, подлежат исправлению.
- Разрешено чинить: `serializers`, `views`, `permissions`, `urls`, обработку ошибок, валидацию.
- Запрещено без согласования:
  - менять модели (поля, типы, ограничения, индексы, миграции);
  - менять статусы заказа и переходы между ними;
  - менять формулы начисления/списания бонусов;
  - менять контракты `/onec/*` и webhook ЮKassa;
  - менять механизм авторизации (заголовки, классы permissions).

## Миграции и данные

- Любая правка моделей → миграция, согласование, отдельный коммит.
- Не запускать `migrate` без подтверждения.
- Не делать destructive-операции в БД (drop, truncate, массовые updates) без явного запроса.

## Тесты

- `make test` — все тесты (backend + боты + shared + frontend).
- Отдельно: `make test-backend`, `make test-bot`, `make test-courier`, `make test-shared`, `make test-frontend`.
- Для тестов backend — `DJANGO_SETTINGS_MODULE=settings_test` (SQLite, eager Celery, LocMemCache).
- При изменении логики добавлять/обновлять тесты в соответствующем `tests/`.

## Workflow

- План → подтверждение → реализация.
- После работы:
  - `git status`
  - `git diff`
- Коммитить только по явному запросу пользователя. Не пушить без запроса.
- Для интеграций (1C, ЮKassa) дополнительно убедиться, что тесты в `apps/integrations/*/tests` зелёные.

## Стиль

- Без маркетинговых описаний. Только инженерный язык.
- Сообщения коммитов и комментарии — по делу, без воды.
- Комментарии в коде — только на русском языке (включая docstrings и TODO). Английский — для идентификаторов, имён классов/функций/переменных.
- Русский язык в пользовательских строках (UI, уведомления, RFM-сегменты).
