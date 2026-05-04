# CRM M1 — Auth + Backend Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Превратить статичный CRM-прототип на фикстурах в работающий staff-tool на реальных данных Django: 9 экранов работают через 9 read-only API-эндпоинтов, авторизация через email+password + session-cookie, защищённые маршруты на фронте.

**Architecture:** Новый Django-app `apps/crm_api/` с DRF views/сериализаторами/тестами. Backend использует `SessionAuthentication` + новый `IsCRMStaff` permission. Фронт `crm-web/` получает API-слой (`api/`, `hooks/` на react-query, `auth/`). Папка `fixtures/` удаляется в конце. Без мутаций — только GET.

**Tech Stack:** Django 5.2 + DRF (auth: `SessionAuthentication`); React 18 + react-router-dom 6 + **TanStack Query (react-query)** + **MSW** для тестов.

**Spec:** `docs/superpowers/specs/2026-05-02-crm-m1-auth-backend-design.md`

---

## Карта файлов

### Новые (backend)

```
backend/apps/crm_api/
├── __init__.py
├── apps.py
├── permissions.py
├── urls.py
├── views/__init__.py
├── views/_base.py            # CRMAPIView с auth + permissions
├── views/auth.py              # LoginView, LogoutView, MeView
├── views/dashboard.py
├── views/clients.py
├── views/orders.py
├── views/campaigns.py
├── views/broadcasts.py
├── views/categories.py
├── views/abc_xyz.py
├── serializers/__init__.py
├── serializers/auth.py
├── serializers/client.py
├── serializers/order.py
├── serializers/campaign.py
├── serializers/broadcast.py
├── serializers/category.py
├── serializers/abc_xyz.py
├── services/__init__.py
├── services/dashboard.py
└── tests/
    ├── __init__.py
    ├── _factories.py          # хелперы для setUp в тестах
    ├── test_auth.py
    ├── test_permissions.py
    ├── test_dashboard.py
    ├── test_clients.py
    ├── test_orders.py
    ├── test_campaigns.py
    ├── test_broadcasts.py
    ├── test_categories.py
    └── test_abc_xyz.py
```

### Новые (frontend)

```
crm-web/src/
├── api/
│   ├── client.js
│   ├── auth.js
│   ├── dashboard.js
│   ├── clients.js
│   ├── orders.js
│   ├── campaigns.js
│   ├── broadcasts.js
│   ├── categories.js
│   └── abcXyz.js
├── hooks/
│   ├── useAuth.js
│   ├── useDashboard.js
│   ├── useClients.js
│   ├── useOrders.js
│   ├── useCampaigns.js
│   ├── useBroadcasts.js
│   ├── useCategories.js
│   └── useAbcXyz.js
├── auth/
│   ├── AuthProvider.jsx
│   ├── ProtectedRoute.jsx
│   └── LoginScreen.jsx
├── components/
│   ├── Splash.jsx
│   ├── ErrorBanner.jsx
│   └── ScreenSkeleton.jsx
└── __tests__/
    ├── auth.test.jsx          # новый
    ├── hooks.test.js          # новый
    └── msw_handlers.js        # MSW handlers общие для тестов
```

### Изменяемые (backend)

- `backend/settings.py` — `INSTALLED_APPS` + (опц.) `qr_login` тут уже есть
- `backend/apps/api/urls.py` — добавить `path("crm/", include("apps.crm_api.urls"))`

### Изменяемые (frontend)

- `crm-web/package.json` — добавить `@tanstack/react-query`, `msw`
- `crm-web/vite.config.js` — добавить proxy `/api → 127.0.0.1:8000`
- `crm-web/src/main.jsx` — добавить `QueryClientProvider`, `AuthProvider`
- `crm-web/src/App.jsx` — `ProtectedRoute` обёртка, `/login` маршрут
- `crm-web/src/routes.jsx` — без изменений в SCREEN_TITLES; `/login` обрабатывается в App.jsx отдельно
- `crm-web/src/components/TopBar.jsx` — кнопка профиля → меню logout
- 9 экранов в `crm-web/src/screens/` — переход с фикстур на хуки
- `crm-web/src/__tests__/routes.test.jsx` — переписать под MSW
- `crm-web/README.md` — раздел dev-запуска с Django
- `docs/ARCHITECTURE.md` — новая секция «CRM API»

### Удаляемые

- `crm-web/src/fixtures/` (вся папка) — после Task 28

---

## Универсальные правила

### Запуск тестов

**Backend (из корня репо):**
```
PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api -v 1
```

Или через `make test-backend` (Docker).

**Frontend (из `crm-web/`):**
```
npm run test
```

### Стиль коммитов

Атомарные коммиты per Task. Префиксы: `feat(crm-api):` для backend, `feat(crm-web):` для frontend, `chore(crm):` для config/deps, `test(crm):` если только тесты, `docs(crm):` для документации.

### TDD-протокол

Каждая Task содержит:
1. Failing test (если применимо)
2. Запуск — должен упасть с понятной ошибкой
3. Минимальная имплементация
4. Запуск — зелёный
5. Commit

### Маппинг данных prod-моделей → CRM-схема

Эти соответствия используются во всех серверных Task'ах:

| CRM поле | Источник | Примечание |
|---|---|---|
| `client.id` | `CustomUser.card_id` | строка `LC-001042`, генерируется из pk |
| `client.name` | `CustomUser.full_name` | может быть пустым |
| `client.bonus` | `CustomUser.bonuses` | Decimal → int (округление) |
| `client.ltv` | `CustomUser.total_spent` | Decimal → int |
| `client.purchaseCount` | `CustomUser.purchase_count` | |
| `client.lastOrder` | `CustomUser.last_purchase_date.date()` | ISO `YYYY-MM-DD` |
| `client.rfmSegment` | `CustomUser.rfm_profile.segment_label` | OneToOne `CustomerRFMProfile`; если профиля нет → `"—"` |
| `client.preferences.push` | `CustomUser.general_enabled` | |
| `client.preferences.telegram` | `bool(CustomUser.telegram_id)` | |
| `client.preferences.email` | `CustomUser.promo_enabled` | приближение |
| `client.preferences.sms` | всегда `false` | поле не существует |
| `order.id` | `f"ORD-{Order.id}"` | |
| `order.amount` | `Order.total_price` | Decimal → int |
| `order.purchaseType` | `Order.fulfillment_type` (`delivery`/`pickup`) | `in_store` не приходит из Order |
| `order.items` | `Order.items.count()` | `prefetch_related('items')` обязательно |
| `campaign.id` | `f"CMP-{Campaign.id}"` | |
| `campaign.status` | `'active'` if `Campaign.is_active` else `'finished'` | `draft` не используется в M1 |
| `campaign.period.from` | `Campaign.start_at.date()` | |
| `campaign.period.to` | `Campaign.end_at.date()` | |
| `campaign.reach` | `Campaign.assignments.count()` | через annotate |
| `campaign.used` | `Campaign.assignments.filter(used=True).count()` | через annotate |
| `campaign.segment` | `Campaign.rfm_segment` (если есть) или `Campaign.segment.name` | |
| `campaign.rules` | `f"{first_rule.reward_type}: {first_rule.reward_value}"` или короче | первое правило |
| `broadcast.id` | `f"BR-{BroadcastMessage.id}"` | |
| `broadcast.reach` | `BroadcastMessage.deliveries.count()` | |
| `broadcast.opened` | `BroadcastMessage.deliveries.filter(opened_at__isnull=False).count()` | |
| `broadcast.clicked` | `0` (нет поля `clicked_at` в модели) | стаб |
| `category.slug` | `f"cat-{Category.external_id or Category.id}"` | |
| `category.code` | `Category.external_id or str(Category.id)` | |
| `category.skus` | `Category.products.filter(is_active=True).count()` | |
| `category.revenue/cogs/share/turnover/abc/xyz/trend` | стаб (заглушка с фиксированными значениями) | реальные расчёты — M2/M5 |
| `sku.abc/xyz/suggestedOrder/stockDays/spark` | стаб | реальная аналитика — M2 |
| `abcXyz.matrix*` | стаб (фиксированный JSON) | реальная классификация — M2 |

**Принципиально:** эндпоинты, где данные есть в БД (clients, orders, campaigns, broadcasts/history) — реализуем полноценно. Эндпоинты, где требуется аналитика (categories с revenue/abc, abc-xyz, sku) — отдают **стабы** (фиксированные значения), но **в реальном формате**, через DB-чтение списка категорий/продуктов. Это позволяет фронту не знать про разницу.

---

## Task 1: Bootstrap `apps/crm_api/`

**Files:**
- Create: `backend/apps/crm_api/__init__.py`
- Create: `backend/apps/crm_api/apps.py`
- Create: `backend/apps/crm_api/urls.py`
- Create: `backend/apps/crm_api/views/__init__.py`
- Create: `backend/apps/crm_api/views/_base.py`
- Create: `backend/apps/crm_api/permissions.py`
- Create: `backend/apps/crm_api/tests/__init__.py`
- Modify: `backend/settings.py` (INSTALLED_APPS)
- Modify: `backend/apps/api/urls.py` (include new urls)

- [ ] **Step 1: Создать каркас app**

`backend/apps/crm_api/__init__.py`:
```python
default_app_config = "apps.crm_api.apps.CrmApiConfig"
```

`backend/apps/crm_api/apps.py`:
```python
from django.apps import AppConfig


class CrmApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crm_api"
    label = "crm_api"
    verbose_name = "CRM API"
```

`backend/apps/crm_api/views/__init__.py`:
```python
# Re-exports populated as views are added.
```

`backend/apps/crm_api/tests/__init__.py`:
```python
```

- [ ] **Step 2: Permission-класс `IsCRMStaff`**

`backend/apps/crm_api/permissions.py`:
```python
from rest_framework.permissions import BasePermission


class IsCRMStaff(BasePermission):
    """Доступ к CRM-API: только аутентифицированные сотрудники (is_staff=True).

    Любой не-staff аккаунт (включая обычных клиентов с CustomUser, если у
    кого-то совпали email/пароль с django.User) получит 403.
    """

    message = "Нет доступа в CRM"

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_staff)
```

- [ ] **Step 3: Базовый view-класс `CRMAPIView`**

`backend/apps/crm_api/views/_base.py`:
```python
from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView

from apps.crm_api.permissions import IsCRMStaff


class CRMAPIView(APIView):
    """Базовый класс для всех CRM-эндпоинтов.

    Авторизация: только session-cookie (никаких JWT/X-Api-Key — это другие
    зоны API). Доступ: только staff-пользователи (is_staff=True).
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsCRMStaff]
```

- [ ] **Step 4: Пустой `urls.py`**

`backend/apps/crm_api/urls.py`:
```python
"""URL-маршруты CRM-API. Эндпоинты добавляются по мере появления views."""
from django.urls import path

urlpatterns = [
    # Auth (Task 3): /api/crm/auth/login/, /logout/, /me/
    # Data (Tasks 6-13): dashboard, clients, orders, campaigns,
    # broadcasts/history, categories, abc-xyz
]
```

- [ ] **Step 5: Зарегистрировать app в settings**

В `backend/settings.py`, в `INSTALLED_APPS`, после `'apps.showcase.apps.ShowcaseConfig'`:
```python
INSTALLED_APPS = [
    # ...
    'apps.showcase.apps.ShowcaseConfig',
    'apps.crm_api.apps.CrmApiConfig',  # ← добавить
]
```

- [ ] **Step 6: Подключить urls к корневому роутеру**

Найти, где регистрируется `apps/api/urls.py` или корневой роутер.

Run: `grep -n "include.*api.urls\|integrations\|customer\|onec" backend/urls.py`

Если корневой `urls.py` подключает app'ы, добавить:
```python
path("api/crm/", include("apps.crm_api.urls")),
```

(Точное место и формат — по существующему паттерну.)

- [ ] **Step 7: Тест регистрации app**

Создать `backend/apps/crm_api/tests/test_smoke.py`:
```python
"""Smoke-тест: app зарегистрирован и доступен Django."""
from django.apps import apps
from django.test import TestCase


class CrmApiSmokeTests(TestCase):
    def test_app_is_registered(self):
        self.assertTrue(apps.is_installed("apps.crm_api"))

    def test_permission_class_importable(self):
        from apps.crm_api.permissions import IsCRMStaff
        self.assertTrue(callable(IsCRMStaff))
```

- [ ] **Step 8: Запустить тесты**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api -v 1`
Expected: 2 passed.

- [ ] **Step 9: Commit**

```bash
git add backend/apps/crm_api/ backend/settings.py backend/urls.py
git commit -m "feat(crm-api): bootstrap apps/crm_api with base view and IsCRMStaff permission"
```

---

## Task 2: Permission tests (параметризованный по эндпоинтам)

**Files:**
- Create: `backend/apps/crm_api/tests/test_permissions.py`
- Create: `backend/apps/crm_api/tests/_factories.py`

Эта Task пишется до тестов конкретных эндпоинтов: создаём universal-тест, который потом сам подхватит каждый новый CRM-маршрут. Сейчас в `urls.py` пусто — тест проверяет permission на одном фейковом маршруте. По мере добавления реальных endpoints — он автоматически расширяется.

- [ ] **Step 1: Хелперы для setUp**

`backend/apps/crm_api/tests/_factories.py`:
```python
"""Хелперы для создания тестовых пользователей в CRM-тестах."""
from django.contrib.auth import get_user_model

User = get_user_model()


def create_staff(email: str = "manager@example.com", password: str = "secret123") -> User:
    """Менеджер CRM (is_staff=True)."""
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_staff=True,
    )


def create_regular_user(email: str = "regular@example.com", password: str = "secret123") -> User:
    """Обычный пользователь (is_staff=False)."""
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_staff=False,
    )
```

- [ ] **Step 2: Базовый тест-класс**

`backend/apps/crm_api/tests/test_permissions.py`:
```python
"""Параметризованный тест permissions по всем CRM-эндпоинтам.

Список CRM_GET_ENDPOINTS пополняется по мере добавления views в Tasks 6-13.
Каждое имя должно быть `name=` в `apps/crm_api/urls.py`.
"""
from django.test import TestCase, override_settings
from django.urls import reverse, NoReverseMatch
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff, create_regular_user

# Список (route_name, kwargs_for_reverse). Пополняется по мере роста CRM-API.
CRM_GET_ENDPOINTS = [
    ("crm_api:auth-me", {}),
    # ("crm_api:dashboard", {}),       # Task 6
    # ("crm_api:clients-list", {}),    # Task 7
    # ("crm_api:clients-detail", {"card_id": "LC-000001"}),  # Task 8
    # ...
]


@override_settings(REST_FRAMEWORK={
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {"anon_auth": "1000/min", "qr_login": "1000/min", "verify_code": "1000/min"},
})
class CrmPermissionParametrizedTests(TestCase):
    """Каждый CRM GET-эндпоинт: 401 без сессии, 403 для не-staff, 200 для staff."""

    def setUp(self):
        self.client = APIClient()

    def _resolve(self, name: str, kwargs: dict) -> str:
        try:
            return reverse(name, kwargs=kwargs)
        except NoReverseMatch:
            self.skipTest(f"Endpoint {name} not yet registered")

    def test_unauthenticated_returns_401(self):
        for name, kwargs in CRM_GET_ENDPOINTS:
            with self.subTest(endpoint=name):
                url = self._resolve(name, kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 401, f"{name}: {response.status_code} {response.content!r}")

    def test_non_staff_user_returns_403(self):
        user = create_regular_user()
        self.client.force_login(user)
        for name, kwargs in CRM_GET_ENDPOINTS:
            with self.subTest(endpoint=name):
                url = self._resolve(name, kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403, f"{name}: {response.status_code}")

    def test_staff_user_returns_200(self):
        user = create_staff()
        self.client.force_login(user)
        for name, kwargs in CRM_GET_ENDPOINTS:
            with self.subTest(endpoint=name):
                url = self._resolve(name, kwargs)
                response = self.client.get(url)
                self.assertIn(
                    response.status_code, (200, 404),
                    f"{name}: {response.status_code} {response.content!r}",
                )
```

(`auth-me` — единственный сейчас в списке; раскомментируется в каждой задаче по добавлению endpoint'а.)

- [ ] **Step 3: Запустить — упадёт пока с NoReverseMatch (skip)**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_permissions -v 1`
Expected: 3 tests, все пропущены или 1 неожиданно прошёл (если auth-me пока нет — skip).

- [ ] **Step 4: Commit**

```bash
git add backend/apps/crm_api/tests/test_permissions.py backend/apps/crm_api/tests/_factories.py
git commit -m "test(crm-api): add parametrized permission tests for all CRM endpoints"
```

---

## Task 3: Auth endpoints (login + logout + me)

**Files:**
- Create: `backend/apps/crm_api/serializers/__init__.py`
- Create: `backend/apps/crm_api/serializers/auth.py`
- Create: `backend/apps/crm_api/views/auth.py`
- Create: `backend/apps/crm_api/tests/test_auth.py`
- Modify: `backend/apps/crm_api/urls.py`
- Modify: `backend/apps/crm_api/views/__init__.py`
- Modify: `backend/apps/crm_api/tests/test_permissions.py`

- [ ] **Step 1: Сериализаторы**

`backend/apps/crm_api/serializers/__init__.py`:
```python
```

`backend/apps/crm_api/serializers/auth.py`:
```python
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=1, max_length=128)


class MeSerializer(serializers.Serializer):
    """Информация о текущем пользователе (для /auth/me/ и для ответа /login/)."""

    id = serializers.IntegerField(source="pk", read_only=True)
    email = serializers.EmailField(read_only=True)
    name = serializers.SerializerMethodField()

    def get_name(self, user) -> str:
        full = f"{user.first_name} {user.last_name}".strip()
        return full or user.email or user.username
```

