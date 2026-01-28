## Целевая структура репозитория (ориентир для V2, не текущее состояние)

```text
/
project_root/
├── README.md
├── .gitignore
├── .editorconfig
├── .env.example
├── docker-compose.yml                 # тонкий entrypoint -> включает infra/docker/*
├── docker-compose.prod.yml
├── Makefile
├── scripts/
│   ├── init_dev.sh
│   ├── migrate.sh
│   └── collectstatic.sh
│
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.override.yml
│   │   └── backend/
│   │       └── Dockerfile
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── sites/
│   │       └── backend.conf
│   ├── postgres/
│   │   └── init.sql
│   └── redis/
│       └── redis.conf
│
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── entrypoint.sh
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── apps/
│       ├── api/
│       ├── main/
│       ├── orders/
│       ├── loyalty/
│       ├── notifications/
│       ├── integrations/
│       │   ├── onec/
│       │   ├── payments/
│       │   └── delivery/
│       └── common/
│
├── bots/
│   ├── customer_bot/
│   ├── courier_bot/
│   └── picker_bot/
│
├── shared/
│   ├── dto/
│   ├── clients/
│   └── config/
│
├── mobile/
│   └── flutter_app/
│
└── docs/
    ├── ARCHITECTURE.md
    ├── REFACTOR_PLAN.md
    └── AGENT_WORKLOG.md
