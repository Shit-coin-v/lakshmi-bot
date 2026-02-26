# Полный аудит Lakshmi Bot v4.0

**Дата:** 2026-02-26
**Версия:** 4.0
**Аудитор:** Claude Opus 4.6
**Предыдущий аудит:** v3.0 (2026-02-07) — все 39 задач закрыты

---

## Обзор

| Область | Файлов проверено | Критичных | Важных | Низких |
|---------|-----------------|-----------|--------|--------|
| Backend Security | ~25 | 3 | 3 | 2 |
| API & Views | ~20 | 1 | 6 | 5 |
| Models & DB | ~15 | 2 | 4 | 3 |
| Bots & Shared | ~30 | 2 | 3 | 4 |
| Infrastructure | ~20 | 3 | 5 | 5 |
| Flutter App | ~40 | 2 | 3 | 4 |
| **Итого** | **~150** | **13** | **24** | **23** |

---

## CRITICAL (13 — блокируют production)

### C1. Timing attack на verification codes
**Файл:** `backend/apps/accounts/email_service.py:44,69,87`
**Проблема:** Сравнение кодов через `==` вместо `hmac.compare_digest()`. Позволяет timing attack на 6-значные коды (10^6 комбинаций).
**Затронуто:** verify_email, reset_password, link_telegram.
**Фикс:** `hmac.compare_digest(stored, code)` во всех трёх местах.

### C2. Слабый RNG для verification codes
**Файл:** `backend/apps/accounts/email_service.py:18`
**Проблема:** `random.choices()` вместо `secrets.choice()`. Модуль `random` — не криптографически безопасен.
**Фикс:** `"".join(secrets.choice(string.digits) for _ in range(CODE_LENGTH))`

### C3. CustomerProfileView — IDOR на update
**Файл:** `backend/apps/main/views.py:17-29`
**Проблема:** `RetrieveUpdateAPIView` с проверкой ownership только в `get_object()`. DRF вызывает `get_object()` и для update, но queryset не фильтрован — потенциальный IDOR если PK угадан.
**Фикс:** Override `get_queryset()`: `return CustomUser.objects.filter(pk=self.request.telegram_user.pk)`

### C4. HTML injection в bot order formatting
**Файл:** `bots/courier_bot/handlers/orders.py:77`, `bots/picker_bot/handlers/orders.py:74`
**Проблема:** `order.comment` вставляется в HTML без escape. Пользователь может отправить `<b>inject</b>` или хуже.
**Фикс:** `from html import escape; f"💬 Комментарий: {escape(order.comment)}"`

### C5. Loki без аутентификации
**Файл:** `infra/observability/loki-config.yaml:1`
**Проблема:** `auth_enabled: false` — любой может читать/писать логи. Логи могут содержать PII.
**Фикс:** Включить basic auth или ограничить доступ через nginx IP whitelist.

### C6. Loki storage в /tmp
**Файл:** `infra/observability/loki-config.yaml:45`
**Проблема:** `/tmp/loki` — теряется при перезагрузке контейнера.
**Фикс:** Volume mount: `- loki-data:/loki` + изменить путь в конфиге.

### C7. /metrics endpoint без auth
**Файл:** `infra/nginx/nginx.conf:54-68`
**Проблема:** Prometheus metrics доступны без аутентификации. Содержат информацию о нагрузке, ошибках, эндпоинтах.
**Фикс:** Ограничить `allow 172.16.0.0/12; deny all;` или basic auth.

### C8. Celery worker без healthcheck
**Файл:** `docker-compose.yml:133-160`
**Проблема:** Нет healthcheck — мёртвый worker не будет перезапущен Docker'ом.
**Фикс:** `healthcheck: test: ["CMD-SHELL", "celery -A celeryapp inspect ping --timeout 10"]`

### C9. Redis password видна в docker ps
**Файл:** `docker-compose.yml:238`
**Проблема:** `--requirepass "${REDIS_PASSWORD}"` в command — видно через `docker inspect`.
**Фикс:** Передавать пароль через конфиг файл (`requirepass` в redis.conf) с env substitution.

