# ТЗ: Round-Robin назначение курьеров

## Цель

Заменить broadcast-уведомления курьерам на автоматическое назначение через round-robin.
Курьер не "берёт" заказ — он назначается автоматически и работает только со статусами.

---

## 1. Новая модель: `CourierProfile`

**Файл:** `backend/apps/orders/models.py`

```python
class CourierProfile(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    accepting_orders = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "courier_profiles"
```

- `accepting_orders` — toggle "Принимаю/Остановить заказы"
- Профили создаются при первом `/start` курьера (или миграцией для существующих)

## 2. Новая модель: `RoundRobinCursor`

**Файл:** `backend/apps/orders/models.py`

```python
class RoundRobinCursor(models.Model):
    """Stores last assigned courier per store for fair round-robin."""
    store_id = models.IntegerField(unique=True)
    last_courier_tg_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "round_robin_cursors"
```

- `store_id` — привязка к магазину (из `Product.store_id`)
- `last_courier_tg_id` — последний назначенный курьер для этого store

> **Примечание:** Сейчас `store_id` только в `Product`. Order не имеет `store_id`. При назначении берём `store_id` из первого товара заказа (все товары одного магазина — проверяется в `order_sync.py`).

## 3. Миграция

**Файл:** `backend/apps/orders/migrations/0006_courierprofile_roundrobincursor.py`

- Создание таблиц `courier_profiles`, `round_robin_cursors`

## 4. Логика назначения: `assign_courier_to_order(order_id)`

**Файл:** `backend/apps/orders/courier_assignment.py` (новый)

```
Алгоритм:
1. Получить order, определить store_id (из первого item.product.store_id)
2. Получить список доступных курьеров:
   - CourierProfile.accepting_orders = True
   - telegram_id в settings.COURIER_ALLOWED_TG_IDS
   - Нет незавершённых заказов (Order с delivered_by=courier AND status NOT IN [completed, canceled])
3. Если список пуст → return None (заказ остаётся без курьера)
4. Round-robin:
   - Получить/создать RoundRobinCursor для store_id
   - Отсортировать доступных курьеров по telegram_id
   - Найти следующего после last_courier_tg_id
   - Если last_courier_tg_id не в списке или последний — взять первого
5. Назначить:
   - Order.delivered_by = выбранный courier.telegram_id
   - Order.save(update_fields=["delivered_by"])
   - RoundRobinCursor.last_courier_tg_id = выбранный
6. Return courier telegram_id
```

Вся логика внутри `select_for_update()` для потокобезопасности.

## 5. Celery task: `assign_courier_task(order_id)`

**Файл:** `backend/apps/notifications/tasks.py`

- Вызывает `assign_courier_to_order(order_id)`
- Если назначен → отправляет уведомление **только этому курьеру** (не broadcast)
- Если не назначен → логирует, заказ ждёт redispatch

## 6. Celery task: `redispatch_unassigned_orders`

**Файл:** `backend/apps/notifications/tasks.py`

- Celery beat: каждые 2 минуты
- Находит заказы: `status=ready`, `fulfillment_type=delivery`, `delivered_by=None`
- Для каждого вызывает `assign_courier_to_order()`
- Страховка на случай, если в момент `ready` все курьеры были заняты

## 7. Event-driven redispatch

При следующих событиях запускать попытку назначения нераспределённых заказов:

### 7a. Курьер завершил доставку (`completed`)

**Файл:** `backend/apps/integrations/onec/order_status.py`

После `status → completed`: если есть unassigned ready-заказы → `assign_courier_task.delay()`

### 7b. Курьер включил "Принимаю заказы"

**Файл:** новый API endpoint `POST /api/bot/courier/toggle-accepting/`

После toggle на `True`: если есть unassigned ready-заказы → `assign_courier_task.delay()`

### 7c. Заказ перешёл в `ready`

**Файл:** `backend/apps/orders/signals.py`

Заменить `notify_couriers_new_order.delay(oid)` → `assign_courier_task.delay(oid)`

## 8. Изменения в `onec/order_status.py`

