## Целевая структура репозитория (V2)

> **Обновлено:** 2026-02-02 - учтены результаты технического аудита и рекомендации по безопасности

```text
lakshmi-bot/
├── .env.example                       # Шаблон переменных окружения
├── .gitignore
├── .editorconfig
├── README.md
├── docker-compose.yml                 # Основной файл для локальной разработки
├── docker-compose.override.yml.example # Шаблон для локальных переопределений
├── docker-compose.prod.yml            # Production конфигурация
├── Makefile                           # Команды для разработки (make test, make deploy)
│
├── scripts/                           # Утилиты для автоматизации
│   ├── init_dev.sh                    # Инициализация dev окружения
│   ├── migrate.sh                     # Применение миграций (вынесено из entrypoint)
│   ├── collectstatic.sh               # Сборка статики
│   └── backup_db.sh                   # Резервное копирование PostgreSQL
│
├── infra/                             # Инфраструктурные конфигурации
│   ├── docker/                        # Dockerfile'ы для сервисов
│   │   ├── backend/
│   │   │   └── Dockerfile
│   │   └── bots/
│   │       └── Dockerfile             # Контейнер для Telegram ботов
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── Dockerfile
│   ├── postgres/
│   │   └── init.sql                   # Начальная инициализация БД
│   ├── redis/
│   │   └── redis.conf
│   └── observability/                 # Мониторинг и логирование
│       ├── grafana/
│       │   └── datasources.yaml
│       ├── prometheus/
│       │   └── prometheus.yml
│       ├── loki/
│       │   └── loki-config.yaml
│       └── promtail/
│           └── promtail-config.yaml
│
├── backend/                           # Django приложение
│   ├── manage.py
│   ├── requirements.txt
│   ├── entrypoint.sh                  # Упрощенный (БЕЗ миграций и collectstatic)
│   ├── __init__.py
│   ├── settings.py                    # ← Было: backend/backend/settings.py (убрана вложенность)
│   ├── settings_test.py               # Настройки для тестов (CELERY_TASK_ALWAYS_EAGER=True)
│   ├── settings_prod.py               # Production настройки (опционально)
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   ├── celery.py
│   │
│   ├── apps/                          # Django приложения
│   │   ├── api/                       # REST API endpoints
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── security.py            # ВАЖНО: удалить print() из production кода
│   │   │   └── tests/
│   │   │
│   │   ├── main/                      # Основные модели (Customer, Product, Transaction)
│   │   │   ├── models.py
│   │   │   ├── admin.py
│   │   │   └── views.py
│   │   │
│   │   ├── orders/                    # Заказы и доставка
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   └── views.py
│   │   │
│   │   ├── loyalty/                   # Программа лояльности
│   │   │   ├── models.py
│   │   │   └── views.py
│   │   │
│   │   ├── notifications/             # Push-уведомления
│   │   │   ├── models.py
│   │   │   ├── tasks.py
│   │   │   ├── push.py
│   │   │   └── views.py
│   │   │
│   │   ├── integrations/              # Внешние интеграции
│   │   │   ├── onec/                  # 1C ERP интеграция
│   │   │   │   ├── customer_sync.py
│   │   │   │   ├── product_sync.py
│   │   │   │   ├── receipt.py
│   │   │   │   ├── order_create.py
│   │   │   │   └── order_status.py
│   │   │   ├── payments/              # Платежные системы (заглушка)
│   │   │   └── delivery/              # Службы доставки (заглушка)
│   │   │
│   │   └── common/                    # Общие утилиты
│   │       ├── security.py            # Аутентификация для 1C API
│   │       ├── health.py              # Health check endpoints
│   │       └── middleware.py
│   │
│   └── tests/                         # Интеграционные и E2E тесты
│       ├── integration/
│       │   ├── test_onec_flow.py
│       │   └── test_order_flow.py
│       ├── e2e/
│       └── conftest.py
│
├── bots/                              # Telegram боты
│   ├── customer_bot/                  # Клиентский бот (активен)
│   │   ├── run.py
│   │   ├── config.py
│   │   ├── requirements.txt           # Отдельные зависимости от backend
│   │   ├── registration.py
│   │   ├── qr_code.py
│   │   ├── broadcast.py
│   │   ├── keyboards.py
│   │   ├── onec_client.py
│   │   ├── database/
│   │   │   └── models.py              # SQLAlchemy модели
│   │   └── tests/
│   │
│   ├── courier_bot/                   # Бот для курьеров (TODO)
│   │   └── .gitkeep
│   │
│   └── picker_bot/                    # Бот для сборщиков (TODO)
│       └── .gitkeep
│
├── shared/                            # Общий код между backend и bots
│   ├── dto/                           # Data Transfer Objects
│   ├── clients/                       # Клиенты для внешних API
│   │   └── onec_client.py             # Shared клиент для 1C
│   └── config/                        # Общие конфигурации
│
├── mobile/                            # Мобильное приложение
│   └── flutter_app/
│       ├── lib/
│       ├── pubspec.yaml
│       └── README.md
│
└── docs/                              # Документация
    ├── ARCHITECTURE.md                # Этот файл
    ├── DEPLOYMENT.md                  # Инструкции по деплою (TODO)
    ├── REFACTOR_PLAN.md               # План рефакторинга
    ├── SECURITY_AUDIT.md              # Результаты аудита безопасности (TODO)
    └── AGENT_WORKLOG.md               # Журнал изменений агента
```