### C10. API_KEY assert отключается в Release (Flutter)
**Файл:** `mobile/flutter_app/lib/core/api_client.dart:56`
**Проблема:** `assert(_apiKey.isNotEmpty)` — assertions отключаются в release mode. Приложение будет работать без API ключа.
**Фикс:** `if (_apiKey.isEmpty) throw StateError('API_KEY must be provided via --dart-define');`

### C11. Отсутствуют iOS permissions descriptions
**Файл:** `mobile/flutter_app/ios/Runner/Info.plist`
**Проблема:** Нет `NSPhotoLibraryUsageDescription` и `NSCameraUsageDescription`. Приложение использует ImagePicker и камеру для QR. Apple отклонит из App Store.
**Фикс:** Добавить обе записи в Info.plist.

### C12. Нет rate limiting на auth endpoints
**Файл:** `backend/apps/accounts/views.py`
**Проблема:** Login, register, verify-email, reset-password используют глобальный лимит 120/min. Позволяет brute-force 6-значных кодов.
**Фикс:** Создать `AuthThrottle` (5 attempts / 5 min per email).

### C13. Нет offsite backup
**Файл:** `scripts/backup_db.sh`
**Проблема:** Backup хранится только в docker volume. `docker volume prune` уничтожит всё.
**Фикс:** Добавить upload в S3/GCS после создания backup. Шифровать перед upload.

---

## IMPORTANT (24 — технический долг)

### I1. User enumeration в registration
**Файл:** `backend/apps/accounts/views.py:42`
**Проблема:** Возвращает 409 если email существует. Позволяет проверить наличие email.
**Фикс:** Всегда возвращать 200 с generic message.

### I2. SendMessage task queued before user validation
**Файл:** `backend/apps/main/views.py:32-56`
**Проблема:** Task ставится в очередь без проверки существования пользователя.
**Фикс:** Проверить `CustomUser.objects.filter(telegram_id=...).exists()` перед `.delay()`.

### I3. Missing min_length на verification code serializer
**Файл:** `backend/apps/accounts/serializers.py:20-22`
**Проблема:** `max_length=6` но нет `min_length=6`. Принимает пустые строки.
**Фикс:** `code = serializers.CharField(min_length=6, max_length=6)`

### I4. Linking code exposed в API response
**Файл:** `backend/apps/accounts/views.py:283-293`
**Проблема:** LinkTelegramRequestView возвращает код в ответе. При HTTP interception код утекает.
**Фикс:** Отправлять код только через Telegram бот, не в API response.

### I5. Transaction.product — DO_NOTHING
**Файл:** `backend/apps/loyalty/models.py:11`
**Проблема:** `on_delete=models.DO_NOTHING` нарушает referential integrity при удалении Product.
**Фикс:** `on_delete=models.SET_NULL` (field уже nullable).

### I6. CustomUser.referrer FK на telegram_id
**Файл:** `backend/apps/main/models.py:44-52`
**Проблема:** FK указывает на `to_field="telegram_id"` (nullable unique). Нарушает нормализацию, проблемы при merge.
**Фикс:** Рефакторить на стандартный FK по PK.

### I7. Отсутствуют CHECK constraints на decimal/stock
**Файлы:** `backend/apps/main/models.py`, `backend/apps/orders/models.py`
**Проблема:** Цены, бонусы, stock могут быть отрицательными. Нет DB-level ограничений.
**Фикс:** `CheckConstraint(check=Q(stock__gte=0), name="stock_non_negative")` в Meta.constraints.

### I8. Отсутствуют composite indexes
**Файлы:** `backend/apps/orders/models.py`, `backend/apps/notifications/models.py`
**Проблема:** Нет индексов на `(status, created_at)`, `(payment_status, created_at)`, `(user, type, is_read)`.
**Фикс:** Добавить в Meta.indexes.

