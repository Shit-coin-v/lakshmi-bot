# Фаза 2: API Hardening — Пагинация + Rate Limiting

**Дата**: 2026-02-07
**Аудит**: FULL_AUDIT_2026_02_07.md v3.0
**Findings**: C5 (пагинация), C6 (rate limiting), I2 (notification permissions — уже исправлено в ea5bf3f)

## Реализованные изменения

### C5: Header-based пагинация
- `HeaderPagination(PageNumberPagination)` — тело ответа остаётся массивом, мета-данные в заголовках
- Заголовки: `X-Total-Count`, `X-Page`, `X-Page-Size`, `Link` (RFC 5988)
- `page_size=50`, `max_page_size=200`, `page_size_query_param=page_size`
- Глобально через `DEFAULT_PAGINATION_CLASS` (ProductListView, OrderListUserView)
- Ручная пагинация в `NotificationViewSet.list()` (ViewSet, не GenericAPIView)

### C6: Rate Limiting (DRF)
- `AnonRateThrottle`: 60/min для публичных endpoints
- `TelegramUserThrottle(SimpleRateThrottle)`: 120/min, идентификация по telegram_user.pk
- Кэш: LocMemCache (без зависимости от Redis)

### C6: Rate Limiting (nginx)
- `limit_req_zone api:10m rate=20r/s` для `/` (API)
- `limit_req_zone onec:10m rate=10r/s` для `/onec/` (1C)
- Отдельный `location /onec/` блок

### I2: Notification permissions
- Уже исправлено в коммите ea5bf3f (TelegramUserPermission на всех endpoints)

## Тесты
- 10 тестов пагинации (headers, body=array, page_size, max_limit, second page)
- 2 теста throttling (AnonRateThrottle 429, TelegramUserThrottle 429)
- Throttling отключён в settings_test.py, тесты патчат class attributes напрямую
- **144 теста, все зелёные**
