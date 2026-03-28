# Referral System — Design Document

> Дата: 2026-03-28
> Статус: DRAFT — ожидает утверждения

---

## 1. Цель

Реферальная система для мобильного приложения + телеграм-бота.
При регистрации у каждого пользователя создаётся уникальный реферальный код.
Если приглашённый совершает **первую подтверждённую покупку** (чек через `onec_receipt`) —
реферер получает **50 бонусов** (one-time, через 1С).

---

## 2. Текущее состояние (что уже есть)

| Компонент | Статус | Проблема |
|-----------|--------|----------|
| `CustomUser.referrer` FK | Работает | `to_field="telegram_id"` — не подходит для email-пользователей |
| Telegram-бот: `/start ref{tg_id}` | Работает | Привязан к telegram_id, не универсальный |
| `onec_receipt` возвращает `referrer_telegram_id` | Работает | Бонус реферу **не начисляется** |
| Начисление бонусов через 1С | Работает | Паттерн есть в `CampaignRewardLog` + `send_bonus_to_onec()` |
| Mobile регистрация (`VerifyEmailView`) | Работает | Реферальный код **не принимается** |

---

## 3. Модель данных

### 3.1. Новое поле `CustomUser.referral_code`

```python
referral_code = models.CharField(
    "Реферальный код",
    max_length=8,
    unique=True,
    db_index=True,
    editable=False,       # immutable после создания
)
```

**Генерация**: 8 символов, base32 (A-Z, 2-7), без амбивалентных символов (0/O, 1/I/L).
Генерируется в `CustomUser.save()` при создании, до `card_id`.
Immutable — после первого сохранения не меняется.

**Почему не `card_id`**: card_id — клиентский/внутренний идентификатор, завязан на PK.
Реферальный код должен быть короткий, человекочитаемый, не раскрывающий внутреннюю структуру.

### 3.2. Миграция `referrer` FK

Текущий FK `referrer` использует `to_field="telegram_id"`. Это ломает связь для email-пользователей.

**Миграция**: изменить FK на стандартный `to_field="id"` (PK).
- Данные: перемаппить существующие связи (SELECT referrer по telegram_id → UPDATE на PK).
- Обратная совместимость: Telegram-бот продолжает передавать `referrer_id` как telegram_id,
  serializer резолвит в PK.

### 3.3. Новая модель `ReferralReward`

```python
class ReferralReward(models.Model):
    class Status(models.TextChoices):
        PENDING  = "pending",  "Ожидает отправки"
        SUCCESS  = "success",  "Успешно"
        FAILED   = "failed",   "Ошибка"

    # Кто пригласил (получатель бонуса)
    referrer = models.ForeignKey(
        "main.CustomUser", on_delete=models.CASCADE,
        related_name="referral_rewards_given",
    )
    # Кого пригласили (чья покупка триггернула бонус)
    referee = models.ForeignKey(
        "main.CustomUser", on_delete=models.CASCADE,
        related_name="referral_reward_received",
    )
    # Идемпотентность: один бонус на реферала
    # UniqueConstraint(fields=["referee"], name="one_referral_reward_per_referee")

    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=50)
    receipt_guid = models.CharField("GUID чека-триггера", max_length=100)
    source = models.CharField(
        "Источник связи", max_length=20,
        choices=[("app", "Приложение"), ("telegram", "Telegram"), ("manual", "Ручное")],
    )

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    last_error = models.TextField(blank=True, default="")
    attempts = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "referral_rewards"
        constraints = [
            models.UniqueConstraint(
                fields=["referee"],
                name="one_referral_reward_per_referee",
            ),
        ]
```

**Ключевое ограничение**: `UniqueConstraint(fields=["referee"])` — один бонус на реферала навсегда.
Повторные webhook, ретраи, конкурентные обработки — всё упирается в DB constraint.

### 3.4. Место размещения

Модель `ReferralReward` — в `apps/loyalty/models.py` (рядом с `Transaction`).
Поле `referral_code` — на `CustomUser` в `apps/main/models.py`.

---

## 4. Событие начисления — единственная точка истины

**Триггер**: `onec_receipt` — факт подтверждённой покупки (чек от 1С).

**НЕ триггер**:
- Создание заказа (`Order.status = "new"`) — может быть отменён.
- Оплата заказа — может быть возврат.
- `customer_sync` от 1С — это синхронизация, не факт покупки.

