# Lakshmi Photo Studio

Mobile-first PWA для сотрудников магазина: массовая съёмка товаров,
обработка фото через OpenAI Image API на backend и обновление каталога
доставки.

## Стек

- React 18 + Vite 5
- React Router v6
- axios
- vite-plugin-pwa (Workbox)
- inline-стили на базе общей темы `src/theme.js`

## Команды

```bash
npm install
npm run dev       # http://localhost:5173
npm run build     # сборка в dist/
npm run preview   # локальный просмотр сборки на 4173
```

## Конфигурация

1. Скопируйте `.env.example` в `.env` и укажите `VITE_API_BASE_URL`
   (адрес backend, например `http://localhost:8000`).
2. При первом запуске приложение запросит **X-Api-Key** — это
   `INTEGRATION_API_KEY` backend. Ключ сохраняется в `localStorage`
   и шлётся во всех запросах.

## Backend контракт

- `GET /api/products/?search=&category_id=&page=&page_size=` — каталог;
- `GET /api/catalog/root/`, `GET /api/catalog/<id>/children/` — категории;
- `POST /api/products/<id>/image/` (`multipart/form-data`, поле `image`) —
  загрузка фото. Backend обрабатывает через OpenAI и сохраняет в
  `media/products/`. Ответ содержит обновлённый `image_url`.

Если backend и фронт живут на разных доменах, на backend нужно задать
`CORS_ALLOWED_ORIGINS` (см. `backend/settings.py`).

## Структура

```
src/
├── api/         # axios-клиент и HTTP-функции
├── components/  # UI-компоненты
├── context/     # SessionContext (выбранный товар, файл, last image_url)
├── hooks/       # useProducts, useCategories, useApiKey, useNetworkStatus, useDailyProgress
├── pages/       # 5 экранов: Catalog, Camera, Preview, Form, Success
├── utils/       # photoStatus, format
├── theme.js     # палитра BRAND
├── App.jsx
└── main.jsx
```

## Поток сотрудника

1. Каталог → выбор товара без фото.
2. Камера / загрузка из галереи.
3. Превью RAW → нажать «Принять» → backend стилизует через OpenAI.
4. Успех: обновлённое фото, прогресс дня, кнопка «Следующий товар».

## Известные ограничения MVP

- Нет полноценной offline-очереди фото; при потере сети текущий снимок
  остаётся в памяти до восстановления соединения.
- Один глобальный X-Api-Key (без per-user JWT). Audit per-user добавляется
  поверх в следующих итерациях.
- AI-генерация описания товара не реализована (опциональный пункт TASK.md).