- [ ] **Step 2: Views**

`backend/apps/crm_api/views/auth.py`:
```python
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttling import AnonAuthThrottle
from apps.crm_api.serializers.auth import LoginSerializer, MeSerializer
from apps.crm_api.views._base import CRMAPIView

User = get_user_model()


class LoginView(APIView):
    """POST /api/crm/auth/login/ — вход менеджера по email + password.

    На успех:
    - проставляется session-cookie (sessionid)
    - проставляется csrftoken-cookie (для будущих POST/PATCH/DELETE)
    - в ответе: {"user": {id, email, name}}
    Ошибки:
    - 400 — невалидный body
    - 401 — пользователь не найден или неверный пароль
    - 403 — найден, но is_staff=False
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonAuthThrottle]

    @method_decorator(ensure_csrf_cookie)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user or not check_password(password, user.password):
            return Response(
                {"detail": "Неверный email или пароль"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_staff:
            return Response(
                {"detail": "Нет доступа в CRM"},
                status=status.HTTP_403_FORBIDDEN,
            )

        django_login(request, user)
        return Response({"user": MeSerializer(user).data})


class LogoutView(CRMAPIView):
    """POST /api/crm/auth/logout/ — выход менеджера.

    Снимает session-cookie. Без тела запроса/ответа (204).
    """

    def post(self, request):
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(CRMAPIView):
    """GET /api/crm/auth/me/ — кто я.

    Возвращает {"user": {...}} если живая сессия, иначе 401 (через permission).
    Также проставляет csrftoken для будущих POST'ов.
    """

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"user": MeSerializer(request.user).data})
```

- [ ] **Step 3: Подключить URL'ы**

`backend/apps/crm_api/urls.py`:
```python
"""URL-маршруты CRM-API."""
from django.urls import path

from apps.crm_api.views.auth import LoginView, LogoutView, MeView

app_name = "crm_api"

urlpatterns = [
    path("auth/login/",  LoginView.as_view(),  name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/",     MeView.as_view(),     name="auth-me"),
    # Data (Tasks 6-13): добавляются по мере имплементации
]
```

- [ ] **Step 4: Failing-тесты на auth**

`backend/apps/crm_api/tests/test_auth.py`:
```python
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff, create_regular_user


@override_settings(REST_FRAMEWORK={
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {"anon_auth": "1000/min", "qr_login": "1000/min", "verify_code": "1000/min"},
})
class LoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("crm_api:auth-login")

    def test_login_success_sets_session_cookie(self):
        user = create_staff(email="manager@lakshmi.ru", password="secret123")
        response = self.client.post(self.url, {"email": "manager@lakshmi.ru", "password": "secret123"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["user"]["email"], "manager@lakshmi.ru")
        self.assertIn("sessionid", response.cookies)
        self.assertIn("csrftoken", response.cookies)

    def test_login_email_case_insensitive(self):
        create_staff(email="manager@lakshmi.ru", password="secret123")
        response = self.client.post(self.url, {"email": "Manager@Lakshmi.RU", "password": "secret123"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_login_wrong_password_returns_401(self):
        create_staff(email="manager@lakshmi.ru", password="secret123")
        response = self.client.post(self.url, {"email": "manager@lakshmi.ru", "password": "wrong"}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Неверный email или пароль")

    def test_login_unknown_email_returns_401(self):
        response = self.client.post(self.url, {"email": "ghost@lakshmi.ru", "password": "any"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_login_non_staff_returns_403(self):
        create_regular_user(email="user@lakshmi.ru", password="secret123")
        response = self.client.post(self.url, {"email": "user@lakshmi.ru", "password": "secret123"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Нет доступа в CRM")

    def test_login_invalid_body_returns_400(self):
        response = self.client.post(self.url, {"email": "not-an-email"}, format="json")
        self.assertEqual(response.status_code, 400)


@override_settings(REST_FRAMEWORK={
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {"anon_auth": "1000/min", "qr_login": "1000/min", "verify_code": "1000/min"},
})
class LogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("crm_api:auth-logout")

    def test_logout_returns_204_and_clears_session(self):
        user = create_staff()
        self.client.force_login(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 204)
        # повторный запрос /me/ — уже 401
        me_response = self.client.get(reverse("crm_api:auth-me"))
        self.assertEqual(me_response.status_code, 401)

    def test_logout_unauthenticated_returns_401(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)


class MeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("crm_api:auth-me")

    def test_me_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_me_authenticated_returns_user(self):
        user = create_staff(email="manager@lakshmi.ru")
        user.first_name = "Иван"
        user.last_name = "Сидоров"
        user.save()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], "manager@lakshmi.ru")
        self.assertEqual(response.data["user"]["name"], "Иван Сидоров")

    def test_me_sets_csrftoken_cookie(self):
        user = create_staff()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertIn("csrftoken", response.cookies)
```

- [ ] **Step 5: Запустить тесты — все должны пройти**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_auth -v 1`
Expected: 11 passed.

- [ ] **Step 6: Активировать `auth-me` в параметризованном permission-тесте**

В `backend/apps/crm_api/tests/test_permissions.py` подтверждение, что строка `("crm_api:auth-me", {})` уже стоит в списке. Запустить:

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_permissions -v 1`
Expected: 3 теста зелёные (без skip).

- [ ] **Step 7: Commit**

```bash
git add backend/apps/crm_api/serializers/ backend/apps/crm_api/views/auth.py backend/apps/crm_api/urls.py backend/apps/crm_api/tests/test_auth.py
git commit -m "feat(crm-api): add login/logout/me endpoints with session cookie auth"
```

---

## Task 4: Pagination helpers + Cache config

**Files:**
- Create: `backend/apps/crm_api/pagination.py`

CRM использует существующий `apps.common.pagination.HeaderPagination` (см. spec §5). Здесь — тонкие надстройки на случай, если CRM нужно своё дефолтное `page_size` или фильтр-helper.

- [ ] **Step 1: Лёгкая обёртка вокруг HeaderPagination**

`backend/apps/crm_api/pagination.py`:
```python
"""CRM-специфичная пагинация. Наследует HeaderPagination, добавляет
дефолт page_size=50 (вместо общего 50) и max=200 (защита от выгребания)."""
from apps.common.pagination import HeaderPagination


class CRMHeaderPagination(HeaderPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
```

(Если в `apps.common.pagination.HeaderPagination` уже есть эти атрибуты — оставить только наследование без override. Проверить через `grep -n "class HeaderPagination" backend/apps/common/pagination.py`.)

- [ ] **Step 2: Smoke-тест пагинации**

В `backend/apps/crm_api/tests/test_smoke.py` добавить:
```python
def test_pagination_class_importable(self):
    from apps.crm_api.pagination import CRMHeaderPagination
    self.assertEqual(CRMHeaderPagination.page_size, 50)
    self.assertEqual(CRMHeaderPagination.max_page_size, 200)
```

- [ ] **Step 3: Запуск тестов**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_smoke -v 1`
Expected: passed.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/crm_api/pagination.py backend/apps/crm_api/tests/test_smoke.py
git commit -m "feat(crm-api): add CRMHeaderPagination with sensible defaults"
```

---

## Task 5: Login throttling verification

**Files:**
- Modify: `backend/apps/crm_api/tests/test_auth.py`

Verify the rate-limit working as planned (login защищён `AnonAuthThrottle` 10/min).

- [ ] **Step 1: Тест на rate-limit**

В `test_auth.py` добавить новый класс:
```python
class LoginRateLimitTests(TestCase):
    """Login защищён AnonAuthThrottle (10/min). Без override_settings —
    используем боевые настройки throttling."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("crm_api:auth-login")

    def test_login_rate_limited_after_10_attempts(self):
        # 10 запросов проходят (пусть и с 401), 11-й отбивается с 429
        for i in range(10):
            response = self.client.post(self.url, {"email": "ghost@example.com", "password": "x"}, format="json")
            self.assertNotEqual(response.status_code, 429, f"attempt {i+1}: throttled too early")
        response = self.client.post(self.url, {"email": "ghost@example.com", "password": "x"}, format="json")
        self.assertEqual(response.status_code, 429)
```

- [ ] **Step 2: Запустить**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_auth.LoginRateLimitTests -v 1`
Expected: 1 passed.

(Если в `settings_test.py` дефолтные rates выкручены до 1000/min — этот тест будет ложно зелёный. Проверить, что `settings_test.py` не override'ит ровно `anon_auth`. Если override'ит — для этого теста нужен `@override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"anon_auth": "10/min"}})`.)

- [ ] **Step 3: Commit**

```bash
git add backend/apps/crm_api/tests/test_auth.py
git commit -m "test(crm-api): verify login rate limiting (10/min)"
```

---

## Task 6: Dashboard endpoint + service

**Files:**
- Create: `backend/apps/crm_api/services/__init__.py`
- Create: `backend/apps/crm_api/services/dashboard.py`
- Create: `backend/apps/crm_api/views/dashboard.py`
- Create: `backend/apps/crm_api/tests/test_dashboard.py`
- Modify: `backend/apps/crm_api/urls.py`
- Modify: `backend/apps/crm_api/tests/test_permissions.py`

- [ ] **Step 1: Service-функция расчёта KPI**

`backend/apps/crm_api/services/__init__.py`:
```python
```

`backend/apps/crm_api/services/dashboard.py`:
```python
"""Расчёты для CRM Dashboard. Кэшируются в Django cache на 5 минут."""
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

CACHE_KEY = "crm:dashboard:v1"
CACHE_TTL = 5 * 60  # 5 минут


