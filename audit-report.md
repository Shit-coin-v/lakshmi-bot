# Аудит проекта Lakshmi Bot

**Дата:** 2026-04-26
**Объём:** backend (Django 5.2 + DRF), bots (aiogram 3.13), shared, mobile (Flutter), photo-studio (React/TS), infra
**Метод:** 4 параллельных Explore-агента + ручная верификация ключевых находок.
**Источник истины:** `CLAUDE.md`, `docs/ARCHITECTURE.md`, актуальный код.

---

> **Статус Critical (раздел 1): ✅ закрыты в `dev`**, коммиты `e5e76fd → 6c09a45`.
> **Статус High (раздел 2): ✅ закрыты в `dev`**, коммиты `ec12d2a → 0f0481b` (5 коммитов).
> **Статус Medium/Low (разделы 3-4): частично закрыты в `dev`** (M8, M11-M14, M17, L1-L3, L9), пункты M5/M7/L11/L14 — намеренно пропущены или не подтверждены, остальные Medium (M1-M4, M6, M9, M10, M15, M16) и Low (L4, L6-L8, L10, L12-L13) — не вошли в этот раунд.
> Backend test-suite (после Medium/Low правок): **892 теста, 6 ошибок** — те же pre-existing test-discovery дубликаты (`backend.apps.X` vs `apps.X`), что и в baseline `05104ff`; каждый из 6 проходит при изолированном запуске.

## Закрытые High-блокеры

| ID | Коммит | Что сделано |
|----|--------|-------------|
| H1 | `47c83fe` | PII удалён из `OrderCreate` (вместе с C2) |
| H2 | `ec12d2a` | FCM-токен через `mask_token()` в `push.py` |
| H3 | `ec12d2a` | Newsletter-token через `mask_token()` в `customer_bot/run.py` |
| H4 | `ec12d2a` | `RedactSecretsFilter` в Django LOGGING |
| H5 | `0f0481b` | Раздельные `except` в `payments/tasks.py`, `serializers.py`, `receipt.py` |
| H6 | `d68fbf5` + `0f0481b` | Magic numbers в settings: `REFERRAL_BONUS_AMOUNT`, `YUKASSA_*`, `RFM_*` |
| H7 | `1494150` | RFM resume с `chunks_sent` — не переотправляет уже отправленные |
| H8 | `d68fbf5` | `ImproperlyConfigured` если `ALLOW_TELEGRAM_HEADER_AUTH=True` в проде |
| H9 | `0f0481b` | Чек обёрнут в `transaction.atomic` (все строки или ни одной) |
| H10 | `84cfd8e` | axios `^1.7.9` → `^1.8.4` |
| H11 | `84cfd8e` | Pin для `bots/courier|picker/requirements.txt` |
| H12 | `1494150` | `Order.clean()` валидирует state-machine через `ALLOWED_TRANSITIONS` |

## 0. Резюме

| Severity     | Кол-во | Ключевые блокеры                                                                 |
|--------------|--------|----------------------------------------------------------------------------------|
| **Critical** | 5 → **0** ✅ | PyJWT CVE-2024-53861, OrderCreate без atomic+idempotency, гонка webhook ЮKassa, dev-секреты в `.env`, отсутствие locks на Celery beat |
| **High**     | 12 → **0** ✅ | Логирование PII в OrderCreate, FCM token в логах, `except Exception` в платежах/чеках, partial RFM sync retry, magic numbers в финансах, X-Telegram-User-Id auth flag |
| **Medium**   | 17 → **8 закрыто, 2 пропущено намеренно, 7 отложено** | Закрыто в раунде 2: M8 (canceled→new doc), M11 (HMAC cursor), M12 (qr_login throttle), M13 (mask email PII), M14 (logger в pre-save), M17 (CORS HTTPS docs); M10/M15 ссылочно ⇒ закрыто. Пропущено: M5 (Content-Type на 1С — не менять контракт), M7 (CheckConstraint bonuses≥0 — бизнес допускает отрицательный баланс). Отложено: M1/M2/M3/M4/M6/M9/M16 (требуют отдельного цикла) |
| **Low/Info** | 14 → **4 закрыто, 2 false-positive, 1 ⚠️, 7 отложено** | Закрыто: L1 (debug+exc_info), L2 (false-positive, добавлены комментарии), L3 (тип в `logger.exception`), L9 (CAPTURE_DELAYS bounds). False-positive: L5 (параметр используется), L11 (noqa нет в коде). ⚠️ требует решения: L14 (MEMORY.md tracked vs gitignore). Отложено: L4, L6, L7, L8, L10, L12, L13 |

**Общая оценка:** проект в целом следует декларациям из `CLAUDE.md` (auth-зоны разделены, idempotency на чеках есть, retry/atomic в платежах присутствуют). Основные риски — **финансовые гонки в OrderCreate** и **CVE в PyJWT**, оба исправляются в часах.

