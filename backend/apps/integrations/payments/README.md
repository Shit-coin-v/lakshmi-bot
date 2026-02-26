# Интеграция с ЮKassa (СБП)

## Статус

**Реализовано** — оплата по СБП через ЮKassa (hold/capture).

## Бизнес-логика

1. Клиент выбирает СБП → backend создаёт hold в ЮKassa (`capture=false`)
2. Клиент оплачивает в банковском приложении
3. ЮKassa присылает webhook → `payment_status=authorized` → заказ создаётся
4. Курьер доставляет → capture (списание)
5. Отмена на любом этапе → cancel/refund

## Файлы

| Файл | Описание |
|------|----------|
| `yukassa_client.py` | HTTP-клиент ЮKassa: create, capture, cancel |
| `webhook.py` | Обработка webhook (`payment.waiting_for_capture`, `payment.canceled`) |
| `tasks.py` | Celery: `capture_payment_task`, `cancel_payment_task`, `expire_pending_payments` |
| `tests/` | 63 теста (webhook, capture, cancel, expire, edge cases) |

## Настройки (.env)

```
YUKASSA_SHOP_ID=
YUKASSA_SECRET_KEY=
YUKASSA_RETURN_URL=
```

## Безопасность

- IP-фильтрация webhook по официальным диапазонам ЮKassa
- `YUKASSA_DISABLE_IP_CHECK=true` для dev-окружения

## Таймауты

- Неоплаченный платёж → автоотмена через 15 минут (`expire_pending_payments`, beat каждые 5 мин)
- Capture task TTL 30 мин → `manual_check_required` при неоднозначном результате