**Логика в `onec_receipt`** (после успешного создания транзакций, перед return):

```python
# --- Referral reward check ---
if not is_guest and created_count > 0 and user.referrer_id:
    _try_referral_reward(user, receipt_guid=data["receipt_guid"])
```

```python
def _try_referral_reward(referee, receipt_guid):
    """Начислить 50 бонусов реферу за первую покупку реферала. Idempotent."""
    from apps.loyalty.models import ReferralReward
    from apps.integrations.onec.tasks import send_referral_reward_to_onec

    referrer = referee.referrer
    if not referrer or not referrer.card_id:
        return

    # Атомарная попытка создать запись.
    # UniqueConstraint(referee) гарантирует one-time.
    reward, created = ReferralReward.objects.get_or_create(
        referee=referee,
        defaults={
            "referrer": referrer,
            "bonus_amount": D("50"),
            "receipt_guid": receipt_guid,
            "source": "telegram" if referee.auth_method == "telegram" else "app",
            "status": ReferralReward.Status.PENDING,
        },
    )
    if not created:
        return  # уже начислено ранее

    db_tx.on_commit(
        lambda rid=reward.id: send_referral_reward_to_onec.delay(rid)
    )
```

**Идемпотентность**:
- DB level: `UniqueConstraint(referee)` — второй INSERT невозможен
- `get_or_create` — атомарная операция, safe при concurrent requests
- Celery task проверяет `status == SUCCESS` перед отправкой (как в `send_campaign_reward_to_onec`)

---

## 5. Защита бизнес-логики

### 5.1. Запрет self-referral
Валидация в serializer и в `CustomUser.save()`:
```python
if self.referrer_id and self.referrer_id == self.pk:
    raise ValidationError("Self-referral is not allowed")
```

### 5.2. Immutable referrer
После первого сохранения `referrer` нельзя менять:
```python
# В CustomUser.save():
if self.pk:
    old = CustomUser.objects.filter(pk=self.pk).values_list("referrer_id", flat=True).first()
    if old is not None and old != self.referrer_id:
        raise ValidationError("Referrer cannot be changed after assignment")
```

### 5.3. Один реферер на пользователя
Уже обеспечивается FK `referrer` (один FK → один реферер).

### 5.4. Невалидный код
API возвращает `400` с конкретной ошибкой:
- `invalid_referral_code` — код не найден
- `self_referral` — свой собственный код
- `referrer_already_set` — у пользователя уже есть реферер

### 5.5. Старые пользователи
Для существующих пользователей без `referrer` — задним числом привязка **запрещена**.
Реферальная связь создаётся **только при регистрации**.

---

## 6. Реферальная ссылка — честная схема (без deferred deep link)

**Ограничение**: без Branch.io / AppsFlyer / Firebase Dynamic Links нельзя надёжно
связать "клик → установка из стора → регистрация" автоматически.

### Сценарий A: приложение установлено
1. Пользователь кликает `https://lakshmi.app/ref/{referral_code}`
2. Universal Link / App Link перехватывает → открывает приложение
3. Приложение парсит код из URL → если пользователь не авторизован, префиллит код в поле регистрации

### Сценарий B: приложение НЕ установлено (основной кейс)
1. Пользователь кликает `https://lakshmi.app/ref/{referral_code}`
2. Промежуточная HTML-страница:
   - Показывает реферальный код крупным шрифтом
   - Кнопка "Скопировать код" (clipboard API)
   - Кнопки "App Store" / "Google Play"
   - Текст: "После установки введите код при регистрации"
3. Пользователь устанавливает → регистрируется → вводит код вручную

### Промежуточная страница
Статическая HTML (Nginx-served или Django template):
- URL: `https://lakshmi.app/ref/<code>`
- Минимальная: код, copy-button, ссылки на сторы
- Без JS-фреймворков

### Telegram-бот
Текущий формат `/start ref{telegram_id}` заменяется на `/start ref_{referral_code}`.
Бот резолвит `referral_code` → `CustomUser` через API.

---

## 7. API endpoints

### 7.1. `GET /api/customer/me/referral/`
Авторизация: JWT (CustomerPermission)