### Ложные срабатывания агентов (исправлено при верификации)

- ❌ Агент по безопасности утверждал, что `.env` и `backend/firebase_service_account.json` закоммичены — **неверно**. `git log --all -- .env backend/firebase_service_account.json` пуст, оба корректно в `.gitignore`. Секреты лежат только в локальном dev-`.env`.
- ❌ Агент по обработке ошибок утверждал, что invalid FCM-токены не удаляются — **неверно**. Удаление есть в `backend/apps/notifications/tasks.py:177` и `:224` через `CustomerDevice.objects.filter(fcm_token__in=invalid_tokens).delete()`.

---

## 1. CRITICAL — все закрыты ✅

### C1. PyJWT 2.9.0 — CVE-2024-53861 (issuer claim type confusion) ✅ closed in `e5e76fd`
**Файл:** `backend/requirements.txt:56`
**Текущая версия:** `PyJWT==2.9.0`
**Безопасная версия:** `>=2.10.1`
**Воздействие:** в issuer-проверке `jwt.decode(...)` неконтролируемые типы могут привести к auth-bypass. В проекте JWT используется как основной механизм авторизации мобильного приложения (`backend/apps/common/authentication.py`).
**Исправление:** `pip install --upgrade 'PyJWT>=2.10.1'`, обновить `backend/requirements.txt`, прогнать backend-тесты.

### C2. `OrderCreateView` — отсутствуют `transaction.atomic` и idempotency ✅ closed in `47c83fe`
**Файл:** `backend/apps/orders/views.py:133-161`
- `create()` не обёрнут в `transaction.atomic()`. Сравните с `OrderCancelView.post` (строка 197), где atomic + `select_for_update()` есть.
- Нет проверки `Idempotency-Key` или дедупа по корзине: двойной POST/двойной клик → два заказа, две инициации платежа в ЮKassa.
**Воздействие:** дубль заказа в проде; двойной hold денег у клиента; рассинхрон с 1С.
**Исправление:**
1. Обернуть `create()`/`OrderCreateSerializer.create()` в `transaction.atomic()`.
2. Принять `Idempotency-Key` (как в `apps/integrations/onec/receipt.py:128`); кэшировать `(customer_id, idempotency_key) → order_id` в Redis на 30 мин или в новой модели; при повторе возвращать тот же order.

### C3. ЮKassa webhook может прийти раньше, чем заказ создан в БД ✅ closed in `1f916df`
**Файл:** `backend/apps/integrations/payments/webhook.py:99` (`Order.objects.get(payment_id=...)`)
**Сценарий:** медленный `Order.save()` → webhook от ЮKassa приходит первым → `DoesNotExist` → 404 в адрес ЮKassa → ЮKassa перестаёт ретраить (или ретраит, но статус заказа уже потерян).
**Исправление:**
- Возвращать 200 + ставить отложенную задачу-ретрай на webhook-обработку через 5–10 сек, если order не найден.
- Либо создавать `Order` до вызова `yukassa.create_payment(...)` (см. C2 — это совмещается).

### C4. Celery beat-таски без локов — двойное выполнение при overlap ✅ closed in `2b36e83`
**Файлы:**
- `backend/apps/rfm/tasks.py` — `recalculate_all_rfm`
- `backend/apps/integrations/payments/tasks.py:279-307` — `expire_pending_payments`
- `backend/apps/notifications/tasks.py:85-119` — `send_birthday_congratulations`

Если задача длится дольше интервала beat (или beat дублируется при рестарте), запустятся параллельные копии: дубли поздравлений с днём рождения, повторные отмены платежей, гонки в RFM-пересчёте.

**Исправление:** Redis-lock через `redis.lock(blocking=False, timeout=...)` или `django-celery-beat`-уровневый `singleton-task` декоратор.

```python
from redis.lock import Lock
@shared_task
def recalculate_all_rfm():
    with Lock(redis_conn, "lock:recalc-rfm", timeout=3600, blocking=False) as got:
        if not got: return
        ...
```

### C5. Реальные production-токены в локальном `.env` ⚠️ tooling добавлен в `4e7ec5d`, ротация — за пользователем
**Файл:** `.env:2,4,6,11,91,110`
- `BOT_TOKEN`, `COURIER_BOT_TOKEN`, `PICKER_BOT_TOKEN` — реальные токены ботов.
- `EMAIL_HOST_PASSWORD=zbtgpagjjrkpmctq` — Yandex app-password.
- `OPENAI_API_KEY=sk-proj-Rb_N…` — действующий ключ.
- `SECRET_KEY=wb@(cwub2g05sp@#…` — Django.

