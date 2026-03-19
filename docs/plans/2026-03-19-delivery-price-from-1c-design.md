# Цена доставки из номенклатуры 1С

**Дата:** 2026-03-19
**Статус:** approved

## Проблема

Цена доставки (150₽) захардкожена в 6+ местах: serializers, views, courier bot, Flutter.
При изменении цены нужно менять код и деплоить.

## Решение

Единый источник цены — `Product` с `product_code = "ЦБ-00073433"` (тип «услуга» в 1С).
Цена обновляется автоматически через существующий импорт из 1С.

## Архитектура

### settings.py

```python
DELIVERY_PRODUCT_CODE = os.getenv("DELIVERY_PRODUCT_CODE", "ЦБ-00073433")
DELIVERY_PRICE_FALLBACK = Decimal(os.getenv("DELIVERY_PRICE_FALLBACK", "150.00"))
DELIVERY_PRICE_CACHE_TTL = 600  # 10 минут
```

### apps/orders/services.py

```python
DELIVERY_PRICE_CACHE_KEY = "delivery_price:{code}"

def get_delivery_price(product_code: str | None = None) -> Decimal:
    """Цена услуги доставки из номенклатуры 1С.
    Кэш 10 мин с инвалидацией при sync. Fallback не кэшируется —
    чтобы новая запись из 1С подхватилась сразу."""
    code = product_code or settings.DELIVERY_PRODUCT_CODE
    cache_key = DELIVERY_PRICE_CACHE_KEY.format(code=code)

    cached = cache.get(cache_key)
    if cached is not None:
        return Decimal(cached)

    from apps.main.models import Product
    price = (
        Product.objects
        .filter(product_code=code, is_active=True)
        .values_list("price", flat=True)
        .first()
    )

    if price is None:
        return Decimal(settings.DELIVERY_PRICE_FALLBACK)

    cache.set(cache_key, str(price), settings.DELIVERY_PRICE_CACHE_TTL)
    return Decimal(price)


def invalidate_delivery_price_cache(product_code: str | None = None):
    """Сбросить кэш цены доставки. Вызывается при sync/delete/деактивации."""
    code = product_code or settings.DELIVERY_PRODUCT_CODE
    cache.delete(DELIVERY_PRICE_CACHE_KEY.format(code=code))
```

### Инвалидация кэша

Вызов `invalidate_delivery_price_cache()` в:
- `product_sync.py` — после `update_or_create`, если `product.product_code == DELIVERY_PRODUCT_CODE`
- `stock_sync.py` — если обновляется `is_active` или удаляется продукт доставки

### Поведение fallback

Fallback (`DELIVERY_PRICE_FALLBACK`) **не кэшируется** осознанно.
Если запись ещё не пришла из 1С или деактивирована — каждый запрос проверяет БД.
Как только запись появится/активируется — цена подхватится мгновенно.

### API для Flutter: `GET /api/config/`

Публичный эндпоинт (`AllowAny`). Цена доставки — глобальная конфигурация, не персональные данные.

```python
class AppConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "delivery_price": str(get_delivery_price()),
        })
```

Flutter вызывает `GET /api/config/` при каждом открытии cart screen.
Без долгоживущего кэша на клиенте.

### Замена хардкодов на бэкенде

| Файл | Было | Станет |
|------|------|--------|
| `orders/serializers.py` | `_DELIVERY_FEE = Decimal("150.00")` | `get_delivery_price()` |
| `bot_api/views.py` | `_get_courier_rate() → 150` | `get_delivery_price()` |
| `courier_bot/handlers/orders.py` | `DELIVERY_RATE = 150` | `get_delivery_price()` |
| `settings.py` | `COURIER_DELIVERY_RATE = 150` | Убрать (заменён на `DELIVERY_PRODUCT_CODE`) |

### Что НЕ меняем

- Модели — не трогаем
- Импорт из 1С — только добавляем вызов `invalidate_delivery_price_cache()`
- Тесты — обновим хардкоды на моки `get_delivery_price`
