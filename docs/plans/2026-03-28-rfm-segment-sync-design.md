# RFM Segment Sync to 1C — Design Document

> Дата: 2026-03-28
> Статус: APPROVED

---

## 1. Цель

Синхронизировать зафиксированные месячные RFM-сегменты клиентов из Django в 1С.
1С использует сегмент для начисления бонусов: 5% всем, 7% Чемпионам.

---

## 2. Source of Truth

**`CustomerBonusTier.segment_label_at_fixation`** — полный RFM-сегмент, зафиксированный
1-го числа каждого месяца задачей `fix_monthly_bonus_tiers`.

Почему не другие источники:
- `CustomerRFMProfile.segment_label` — обновляется ежедневно, не фиксация
- `CustomerBonusTier.tier` — бинарный (champions/standard), не полный сегмент

`segment_label_at_fixation` уже заполняется (tasks.py:88) полным значением
из `RFM_SEGMENT_CHOICES`: champions, loyal, potential_loyalists, new_customers,
at_risk, hibernating, lost.

---

## 3. Модель `RFMSegmentSyncLog`

Журнал batch-синхронизации. Одна запись на месяц.

```python
class RFMSegmentSyncLog(models.Model):
    class Status(models.TextChoices):
        PENDING    = "pending"
        IN_PROGRESS = "in_progress"
        SUCCESS    = "success"
        PARTIAL    = "partial"      # часть chunks не доставлена
        FAILED     = "failed"

    effective_month = models.DateField(unique=True)  # 2026-04-01
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_customers = models.IntegerField(default=0)
    total_chunks = models.IntegerField(default=0)
    chunks_sent = models.IntegerField(default=0)
    chunks_failed = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rfm_segment_sync_log"
```

---

## 4. Monthly Flow

```
1-го числа 00:05 → fix_monthly_bonus_tiers()
    → создаёт CustomerBonusTier с segment_label_at_fixation для каждого клиента
    → в конце, если ONEC_RFM_SYNC_ENABLED:
        on_commit → sync_rfm_segments_to_onec.delay(effective_month)
```

---

## 5. Sync Contract

### Request (один chunk)

`POST {ONEC_RFM_SYNC_URL}`

Headers: `X-Api-Key`, `Authorization: Basic ...` (стандартные onec headers)

Body:
```json
[
  {"card_id": "LC-000042", "segment": "champions"},
  {"card_id": "LC-000105", "segment": "loyal"},
  ...
]
```

Payload — массив объектов, только `card_id` и `segment`. Без обёрток.

### Response

```json
{"status": "ok", "processed": 500}
```

### Chunking

- Размер chunk: `ONEC_RFM_SYNC_CHUNK_SIZE` (default 500)
- Chunks отправляются последовательно
- Если chunk failed — логировать, продолжить со следующим
- Финальный статус: SUCCESS (все ok), PARTIAL (есть failed chunks), FAILED (все failed)

---

## 6. Celery Task: `sync_rfm_segments_to_onec`

```
@shared_task(bind=True, max_retries=3)
def sync_rfm_segments_to_onec(self, effective_month: str):
```

Алгоритм:
1. Проверить ONEC_RFM_SYNC_ENABLED и ONEC_RFM_SYNC_URL
2. Получить или создать RFMSegmentSyncLog (get_or_create по effective_month)
3. Если status == SUCCESS — skip (idempotency)
4. Прочитать CustomerBonusTier за месяц: JOIN customer, WHERE card_id IS NOT NULL
5. Сформировать list of {card_id, segment_label_at_fixation}
6. Разбить на chunks по ONEC_RFM_SYNC_CHUNK_SIZE
7. Отправлять chunks последовательно через send_rfm_chunk_to_onec()
8. Обновлять RFMSegmentSyncLog: chunks_sent, chunks_failed, last_error
9. Финальный статус: SUCCESS / PARTIAL / FAILED

При ошибке всего task (не отдельного chunk): retry с backoff.

---

## 7. Settings

```python
ONEC_RFM_SYNC_URL = os.getenv("ONEC_RFM_SYNC_URL", "")
ONEC_RFM_SYNC_CHUNK_SIZE = _env_int("ONEC_RFM_SYNC_CHUNK_SIZE", 500)
ONEC_RFM_SYNC_ENABLED = _env_bool("ONEC_RFM_SYNC_ENABLED", False)
```

`ONEC_RFM_SYNC_ENABLED=False` по умолчанию — kill switch до готовности 1С.

---

## 8. Фильтрация

- Только клиенты с `card_id IS NOT NULL AND card_id != ""`
- Guest user исключён (уже исключён в fix_monthly_bonus_tiers)

---

## 9. Idempotency

- `RFMSegmentSyncLog.effective_month` UNIQUE — один sync на месяц
- Если status == SUCCESS → skip
- Если status == PARTIAL или FAILED → повторная отправка всех chunks (1С idempotent по card_id + month)
- Повторный вызов fix_monthly_bonus_tiers не создаёт дублей (exists check)

---

## 10. Порядок реализации

1. Миграция: `RFMSegmentSyncLog`
2. Settings: 3 env vars
3. `onec_client.py`: `send_rfm_chunk_to_onec(customers_payload)`
4. `rfm/tasks.py`: `sync_rfm_segments_to_onec`
5. `rfm/tasks.py`: вызов sync из `fix_monthly_bonus_tiers`
6. Admin: `RFMSegmentSyncLogAdmin` (read-only)
7. Тесты

---

## 11. Тестовый план

| # | Сценарий |
|---|----------|
| 1 | Фиксация segment_label_at_fixation содержит полный сегмент |
| 2 | Sync отправляет только клиентов с card_id |
| 3 | Payload содержит только card_id и segment |
| 4 | Chunking: 1200 клиентов → 3 chunk по 500/500/200 |
| 5 | Retry при ошибке HTTP |
| 6 | Повторный запуск при status=SUCCESS → skip |
| 7 | Partial failure: 2 из 3 chunks ok → status=PARTIAL |
| 8 | Sync не запускается если ONEC_RFM_SYNC_ENABLED=False |
| 9 | Sync не запускается если нет CustomerBonusTier за месяц |
| 10 | Sync запускается после fix_monthly_bonus_tiers, не после recalculate_all_rfm |