---

## Ключевые изменения V2

### 1. Упрощение структуры backend
```diff
- backend/backend/settings.py  # Двойная вложенность
+ backend/settings.py           # Плоская структура
```

**Влияние:**
- `DJANGO_SETTINGS_MODULE`: `backend.settings` → `settings`
- `PYTHONPATH`: `/app:/app/backend` → `/app/backend`
- Все импорты: `from backend.settings` → `from settings`

### 2. docker-compose.yml в корне
```diff
- infra/docker/docker-compose.yml
+ docker-compose.yml
```

**Преимущества:**
- Стандартная практика (docker-compose up в корне проекта)
- Проще для новых разработчиков
- Четкое разделение dev/prod конфигураций

### 3. Вынос миграций из entrypoint.sh
```diff
- backend/entrypoint.sh: python manage.py migrate --noinput
+ scripts/migrate.sh + отдельный docker-compose сервис
```

**Преимущества:**
- Избавление от race conditions при scaling
- Миграции выполняются один раз перед запуском app
- Возможность запускать миграции отдельно

### 4. Интеграция customer_bot в Docker Compose
```yaml
# Новый сервис
services:
  customer_bot:
    build: infra/docker/bots
    restart: always
```

**Преимущества:**
- Автоматический запуск вместе с backend
- Автоперезапуск при падении
- Единообразное управление сервисами

### 5. Разделение настроек Django
```
backend/
├── settings.py           # Базовые настройки
├── settings_test.py      # Для тестов (CELERY_TASK_ALWAYS_EAGER=True)
└── settings_prod.py      # Production (опционально)
```

**Преимущества:**
- Четкое разделение окружений
- Нет случайных production настроек в dev
- Безопасность (Celery не работает синхронно в prod)

---

## Критичные фиксы из аудита безопасности

### P0 - Утечка данных в логах
**Файл:** `backend/apps/common/security.py:60-69, 89`

```python
# УДАЛИТЬ:
print(f"HEADER: '{key}' = '{value}'")
print(f"DEBUG: SERVER_KEY='{API_KEY}' | CLIENT_KEY='{api_key}'")

# ЗАМЕНИТЬ НА:
logger.debug("API key verification", extra={"ip": _client_ip(request)})
```

### P0 - Production конфиг в git
**Файл:** `infra/docker/docker-compose.override.yml`

```diff
+ # Добавить в .gitignore
+ docker-compose.override.yml

+ # Создать шаблон
+ docker-compose.override.yml.example
```

### P1 - Зафиксировать версии Docker images
```diff
- nginx:latest
+ nginx:1.25-alpine

- grafana/grafana:latest
+ grafana/grafana:10.4.3
```

---

## Чеклист миграции на V2

### Подготовка
- [ ] Создать ветку `refactor/structure-v2`
- [ ] Убедиться, что все тесты проходят
- [ ] Сделать бэкап БД
- [ ] Зафиксировать текущие переменные окружения

