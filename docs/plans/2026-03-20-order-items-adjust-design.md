# Order Items Adjust — Backend Design v3

## Назначение

Эндпоинт для 1С: уменьшение количества или удаление позиций заказа в статусе `assembly`.
Сценарий: сборщик обнаружил, что товара нет в наличии, клиент согласился на изменение.

## Endpoint

`POST /onec/order/items/adjust` (X-Api-Key, `@require_onec_auth`)

### Запрос

```json
{
  "order_id": 123,
  "items": [
    {"product_code": "00-001234", "quantity": 0},
    {"product_code": "00-005678", "quantity": 2}
  ]
}
```

### Успешный ответ (200)

```json
{
  "status": "ok",
  "order_id": 123,
  "batch_id": "uuid",
  "products_price": "1500.00",
  "delivery_price": "200.00",
  "total_price": "1700.00",
  "changes": [
    {"product_code": "00-001234", "action": "removed", "old_quantity": 1, "new_quantity": 0},
    {"product_code": "00-005678", "action": "decreased", "old_quantity": 3, "new_quantity": 2}
  ]
}
```

## Top-level contract

| Поле | Принимаем | Отбиваем |
|------|-----------|----------|
| `order_id` | int, numeric string (`"123"`) | `null`, `true`, `false`, `""` → `missing_field`; нечисловая строка → `invalid_order_id` |
| `items` | non-empty list | `null`, `[]`, `{}`, string, int → `missing_field` |

Совместимость с `onec_order_status`: `order_id` как string разрешён — 1С может прислать и `123`, и `"123"`.

## Ошибки

| error_code | status | Когда |
|------------|--------|-------|
| `invalid_json` | 400 | Невалидный JSON |
| `missing_field` | 400 | Нет `order_id`, нет/пустой `items` |
| `invalid_payload` | 400 | Элемент items не dict, нет product_code/quantity, quantity не int, quantity bool, пустой product_code |
| `order_not_found` | 404 | Заказ не найден |
| `invalid_status` | 409 | Статус ≠ assembly |
| `item_not_found` | 400 | product_code не в заказе |
| `invalid_quantity` | 400 | quantity ≥ текущего или < 0 |
| `duplicate_product_code` | 400 | Дубль product_code в запросе |
| `cannot_remove_all` | 400 | Удаление всех позиций |
| `invalid_order_id` | 400 | order_id не число |

Формат: `{"error_code": "...", "message": "...", "details": {...}}` через `onec_error()`.

## Бизнес-правила

- Инициатор: всегда 1С
- Статус: только `assembly`
- Только уменьшение / удаление (увеличение и добавление запрещены)
- Удалить все позиции нельзя (для этого — отмена заказа)
- batch_id связывает изменения из одного запроса
- delivery_price не пересчитывается
- Клиент видит изменения при повторном открытии экрана заказа (без push)

## Исключения (apps/orders/services.py)

- `OrderNotInAssembly` → `invalid_status` (409)
- `ItemNotFound` → `item_not_found` (400)
- `InvalidItemQuantity` → `invalid_quantity` (400)
- `DuplicateProductCode` → `duplicate_product_code` (400)
- `CannotRemoveAllItems` → `cannot_remove_all` (400)
- `InvalidItemPayload` → `invalid_payload` (400)

## Файлы

- `backend/apps/integrations/onec/order_items_adjust.py` — endpoint
- `backend/apps/orders/services.py` — `adjust_order_items()` + исключения
- `backend/apps/orders/models.py` — `OrderItemChange`
- `backend/apps/orders/migrations/0015_orderitemchange.py` — миграция
- `backend/apps/api/urls.py` — регистрация маршрута
- `backend/apps/api/tests/test_onec_order_items_adjust.py` — тесты