def compute_dashboard() -> dict:
    """Собрать payload для GET /api/crm/dashboard/.

    Кэширует целиком; повторные запросы в течение 5 мин не читают БД.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    payload = _compute_dashboard_uncached()
    cache.set(CACHE_KEY, payload, CACHE_TTL)
    return payload


def _compute_dashboard_uncached() -> dict:
    from apps.main.models import CustomUser
    from apps.orders.models import Order
    from apps.campaigns.models import Campaign

    now = timezone.now()
    week_start = now - timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    customers_total = CustomUser.objects.count()
    orders_today = Order.objects.filter(created_at__gte=today_start).count()
    revenue_week = (
        Order.objects.filter(created_at__gte=week_start, status="completed")
        .aggregate(total=Sum("total_price"))["total"] or Decimal("0")
    )
    bonuses_total = (
        CustomUser.objects.aggregate(total=Sum("bonuses"))["total"] or Decimal("0")
    )

    daily = list(
        Order.objects.filter(created_at__gte=now - timedelta(days=14))
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(orders=Count("id"), revenue=Sum("total_price"))
        .order_by("day")
    )
    daily_serialized = [
        {
            "date": d["day"].isoformat(),
            "orders": d["orders"],
            "revenue": int(d["revenue"] or 0),
        }
        for d in daily
    ]

    active_campaigns = list(
        Campaign.objects.filter(is_active=True).order_by("-priority")[:5]
    )
    campaigns_payload = [
        {
            "id": f"CMP-{c.id}",
            "name": c.name,
            "hint": (c.rfm_segment or (c.segment.name if c.segment_id else "Все")),
        }
        for c in active_campaigns
    ]

    rfm_segments = _compute_rfm_segments()

    return {
        "kpis": [
            {
                "id": "customers",
                "label": "Активные клиенты",
                "value": customers_total,
                "delta": 0,
                "deltaLabel": "",
                "format": "number",
            },
            {
                "id": "orders",
                "label": "Заказы сегодня",
                "value": orders_today,
                "delta": 0,
                "deltaLabel": "",
                "format": "number",
            },
            {
                "id": "revenue",
                "label": "Выручка за неделю",
                "value": int(revenue_week),
                "delta": 0,
                "deltaLabel": "",
                "format": "rubShort",
            },
            {
                "id": "bonuses",
                "label": "Бонусов на балансе",
                "value": int(bonuses_total),
                "delta": 0,
                "deltaLabel": "",
                "format": "number",
            },
        ],
        "daily": daily_serialized,
        "activeCampaigns": campaigns_payload,
        "rfmSegments": rfm_segments,
    }


def _compute_rfm_segments() -> list[dict]:
    """Распределение клиентов по RFM-сегментам.

    Источник: CustomerRFMProfile.segment_label. Если профилей нет —
    возвращаем пустой список (фронт корректно отрендерит)."""
    from apps.rfm.models import CustomerRFMProfile

    rows = (
        CustomerRFMProfile.objects.values("segment_label")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    total = sum(r["count"] for r in rows)
    if total == 0:
        return []
    return [
        {
            "name": r["segment_label"] or "—",
            "count": r["count"],
            "share": round(r["count"] * 100.0 / total, 1),
        }
        for r in rows
    ]
```

- [ ] **Step 2: View**

`backend/apps/crm_api/views/dashboard.py`:
```python
from rest_framework.response import Response

from apps.crm_api.services.dashboard import compute_dashboard
from apps.crm_api.views._base import CRMAPIView


class DashboardView(CRMAPIView):
    """GET /api/crm/dashboard/ — агрегаты для главной страницы CRM.

    Кэш 5 минут (см. compute_dashboard)."""

    def get(self, request):
        return Response(compute_dashboard())
```

- [ ] **Step 3: Подключить URL**

В `backend/apps/crm_api/urls.py` добавить импорт и path:
```python
from apps.crm_api.views.dashboard import DashboardView
# ...
urlpatterns = [
    path("auth/login/",  LoginView.as_view(),  name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/",     MeView.as_view(),     name="auth-me"),
    path("dashboard/",   DashboardView.as_view(), name="dashboard"),
]
```

- [ ] **Step 4: Активировать в permission-тесте**

В `backend/apps/crm_api/tests/test_permissions.py`, в `CRM_GET_ENDPOINTS`, раскомментировать строку:
```python
("crm_api:dashboard", {}),
```

- [ ] **Step 5: Тест dashboard**

`backend/apps/crm_api/tests/test_dashboard.py`:
```python
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff
from apps.main.models import CustomUser
from apps.orders.models import Order

User = get_user_model()


class DashboardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.staff = create_staff()
        self.client.force_login(self.staff)
        self.url = reverse("crm_api:dashboard")

        # Тестовые данные
        c1 = CustomUser.objects.create(full_name="A", phone="+7 1", bonuses=Decimal("100"))
        c2 = CustomUser.objects.create(full_name="B", phone="+7 2", bonuses=Decimal("250"))
        # Заказы за неделю
        now = timezone.now()
        Order.objects.create(
            customer=c1, status="completed", address="x", phone="+7 1",
            total_price=Decimal("1500"), products_price=Decimal("1500"),
        )
        Order.objects.create(
            customer=c2, status="completed", address="x", phone="+7 2",
            total_price=Decimal("2500"), products_price=Decimal("2500"),
        )
        # И один сегодня
        Order.objects.create(
            customer=c1, status="new", address="x", phone="+7 1",
            total_price=Decimal("500"), products_price=Decimal("500"),
        )

    def test_dashboard_returns_kpis(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        kpis = {k["id"]: k for k in response.data["kpis"]}
        self.assertEqual(kpis["customers"]["value"], 2)
        self.assertEqual(kpis["bonuses"]["value"], 350)
        self.assertEqual(kpis["revenue"]["value"], 4000)
        self.assertGreaterEqual(kpis["orders"]["value"], 1)

    def test_dashboard_returns_daily_array(self):
        response = self.client.get(self.url)
        self.assertIn("daily", response.data)
        self.assertIsInstance(response.data["daily"], list)

    def test_dashboard_returns_active_campaigns(self):
        response = self.client.get(self.url)
        self.assertIn("activeCampaigns", response.data)
        self.assertIsInstance(response.data["activeCampaigns"], list)

    def test_dashboard_returns_rfm_segments(self):
        response = self.client.get(self.url)
        self.assertIn("rfmSegments", response.data)
        self.assertIsInstance(response.data["rfmSegments"], list)

    def test_dashboard_is_cached(self):
        # Первый запрос — кэш промахивается
        first = self.client.get(self.url)
        # Создаём ещё одного клиента
        CustomUser.objects.create(full_name="C", phone="+7 3", bonuses=Decimal("50"))
        # Второй запрос — должен вернуть данные из кэша (без нового клиента)
        second = self.client.get(self.url)
        self.assertEqual(first.data["kpis"], second.data["kpis"])

    def test_dashboard_unauthenticated_returns_401(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
```

- [ ] **Step 6: Запуск тестов**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_dashboard apps.crm_api.tests.test_permissions -v 1`
Expected: 6 dashboard + 3 permission = 9 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/crm_api/services/ backend/apps/crm_api/views/dashboard.py backend/apps/crm_api/urls.py backend/apps/crm_api/tests/test_dashboard.py backend/apps/crm_api/tests/test_permissions.py
git commit -m "feat(crm-api): add dashboard endpoint with cached KPI/RFM/campaigns aggregates"
```

---

## Task 7: Clients list endpoint

**Files:**
- Create: `backend/apps/crm_api/serializers/client.py`
- Create: `backend/apps/crm_api/views/clients.py`
- Create: `backend/apps/crm_api/tests/test_clients.py`
- Modify: `backend/apps/crm_api/urls.py`
- Modify: `backend/apps/crm_api/tests/test_permissions.py`

- [ ] **Step 1: List-сериализатор**

`backend/apps/crm_api/serializers/client.py`:
```python
from rest_framework import serializers

from apps.main.models import CustomUser


def _segment_label(user) -> str:
    profile = getattr(user, "rfm_profile", None)
    return (profile.segment_label if profile else "") or "—"


def _last_order_iso(user) -> str | None:
    if not user.last_purchase_date:
        return None
    return user.last_purchase_date.date().isoformat()


def _tags(user) -> list[str]:
    tags = []
    if (user.purchase_count or 0) >= 30:
        tags.append("vip")
    if (user.bonuses or 0) >= 1000:
        tags.append("много бонусов")
    if user.email and user.telegram_id:
        tags.append("мульти-канал")
    return tags


class ClientListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="card_id")
    name = serializers.CharField(source="full_name", default="")
    rfmSegment = serializers.SerializerMethodField()
    bonus = serializers.SerializerMethodField()
    ltv = serializers.SerializerMethodField()
    purchaseCount = serializers.IntegerField(source="purchase_count", default=0)
    lastOrder = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id", "name", "phone", "email",
            "rfmSegment", "bonus", "ltv", "purchaseCount", "lastOrder", "tags",
        ]

    def get_rfmSegment(self, obj) -> str:
        return _segment_label(obj)

    def get_bonus(self, obj) -> int:
        return int(obj.bonuses or 0)

    def get_ltv(self, obj) -> int:
        return int(obj.total_spent or 0)

    def get_lastOrder(self, obj):
        return _last_order_iso(obj)

    def get_tags(self, obj) -> list[str]:
        return _tags(obj)
```

- [ ] **Step 2: View**

`backend/apps/crm_api/views/clients.py`:
```python
from django.db.models import Q
from rest_framework.generics import ListAPIView

from apps.crm_api.pagination import CRMHeaderPagination
from apps.crm_api.serializers.client import ClientListSerializer
from apps.crm_api.views._base import CRMAPIView
from apps.main.models import CustomUser


class ClientListView(ListAPIView, CRMAPIView):
    """GET /api/crm/clients/?q=&segment=&page=&page_size= — список клиентов CRM.

    Поиск (q) — по name/phone/email/card_id.
    Фильтр по сегменту (segment) — по значению CustomerRFMProfile.segment_label.
    """

    serializer_class = ClientListSerializer
    pagination_class = CRMHeaderPagination

    def get_queryset(self):
        qs = (
            CustomUser.objects
            .select_related("rfm_profile")
            .order_by("-id")
        )
        q = self.request.query_params.get("q", "").strip()
        segment = self.request.query_params.get("segment", "").strip()

        if q:
            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(phone__icontains=q)
                | Q(email__icontains=q)
                | Q(card_id__icontains=q)
            )
        if segment and segment != "Все":
            qs = qs.filter(rfm_profile__segment_label=segment)
        return qs
```

- [ ] **Step 3: Подключить URL**

В `backend/apps/crm_api/urls.py`:
```python
from apps.crm_api.views.clients import ClientListView
# ...
path("clients/", ClientListView.as_view(), name="clients-list"),
```

- [ ] **Step 4: Активировать в permission-тесте**

В `test_permissions.py`, в `CRM_GET_ENDPOINTS`:
```python
("crm_api:clients-list", {}),
```

- [ ] **Step 5: Тест**

`backend/apps/crm_api/tests/test_clients.py`:
```python
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff
from apps.main.models import CustomUser


class ClientListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = CustomUser.objects.create(
            full_name="Алиса Иванова", phone="+7 914 111-22-33",
            email="alice@example.ru", bonuses=Decimal("500"),
            total_spent=Decimal("12000"), purchase_count=5,
            card_id="LC-000001",
        )
        cls.bob = CustomUser.objects.create(
            full_name="Боб Петров", phone="+7 914 222-33-44",
            email="bob@example.ru", bonuses=Decimal("0"),
            total_spent=Decimal("0"), purchase_count=0,
            card_id="LC-000002",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:clients-list")

    def test_list_returns_all(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = {c["id"] for c in response.data["results"]}
        self.assertEqual(ids, {"LC-000001", "LC-000002"})

    def test_search_by_name(self):
        response = self.client.get(self.url, {"q": "Алис"})
        ids = {c["id"] for c in response.data["results"]}
        self.assertEqual(ids, {"LC-000001"})

    def test_search_by_phone(self):
        response = self.client.get(self.url, {"q": "111-22-33"})
        ids = {c["id"] for c in response.data["results"]}
        self.assertEqual(ids, {"LC-000001"})

    def test_search_by_card_id(self):
        response = self.client.get(self.url, {"q": "LC-000002"})
        ids = {c["id"] for c in response.data["results"]}
        self.assertEqual(ids, {"LC-000002"})

    def test_pagination_headers(self):
        response = self.client.get(self.url, {"page_size": 1})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.headers.get("X-Total-Count"), "2")
        self.assertEqual(response.headers.get("X-Page-Size"), "1")

    def test_n_plus_one_safe(self):
        # Создаём ещё клиентов; запрос должен оставаться <= 4 SQL-запросов
        for i in range(10):
            CustomUser.objects.create(full_name=f"User {i}", phone=f"+7 {i:04d}", card_id=f"LC-{i:06d}")
        with self.assertNumQueries(4):  # session+staff lookup + count + select clients
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)

    def test_serializer_outputs_camelcase(self):
        response = self.client.get(self.url)
        first = response.data["results"][0]
        self.assertIn("rfmSegment", first)
        self.assertIn("purchaseCount", first)
        self.assertIn("lastOrder", first)
```

- [ ] **Step 6: Запуск**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_clients -v 1`
Expected: 7 passed. Если `assertNumQueries(4)` упадёт с другим числом — поправить число (`select_related` уменьшает запросы), но точно <10.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/crm_api/serializers/client.py backend/apps/crm_api/views/clients.py backend/apps/crm_api/urls.py backend/apps/crm_api/tests/test_clients.py backend/apps/crm_api/tests/test_permissions.py
git commit -m "feat(crm-api): add clients list endpoint with search/segment filter/pagination"
```

---

## Task 8: Client detail endpoint

**Files:**
- Modify: `backend/apps/crm_api/serializers/client.py` (добавить ClientDetailSerializer)
- Modify: `backend/apps/crm_api/views/clients.py` (добавить ClientDetailView)
- Modify: `backend/apps/crm_api/tests/test_clients.py` (добавить ClientDetailTests)
- Modify: `backend/apps/crm_api/urls.py`
- Modify: `backend/apps/crm_api/tests/test_permissions.py`

- [ ] **Step 1: Detail-сериализатор**

В `backend/apps/crm_api/serializers/client.py` добавить:
```python
class _OrderInClientSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source="created_at")
    amount = serializers.SerializerMethodField()
    status = serializers.CharField()

    def get_id(self, obj) -> str:
        return f"ORD-{obj.id}"

    def get_amount(self, obj) -> int:
        return int(obj.total_price or 0)


class _CampaignInClientSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    name = serializers.CharField()
    rules = serializers.SerializerMethodField()

    def get_id(self, obj) -> str:
        return f"CMP-{obj.id}"

    def get_rules(self, obj) -> str:
        first = obj.rules.first() if hasattr(obj, "rules") else None
        if not first:
            return ""
        return f"{first.reward_type}: {first.reward_value or first.reward_percent or ''}".strip()


class ClientDetailSerializer(ClientListSerializer):
    telegramId = serializers.IntegerField(source="telegram_id", default=None)
    preferences = serializers.SerializerMethodField()
    orders = serializers.SerializerMethodField()
    activeCampaigns = serializers.SerializerMethodField()

    class Meta(ClientListSerializer.Meta):
        fields = ClientListSerializer.Meta.fields + ["telegramId", "preferences", "orders", "activeCampaigns"]

    def get_preferences(self, obj) -> dict:
        return {
            "push": bool(obj.general_enabled),
            "telegram": bool(obj.telegram_id),
            "email": bool(obj.promo_enabled),
            "sms": False,
        }

    def get_orders(self, obj) -> list[dict]:
        orders = obj.orders.order_by("-created_at")[:20]
        return _OrderInClientSerializer(orders, many=True).data

    def get_activeCampaigns(self, obj) -> list[dict]:
        # Активные кампании: все is_active=True, аудитория совпадает с RFM-сегментом клиента
        from apps.campaigns.models import Campaign
        segment = _segment_label(obj)
        if segment == "—":
            return []
        qs = Campaign.objects.filter(is_active=True, rfm_segment=segment).prefetch_related("rules")[:10]
        return _CampaignInClientSerializer(qs, many=True).data
```

- [ ] **Step 2: View**

В `backend/apps/crm_api/views/clients.py` добавить:
```python
from rest_framework.generics import RetrieveAPIView
from rest_framework.exceptions import NotFound

from apps.crm_api.serializers.client import ClientDetailSerializer


class ClientDetailView(RetrieveAPIView, CRMAPIView):
    """GET /api/crm/clients/<card_id>/ — карточка клиента CRM."""

    serializer_class = ClientDetailSerializer
    lookup_field = "card_id"
    lookup_url_kwarg = "card_id"

    def get_queryset(self):
        return (
            CustomUser.objects
            .select_related("rfm_profile")
            .prefetch_related("orders")
        )

    def get_object(self):
        try:
            return super().get_object()
        except CustomUser.DoesNotExist:
            raise NotFound("Клиент не найден")
```

- [ ] **Step 3: URL**

В `backend/apps/crm_api/urls.py`:
```python
from apps.crm_api.views.clients import ClientListView, ClientDetailView
# ...
path("clients/<str:card_id>/", ClientDetailView.as_view(), name="clients-detail"),
```

- [ ] **Step 4: Permission-тест**

В `test_permissions.py`, добавить (использовать существующий card_id из setUp нет смысла — для permission-теста достаточно несуществующего, ожидаем 200/404 — оба валидны для staff):

```python
("crm_api:clients-detail", {"card_id": "LC-000001"}),
```

- [ ] **Step 5: Failing-тест detail**

В `test_clients.py` добавить:
```python
class ClientDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = CustomUser.objects.create(
            full_name="Алиса Иванова", phone="+7 914 111-22-33",
            card_id="LC-000001", bonuses=Decimal("500"),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())

    def test_detail_returns_full_data(self):
        url = reverse("crm_api:clients-detail", kwargs={"card_id": "LC-000001"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], "LC-000001")
        self.assertEqual(response.data["name"], "Алиса Иванова")
        self.assertEqual(response.data["bonus"], 500)
        self.assertIn("preferences", response.data)
        self.assertIn("orders", response.data)
        self.assertIn("activeCampaigns", response.data)

    def test_detail_unknown_returns_404(self):
        url = reverse("crm_api:clients-detail", kwargs={"card_id": "LC-NO-SUCH"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "Клиент не найден")

    def test_detail_n_plus_one_safe(self):
        url = reverse("crm_api:clients-detail", kwargs={"card_id": "LC-000001"})
        with self.assertNumQueries(5):  # session/user + client + rfm + orders + campaigns
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
```

- [ ] **Step 6: Запуск**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_clients -v 1`
Expected: 10 passed. Подкорректировать `assertNumQueries(N)` если число другое.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/crm_api/serializers/client.py backend/apps/crm_api/views/clients.py backend/apps/crm_api/urls.py backend/apps/crm_api/tests/test_clients.py backend/apps/crm_api/tests/test_permissions.py
git commit -m "feat(crm-api): add client detail endpoint with orders and active campaigns"
```

---

## Task 9: Orders list endpoint

**Files:**
- Create: `backend/apps/crm_api/serializers/order.py`
- Create: `backend/apps/crm_api/views/orders.py`
- Create: `backend/apps/crm_api/tests/test_orders.py`
- Modify: `backend/apps/crm_api/urls.py`
- Modify: `backend/apps/crm_api/tests/test_permissions.py`

- [ ] **Step 1: Serializer**

`backend/apps/crm_api/serializers/order.py`:
```python
from rest_framework import serializers

from apps.orders.models import Order


class OrderListSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source="created_at")
    clientId = serializers.SerializerMethodField()
    clientName = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    purchaseType = serializers.CharField(source="fulfillment_type")
    items = serializers.SerializerMethodField()
    payment = serializers.CharField(source="payment_method")
    courier = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "date", "clientId", "clientName", "amount",
            "status", "purchaseType", "items", "address", "payment", "courier",
        ]

    def get_id(self, obj) -> str:
        return f"ORD-{obj.id}"

    def get_clientId(self, obj):
        return obj.customer.card_id if obj.customer_id else None

    def get_clientName(self, obj):
        return (obj.customer.full_name if obj.customer_id else "") or ""

    def get_amount(self, obj) -> int:
        return int(obj.total_price or 0)

    def get_items(self, obj) -> int:
        return obj.items.count() if hasattr(obj, "_prefetched_items_count") is False else obj._prefetched_items_count

    def get_courier(self, obj) -> str:
        return str(obj.delivered_by) if obj.delivered_by else "—"
```

- [ ] **Step 2: View**

`backend/apps/crm_api/views/orders.py`:
```python
from django.db.models import Count
from rest_framework.generics import ListAPIView

from apps.crm_api.pagination import CRMHeaderPagination
from apps.crm_api.serializers.order import OrderListSerializer
from apps.crm_api.views._base import CRMAPIView
from apps.orders.models import Order


class OrderListView(ListAPIView, CRMAPIView):
    """GET /api/crm/orders/?status=&purchaseType=&page=&page_size= — заказы CRM."""

    serializer_class = OrderListSerializer
    pagination_class = CRMHeaderPagination

    def get_queryset(self):
        qs = (
            Order.objects
            .select_related("customer")
            .annotate(_prefetched_items_count=Count("items"))
            .order_by("-created_at")
        )
        status = self.request.query_params.get("status", "").strip()
        ptype = self.request.query_params.get("purchaseType", "").strip()
        if status and status != "Все":
            qs = qs.filter(status=status)
        if ptype and ptype != "Все":
            qs = qs.filter(fulfillment_type=ptype)
        return qs
```

- [ ] **Step 3: URL + permission-тест**

В `urls.py`:
```python
from apps.crm_api.views.orders import OrderListView
# ...
path("orders/", OrderListView.as_view(), name="orders-list"),
```

В `test_permissions.py`:
```python
("crm_api:orders-list", {}),
```

- [ ] **Step 4: Тест**

`backend/apps/crm_api/tests/test_orders.py`:
```python
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff
from apps.main.models import CustomUser
from apps.orders.models import Order


class OrderListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = CustomUser.objects.create(full_name="Алиса", phone="+7 1", card_id="LC-001")
        cls.bob = CustomUser.objects.create(full_name="Боб", phone="+7 2", card_id="LC-002")
        cls.o1 = Order.objects.create(
            customer=cls.alice, status="new", address="x", phone="+7 1",
            total_price=Decimal("1500"), products_price=Decimal("1500"),
            fulfillment_type="delivery",
        )
        cls.o2 = Order.objects.create(
            customer=cls.bob, status="completed", address="x", phone="+7 2",
            total_price=Decimal("2500"), products_price=Decimal("2500"),
            fulfillment_type="pickup",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:orders-list")

    def test_list_returns_orders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = {o["id"] for o in response.data["results"]}
        self.assertEqual(ids, {f"ORD-{self.o1.id}", f"ORD-{self.o2.id}"})

    def test_filter_by_status(self):
        response = self.client.get(self.url, {"status": "new"})
        self.assertEqual({o["status"] for o in response.data["results"]}, {"new"})

    def test_filter_by_purchase_type(self):
        response = self.client.get(self.url, {"purchaseType": "pickup"})
        self.assertEqual({o["purchaseType"] for o in response.data["results"]}, {"pickup"})

    def test_payload_shape(self):
        response = self.client.get(self.url)
        first = response.data["results"][0]
        self.assertIn("clientId", first)
        self.assertIn("clientName", first)
        self.assertIn("amount", first)

    def test_n_plus_one_safe(self):
        for i in range(10):
            Order.objects.create(
                customer=self.alice, status="new", address="x", phone="+7",
                total_price=Decimal("100"), products_price=Decimal("100"), fulfillment_type="delivery",
            )
        with self.assertNumQueries(4):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
```

- [ ] **Step 5: Запуск + Commit**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_orders -v 1`
Expected: 5 passed.

```bash
git add backend/apps/crm_api/serializers/order.py backend/apps/crm_api/views/orders.py backend/apps/crm_api/urls.py backend/apps/crm_api/tests/test_orders.py backend/apps/crm_api/tests/test_permissions.py
git commit -m "feat(crm-api): add orders list endpoint with status/purchaseType filters"
```

---

## Task 10: Campaigns list endpoint

**Files:**
- Create: `backend/apps/crm_api/serializers/campaign.py`
- Create: `backend/apps/crm_api/views/campaigns.py`
- Create: `backend/apps/crm_api/tests/test_campaigns.py`
- Modify: `backend/apps/crm_api/urls.py`
- Modify: `backend/apps/crm_api/tests/test_permissions.py`

- [ ] **Step 1: Serializer**

`backend/apps/crm_api/serializers/campaign.py`:
```python
from rest_framework import serializers

from apps.campaigns.models import Campaign


class CampaignListSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    period = serializers.SerializerMethodField()
    reach = serializers.IntegerField(read_only=True)  # из annotate
    used = serializers.IntegerField(read_only=True)   # из annotate
    segment = serializers.SerializerMethodField()
    audience = serializers.SerializerMethodField()
    rules = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "slug", "status",
            "period", "reach", "used", "segment", "audience", "rules", "priority",
        ]

    def get_id(self, obj) -> str:
        return f"CMP-{obj.id}"

    def get_status(self, obj) -> str:
        return "active" if obj.is_active else "finished"

    def get_period(self, obj) -> dict:
        return {
            "from": obj.start_at.date().isoformat() if obj.start_at else None,
            "to": obj.end_at.date().isoformat() if obj.end_at else None,
        }

    def get_segment(self, obj) -> str:
        if obj.rfm_segment:
            return obj.rfm_segment
        return obj.segment.name if obj.segment_id else ""

    def get_audience(self, obj) -> str:
        if obj.rfm_segment:
            return f"RFM: {obj.rfm_segment}"
        if obj.segment_id:
            return f"Сегмент: {obj.segment.name}"
        return "Все клиенты"

    def get_rules(self, obj) -> str:
        first = next(iter(obj.rules.all()), None) if hasattr(obj, "rules") else None
        if not first:
            return ""
        if first.reward_percent:
            return f"{first.reward_percent}% бонусов"
        if first.reward_value:
            return f"+{int(first.reward_value)} бонусов"
        return first.reward_type
```

- [ ] **Step 2: View**

`backend/apps/crm_api/views/campaigns.py`:
```python
from django.db.models import Count, Q
from rest_framework.generics import ListAPIView

from apps.campaigns.models import Campaign
from apps.crm_api.pagination import CRMHeaderPagination
from apps.crm_api.serializers.campaign import CampaignListSerializer
from apps.crm_api.views._base import CRMAPIView


class CampaignListView(ListAPIView, CRMAPIView):
    """GET /api/crm/campaigns/?status=&page=&page_size= — кампании CRM."""

    serializer_class = CampaignListSerializer
    pagination_class = CRMHeaderPagination

    def get_queryset(self):
        qs = (
            Campaign.objects
            .select_related("segment")
            .prefetch_related("rules")
            .annotate(
                reach=Count("assignments", distinct=True),
                used=Count("assignments", filter=Q(assignments__used=True), distinct=True),
            )
            .order_by("-priority", "-id")
        )
        status = self.request.query_params.get("status", "").strip()
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "finished":
            qs = qs.filter(is_active=False)
        # status == "all" / "" — без фильтра
        return qs
```

- [ ] **Step 3: URL + permission-тест**

В `urls.py`:
```python
from apps.crm_api.views.campaigns import CampaignListView
path("campaigns/", CampaignListView.as_view(), name="campaigns-list"),
```

В `test_permissions.py`:
```python
("crm_api:campaigns-list", {}),
```

- [ ] **Step 4: Тест**

`backend/apps/crm_api/tests/test_campaigns.py`:
```python
from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.campaigns.models import Campaign, CampaignRule, CustomerCampaignAssignment
from apps.crm_api.tests._factories import create_staff
from apps.main.models import CustomUser


class CampaignListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.c1 = Campaign.objects.create(
            name="Весенний кешбэк",
            slug="spring-cb",
            audience_type="rfm",
            rfm_segment="Чемпионы",
            push_title="t",
            push_body="b",
            start_at=now,
            end_at=now + timedelta(days=30),
            priority=200,
            is_active=True,
        )
        CampaignRule.objects.create(
            campaign=cls.c1, reward_type="bonus_percent", reward_percent=Decimal("7"), is_active=True,
        )
        cls.c2 = Campaign.objects.create(
            name="Старая",
            slug="old",
            audience_type="rfm",
            rfm_segment="Лояльные",
            push_title="t", push_body="b",
            start_at=now - timedelta(days=60), end_at=now - timedelta(days=30),
            priority=100, is_active=False,
        )
        # Назначения
        u = CustomUser.objects.create(full_name="X", phone="+7", card_id="LC-X")
        CustomerCampaignAssignment.objects.create(customer=u, campaign=cls.c1, used=False)
        CustomerCampaignAssignment.objects.create(customer=u, campaign=cls.c1, used=True)

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:campaigns-list")

    def test_list_returns_campaigns(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = {c["id"] for c in response.data["results"]}
        self.assertEqual(ids, {f"CMP-{self.c1.id}", f"CMP-{self.c2.id}"})

    def test_filter_active(self):
        response = self.client.get(self.url, {"status": "active"})
        self.assertEqual({c["status"] for c in response.data["results"]}, {"active"})

    def test_reach_used_counts(self):
        response = self.client.get(self.url, {"status": "active"})
        c = response.data["results"][0]
        self.assertEqual(c["reach"], 2)
        self.assertEqual(c["used"], 1)

    def test_rules_serialized_first(self):
        response = self.client.get(self.url, {"status": "active"})
        c = response.data["results"][0]
        self.assertIn("7", c["rules"])

    def test_audience_field(self):
        response = self.client.get(self.url, {"status": "active"})
        c = response.data["results"][0]
        self.assertEqual(c["audience"], "RFM: Чемпионы")
```

- [ ] **Step 5: Запуск + Commit**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_campaigns -v 1`
Expected: 5 passed.

```bash
git add backend/apps/crm_api/serializers/campaign.py backend/apps/crm_api/views/campaigns.py backend/apps/crm_api/urls.py backend/apps/crm_api/tests/test_campaigns.py backend/apps/crm_api/tests/test_permissions.py
git commit -m "feat(crm-api): add campaigns list with status filter and reach/used aggregates"
```

---

## Task 11: Broadcasts history endpoint

**Files:**
- Create: `backend/apps/crm_api/serializers/broadcast.py`
- Create: `backend/apps/crm_api/views/broadcasts.py`
- Create: `backend/apps/crm_api/tests/test_broadcasts.py`
- Modify: `backend/apps/crm_api/urls.py`
- Modify: `backend/apps/crm_api/tests/test_permissions.py`

- [ ] **Step 1: Serializer**

`backend/apps/crm_api/serializers/broadcast.py`:
```python
from rest_framework import serializers

from apps.main.models import BroadcastMessage


class BroadcastHistorySerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    sentAt = serializers.DateTimeField(source="created_at")
    segment = serializers.SerializerMethodField()
    channel = serializers.SerializerMethodField()
    reach = serializers.IntegerField(read_only=True)
    opened = serializers.IntegerField(read_only=True)
    clicked = serializers.SerializerMethodField()

    class Meta:
        model = BroadcastMessage
        fields = ["id", "sentAt", "segment", "channel", "reach", "opened", "clicked"]

    def get_id(self, obj) -> str:
        return f"BR-{obj.id}"

    def get_segment(self, obj) -> str:
        if obj.send_to_all:
            return "Все клиенты"
        return "Список ID"

    def get_channel(self, obj) -> str:
        # CATEGORY_CHOICES: general/promo/news. Для UI показываем как канал —
        # фактически рассылки уходят в Telegram + push (см. apps/notifications),
        # для CRM-history достаточно категории.
        return obj.get_category_display() if hasattr(obj, "get_category_display") else (obj.category or "general")

    def get_clicked(self, obj) -> int:
        # В модели нет поля clicked_at — возвращаем 0 как стаб.
        return 0
```

- [ ] **Step 2: View**

`backend/apps/crm_api/views/broadcasts.py`:
```python
from django.db.models import Count, Q
from rest_framework.generics import ListAPIView

from apps.crm_api.pagination import CRMHeaderPagination
from apps.crm_api.serializers.broadcast import BroadcastHistorySerializer
from apps.crm_api.views._base import CRMAPIView
from apps.main.models import BroadcastMessage


class BroadcastHistoryView(ListAPIView, CRMAPIView):
    """GET /api/crm/broadcasts/history/?page=&page_size= — история рассылок."""

    serializer_class = BroadcastHistorySerializer
    pagination_class = CRMHeaderPagination

    def get_queryset(self):
        return (
            BroadcastMessage.objects
            .annotate(
                reach=Count("deliveries", distinct=True),
                opened=Count("deliveries", filter=Q(deliveries__opened_at__isnull=False), distinct=True),
            )
            .order_by("-created_at")
        )
```

- [ ] **Step 3: URL + permission-тест**

В `urls.py`:
```python
from apps.crm_api.views.broadcasts import BroadcastHistoryView
path("broadcasts/history/", BroadcastHistoryView.as_view(), name="broadcasts-history"),
```

В `test_permissions.py`:
```python
("crm_api:broadcasts-history", {}),
```

- [ ] **Step 4: Тест**

`backend/apps/crm_api/tests/test_broadcasts.py`:
```python
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff
from apps.main.models import BroadcastMessage, NewsletterDelivery, CustomUser


class BroadcastHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        u = CustomUser.objects.create(full_name="X", phone="+7", card_id="LC-X")
        cls.b1 = BroadcastMessage.objects.create(message_text="Скидки", category="promo", send_to_all=True)
        # 2 доставки, одна открыта
        NewsletterDelivery.objects.create(message=cls.b1, customer=u, channel="telegram", opened_at=timezone.now())
        NewsletterDelivery.objects.create(message=cls.b1, customer=u, channel="telegram")

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:broadcasts-history")

    def test_list_returns_broadcasts(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_aggregates_reach_and_opened(self):
        response = self.client.get(self.url)
        b = response.data["results"][0]
        self.assertEqual(b["reach"], 2)
        self.assertEqual(b["opened"], 1)

    def test_clicked_is_stub_zero(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["results"][0]["clicked"], 0)
```

- [ ] **Step 5: Запуск + Commit**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_broadcasts -v 1`
Expected: 3 passed.

```bash
git add backend/apps/crm_api/serializers/broadcast.py backend/apps/crm_api/views/broadcasts.py backend/apps/crm_api/urls.py backend/apps/crm_api/tests/test_broadcasts.py backend/apps/crm_api/tests/test_permissions.py
git commit -m "feat(crm-api): add broadcasts history endpoint with reach/opened aggregates"
```

---

## Task 12: Categories list + detail endpoints (с стаб-полями ABC/XYZ)

**Files:**
- Create: `backend/apps/crm_api/serializers/category.py`
- Create: `backend/apps/crm_api/views/categories.py`
- Create: `backend/apps/crm_api/tests/test_categories.py`
- Modify: `backend/apps/crm_api/urls.py`
- Modify: `backend/apps/crm_api/tests/test_permissions.py`

В CRM-схеме каждая категория имеет поля `revenue/cogs/share/turnover/abc/xyz/trend`, которых **нет в модели** `apps.main.Category`. На M1 отдаём **стабы с реальной структурой**, чтобы фронт работал. Реальные расчёты — задача отдельной аналитики (M2/M5).

- [ ] **Step 1: Serializer**

`backend/apps/crm_api/serializers/category.py`:
```python
from rest_framework import serializers

from apps.main.models import Category, Product


# Стабы для аналитических полей. Распределяем по позиции (sort_order).
# Реальные расчёты — отдельный milestone.
_STUB_TREND = [42, 48, 51, 55, 58, 62, 65, 68, 72, 75, 78, 82]
_STUB_ABC_BY_INDEX = ["A", "A", "A", "B", "B", "B", "B", "C", "C", "C", "C", "C"]
_STUB_XYZ_BY_INDEX = ["X", "X", "Y", "Y", "X", "Y", "Z", "Y", "X", "Z", "X", "Y"]


def _slug_for(category) -> str:
    return f"cat-{category.external_id or category.id}"


def _stub_index(idx: int, default: str) -> str:
    return idx % 12  # noqa


class CategoryListSerializer(serializers.ModelSerializer):
    slug = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()
    skus = serializers.IntegerField(read_only=True)  # из annotate
    revenue = serializers.SerializerMethodField()
    cogs = serializers.SerializerMethodField()
    share = serializers.SerializerMethodField()
    turnover = serializers.SerializerMethodField()
    abc = serializers.SerializerMethodField()
    xyz = serializers.SerializerMethodField()
    trend = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "slug", "code", "name", "skus", "revenue", "cogs", "share", "turnover", "abc", "xyz", "trend"]

    def get_slug(self, obj) -> str:
        return _slug_for(obj)

    def get_code(self, obj) -> str:
        return obj.external_id or str(obj.id)

    def get_revenue(self, obj) -> int:
        # Стаб: 100k * (sort_order+1). Реальный расчёт — M2.
        return (obj.sort_order + 1) * 100_000

    def get_cogs(self, obj) -> int:
        return int(self.get_revenue(obj) * 0.7)

    def get_share(self, obj) -> float:
        # Стаб: распределение от sort_order
        return round(8.0 - obj.sort_order * 0.3, 1)

    def get_turnover(self, obj) -> float:
        return 5.0

    def get_abc(self, obj) -> str:
        return _STUB_ABC_BY_INDEX[obj.sort_order % 12]

    def get_xyz(self, obj) -> str:
        return _STUB_XYZ_BY_INDEX[obj.sort_order % 12]

    def get_trend(self, obj) -> list[int]:
        return _STUB_TREND


class _SkuInCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="product_code")
    sales30d = serializers.SerializerMethodField()
    units30d = serializers.SerializerMethodField()
    abc = serializers.SerializerMethodField()
    xyz = serializers.SerializerMethodField()
    suggestedOrder = serializers.SerializerMethodField()
    stockDays = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()
    spark = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "stock", "sales30d", "units30d",
            "abc", "xyz", "suggestedOrder", "stockDays", "supplier", "spark",
        ]

    # Все аналитические поля — стабы. Реальный источник появится в M2.
    def get_sales30d(self, obj) -> int:
        return int((obj.price or 0) * 100)

    def get_units30d(self, obj) -> int:
        return 50

    def get_abc(self, obj) -> str:
        return "A"

    def get_xyz(self, obj) -> str:
        return "X"

    def get_suggestedOrder(self, obj) -> int:
        return 100

    def get_stockDays(self, obj) -> float:
        return 2.5

    def get_supplier(self, obj) -> str:
        return "—"

    def get_spark(self, obj) -> list[int]:
        return _STUB_TREND


class CategoryDetailSerializer(CategoryListSerializer):
    skuList = serializers.SerializerMethodField()

    class Meta(CategoryListSerializer.Meta):
        fields = CategoryListSerializer.Meta.fields + ["skuList"]

    def get_skuList(self, obj) -> list[dict]:
        products = list(obj.products.filter(is_active=True)[:50])
        return _SkuInCategorySerializer(products, many=True).data
```

- [ ] **Step 2: Views**

`backend/apps/crm_api/views/categories.py`:
```python
from django.db.models import Count, Q
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.crm_api.serializers.category import CategoryDetailSerializer, CategoryListSerializer
from apps.crm_api.views._base import CRMAPIView
from apps.main.models import Category


class CategoryListView(ListAPIView, CRMAPIView):
    """GET /api/crm/categories/ — без пагинации (категорий обычно <100)."""

    serializer_class = CategoryListSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True)
            .annotate(skus=Count("products", filter=Q(products__is_active=True)))
            .order_by("sort_order", "name")
        )


class CategoryDetailView(RetrieveAPIView, CRMAPIView):
    """GET /api/crm/categories/<slug>/ — карточка категории + SKU."""

    serializer_class = CategoryDetailSerializer

    def get_object(self):
        slug = self.kwargs["slug"]
        if not slug.startswith("cat-"):
            raise NotFound("Категория не найдена")
        ext = slug[4:]
        qs = (
            Category.objects.filter(is_active=True)
            .annotate(skus=Count("products", filter=Q(products__is_active=True)))
            .prefetch_related("products")
        )
        cat = qs.filter(external_id=ext).first()
        if cat is None and ext.isdigit():
            cat = qs.filter(id=int(ext)).first()
        if cat is None:
            raise NotFound("Категория не найдена")
        return cat
```

- [ ] **Step 3: URL + permission-тест**

В `urls.py`:
```python
from apps.crm_api.views.categories import CategoryListView, CategoryDetailView
path("categories/",                CategoryListView.as_view(),   name="categories-list"),
path("categories/<slug:slug>/",    CategoryDetailView.as_view(), name="categories-detail"),
```

В `test_permissions.py`:
```python
("crm_api:categories-list", {}),
("crm_api:categories-detail", {"slug": "cat-1"}),
```

- [ ] **Step 4: Тест**

`backend/apps/crm_api/tests/test_categories.py`:
```python
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff
from apps.main.models import Category, Product


class CategoryListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dairy = Category.objects.create(name="Молочные", external_id="01", sort_order=0, is_active=True)
        cls.bread = Category.objects.create(name="Хлеб", external_id="02", sort_order=1, is_active=True)
        Product.objects.create(name="Молоко", price=Decimal("100"), category=cls.dairy, is_active=True, store_id=1)
        Product.objects.create(name="Кефир", price=Decimal("90"), category=cls.dairy, is_active=True, store_id=1)
        Product.objects.create(name="Багет", price=Decimal("60"), category=cls.bread, is_active=True, store_id=1)

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:categories-list")

    def test_list_returns_categories_with_skus_count(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        by_slug = {c["slug"]: c for c in response.data["results"]}
        self.assertEqual(by_slug["cat-01"]["skus"], 2)
        self.assertEqual(by_slug["cat-02"]["skus"], 1)

    def test_list_no_pagination(self):
        response = self.client.get(self.url)
        # ответ — простой массив или {"results": [...]}; проверяем "results" наличие
        self.assertIn("results", response.data)

    def test_stub_fields_present(self):
        response = self.client.get(self.url)
        first = response.data["results"][0]
        for f in ("revenue", "cogs", "share", "turnover", "abc", "xyz", "trend"):
            self.assertIn(f, first)


class CategoryDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dairy = Category.objects.create(name="Молочные", external_id="01", sort_order=0, is_active=True)
        Product.objects.create(name="Молоко", price=Decimal("100"), category=cls.dairy, is_active=True, store_id=1)

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())

    def test_detail_returns_skus(self):
        url = reverse("crm_api:categories-detail", kwargs={"slug": "cat-01"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], "cat-01")
        self.assertEqual(len(response.data["skuList"]), 1)

    def test_detail_404_for_unknown(self):
        url = reverse("crm_api:categories-detail", kwargs={"slug": "cat-no-such"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "Категория не найдена")
```

- [ ] **Step 5: Запуск + Commit**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api.tests.test_categories -v 1`
Expected: 5 passed.

```bash
git add backend/apps/crm_api/serializers/category.py backend/apps/crm_api/views/categories.py backend/apps/crm_api/urls.py backend/apps/crm_api/tests/test_categories.py backend/apps/crm_api/tests/test_permissions.py
git commit -m "feat(crm-api): add categories list+detail endpoints with stub analytics fields"
```

---

## Task 13: ABC/XYZ matrix endpoint (стаб)

**Files:**
- Create: `backend/apps/crm_api/serializers/abc_xyz.py`
- Create: `backend/apps/crm_api/views/abc_xyz.py`
- Create: `backend/apps/crm_api/tests/test_abc_xyz.py`
- Modify: `backend/apps/crm_api/urls.py`
- Modify: `backend/apps/crm_api/tests/test_permissions.py`

ABC/XYZ-классификация SKU требует отдельной аналитической инфраструктуры (apps/showcase или новый сервис). На M1 — стаб с реальной структурой контракта.

- [ ] **Step 1: View с inline-стабом**

`backend/apps/crm_api/views/abc_xyz.py`:
```python
from rest_framework.response import Response

from apps.crm_api.views._base import CRMAPIView


# Стаб-матрица. Реальная классификация — отдельный milestone.
_STUB_MATRIX_SKU = {
    "AX": 84, "AY": 56, "AZ": 18,
    "BX": 142, "BY": 168, "BZ": 92,
    "CX": 218, "CY": 384, "CZ": 240,
}
_STUB_MATRIX_REVENUE = {
    "AX": 4_830_000, "AY": 2_980_000, "AZ": 840_000,
    "BX": 1_640_000, "BY": 1_390_000, "BZ": 680_000,
    "CX": 490_000, "CY": 470_000, "CZ": 290_000,
}


def _share_from_counts(matrix: dict[str, int]) -> dict[str, float]:
    total = sum(matrix.values()) or 1
    return {k: round(v * 100.0 / total, 1) for k, v in matrix.items()}


class AbcXyzView(CRMAPIView):
    """GET /api/crm/abc-xyz/ — матрица распределения SKU по ABC×XYZ.

    На M1 возвращает стаб-данные. Реальная классификация — отдельная
    задача (требует pipeline для расчёта по продажам)."""

    def get(self, request):
        return Response({
            "matrixSku": _STUB_MATRIX_SKU,
            "matrixRevenue": _STUB_MATRIX_REVENUE,
            "matrixShare": _share_from_counts(_STUB_MATRIX_SKU),
        })
```

- [ ] **Step 2: URL + permission-тест**

В `urls.py`:
```python
from apps.crm_api.views.abc_xyz import AbcXyzView
path("abc-xyz/", AbcXyzView.as_view(), name="abc-xyz"),
```

В `test_permissions.py`:
```python
("crm_api:abc-xyz", {}),
```

- [ ] **Step 3: Тест**

`backend/apps/crm_api/tests/test_abc_xyz.py`:
```python
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff


class AbcXyzTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:abc-xyz")

    def test_returns_three_matrices(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for key in ("matrixSku", "matrixRevenue", "matrixShare"):
            self.assertIn(key, response.data)
            self.assertEqual(set(response.data[key].keys()),
                             {"AX","AY","AZ","BX","BY","BZ","CX","CY","CZ"})

    def test_share_sums_to_100(self):
        response = self.client.get(self.url)
        s = sum(response.data["matrixShare"].values())
        self.assertAlmostEqual(s, 100.0, places=0)
```

- [ ] **Step 4: Запуск + Commit**

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api -v 1`
Expected: все 30+ тестов зелёные.

```bash
git add backend/apps/crm_api/views/abc_xyz.py backend/apps/crm_api/urls.py backend/apps/crm_api/tests/test_abc_xyz.py backend/apps/crm_api/tests/test_permissions.py
git commit -m "feat(crm-api): add abc-xyz matrix endpoint (stub data, real analytics in M2)"
```

---

## Task 14: Установить deps + Vite proxy + QueryClient

**Files:**
- Modify: `crm-web/package.json`
- Modify: `crm-web/vite.config.js`
- Modify: `crm-web/src/main.jsx`

- [ ] **Step 1: Установить react-query и MSW**

Run: `cd crm-web && npm install @tanstack/react-query@^5 msw@^2 --save`
Expected: deps добавлены в `package.json`.

- [ ] **Step 2: Vite proxy для dev**

В `crm-web/vite.config.js` добавить `proxy` в секцию `server`:
```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.js'],
  },
});
```

- [ ] **Step 3: QueryClientProvider в main.jsx**

`crm-web/src/main.jsx`:
```jsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import './styles/tokens.css';
import './styles/reset.css';
import './styles/global.css';
import App from './App.jsx';
import { ErrorBoundary } from './components/ErrorBoundary.jsx';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
});

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>
);
```

- [ ] **Step 4: Smoke — build не падает**

Run: `cd crm-web && npm run build 2>&1 | tail -5`
Expected: `✓ built in ...` без ошибок.

- [ ] **Step 5: Тесты не упали (фикстуры ещё подключены)**

Run: `cd crm-web && npm run test 2>&1 | tail -5`
Expected: 24 теста зелёные.

- [ ] **Step 6: Commit**

```bash
cd /home/oem/lakshmi_project_dev/lakshmi-bot
git add crm-web/package.json crm-web/package-lock.json crm-web/vite.config.js crm-web/src/main.jsx
git commit -m "chore(crm-web): add react-query and MSW deps; configure Vite proxy"
```

---

## Task 15: API client (fetch-обёртка с CSRF)

**Files:**
- Create: `crm-web/src/api/client.js`
- Create: `crm-web/src/api/auth.js`
- Create: `crm-web/src/api/dashboard.js`
- Create: `crm-web/src/api/clients.js`
- Create: `crm-web/src/api/orders.js`
- Create: `crm-web/src/api/campaigns.js`
- Create: `crm-web/src/api/broadcasts.js`
- Create: `crm-web/src/api/categories.js`
- Create: `crm-web/src/api/abcXyz.js`

- [ ] **Step 1: Базовый client**

`crm-web/src/api/client.js`:
```js
const BASE = import.meta.env.VITE_API_BASE || '/api/crm';

export class ApiError extends Error {
  constructor(status, body, message) {
    super(message || `API error ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export class UnauthorizedError extends ApiError {
  constructor(body) {
    super(401, body, 'Unauthorized');
    this.name = 'UnauthorizedError';
  }
}

export class ForbiddenError extends ApiError {
  constructor(body) {
    super(403, body, 'Forbidden');
    this.name = 'ForbiddenError';
  }
}

export class NotFoundError extends ApiError {
  constructor(body) {
    super(404, body, 'Not Found');
    this.name = 'NotFoundError';
  }
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^|;)\\s*${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

async function parseBody(response) {
  const ct = response.headers.get('content-type') || '';
  if (response.status === 204) return null;
  if (ct.includes('application/json')) return response.json();
  return response.text();
}

function paginationFromHeaders(headers) {
  const total = parseInt(headers.get('X-Total-Count') || '0', 10);
  const page = parseInt(headers.get('X-Page') || '1', 10);
  const pageSize = parseInt(headers.get('X-Page-Size') || '0', 10) || total || 1;
  return {
    total,
    page,
    pageSize,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
  };
}

async function request(path, { method = 'GET', body, query } = {}) {
  let url = `${BASE}${path}`;
  if (query) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') qs.set(k, v);
    }
    const qsString = qs.toString();
    if (qsString) url += `?${qsString}`;
  }

  const headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
  if (method !== 'GET') {
    const csrf = getCookie('csrftoken');
    if (csrf) headers['X-CSRFToken'] = csrf;
  }

  const response = await fetch(url, {
    method,
    headers,
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errBody = await parseBody(response).catch(() => null);
    if (response.status === 401) throw new UnauthorizedError(errBody);
    if (response.status === 403) throw new ForbiddenError(errBody);
    if (response.status === 404) throw new NotFoundError(errBody);
    throw new ApiError(response.status, errBody);
  }

  const data = await parseBody(response);
  return { data, pagination: paginationFromHeaders(response.headers) };
}

export const apiGet = (path, query) => request(path, { query });
export const apiPost = (path, body) => request(path, { method: 'POST', body });
```

- [ ] **Step 2: Resource-модули**

`crm-web/src/api/auth.js`:
```js
import { apiGet, apiPost, UnauthorizedError } from './client.js';

export async function me() {
  try {
    const { data } = await apiGet('/auth/me/');
    return data.user;
  } catch (err) {
    if (err instanceof UnauthorizedError) return null;
    throw err;
  }
}

export async function login({ email, password }) {
  const { data } = await apiPost('/auth/login/', { email, password });
  return data.user;
}

export async function logout() {
  await apiPost('/auth/logout/');
}
```

`crm-web/src/api/dashboard.js`:
```js
import { apiGet } from './client.js';

export async function getDashboard() {
  const { data } = await apiGet('/dashboard/');
  return data;
}
```

`crm-web/src/api/clients.js`:
```js
import { apiGet } from './client.js';

export async function listClients({ q, segment, page, pageSize } = {}) {
  const { data, pagination } = await apiGet('/clients/', {
    q, segment, page, page_size: pageSize,
  });
  return { results: data.results, pagination };
}

export async function getClient(cardId) {
  const { data } = await apiGet(`/clients/${encodeURIComponent(cardId)}/`);
  return data;
}
```

`crm-web/src/api/orders.js`:
```js
import { apiGet } from './client.js';

export async function listOrders({ status, purchaseType, page, pageSize } = {}) {
  const { data, pagination } = await apiGet('/orders/', {
    status, purchaseType, page, page_size: pageSize,
  });
  return { results: data.results, pagination };
}
```

`crm-web/src/api/campaigns.js`:
```js
import { apiGet } from './client.js';

export async function listCampaigns({ status, page, pageSize } = {}) {
  const { data, pagination } = await apiGet('/campaigns/', {
    status, page, page_size: pageSize,
  });
  return { results: data.results, pagination };
}
```

`crm-web/src/api/broadcasts.js`:
```js
import { apiGet } from './client.js';

export async function listBroadcastHistory({ page, pageSize } = {}) {
  const { data, pagination } = await apiGet('/broadcasts/history/', {
    page, page_size: pageSize,
  });
  return { results: data.results, pagination };
}
```

`crm-web/src/api/categories.js`:
```js
import { apiGet } from './client.js';

export async function listCategories() {
  const { data } = await apiGet('/categories/');
  return data.results;
}

export async function getCategory(slug) {
  const { data } = await apiGet(`/categories/${encodeURIComponent(slug)}/`);
  return data;
}
```

`crm-web/src/api/abcXyz.js`:
```js
import { apiGet } from './client.js';

export async function getAbcXyz() {
  const { data } = await apiGet('/abc-xyz/');
  return data;
}
```

- [ ] **Step 3: Smoke-тест unit на client.js**

`crm-web/src/__tests__/api_client.test.js`:
```js
import { describe, it, expect } from 'vitest';
import { ApiError, UnauthorizedError, ForbiddenError, NotFoundError } from '../api/client.js';

describe('API error classes', () => {
  it('exposes status', () => {
    const e = new ApiError(500, { detail: 'boom' });
    expect(e.status).toBe(500);
    expect(e.body.detail).toBe('boom');
  });

  it('UnauthorizedError is ApiError', () => {
    const e = new UnauthorizedError({});
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(401);
  });

  it('ForbiddenError, NotFoundError have right status', () => {
    expect(new ForbiddenError({}).status).toBe(403);
    expect(new NotFoundError({}).status).toBe(404);
  });
});
```

Run: `cd crm-web && npm run test -- api_client`
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add crm-web/src/api/ crm-web/src/__tests__/api_client.test.js
git commit -m "feat(crm-web): add API client with CSRF, error classes, and resource modules"
```

---

## Task 16: AuthProvider + useAuth + Splash

**Files:**
- Create: `crm-web/src/components/Splash.jsx`
- Create: `crm-web/src/auth/AuthProvider.jsx`
- Create: `crm-web/src/hooks/useAuth.js`

- [ ] **Step 1: Splash-компонент**

`crm-web/src/components/Splash.jsx`:
```jsx
import lakshmiGlyph from '../assets/lakshmi-glyph.svg';

export function Splash() {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--surface-page)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 16,
    }}>
      <img src={lakshmiGlyph} width="48" height="48" alt="" style={{ borderRadius: 8 }} />
      <div style={{ width: 32, height: 32, border: '3px solid var(--border-strong)', borderTopColor: 'var(--accent-600)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default Splash;
```

- [ ] **Step 2: useAuth hook**

`crm-web/src/hooks/useAuth.js`:
```js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as authApi from '../api/auth.js';

const ME_KEY = ['auth/me'];

export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    queryFn: authApi.me,
    retry: false,
    staleTime: 5 * 60_000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: authApi.login,
    onSuccess: (user) => {
      qc.setQueryData(ME_KEY, user);
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      qc.setQueryData(ME_KEY, null);
      qc.clear();
    },
  });
}
```

- [ ] **Step 3: AuthProvider context**

`crm-web/src/auth/AuthProvider.jsx`:
```jsx
import { createContext, useContext } from 'react';
import { useMe } from '../hooks/useAuth.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const { data: user, isLoading, isFetching } = useMe();
  const value = {
    user: user ?? null,
    isAuthenticated: !!user,
    isLoading: isLoading,
    isFetching,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be used within AuthProvider');
  return ctx;
}
```

- [ ] **Step 4: Commit**

```bash
git add crm-web/src/components/Splash.jsx crm-web/src/auth/AuthProvider.jsx crm-web/src/hooks/useAuth.js
git commit -m "feat(crm-web): add AuthProvider, useMe/useLogin/useLogout hooks, Splash"
```

---

## Task 17: ProtectedRoute + LoginScreen + /login route

**Files:**
- Create: `crm-web/src/auth/ProtectedRoute.jsx`
- Create: `crm-web/src/auth/LoginScreen.jsx`
- Modify: `crm-web/src/App.jsx`
- Modify: `crm-web/src/main.jsx` (обернуть в AuthProvider)

- [ ] **Step 1: ProtectedRoute**

`crm-web/src/auth/ProtectedRoute.jsx`:
```jsx
import { Navigate, useLocation } from 'react-router-dom';
import { Splash } from '../components/Splash.jsx';
import { useAuthContext } from './AuthProvider.jsx';

export function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuthContext();
  const location = useLocation();
  if (isLoading) return <Splash />;
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}

export default ProtectedRoute;
```

- [ ] **Step 2: LoginScreen**

`crm-web/src/auth/LoginScreen.jsx`:
```jsx
import { useState } from 'react';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useLogin } from '../hooks/useAuth.js';
import { useAuthContext } from './AuthProvider.jsx';
import { ForbiddenError, UnauthorizedError } from '../api/client.js';
import lakshmiGlyph from '../assets/lakshmi-glyph.svg';

export function LoginScreen() {
  const { isAuthenticated, isLoading } = useAuthContext();
  const navigate = useNavigate();
  const location = useLocation();
  const next = location.state?.from?.pathname || '/dashboard';
  const login = useLogin();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);

  if (isLoading) return null;
  if (isAuthenticated) return <Navigate to={next} replace />;

  const canSubmit = email.includes('@') && password.length > 0 && !login.isPending;

  function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    login.mutate(
      { email: email.trim(), password },
      {
        onSuccess: () => navigate(next, { replace: true }),
        onError: (err) => {
          if (err instanceof UnauthorizedError) setError('Неверный email или пароль');
          else if (err instanceof ForbiddenError) setError('У этого аккаунта нет доступа в CRM');
          else setError('Ошибка сервера, попробуйте позже');
        },
      },
    );
  }

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--surface-page)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <form onSubmit={handleSubmit} style={{
        width: 360,
        background: 'var(--surface-panel)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)', padding: 24,
        display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <img src={lakshmiGlyph} width="48" height="48" alt="" style={{ borderRadius: 8 }} />
          <div style={{ fontSize: 16, fontWeight: 600 }}>Lakshmi CRM</div>
          <div style={{ fontSize: 13, color: 'var(--fg-muted)' }}>Вход для менеджеров</div>
        </div>

        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Email</span>
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="manager@lakshmi.ru"
            style={{
              height: 36, padding: '0 12px',
              background: 'var(--surface-input)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', color: 'var(--fg-primary)',
            }}
          />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Пароль</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{
              height: 36, padding: '0 12px',
              background: 'var(--surface-input)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', color: 'var(--fg-primary)',
            }}
          />
        </label>

        {error && (
          <div role="alert" style={{
            padding: '8px 12px', background: 'rgba(248, 113, 113, 0.12)',
            border: '1px solid var(--danger)', borderRadius: 'var(--radius-md)',
            color: 'var(--danger)', fontSize: 13,
          }}>{error}</div>
        )}

        <button type="submit" disabled={!canSubmit} style={{
          height: 36, padding: '0 14px',
          background: canSubmit ? 'var(--accent-600)' : 'var(--surface-panel-elevated)',
          color: canSubmit ? '#FFFFFF' : 'var(--fg-muted)',
          border: 'none', borderRadius: 'var(--radius-md)',
          fontSize: 13, fontWeight: 600, cursor: canSubmit ? 'pointer' : 'not-allowed',
        }}>
          {login.isPending ? 'Вход…' : 'Войти'}
        </button>
      </form>
    </div>
  );
}

export default LoginScreen;
```

- [ ] **Step 3: Обновить main.jsx — обернуть в AuthProvider**

```jsx
// добавить импорт
import { AuthProvider } from './auth/AuthProvider.jsx';

// в createRoot:
<QueryClientProvider client={queryClient}>
  <BrowserRouter>
    <AuthProvider>
      <App />
    </AuthProvider>
  </BrowserRouter>
</QueryClientProvider>
```

- [ ] **Step 4: Обновить App.jsx — /login + ProtectedRoute**

```jsx
import { Routes, Route, useLocation, matchPath, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar.jsx';
import { TopBar } from './components/TopBar.jsx';
import { ROUTES, ROOT_REDIRECT, NOT_FOUND_ELEMENT, SCREEN_TITLES } from './routes.jsx';
import dashboard from './fixtures/dashboard.js';  // временно остаётся до Task 19
import { LoginScreen } from './auth/LoginScreen.jsx';
import { ProtectedRoute } from './auth/ProtectedRoute.jsx';

function findMeta(pathname) {
  for (const key of Object.keys(SCREEN_TITLES)) {
    if (matchPath(key, pathname)) return SCREEN_TITLES[key];
  }
  return { title: '', breadcrumbs: [] };
}

function ProtectedShell() {
  const location = useLocation();
  const meta = findMeta(location.pathname);
  const badges = { newOrders: dashboard.newOrdersBadge ?? 0 };
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar badges={badges} />
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <TopBar title={meta.title} breadcrumbs={meta.breadcrumbs} primaryAction={meta.primaryAction} />
        <div style={{ flex: 1, padding: 24, overflow: 'auto' }}>
          <Routes>
            <Route path="/" element={ROOT_REDIRECT} />
            {ROUTES.map((r) => (
              <Route key={r.path} path={r.path} element={r.element} />
            ))}
            <Route path="*" element={NOT_FOUND_ELEMENT} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginScreen />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <ProtectedShell />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
```

- [ ] **Step 5: Тесты роутинга — пока не сломаются**

Тесты в `routes.test.jsx` импортируют App, и теперь /me запрос пойдёт. На JSDOM-окружении fetch не настроен по умолчанию, тест упадёт.

Решение: добавить mock для fetch в `setup.js` или прокинуть через jest.fn. Сейчас отложим — Task 24 переписывает все тесты под MSW.

Минимально добавим в `setup.js`:
```js
import '@testing-library/jest-dom';

// Заглушка fetch для тестов, не использующих MSW (большинство).
// Возвращает 401 на /api/crm/auth/me/ — рендерит /login или Splash в зависимости от пути.
if (!globalThis.fetch || !globalThis.fetch._isStub) {
  const stub = async () => new Response(null, { status: 401 });
  stub._isStub = true;
  globalThis.fetch = stub;
}
```

- [ ] **Step 6: Запустить тесты**

Run: `cd crm-web && npm run test 2>&1 | tail -8`
Expected: тесты падают на 401-кейс и пытаются увидеть Login. Наверняка упадут — это ожидаемо, починим в Task 24 при общем переписывании. Зафиксируем падающие, не блокируем.

**Допустимый сценарий на этом шаге:** тесты с прямым импортом фикстур упадут. Tasks 19-23 их перепишут.

Если падают _все_ — вернуть `setup.js` к минимальной версии и проверить, что login тестам ходит на /login через `<MemoryRouter initialEntries={['/login']}>`.

- [ ] **Step 7: Commit**

```bash
git add crm-web/src/auth/ crm-web/src/main.jsx crm-web/src/App.jsx crm-web/src/__tests__/setup.js
git commit -m "feat(crm-web): add /login route, ProtectedRoute wrapper, LoginScreen"
```

---

## Task 18: ScreenSkeleton + ErrorBanner

**Files:**
- Create: `crm-web/src/components/ScreenSkeleton.jsx`
- Create: `crm-web/src/components/ErrorBanner.jsx`

- [ ] **Step 1: ScreenSkeleton**

`crm-web/src/components/ScreenSkeleton.jsx`:
```jsx
const PULSE_KEYFRAMES = `
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
`;

const skeletonBlock = {
  background: 'var(--surface-panel-elevated)',
  borderRadius: 'var(--radius-md)',
  animation: 'pulse 1.4s ease-in-out infinite',
};

export function ScreenSkeleton({ variant = 'table' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <style>{PULSE_KEYFRAMES}</style>
      {variant === 'dashboard' && <DashboardSkeleton />}
      {variant === 'table' && <TableSkeleton />}
      {variant === 'card' && <CardSkeleton />}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={{ ...skeletonBlock, height: 88 }} />
        ))}
      </div>
      <div style={{ ...skeletonBlock, height: 220 }} />
      <div style={{ ...skeletonBlock, height: 180 }} />
    </>
  );
}

function TableSkeleton() {
  return (
    <>
      <div style={{ ...skeletonBlock, height: 36 }} />
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} style={{ ...skeletonBlock, height: 44, opacity: 0.6 }} />
      ))}
    </>
  );
}

function CardSkeleton() {
  return (
    <>
      <div style={{ ...skeletonBlock, height: 80 }} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={{ ...skeletonBlock, height: 88 }} />
        ))}
      </div>
      <div style={{ ...skeletonBlock, height: 220 }} />
    </>
  );
}

export default ScreenSkeleton;
```

- [ ] **Step 2: ErrorBanner**

`crm-web/src/components/ErrorBanner.jsx`:
```jsx
import { Icon } from './Icon.jsx';

export function ErrorBanner({ title = 'Что-то пошло не так', hint, error, onRetry }) {
  const message = hint || error?.message || error?.body?.detail || '';
  return (
    <div role="alert" style={{
      background: 'var(--surface-panel)',
      border: '1px solid var(--danger)',
      borderRadius: 'var(--radius-lg)',
      padding: 16,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <Icon name="alert-triangle" size={20} style={{ color: 'var(--danger)' }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--fg-primary)' }}>{title}</div>
        {message && <div style={{ fontSize: 12, color: 'var(--fg-muted)', marginTop: 2 }}>{message}</div>}
      </div>
      {onRetry && (
        <button onClick={onRetry} style={{
          padding: '6px 12px', borderRadius: 'var(--radius-md)',
          background: 'var(--accent-600)', border: 'none', color: '#FFFFFF',
          fontSize: 13, fontWeight: 500, cursor: 'pointer',
        }}>Повторить</button>
      )}
    </div>
  );
}

export default ErrorBanner;
```

- [ ] **Step 3: Commit**

```bash
git add crm-web/src/components/ScreenSkeleton.jsx crm-web/src/components/ErrorBanner.jsx
git commit -m "feat(crm-web): add ScreenSkeleton and ErrorBanner components"
```

---

## Универсальный паттерн миграции экрана (для Tasks 19-26)

Каждый экран сейчас импортирует фикстуру (`import X from '../fixtures/X.js'`). После миграции:
1. Создаём хук `crm-web/src/hooks/useX.js` — обёртка `useQuery` над API.
2. В экране заменяем `import X from '../fixtures/X.js'` на `import { useX } from '../hooks/useX.js'`.
3. В начале компонента — `const { data, isLoading, error, refetch } = useX(filters)`.
4. Обработка состояний:
   ```jsx
   if (isLoading) return <ScreenSkeleton variant="table" />;
   if (error)     return <ErrorBanner title="Не удалось загрузить" error={error} onRetry={refetch} />;
   ```
5. Удаляем все упоминания фикстур из экрана.

Каждый Task ниже соответствует одному экрану.

---

## Task 19: DashboardScreen → API

**Files:**
- Create: `crm-web/src/hooks/useDashboard.js`
- Modify: `crm-web/src/screens/DashboardScreen.jsx`
- Modify: `crm-web/src/App.jsx` (убрать использование `dashboard.newOrdersBadge`)

- [ ] **Step 1: Hook**

`crm-web/src/hooks/useDashboard.js`:
```js
import { useQuery } from '@tanstack/react-query';
import { getDashboard } from '../api/dashboard.js';

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
  });
}
```

- [ ] **Step 2: Update DashboardScreen**

```jsx
import { Stat } from '../components/primitives/Stat.jsx';
import { BarChart } from '../components/primitives/BarChart.jsx';
import { ActiveCampaign } from '../components/primitives/ActiveCampaign.jsx';
import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
import { ErrorBanner } from '../components/ErrorBanner.jsx';
import { useDashboard } from '../hooks/useDashboard.js';
import { fmtRubShort } from '../utils/format.js';

function fmtKpi(kpi) {
  if (kpi.format === 'rubShort') return fmtRubShort(kpi.value);
  return new Intl.NumberFormat('ru-RU').format(kpi.value);
}

export default function DashboardScreen() {
  const { data, isLoading, error, refetch } = useDashboard();

  if (isLoading) return <ScreenSkeleton variant="dashboard" />;
  if (error)     return <ErrorBanner title="Не удалось загрузить дашборд" error={error} onRetry={refetch} />;

  const barData = (data.daily || []).map((d) => ({
    label: d.date.slice(8, 10),
    value: d.revenue,
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {data.kpis.map((k) => (
          <Stat key={k.id} label={k.label} value={fmtKpi(k)} delta={k.delta} deltaLabel={k.deltaLabel} />
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 12 }}>Заказы за 14 дней</div>
          <BarChart data={barData} />
        </div>
        <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 12 }}>RFM-сегменты</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
            {(data.rfmSegments || []).map((s) => (
              <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ flex: 1, color: 'var(--fg-primary)' }}>{s.name}</span>
                <span style={{ color: 'var(--fg-secondary)', fontVariantNumeric: 'tabular-nums' }}>{s.count.toLocaleString('ru-RU')}</span>
                <span style={{ color: 'var(--fg-muted)', width: 48, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{s.share}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 12 }}>Активные кампании</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(data.activeCampaigns || []).map((c, i) => (
            <ActiveCampaign key={i} name={c.name} hint={c.hint} />
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: App.jsx — убрать `dashboard.newOrdersBadge`**

В `App.jsx`:
- Удалить `import dashboard from './fixtures/dashboard.js';`
- Заменить `const badges = { newOrders: dashboard.newOrdersBadge ?? 0 };` на `const badges = { newOrders: 0 };` (бейдж заказов после M1 будет приходить отдельным каналом — out of scope для M1).

- [ ] **Step 4: Commit**

```bash
git add crm-web/src/hooks/useDashboard.js crm-web/src/screens/DashboardScreen.jsx crm-web/src/App.jsx
git commit -m "feat(crm-web): wire DashboardScreen to /api/crm/dashboard via react-query"
```

---

## Task 20: ClientsScreen → API

**Files:**
- Create: `crm-web/src/hooks/useClients.js`
- Modify: `crm-web/src/screens/ClientsScreen.jsx`

- [ ] **Step 1: Hook**

`crm-web/src/hooks/useClients.js`:
```js
import { useQuery } from '@tanstack/react-query';
import { listClients, getClient } from '../api/clients.js';

export function useClients(filters) {
  return useQuery({
    queryKey: ['clients', filters],
    queryFn: () => listClients(filters),
    keepPreviousData: true,
  });
}

export function useClient(cardId) {
  return useQuery({
    queryKey: ['client', cardId],
    queryFn: () => getClient(cardId),
    enabled: !!cardId,
    retry: (failureCount, error) => error?.status !== 404 && failureCount < 2,
  });
}
```

- [ ] **Step 2: Update ClientsScreen**

Полностью заменить `crm-web/src/screens/ClientsScreen.jsx` на:
```jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../components/Icon.jsx';
import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
import { ErrorBanner } from '../components/ErrorBanner.jsx';
import { useClients } from '../hooks/useClients.js';
import { fmtRub, fmtDate } from '../utils/format.js';

const SEGMENTS = ['Все', 'Чемпионы', 'Лояльные', 'Новички', 'Спящие', 'Рискуют уйти', 'Потерянные'];
const PAGE_SIZE = 50;

export default function ClientsScreen() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [seg, setSeg] = useState('Все');
  const [page, setPage] = useState(1);

  const { data, isLoading, error, refetch } = useClients({
    q: q.trim() || undefined,
    segment: seg !== 'Все' ? seg : undefined,
    page,
    pageSize: PAGE_SIZE,
  });

  if (isLoading) return <ScreenSkeleton variant="table" />;
  if (error)     return <ErrorBanner title="Не удалось загрузить клиентов" error={error} onRetry={refetch} />;

  const rows = data.results;
  const pages = data.pagination.totalPages;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Icon name="search" size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--fg-muted)' }} />
          <input
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
            placeholder="Поиск по имени, телефону, email…"
            style={{
              width: '100%', height: 36, paddingLeft: 36, paddingRight: 12,
              background: 'var(--surface-input)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', color: 'var(--fg-primary)',
            }}
          />
        </div>
        <select
          value={seg}
          onChange={(e) => { setSeg(e.target.value); setPage(1); }}
          style={{
            height: 36, padding: '0 12px',
            background: 'var(--surface-input)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)', color: 'var(--fg-primary)',
          }}
        >
          {SEGMENTS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
        <table style={{ width: '100%', fontSize: 13 }}>
          <thead style={{ background: 'var(--surface-panel-elevated)', color: 'var(--fg-muted)' }}>
            <tr>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Клиент</th>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Сегмент</th>
              <th style={{ textAlign: 'right', padding: '10px 12px', fontWeight: 500 }}>Бонусы</th>
              <th style={{ textAlign: 'right', padding: '10px 12px', fontWeight: 500 }}>LTV</th>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Последний заказ</th>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Теги</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} onClick={() => navigate(`/clients/${c.id}`)} style={{ cursor: 'pointer', borderTop: '1px solid var(--border)' }}>
                <td style={{ padding: '10px 12px' }}>
                  <div style={{ fontWeight: 500, color: 'var(--fg-primary)' }}>{c.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{c.phone}</div>
                </td>
                <td style={{ padding: '10px 12px', color: 'var(--fg-secondary)' }}>{c.rfmSegment}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--fg-primary)' }}>{fmtRub(c.bonus)}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--fg-primary)' }}>{fmtRub(c.ltv)}</td>
                <td style={{ padding: '10px 12px', color: 'var(--fg-secondary)' }}>{c.lastOrder ? fmtDate(c.lastOrder) : '—'}</td>
                <td style={{ padding: '10px 12px', color: 'var(--fg-muted)' }}>{(c.tags || []).join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 4 }}>
          {Array.from({ length: pages }).map((_, i) => (
            <button
              key={i}
              onClick={() => setPage(i + 1)}
              style={{
                width: 32, height: 32, borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border)',
                background: page === i + 1 ? 'var(--accent-600)' : 'var(--surface-panel)',
                color: page === i + 1 ? '#FFFFFF' : 'var(--fg-secondary)',
                cursor: 'pointer', fontSize: 13, fontWeight: 500,
              }}
            >{i + 1}</button>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add crm-web/src/hooks/useClients.js crm-web/src/screens/ClientsScreen.jsx
git commit -m "feat(crm-web): wire ClientsScreen to /api/crm/clients"
```

---

## Task 21: ClientDetailScreen → API

**Files:**
- Modify: `crm-web/src/screens/ClientDetailScreen.jsx`

(Хук `useClient` уже создан в Task 20.)

- [ ] **Step 1: Update ClientDetailScreen**

Полностью заменить на:
```jsx
import { useNavigate, useParams, Link } from 'react-router-dom';
import { Stat } from '../components/primitives/Stat.jsx';
import { KV } from '../components/primitives/KV.jsx';
import { Toggle } from '../components/primitives/Toggle.jsx';
import { ActiveCampaign } from '../components/primitives/ActiveCampaign.jsx';
import { EmptyState } from '../components/EmptyState.jsx';
import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
import { ErrorBanner } from '../components/ErrorBanner.jsx';
import { useClient } from '../hooks/useClients.js';
import { NotFoundError } from '../api/client.js';
import { fmtRub, fmtDate } from '../utils/format.js';

export default function ClientDetailScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: client, isLoading, error, refetch } = useClient(id);

  if (isLoading) return <ScreenSkeleton variant="card" />;
  if (error instanceof NotFoundError) {
    return (
      <EmptyState
        title="Клиент не найден"
        hint={`ID ${id} отсутствует в системе`}
        onBack={() => navigate('/clients')}
        backLabel="← К списку клиентов"
      />
    );
  }
  if (error) return <ErrorBanner title="Не удалось загрузить клиента" error={error} onRetry={refetch} />;
  if (!client) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Link to="/clients" style={{ color: 'var(--fg-muted)', fontSize: 12 }}>← Все клиенты</Link>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{
          width: 56, height: 56, borderRadius: 999,
          background: 'var(--accent-soft)', color: 'var(--accent-600)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, fontWeight: 600,
        }}>{(client.name || '').split(' ').map((s) => s[0]).join('').slice(0, 2)}</div>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--fg-primary)' }}>{client.name}</div>
          <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>{client.id} · {client.rfmSegment}</div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <Stat label="LTV" value={fmtRub(client.ltv)} />
        <Stat label="Бонусы" value={fmtRub(client.bonus)} />
        <Stat label="Заказов всего" value={client.purchaseCount ?? (client.orders?.length || 0)} />
        <Stat label="Последний заказ" value={client.lastOrder ? fmtDate(client.lastOrder) : '—'} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 8 }}>Контакты</div>
          <KV k="Телефон" v={client.phone} mono />
          <KV k="Email" v={client.email || '—'} />
          <KV k="Telegram ID" v={client.telegramId || '—'} mono />
          <KV k="Теги" v={(client.tags || []).join(', ') || '—'} />
        </div>
        <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 8 }}>Уведомления</div>
          <Toggle label="Push" on={!!client.preferences?.push} />
          <Toggle label="Telegram" on={!!client.preferences?.telegram} />
          <Toggle label="Email" on={!!client.preferences?.email} />
          <Toggle label="SMS" on={!!client.preferences?.sms} />
        </div>
      </div>
      {(client.activeCampaigns || []).length > 0 && (
        <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 8 }}>Активные кампании</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {client.activeCampaigns.map((c) => <ActiveCampaign key={c.id} name={c.name} hint={c.rules} />)}
          </div>
        </div>
      )}
      <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 8 }}>История заказов</div>
        {(client.orders || []).length === 0 ? (
          <div style={{ color: 'var(--fg-muted)', fontSize: 13 }}>Нет заказов</div>
        ) : (
          <table style={{ width: '100%', fontSize: 13 }}>
            <thead style={{ color: 'var(--fg-muted)' }}>
              <tr>
                <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500 }}>Заказ</th>
                <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500 }}>Дата</th>
                <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500 }}>Сумма</th>
                <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500 }}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {client.orders.map((o) => (
                <tr key={o.id} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: '8px 0', color: 'var(--fg-primary)' }}>{o.id}</td>
                  <td style={{ padding: '8px 0', color: 'var(--fg-secondary)' }}>{fmtDate(o.date)}</td>
                  <td style={{ padding: '8px 0', textAlign: 'right', color: 'var(--fg-primary)' }}>{fmtRub(o.amount)}</td>
                  <td style={{ padding: '8px 0', color: 'var(--fg-secondary)' }}>{o.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add crm-web/src/screens/ClientDetailScreen.jsx
git commit -m "feat(crm-web): wire ClientDetailScreen to /api/crm/clients/<id>"
```

---

## Task 22: OrdersScreen → API

**Files:**
- Create: `crm-web/src/hooks/useOrders.js`
- Modify: `crm-web/src/screens/OrdersScreen.jsx`

- [ ] **Step 1: Hook**

`crm-web/src/hooks/useOrders.js`:
```js
import { useQuery } from '@tanstack/react-query';
import { listOrders } from '../api/orders.js';

export function useOrders(filters) {
  return useQuery({
    queryKey: ['orders', filters],
    queryFn: () => listOrders(filters),
    keepPreviousData: true,
  });
}
```

- [ ] **Step 2: Update OrdersScreen**

В `crm-web/src/screens/OrdersScreen.jsx`:
- Удалить `import orders from '../fixtures/orders.js';`
- Добавить:
  ```jsx
  import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
  import { ErrorBanner } from '../components/ErrorBanner.jsx';
  import { useOrders } from '../hooks/useOrders.js';
  ```
- В компоненте перед таблицей:
  ```jsx
  const { data, isLoading, error, refetch } = useOrders({
    status: status !== 'Все' ? status : undefined,
    purchaseType: pType !== 'Все' ? pType : undefined,
  });
  if (isLoading) return <ScreenSkeleton variant="table" />;
  if (error)     return <ErrorBanner title="Не удалось загрузить заказы" error={error} onRetry={refetch} />;
  const list = data.results;
  ```
- Удалить `useMemo`-фильтрацию (теперь её делает backend).

- [ ] **Step 3: Commit**

```bash
git add crm-web/src/hooks/useOrders.js crm-web/src/screens/OrdersScreen.jsx
git commit -m "feat(crm-web): wire OrdersScreen to /api/crm/orders"
```

---

## Task 23: CampaignsScreen → API

**Files:**
- Create: `crm-web/src/hooks/useCampaigns.js`
- Modify: `crm-web/src/screens/CampaignsScreen.jsx`

- [ ] **Step 1: Hook**

`crm-web/src/hooks/useCampaigns.js`:
```js
import { useQuery } from '@tanstack/react-query';
import { listCampaigns } from '../api/campaigns.js';

export function useCampaigns({ status } = {}) {
  return useQuery({
    queryKey: ['campaigns', status],
    queryFn: () => listCampaigns({ status, pageSize: 100 }),
    keepPreviousData: true,
  });
}
```

- [ ] **Step 2: Update CampaignsScreen**

Удалить `import campaigns from '../fixtures/campaigns.js';`. Добавить:
```jsx
import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
import { ErrorBanner } from '../components/ErrorBanner.jsx';
import { useCampaigns } from '../hooks/useCampaigns.js';
```

Заменить `useMemo`-фильтрацию на:
```jsx
const apiStatus = tab === 'all' ? undefined : tab;
const { data, isLoading, error, refetch } = useCampaigns({ status: apiStatus });

if (isLoading) return <ScreenSkeleton variant="table" />;
if (error)     return <ErrorBanner title="Не удалось загрузить кампании" error={error} onRetry={refetch} />;
const list = data.results;
```

- [ ] **Step 3: Commit**

```bash
git add crm-web/src/hooks/useCampaigns.js crm-web/src/screens/CampaignsScreen.jsx
git commit -m "feat(crm-web): wire CampaignsScreen to /api/crm/campaigns"
```

---

## Task 24: BroadcastsScreen → API (history table)

**Files:**
- Create: `crm-web/src/hooks/useBroadcasts.js`
- Modify: `crm-web/src/screens/BroadcastsScreen.jsx`

Форма создания на фронте остаётся (это не мутация — submit не отправляет в backend в M1, см. spec; M3 добавит реальную POST). Меняем только табличку «История рассылок» — она теперь из API.

- [ ] **Step 1: Hook**

`crm-web/src/hooks/useBroadcasts.js`:
```js
import { useQuery } from '@tanstack/react-query';
import { listBroadcastHistory } from '../api/broadcasts.js';

export function useBroadcastHistory({ page = 1, pageSize = 50 } = {}) {
  return useQuery({
    queryKey: ['broadcasts/history', page, pageSize],
    queryFn: () => listBroadcastHistory({ page, pageSize }),
    keepPreviousData: true,
  });
}
```

- [ ] **Step 2: Update BroadcastsScreen — секция «История рассылок»**

В `crm-web/src/screens/BroadcastsScreen.jsx`:
- Удалить `import broadcasts from '../fixtures/broadcasts.js';` (имя `broadcasts.HISTORY` использовалось)
- Сохранить `import { SEGMENTS, CHANNELS, CATEGORIES } from '../fixtures/broadcasts.js';` если форма использует — переписать форму на инлайн-литералы:
  ```jsx
  const SEGMENTS = ['Чемпионы', 'Лояльные', 'Новички', 'Спящие', 'Рискуют уйти'];
  const CHANNELS = [
    { id: 'push', label: 'Push (мобильное)' },
    { id: 'telegram', label: 'Telegram' },
    { id: 'email', label: 'Email' },
  ];
  const CATEGORIES = [
    { id: 'general', label: 'Общая' },
    { id: 'promo',   label: 'Акции и скидки' },
    { id: 'news',    label: 'Новости магазина' },
  ];
  ```
- Добавить хук:
  ```jsx
  import { useBroadcastHistory } from '../hooks/useBroadcasts.js';
  // ...
  const { data: history, isLoading: histLoading, error: histError, refetch } = useBroadcastHistory();
  ```
- Заменить блок «История рассылок» на:
  ```jsx
  <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
    <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--fg-primary)', marginBottom: 12 }}>История рассылок</div>
    {histLoading && <ScreenSkeleton variant="table" />}
    {histError && <ErrorBanner title="Не удалось загрузить историю" error={histError} onRetry={refetch} />}
    {history && (
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {history.results.map((b, i) => (
          <div key={b.id} style={{ padding: '10px 0', borderBottom: i < history.results.length - 1 ? '1px solid var(--border)' : 'none' }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-primary)' }}>{b.id} · {b.segment}</div>
            <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 12, color: 'var(--fg-muted)' }}>
              <span>{fmtDate(b.sentAt)}</span>
              <span>·</span>
              <span>{b.channel}</span>
              <span>·</span>
              <span>{b.reach.toLocaleString('ru-RU')} → {b.opened.toLocaleString('ru-RU')}</span>
              <span style={{ color: 'var(--success)', fontWeight: 500 }}>{b.reach > 0 ? Math.round(b.opened / b.reach * 100) : 0}%</span>
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
  ```

- [ ] **Step 3: Commit**

```bash
git add crm-web/src/hooks/useBroadcasts.js crm-web/src/screens/BroadcastsScreen.jsx
git commit -m "feat(crm-web): wire BroadcastsScreen history to /api/crm/broadcasts/history"
```

---

## Task 25: Categories list+detail → API

**Files:**
- Create: `crm-web/src/hooks/useCategories.js`
- Modify: `crm-web/src/screens/CategoriesScreen.jsx`
- Modify: `crm-web/src/screens/CategoryDetailScreen.jsx`

- [ ] **Step 1: Hook**

`crm-web/src/hooks/useCategories.js`:
```js
import { useQuery } from '@tanstack/react-query';
import { listCategories, getCategory } from '../api/categories.js';

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: listCategories,
  });
}

export function useCategory(slug) {
  return useQuery({
    queryKey: ['category', slug],
    queryFn: () => getCategory(slug),
    enabled: !!slug,
    retry: (failureCount, error) => error?.status !== 404 && failureCount < 2,
  });
}
```

- [ ] **Step 2: Update CategoriesScreen**

В `crm-web/src/screens/CategoriesScreen.jsx`:
- Удалить `import categories from '../fixtures/categories.js';`
- Добавить:
  ```jsx
  import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
  import { ErrorBanner } from '../components/ErrorBanner.jsx';
  import { useCategories } from '../hooks/useCategories.js';
  ```
- В начале компонента:
  ```jsx
  const { data, isLoading, error, refetch } = useCategories();
  if (isLoading) return <ScreenSkeleton variant="table" />;
  if (error)     return <ErrorBanner title="Не удалось загрузить категории" error={error} onRetry={refetch} />;
  const categories = data; // массив
  ```

- [ ] **Step 3: Update CategoryDetailScreen**

В `crm-web/src/screens/CategoryDetailScreen.jsx`:
- Удалить импорты фикстур.
- Добавить:
  ```jsx
  import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
  import { ErrorBanner } from '../components/ErrorBanner.jsx';
  import { useCategory } from '../hooks/useCategories.js';
  import { NotFoundError } from '../api/client.js';
  ```
- Использовать хук:
  ```jsx
  const { slug } = useParams();
  const { data: cat, isLoading, error, refetch } = useCategory(slug);
  if (isLoading) return <ScreenSkeleton variant="card" />;
  if (error instanceof NotFoundError) {
    return <EmptyState title="Категория не найдена" hint={`slug «${slug}» отсутствует`} onBack={() => navigate('/categories')} backLabel="← К списку категорий" />;
  }
  if (error) return <ErrorBanner title="Не удалось загрузить категорию" error={error} onRetry={refetch} />;
  if (!cat) return null;
  // SKU теперь из cat.skuList (уже в ответе detail-endpoint'а)
  const catSkus = cat.skuList || [];
  ```

- [ ] **Step 4: Commit**

```bash
git add crm-web/src/hooks/useCategories.js crm-web/src/screens/CategoriesScreen.jsx crm-web/src/screens/CategoryDetailScreen.jsx
git commit -m "feat(crm-web): wire Categories+Detail screens to /api/crm/categories"
```

---

## Task 26: AbcXyzScreen → API

**Files:**
- Create: `crm-web/src/hooks/useAbcXyz.js`
- Modify: `crm-web/src/screens/AbcXyzScreen.jsx`

- [ ] **Step 1: Hook**

`crm-web/src/hooks/useAbcXyz.js`:
```js
import { useQuery } from '@tanstack/react-query';
import { getAbcXyz } from '../api/abcXyz.js';

export function useAbcXyz() {
  return useQuery({
    queryKey: ['abc-xyz'],
    queryFn: getAbcXyz,
  });
}
```

- [ ] **Step 2: Update AbcXyzScreen**

В `crm-web/src/screens/AbcXyzScreen.jsx`:
- Удалить `import abcXyz from '../fixtures/abcXyz.js';`
- Добавить:
  ```jsx
  import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
  import { ErrorBanner } from '../components/ErrorBanner.jsx';
  import { useAbcXyz } from '../hooks/useAbcXyz.js';
  ```
- В компоненте:
  ```jsx
  const { data: abcXyz, isLoading, error, refetch } = useAbcXyz();
  if (isLoading) return <ScreenSkeleton variant="dashboard" />;
  if (error)     return <ErrorBanner title="Не удалось загрузить матрицу" error={error} onRetry={refetch} />;
  ```

- [ ] **Step 3: Commit**

```bash
git add crm-web/src/hooks/useAbcXyz.js crm-web/src/screens/AbcXyzScreen.jsx
git commit -m "feat(crm-web): wire AbcXyzScreen to /api/crm/abc-xyz"
```

---

## Task 27: Logout-меню в TopBar

**Files:**
- Modify: `crm-web/src/components/TopBar.jsx`

- [ ] **Step 1: Расширить TopBar**

Заменить полностью на:
```jsx
import { useState, useRef, useEffect } from 'react';
import { Icon } from './Icon.jsx';
import { useAuthContext } from '../auth/AuthProvider.jsx';
import { useLogout } from '../hooks/useAuth.js';
import { useNavigate } from 'react-router-dom';

export function TopBar({ title, breadcrumbs = [], primaryAction }) {
  const { user } = useAuthContext();
  const logout = useLogout();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  function handleLogout() {
    logout.mutate(undefined, {
      onSuccess: () => navigate('/login', { replace: true }),
    });
  }

  return (
    <header style={{
      height: 'var(--topbar-h)',
      borderBottom: '1px solid var(--border)',
      background: 'var(--surface-page)',
      display: 'flex', alignItems: 'center', padding: '0 24px', gap: 16,
      flexShrink: 0,
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}>
        {breadcrumbs.length > 0 && (
          <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>{breadcrumbs.join(' / ')}</div>
        )}
        <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--fg-primary)', letterSpacing: '-0.01em' }}>{title}</h1>
      </div>
      {primaryAction && (
        <button style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: 'var(--accent-600)', color: '#FFFFFF', border: 'none',
          borderRadius: 'var(--radius-md)', padding: '8px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
        }}>
          {primaryAction.icon && <Icon name={primaryAction.icon} size={16} />}
          {primaryAction.label}
        </button>
      )}
      <div ref={ref} style={{ position: 'relative' }}>
        <button
          aria-label="Профиль"
          onClick={() => setOpen((v) => !v)}
          style={{
            background: 'var(--surface-panel)', border: '1px solid var(--border)',
            borderRadius: 999, width: 32, height: 32, display: 'inline-flex',
            alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
          }}
        >
          <Icon name="user" size={16} />
        </button>
        {open && (
          <div style={{
            position: 'absolute', top: 36, right: 0, zIndex: 10,
            width: 220, background: 'var(--surface-panel)',
            border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
            padding: 4, boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
          }}>
            {user && (
              <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-primary)' }}>{user.name}</div>
                <div style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{user.email}</div>
              </div>
            )}
            <button
              onClick={handleLogout}
              disabled={logout.isPending}
              style={{
                width: '100%', padding: '8px 12px',
                background: 'transparent', border: 'none', textAlign: 'left',
                color: 'var(--fg-primary)', fontSize: 13, cursor: 'pointer',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              {logout.isPending ? 'Выход…' : 'Выйти'}
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

export default TopBar;
```

- [ ] **Step 2: Commit**

```bash
git add crm-web/src/components/TopBar.jsx
git commit -m "feat(crm-web): add profile menu with logout to TopBar"
```

---

## Task 28: MSW-handlers + переписать routes test + auth tests

**Files:**
- Create: `crm-web/src/__tests__/msw_handlers.js`
- Modify: `crm-web/src/__tests__/setup.js`
- Modify: `crm-web/src/__tests__/routes.test.jsx`
- Create: `crm-web/src/__tests__/auth.test.jsx`

- [ ] **Step 1: MSW-handlers (общая мокированная база API)**

`crm-web/src/__tests__/msw_handlers.js`:
```js
import { http, HttpResponse } from 'msw';

const BASE = '/api/crm';

export const FIXTURE_USER = { id: 1, email: 'manager@lakshmi.ru', name: 'Тестовый Менеджер' };

export const FIXTURE_CLIENT = {
  id: 'LC-000001', name: 'Алиса Иванова', phone: '+7 914 111-22-33',
  email: 'alice@example.ru', rfmSegment: 'Чемпионы',
  bonus: 1500, ltv: 50000, purchaseCount: 12, lastOrder: '2026-04-15', tags: ['vip'],
};

export const FIXTURE_ORDER = {
  id: 'ORD-30001', date: '2026-04-15T14:32:00', clientId: 'LC-000001',
  clientName: 'Алиса Иванова', amount: 2340, status: 'assembly',
  purchaseType: 'delivery', items: 5, address: 'ул. Тестовая, 1', payment: 'sbp', courier: '—',
};

export const FIXTURE_CAMPAIGN = {
  id: 'CMP-1', name: 'Тестовая кампания', slug: 'test', status: 'active',
  period: { from: '2026-04-01', to: '2026-04-30' }, reach: 100, used: 25,
  segment: 'Чемпионы', audience: 'RFM: Чемпионы', rules: '7% бонусов', priority: 200,
};

export const FIXTURE_BROADCAST = {
  id: 'BR-1', sentAt: '2026-04-12T10:00:00', segment: 'Все клиенты',
  channel: 'promo', reach: 100, opened: 50, clicked: 0,
};

export const FIXTURE_CATEGORY = {
  id: 1, slug: 'cat-01', code: '01', name: 'Молочные', skus: 5,
  revenue: 100000, cogs: 70000, share: 8.0, turnover: 5.0,
  abc: 'A', xyz: 'X', trend: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120],
};

export const authedHandlers = [
  http.get(`${BASE}/auth/me/`, () => HttpResponse.json({ user: FIXTURE_USER })),
  http.get(`${BASE}/dashboard/`, () => HttpResponse.json({
    kpis: [
      { id: 'customers', label: 'Активные клиенты', value: 100, delta: 0, deltaLabel: '', format: 'number' },
      { id: 'orders',    label: 'Заказы сегодня',  value: 5,   delta: 0, deltaLabel: '', format: 'number' },
      { id: 'revenue',   label: 'Выручка за неделю',value: 50000, delta: 0, deltaLabel: '', format: 'rubShort' },
      { id: 'bonuses',   label: 'Бонусов на балансе', value: 10000, delta: 0, deltaLabel: '', format: 'number' },
    ],
    daily: [{ date: '2026-04-15', orders: 5, revenue: 50000 }],
    activeCampaigns: [{ id: 'CMP-1', name: 'Тестовая', hint: 'RFM: Чемпионы' }],
    rfmSegments: [{ name: 'Чемпионы', count: 30, share: 30.0 }],
  })),
  http.get(`${BASE}/clients/`, () => HttpResponse.json({ results: [FIXTURE_CLIENT] }, {
    headers: { 'X-Total-Count': '1', 'X-Page': '1', 'X-Page-Size': '50' },
  })),
  http.get(`${BASE}/clients/:cardId/`, ({ params }) => {
    if (params.cardId === 'LC-000001') {
      return HttpResponse.json({
        ...FIXTURE_CLIENT, telegramId: 142839201,
        preferences: { push: true, telegram: true, email: false, sms: false },
        orders: [FIXTURE_ORDER],
        activeCampaigns: [FIXTURE_CAMPAIGN],
      });
    }
    return HttpResponse.json({ detail: 'Клиент не найден' }, { status: 404 });
  }),
  http.get(`${BASE}/orders/`, () => HttpResponse.json({ results: [FIXTURE_ORDER] }, {
    headers: { 'X-Total-Count': '1', 'X-Page': '1', 'X-Page-Size': '50' },
  })),
  http.get(`${BASE}/campaigns/`, () => HttpResponse.json({ results: [FIXTURE_CAMPAIGN] }, {
    headers: { 'X-Total-Count': '1', 'X-Page': '1', 'X-Page-Size': '50' },
  })),
  http.get(`${BASE}/broadcasts/history/`, () => HttpResponse.json({ results: [FIXTURE_BROADCAST] }, {
    headers: { 'X-Total-Count': '1', 'X-Page': '1', 'X-Page-Size': '50' },
  })),
  http.get(`${BASE}/categories/`, () => HttpResponse.json({ results: [FIXTURE_CATEGORY] })),
  http.get(`${BASE}/categories/:slug/`, ({ params }) => {
    if (params.slug === 'cat-01') {
      return HttpResponse.json({ ...FIXTURE_CATEGORY, skuList: [] });
    }
    return HttpResponse.json({ detail: 'Категория не найдена' }, { status: 404 });
  }),
  http.get(`${BASE}/abc-xyz/`, () => HttpResponse.json({
    matrixSku: { AX: 1, AY: 1, AZ: 1, BX: 1, BY: 1, BZ: 1, CX: 1, CY: 1, CZ: 1 },
    matrixRevenue: { AX: 100, AY: 100, AZ: 100, BX: 100, BY: 100, BZ: 100, CX: 100, CY: 100, CZ: 100 },
    matrixShare: { AX: 11.1, AY: 11.1, AZ: 11.1, BX: 11.1, BY: 11.1, BZ: 11.1, CX: 11.1, CY: 11.1, CZ: 11.1 },
  })),
];

export const unauthedHandlers = [
  http.get(`${BASE}/auth/me/`, () => HttpResponse.json({ detail: 'Требуется авторизация' }, { status: 401 })),
];

export const handlers = authedHandlers;
```

- [ ] **Step 2: Setup MSW в setup.js**

`crm-web/src/__tests__/setup.js`:
```js
import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from './msw_handlers.js';

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// jsdom не имеет fetch — MSW его подменит, но если нужен fallback:
if (!globalThis.fetch) globalThis.fetch = (...args) => import('cross-fetch').then(({ default: f }) => f(...args));
```

- [ ] **Step 3: Переписать routes.test.jsx**

Полностью заменить `crm-web/src/__tests__/routes.test.jsx` на:
```jsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '../App.jsx';
import { SCREEN_TITLES } from '../routes.jsx';
import { AuthProvider } from '../auth/AuthProvider.jsx';

function renderApp(initialEntries = ['/']) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const URLS_TO_CHECK = [
  '/dashboard',
  '/clients',
  '/clients/LC-000001',
  '/orders',
  '/campaigns',
  '/rfm',
  '/broadcasts',
  '/catalog',
  '/categories',
  '/categories/cat-01',
  '/abc-xyz',
  '/analytics',
];

function titleFor(url) {
  if (url === '/clients/LC-000001') return SCREEN_TITLES['/clients/:id'].title;
  if (url === '/categories/cat-01') return SCREEN_TITLES['/categories/:slug'].title;
  return SCREEN_TITLES[url]?.title ?? '';
}

describe('CRM routing smoke (authenticated)', () => {
  it('redirects / to /dashboard', async () => {
    renderApp(['/']);
    await waitFor(() => expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(SCREEN_TITLES['/dashboard'].title));
  });

  for (const url of URLS_TO_CHECK) {
    it(`renders ${url} with correct title`, async () => {
      renderApp([url]);
      await waitFor(() => expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(titleFor(url)));
    });
  }

  it('renders 404 on unknown URL', async () => {
    renderApp(['/no-such-thing']);
    await waitFor(() => expect(screen.getByText('404')).toBeInTheDocument());
  });
});
```

- [ ] **Step 4: Auth-тесты**

`crm-web/src/__tests__/auth.test.jsx`:
```jsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import App from '../App.jsx';
import { AuthProvider } from '../auth/AuthProvider.jsx';
import { server } from './setup.js';
import { unauthedHandlers, FIXTURE_USER } from './msw_handlers.js';

function renderApp(initialEntries = ['/']) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Login flow', () => {
  beforeEach(() => {
    // Без auth: /me возвращает 401 → редирект на /login
    server.use(...unauthedHandlers);
  });

  it('shows login screen when unauthenticated', async () => {
    renderApp(['/dashboard']);
    await waitFor(() => expect(screen.getByText('Вход для менеджеров')).toBeInTheDocument());
  });

  it('login success redirects to /dashboard', async () => {
    server.use(
      http.post('/api/crm/auth/login/', () => HttpResponse.json({ user: FIXTURE_USER })),
      http.get('/api/crm/auth/me/', () => HttpResponse.json({ user: FIXTURE_USER })),
    );
    renderApp(['/login']);
    await waitFor(() => expect(screen.getByText('Вход для менеджеров')).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText('manager@lakshmi.ru'), { target: { value: 'manager@lakshmi.ru' } });
    fireEvent.change(document.querySelector('input[type="password"]'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /Войти/i }));

    await waitFor(() => expect(screen.queryByText('Вход для менеджеров')).not.toBeInTheDocument());
  });

  it('shows "Неверный email или пароль" on 401', async () => {
    server.use(http.post('/api/crm/auth/login/', () => HttpResponse.json({ detail: 'Неверный email или пароль' }, { status: 401 })));
    renderApp(['/login']);
    fireEvent.change(screen.getByPlaceholderText('manager@lakshmi.ru'), { target: { value: 'manager@lakshmi.ru' } });
    fireEvent.change(document.querySelector('input[type="password"]'), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: /Войти/i }));

    await waitFor(() => expect(screen.getByRole('alert').textContent).toMatch(/Неверный/));
  });

  it('shows "нет доступа" on 403', async () => {
    server.use(http.post('/api/crm/auth/login/', () => HttpResponse.json({ detail: 'Нет доступа в CRM' }, { status: 403 })));
    renderApp(['/login']);
    fireEvent.change(screen.getByPlaceholderText('manager@lakshmi.ru'), { target: { value: 'user@lakshmi.ru' } });
    fireEvent.change(document.querySelector('input[type="password"]'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /Войти/i }));

    await waitFor(() => expect(screen.getByRole('alert').textContent).toMatch(/доступ/i));
  });
});
```

- [ ] **Step 5: Запустить все frontend-тесты**

Run: `cd crm-web && npm run test 2>&1 | tail -10`
Expected: 24 routes-теста + 4 auth-теста + 3 api_client-теста = 31 passed.

- [ ] **Step 6: Lint + build smoke**

Run: `cd crm-web && npm run lint 2>&1 | tail -5`
Expected: 0 errors.

Run: `cd crm-web && npm run build 2>&1 | tail -3`
Expected: ✓ built.

- [ ] **Step 7: Commit**

```bash
git add crm-web/src/__tests__/
git commit -m "test(crm-web): rewrite routes/auth tests on MSW; add fixtures-free test setup"
```

---

## Task 29: Удалить fixtures, обновить docs, финальная DoD-проверка

**Files:**
- Delete: `crm-web/src/fixtures/` (вся папка)
- Modify: `crm-web/README.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Убедиться, что фикстуры больше нигде не используются**

Run: `grep -rn "from .*fixtures\|from '../fixtures\|from './fixtures" crm-web/src/`
Expected: пусто. Если что-то осталось — ошибка в Tasks 19-26, исправить.

- [ ] **Step 2: Удалить папку**

Run: `rm -r crm-web/src/fixtures && ls crm-web/src/`
Expected: `fixtures` нет в выводе.

- [ ] **Step 3: Прогнать все тесты — должны быть зелёные**

Run: `cd crm-web && npm run test && npm run lint && npm run build 2>&1 | tail -10`
Expected: тесты зелёные, lint OK, build OK.

- [ ] **Step 4: Обновить README**

Заменить раздел «Запуск» в `crm-web/README.md` на:
```markdown
## Запуск

CRM — статическая SPA, требует работающего Django backend для данных.

**Локально (dev):**

```bash
# 1. Терминал 1: Django backend на :8000
cd backend
DJANGO_SETTINGS_MODULE=settings python3 manage.py runserver 8000
# (или через docker compose up -d)

# 2. Терминал 2: CRM dev-сервер на :5173
cd crm-web
npm install        # один раз
npm run dev        # http://127.0.0.1:5173/
```

Vite-proxy автоматически проксирует `/api/*` запросы на `http://127.0.0.1:8000`. Cookie работают на одном origin (5173).

**Создать менеджера** (один раз):
1. Войти в Django-admin: `http://127.0.0.1:8000/admin/`
2. Users → Add → ввести email, пароль, поставить **is_staff=True**
3. Email + пароль использовать для логина в CRM на `/login`

**Команды:**

```bash
npm run dev         # http://127.0.0.1:5173/
npm run build       # сборка в ./dist
npm run preview     # просмотр production-сборки
npm run test        # vitest run + MSW
npm run lint        # eslint src
```

Из корня репо: `make crm-dev`, `make crm-build`, `make crm-test`, `make crm-lint`, `make crm-preview`.

## Переменные окружения

- `VITE_API_BASE` (опционально) — базовый URL для API-запросов. Дефолт: `/api/crm` (через Vite-proxy в dev / nginx-proxy в prod).
```

Заменить раздел «Структура» (добавить новые папки):
```markdown
## Структура

- `src/screens/` — экраны (один файл — один маршрут).
- `src/components/` — общие компоненты (Sidebar, TopBar, Icon, Placeholder, EmptyState, ErrorBoundary, **ScreenSkeleton**, **ErrorBanner**, **Splash**).
- `src/components/primitives/` — переиспользуемые UI-примитивы.
- `src/api/` — API-клиент и resource-модули (auth, clients, orders, ...). Тонкая обёртка над fetch с CSRF + cookie-based session.
- `src/hooks/` — react-query хуки на каждый ресурс (useAuth, useClients, useOrders, ...).
- `src/auth/` — AuthProvider, ProtectedRoute, LoginScreen.
- `src/styles/tokens.css` — единый источник цветов и токенов (dark theme).
- `src/utils/format.js` — форматирование чисел и дат.
- `src/routes.jsx` — карта маршрутов и заголовков (SCREEN_TITLES, ROUTES).
- `src/__tests__/` — vitest + MSW; фикстуры мокаются на уровне fetch.
- `.reference/` — распакованный референс-артефакт (gitignored, регенерируется через `python3 ../scripts/extract_crm_reference.py`).
```

Удалить упоминание `src/fixtures/` если есть.

- [ ] **Step 5: Обновить ARCHITECTURE.md**

В `docs/ARCHITECTURE.md`, в раздел про auth-зоны, добавить:
```markdown
### CRM API (для менеджеров)

- Префикс: `/api/crm/*`
- Авторизация: **session-cookie** (`sessionid`) через `SessionAuthentication`
- Permission: `IsCRMStaff` — только пользователи `django.contrib.auth.User` с `is_staff=True`
- CSRF: `csrftoken` cookie + `X-CSRFToken` header для не-GET (read-only в M1, под мутации в M3)
- Endpoints:
  - `POST /api/crm/auth/login/` — вход (email + password)
  - `POST /api/crm/auth/logout/` — выход
  - `GET  /api/crm/auth/me/` — текущий пользователь
  - `GET  /api/crm/dashboard/` — KPI + RFM + activeCampaigns + 14d daily
  - `GET  /api/crm/clients/` — список клиентов (фильтры: q, segment)
  - `GET  /api/crm/clients/<card_id>/` — детальная карточка
  - `GET  /api/crm/orders/` — список заказов (фильтры: status, purchaseType)
  - `GET  /api/crm/campaigns/` — список кампаний (фильтр: status)
  - `GET  /api/crm/broadcasts/history/` — история рассылок
  - `GET  /api/crm/categories/` — список категорий
  - `GET  /api/crm/categories/<slug>/` — категория + SKU
  - `GET  /api/crm/abc-xyz/` — матрица распределения SKU (стаб в M1, реальная аналитика — M2/M5)
- Rate-limit: `qr_login`/`anon_auth` 5-10/min на login (общий с мобильным auth)
- Изоляция: `/api/crm/*` НЕ принимает JWT/X-Api-Key/X-Telegram-User-Id
- Источник: `backend/apps/crm_api/`
```

- [ ] **Step 6: Финальный прогон**

Run: `cd crm-web && npm run test && npm run lint && npm run build 2>&1 | tail -5`
Expected: всё зелёное.

Run: `PYTHONPATH=/home/oem/lakshmi_project_dev/lakshmi-bot DJANGO_SETTINGS_MODULE=settings_test python3 backend/manage.py test apps.crm_api -v 1 2>&1 | tail -5`
Expected: ≥30 тестов зелёные.

Run: `grep -rn "fixtures" crm-web/src/screens/`
Expected: пусто.

- [ ] **Step 7: DoD-чеклист (см. spec §8)**

Пройтись по всем 6 пунктам Definition of Done в `docs/superpowers/specs/2026-05-02-crm-m1-auth-backend-design.md`. Если что-то не сделано — зафиксировать как 30-ю задачу и закрыть.

- [ ] **Step 8: Commit**

```bash
git add crm-web/README.md docs/ARCHITECTURE.md
git rm -r crm-web/src/fixtures
git commit -m "chore(crm-web): remove fixtures; document Django backend setup; update architecture"
```

---

## Самопроверка плана vs spec

После выполнения всех Tasks 1-29:

| Spec section | Tasks | Покрыто |
|---|---|---|
| §1 Цель и scope | All | ✅ |
| §2 Auth: User+is_staff | 1 | ✅ |
| §2 Auth: SessionAuthentication | 1, 3 | ✅ |
| §2 Auth: IsCRMStaff permission | 1, 2 | ✅ |
| §2 Auth: 3 endpoints (login/logout/me) | 3 | ✅ |
| §2 Auth: csrftoken cookie | 3, 15 | ✅ |
| §2 Auth: rate-limit AnonAuthThrottle | 5 | ✅ |
| §3 apps/crm_api/ структура | 1, 6-13 | ✅ |
| §3 _base.py CRMAPIView | 1 | ✅ |
| §3 services/dashboard.py | 6 | ✅ |
| §4 react-query setup | 14 | ✅ |
| §4 api/ + hooks/ + auth/ | 15-17 | ✅ |
| §4 Vite proxy | 14 | ✅ |
| §4 Удаление fixtures | 29 | ✅ |
| §5 12 endpoints contract | 3, 6-13 | ✅ |
| §5 HeaderPagination | 4, 7-11 | ✅ |
| §6 LoginScreen | 17 | ✅ |
| §6 Logout menu | 27 | ✅ |
| §6 ScreenSkeleton + ErrorBanner | 18, 19-26 | ✅ |
| §6 401 flow | 17 (через ProtectedRoute), 15 (UnauthorizedError) | ✅ |
| §7 Backend tests | 1-13 | ✅ |
| §7 Frontend tests (MSW) | 28 | ✅ |
| §8 DoD | 29 (Step 7) | ✅ |
| §9 Risks | mitigated в коде | ✅ |
| §10 Связь со spec'ом прототипа | — | ✅ (комментарий в README) |

Если в фактической реализации найдены отклонения — добавить Task 30+.
