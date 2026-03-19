# Зоны доставки — выбор пользователем

**Дата:** 2026-03-19
**Статус:** approved

## Проблема

Одна фиксированная цена доставки. Реально 4 зоны с разными ценами:
- с. Намцы (ЦБ-00073433)
- с. Аппаны (ЦБ-00073441)
- с. Графский-Берег (ЦБ-00073439)
- с. Кыhыл (ЦБ-00073440)

## Решение

Пользователь выбирает зону на экране корзины (dropdown под переключателем доставка/самовывоз).

## Модель DeliveryZone

```python
class DeliveryZone(models.Model):
    name = models.CharField(max_length=100)
    product_code = models.CharField(max_length=50, unique=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order"]
```

Без поля `price` — цена берётся из `Product` по `product_code`.
Только одна зона `is_default=True` среди активных (UniqueConstraint).

## Поле в Order

```python
delivery_zone_code = models.CharField(max_length=50, blank=True, null=True)
```

## GET /api/config/

```json
{
  "delivery_zones": [
    {"name": "с. Намцы", "product_code": "ЦБ-00073433", "price": "200.00", "is_default": true},
    {"name": "с. Аппаны", "product_code": "ЦБ-00073441", "price": "150.00", "is_default": false}
  ]
}
```

### Валидация при выдаче

В список попадают только зоны, у которых:
- `DeliveryZone.is_active = True`
- Существует `Product` с этим `product_code`
- `Product.is_active = True`
- `Product.price` не null

Зоны без валидного Product не отдаются.

## Контракт создания заказа

Flutter отправляет:
```json
{
  "delivery_zone_code": "ЦБ-00073441",
  "fulfillment_type": "delivery",
  ...
}
```

### Валидация при создании

**delivery:**
- `delivery_zone_code` обязателен, иначе 400
- зона должна существовать и `is_active=True`
- Product с этим `product_code` должен существовать, `is_active=True`, `price` не null
- `delivery_price` = `Product.price` — бэкенд считает сам

**pickup:**
- `delivery_zone_code` игнорируется → `null` в заказе
- `delivery_price = 0`

## is_default

- Только одна зона `is_default=True` среди активных
- Flutter берёт зону с `is_default: true`
- Если ни одна не default — Flutter использует первую из списка

## Payload в 1С

```json
"delivery": {
    "type": "delivery",
    "address": "...",
    "comment": "...",
    "product_code": "ЦБ-00073441"
}
```

`product_code` из `order.delivery_zone_code`.

## Что меняется

- Новая модель `DeliveryZone` + миграция
- Поле `delivery_zone_code` в `Order` + миграция
- `GET /api/config/` — возвращает `delivery_zones` вместо `delivery_price`
- `OrderCreateSerializer` — принимает `delivery_zone_code`, валидирует, считает цену
- `order_sync.py` — `delivery.product_code` из `order.delivery_zone_code`
- `get_delivery_price()` — принимает `product_code` зоны
- Flutter: dropdown зон на экране корзины
- `deliveryPriceProvider` → `deliveryZonesProvider`