- При `completed`: trigger redispatch
- Убрать прямой вызов `notify_couriers_new_order` (заменён на assign)

## 9. Изменения в `signals.py`

- `ready` + delivery → `assign_courier_task.delay(oid)` вместо `notify_couriers_new_order.delay(oid)`

## 10. Новый API endpoint: toggle accepting

**Endpoint:** `POST /api/bot/courier/toggle-accepting/`

```json
Request:  {"courier_tg_id": 123456, "accepting": true}
Response: {"accepting_orders": true}
```

## 11. Новый API endpoint: courier profile

**Endpoint:** `GET /api/bot/courier/profile/?courier_tg_id=<int>`

```json
Response: {"telegram_id": 123456, "accepting_orders": true}
```

## 12. Изменения в courier_bot

### 12a. Убрать `/orders` как "все ready-заказы"

Сейчас `/orders` показывает ВСЕ `ready/delivery/arrived` заказы.
Заменить: показывать только **мои** заказы (где `delivered_by = мой tg_id`).

### 12b. Новая команда/кнопка: toggle "Принимаю заказы" / "Остановить заказы"

- Команда `/toggle` или inline-кнопка в `/start`
- Вызывает `POST /api/bot/courier/toggle-accepting/`
- Показывает текущий статус

### 12c. Убрать логику "взять заказ"

Курьер НЕ берёт заказ. Кнопка "🚗 Забрал заказ" (ready→delivery) остаётся — это смена статуса, не взятие.

### 12d. Уведомления

Курьер получает уведомление только о назначенном ему заказе (не broadcast).

## 13. Изменения в `ActiveOrdersView`

**Файл:** `backend/apps/bot_api/views.py`

Добавить фильтр `courier_tg_id`:
```
GET /api/bot/orders/active/?courier_tg_id=<int>
```
Возвращать только заказы где `delivered_by = courier_tg_id` (+ ready с delivered_by=courier_tg_id).

## 14. Изменения в `BackendClient`

**Файл:** `shared/clients/backend_client.py`

- `get_active_orders(courier_tg_id)` — добавить параметр
- `get_courier_profile(courier_tg_id)` — новый
- `toggle_accepting(courier_tg_id, accepting)` — новый

## 15. Celery beat schedule

**Файл:** `backend/config/settings.py` (или где beat schedule)

```python
CELERY_BEAT_SCHEDULE["redispatch-unassigned"] = {
    "task": "apps.notifications.tasks.redispatch_unassigned_orders",
    "schedule": 120.0,  # каждые 2 мин
}
```

---

## Изменяемые файлы (сводка)

### Backend
| Файл | Действие |
|---|---|
| `apps/orders/models.py` | + `CourierProfile`, `RoundRobinCursor` |
| `apps/orders/migrations/0006_*` | Новая миграция |
| `apps/orders/courier_assignment.py` | **Новый** — логика round-robin |
| `apps/notifications/tasks.py` | + `assign_courier_task`, `redispatch_unassigned_orders`; рефакторинг `notify_couriers_new_order` |
| `apps/integrations/onec/order_status.py` | + redispatch при `completed` |
| `apps/orders/signals.py` | `notify_couriers → assign_courier_task` |
| `apps/bot_api/views.py` | + `CourierToggleView`, `CourierProfileView`; изменить `ActiveOrdersView` |
| `apps/bot_api/urls.py` | + 2 новых маршрута |
| `apps/bot_api/serializers.py` | + сериализаторы для courier profile |
| `shared/clients/backend_client.py` | + новые методы |
| `config/settings.py` | + celery beat schedule |

### Courier Bot
| Файл | Действие |
|---|---|
| `handlers/orders.py` | Рефакторинг: мои заказы вместо всех |
| `handlers/start.py` | + toggle кнопка |
| `keyboards.py` | + toggle keyboard |
| `run.py` | + команда `/toggle` |

---

## Что НЕ входит в этот таск

- Лимит 3 заказа для сборщика (отдельная задача)
- Изменения в picker_bot
- Изменения в Flutter app
