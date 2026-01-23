План рефакторинга: перенос директорий

A) Текущее дерево (2 уровня)
/
├── infra/
│   ├── docker/
│   │   ├── docker-compose.override.yml
│   │   ├── docker-compose.yml
│   │   ├── nginx/
│   │   └── backend/
│   │       └── Dockerfile
│   └── observability/
│       ├── grafana/
│       ├── prometheus.yml
│       ├── loki-config.yaml
│       └── promtail-config.yaml
├── mobile/
│   └── flutter_app/
│       ├── android/
│       ├── ios/
│       ├── lib/
│       ├── linux/
│       ├── macos/
│       ├── web/
│       └── windows/
├── backend/
│   ├── backend/
│   ├── entrypoint.sh
│   ├── manage.py
│   └── requirements.txt
├── bots/
│   ├── customer_bot/
│   ├── courier_bot/
│   └── picker_bot/
├── shared/
└── docs/
    └── ARCHITECTURE.md

B) Target Tree V1 (структурный, безопасный)
/
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.override.yml
│   │   ├── nginx/
│   │   └── backend/
│   │       └── Dockerfile
│   └── observability/
│       ├── grafana/
│       ├── prometheus.yml
│       ├── loki-config.yaml
│       └── promtail-config.yaml
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── entrypoint.sh
│   ├── backend/        (django project: settings/urls/asgi/wsgi/celery)
│   └── apps/
│       ├── api/
│       └── main/
├── bots/
│   ├── customer_bot/
│   ├── courier_bot/
│   └── picker_bot/
├── shared/
├── mobile/
│   └── flutter_app/
└── docs/
    └── ARCHITECTURE.md

C) Target Tree V2 (архитектурная цель из ARCHITECTURE.md)
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
│       └── common/
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


Правило для V2: делаем маленькими PR. Не меняем API-контракты (эндпоинты, поля, форматы, статусы) без прямого указания. Если нужен перенос кода/моделей/urls/migrations — он допускается, но только при сохранении внешнего поведения API.

D) Таблица переноса путей (V1)
FROM	TO	Тип	Риск	Причина
backend/	backend/	backend	высокий	Django настройки/импорты и пути запуска были привязаны к старому корню.
backend/requirements.txt	backend/requirements.txt	backend	средний	Используется в Dockerfile/CI.
backend/entrypoint.sh	backend/entrypoint.sh	backend	средний	Скрипт старта Django/Celery привязан к путям.
bots/customer_bot/	bots/customer_bot/	bot	высокий	Перенос исходников бота и правки путей/импортов.
bots/customer_bot/config/blocked_ids.txt	bots/customer_bot/config/blocked_ids.txt	bot	низкий	Файл перенесён рядом с исходниками.
infra/docker/backend/Dockerfile	infra/docker/backend/Dockerfile	infra	высокий	В Dockerfile зашиты относительные пути; нужен корректный build context.
infra/docker/docker-compose.yml	infra/docker/docker-compose.yml	infra	высокий	Build/volumes/paths должны соответствовать V1.
infra/docker/docker-compose.override.yml	infra/docker/docker-compose.override.yml	infra	высокий	Влияет на локальную разработку, важно корректное merge-поведение.
infra/docker/nginx/	infra/docker/nginx/	infra	средний	Пути статики/медиа/прокси должны совпасть с V1.
infra/observability/grafana/	infra/observability/grafana/	infra	средний	Привязки datasource/дашбордов к сервисам должны остаться рабочими.
infra/observability/prometheus.yml	infra/observability/prometheus.yml	infra	средний	Scrape targets зависят от имён сервисов/портов.
infra/observability/loki-config.yaml	infra/observability/loki-config.yaml	infra	низкий	Конфиг переносится как есть, пути к логам сверить позже.
infra/observability/promtail-config.yaml	infra/observability/promtail-config.yaml	infra	низкий	Конфиг переносится как есть, пути к логам сверить позже.
app/	mobile/flutter_app/	mobile	средний	Flutter должен жить строго в mobile/flutter_app/.
docs/ARCHITECTURE.md	docs/ARCHITECTURE.md	docs	низкий	Уже на месте.

E) Порядок PR (V1 -> V2, локальные тесты последними)
V1 (структура и пути, без изменения бизнес-логики)

