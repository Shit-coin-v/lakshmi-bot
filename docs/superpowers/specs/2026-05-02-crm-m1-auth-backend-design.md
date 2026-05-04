# CRM M1 — Auth + Backend Integration (read-only)

**Дата:** 2026-05-02
**Milestone:** M1 (первый из 4 milestones по «допиливанию» CRM)
**Зависимости:** работающий прототип `crm-web/` (см. `docs/superpowers/specs/2026-04-29-crm-web-prototype-design.md`)
**Статус:** Design (готов к написанию плана)

---

## 1. Цель и scope

Превратить CRM-прототип на фикстурах в работающий staff-tool на реальных данных Django. После M1 менеджер логинится по email+паролю и видит настоящих клиентов, заказы, кампании из БД проекта. **Только чтение** — никаких мутаций.

### В scope

- 9 рабочих экранов CRM (Dashboard, Clients, ClientDetail, Orders, Campaigns, Broadcasts, Categories, CategoryDetail, AbcXyz) → реальные API
- Auth через email+password, session-cookie
- Login/logout-страница, защищённые маршруты, 401-flow
- Новый Django-app `apps/crm_api/` с эндпоинтами и тестами
- Frontend: миграция фикстур на хуки `react-query`

### Out of scope (отдельные milestones)

| Что | Когда | Почему не сейчас |
|---|---|---|
| Полнофункциональные RFM / Catalog / Analytics | M2 | Каждый — самостоятельный дизайн дашборда |
| Мутации (создание кампании, рассылки, изменение статусов) | M3 | Требуют аудит-логов, подтверждений, rollback-семантики |
| Deploy в production + CI для `crm-web/` | M4 | Не блокирует разработку M1 |
| Роли менеджеров | M5 | Сейчас все staff равны; добавим Django Groups когда будет 5+ человек |
| Self-service password reset | M5+ | На <15 человек админ-resolve достаточен |
| Аудит-лог управленческих действий | M3 | Без мутаций нечего логировать |
| Светлая тема | **не делаем** | Подтверждено: dark forever |
| Мобильная адаптивность | **не делаем** | CRM — desktop tool ≥1280px |
| i18n / другие языки | **не делаем** | Только русский |
| Storybook / визуальный регресс | **не делаем** | На 12 экранах ROI отрицательный |
| Real-time updates (WebSocket / SSE) | **не делаем** | Sidebar-бейдж обновляется при F5 — достаточно |

### Размер milestone

Оценочно 5-10 рабочих дней:
- Backend (auth + 9 endpoints + тесты): ~2-3 дня
- Frontend (login + 9 экранов на API): ~3-4 дня
- Интеграционные тесты + полировка: ~1-2 дня

---

## 2. Auth-архитектура

### Модель пользователя

Штатный `django.contrib.auth.User`. Менеджер CRM = `User` с `is_staff=True`. Создание — админом через `/admin/`. Никакой `Manager`-модели, никаких новых таблиц для auth.

**Обоснование:** на M1 ролей нет, все менеджеры равны. `is_staff` — встроенный Django-флаг ровно для этого: «допущен в управленческие интерфейсы». Когда понадобятся роли — добавим Django Groups, без переписывания auth-зоны.

### Permission-класс

Новый класс в `apps/crm_api/permissions.py`:

```python
class IsCRMStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
```

Применяется глобально ко всем `/api/crm/*` через базовый view-class (см. §3).

### Механизм авторизации запросов

**Django session-cookie:**
- `sessionid` — httpOnly, Secure, SameSite=Lax
- Ставится при `POST /api/crm/auth/login/`
- Удаляется при `POST /api/crm/auth/logout/`
- Authentication class на бэке: штатный `rest_framework.authentication.SessionAuthentication`
- Срок жизни: дефолт Django (2 недели)

**CSRF:**
Django выставляет `csrftoken` cookie. Фронт считывает и шлёт в `X-CSRFToken` при не-GET запросах (включая login). Read-only-эндпоинты не используют CSRF, но инфра готовится сразу под будущие мутации (M3).