### Критичные фиксы безопасности (делать ВМЕСТЕ с рефакторингом)
- [ ] Удалить все `print()` из `apps/common/security.py`
- [ ] Переместить `docker-compose.override.yml` в `.gitignore`
- [ ] Создать `docker-compose.override.yml.example`
- [ ] Переместить `.env.example` в корень
- [ ] Создать `settings_test.py` с `CELERY_TASK_ALWAYS_EAGER=True`
- [ ] Убрать `CELERY_TASK_ALWAYS_EAGER` из `settings.py`
- [ ] Зафиксировать версии всех Docker images

### Структурные изменения
- [ ] Переместить `backend/backend/*` → `backend/`
- [ ] Обновить `DJANGO_SETTINGS_MODULE` в:
  - [ ] `docker-compose.yml`
  - [ ] `.env.example`
  - [ ] `backend/wsgi.py`
  - [ ] `backend/asgi.py`
  - [ ] `backend/celery.py`
  - [ ] `infra/docker/backend/Dockerfile`
- [ ] Обновить `PYTHONPATH` в `infra/docker/backend/Dockerfile`
- [ ] Обновить все импорты в коде
- [ ] Переместить `infra/docker/docker-compose.yml` → `docker-compose.yml`
- [ ] Создать `scripts/` директорию
- [ ] Создать `scripts/migrate.sh`
- [ ] Создать `scripts/collectstatic.sh`
- [ ] Создать `scripts/backup_db.sh`
- [ ] Упростить `backend/entrypoint.sh` (убрать миграции и collectstatic)
- [ ] Добавить сервис `migrate` в `docker-compose.yml`
- [ ] Создать `infra/docker/bots/Dockerfile`
- [ ] Добавить сервис `customer_bot` в `docker-compose.yml`
- [ ] Создать `Makefile` с базовыми командами
- [ ] Создать `backend/tests/` для интеграционных тестов

### Обновление документации
- [ ] Обновить README.md с новыми инструкциями
- [ ] Создать `docs/DEPLOYMENT.md`
- [ ] Обновить комментарии в `.env.example`

### Тестирование после миграции
- [ ] Запустить `docker-compose build`
- [ ] Запустить `docker-compose up`
- [ ] Проверить логи всех сервисов (без ошибок)
- [ ] Проверить, что миграции применились
- [ ] Проверить Django Admin (`/admin/`)
- [ ] Проверить API endpoints (`/api/products/`, `/onec/health`)
- [ ] Проверить Telegram bot (отправить `/start`)
- [ ] Проверить Celery tasks (запустить тестовую задачу)
- [ ] Проверить Grafana (`/grafana/`)
- [ ] Проверить Prometheus (`/metrics`)
- [ ] Запустить все тесты (`make test`)
- [ ] Проверить отсутствие `print()` в production коде
- [ ] Проверить, что секреты не попадают в логи

### Финализация
- [ ] Обновить `docs/AGENT_WORKLOG.md`
- [ ] Создать Pull Request
- [ ] Code review
- [ ] Merge в `dev`
- [ ] Тестирование на staging
- [ ] Deploy в production

---

## Важные замечания

### DJANGO_SETTINGS_MODULE
После миграции изменится значение переменной:
```bash
# Было
DJANGO_SETTINGS_MODULE=backend.settings

# Стало
DJANGO_SETTINGS_MODULE=settings
```

Обновить в:
- `.env.example`
- `docker-compose.yml`
- `backend/manage.py`
- `backend/wsgi.py`
- `backend/asgi.py`
- `backend/celery.py`

### PYTHONPATH
```diff
# Было
- ENV PYTHONPATH=/app:/app/backend

# Стало
+ ENV PYTHONPATH=/app/backend
```

### Импорты
Все импорты вида `from backend.settings import ...` нужно заменить на `from settings import ...`

### Docker Compose
Если `.env` будет в корне, обновить:
```yaml
services:
  app:
    env_file: .env  # Было: ../../backend/.env
```

---

## Проверка совместимости

### Боты (SQLAlchemy)
- ✅ Боты используют отдельное подключение к БД
- ✅ Модели SQLAlchemy не зависят от Django ORM
- ⚠️ Убедиться, что переменные окружения доступны

### Mobile App (Flutter)
- ✅ API endpoints не меняются
- ✅ Контракт API сохраняется
- ⚠️ Убедиться, что базовый URL актуален

### 1C Интеграция
- ✅ REST API endpoints остаются теми же
- ⚠️ API ключ должен остаться в `.env`
- ⚠️ Проверить IP whitelist после деплоя
