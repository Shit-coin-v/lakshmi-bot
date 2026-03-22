# Bonus History — Техдизайн

## Принципы

- Истина по баллам = 1С
- Бэкенд только записывает и отдаёт данные, ничего не вычисляет
- Текущий баланс (`CustomUser.bonuses`) — отдельно, не из этого endpoint
- Legacy-записи без `receipt_guid` не показываем

## Секция 1: API endpoint

**Endpoint:** `GET /api/customer/me/bonus-history/`

**Авторизация:** `CustomerPermission`. Пользователь из токена (`request.telegram_user`). В URL нет `{id}`.

**Источник данных:** модель `Transaction`. Только записи, сохранённые после приёма данных из 1С.

**Логика агрегации:**

Фильтр: `customer = текущий пользователь`, `receipt_guid IS NOT NULL`, исключить пустые `receipt_guid`.

Группировка по `receipt_guid` (все поля построчные, подтверждено по коду `receipt.py:297-334`):

- `sort_date` = `MAX(purchased_at)`
- `purchase_total` = `COALESCE(SUM(total_amount), 0)`
- `bonus_earned` = `COALESCE(SUM(receipt_bonus_earned), 0)`
- `bonus_spent` = `COALESCE(SUM(receipt_bonus_spent), 0)`

**Сортировка:** `sort_date DESC`, `receipt_guid DESC`.

**Пагинация:** cursor-based по агрегированному набору, page size 20. Cursor кодирует пару `(sort_date, receipt_guid)`. Параметр: `?cursor=...`. Без cursor — первая страница.

**Cursor filter** (если cursor передан):

- `sort_date < cursor_date` ИЛИ `(sort_date = cursor_date И receipt_guid < cursor_guid)`
- Обычная лексикографическая пагинация через `Q` объекты

**Pagination logic:**

1. Берём 21 элемент
2. В `results` отдаём первые 20
3. Если элементов ≤ 20 → `next_cursor = null`
4. Если элементов 21 → `next_cursor` строим по **20-му элементу** (последнему отданному). 21-й элемент — индикатор наличия следующей страницы, он будет первым на следующей странице.

**Записи без `receipt_guid`:** не показываем. Legacy-данные от `/api/purchase/` неполные.

**Response:**

```json
{
  "next_cursor": "...",
  "results": [
    {
      "receipt_guid": "abc-123",
      "date": "2026-03-15T10:30:00",
      "purchase_total": "2500.00",
      "bonus_earned": "125.00",
      "bonus_spent": "50.00"
    }
  ]
}
```

`next_cursor = null` если записей больше нет. Числа — строки (DecimalField через DRF).

**Edge cases:**

- Нет транзакций → `{"next_cursor": null, "results": []}`
- Только legacy-записи без `receipt_guid` → пустой список
- `receipt_bonus_earned` / `receipt_bonus_spent` = NULL → COALESCE даёт 0
- Чек с `bonus_earned = 0` и `bonus_spent = 0` → показываем

## Секция 2: Backend structure + Frontend integration

### Backend: View

**`BonusHistoryView(GenericAPIView)`** в `apps/loyalty/views.py`.

`GenericAPIView` — ради стандартного DRF flow (`get_serializer()`, `serializer_class`). Manual cursor — потому что grouped/annotated queryset не ложится на DRF `CursorPagination` (он делает `.filter()` по аннотированному полю → ломает SQL).

- `permission_classes = [CustomerPermission]`
- `serializer_class = BonusHistorySerializer`

**Логика `get()`:**

1. Annotated queryset:
   - `Transaction.objects.filter(customer=user, receipt_guid__isnull=False)` + исключить пустые `receipt_guid`
   - `.values("receipt_guid").annotate(sort_date=..., purchase_total=..., bonus_earned=..., bonus_spent=...)`
2. Cursor filter (если cursor передан):
   - Декодируем cursor → `(cursor_date, cursor_guid)`
   - Фильтр через `Q` объекты: лексикографическое сравнение
3. `.order_by("-sort_date", "-receipt_guid")`
4. Slice 21 элемент
5. Results = первые 20
6. `next_cursor` по 20-му элементу если элементов 21, иначе null
7. Сериализация → response

### Backend: Serializer

**`BonusHistorySerializer(serializers.Serializer)`** в `apps/loyalty/serializers.py`.

Не `ModelSerializer` — работает с dict из `.values().annotate()`.

| Поле | Тип | Примечание |
|---|---|---|
| `receipt_guid` | `CharField` | |
| `date` | `DateTimeField(source="sort_date")` | |
| `purchase_total` | `DecimalField` | строка в JSON |
| `bonus_earned` | `DecimalField` | строка в JSON |
| `bonus_spent` | `DecimalField` | строка в JSON |

Decimal отдаётся строками — дефолтное поведение DRF, консистентно с `CustomerProfileSerializer.bonuses`.

### Backend: URL

`path("customer/me/bonus-history/", BonusHistoryView.as_view())` в `apps/api/urls.py`.

### Frontend: Data layer

**`BonusHistoryItem`** — `receiptGuid` (String), `date` (DateTime), `purchaseTotal` (double), `bonusEarned` (double), `bonusSpent` (double). Числа приходят строками из API → парсим через `double.tryParse`. Никакой бизнес-логики расчёта баллов на клиенте.

**`BonusHistoryResponse`** — `results` (List<BonusHistoryItem>), `nextCursor` (String?).

**Сервис:** `getBonusHistory({String? cursor})` — `GET /api/customer/me/bonus-history/?cursor=...`. Возвращает `BonusHistoryResponse`.

### Frontend: State management

**Riverpod `StateNotifier`** с состоянием: `List<BonusHistoryItem>`, `nextCursor`, `isLoading`, `hasError`.

- `loadMore()` — дозапрашивает следующую страницу, добавляет к текущему списку
- Если `isLoading == true` → `loadMore()` игнорируется
- Если `nextCursor == null` → `loadMore()` не делает запрос

### Frontend: UI (LoyaltyScreen)

Замена заглушки (строки 177-205 текущего `loyalty_screen.dart`).

**Элемент списка:** дата покупки, сумма покупки. Если `bonusEarned > 0` → "+X Б" зелёным. Если `bonusSpent > 0` → "−X Б" красным. Если в чеке и начисление, и списание — оба значения одновременно.

**Бесконечный скролл:** при достижении конца списка → `loadMore()`.

**Пустое состояние:** "История покупок пока пуста".

**Loading:** индикатор при загрузке первой страницы и при подгрузке следующих.
