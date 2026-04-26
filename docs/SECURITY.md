# Безопасность Lakshmi Bot

## Авторизация

В проекте используется 4 разделённых механизма (см. `CLAUDE.md`):

- **`@require_onec_auth`** — для `/onec/*` (от 1C). `X-Api-Key` + IP whitelist (`ONEC_ALLOW_IPS`). 401 при ошибке.
- **`ApiKeyPermission`** — service-to-service (push, SendMessage). `X-Api-Key`. 403 при ошибке.
- **`TelegramUserPermission`** — клиентские endpoints из ботов. `X-Telegram-User-Id`. 403 при ошибке.
- **JWT** (PyJWT, HS256) — мобильное приложение. `Authorization: Bearer <token>`. 401 при ошибке.

HMAC не используется. Не вводить HMAC/подписи без явного согласования.

## Pre-commit hook

Защита от случайного коммита секретов и крупных файлов.

```bash
pip install pre-commit
pre-commit install
```

Hook'и:
- `gitleaks` — сканер секретов (API-ключи, токены, приватные ключи).
- `detect-private-key` — RSA/EC/SSH-ключи.
- `check-added-large-files` — блок файлов больше 500 KB.
- `ruff` — линтер Python для `backend/`, `bots/`, `shared/`.

Запуск вручную: `pre-commit run --all-files`.

## Чеклист ротации секретов

Если секрет утёк (закоммичен, отправлен в Slack/email/Issue), **ротируйте его ПЕРВЫМ ДЕЛОМ**, потом чистите репозиторий.

| Секрет | Где ротировать | Как |
|--------|----------------|-----|
| `BOT_TOKEN`, `COURIER_BOT_TOKEN`, `PICKER_BOT_TOKEN` | @BotFather | `/revoke` → `/token` |
| `OPENAI_API_KEY` | platform.openai.com/api-keys | Revoke + Create new |
| `EMAIL_HOST_PASSWORD` (Yandex) | Yandex.Passport → Пароли приложений | Revoke + Create |
| `SECRET_KEY` (Django) | Локально | `python -c "import secrets; print(secrets.token_urlsafe(50))"`. **Внимание:** ротация инвалидирует все JWT, сессии и CSRF-токены — все клиенты будут разлогинены. |
| `INTEGRATION_API_KEY`, `ONEC_API_KEY` | Согласовать с 1C-командой | Контрагентский ключ |
| `YUKASSA_SECRET_KEY` | Личный кабинет ЮKassa | API-ключи → пересоздать |
| `POSTGRES_PASSWORD` | psql + `.env` + рестарт | `ALTER USER lakshmi WITH PASSWORD '...';` затем `docker compose restart app celery_worker celery_beat` |
| `REDIS_PASSWORD` | `.env` + рестарт redis | Обновить `CELERY_BROKER_URL` тоже |
| `FIREBASE_SERVICE_ACCOUNT_*` | Firebase Console | Project Settings → Service accounts → Generate new key |
| `GRAFANA_ADMIN_PASSWORD` | `.env` + рестарт | `docker compose restart grafana` |

После ротации:
1. Обновить значения в `.env` всех окружений (dev / staging / prod).
2. Применить — `docker compose restart` для затронутых сервисов.
3. Проверить, что приложение работает (login flow, push, оплата).

## Если секрет случайно закоммичен

1. **Ротируй сейчас** (см. чеклист выше). Любая чистка истории — после.
2. Удали из истории: `git filter-repo --path <file> --invert-paths` (или `git filter-branch`, если `git-filter-repo` не установлен).
3. `git push --force` на все ветки и теги (предупреди команду заранее).
4. Удали кеши форков, если репо публичный (GitHub автоматически чистит после ~30 дней, но злоумышленник мог уже забрать).
5. Помни: данные могут быть закешированы у внешних индексаторов (Wayback Machine, GitHub Archive). Ротация — единственная гарантия.

## Что НЕ коммитить

- `.env` и `.env.*` (защищено `.gitignore`)
- `backend/firebase_service_account.json`
- `*.pem`, `*.p12`, `*.pfx`, `*.key` (RSA/SSL/SSH-ключи)
- Дампы БД (`*.sql`, `*.sql.gz`)
- Бэкапы со связками email+пароль
- API-ключи в коде и комментариях
- Логи с PII (телефоны, email, адреса)

## Рекомендации

- В CI добавить `pip-audit -r backend/requirements.txt` для регулярной проверки CVE.
- Для photo-studio — `npm audit` в CI.
- Включить branch protection на `main`/`dev`: required reviews, required status checks, no force-push.
- Логировать только идемпотентные ID (`order_id`, `payment_id`, `customer_id`), не PII (`phone`, `email`, `full_name`).

## Контакт по инцидентам

Подозрение на утечку — немедленно:
1. Ротация (см. выше).
2. Аудит логов: `docker compose logs --since 7d | grep -iE 'secret|password|token'` (внимательно — это сами по себе чувствительные данные).
3. Уведомить ответственного за инфру.