### I9. Race condition в courier pre_save signal
**Файл:** `backend/apps/orders/signals.py:51-63`
**Проблема:** Каждый `save()` запускает SELECT для проверки предыдущего значения `is_approved`.
**Фикс:** Использовать `post_init` сигнал: `instance._was_approved = instance.is_approved`.

### I10. Денормализованные поля CustomUser без синхронизации
**Файл:** `backend/apps/main/models.py:53-55`
**Проблема:** `last_purchase_date`, `total_spent`, `purchase_count` не обновляются при удалении Transaction.
**Фикс:** Добавить `post_delete` сигнал или перевести на annotated properties.

### I11. Products endpoint без pagination
**Файл:** `backend/apps/orders/views.py:21-27`
**Проблема:** `ProductListView` может вернуть все продукты без пагинации.
**Фикс:** `pagination_class = HeaderPagination`

### I12. Bot endpoints без pagination
**Файл:** `backend/apps/bot_api/views.py:287-294, 214-234`
**Проблема:** `/api/bot/orders/new/`, `/api/bot/orders/active/` — могут вернуть тысячи записей.
**Фикс:** Добавить пагинацию или лимит в queryset.

### I13. Inconsistent error response format
**Файлы:** Различные views
**Проблема:** 1C endpoints возвращают `{"error_code": ...}`, DRF — `{"detail": ...}`, bot views — разное.
**Фикс:** Стандартизировать: `{"detail": "...", "code": "..."}` через custom exception handler.

### I14. Picker bot — нет тестов
**Файл:** `bots/picker_bot/tests/__init__.py`
**Проблема:** Пустая директория тестов. Courier bot имеет 5 test файлов, picker — 0.
**Фикс:** Скопировать структуру тестов courier_bot, адаптировать для picker.

### I15. Code duplication: courier/picker registration handlers
**Файлы:** `bots/courier_bot/handlers/registration.py`, `bots/picker_bot/handlers/registration.py`
**Проблема:** 82 строки идентичного кода. Отличается только `role="courier"` vs `role="picker"`.
**Фикс:** Извлечь в `shared/bot_utils/registration.py` с параметром role.

### I16. Code duplication: courier/picker start handlers
**Файлы:** `bots/courier_bot/handlers/start.py`, `bots/picker_bot/handlers/start.py`
**Проблема:** ~50 строк почти идентичного кода.
**Фикс:** Shared handler factory.

### I17. Customer bot /link — raw aiohttp вместо BackendClient
**Файл:** `bots/customer_bot/run.py:291-320`
**Проблема:** Создаёт новую ClientSession для каждого запроса. Нет retry, нет JSONDecodeError handling.
**Фикс:** Использовать BackendClient singleton.

### I18. Alertmanager не настроен
**Файл:** `infra/observability/alerts.yml`
**Проблема:** Prometheus alerts определены, но alertmanager не настроен. Alerts никуда не отправляются.
**Фикс:** Добавить alertmanager сервис + notification channel (Telegram/email).

### I19. Недостаточные alert rules
**Файл:** `infra/observability/alerts.yml`
**Проблема:** Только 3 alert rules. Нет: disk space, Redis memory, DB connections, Celery crash, response latency.
**Фикс:** Добавить минимум 5 дополнительных alert rules.

### I20. CI Python version mismatch
**Файл:** `.github/workflows/ci.yml`
**Проблема:** CI тестирует на Python 3.10, Dockerfiles используют 3.12.
**Фикс:** Обновить CI на `python-version: "3.12"`.

### I21. CI нет security scanning
**Файл:** `.github/workflows/ci.yml`
**Проблема:** Нет pip-audit, trivy, semgrep, hadolint.
**Фикс:** Добавить job с pip-audit + trivy scan.

### I22. Redis maxmemory-policy allkeys-lru
**Файл:** `infra/redis/redis.conf:10`
**Проблема:** LRU eviction может удалить активные Celery tasks из очереди.
**Фикс:** Изменить на `noeviction` (fail gracefully) или `volatile-lru`.

