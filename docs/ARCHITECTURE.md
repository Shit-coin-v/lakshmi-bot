/
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.override.yml
│   │   ├── nginx/
│   │   │   ├── Dockerfile
│   │   │   └── nginx.conf
│   │   └── backend/
│   │       └── Dockerfile
│   └── observability/
│       ├── grafana/
│       ├── prometheus.yml
│       ├── loki-config.yaml
│       └── promtail-config.yaml
│
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── entrypoint.sh
│   ├── backend/                 # Django project (settings, urls, celery)
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── celery.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── apps/
│       ├── api/                  # legacy API layer (V1, будет разобран в V2)
│       ├── main/                 # legacy core (V1, будет разобран в V2)
│       ├── orders/
│       ├── loyalty/
│       ├── notifications/
│       ├── integrations/
│       │   ├── onec/
│       │   ├── payments/
│       │   └── delivery/
│       └── common/               # shared backend utils (без бизнес-логики)
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
