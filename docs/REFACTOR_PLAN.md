# План рефакторинга V2: Статус

## Статус выполнения

| Фаза | Описание | Статус |
|------|----------|--------|
| Phase 0 | Security - удалить print(), pinned metabase | ✅ Выполнено |
| Phase 1 | scripts/ - создать директорию скриптов | ✅ Выполнено |
| Phase 2 | Flatten backend - устранить вложенность backend/backend/ | ✅ Выполнено |
| Phase 3 | Docker compose в корне + Makefile | ✅ Выполнено |
| Phase 4 | Упростить entrypoint.sh | ✅ Выполнено |
| Phase 5 | Customer bot в Docker | ✅ Выполнено |
| Phase 6 | shared/ module - shared/config/qr.py | ✅ Выполнено |
| Phase 7 | Технический долг - убрать _lazy_view | ✅ Выполнено |

## Текущая структура проекта

```
lakshmi-bot/
├── docker-compose.yml          # Основной compose (был в infra/docker/)
├── Makefile                    # Команды: make build, make up, make migrate, make test
├── scripts/
│   ├── migrate.sh
│   ├── collectstatic.sh
│   ├── backup_db.sh
│   └── init_dev.sh
├── backend/
│   ├── settings.py             # Был backend/backend/settings.py
│   ├── settings_test.py        # Был backend/backend/test_settings.py
│   ├── urls.py                 # Был backend/backend/urls.py
│   ├── wsgi.py                 # Был backend/backend/wsgi.py
│   ├── asgi.py                 # Был backend/backend/asgi.py
│   ├── celery.py               # Был backend/backend/celery.py
│   ├── manage.py
│   ├── entrypoint.sh           # Упрощён: только gunicorn
│   └── apps/
│       ├── api/
│       ├── main/
│       └── common/
├── bots/
│   └── customer_bot/
├── shared/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── qr.py               # QR_DIR, константы
│   └── dto/
│       ├── __init__.py
│       └── broadcast.py        # BroadcastRecipient dataclass
└── infra/
    └── docker/
        └── bots/
            └── Dockerfile      # Dockerfile для customer_bot
```

## Ключевые изменения V2

### Phase 2: Flatten backend
- `DJANGO_SETTINGS_MODULE=settings` (было `backend.settings`)
- `ROOT_URLCONF = 'urls'` (было `backend.urls`)
- `WSGI_APPLICATION = 'wsgi.application'` (было `backend.wsgi.application`)

### Phase 3: Docker compose
- `docker-compose.yml` перемещён в корень проекта
- `PYTHONPATH: /app/backend` в контейнерах
- Celery: `-A celery` (было `-A backend.celery`)

### Phase 4: Entrypoint
- Убраны migrate и collectstatic из entrypoint.sh
- Добавлены отдельные сервисы с profiles для миграций

### Phase 5: Customer bot
- Добавлен сервис `customer_bot` в docker-compose.yml
- Dockerfile: `infra/docker/bots/Dockerfile`

### Phase 6: Shared module
- Создан `shared/` модуль для общего кода между backend и bots
- Устранены прямые импорты `from bots.*` в backend

## Phase 7: Технический долг (Выполнено)

### Выполненные задачи:
1. ✅ `apps/api/views.py` - удалён (содержал только реэкспорты)
2. ✅ `apps/api/urls.py` - `_lazy_view`/`_lazy_viewset` заменены на прямые импорты
3. ✅ Contract-файлы - отсутствуют (не требуется действий)

### Проверка:
```bash
grep -n "_lazy_view\|_lazy_viewset" backend/apps/api/urls.py
# 0 совпадений ✅
```

## Команды верификации

```bash
# 1. Build
docker compose build

# 2. Migrate
docker compose --profile migrate run --rm migrate

# 3. Start
docker compose up -d

# 4. Health checks
curl -f http://localhost:8000/healthz/
curl -f http://localhost:8000/onec/health

# 5. Bot check
# Отправить /start в Telegram

# 6. Tests
docker compose run --rm app python backend/manage.py test

# 7. Security check
grep -rn "print.*API\|print.*KEY" backend/
# 0 совпадений

# 8. Boundary check
grep -rn "from bots\." backend/
# 0 совпадений
```

## Локальные проверки

Backend:
```bash
cd backend && DJANGO_SETTINGS_MODULE=settings python manage.py check
python -m compileall backend
```

Docker:
```bash
docker compose config
docker compose up -d --build
docker compose logs --tail=200
```

## V2 Завершён

**Дата завершения:** 2026-02-02

Рефакторинг V2 успешно завершён. Все 8 фаз (0-7) выполнены:

- **Безопасность**: Удалены print() с секретами, закреплена версия Metabase
- **Структура**: Создана директория scripts/, устранена вложенность backend/backend/
- **DevOps**: Docker Compose перенесён в корень, добавлен Makefile
- **Сервисы**: Упрощён entrypoint, customer_bot добавлен в Docker Compose
- **Архитектура**: Создан shared/ модуль, устранены lazy view proxies

Проект готов к дальнейшей разработке.

## История

Детальный журнал выполнения ведётся в `docs/AGENT_WORKLOG.md`.