### I23. Backend Dockerfile — нет multi-stage build
**Файл:** `infra/docker/backend/Dockerfile`
**Проблема:** Финальный образ содержит build-essential, gcc (~200MB лишнего).
**Фикс:** Multi-stage: builder stage с build deps → runtime stage без них.

### I24. Смешанная навигация GoRouter + Navigator (Flutter)
**Файлы:** 14 файлов в `mobile/flutter_app/lib/features/`
**Проблема:** Некоторые экраны используют `Navigator.pop()` вместо `context.pop()`. Нарушает GoRouter routing stack.
**Фикс:** Заменить все `Navigator.pop/push` на `context.go/pop`.

---

## LOW (23 — улучшения)

### L1. Unused serializers (dead code)
**Файлы:** `backend/apps/notifications/serializers.py:6-21,31-33`
**Проблема:** `UpdateFCMTokenSerializer` и `NotificationReadSerializer` не используются.
**Фикс:** Удалить.

### L2. Missing authentication_classes declaration
**Файлы:** Все views
**Проблема:** DRF default `[SessionAuthentication, BasicAuthentication]` — overhead для API-only.
**Фикс:** `DEFAULT_AUTHENTICATION_CLASSES: []` в settings + явно на views.

### L3. Multiple API key header formats
**Файл:** `backend/apps/common/permissions.py:10-25`
**Проблема:** Принимает `X-Api-Key`, `HTTP_X_API_KEY`, `HTTP_X_ONEC_AUTH`. Запутывает.
**Фикс:** Оставить только `X-Api-Key`.

### L4. Hardcoded delivery fee
**Файл:** `backend/apps/orders/serializers.py:11`
**Проблема:** `_DELIVERY_FEE = Decimal("150.00")` — hardcoded.
**Фикс:** Перенести в SiteSettings.

### L5. PurchaseAPIView lazy-loads referrer (N+1)
**Файл:** `backend/apps/loyalty/views.py:83`
**Проблема:** `customer.referrer` без `select_related`.
**Фикс:** Добавить `.select_related("referrer")` в queryset.

### L6. OneCMapUpsert race condition
**Файл:** `backend/apps/bot_api/views.py:175-208`
**Проблема:** Check-then-act без atomic block.
**Фикс:** Обернуть в `transaction.atomic()`.

### L7. Hardcoded Google Docs link в customer bot
**Файл:** `bots/customer_bot/run.py:160-161`
**Проблема:** URL политики конфиденциальности hardcoded. Требует redeploy при изменении.
**Фикс:** Вынести в environment variable.

### L8. Unicode escapes в courier keyboards
**Файл:** `bots/courier_bot/keyboards.py:8-9`
**Проблема:** `"\u2705"` вместо `"✅"`. Нечитаемо.
**Фикс:** Использовать прямые символы.

### L9. Customer bot global state
**Файл:** `bots/customer_bot/run.py:32-33`
**Проблема:** `bot: Bot | None = None` — глобальный state.
**Фикс:** Передавать через Dispatcher context.

### L10. Models не зарегистрированы в admin
**Файлы:** `backend/apps/api/models.py`, `backend/apps/notifications/models.py`
**Проблема:** OneCClientMap, ReceiptDedup, CourierNotificationMessage, PickerNotificationMessage, RoundRobinCursor не в admin.
**Фикс:** Добавить базовую admin registration.

### L11. Missing healthchecks: nginx, observability
**Файлы:** `docker-compose.yml`, `docker-compose.prod.yml`
**Проблема:** Нет healthcheck для nginx, promtail, grafana, metabase.
**Фикс:** Добавить curl-based checks.

### L12. Resource limits для observability
**Файл:** `docker-compose.prod.yml`
**Проблема:** promtail, loki, prometheus, grafana без resource limits.
**Фикс:** Добавить deploy.resources.limits.

### L13. No gzip в nginx
**Файл:** `infra/nginx/nginx.conf`
**Проблема:** Нет gzip сжатия для static/API responses.
**Фикс:** `gzip on; gzip_types text/plain application/json ...;`

