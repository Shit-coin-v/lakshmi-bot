# 1C Integration Endpoints

## `/onec/receipt`

`POST /onec/receipt` accepts a minimal JSON payload describing the receipt and
requires the `X-Api-Key` header. Provide an idempotency token via
`X-Idempotency-Key` to deduplicate retries.

### Required headers

```
Content-Type: application/json
X-Api-Key: <INTEGRATION_API_KEY value>
X-Idempotency-Key: <uuid4 or other unique identifier per request>
```

### Minimal payload example

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

To process a guest purchase, omit the `customer` block or send it as an empty
object; the server will allocate the receipt to the configured guest user.

## Telegram newsletter tracking

### Local setup

1. Apply migrations:
   ```bash
   SECRET_KEY=dummy python backend/manage.py migrate --settings=backend.settings
   ```
2. Run the bot with the required environment (see `.env.example`) so that the
   Telegram callbacks can be processed.
3. To execute tests that cover the tracking flow:
   ```bash
   DJANGO_SETTINGS_MODULE=backend.test_settings pytest src/tests/test_newsletter_tracking.py
   SECRET_KEY=dummy python backend/manage.py test main.tests --settings=backend.test_settings
   ```
4. Run the Celery workers that handle broadcast delivery:
   ```bash
   # Using docker-compose
   docker-compose up celery_worker

   # Or locally
   celery -A backend.celery worker --loglevel=info
   ```
   Keep the worker logs open to watch lines such as `Broadcast <id>: sent=…`
   for progress. Each delivery is also written to the `newsletter_deliveries`
   table, so you can monitor completion with a simple count query:
   ```sql
   SELECT COUNT(*) FROM newsletter_deliveries WHERE message_id = <broadcast_id>;
   ```
   Errors are surfaced in the worker logs with `Broadcast <id> failed` or
   `Unexpected error` messages.

### Stored data

* `newsletter_deliveries` — one record per Telegram message that contains the
  hidden content. Fields include the recipient, Telegram identifiers, unique
  open token, and the first-open timestamp.
* `newsletter_open_events` — immutable log of every callback click with the
  raw payload and the Telegram user id.

### Reporting queries (PostgreSQL)

* Sent vs opened per broadcast:
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
* Purchases after an open (using UTC timestamps converted to Asia/Yakutsk):
  ```sql
  WITH opened AS (
      SELECT
          nd.id,
          nd.customer_id,
          nd.message_id,
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
* Daily open dynamics in the shop’s local time zone:
  ```sql
  SELECT
      (nd.opened_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Yakutsk')::date AS opened_date,
      COUNT(*)
  FROM newsletter_deliveries nd
  WHERE nd.opened_at IS NOT NULL
  GROUP BY opened_date
  ORDER BY opened_date;
  ```
* Raw open event log for auditing:
  ```sql
  SELECT
      e.delivery_id,
      e.telegram_user_id,
      e.occurred_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Yakutsk' AS opened_local,
      e.raw_callback_data
  FROM newsletter_open_events e
  ORDER BY e.occurred_at DESC;
  ```

The queries assume that timestamps are stored in UTC; adjust if the database
uses a different timezone configuration.
