# ТЗ: Оплата по СБП через ЮKassa

## Цель

Добавить третий способ оплаты — СБП через ЮKassa. Предоплата при оформлении заказа.
Деньги резервируются (hold), списываются (capture) после нажатия курьером "Доставлено".
При отмене заказа — автоматический возврат (refund/cancel).

---

## Бизнес-логика

### Успешный сценарий

1. Клиент выбирает СБП в приложении → нажимает "Оформить"
2. Backend создаёт платёж в ЮKassa (`payment.create`, `capture=false`)
3. ЮKassa возвращает `confirmation_url` (ссылка на оплату СБП)
4. Приложение открывает `confirmation_url` (WebView/deeplink)
5. Клиент оплачивает в банковском приложении
6. ЮKassa шлёт webhook → `payment.succeeded` → статус платежа = `waiting_for_capture`
7. Backend создаёт заказ со статусом `new` + `payment_status=authorized`
8. Заказ проходит обычный цикл: сборщик → курьер
9. Курьер нажимает "Доставлено" → backend делает `capture` в ЮKassa
10. Деньги списаны. Цикл завершён.

### Отмена

- Заказ отменяется (клиент/сборщик/любой этап до capture) → backend делает `cancel` платежа в ЮKassa → деньги возвращаются клиенту

### Таймаут

- Если клиент не оплатил в течение **15 минут** → платёж автоматически отменяется ЮKassa
- Заказ не создаётся (или помечается `payment_failed`)

---

## Архитектура

### Поток данных

```
Flutter App          Backend                    ЮKassa
    |                   |                         |
    |-- POST /orders/create/ (payment=sbp) -->    |
    |                   |-- POST /payments -->     |
    |                   |<-- confirmation_url --   |
    |<-- confirmation_url --|                      |
    |-- user pays in bank app -->                  |
    |                   |<-- webhook (succeeded) --|
    |                   |-- create Order (new) --> |
    |<-- order created --|                         |
    |                   |                          |
    |   ... order lifecycle ...                    |
    |                   |                          |
    |   courier: "Доставлено"                      |
    |                   |-- POST capture -------->|
    |                   |<-- captured ------------|
```

---

## 1. Настройки

**Файл:** `backend/settings.py`

```python
YUKASSA_SHOP_ID = os.getenv("YUKASSA_SHOP_ID", "")
YUKASSA_SECRET_KEY = os.getenv("YUKASSA_SECRET_KEY", "")
YUKASSA_WEBHOOK_SECRET = os.getenv("YUKASSA_WEBHOOK_SECRET", "")  # для верификации
YUKASSA_RETURN_URL = os.getenv("YUKASSA_RETURN_URL", "")  # deeplink/URL возврата в приложение
```

**Файл:** `.env.example` — добавить переменные

---

## 2. Новые поля в Order

**Файл:** `backend/apps/orders/models.py`

```python
# --- Оплата ---
payment_id = models.CharField(max_length=64, null=True, blank=True, db_index=True,
                              verbose_name="ID платежа ЮKassa")
payment_status = models.CharField(max_length=20, default="none",
    choices=[
        ("none", "Нет онлайн-оплаты"),
        ("pending", "Ожидает оплаты"),
        ("authorized", "Авторизован (hold)"),
        ("captured", "Списан"),
        ("canceled", "Отменён"),
        ("failed", "Ошибка"),
    ],
    verbose_name="Статус платежа")
```

Миграция: `0007_order_payment_fields.py`

---

## 3. ЮKassa клиент

**Файл:** `backend/apps/integrations/payments/yukassa_client.py` (новый)

Используем библиотеку `yookassa` (официальный SDK) или raw HTTP.

Методы:
- `create_payment(amount, description, order_metadata, return_url)` → `{payment_id, confirmation_url}`
- `capture_payment(payment_id, amount)` → `{status}`
- `cancel_payment(payment_id)` → `{status}`
- `get_payment(payment_id)` → `{status, ...}`

---

## 4. Изменения в OrderCreateView / OrderCreateSerializer

**Файл:** `backend/apps/orders/views.py`, `serializers.py`

Для `payment_method == "sbp"`:
1. Валидация проходит как обычно
2. Заказ создаётся со статусом `new` + `payment_status=pending`
3. Вызываем `create_payment()` в ЮKassa (amount=total_price, capture=false)
4. Сохраняем `payment_id` в заказе
5. Возвращаем клиенту `{order_id, confirmation_url}`
6. Заказ **НЕ отправляется в 1С** пока не получим webhook об успешной оплате
7. Уведомления сборщикам **НЕ отправляются** пока `payment_status != authorized`

