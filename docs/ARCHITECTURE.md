# Архитектура монорепозитория

## Карта системы
- **Backend**: Django + Django REST Framework, хранит бизнес-логику и REST API.
- **Асинхронные задачи**: Celery для фоновых джобов.
- **Интеграция 1С**: изолированный модуль OneC для обмена данными.
- **Telegram-боты**: три бота (клиентский, курьерский, сборщик) обращаются к backend через API.
- **Мобильное приложение**: Flutter-клиент, общается с backend API.

## Назначение директорий
- `infra/` — инфраструктура и окружения (Docker/K8s, CI/CD, observability).
- `backend/` — Django/DRF приложение, Celery, бизнес-правила и интеграции.
- `bots/` — исходники Telegram-ботов, обвязка и клиентские адаптеры.
- `shared/` — общие DTO, клиенты и конфигурация, которые переиспользуются между компонентами без бизнес-логики.
- `mobile/` — Flutter-приложение.
- `docs/` — документация по архитектуре, процессам и соглашениям.

## Границы и правила
- Боты не ходят в базу напрямую, только через HTTP API backend.
- Бизнес-логика живёт в `backend/apps/*/services.py`; вьюхи, сериализаторы и модели тонкие.
- Интеграция с 1С изолирована в `backend/apps/integrations/onec`.
- `shared/` содержит только общий код (DTO, клиенты, конфиги), без бизнес-логики.

## Куда добавлять новую фичу
- **Заказ/корзина/оплата** — `backend/apps/orders` (сервисы) + API слой там же; фронты/боты используют существующие клиенты из `shared/`.
- **Лояльность/бонусы/промокоды** — `backend/apps/loyalty` (сервисы) + необходимые API; фронты/боты через API.
- **Уведомления (push/SMS/email/Telegram)** — `backend/apps/notifications` + Celery таски; клиенты/боты инициируют запросы в API.
- **Интеграции (1С/платежи/доставки)** — `backend/apps/integrations/*` (например, `onec`, `payments`, `delivery`) с четкой изоляцией адаптеров.
- **Боты** — `bots/<bot_name>`: UI-логика/команды; общение с backend только через REST клиенты из `shared/`.
- **Мобилка** — `mobile/` (Flutter): экранная логика + обращения к backend API через клиенты/DTO из `shared/`.

## Целевое дерево проекта
```
/ 
├── infra/
│   ├── docker/
│   ├── k8s/
│   └── ci/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   └── apps/
│       ├── orders/
│       ├── loyalty/
│       ├── notifications/
│       ├── integrations/
│       │   ├── onec/
│       │   ├── payments/
│       │   └── delivery/
│       └── common/  # base models, utils без бизнес-логики
├── bots/
│   ├── customer_bot/
│   ├── courier_bot/
│   └── picker_bot/
├── shared/
│   ├── dto/
│   ├── clients/
│   └── config/
├── mobile/
│   └── flutter_app/
└── docs/
    └── ARCHITECTURE.md
```