### Изоляция от других auth-зон

`/api/crm/*` использует **только** `SessionAuthentication + IsCRMStaff`. Существующие зоны не трогаются:
- `/api/auth/*`, `/api/customer/*` — JWT через `apps/common/authentication.py` (мобильное приложение)
- `/api/bot/*` — `X-Telegram-User-Id` через `apps/common/permissions.py::TelegramUserPermission`
- `/onec/*` — `X-Api-Key` через `apps/api/security.py::require_onec_auth`

Если менеджер случайно зайдёт на `/api/customer/*` — его session-cookie там не сработает, ApiKeyPermission/JWT не пропустит → 403.

### Auth endpoints

```
POST /api/crm/auth/login/    {email, password} → 200 + Set-Cookie sessionid + {user:{...}}
POST /api/crm/auth/logout/                     → 204 + Delete-Cookie sessionid
GET  /api/crm/auth/me/                         → 200 {user:{...}} | 401
```

`me` — для bootstrap-flow на фронте: при загрузке CRM делаем `GET /me`, если 200 → у пользователя живая сессия → пускаем; если 401 → редирект на `/login`.

**Защита от brute-force:** login-endpoint навешан на существующий `AnonAuthThrottle` (10/min на IP). Достаточно для staff-tool на ~10 человек.

---

## 3. Backend structure (`apps/crm_api/`)

### Файловая раскладка

```
backend/apps/crm_api/
├── __init__.py
├── apps.py                    # CrmApiConfig
├── permissions.py             # IsCRMStaff
├── urls.py                    # roots + nested
├── views/
│   ├── __init__.py
│   ├── _base.py               # CRMAPIView с auth/permission по умолчанию
│   ├── auth.py                # LoginView, LogoutView, MeView
│   ├── dashboard.py           # DashboardView
│   ├── clients.py             # ClientListView, ClientDetailView
│   ├── orders.py              # OrderListView
│   ├── campaigns.py           # CampaignListView
│   ├── broadcasts.py          # BroadcastHistoryView
│   ├── categories.py          # CategoryListView, CategoryDetailView
│   └── abc_xyz.py             # AbcXyzView
├── serializers/
│   ├── __init__.py
│   ├── auth.py                # LoginSerializer, MeSerializer
│   ├── client.py              # ClientListSerializer, ClientDetailSerializer
│   ├── order.py               # OrderListSerializer
│   ├── campaign.py            # CampaignListSerializer
│   ├── broadcast.py           # BroadcastHistorySerializer
│   ├── category.py            # CategoryListSerializer, CategoryDetailSerializer
│   └── abc_xyz.py             # AbcXyzSerializer
├── services/                  # вычисления KPI/агрегаций отдельно от views
│   ├── __init__.py
│   └── dashboard.py           # compute_dashboard_kpis(), compute_daily_revenue()
└── tests/
    ├── __init__.py
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

### Принципы

- **Один view = один endpoint.** Без массивных ViewSet'ов с `list+create+update+destroy`. На M1 у нас только `GET`-методы. Когда придут мутации (M3) — в тот же файл добавятся `Create*View`.
- **Сериализаторы отдельно от views.** Импортируем модели (`apps.main.CustomUser`, `apps.orders.Order`) и пишем CRM-специфичные сериализаторы. Они отличаются от мобильных (`name`, `lastOrder`, `bonus` без чувствительных полей вроде `password_hash`, `referrer_id`).
- **N+1 предотвращаем сразу.** В каждом `ListView.get_queryset()` ставим `prefetch_related/select_related` для полей, которые читает сериализатор. Тест `assertNumQueries(N)` фиксирует число запросов.
- **Агрегации — в `services/`.** Dashboard KPIs (revenue/orders/aov/conv) — `Sum/Count/Avg`, не относятся к одной модели. Логика в `services/dashboard.py`, view только сериализует. Это позволит потом использовать ту же функцию из Celery beat для прогрева кэша.

### Базовый view-class

```python
# apps/crm_api/views/_base.py
from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView
from apps.crm_api.permissions import IsCRMStaff


