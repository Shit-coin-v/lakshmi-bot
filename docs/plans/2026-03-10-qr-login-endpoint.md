# QR Login Endpoint — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Создать эндпоинт `POST /api/auth/login-qr/` для QR-логина из мобильного приложения с возвратом JWT-токенов.

**Architecture:** Новый view `LoginQrView` в `apps.accounts` принимает `qr_code`, ищет `CustomUser` по полю `qr_code`, возвращает данные пользователя + JWT-токены. Защита: `AllowAny` + `AnonAuthThrottle` (как `LoginView`). Flutter переключается на новый эндпоинт.

**Tech Stack:** Django, DRF, existing `generate_tokens`, existing `CustomUser.qr_code` field.

---

### Task 1: Serializer

**Files:**
- Modify: `backend/apps/accounts/serializers.py`

**Step 1: Добавить `LoginQrSerializer`**

```python
class LoginQrSerializer(serializers.Serializer):
    qr_code = serializers.CharField(max_length=500)
```

Добавить в конец файла.

**Step 2: Commit**

```bash
git add backend/apps/accounts/serializers.py
git commit -m "feat(auth): add LoginQrSerializer"
```

---

### Task 2: View

**Files:**
- Modify: `backend/apps/accounts/views.py`

**Step 1: Добавить `LoginQrView`**

Добавить после `LoginView` (после строки 102):

```python
class LoginQrView(APIView):
    """POST /api/auth/login-qr/ — QR code login (mobile app)."""

    permission_classes = [AllowAny]
    throttle_classes = [AnonAuthThrottle]

    def post(self, request):
        ser = LoginQrSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qr_code = ser.validated_data["qr_code"].strip()

        user = CustomUser.objects.filter(qr_code=qr_code).first()
        if not user:
            return Response(
                {"detail": "Пользователь с таким QR-кодом не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        tokens = generate_tokens(user)
        return Response({
            "user_id": user.pk,
            "telegram_id": user.telegram_id,
            "tokens": tokens,
            "customer": {
                "id": user.pk,
                "telegram_id": user.telegram_id,
                "qr_code": user.qr_code,
                "bonus_balance": float(user.bonuses or 0),
            },
        })
```

Добавить `LoginQrSerializer` в import из `.serializers`.

**Step 2: Commit**

```bash
git add backend/apps/accounts/views.py
git commit -m "feat(auth): add LoginQrView for mobile QR login"
```

---

### Task 3: URL

**Files:**
- Modify: `backend/apps/accounts/urls.py`

**Step 1: Добавить маршрут**

```python
path("login-qr/", views.LoginQrView.as_view(), name="auth-login-qr"),
```

Добавить после строки с `login/`.

**Step 2: Commit**

```bash
git add backend/apps/accounts/urls.py
git commit -m "feat(auth): register login-qr URL"
```

---

### Task 4: Тесты

**Files:**
- Modify: `backend/apps/accounts/tests/test_auth_api.py`

**Step 1: Написать тесты**

Добавить после `LoginTests`:

```python
class LoginQrTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(
            telegram_id=123456789,
            qr_code="/media/qr/test123",
            full_name="QR User",
            auth_method="telegram",
            bonuses=50,
        )

    def test_login_qr_success(self):
        resp = self.client.post(
            "/api/auth/login-qr/",
            data={"qr_code": "/media/qr/test123"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("tokens", data)
        self.assertIn("access", data["tokens"])
        self.assertIn("refresh", data["tokens"])
        self.assertEqual(data["user_id"], self.user.pk)
        self.assertEqual(data["customer"]["telegram_id"], 123456789)
        self.assertEqual(data["customer"]["bonus_balance"], 50.0)

    def test_login_qr_not_found(self):
        resp = self.client.post(
            "/api/auth/login-qr/",
            data={"qr_code": "nonexistent"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_login_qr_empty(self):
        resp = self.client.post(
            "/api/auth/login-qr/",
            data={"qr_code": ""},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
```

**Step 2: Запустить тесты**

```bash
cd backend && python manage.py test apps.accounts.tests.test_auth_api.LoginQrTests -v2
```

Expected: все 3 теста PASS.

**Step 3: Commit**

```bash
git add backend/apps/accounts/tests/test_auth_api.py
git commit -m "test(auth): add LoginQrTests"
```

---

### Task 5: Flutter — переключить на новый эндпоинт

**Files:**
- Modify: `mobile/flutter_app/lib/features/auth/services/auth_service.dart`

**Step 1: Изменить `loginWithQr`**

Заменить URL `/onec/customer` на `/api/auth/login-qr/`.
Обновить обработку ответа — сохранять JWT-токены (как в `loginWithEmail`).

```dart
Future<UserModel> loginWithQr(String qrCode) async {
    try {
      final response = await _dio.post(
        '/api/auth/login-qr/',
        data: {"qr_code": qrCode},
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = response.data;

        if (data['customer'] != null) {
          await _storage.deleteAll();
          await ApiClient().clearTokens();

          // Save JWT tokens
          if (data['tokens'] != null) {
            final tokens = data['tokens'];
            await ApiClient().saveTokens(tokens['access'], tokens['refresh']);
          }

          final user = UserModel.fromJson(data);

          await _storage.write(key: _storageQrKey, value: qrCode);
          await _storage.write(key: _storageAuthMethodKey, value: 'qr');

          if (data['customer']['id'] != null) {
            await _storage.write(
              key: _storageIdKey,
              value: data['customer']['id'].toString(),
            );
          }

          if (data['customer']['telegram_id'] != null) {
            final telegramId = data['customer']['telegram_id'];
            await _storage.write(
              key: _storageTelegramIdKey,
              value: telegramId.toString(),
            );
            ApiClient().setTelegramUserId(
              telegramId is int ? telegramId : int.parse(telegramId.toString()),
            );
          }

          return user;
        } else {
          throw Exception('Сервер не вернул данные пользователя');
        }
      } else {
        throw Exception('Ошибка сервера: ${response.statusCode}');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        throw Exception('Пользователь с таким QR-кодом не найден');
      }
      if (e.response?.data != null && e.response?.data['detail'] != null) {
        throw Exception('Ошибка: ${e.response?.data['detail']}');
      }
      throw Exception('Ошибка сети: ${e.message}');
    }
  }
```

**Step 2: Commit**

```bash
git add mobile/flutter_app/lib/features/auth/services/auth_service.dart
git commit -m "feat(mobile): switch QR login to /api/auth/login-qr/ with JWT"
```

---

### Итого изменений

| Файл | Действие |
|---|---|
| `backend/apps/accounts/serializers.py` | + `LoginQrSerializer` |
| `backend/apps/accounts/views.py` | + `LoginQrView` |
| `backend/apps/accounts/urls.py` | + route `login-qr/` |
| `backend/apps/accounts/tests/test_auth_api.py` | + `LoginQrTests` (3 теста) |
| `mobile/flutter_app/lib/features/auth/services/auth_service.dart` | URL `/onec/customer` → `/api/auth/login-qr/`, сохранение токенов |
