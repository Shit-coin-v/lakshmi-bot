# Backend API — справочник

## Настройка окружения (Docker Compose)

```bash
cp .env.example .env
docker compose up -d
```

---

## 1C Интеграция

### `/onec/receipt` — Приём чеков

`POST /onec/receipt` — JSON с данными чека. Требует `X-Api-Key` и IP из whitelist.

**Обязательные заголовки:**

```
Content-Type: application/json
X-Api-Key: <INTEGRATION_API_KEY>
X-Idempotency-Key: <uuid4>
```

**Минимальный payload:**

```json
{
  "receipt_guid": "R-12345",
  "datetime": "2025-03-10T12:30:00+00:00",
  "store_id": "77",
  "customer": {
    "telegram_id": 9001
  },
  "positions": [
    {
      "line_number": 1,
      "product_code": "SKU-1",
      "quantity": "1",
      "price": "100.00"
    }
  ],
  "totals": {
    "total_amount": "100.00",
    "discount_total": "0",
    "bonus_spent": "0",
    "bonus_earned": "0"
  }
}
```

Гостевая покупка — без блока `customer` (или пустой объект).

---

## Отслеживание рассылок

### Таблицы

- `newsletter_deliveries` — записи доставки: получатель, Telegram ID сообщения, open_token, время открытия
- `newsletter_open_events` — лог кликов: callback data, Telegram user ID

### SQL-отчёты (PostgreSQL)

**Отправлено vs открыто по рассылке:**

```sql
SELECT
    bm.id AS broadcast_id,
    COUNT(nd.id) AS sent,
    COUNT(nd.opened_at) AS opened
FROM broadcast_messages bm
LEFT JOIN newsletter_deliveries nd ON nd.message_id = bm.id
GROUP BY bm.id
ORDER BY bm.id;
```

**Покупки после открытия (Asia/Yakutsk):**

```sql
WITH opened AS (
    SELECT
        nd.id, nd.customer_id, nd.message_id,
        (nd.opened_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Yakutsk') AS opened_local
    FROM newsletter_deliveries nd
    WHERE nd.opened_at IS NOT NULL
)
SELECT
    o.message_id,
    COUNT(DISTINCT t.id) AS purchases_after_open
FROM opened o
JOIN transactions t ON t.customer_id = o.customer_id
    AND t.purchased_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Yakutsk' >= o.opened_local
GROUP BY o.message_id;
```

**Динамика открытий по дням:**

```sql
SELECT
    (nd.opened_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Yakutsk')::date AS opened_date,
    COUNT(*)
FROM newsletter_deliveries nd
WHERE nd.opened_at IS NOT NULL
GROUP BY opened_date
ORDER BY opened_date;
```

Все timestamps хранятся в UTC.

---

## Тестирование

```bash
# В Docker (рекомендуемый способ)
docker compose run --rm -w /app/backend app python manage.py test --settings=settings_test --verbosity=2

# Только конкретное приложение
docker compose run --rm -w /app/backend app python manage.py test apps.orders --settings=settings_test --verbosity=2
```

Настройки тестов: `backend/settings_test.py` (SQLite in-memory, eager Celery, LocMemCache).

---

## Celery

```bash
# Запуск worker через Docker Compose
docker compose up celery_worker

# Мониторинг рассылки
# Логи: "Broadcast <id>: sent=…"
# SQL: SELECT COUNT(*) FROM newsletter_deliveries WHERE message_id = <id>;
```