`.env` корректно в `.gitignore` и **не** в истории git (проверено), но:
- если dev-машина скомпрометирована — токены ботов утекают мгновенно;
- легко случайно поделиться файлом (zip/copy/scp).

**Исправление:**
1. Если эти боты используются в проде → ротировать через @BotFather (минута).
2. Для dev завести отдельных ботов под dev-окружение (`BOT_TOKEN_DEV`).
3. Поставить pre-commit hook `detect-secrets` или `gitleaks` — защита от случайного `git add -A`.
4. Проверить, что `.env` не попадает в `docker build` (есть `.dockerignore` — проверить, что в нём `.env`).

---

## 2. HIGH

## 2. HIGH — все закрыты ✅

### H1. Логирование PII в `OrderCreateView` ✅ closed in `47c83fe` (вместе с C2)
**Файл:** `backend/apps/orders/views.py:145`
```python
_logger.info("OrderCreate payload: %s", request.data)
_logger.warning("OrderCreate validation errors: %s", serializer.errors)
```
`request.data` содержит телефон, ФИО, адрес доставки. PII попадает в Loki/Prometheus/Grafana.
**Исправление:** логировать только `customer_id`, `items_count`, `total`. Для дебага полный payload — только при `DEBUG=True`, либо с маскированием (`phone[-4:]`).

### H2. FCM token в логе при ошибке ✅ closed in `ec12d2a`
**Файл:** `backend/apps/notifications/push.py:108-116`
```python
logger.warning("FCM push failed token=%s code=%s exc=%s", token, code, exc)
```
FCM-токен — секрет, по нему можно слать push'и пользователю с другой инфраструктуры.
**Исправление:** `token=%s...%s` (первые 6 + последние 4 символа), либо хеш `sha256(token)[:16]`.

### H3. Newsletter-token и связки PII в customer_bot ✅ closed in `ec12d2a`
**Файлы:**
- `bots/customer_bot/run.py:337` — `logger.warning("Invalid newsletter token: %s", data)`
- `bots/customer_bot/run.py:348` — `logger.warning("Newsletter delivery not found for token %s (user=%s)", token, callback.from_user.id)`

Связка `newsletter_token + telegram_id` в логах — компрометирует tracking и позволяет атакующему с доступом к логам подделать клик «прочитал».
**Исправление:** хешировать токен или логировать только `delivery_id`.

### H4. Django LOGGING без redact-фильтра для секретов в трассировках ✅ closed in `ec12d2a`
**Файл:** `backend/settings.py:259-277`
При `logger.exception(...)` Django при старом `DEBUG=True` или в кастомных handler'ах может включать `os.environ` в трейс (через локальные переменные frame'а, если используется `loguru` с `backtrace=True` или Sentry с `send_default_pii=True`).
**Исправление:** добавить `logging.Filter`, заменяющий значения переменных, чьи имена матчат `KEY|PASSWORD|TOKEN|SECRET`, на `***`.

### H5. `except Exception` в финансовых/чековых местах без re-raise/контекста ✅ closed in `0f0481b`
**Файлы:**
- `backend/apps/integrations/onec/receipt.py:433` (campaign reward) — fail-open: ошибка молча пропускается, бонус не начислится. Документировать или заменить на explicit fallback.
- `backend/apps/integrations/onec/receipt.py:443` (referral reward) — то же.
- `backend/apps/integrations/payments/tasks.py:78` — TTL-проверка падает → `manual_check_required=True` без retry. Сетевая ошибка из ЮKassa-API → клиент в ручную обработку, хотя достаточно одной retry.
- `backend/apps/orders/serializers.py:330` (`OrderCreateSerializer.create`) — все ошибки ЮKassa в одну воронку. Должно быть: `YukassaLogicalError` (не ретраим, отдаём 4xx клиенту), `YukassaNetworkError` (ставим в очередь и говорим клиенту «попробуйте позже»), `Exception` (Sentry + 500).

### H6. Magic numbers в формулах бонусов и retry ✅ closed in `d68fbf5` + `0f0481b`
**Файлы:**
- `backend/apps/integrations/onec/receipt.py:72` — `"bonus_amount": D("50")` (реферальный бонус) hardcoded.
- `backend/apps/loyalty/models.py:73` — `default=50` (то же значение, но в другом месте — рассинхрон при изменении).
- `backend/apps/rfm/services.py:17-29` — `RECENCY/FREQUENCY/MONETARY_THRESHOLDS` как module-level константы.
- `backend/apps/integrations/payments/tasks.py:26-27` — `_CAPTURE_DELAYS = [10,20,40,80,160]`.
- `backend/apps/integrations/payments/tasks.py:286` — `timeout_minutes=15`.

