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
