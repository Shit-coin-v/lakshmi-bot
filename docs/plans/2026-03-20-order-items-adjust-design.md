# Order Items Adjust — Backend Design

## Назначение

Эндпоинт для 1С: корректировка состава заказа в статусе `assembly`.
1С отправляет полный список оставшихся товаров, backend вычисляет дельту и применяет изменения.

## Endpoint

`POST /onec/order/items/adjust` (X-Api-Key, `@require_onec_auth`)

### Запрос

```json
{
  "order_id": 123,
  "items": [
    {"product_code": "ЦБ-00012345", "quantity": 1},
    {"product_code": "ЦБ-00099999", "quantity": 2}
  ]
}
```

`items` — полный список товаров, которые должны остаться в заказе. Товары не в списке — удаляются.

### Успешный ответ (200)

```json
{"status": "ok"}
```

## Top-level contract

| Поле | Принимаем | Отбиваем |
|------|-----------|----------|
| `order_id` | int, numeric string | `null`, `true`, `false`, `""` → `missing_field`; нечисловая строка → `invalid_order_id` |
| `items` | non-empty list | `null`, `[]`, `{}`, string, int → `missing_field` |

## Логика сравнения

| Что прислал 1С | Что делает backend |
|---|---|
| Товар есть, quantity меньше текущего | Уменьшает |
| Товара нет в списке | Удаляет из заказа |
| Товар есть, quantity такой же | Ничего не делает |
| Quantity больше текущего | Ошибка 400 `invalid_quantity` |
| Новый товар, которого не было | Ошибка 400 `item_not_found` |
| Точно такой же состав | 200 ok, без изменений (идемпотентно) |

## Ошибки

| error_code | status | Когда |
|---|---|---|
| `invalid_json` | 400 | Невалидный JSON |
| `missing_field` | 400 | Нет `order_id`, нет/пустой `items` |
| `invalid_payload` | 400 | Элемент items: не dict, нет product_code/quantity, qty не int, qty bool, qty < 1 |
| `order_not_found` | 404 | Заказ не найден |
| `invalid_status` | 409 | Статус ≠ assembly |
| `item_not_found` | 400 | product_code не в заказе (новый товар) |
| `invalid_quantity` | 400 | quantity > текущего (увеличение) |
| `duplicate_product_code` | 400 | Дубль product_code в запросе |
| `invalid_order_id` | 400 | order_id не число |

## Audit

Внутренний лог `OrderItemChange` — записывает что изменилось (removed/decreased), batch_id, old/new quantity. Не отдаётся в API-ответе.

## Файлы

- `backend/apps/integrations/onec/order_items_adjust.py` — endpoint
- `backend/apps/orders/services.py` — `adjust_order_items()` + исключения
- `backend/apps/orders/models.py` — `OrderItemChange`
- `backend/apps/orders/migrations/0015_orderitemchange.py` — миграция
- `backend/apps/api/urls.py` — регистрация маршрута
- `backend/apps/api/tests/test_onec_order_items_adjust.py` — тесты