**Исправление:** перенести в `settings.py` (`REFERRAL_BONUS_AMOUNT`, `YUKASSA_CAPTURE_DELAYS`, `YUKASSA_PAYMENT_TIMEOUT_MINUTES`) или в `RFMConfig` модель в БД.

### H7. RFM partial sync — на retry переотправляются уже отправленные chunks ✅ closed in `1494150`
**Файл:** `backend/apps/rfm/tasks.py:146-238` (`sync_rfm_segments_to_onec`)
`RFMSegmentSyncLog.chunks_sent` инкрементируется, но при `self.retry()` итерация начинается с нулевого chunk → 1С получает дубли назначений сегментов.
**Исправление:** хранить `last_sent_chunk_index` и продолжать с него.

### H8. `ALLOW_TELEGRAM_HEADER_AUTH` — небезопасный fallback на X-Telegram-User-Id ✅ closed in `d68fbf5`
**Файл:** `backend/apps/common/permissions.py:68-121`
Сейчас отключено по умолчанию (good), но это опасный legacy: header можно подделать любым curl. **Не включать в проде.** Рекомендую добавить хард-ассерт в `settings.py`:
```python
if not DEBUG and ALLOW_TELEGRAM_HEADER_AUTH:
    raise ImproperlyConfigured("X-Telegram-User-Id auth disabled in production")
```

### H9. Гонка в `receipt.py` при параллельном чеке на одну строку ✅ closed in `0f0481b`
**Файл:** `backend/apps/integrations/onec/receipt.py:334-341`
Защита `(receipt_guid, receipt_line)` UNIQUE есть, но между check и insert два запроса 1С могут создать оба `Transaction` в одном race window и один уйдёт в `IntegrityError`. Сейчас обработка есть (`DuplicateReceiptLineError`), но цикл не атомарен — частичная обработка чека.
**Исправление:** обернуть весь чек в один `transaction.atomic()` + `select_for_update()` на сам `Order`/`receipt_guid`.

### H10. axios `^1.7.9` (photo-studio) — диапазон, потенциально уязвимый ✅ closed in `84cfd8e`
**Файл:** `photo-studio/package.json:14`
`^1.7.9` разрешает `<2.0.0`. Версии `1.6.x` имеют CVE-2023-45857 (proxy-config exfiltration). Текущая зависит от lockfile.
**Исправление:** `npm i axios@^1.8.4 --save` и зафиксировать в `package-lock.json`.

### H11. Бот-зависимости без pin ✅ closed in `84cfd8e`
**Файлы:** `bots/courier_bot/requirements.txt`, `bots/picker_bot/requirements.txt`
```
aiogram>=3.13
aiohttp
python-dotenv
```
Любой `pip install` притянет последний minor — потенциально несовместимый или уязвимый. Supply-chain risk.
**Исправление:** заморозить версии (`aiogram==3.13.0`, `aiohttp==3.10.11`, `python-dotenv==1.0.1`).

### H12. Order.save() без валидации state-machine ✅ closed in `1494150`
**Файл:** `backend/apps/orders/models.py`, переходы — в `apps/orders/services.py:49-58`
`ALLOWED_TRANSITIONS` — словарь, но enforce-логика только в `update_order_status()`. Прямое `order.status = "completed"; order.save()` (через admin/management command/баг) пройдёт без проверки.
**Исправление:** перенести проверку в `Order.save()` или использовать `django-fsm`. Минимально — отдельный `clean()` метод и `model.full_clean()` на save.

---

## 3. MEDIUM

### M1. N+1 в сериализаторах
- `backend/apps/bot_api/serializers.py:51-62` — `BotUserSerializer.get_referrer_telegram_id` делает доп. SELECT на каждый объект.
- `backend/apps/orders/serializers.py:108-122` — `_get_staff_phones` кэширует на инстансе, но если view создаёт новый сериализатор на каждый объект (ListAPIView с many=True так не делает, но при ручных циклах — повторные запросы).
- `backend/apps/campaigns/services.py:236-246` — `select_related("campaign")` + цикл `.select_related(...)` — второй уже не работает (правила уже подгружены).

**Исправление:** добавить `prefetch_related("referrer", "items__product", "campaign__rules__product")` в `get_queryset()`.

### M2. Дублирование между ботами
- `bots/courier_bot/handlers/orders.py:77-104` ↔ `bots/picker_bot/handlers/orders.py` — `_format_order_detail`, `_fetch_active_orders`.
- Retry handlers в `bots/courier_bot/handlers/orders.py:212-281` повторяются.

**Исправление:** вынести в `shared/bot_utils/order_format.py`.

### M3. Длинные файлы, тяжёлые для навигации
- `backend/apps/bot_api/views.py` — 791 строк, много role-specific views.
- `backend/apps/accounts/views.py` — 448 строк.
- `bots/courier_bot/handlers/orders.py` — 481 строк.