class CRMAPIView(APIView):
    """Base for CRM endpoints: session auth + IsCRMStaff."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsCRMStaff]
```

Login-views переопределяют `permission_classes = [AllowAny]`; всё остальное наследует от `CRMAPIView`.

### URL-роутинг

В корневом `apps/api/urls.py`:
```python
path("crm/", include("apps.crm_api.urls")),
```

`apps/crm_api/urls.py`:
```python
urlpatterns = [
    path("auth/login/",  LoginView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/me/",     MeView.as_view()),
    path("dashboard/",   DashboardView.as_view()),
    path("clients/",                 ClientListView.as_view()),
    path("clients/<str:card_id>/",   ClientDetailView.as_view()),
    path("orders/",                  OrderListView.as_view()),
    path("campaigns/",               CampaignListView.as_view()),
    path("broadcasts/history/",      BroadcastHistoryView.as_view()),
    path("categories/",              CategoryListView.as_view()),
    path("categories/<slug:slug>/",  CategoryDetailView.as_view()),
    path("abc-xyz/",                 AbcXyzView.as_view()),
]
```

### Регистрация app

`backend/settings.py` → `INSTALLED_APPS`:
```python
'apps.crm_api.apps.CrmApiConfig',
```

---

## 4. Frontend structure (`crm-web/src/`)

### Новые папки

```
crm-web/src/
├── api/                       # ← новое
│   ├── client.js              # fetch-обёртка с CSRF + credentials
│   ├── auth.js                # login/logout/me
│   ├── clients.js             # listClients(), getClient(card_id)
│   ├── orders.js              # listOrders(filters)
│   ├── campaigns.js
│   ├── broadcasts.js
│   ├── categories.js
│   ├── abcXyz.js
│   └── dashboard.js
├── hooks/                     # ← новое (react-query)
│   ├── useAuth.js             # useMe(), useLoginMutation(), useLogoutMutation()
│   ├── useClients.js          # useClients(filters), useClient(card_id)
│   ├── useOrders.js
│   ├── useCampaigns.js
│   ├── useBroadcasts.js
│   ├── useCategories.js       # useCategories(), useCategory(slug)
│   ├── useAbcXyz.js
│   └── useDashboard.js
├── auth/                      # ← новое
│   ├── AuthProvider.jsx       # context: {user, isLoading, isAuthenticated}
│   ├── ProtectedRoute.jsx     # wraps routes
│   └── LoginScreen.jsx        # /login route
├── components/                # уже существует
├── components/primitives/     # уже существует
├── screens/                   # экраны мигрируют на хуки
└── fixtures/                  # ← удаляется в конце M1
```

### API-клиент `api/client.js`

Тонкая обёртка над `fetch`:
- Базовый префикс `/api/crm` (через `import.meta.env.VITE_API_BASE` для prod-домена)
- `credentials: 'include'` для cookie
- Чтение `csrftoken` cookie + `X-CSRFToken` заголовок для не-GET запросов
- Парсит JSON, бросает `ApiError(status, body)` на 4xx/5xx
- На 401 бросает `UnauthorizedError`, который ловит глобальный interceptor (см. §5)

### React-query setup

`QueryClient` создаётся в `src/main.jsx`, обёртка `<QueryClientProvider>` над `<App>`. Дефолты:
- `staleTime: 60_000` (минута)
- `retry: 1`
- `refetchOnWindowFocus: true`

Глобальный обработчик `queryCache.onError`: если `UnauthorizedError` → `queryClient.clear()` + `navigate('/login?next=' + currentPath)`.

### Auth-flow

`AuthProvider.jsx`:
```jsx
const { data: user, isLoading } = useQuery(['auth/me'], () => api.auth.me());
return <AuthCtx.Provider value={{ user, isLoading, isAuthenticated: !!user }}>...</AuthCtx.Provider>;
```

Один `GET /api/crm/auth/me/` при старте. Пока `isLoading` — `<Splash/>`. Если `user` есть — рендерим CRM. Если 401 — `ProtectedRoute` редиректит.

`ProtectedRoute.jsx`:
```jsx
function ProtectedRoute({ children }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return <Splash />;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return children;
}
```

### Замена фикстур на хуки

Каждый экран сейчас:
```jsx
import clients from '../fixtures/clients.js';
```

Становится:
```jsx
import { useClients } from '../hooks/useClients.js';

function ClientsScreen() {
  const [q, setQ] = useState('');
  const [seg, setSeg] = useState('Все');
  const [page, setPage] = useState(1);
  const { data, pagination, isLoading, error, refetch } = useClients({ q, segment: seg, page });

  if (isLoading) return <ScreenSkeleton variant="table" />;
  if (error)     return <ErrorBanner error={error} onRetry={refetch} />;
  return <ClientsTable rows={data} pagination={pagination} />;
}
```

**Контракт хука:** `useClients` (и аналоги для списочных endpoint'ов) парсит ответ так:
- `data` — массив `results` из body
- `pagination` — `{page, totalPages, total}`, восстанавливается из заголовков `X-Page`, `X-Total-Count`, `X-Page-Size` (расчёт `totalPages = ceil(total / page_size)`)
- `isLoading`, `error`, `refetch` — стандартные поля react-query

Это инкапсулирует логику `HeaderPagination` внутри API-клиента — экраны не работают с заголовками напрямую.

### Vite-proxy для dev

`crm-web/vite.config.js`:
```js
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: false,
    },
  },
},
```

Фронт «думает», что всё на одном origin → cookie работают без CORS-настроек.

### Удаление фикстур

В конце M1 папка `crm-web/src/fixtures/` удаляется. Скрипт `scripts/extract_crm_reference.py` остаётся (уже не нужен, но безвредно). `.reference/` остаётся в `.gitignore`.

---

## 5. API contract (12 endpoints)

Все ответы — JSON, UTF-8. Ошибки в формате DRF: `{"detail": "..."}` для 401/403/404, `{"field": ["msg"]}` для 400 валидации. Списочные эндпоинты используют существующий `HeaderPagination` (заголовки `X-Total-Count`, `X-Page`, `X-Page-Size`, `Link`).

### Принципы контракта

- **camelCase в JSON** — Django сериализатор маппит, на бэке внутри snake_case.
- Даты в **ISO-8601** (UTC). Фронт парсит через `fmtDate(...)`.
- Деньги — целые в **рублях** (без копеек). `Decimal` копейки округляем в сериализаторе.
- **Никаких чувствительных полей**: `password_hash`, `auth_method`, `referrer_id` не отдаются.
- Цвета/визуальные атрибуты на фронте; бэк отдаёт только семантику (`"A"`, `"X"`).

### Auth

```
POST /api/crm/auth/login/
  Body: {"email": "manager@lakshmi.ru", "password": "..."}
  200:  {"user": {"id": 1, "email": "manager@lakshmi.ru", "name": "Иван Сидоров"}}
        + Set-Cookie: sessionid=...; csrftoken=...
  400:  {"email": ["..."]} | {"password": ["..."]}
  401:  {"detail": "Неверный email или пароль"}
  403:  {"detail": "Нет доступа в CRM"}        # is_staff=False

POST /api/crm/auth/logout/
  204:  (Set-Cookie sessionid=; expires=…)

GET  /api/crm/auth/me/
  200:  {"user": {"id": 1, "email": "...", "name": "..."}}
  401:  {"detail": "Требуется авторизация"}
```

### Dashboard

```
GET /api/crm/dashboard/
  200: {
    "kpis": [
      {"id":"customers","label":"Активные клиенты","value":10084,"delta":182,"deltaLabel":"+182 за неделю","format":"number"},
      {"id":"orders","label":"Заказы сегодня","value":74,"delta":0.12,"deltaLabel":"+12% к среднему","format":"number"},
      {"id":"revenue","label":"Выручка за неделю","value":1248320,"delta":0.042,"deltaLabel":"+4,2%","format":"rubShort"},
      {"id":"bonuses","label":"Бонусов на балансе","value":2410880,"delta":-0.011,"deltaLabel":"−1,1%","format":"number"}
    ],
    "daily": [{"date":"2026-04-15","orders":74,"revenue":78200}, ...],
    "activeCampaigns": [{"id":"CMP-7","name":"Весенний кешбэк 7%","hint":"RFM: Чемпионы · 412 клиентов"}, ...],
    "rfmSegments": [{"name":"Чемпионы","count":412,"share":4.1}, ...]
  }
```

KPIs «за неделю» = последние 7 дней по `Order.created_at`. Кэш на 5 минут (Django cache).

### Clients

```
GET /api/crm/clients/?q=&segment=&page=1&page_size=50
  q (optional)        — поиск по name/phone/email/card_id
  segment (optional)  — Чемпионы | Лояльные | Новички | Спящие | Рискуют уйти | Потерянные | Все
  200: {"results": [
    {"id":"LC-001042","name":"Сардаана Николаева","phone":"+7 914 222-31-09","email":"sardana@example.ru",
     "rfmSegment":"Чемпионы","bonus":1840,"ltv":78420,"purchaseCount":34,
     "lastOrder":"2026-04-14","tags":["vip"]}, ...
  ]}

GET /api/crm/clients/<card_id>/
  200: {
    "id":"LC-001042","name":"...","phone":"...","email":"...","telegramId":142839201,
    "rfmSegment":"Чемпионы","bonus":1840,"ltv":78420,"purchaseCount":34,
    "lastOrder":"2026-04-14","tags":["vip","много бонусов"],
    "preferences":{"push":true,"telegram":true,"email":true,"sms":false},
    "orders":[{"id":"ORD-30412","date":"2026-04-15T14:32:00","amount":2340,"status":"assembly"}, ...],
    "activeCampaigns":[{"id":"CMP-7","name":"Весенний кешбэк 7%","rules":"7% бонусов"}, ...]
  }
  404: {"detail":"Клиент не найден"}
```

`id` в API — это `card_id` (string `LC-001042`), используется в URL фронта. Backend хранит и числовой `pk` (CustomUser.id), и `card_id`; в API отдаём `card_id` как `id` для устойчивости URL'ов от смены БД-pk.

### Orders

```
GET /api/crm/orders/?status=&purchaseType=&page=1&page_size=50
  status        — new | accepted | assembly | ready | delivery | arrived | completed | canceled | Все
  purchaseType  — delivery | pickup | in_store | Все
  200: {"results": [
    {"id":"ORD-30412","date":"2026-04-15T14:32:00","clientId":"LC-001042","clientName":"...",
     "amount":2340,"status":"assembly","purchaseType":"delivery","items":7,
     "address":"ул. Лермонтова, 24, кв. 12","payment":"sbp","courier":"—"}, ...
  ]}
```

### Campaigns

```
GET /api/crm/campaigns/?status=&page=1&page_size=50
  status — active | draft | finished | all
  200: {"results": [
    {"id":"CMP-7","name":"Весенний кешбэк 7%","slug":"spring-cb-7","status":"active",
     "period":{"from":"2026-04-01","to":"2026-04-30"},"reach":412,"used":287,
     "segment":"Чемпионы","audience":"RFM: Champions","rules":"7% бонусов","priority":200}, ...
  ]}
```

### Broadcasts

```
GET /api/crm/broadcasts/history/?page=1&page_size=50
  200: {"results": [
    {"id":"BR-103","sentAt":"2026-04-12T10:00:00","segment":"Все клиенты",
     "channel":"telegram","reach":8240,"opened":5612,"clicked":1820}, ...
  ]}
```

### Categories

```
GET /api/crm/categories/
  (без пагинации — категорий обычно <100)
  200: {"results": [
    {"id":1,"slug":"cat-01","code":"01","name":"Молочные продукты","skus":142,
     "revenue":2840000,"cogs":1980000,"share":22.4,"turnover":8.4,
     "abc":"A","xyz":"X","trend":[62,68,71,69,74,78,82,85,88,86,89,92]}, ...
  ]}

GET /api/crm/categories/<slug>/
  200: {
    "id":1,"slug":"cat-01","code":"01","name":"Молочные продукты",
    "skus":142,"revenue":2840000,"cogs":1980000,"share":22.4,"turnover":8.4,
    "abc":"A","xyz":"X","trend":[...],
    "skuList":[
      {"id":"0101-001","name":"Молоко 3,2% 1 л","stock":84,"units30d":142,
       "sales30d":286000,"abc":"A","xyz":"X","suggestedOrder":920,
       "stockDays":0.6,"supplier":"Молочный край","spark":[...]}, ...
    ]
  }
  404: {"detail":"Категория не найдена"}
```

### ABC/XYZ

```
GET /api/crm/abc-xyz/
  200: {
    "matrixSku":     {"AX":84,"AY":56,"AZ":18,"BX":142,"BY":168,"BZ":92,"CX":218,"CY":384,"CZ":240},
    "matrixRevenue": {"AX":4830000,"AY":2980000,"AZ":840000,"BX":1640000, ...},
    "matrixShare":   {"AX":6.0,"AY":4.0,"AZ":1.3, ...}
  }
```

---

## 6. Login UX и Error/Loading flow

### Login screen (`/login`)

Пустой layout (без Sidebar и TopBar). Центрированная карточка, токены `--surface-page` / `--surface-panel`.

**Структура:** logo → заголовок «Lakshmi CRM / Вход для менеджеров» → поле email → поле пароль → (опц.) banner с ошибкой → кнопка «Войти».

**Валидация (на фронте):**
- email: непусто, содержит `@`
- пароль: непусто, длина ≥ 1
- На submit без валидации — кнопка disabled, ошибки под полем

**Submit-flow:**
1. Кнопка → `<Spinner/> Вход…`, форма disabled
2. `POST /api/crm/auth/login/` с `email + password`
3. **200** → `queryClient.invalidateQueries(['auth/me'])` → AuthProvider получает user → `navigate(state.from ?? '/dashboard')`
4. **400** → подсветка поля + текст ошибки под ним
5. **401** → banner «Неверный email или пароль»
6. **403** → banner «У этого аккаунта нет доступа в CRM»
7. **5xx / network** → banner «Ошибка сервера, попробуйте позже» + retry

### Logout

Кнопка профиля в `TopBar` (сейчас не нажимается) → раскрывающееся меню с email и кнопкой «Выйти». Клик → `POST /api/crm/auth/logout/` → `queryClient.clear()` → `navigate('/login', {replace: true})`.

### 401 flow (сессия истекла во время работы)

Глобальный обработчик в `QueryClient`:
```js
queryClient.setDefaultOptions({
  queries: {
    onError: (err) => {
      if (err instanceof UnauthorizedError) {
        queryClient.clear();
        navigate(`/login?next=${encodeURIComponent(location.pathname)}`, { replace: true });
      }
    },
  },
});
```

После повторного логина `next`-параметр возвращает на исходный экран. Кэш чистый, все экраны делают свежие запросы.

### Error states

| Код | UX |
|-----|----|
| 401 | Глобальный — редирект на `/login` |
| 403 | Inline `<ErrorBanner>` на текущем экране (маловероятно в M1) |
| 404 (detail) | `<EmptyState>` с кнопкой «Назад к списку» |
| 5xx | `<ErrorBanner>` с кнопкой «Повторить» (`refetch`) |
| Network | `<ErrorBanner>`: «Нет соединения с сервером. Повторить» |
| 400 | На list — banner; на login — inline под полем |

**`<ErrorBanner>`** (новый компонент в `components/`):
```jsx
<ErrorBanner title="Не удалось загрузить заказы" hint={error?.message} onRetry={() => refetch()} />
```

### Loading states

**Initial load (нет данных в кэше):**
- Layout уже отрендерен (sidebar + topbar)
- В контентной области — `<ScreenSkeleton>`:
  - `variant="table"` — N серых строк-плейсхолдеров (для list)
  - `variant="card"` — серая карточка-плейсхолдер (для detail)
  - `variant="dashboard"` — 4 KPI-плейсхолдера + bar-плейсхолдер

**Refetch (есть старые данные):**
- Старые данные на экране, без skeleton'ов
- В углу мини-индикатор `<Spinner size={12}/>` (опц.)
- Если refetch упал — `<ErrorBanner>` поверх + старые данные остаются

**App initial bootstrap (`GET /me`):**
- Полноэкранный `<Splash/>` (логотип + спиннер)
- Длится <500мс при живой сессии

---

## 7. Testing strategy

### Backend (Django test runner, `apps/crm_api/tests/`)

1. **Permission tests** — параметризованный тест по всем CRM-endpoints: 401 без session, 403 с обычной session (`is_staff=False`), 200 с staff-session.
2. **Auth tests** — login happy path, неверный пароль (401), `is_staff=False` (403), rate-limit (429 после 11 попыток), logout, me.
3. **List endpoints** — happy path, фильтры (`?segment=`, `?status=`), поиск (`?q=`), пагинация. **`assertNumQueries(N)`** — фиксируем число SQL-запросов.
4. **Detail endpoints** — happy path, 404 для несуществующего, связанные данные (orders, activeCampaigns).
5. **Dashboard** — KPIs корректны для контролируемых данных, кэш работает (`assertNumQueries(0)` на повторе).

**Фикстуры:** через factory_boy или штатные `setUp`. Минимально-необходимое.

**Что НЕ тестируем сейчас:** интеграцию с 1С, FCM, ЮKassa-webhook (CRM их не трогает).

### Frontend (vitest + @testing-library/react + MSW)

**Новая зависимость:** `msw` (~10kb) — мокаем `/api/crm/*` на уровне fetch.

1. **Auth tests** (`__tests__/auth.test.jsx`):
   - LoginScreen submit happy path → `navigate('/dashboard')` вызывается
   - 401 → banner «Неверный email или пароль»
   - 403 → banner «Нет доступа в CRM»
   - ProtectedRoute без user → редирект на /login
   - Logout → POST вызван, redirect на /login

2. **Screen smoke tests** (`__tests__/screens.test.jsx`) — расширение `routes.test.jsx`. Для каждого из 9 экранов:
   - Live session + mock data → экран рендерит данные
   - 500 от list → `<ErrorBanner>` с retry
   - Initial load → `<ScreenSkeleton>`

3. **Hook tests** (`__tests__/hooks.test.js`):
   - `useClients({segment:'Чемпионы'})` → fetch с `?segment=Чемпионы`
   - `useClient('LC-no-such')` → 404 → `error` проброшен

4. **Routes test** — обновляем существующий: 24 текущих smoke под mock-API, добавляем `/login` и редиректы.

**Что НЕ тестируем на фронте:** реальные API-запросы (только моки), E2E (отдельная задача).

### CI

В рамках M1 CI не настраиваем (M4). Локальная проверка:
- `make test-backend` (с новым `apps.crm_api`)
- `cd crm-web && npm run test`
- `cd crm-web && npm run lint`
- `cd crm-web && npm run build`

---

## 8. Definition of Done

Milestone закрыт, когда **все** пункты выполнены:

1. **Auth работает:**
   - Менеджер с `is_staff=True` логинится через `/login`, видит `/dashboard`
   - Менеджер без `is_staff` → 403 banner на `/login`
   - Без auth все `/api/crm/*` → 401
   - Logout кнопкой → редирект на `/login`
   - Сессия истекает → редирект на `/login?next=...` без потери intended URL

2. **9 экранов на реальных API:**
   - Все экраны импортируют хуки `useClients/useOrders/...`
   - Никто не импортирует `fixtures/*.js`
   - Папка `crm-web/src/fixtures/` удалена
   - Фильтры/поиск/пагинация делают новый запрос с правильным query-string

3. **Backend:**
   - 12 endpoints (3 auth + 9 data) реализованы
   - Permission `IsCRMStaff` применён ко всем эндпоинтам, кроме login
   - `assertNumQueries` тесты проходят — нет N+1 в сериализаторах
   - Dashboard-агрегации кэшируются на 5 минут

4. **UX:**
   - Skeleton при initial load, ErrorBanner при ошибках, EmptyState при 404
   - Vite-proxy `/api/*` работает в dev
   - LoginScreen рендерится на пустом layout (без sidebar/topbar)

5. **Тесты:**
   - Backend: все тесты `apps.crm_api.tests` зелёные, `assertNumQueries` зафиксированы
   - Frontend: vitest зелёный, ESLint без ошибок, prod-build собирается

6. **Документация:**
   - `crm-web/README.md` — dev-запуск с Django backend, переменная `VITE_API_BASE` (если нужна)
   - `docs/ARCHITECTURE.md` — раздел «CRM API» с описанием auth-зоны и эндпоинтов

### Метрики успеха

- Менеджер открывает CRM, логинится, видит реальных клиентов на дашборде — за <30 секунд
- Список 1000+ клиентов с фильтром — <500мс (с кэшем — <100мс)
- 0 свежих фикстур: `grep -r 'fixtures' crm-web/src/screens/` пустой
- Backend-тесты CRM ≥ 30, frontend-тесты ≥ 30, оба suite зелёные

---

## 9. Риски

| Риск | Вероятность | Митигация |
|---|---|---|
| Cross-origin cookie не работает между Vite (5173) и Django (8000) в dev | Средняя | Vite-proxy решает (фронт «думает», что всё на 5173) |
| CSRF-токен не доходит до Django в `POST /login` | Низкая | Django ставит `csrftoken` на `GET /me`, фронт читает и шлёт в header. Тесты login-flow |
| N+1 в `clients/<id>/` (orders + activeCampaigns nested) | Высокая | Тест `assertNumQueries(≤4)`. Использовать `prefetch_related('orders__items', 'campaigns')` |
| Dashboard-агрегации тормозят на боевых данных (10к пользователей, 100к заказов) | Средняя | Кэш на 5 минут. Если не хватит — материализованные view (out of scope) |
| Менеджер не знает свой пароль (первый раз) | Высокая на старте | Чеклист в `docs/`: «как создать менеджера через /admin/». Без password-reset infra это операционная задача |
| Старая мобилка (с JWT) сломается из-за изменений в auth-зоне | Низкая | CRM-зона полностью изолирована (`/api/crm/*`). Существующие `/api/customer/*`, `/api/auth/*` не трогаются. Тестами закрепить |
| Фронт случайно начнёт слать `csrftoken` на не-CRM endpoints | Низкая | Один axios/fetch instance с baseURL `/api/crm` — другие endpoints просто не используются из CRM |
| Тесты с MSW замедляют suite | Низкая | MSW грузится 1 раз при setup. Существующие 24 smoke-теста идут <2с — добавим ~30, бюджет ~10с |

---

## 10. Связь со spec'ом прототипа

Этот milestone — продолжение `docs/superpowers/specs/2026-04-29-crm-web-prototype-design.md`.

**Что уже есть** (из M0/прототипа):
- 9 рабочих экранов + 3 заглушки (RFM, Catalog, Analytics)
- Дизайн-токены, dark theme
- Sidebar / TopBar / роутинг
- 24 smoke-теста routing
- `make crm-dev/build/test/lint/preview`

**Что добавит M1:**
- 13-й маршрут `/login`
- API-слой (`api/`, `hooks/`, `auth/`)
- 12 endpoints на бэке (`apps/crm_api/`)
- ScreenSkeleton, ErrorBanner, Splash компоненты

**Что не меняет M1:**
- Дизайн существующих 9 экранов (компоновка, цвета, иконки)
- Фикстуры RFM/Catalog/Analytics-заглушек (`<Placeholder>`) — остаются на месте до M2
- `routes.jsx` — добавляется `/login`, остальное без изменений
