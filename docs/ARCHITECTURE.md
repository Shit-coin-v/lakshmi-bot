# Архитектура монорепозитория

## Карта системы
- **Backend**: Django + Django REST Framework — основной API и бизнес-логика.
- **Асинхронные задачи**: Celery (worker + beat) для фоновых задач.
- **Интеграция 1С**: изолированный слой интеграции, доступ только через backend.
- **Telegram-боты**: клиентский, курьерский и сборщик; работают **только** через HTTP API backend.
- **Мобильное приложение**: Flutter-клиент, общается с backend по REST API.
- **Observability**: Prometheus, Grafana, Loki, Promtail (инфраструктурный слой).

---

## Назначение директорий (актуально)

- `infra/` — инфраструктура и окружение:
  - Docker Compose
  - nginx
  - observability (Prometheus / Grafana / Loki)
- `backend/` — Django/DRF backend, Celery, бизнес-логика и интеграции.
- `bots/` — исходники Telegram-ботов (UI-логика и сценарии).
- `shared/` — общий код без бизнес-логики (DTO, клиенты, конфигурация).
- `mobile/` — Flutter-приложение.
- `docs/` — архитектура, правила, план рефакторинга, журнал работ.

---

## V1 и V2: статус и границы

### V1 — **завершён**
Цель: стабилизация структуры проекта, путей, Docker/infra **без изменения бизнес-логики и API-контрактов**.

Факты:
- Docker Compose валиден
- Проект поднимается локально
- `healthz` отвечает `200 OK`
- Backend не зависит от `bots`
- Все изменения и проверки зафиксированы в `docs/AGENT_WORKLOG.md`

Повторять задачи V1 запрещено.

### V2 — **в процессе**
Цель: доменная декомпозиция backend-кода и постепенный перенос логики **без изменения внешнего поведения API**.

---

## Границы и правила архитектуры

- Боты **не имеют прямого доступа** к БД — только HTTP API backend.
- Бизнес-логика живёт в сервисах доменных приложений.
- View / Serializer / Model — тонкие.
- Интеграции (1С, платежи, доставка) строго изолированы.
- `shared/` **не содержит бизнес-логики**.
- Любые переносы делаются маленькими PR.
- API-контракты (эндпоинты, поля, форматы, статусы) не меняются без явного разрешения владельца проекта.

---

## Куда добавлять новую функциональность

- **Заказы / корзина / оплата**  
  `backend/apps/orders`

- **Лояльность / бонусы / промокоды**  
  `backend/apps/loyalty`

- **Уведомления (push / Telegram / email / SMS)**  
  `backend/apps/notifications` + Celery

- **Интеграции**  
  `backend/apps/integrations/*`
  - `onec`
  - `payments`
  - `delivery`

- **Общий backend-код (без доменной логики)**  
  `backend/apps/common`

- **Telegram-боты**  
  `bots/<bot_name>` — только UI и сценарии, работа через API

- **Мобильное приложение**  
  `mobile/flutter_app`

/
├── infra/
│ ├── docker/
│ │ ├── docker-compose.yml
│ │ ├── docker-compose.override.yml
│ │ ├── nginx/
│ │ │ ├── Dockerfile
│ │ │ └── nginx.conf
│ │ └── backend/
│ │ └── Dockerfile
│ └── observability/
│ ├── grafana/
│ ├── prometheus.yml
│ ├── loki-config.yaml
│ └── promtail-config.yaml
│
├── backend/
│ ├── manage.py
│ ├── requirements.txt
│ ├── entrypoint.sh
│ ├── backend/ # Django project (settings, urls, wsgi, asgi, celery)
│ └── apps/
│ ├── api/ # текущий API слой (будет постепенно разбираться)
│ ├── main/ # легаси-логика (постепенный перенос)
│ ├── orders/ # V2
│ ├── loyalty/ # V2
│ ├── notifications/ # V2
│ ├── integrations/ # V2
│ │ ├── onec/
│ │ ├── payments/
│ │ └── delivery/
│ └── common/ # общие модели/утилиты без бизнес-логики
│
├── bots/
│ ├── customer_bot/
│ ├── courier_bot/
│ └── picker_bot/
│
├── shared/
│ ├── dto/
│ ├── clients/
│ └── config/
│
├── mobile/
│ └── flutter_app/
│
└── docs/
├── ARCHITECTURE.md
├── REFACTOR_PLAN.md
└── AGENT_WORKLOG.md

---

## Источник актуального контекста

- `docs/AGENT_WORKLOG.md` — **обязателен к прочтению перед началом любой работы**.  
  Фиксирует:
  - что уже сделано
  - какие гейты закрыты
  - какие шаги повторять нельзя

Этот файл является единственным источником истины по статусу рефакторинга.
## Актуальное дерево проекта (на данный момент)