**Исправление:** разбить по подмодулям (`views/customer.py`, `views/courier.py`, …), без изменения публичных импортов.

### M4. File-uploads без magic-bytes
**Файл:** `backend/apps/main/views.py:90-145`
Проверяется размер, расширение и `content_type`, но они задаются клиентом. PNG может оказаться `.exe`.
**Исправление:** `python-magic` либо `Pillow.Image.open(...).verify()` до сохранения.

### M5. Content-Type не валидируется на 1С-endpoints — ⚠️ skipped intentionally
**Файл:** `backend/apps/integrations/onec/receipt.py:94-98` — `request.body` парсится как JSON независимо от Content-Type.
**Исправление (предлагалось):** `if request.content_type != "application/json": return 415`.
**Статус:** не внедряется. CLAUDE.md прямо запрещает менять контракты `/onec/*` без согласования. Эти endpoint'ы защищены `@require_onec_auth` (X-Api-Key + IP-whitelist), невалидный JSON в любом случае падает на парсинге → 400. Реальной защиты не добавит, но может сломать клиентов 1С, которые шлют без Content-Type. Если когда-нибудь понадобится — реализовать как **soft warning** (логировать, но всё равно парсить) с переходом в strict через несколько релизов.

### M6. Нет push-уведомления при `expire_pending_payments`
**Файл:** `backend/apps/integrations/payments/tasks.py:279-307`
Платёж тихо отменяется по TTL — клиент не понимает, что произошло.
**Исправление:** `Notification.create(...)` + FCM-push «оплата истекла, попробуйте снова».

### M7. Negative bonus balance — ⚠️ skipped intentionally
В `backend/apps/loyalty/models.py` нет CHECK-constraint `bonuses >= 0`. F-expression `Coalesce(F("bonuses")) + delta` атомарен, но не защищает от ухода в минус при списании.
**Исправление (предлагалось):** добавить `CheckConstraint(check=Q(bonuses__gte=0), ...)` в `Meta.constraints`, плюс предварительная проверка перед списанием.
**Статус:** не внедряется. Бизнес-логика проекта **допускает** временно отрицательный баланс бонусов (коррекции/реверсы из 1С). Жёсткий DB-constraint сломает существующие сценарии. Если нужна защита от перерасхода — её следует делать на уровне конкретного use-case (мобильное списание, бонус-оплата), а не глобальным constraint.

### M8. `canceled → new` переход без документации ✅ closed in `7aa9145`
**Файл:** `backend/apps/orders/services.py:49-58`
Допускается «реopen» отменённого заказа, но юз-кейс непрозрачен. Может быть случайным side-channel для манипуляции платежом.
**Закрыто:** документирован в `docs/ARCHITECTURE.md` (раздел «Поток заказа» / «Reopen») и в комментарии над `ALLOWED_TRANSITIONS` в `services.py`. Описано: административный сценарий, авто-рефанд capture'нутого СБП на reopen не реверсится.

### M9. Picker-notification дубли при retry
**Файл:** `backend/apps/notifications/tasks.py:189-195`
`notify_pickers_new_order` ретраится целиком при `errors > 0` — pickers, кому уже доставлено, получают второй раз.
**Исправление:** per-picker лок в Redis (`SETNX picker:{order_id}:{picker_id}` с TTL).

### M10. Длинная функция `OrderCreateSerializer.create` с блоком `except Exception`
**Файл:** `backend/apps/orders/serializers.py:330` (см. H5).

### M11. `loyalty/views.py:30-51` — base64 cursor без HMAC ✅ closed in `0c3dadf`
Не критично (содержимое — публичные данные пользователя), но открыто для ручной правки. Если в будущем туда положат `customer_id`/lookback — будет IDOR.
**Закрыто:** курсор подписывается HMAC-SHA256(`SECRET_KEY`), формат `<payload_b64>.<sig16>`. Подмена → `signature mismatch` → 400. Существующие тесты `test_bonus_history` (21 шт) — зелёные.

### M12. QR-логин без throttling ✅ closed in `db79384`
**Файл:** `backend/apps/accounts/views.py:107-137`
Подбор QR-кода (`qr_code` строка) был ограничен `AnonAuthThrottle` (10/min) — слишком мягко для подбора.
**Закрыто:** добавлен `QrLoginThrottle` (scope `qr_login`, 5/min) в `apps/common/throttling.py`, прописан в `settings.py` и `settings_test.py`, применён к `LoginQrView`.