PR1: Создать каркас папок infra/, infra/docker/, infra/observability/, backend/, bots/customer_bot/, mobile/flutter_app/, docs/ без переносов кода.

PR2: Перенос/актуализация документации под новое дерево (папки/пути/ссылки).

PR3: Перенос Flutter в mobile/flutter_app/ и правка путей сборки/CI на новый корень.

PR4: Перенос исходников customer_bot (src/ и blocked_ids.txt) в bots/customer_bot/ + исправление импортов/entrypoint.

PR5: Перенос Django в backend/ вместе с requirements.txt и entrypoint.sh + выравнивание путей запуска.

PR6: Перенос infra-файлов в infra/docker и infra/observability + обновление путей build/volumes.

PR7: Удаление старого корня из репозитория и финальная чистка ссылок/доков под V1.

PR8: Синхронизация env-стандарта: актуализировать backend/.env.example, env_file пути, и документацию по запуску (без запуска локально).

V2 (архитектура приложений, дробим на маленькие PR)

PR9: Ввести каркас доменных приложений в backend/apps/:

создать orders/, loyalty/, notifications/, integrations/onec/, integrations/payments/, integrations/delivery/, common/

добавить пустые apps.py, __init__.py, базовую структуру, без переносов кода

PR10: Перенос кода из текущих apps/api и apps/main в доменные приложения (часть 1):

перенос только модулей/пакетов, которые не ломают импорты

добавить временные прокси-импорты (re-export), чтобы внешние импорты не упали

PR11: Перенос кода (часть 2):

перенос моделей/сервисов/тасок по доменам

сохранить миграции и их порядок (не переписывать историю)

сохранить URL/эндпоинты и сериализацию без изменений

PR12: Очистка временных прокси-импортов, финальная выверка путей и INSTALLED_APPS:

привести backend/backend/settings.py к доменным apps

убедиться, что старые импорты больше не используются

PR13: Приведение shared/ к целевому виду:

shared/dto, shared/clients, shared/config

перенос только общих структур, не ломая зависимости

Локальные тесты (только после завершения V2)

PR14 (локально, без коммита): полный прогон локальных проверок:

backend: системные проверки, миграции, запуск

celery: запуск worker/beat

bots: запуск customer_bot, courier_bot, picker_bot

flutter: flutter test / сборка

F) Чек-лист локальных проверок (делаем последним шагом)

Backend:

python backend/manage.py check

python backend/manage.py migrate

запуск сервера (docker или локально)

Celery:

запуск worker и beat, проверка что задачи подхватываются

Bots:

запуск customer_bot, courier_bot, picker_bot из новых путей

Flutter:

flutter test

при необходимости flutter build ... в mobile/flutter_app/

## Журнал выполнения V1 (проверки и изменения)

### Выполненные проверки без изменений

p.1 infra/docker/docker-compose.override.yml — изменений не потребовалось.

p.2 infra/docker/backend/Dockerfile — изменений не потребовалось.

p.3 backend/entrypoint.sh — изменений не потребовалось.

### Проверки, потребовавшие правок

p.4 согласованность nginx ↔ volumes (статика/медиа): выровнены пути статики/медиа между infra/docker/nginx/nginx.conf, infra/docker/docker-compose.yml и настройками Django (STATIC_URL/MEDIA_ROOT).

p.5 финальный rg-скан “старых следов” — совпадения только в документации/настройках, без правок кода/infra.
Найденные файлы:
- docs/REFACTOR_PLAN.md
- docs/ARCHITECTURE.md
- .gitignore

### Изменения, которые были внесены

3de976d Align media mounts with Django settings
infra/docker/docker-compose.yml и infra/docker/nginx/nginx.conf: выровнены пути/маунты media в конфигурации.

a451600 Fix Django static URL
backend/backend/settings.py: обновлено значение STATIC_URL.

### Проверки, которые выполнялись

python -m compileall backend

DJANGO_SETTINGS_MODULE=backend.settings python backend/manage.py check

rg -n --hidden --glob '!.git/**' "(infra/docker-compose\.yml|docker-compose\.override\.yml|flutter_app|mobile/app\b|app/(pubspec\.yaml|lib/|android/|ios/))" .

docker compose -f infra/docker/docker-compose.yml config — не выполнялось (docker недоступен в среде).

### Неподтверждённый гейт V1

p.6 (docker compose -f infra/docker/docker-compose.yml config) остаётся непроверенным в текущей среде.
