# Lakshmi CRM Web (prototype)

Статичный кликабельный прототип CRM на фикстурах. Без backend, без авторизации.

**Stack:** Vite 5 + React 18 + react-router-dom 6 + lucide-react.

## Запуск

```bash
npm install         # один раз
npm run dev         # http://127.0.0.1:5173/
npm run build       # сборка в ./dist
npm run preview     # просмотр production-сборки
npm run test        # vitest run
npm run lint        # eslint src
```

Из корня репо: `make crm-dev`, `make crm-build`, `make crm-test`, `make crm-lint`, `make crm-preview`.

## Структура

- `src/screens/` — экраны (один файл — один маршрут).
- `src/components/` — общие компоненты (Sidebar, TopBar, Icon, Placeholder, EmptyState, ErrorBoundary).
- `src/components/primitives/` — переиспользуемые UI-примитивы (Stat, KV, Toggle, Field, BarChart, Sparkline, StockBar, AbcBadge, XyzBadge, SuggestedOrder, AbcXyzMatrix, ActiveCampaign).
- `src/fixtures/` — статичные данные (clients, orders, campaigns, etc.).
- `src/styles/tokens.css` — единый источник цветов и токенов (dark theme).
- `src/utils/format.js` — форматирование чисел и дат.
- `src/routes.jsx` — карта маршрутов и заголовков (SCREEN_TITLES, ROUTES).
- `.reference/` — распакованный референс-артефакт (gitignored, регенерируется через `python3 ../scripts/extract_crm_reference.py`).

## Spec и план

- Spec: `../docs/superpowers/specs/2026-04-29-crm-web-prototype-design.md`
- Plan: `../docs/superpowers/plans/2026-04-29-crm-web-prototype.md`
