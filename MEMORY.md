# MEMORY.md — Long-Term Memory

## Project: lakshmi-bot
- Production loyalty program: backend (Django REST) + Telegram bots (aiogram) + Flutter app + Docker + PostgreSQL
- Owner: Василий (prefers brevity, direct communication)
- Branch: `dev`

## Architecture
- Backend: Django REST Framework, Celery (worker + beat), PostgreSQL
- Bots: aiogram 3.x — `courier_bot`, `picker_bot` (separate containers)
- App: Flutter mobile
- Infra: Docker Compose, CI on GitHub Actions
- 1C integration: `POST /onec/order/status` for status updates

## Order Status Flow (as of 2026-02-17)
`new → accepted → assembly → ready → delivery → arrived → completed` (+ `canceled`)
- Picker: `new → accepted → assembly → ready` (all orders), `ready → completed` (pickup)
- Courier: `ready → delivery → arrived → completed` (delivery)
- Notifications: new order → pickers; `ready` → couriers

## Key Files
- `bots/picker_bot/handlers/orders.py` — main picker logic
- `bots/courier_bot/` — courier bot (similar structure)
- `backend/apps/orders/models.py` — Order model with statuses
- `backend/apps/integrations/onec/order_sync.py` — 1C sync (dev stub removed)
- `docs/plans/picker-bot-spec.md` — approved spec

## Tech Debt
- `chat_cleanup.py` and `retry.py` duplicated between courier_bot and picker_bot → refactor to `shared/bot_utils/`

## Lessons
- Dev stubs that auto-advance statuses cause confusing side effects (courier notifications on order creation). Always check for dev shortcuts before debugging notification issues.
