# План рефакторинга: перенос директорий

## A) Текущее дерево (2 уровня)
```
/
├── app/
│   ├── android/
│   ├── ios/
│   ├── lib/
│   ├── linux/
│   ├── macos/
│   ├── web/
│   └── windows/
├── backend_bot/
│   ├── backend/
│   ├── grafana/
│   ├── nginx/
│   ├── src/
│   ├── Dockerfile
│   ├── README.md
│   ├── blocked_ids.txt
│   ├── docker-compose.override.yml
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   ├── loki-config.yaml
│   ├── promtail-config.yaml
│   └── prometheus.yml
└── docs/
    └── ARCHITECTURE.md
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
│   └── support_bot/
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
| FROM | TO | Тип | Риск | Причина |
| --- | --- | --- | --- | --- |
| `backend_bot/backend/` | `backend/` | backend | высокий | Django настройки и импорты привязаны к прежним путям, плюс manage.py расположение в docker-compose. |
| `backend_bot/requirements.txt` | `backend/requirements.txt` | backend | средний | Путь зависимостей используется в Dockerfile и CI. |
| `backend_bot/entrypoint.sh` | `backend/entrypoint.sh` | backend | средний | Скрипт стартует Django/Celery; жёстко привязан к путям. |
| `backend_bot/src/` | `bots/customer_bot/` | bot | высокий | Импорты и файлы данных (blocked_ids.txt) могут быть указаны относительными путями; потребуется обновление entrypoint. |
| `backend_bot/blocked_ids.txt` | `bots/customer_bot/config/blocked_ids.txt` | bot | низкий | Используется ботом как файл данных; потребуется обновить путь загрузки. |
| `backend_bot/Dockerfile` | `infra/docker/backend/Dockerfile` | infra | высокий | В Dockerfile зашиты относительные пути к исходникам; нужен апдейт контекста. |
| `backend_bot/docker-compose.yml` | `infra/docker/docker-compose.yml` | infra | высокий | Содержит volume-пути и build-контексты на старые директории. |
| `backend_bot/docker-compose.override.yml` | `infra/docker/docker-compose.override.yml` | infra | высокий | Дублирует пути, влияет на локальную разработку. |
| `backend_bot/nginx/` | `infra/docker/nginx/` | infra | средний | Конфиги nginx завязаны на пути статики и сокетов. |
| `backend_bot/grafana/` | `infra/observability/grafana/` | infra | средний | Дашборды/конфиги ссылаются на источники; нужно проверить пути. |
| `backend_bot/prometheus.yml` | `infra/observability/prometheus.yml` | infra | средний | Путь к scrape targets требует обновления после переноса. |
| `backend_bot/loki-config.yaml` | `infra/observability/loki-config.yaml` | infra | низкий | Файл конфигурации, пути к логам нужно сверить. |
| `backend_bot/promtail-config.yaml` | `infra/observability/promtail-config.yaml` | infra | низкий | Путь к логам и docker labels может потребовать правок. |
| `backend_bot/README.md` | `docs/backend/README.md` | docs | низкий | Только документация, перенос без изменения содержимого. |
| `app/` | `mobile/flutter_app/` | mobile | средний | Сборочные скрипты и CI ищут проект в корне `app`; нужно обновить пути. |
| `docs/ARCHITECTURE.md` | `docs/ARCHITECTURE.md` | docs | низкий | Уже на месте; перенос не требуется, но остаётся в репозитории. |

## D) Порядок PR (минимально безопасные шаги)
1. **PR1**: Создать каркас папок `infra/`, `infra/docker/`, `infra/observability/`, `backend/`, `bots/customer_bot/`, `mobile/flutter_app/`, `docs/backend/` с `.gitkeep`, не перемещая код.
2. **PR2**: Перенести иерархию документации (`backend_bot/README.md`) в `docs/backend/`; убедиться, что ссылки в документах обновлены.
3. **PR3**: Перенести Flutter-проект `app/` в `mobile/flutter_app/` и обновить CI/скрипты сборки (пути к `flutter`).
4. **PR4**: Перенести исходники бота `backend_bot/src/` + `blocked_ids.txt` в `bots/customer_bot/`, поправить импорт-пути и entrypoint.
5. **PR5**: Перенести Django код `backend_bot/backend/` и вспомогательные файлы (`requirements.txt`, `entrypoint.sh`) в `backend/`, обновить импорты, manage.py пути и Celery конфигурацию.
6. **PR6**: Перенести инфраструктурные файлы (`Dockerfile`, `docker-compose*.yml`, `nginx/`, `grafana/`, `prometheus.yml`, `loki-config.yaml`, `promtail-config.yaml`) в `infra/` и обновить пути сборки/volume, после чего проверить запуск через docker-compose.

## E) Чек-лист проверок после каждого PR
- Backend запускается: `python manage.py check` / запуск dev-сервера.
- Celery стартует (если используется): `celery -A <project> worker -l info`.
- Бот стартует: команда/entrypoint запуска бота в новом пути.
- Flutter собирается: `flutter test` / `flutter build` в `mobile/flutter_app/` (если применимо).