Для `cash` / `card_courier` — без изменений (как сейчас).

---

## 5. Webhook endpoint

**Файл:** `backend/apps/integrations/payments/webhook.py` (новый)

**URL:** `POST /payments/webhook/`

Обработка событий ЮKassa:

### `payment.waiting_for_capture`
- Найти заказ по `payment_id`
- `payment_status` → `authorized`
- Отправить заказ в 1С (`send_order_to_onec.delay`)
- Уведомить сборщиков (`notify_pickers_new_order.delay`)
- Push клиенту: "Оплата прошла, заказ принят"

### `payment.canceled`
- Найти заказ по `payment_id`
- `payment_status` → `canceled`
- `status` → `canceled`
- Push клиенту: "Оплата не прошла, заказ отменён"

### Безопасность
- Проверка IP ЮKassa (185.71.76.0/27, 185.71.77.0/27) или HTTP Basic Auth

---

## 6. Capture при "Доставлено"

**Файл:** `backend/apps/integrations/onec/order_status.py`

При `status → completed`:
- Если `payment_status == "authorized"` и `payment_id` → вызвать `capture_payment()`
- `payment_status` → `captured`
- Если capture не удался → лог + retry (Celery task)

---

## 7. Refund при отмене

**Файл:** `backend/apps/orders/views.py` (`OrderCancelView`)

При отмене заказа:
- Если `payment_status == "authorized"` → `cancel_payment()` (отмена hold)
- Если `payment_status == "captured"` → `refund_payment()` (возврат)
- `payment_status` → `canceled`

Также в `onec/order_status.py` при `status → canceled`.

---

## 8. Celery tasks

**Файл:** `backend/apps/integrations/payments/tasks.py` (новый)

- `capture_payment_task(order_id)` — capture с retry
- `cancel_payment_task(order_id)` — cancel/refund с retry
- `expire_pending_payments` — Celery beat (каждые 5 мин): найти заказы с `payment_status=pending` старше 15 мин → отменить

---

## 9. Flutter — изменения

**Файл:** `cart_screen.dart`

- Добавить третий RadioButton: "📱 СБП" (value: `sbp`)
- После `createOrder` с `sbp`: получить `confirmation_url` из ответа
- Открыть `confirmation_url` через `url_launcher` (банковское приложение)
- После возврата — поллить статус заказа или ждать push

**Файл:** `order_service.dart`

- `createOrder` возвращает `{order_id, confirmation_url?}`

**Файл:** `order_details_screen.dart`

- Показывать `payment_status` (badge "Оплачен" / "Ожидает оплаты")

---

## 10. Зависимости

**Файл:** `backend/requirements.txt`

```
yookassa>=3.0.0
```

---

## Изменяемые файлы (сводка)

### Backend
| Файл | Действие |
|---|---|
| `orders/models.py` | + `payment_id`, `payment_status` |
| `orders/migrations/0007_*` | Новая миграция |
| `orders/serializers.py` | `OrderCreateSerializer` — возврат `confirmation_url` для sbp |
| `orders/views.py` | `OrderCreateView` — логика sbp; `OrderCancelView` — refund |
| `integrations/payments/yukassa_client.py` | **Новый** — клиент ЮKassa |
| `integrations/payments/webhook.py` | **Новый** — webhook обработчик |
| `integrations/payments/tasks.py` | **Новый** — capture/cancel/expire tasks |
| `integrations/onec/order_status.py` | + capture при completed, cancel при canceled |
| `notifications/tasks.py` | Пикер-уведомление для sbp — только после authorized |
| `settings.py` | + YUKASSA_* настройки |
| `urls.py` | + `/payments/webhook/` |
| `.env.example` | + YUKASSA_* |

### Flutter
| Файл | Действие |
|---|---|
| `cart_screen.dart` | + СБП radio button, open confirmation_url |
| `order_service.dart` | Парсинг confirmation_url из ответа |
| `order_details_screen.dart` | Бейдж оплаты |

---

## Что НЕ входит

- Оплата картой онлайн (только СБП)
- Рекуррентные платежи
- Чеки (54-ФЗ) — ЮKassa может генерить автоматически, но настройка отдельно