**Response:**
```json
{
  "referral_code": "A7K2M9XP",
  "referral_link": "https://lakshmi.app/ref/A7K2M9XP",
  "stats": {
    "invited_count": 12,
    "registered_count": 8,
    "purchased_count": 3,
    "bonus_earned": 150.00
  }
}
```

Счётчики:
- `invited_count` — не отслеживается (нет данных о кликах по ссылке), **исключаем**
- `registered_count` — `CustomUser.objects.filter(referrer=user).count()`
- `purchased_count` — `ReferralReward.objects.filter(referrer=user, status="success").count()`
- `bonus_earned` — `ReferralReward.objects.filter(referrer=user, status="success").aggregate(Sum("bonus_amount"))`

**Уточнение**: `invited_count` убираем — без аналитики кликов это ложная метрика.
Оставляем 3 реальных счётчика: зарегистрировались, купили, бонус начислен.

### 7.2. Регистрация: принятие реферального кода

**Email-регистрация** (`POST /api/auth/register/`):
Добавить опциональное поле `referral_code` в `RegisterSerializer`.
Сохранять в `pending_reg:{email}` cache.
При создании пользователя в `VerifyEmailView` — резолвить код → установить `referrer`.

**Telegram-бот** (`POST /api/bot/users/register/`):
Заменить `referrer_id` (telegram_id) на `referral_code`.
`UserRegisterSerializer` резолвит код → устанавливает `referrer`.

**Валидации**:
- Код не найден → `400 invalid_referral_code`
- Свой код → `400 self_referral` (проверяется post-create, т.к. PK ещё нет при регистрации —
  проверка в `VerifyEmailView` после `user.save()`)
- Код опционален — если не передан, `referrer = None`

### 7.3. `GET /api/customer/me/referrals/`
Авторизация: JWT (CustomerPermission)

Список рефералов с детализацией (для расширенной статистики):
```json
{
  "results": [
    {
      "full_name": "Иван И.",    // маскированное имя
      "registered_at": "2026-03-15T10:00:00Z",
      "has_purchased": true,
      "reward_status": "success",  // pending | success | failed | null
      "bonus_amount": 50.00
    }
  ]
}
```

---

## 8. Audit trail

Каждый `ReferralReward` хранит:
- `referrer` — кто получил бонус
- `referee` — чья покупка триггернула
- `receipt_guid` — конкретный чек
- `source` — откуда пришла связь (app / telegram / manual)
- `status` — pending / success / failed
- `last_error` — текст ошибки 1С (если failed)
- `attempts` — количество попыток отправки
- `created_at` / `updated_at` — временные метки

Связь `CustomUser.referrer` хранит сам факт привязки.
`registration_date` на `CustomUser` — когда зарегистрировался.

Для ручной поддержки: admin inline на `CustomUserAdmin` показывает рефералов и статусы наград.

---

## 9. Celery task: `send_referral_reward_to_onec`

Паттерн: копия `send_campaign_reward_to_onec` с адаптацией.

```python
@shared_task(bind=True, max_retries=5)
def send_referral_reward_to_onec(self, reward_id: int):
    from apps.loyalty.models import ReferralReward
    from .onec_client import send_bonus_to_onec

    reward = ReferralReward.objects.select_related("referrer").get(id=reward_id)

    if reward.status == ReferralReward.Status.SUCCESS:
        return {"status": "already_sent"}

    ReferralReward.objects.filter(id=reward.id).update(attempts=F("attempts") + 1)

    try:
        result = send_bonus_to_onec(
            card_id=reward.referrer.card_id,
            bonus_amount=reward.bonus_amount,
            is_accrual=True,
            receipt_guid=f"ref-{reward.id}",  # отдельный GUID для реферальных начислений
        )
        ReferralReward.objects.filter(id=reward.id).update(
            status=ReferralReward.Status.SUCCESS, last_error=""
        )
        # Обновить баланс если 1С вернул new_balance
        ...
    except Exception as exc:
        ReferralReward.objects.filter(id=reward.id).update(
            status=ReferralReward.Status.FAILED, last_error=str(exc)[:1000]
        )
        # retry с exponential backoff
```

---

## 10. Flutter — мобильное приложение

### 10.1. Регистрация: поле реферального кода
- На экране регистрации (`registration_screen.dart`): опциональное поле
  "У меня есть код приглашения" (collapsed по умолчанию, expand по тапу)
- Если приложение открыто через deep link `/ref/{code}` — поле prefilled
- Передаётся в `POST /api/auth/register/` как `referral_code`

