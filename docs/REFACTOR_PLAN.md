# План рефакторинга: перенос директорий

## A) Текущее дерево (2 уровня)
```
/
├── AGENTS.md
├── backend/
├── bots/
│   ├── customer_bot/
│   ├── courier_bot/
│   └── picker_bot/
├── docs/
├── infra/
├── mobile/
└── shared/
```

## B) Целевое дерево (кратко) из ARCHITECTURE.md
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
```

## C) Таблица переноса путей
`legacy_root/` — исторический корень до переноса, сейчас удалён.
| FROM (legacy_root) | TO | Тип | Риск | Причина |
| --- | --- | --- | --- | --- |
| `legacy_root/backend/` | `backend/` | backend | высокий | **ВЫПОЛНЕНО в dev**. Django настройки и импорты привязаны к прежним путям, плюс manage.py расположение в docker-compose. |
| `legacy_root/requirements.txt` | `backend/requirements.txt` | backend | средний | **ВЫПОЛНЕНО в dev**. Путь зависимостей используется в Dockerfile и CI. |
| `legacy_root/entrypoint.sh` | `backend/entrypoint.sh` | backend | средний | **ВЫПОЛНЕНО в dev**. Скрипт стартует Django/Celery; жёстко привязан к путям. |
| `legacy_root/src/` | `bots/customer_bot/` | bot | высокий | **ВЫПОЛНЕНО в dev**. Импорты и файлы данных перенесены в новый корень бота. |
| `legacy_root/blocked_ids.txt` | `bots/customer_bot/config/blocked_ids.txt` | bot | низкий | **ВЫПОЛНЕНО в dev**. Файл перенесён рядом с исходниками бота. |
| `legacy_root/Dockerfile` | `infra/docker/backend/Dockerfile` | infra | высокий | **ВЫПОЛНЕНО (PR6)**. В Dockerfile зашиты относительные пути к исходникам; нужен апдейт контекста. |
| `legacy_root/docker-compose.yml` | `infra/docker/docker-compose.yml` | infra | высокий | **ВЫПОЛНЕНО (PR6)**. Содержит volume-пути и build-контексты на старые директории. |
| `legacy_root/docker-compose.override.yml` | `infra/docker/docker-compose.override.yml` | infra | высокий | **ВЫПОЛНЕНО (PR6)**. Дублирует пути, влияет на локальную разработку. |
| `legacy_root/nginx/` | `infra/docker/nginx/` | infra | средний | **ВЫПОЛНЕНО (PR6)**. Конфиги nginx завязаны на пути статики и сокетов. |
| `legacy_root/grafana/` | `infra/observability/grafana/` | infra | средний | **ВЫПОЛНЕНО (PR6)**. Дашборды/конфиги ссылаются на источники; нужно проверить пути. |
| `legacy_root/prometheus.yml` | `infra/observability/prometheus.yml` | infra | средний | **ВЫПОЛНЕНО (PR6)**. Путь к scrape targets требует обновления после переноса. |
| `legacy_root/loki-config.yaml` | `infra/observability/loki-config.yaml` | infra | низкий | **ВЫПОЛНЕНО (PR6)**. Файл конфигурации, пути к логам нужно сверить. |
| `legacy_root/promtail-config.yaml` | `infra/observability/promtail-config.yaml` | infra | низкий | **ВЫПОЛНЕНО (PR6)**. Путь к логам и docker labels может потребовать правок. |
| `docs/backend/README.md` | `docs/backend/README.md` | docs | низкий | **ВЫПОЛНЕНО в dev**. Документация перенесена из старого корня бэкенда без изменений. |
| `app/` | `mobile/flutter_app/` | mobile | средний | Выполнено: Flutter-проект перенесён, CI/скрипты теперь должны использовать путь `mobile/flutter_app/`. |
| `docs/ARCHITECTURE.md` | `docs/ARCHITECTURE.md` | docs | низкий | Уже на месте; перенос не требуется, но остаётся в репозитории. |

## D) Порядок PR (минимально безопасные шаги)
1. **PR1**: Создать каркас папок `infra/`, `infra/docker/`, `infra/observability/`, `backend/`, `bots/customer_bot/`, `mobile/flutter_app/`, `docs/backend/` с `.gitkeep`, не перемещая код.
2. **PR2 (выполнено)**: Документация перенесена в `docs/backend/`; ссылки в документах обновлены.
3. **PR3 (выполнено)**: Flutter-проект перенесён в `mobile/flutter_app/`, пути сборки/CI обновлены на новый корень.
4. **PR4 (выполнено)**: Перенести исходники бота `legacy_root/src/` + `blocked_ids.txt` в `bots/customer_bot/`, поправить импорт-пути и entrypoint.
5. **PR5 (выполнено)**: Перенести Django код из `legacy_root/` в `backend/` вместе с `requirements.txt` и `entrypoint.sh`, обновить зависимые пути и конфигурацию.
6. **PR6 (выполнено)**: Перенести инфраструктурные файлы из `legacy_root/` (`Dockerfile`, `docker-compose*.yml`, `nginx/`, `grafana/`, `prometheus.yml`, `loki-config.yaml`, `promtail-config.yaml`) в `infra/` и обновить пути сборки/volume, после чего проверить запуск через docker-compose.
7. **PR7 (выполнено)**: Удаление legacy директории `legacy_root/` из репозитория и актуализация документации по текущему дереву.

## E) Чек-лист проверок после каждого PR
- Backend запускается: `python manage.py check` / запуск dev-сервера.
- Celery стартует (если используется): `celery -A <project> worker -l info`.
- Бот стартует: команда/entrypoint запуска бота в новом пути.
- Flutter собирается: `flutter test` / `flutter build` в `mobile/flutter_app/` (если применимо).