### M13. Email PII в exception-логах ✅ closed in `6cb0855`
**Файлы:** `backend/apps/accounts/views.py:65, 257, 323` — `logger.exception("Failed to send … email to %s", email)`.
В нормальных условиях OK, но email — PII по 152-ФЗ. Минимизируйте: `email[:3]+"***"+email[-5:]`.
**Закрыто:** добавлены `mask_email` и `mask_phone` в `shared/log_redact.py` (рядом с существующим `mask_token`). Применены в `accounts/views.py` (3 места) и `accounts/email_service.py` (2 места). Формат: `a***a@example.com` — домен сохраняется для дебага.

### M14. Pre-save signals — silent exception ✅ closed in `4193e12`
**Файл:** `backend/apps/orders/signals.py:62, 86`
```python
try: ...
except Exception:
    instance._was_approved = False
```
Без `logger.exception`. Если БД-проблема — никто не узнает.
**Закрыто:** добавлен `logger.exception(...)` в обоих местах (`_track_courier_approved`, `_track_picker_approved`). Поведение _was_approved=False сохранено (graceful degradation при недоступной БД), но теперь видно в логах.

### M15. `bonus_amount` `D("50")` рассинхронизирован между receipt.py и model default — см. H6.

### M16. Bot-handlers async не имеют timeout-обёртки на FSM-операциях
В `bots/courier_bot/handlers/orders.py` нет видимых таймаутов FSM-state. При зависшем backend пользователь застревает.

### M17. CORS — есть, но `CORS_ALLOWED_ORIGINS` не валидирует трафик photo-studio под HTTPS в проде ✅ closed (docs) in `428c5cc`
**Файл:** `backend/settings.py:353-381` + `.env:108`
Сейчас в dev — `http://localhost:5173,http://192.168.1.218:5173`. Документировать, что в prod должно быть `https://`.
**Закрыто (docs):** комментарий в `settings.py` рядом с `CORS_ALLOWED_ORIGINS = _env_list(...)` — явно прописано: prod — только `https://`, dev — допустимы `http://localhost`/IP-loopback. Hard-assert на `DEBUG=False && http://` — не добавлен (не хочу ломать существующие dev-overrides без необходимости).

---

## 4. LOW / INFO

| ID  | Файл                                                       | Описание                                                                                     | Статус |
|-----|------------------------------------------------------------|----------------------------------------------------------------------------------------------|--------|
| L1  | `shared/bot_utils/notifications.py:32`                     | `except Exception:` без логгирования (cleanup-код)                                           | ✅ закрыт в `7b6089c`: `logger.debug(..., exc_info=True)` + комментарий о причинах |
| L2  | `shared/bot_utils/retry.py:69-74`                          | nested `except Exception` маскирует оригинал                                                 | ✅ false-positive в `efdd405` (оба логируются через `logger.exception`); добавлены поясняющие комментарии |
| L3  | `shared/clients/onec_client.py:78`                         | `except Exception:` теряет тип ошибки                                                        | ✅ закрыт в `51e4145`: тип в `logger.exception` через `type(exc).__name__` + комментарий |
| L4  | `backend/apps/integrations/onec/receipt.py:300-303`        | `Product.get_or_create` в цикле — потенциальные дубли при race                               | ⏸ отложено |
| L5  | `backend/apps/orders/services.py:32`                       | неиспользуемый параметр `Order` в `_finalize_ttl_expired`                                    | ❌ false-positive: параметр используется на строке 54 (DI для тестов) |
| L6  | `backend/apps/campaigns/services.py:298`                   | использование deprecated `rule.product_id`                                                   | ⏸ отложено |
| L7  | `backend/apps/rfm/tasks.py:69-100`                         | `fix_monthly_bonus_tiers` создаёт дубли при двойном запуске в день                           | ⏸ отложено |
| L8  | `backend/apps/integrations/onec/receipt.py:219-234`        | расчёт распределения бонусов без `_quantize` после каждой операции — копеечная погрешность   | ⏸ отложено |
| L9  | `backend/apps/integrations/payments/tasks.py:175-177`      | `_CAPTURE_DELAYS[min(...)]` без явной проверки длины                                         | ✅ закрыт в `b903fca`: фолбэк на 60s при пустом списке + комментарий |
| L10 | `backend/apps/orders/serializers.py:106-122`               | mutable cache на инстансе сериализатора                                                      | ⏸ отложено |
| L11 | `backend/apps/rfm/tests/test_segment_sync.py`              | импорты `# noqa: F401` без пояснения                                                         | ❌ moot: в текущем коде `noqa` отсутствует |
| L12 | `backend/apps/main/views.py:146-148`                       | имя файла генерируется через `slugify`, нет тестов на коллизии                               | ⏸ отложено |
| L13 | `backend/apps/notifications/push.py`                       | Firebase init на каждый таск (не singleton) — посмотреть по факту                            | ⏸ отложено |
| L14 | `MEMORY.md`                                                | присутствует в репо, но это OpenClaw artifact                                                 | ⚠️ требует решения пользователя: файл tracked в git (1559 байт от 2026-02-17), но соседние OpenClaw-файлы в `.gitignore`. Содержит «Owner: Василий…» — личные предпочтения. Кандидат на `git rm --cached MEMORY.md` + добавить в `.gitignore` |