### 10.2. Профиль: секция "Пригласить друга"
- Расположение: `profile_screen.dart`
- Реферальный код + кнопка "Поделиться" (Share sheet с текстом + ссылкой)
- Статистика: зарегистрировались / купили / бонусов получено
- Данные: `GET /api/customer/me/referral/`

---

## 11. Edge cases и тестовые сценарии

### Критические (must have)

| # | Сценарий | Ожидание |
|---|----------|----------|
| 1 | Повторный webhook с тем же `receipt_guid` | Бонус НЕ дублируется (idempotency_key + UniqueConstraint) |
| 2 | Два параллельных webhook на первую покупку одного реферала | Только один `ReferralReward` создаётся (DB constraint) |
| 3 | Self-referral (свой код при регистрации) | `400 self_referral` |
| 4 | Несуществующий реферальный код | `400 invalid_referral_code` |
| 5 | Пользователь уже имеет реферера, пытается привязать другого | `400 referrer_already_set` (или игнор — referrer immutable) |
| 6 | Первая покупка в физическом магазине (чек от 1С) | Бонус начисляется (триггер — `onec_receipt`, не источник покупки) |
| 7 | Первая покупка через заказ в приложении (чек от 1С после доставки) | Бонус начисляется |
| 8 | Заказ создан, но не завершён (отменён) | Бонус НЕ начисляется (нет чека) |
| 9 | Сбой отправки бонуса в 1С | `ReferralReward.status = "failed"`, Celery retry до 5 раз |
| 10 | Успешный retry после предыдущего failed | Статус обновляется на `success`, повторная отправка safe |
| 11 | Реферер удалён / заблокирован | `referrer.card_id` проверяется перед отправкой |
| 12 | Email-регистрация с реферальным кодом | Код резолвится, `referrer` устанавливается |
| 13 | Telegram-регистрация с реферальным кодом | Код резолвится через новый формат `/start ref_{code}` |

### Граничные (should have)

| # | Сценарий | Ожидание |
|---|----------|----------|
| 14 | Merge аккаунтов (telegram + email) когда у обоих есть referrer | Сохраняется referrer keep-аккаунта |
| 15 | Merge аккаунтов когда реферал уже получил reward | ReferralReward.referee обновляется на keep-аккаунт |
| 16 | `referral_code` генерация — коллизия | Retry с новым кодом (крайне маловероятно при 8 символах base32) |
| 17 | Старый пользователь без `referral_code` после миграции | Миграция генерирует коды для всех существующих пользователей |

---

## 12. Миграция данных

1. Добавить поле `referral_code` на `CustomUser` (nullable initially)
2. Data migration: сгенерировать коды для всех существующих пользователей
3. Сделать поле `NOT NULL` + `UNIQUE`
4. Изменить FK `referrer`: `to_field="telegram_id"` → `to_field="id"`
   - Data migration: перемаппить `referrer_id` (telegram_id → PK)
5. Создать таблицу `referral_rewards`

---

## 13. Распределение по агентам

### Техлид
- Ревью дизайна
- Ревью миграции FK `referrer`
- Проверка идемпотентности и concurrency

### Бэкенд
- Модель `ReferralReward`
- Поле `referral_code` + генерация
- Миграция FK `referrer`
- Логика в `onec_receipt`
- Celery task `send_referral_reward_to_onec`
- API endpoints: `/me/referral/`, `/me/referrals/`
- Валидации: self-referral, immutable referrer, невалидный код
- Интеграция в `RegisterSerializer`, `VerifyEmailView`, `UserRegisterSerializer`

### Фронтенд (Flutter)
- Поле реферального кода на экране регистрации
- Deep link handling для `/ref/{code}`
- Секция "Пригласить друга" в профиле
- Share sheet
- Экран статистики рефералов

### Тестировщик
- Все сценарии из раздела 11
- Load test: 10 concurrent webhooks на одного реферала
- E2E: регистрация с кодом → покупка → проверка бонуса

---

## 14. Вне скоупа (V1)

- Аналитика кликов по реферальной ссылке (нет SDK)
- Deferred deep links (Branch/AppsFlyer)
- Многоуровневая реферальная программа
- Изменяемый размер бонуса (хардкод 50)
- Реферальные промоакции с ограниченным сроком