### L14. cleartext traffic в Flutter release
**Файл:** `mobile/flutter_app/android/app/src/main/AndroidManifest.xml:7`
**Проблема:** `usesCleartextTraffic="true"` в release mode.
**Фикс:** Разделить debug/release AndroidManifest.

### L15. No certificate pinning (Flutter)
**Файл:** `mobile/flutter_app/lib/core/api_client.dart`
**Проблема:** Нет SSL pinning. MITM атаки возможны.
**Фикс:** Добавить certificate pinning через Dio adapter.

### L16. Отсутствуют retry в Flutter API services
**Файлы:** `mobile/flutter_app/lib/features/*/services/*.dart`
**Проблема:** DioException не ретраятся.
**Фикс:** Добавить dio_smart_retry.

### L17. No Grafana dashboards provisioned
**Файл:** Нет `infra/observability/dashboards/`
**Проблема:** Grafana требует ручной настройки.
**Фикс:** Добавить provisioning с базовыми dashboards.

### L18. Нет exporters (Redis, PostgreSQL, Celery)
**Файл:** `infra/observability/prometheus.yml`
**Проблема:** Только Django metrics. Нет Redis, PostgreSQL, Celery.
**Фикс:** Добавить redis_exporter, postgres_exporter.

### L19. Backup без шифрования и валидации
**Файл:** `scripts/backup_db.sh`
**Проблема:** Бэкап не шифрован, нет проверки целостности.
**Фикс:** `gpg --encrypt` + проверка размера файла.

### L20. No DELETE endpoint для notifications
**Файл:** `backend/apps/notifications/views.py`
**Проблема:** Нет удаления уведомлений.
**Фикс:** `@action(detail=True, methods=["delete"])`.

### L21. Arbitrary delay в Flutter verify_email
**Файл:** `mobile/flutter_app/lib/features/auth/screens/verify_email_screen.dart:46`
**Проблема:** `Future.delayed(Duration(seconds: 1))` перед навигацией.
**Фикс:** Callback-based navigation.

### L22. Flutter tests coverage gaps
**Файлы:** `mobile/flutter_app/test/`
**Проблема:** Нет тестов для auth_provider, address_provider, push_notification_service.
**Фикс:** Добавить unit тесты.

### L23. Нет интеграционных тестов (Flutter)
**Файл:** `mobile/flutter_app/integration_test/`
**Проблема:** Директория отсутствует.
**Фикс:** Добавить базовые integration tests (login flow, order flow).

---

## Сравнение с аудитом v3.0

| Метрика | v3.0 (2026-02-07) | v4.0 (2026-02-26) |
|---------|-------------------|-------------------|
| Critical | 12 | 13 |
| Important | 15 | 24 |
| Optional | 12 | 23 |
| **Итого** | **39** | **60** |
| Область покрытия | Backend + Infra | Backend + Infra + Bots + Flutter |
| Закрыто из v3.0 | — | 39/39 (100%) |

**Примечание:** Рост числа находок обусловлен расширением scope (добавлены Flutter, accounts app, углублённый анализ ботов). Из новых 60 задач ~40 — новые области, не покрытые в v3.0.

---

## Рекомендуемый порядок исправления

### Phase 1 — Security (C1-C4, C10, C12)
Timing attacks, IDOR, HTML injection, auth bypass. **Блокер для production.**

### Phase 2 — Infrastructure (C5-C9, C13)
Loki auth, storage, metrics auth, healthchecks, backup. **Блокер для production.**

### Phase 3 — Data Integrity (I5-I10)
FK constraints, CHECK constraints, indexes, signals.

### Phase 4 — API Hardening (I1-I4, I11-I13)
User enumeration, pagination, response consistency.

### Phase 5 — Code Quality (I14-I17, I20-I24)
Test coverage, deduplication, Flutter navigation.

### Phase 6 — Observability (I18-I19, L11-L12, L17-L18)
Alertmanager, dashboards, exporters.

### Phase 7 — Polish (L1-L23)
Dead code, configs, optimizations.