---

## 5. OWASP Top-10 — сводка

| OWASP | Статус   | Комментарий                                                                                       |
|-------|----------|---------------------------------------------------------------------------------------------------|
| A01   | OK       | Permissions расставлены явно (CustomerPermission/ApiKeyPermission/TelegramUserPermission/onec_auth). Object-level в OrderDetailView/OrderCancelView корректно фильтрует по `request.telegram_user`. |
| A02   | OK       | JWT HS256, `SECRET_KEY` из env, `ExpiredSignatureError` ловится. Рекомендация: отдельный `JWT_SECRET_KEY` (см. H5/M12). |
| A03   | OK       | Raw SQL/`extra`/`raw` не найдены. ORM-инъекций нет. Path-traversal на uploads — закрыт через `slugify`. |
| A04   | **HIGH** | Дизайн-проблемы: C2 (no atomic+idempotency на OrderCreate), C3 (webhook race), C4 (no locks), H7 (RFM partial retry). |
| A05   | Med      | DEBUG/HSTS/SSL-redirect/CORS — конфигурируются через env, дефолты безопасны. Рекомендация — DEFAULT_PERMISSION_CLASSES = DenyAll как fail-safe. |
| A06   | **CRIT** | PyJWT 2.9.0 (CVE-2024-53861); axios `^1.7.9` (range covers CVE-2023-45857); bot deps без pin. |
| A07   | OK       | Throttling настроен (`anon_auth=10/min`, `verify_code=5/min`). JWT-only по умолчанию. Legacy header-auth gated через feature flag. |
| A08   | OK       | 1С — IP-whitelist + API-key + idempotency. ЮKassa — IP-whitelist (с feature-flag отключения, проверить в проде). |
| A09   | Med      | Логирование PII (H1, H2, H3); нет redact-фильтра в `LOGGING` (H4). |
| A10   | OK       | URLs внешних запросов берутся из `settings`, не из user-input. SSRF не нашли. |

---

## 6. Архитектура и качество кода — резюме

- **Структура соответствует** `CLAUDE.md`/`docs/ARCHITECTURE.md`.
- **Боты полностью async** — sync ORM из async не вызывается, используется HTTP-клиент к backend.
- **Retry/atomic** в платежах и 1С реализованы качественно (`_with_http_retry`, `select_for_update`, `transaction.on_commit`).
- **Слабые места:** длинные view-файлы, дублирование между ботами, magic numbers в финансах, несколько fail-open `except Exception` в receipt-обработке.

---

## 7. Зависимости — пакеты и версии

