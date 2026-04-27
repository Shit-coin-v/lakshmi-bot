# lakshmi openai-proxy

Минимальный FastAPI-сервис, который скрывает `OPENAI_API_KEY` от основного backend.
Деплоится отдельно (на VPS), принимает запросы только с IP основного backend и
проксирует их в OpenAI Image API.

## Архитектура

```
photo-studio  →  Django backend  →  openai-proxy (этот сервис)  →  OpenAI API
                  X-Api-Key            X-Internal-Api-Key                
```

- `OPENAI_API_KEY` живёт **только** на VPS с proxy.
- Django backend НЕ знает реальный ключ OpenAI — у него только `OPENAI_PROXY_API_KEY`.
- Photo-studio (frontend) о proxy не знает — внешний контракт endpoint
  `POST /api/products/<id>/image/` не меняется.

## Endpoints

### `GET /health`

Без аутентификации. Возвращает `{"status":"ok"}`. Использовать для healthcheck Docker
и мониторинга.

### `POST /v1/images/edit`

Требует заголовок `X-Internal-Api-Key`. Тело — `multipart/form-data`:

| поле   | тип    | пример              |
|--------|--------|---------------------|
| image  | file   | `photo.png` (binary)|
| prompt | string | `"studio photo..."` |
| model  | string | `"gpt-image-1"`     |
| size   | string | `"1024x1024"`       |

Ответ при успехе: `200`, `Content-Type: image/png`, тело — байты обработанного PNG.

| код | условие                                              |
|-----|------------------------------------------------------|
| 200 | OpenAI вернул изображение                            |
| 400 | пустой/невалидный запрос                             |
| 401 | нет/неверный `X-Internal-Api-Key`                    |
| 413 | файл больше `MAX_IMAGE_SIZE_BYTES`                   |
| 502 | ошибка OpenAI или невалидный ответ                   |
| 503 | proxy не настроен (нет `OPENAI_API_KEY`/INTERNAL_KEY)|
| 504 | таймаут OpenAI                                       |

## Запуск локально

```bash
cp .env.example .env
# ОТРЕДАКТИРУЙ .env: вставь реальные OPENAI_API_KEY и INTERNAL_API_KEY

docker compose up --build -d
docker compose logs -f openai-proxy

# Проверка
curl -fsS http://localhost:8080/health
```

## Тесты

```bash
pip install -r requirements.txt
pytest -v
```

## Деплой

См. `docs/openai-proxy-deploy.md` в корне репозитория.
