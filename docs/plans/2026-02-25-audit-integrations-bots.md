# Аудит: Интеграции + Боты + Celery/Сигналы

**Дата:** 2026-02-25
**Scope:** `backend/apps/integrations/`, `bots/`, `backend/apps/notifications/tasks.py`, `backend/apps/common/security.py`, `shared/`

---

## P0 — КРИТИЧЕСКИЕ ✅

> Коммиты: 74ce802, 5b7a5ae, 7ba638c, f03af69

| # | Файл | Баг | Статус |
|---|------|-----|--------|
| 1 | `notifications/signals.py:19` | `delay()` без `transaction.on_commit` → `DoesNotExist` в Celery | ✅ |
| 2 | `payments/webhook.py:115` + `push.py` | Push при SBP-авторизации не работал (`"new","new"` = no-op + нет `"new"` в `_STATUS_MESSAGES`) | ✅ |
| 3 | `payments/tasks.py:288` | `expire_pending_payments` — bulk `.update()` без push клиенту | ✅ |
| 4 | `common/security.py:22` | IP spoofing через `X-Forwarded-For[0]` (nginx append → нужен `[-1]`) | ✅ |
| 5 | `payments/webhook.py:112-115` | `on_commit` вне `atomic()` блока | ✅ |

---

## P1 — ВЫСОКИЕ ✅

> Коммит: 709c79e

| # | Файл | Баг | Статус |
|---|------|-----|--------|
| P1-1 | `order_sync.py:133-139` | `MaxRetriesExceededError` не ловится → `sync_status` навсегда `"queued"` | ✅ |
| P1-2 | `order_create.py` | Endpoint-заглушка, `onec_guid` не сохраняется в БД | ✅ |
| P1-3 | `tasks.py:153,254` | `order.address` в `parse_mode=HTML` без `html.escape()` → Telegram отклоняет | ✅ |

### P1-1: `order_sync.py` — `sync_status` зависает в `queued` после max_retries

**Фикс:** Проверка `self.request.retries >= self.max_retries` перед `self.retry()`, вызов `_fail_order()` при исчерпании попыток.

### P1-2: `order_create.py` — endpoint-заглушка, `onec_guid` не сохраняется

**Фикс:** Получаем `Order` из БД, сохраняем `onec_guid` + ставим `sync_status="confirmed"`. 404 если заказ не найден.

### P1-3: HTML injection в Telegram-сообщениях → уведомления не доставляются

**Фикс:** `html.escape()` для `order.address` в `notify_pickers_new_order` и `send_courier_notification_task`. Birthday messages не затронуты (plain text, без `parse_mode=HTML`).

---

## P2 — СРЕДНИЕ (7/7) ✅

> Коммит: 76ef85a

| # | Файл | Баг | Статус |
|---|------|-----|--------|
| P2-1 | `orders_pending.py:94` | GET меняет статус без подтверждения от 1С | ✅ periodic rollback |
| P2-2 | `order_sync.py:142` | Retry без jitter → thundering herd | ✅ |
| P2-3 | `order_sync.py:54` | Items читаются вне транзакции → stale read | ✅ |
| P2-4 | `bot_api/serializers.py:41` | `password_hash` в ответе API | ✅ |
| P2-5 | `order_sync.py:128` | `sync_idempotency_key = None` при успехе → дубли при NACK | ✅ |
| P2-6 | `backend_client.py:47` | Новая `aiohttp.ClientSession` на каждый запрос | ✅ |
| P2-7 | `courier/picker start.py` | FSM не сбрасывается при повторном `/start` | ✅ |

### P2-1: `orders_pending.py:94` — смена статуса на GET без подтверждения от 1С

**Статус:** ✅ Решено (вариант B — periodic rollback task).

**Проблема:** GET-запрос меняет `status="new"` → `"assembly"`. Если 1С получит ответ, но упадёт до обработки — заказы застрянут в `assembly` навсегда.

**Фикс:** Periodic task `rollback_stuck_assembly_orders` (каждые 5 мин) — откатывает заказы в `assembly` без `onec_guid` старше 10 мин обратно в `new`. Зарегистрирован в `celeryapp.py` beat_schedule.

---

## P3 — НИЗКИЕ (8/8) ✅

> Коммит: 0824c29

| # | Файл | Баг | Статус |
|---|------|-----|--------|
| P3-1 | `product_sync.py`, `stock_sync.py` | `JsonResponse({"detail":...})` вместо `onec_error()` | ✅ |
| P3-2 | `customer_sync.py:81-95` | Тройная проверка telegram_id | ✅ |
| P3-3 | courier_bot / picker_bot | Дублирование кода между ботами | ✅ shared/bot_utils/ |
| P3-4 | `run.py`, `tasks.py` | Мёртвый код (`Registration`, `notify_couriers_new_order`) | ✅ |
| P3-5 | `orders.py`, `views.py` | `DELIVERY_RATE=150` захардкожен в двух местах | ✅ |
| P3-6 | `settings.py` | Нет `CELERY_TASK_TIME_LIMIT` | ✅ |
| P3-7 | `*/run.py` (3 бота) | Нет фильтра `chat.type == private` | ✅ |
| P3-8 | `customer_bot/broadcast.py` | Мёртвый код — дубль `shared/broadcast/` | ✅ |

### P3-3: Дублирование кода между courier_bot и picker_bot

**Статус:** ✅ Готово.

**Что сделано:**
- `shared/bot_utils/access.py` — `check_staff_access(backend, telegram_id, role)`
- `shared/bot_utils/order_helpers.py` — `fetch_order_with_items()`, `to_order_namespace()`
- `shared/bot_utils/notifications.py` — `cleanup_notifications(backend, bot, chat_id, telegram_id, role)`
- Singleton `BackendClient` в `courier_bot/config.py` и `picker_bot/config.py`
- Все handlers обоих ботов обновлены на shared-импорты

### P3-4: Мёртвый код — детали

| Файл | Код | Статус |
|------|-----|--------|
| `customer_bot/run.py:80-81` | `class Registration(StatesGroup): pass` — не используется | ✅ удалён |
| `notifications/tasks.py:201-205` | `notify_couriers_new_order` — deprecated, 0 callers | ✅ удалён |
| `order_sync.py:104` | `os.getenv("INTEGRATION_API_KEY")` — исходящий HTTP-заголовок, не дубль | — не баг |

---

## Сводка

| Приоритет | Всего | Готово | Осталось |
|-----------|-------|--------|----------|
| P0 | 5 | 5 | 0 |
| P1 | 3 | 3 | 0 |
| P2 | 7 | 7 | 0 |
| P3 | 8 | 8 | 0 |
| **Итого** | **23** | **23** | **0** |

## Коммиты

| Коммит | Описание |
|--------|----------|
| `74ce802` | fix: wrap notification signal delay() in transaction.on_commit |
| `5b7a5ae` | fix: payment authorization push — add "new" status, correct previous_status |
| `7ba638c` | fix: expire_pending_payments — send push on timeout cancellation |
| `f03af69` | fix: XFF IP spoofing — use last IP from X-Forwarded-For |
| `709c79e` | fix: P1 audit — sync_status fail handler, order_create stub, HTML escape |
| `76ef85a` | fix: P2 audit — reliability and security improvements |
| `0824c29` | fix: P3 audit — code quality and operational improvements |

## Оставшиеся задачи

Все 23 задачи выполнены.

## Верификация

```bash
docker compose run --rm -w /app/backend app python manage.py test --settings=settings_test --verbosity=2
```

285 тестов — OK (проверено после каждого этапа).