| Пакет                  | Файл                          | Версия     | CVE / статус            |
|------------------------|-------------------------------|------------|-------------------------|
| **PyJWT**              | backend/requirements.txt:56   | ~~2.9.0~~ → 2.10.1 ✅ | CVE-2024-53861 fixed in `e5e76fd` |
| Django                 | backend/requirements.txt:21   | 5.2        | OK                      |
| djangorestframework    | backend/requirements.txt:26   | 3.15.2     | OK                      |
| aiohttp                | backend/requirements.txt:4    | 3.10.11    | OK (≥3.10.0 fixed)      |
| requests               | backend/requirements.txt:46   | 2.32.3     | OK                      |
| urllib3                | backend/requirements.txt:51   | 2.4.0      | OK                      |
| gunicorn               | backend/requirements.txt:55   | 23.0.0     | OK (≥22 fixed)          |
| celery                 | backend/requirements.txt:12   | 5.5.2      | OK                      |
| pillow                 | backend/requirements.txt:34   | 11.2.1     | OK                      |
| psycopg2-binary        | backend/requirements.txt:38   | 2.9.10     | OK                      |
| **axios** (npm)        | photo-studio/package.json:14  | ~~^1.7.9~~ → ^1.8.4 ✅ | bumped in `84cfd8e` |
| **aiogram** (bots)     | bots/*/requirements.txt       | ~~>=3.13~~ → ==3.13.0 ✅ | pinned in `84cfd8e` |
| **python-dotenv** (bots)| bots/*/requirements.txt      | ~~без версии~~ → ==1.0.1 ✅ | pinned in `84cfd8e` |
| **aiohttp** (bots)     | bots/*/requirements.txt       | ~~без версии~~ → ==3.10.11 ✅ | pinned in `84cfd8e` |
| firebase_core (Flutter)| pubspec.yaml:33               | ^3.10.1    | OK                      |
| dio (Flutter)          | pubspec.yaml:42               | ^5.4.0     | OK                      |
| flutter_secure_storage | pubspec.yaml:43               | ^9.0.0     | OK                      |

---

## 8. План действий

### Сегодня (1–4 часа) — все ✅
1. ~~**C1**~~ ✅ `e5e76fd` — PyJWT 2.10.1.
2. ~~**C5**~~ ✅ `4e7ec5d` — pre-commit + `docs/SECURITY.md` (ротация секретов — за пользователем по чеклисту).
3. ~~**H10/H11**~~ ✅ `84cfd8e` — axios + bot deps закреплены.
4. ~~**H1/H2/H3**~~ ✅ `47c83fe` (H1) + `ec12d2a` (H2/H3) — PII/токены убраны.

### Эта неделя (1–3 дня работы) — все ✅
5. ~~**C2**~~ ✅ `47c83fe` — atomic + Idempotency-Key.
6. ~~**C3**~~ ✅ `1f916df` — webhook retry-task.
7. ~~**C4**~~ ✅ `2b36e83` — Redis-locks на 3 beat-таски.
8. ~~**H4**~~ ✅ `ec12d2a` — `RedactSecretsFilter`.
9. ~~**H5**~~ ✅ `0f0481b` — раздельные except.
10. ~~**H6**~~ ✅ `d68fbf5` + `0f0481b` — magic numbers в settings.

### Следующие 2 недели — High закрыты, Medium частично
11. ~~**H7**~~ ✅ `1494150` — RFM resume с `chunks_sent`.
12. ~~**H8**~~ ✅ `d68fbf5` — assert auth-flag.
13. ~~**H9, H12**~~ ✅ `0f0481b` (H9) + `1494150` (H12).
14. **M1, M2, M3** — N+1 fix, вынос дублей в shared, разбиение длинных view-файлов. *(не сделано)*
15. **M4, M6, M9, M16** — magic-bytes upload, push при expire, pickers per-picker lock, FSM-таймауты. *(не сделано)*
15a. ~~**M8** (`canceled→new` док)~~ ✅ `7aa9145`.
15b. ~~**M11** (HMAC cursor)~~ ✅ `0c3dadf`.
15c. ~~**M12** (qr_login throttle)~~ ✅ `db79384`.
15d. ~~**M13** (mask email PII)~~ ✅ `6cb0855`.
15e. ~~**M14** (logger.exception в signals)~~ ✅ `4193e12`.
15f. ~~**M17** (CORS HTTPS docs)~~ ✅ `428c5cc`.
15g. **M5** (Content-Type на 1С) — пропущен сознательно (не менять контракт `/onec/*`).
15h. **M7** (CHECK constraint bonuses≥0) — пропущен сознательно (бизнес-логика допускает отрицательный баланс).
15i. **M10** = ссылается на H5 — закрыт ранее.
15j. **M15** = ссылается на H6 — закрыт ранее.

### В фоне
16. ~~Установить **gitleaks**/**detect-secrets** в pre-commit~~ ✅ `4e7ec5d`. CI — todo.
17. Включить **pip-audit** / **safety** в CI (`.github/workflows/ci.yml`). *(не сделано)*
18. **npm audit** в CI для photo-studio. *(не сделано)*
19. ~~Добавить тесты на гонки (двойной POST OrderCreate, webhook до save, Celery overlap)~~ ✅ — добавлено в коммитах C2/C3/C4.

### Low (раздел 4) — закрыты в этом раунде
20. ~~**L1** (logger в bot cleanup)~~ ✅ `7b6089c` — `logger.debug(..., exc_info=True)`.
21. ~~**L2** (retry nested except)~~ ✅ `efdd405` — false-positive, поясняющие комментарии.
22. ~~**L3** (onec_client typed except)~~ ✅ `51e4145` — `type(exc).__name__` в логе + комментарий.
23. ~~**L9** (CAPTURE_DELAYS bounds)~~ ✅ `b903fca` — фолбэк на 60s при пустом списке.
24. **L5** ❌ false-positive: `Order` параметр используется (DI).
25. **L11** ❌ moot: `noqa: F401` в коде нет.
26. **L14** ⚠️ требует решения пользователя — `MEMORY.md` tracked, добавить ли в gitignore.
27. **L4, L6, L7, L8, L10, L12, L13** — отложены (точечные риски, требуют отдельного контекста).

---

## 9. Приложение: команды для верификации

```bash
# CVE PyJWT
pip install 'PyJWT>=2.10.1' && pip show PyJWT

# Поиск секретов в коде (после установки detect-secrets)
detect-secrets scan --baseline .secrets.baseline

# Проверка отсутствия .env в истории
git log --all --full-history --oneline -- .env

# Аудит npm
cd photo-studio && npm audit --production

# Аудит pip
pip install pip-audit && pip-audit -r backend/requirements.txt
```
