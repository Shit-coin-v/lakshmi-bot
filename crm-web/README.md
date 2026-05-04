# Lakshmi CRM Web

**Stack:** Vite 5 + React 18 + React Router 6 + React Query 5 + lucide-react.

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
- `src/__tests__/` — vitest + MSW; backend моки на уровне fetch.
- `.reference/` — распакованный референс-артефакт (gitignored, регенерируется через `python3 ../scripts/extract_crm_reference.py`).
