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

## P2 — СРЕДНИЕ (6/7) ✅

> Коммит: 76ef85a

| # | Файл | Баг | Статус |
|---|------|-----|--------|
| P2-1 | `orders_pending.py:94` | GET меняет статус без подтверждения от 1С | ⏳ требует обсуждения |
| P2-2 | `order_sync.py:142` | Retry без jitter → thundering herd | ✅ |
| P2-3 | `order_sync.py:54` | Items читаются вне транзакции → stale read | ✅ |
| P2-4 | `bot_api/serializers.py:41` | `password_hash` в ответе API | ✅ |
| P2-5 | `order_sync.py:128` | `sync_idempotency_key = None` при успехе → дубли при NACK | ✅ |
| P2-6 | `backend_client.py:47` | Новая `aiohttp.ClientSession` на каждый запрос | ✅ |
| P2-7 | `courier/picker start.py` | FSM не сбрасывается при повторном `/start` | ✅ |

### P2-1: `orders_pending.py:94` — смена статуса на GET без подтверждения от 1С

**Статус:** ⏳ Отложено — требует архитектурного решения.

**Проблема:** GET-запрос меняет `status="new"` → `"assembly"`. Если 1С получит ответ, но упадёт до обработки — заказы застрянут в `assembly` навсегда.

**Варианты:**
- A) Убрать автосмену статуса, перенести в отдельный POST endpoint (1С подтверждает получение)
- B) Добавить таймаут: periodic task откатывает `assembly` → `new` если заказ в `assembly` > 10 мин и нет `onec_guid`

---

## P3 — НИЗКИЕ (7/8) ✅

> Коммит: 0824c29

| # | Файл | Баг | Статус |
|---|------|-----|--------|
| P3-1 | `product_sync.py`, `stock_sync.py` | `JsonResponse({"detail":...})` вместо `onec_error()` | ✅ |
| P3-2 | `customer_sync.py:81-95` | Тройная проверка telegram_id | ✅ |
| P3-3 | courier_bot / picker_bot | Дублирование кода между ботами | ⏳ крупный рефакторинг |
| P3-4 | `run.py`, `tasks.py` | Мёртвый код (`Registration`, `notify_couriers_new_order`) | ✅ |
| P3-5 | `orders.py`, `views.py` | `DELIVERY_RATE=150` захардкожен в двух местах | ✅ |
| P3-6 | `settings.py` | Нет `CELERY_TASK_TIME_LIMIT` | ✅ |
| P3-7 | `*/run.py` (3 бота) | Нет фильтра `chat.type == private` | ✅ |
| P3-8 | `customer_bot/broadcast.py` | Мёртвый код — дубль `shared/broadcast/` | ✅ |

### P3-3: Дублирование кода между courier_bot и picker_bot

**Статус:** ⏳ Отложено — крупный рефакторинг, требует отдельной сессии.

**Файлы:**
- `_check_access` — 3 копии (courier orders.py, toggle.py, help.py)
- `_fetch_order_with_items` — 2 копии (courier, picker)
- `_cleanup_notifications` — 3 копии (courier start.py, orders.py, picker start.py)
- `BackendClient` — 5 экземпляров в courier_bot handlers

**Фикс:** Вынести в `shared/bot_utils/`: `access.py`, `order_helpers.py`, `cleanup.py`. Создать singleton `BackendClient` на уровне бота.

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
| P2 | 7 | 6 | 1 (P2-1) |
| P3 | 8 | 7 | 1 (P3-3) |
| **Итого** | **23** | **21** | **2** |

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

1. **P2-1** — `orders_pending.py` GET меняет статус. Требует решения: отдельный POST или таймаут-откат.
2. **P3-3** — Рефакторинг дублей между courier_bot/picker_bot в `shared/bot_utils/`.

## Верификация

```bash
docker compose run --rm -w /app/backend app python manage.py test --settings=settings_test --verbosity=2
```

285 тестов — OK (проверено после каждого этапа).
