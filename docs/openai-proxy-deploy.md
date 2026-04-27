# Деплой openai-proxy на внешний VPS

Инструкция по запуску сервиса `openai-proxy/` на отдельном VPS.
Основной проект (Django backend, БД, 1С-интеграции, ЮKassa, заказы, бонусы)
на VPS не переносится — туда едет только этот микросервис.

## Архитектура

```
photo-studio (browser, общедоступно)
        ↓ POST /api/products/<id>/image/  multipart, X-Api-Key
Django backend (текущий сервер)
        ↓ POST /v1/images/edit             multipart, X-Internal-Api-Key
openai-proxy (внешний VPS)
        ↓ images.edit(...)                  Bearer OPENAI_API_KEY
OpenAI API
```

`OPENAI_API_KEY` живёт **только** на VPS proxy. На основном сервере его нет.

## Подготовка VPS

Минимальные требования: 1 CPU, 1 GB RAM, 5 GB диск, Linux (Ubuntu 22.04+/Debian 12).
Установить:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin curl ufw
sudo usermod -aG docker $USER
# перелогиниться, чтобы группа docker применилась
```

## Установка proxy

```bash
# 1. Клонировать или скопировать каталог openai-proxy/ на VPS.
#    Можно tar/scp, можно git sparse-checkout — БЕЗ всего остального проекта.
mkdir -p /opt/lakshmi
cd /opt/lakshmi
# (например) scp -r openai-proxy oem@vps:/opt/lakshmi/
cd openai-proxy

# 2. Создать .env из шаблона.
cp .env.example .env

# 3. Сгенерировать INTERNAL_API_KEY (запомни значение, оно понадобится Django'у).
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 4. Отредактировать .env:
#    OPENAI_API_KEY=sk-...           ← реальный ключ OpenAI
#    INTERNAL_API_KEY=<сгенерённый>  ← из шага 3
#    OPENAI_REQUEST_TIMEOUT=120
#    MAX_IMAGE_SIZE_BYTES=10485760
nano .env
chmod 600 .env

# 5. Собрать и поднять контейнер.
docker compose up --build -d

# 6. Проверить логи.
docker compose logs -f openai-proxy
```

## Проверка работы

### `/health` (изнутри VPS)

```bash
curl -fsS http://localhost:8080/health
# ожидаем: {"status":"ok"}
```

### Запрос без ключа должен вернуть 401

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/v1/images/edit
# ожидаем: 401
```

### Тестовая обработка изображения

```bash
curl -fsS -X POST http://localhost:8080/v1/images/edit \
  -H "X-Internal-Api-Key: <значение_INTERNAL_API_KEY>" \
  -F "image=@./test.jpg" \
  -F "prompt=studio product photo, white background" \
  -F "model=gpt-image-1" \
  -F "size=1024x1024" \
  --output processed.png

file processed.png
# ожидаем: processed.png: PNG image data
```

## Сетевая безопасность

Сервис **не должен** быть доступен из открытого интернета. Доступ ограничивается
firewall'ом по IP основного backend-сервера.

### Через UFW

```bash
# BACKEND_IP — публичный IPv4 основного backend-сервера.
BACKEND_IP=203.0.113.10

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp                          # SSH
sudo ufw allow from "$BACKEND_IP" to any port 8080 proto tcp
sudo ufw enable
sudo ufw status numbered
```

### Через iptables (если UFW нет)

```bash
BACKEND_IP=203.0.113.10
sudo iptables -A INPUT -p tcp -s "$BACKEND_IP" --dport 8080 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8080 -j DROP
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

Если у тебя несколько backend-серверов — добавь правило для каждого IP.
**Не открывай 8080 миру** даже на короткое время: `INTERNAL_API_KEY` — единственная
защита уровня приложения, и её одной недостаточно.

### Опционально: TLS

Если VPS проксируется через свой nginx с Let's Encrypt — поставь TLS перед
контейнером proxy и пропишь HTTPS-URL в `OPENAI_PROXY_BASE_URL` на стороне Django.
Для большинства случаев достаточно plain-HTTP внутри VPN/private-сети.

## Переменные на основном backend-сервере

В `.env` основного проекта добавить/обновить:

```env
# Включить proxy-режим.
OPENAI_USE_PROXY=True
# Адрес proxy. Если оба сервера в одной приватной сети — лучше private IP.
OPENAI_PROXY_BASE_URL=http://<VPS_IP_OR_HOSTNAME>:8080
# Должен совпадать с INTERNAL_API_KEY на VPS.
OPENAI_PROXY_API_KEY=<значение_INTERNAL_API_KEY>
# Таймаут запроса. Должен быть >= OPENAI_REQUEST_TIMEOUT на proxy + сетевой запас.
OPENAI_PROXY_TIMEOUT=120

# В proxy-режиме можно (и нужно) очистить:
OPENAI_API_KEY=
```

После правки `.env`:

```bash
# Перезапустить только сервисы, которые читают эти переменные.
docker compose up -d --no-deps app celery_worker
docker compose logs -f app | head -50
```

Проверить, что endpoint работает в proxy-режиме:

```bash
curl -fsS -X POST "https://<your-domain>/api/products/<id>/image/" \
  -H "X-Api-Key: <INTEGRATION_API_KEY>" \
  -F "image=@./test.jpg"
# ожидаем JSON с image_url; в логах backend нет упоминания OpenAI SDK.
```

## Обслуживание

- **Лог:** `docker compose logs --tail=200 -f openai-proxy`. Не должно быть `prompt`,
  байтов изображения или ключей.
- **Обновление:** `git pull && docker compose up --build -d`.
- **Ротация ключей:**
  - сменить `OPENAI_API_KEY` в `.env` proxy → `docker compose restart openai-proxy`;
  - сменить `INTERNAL_API_KEY` → одновременно обновить `OPENAI_PROXY_API_KEY` на
    backend, иначе все запросы получат 401.
- **Мониторинг:** добавить healthcheck на `BACKEND_IP → http://VPS_IP:8080/health`
  в основной Prometheus (см. `infra/observability/prometheus.yml`).

## Что НЕ делаем

- ❌ Не переносим Django backend, Postgres, Celery, Redis, ботов — они остаются
  на основном сервере.
- ❌ Не открываем порт 8080 миру.
- ❌ Не коммитим `.env` proxy в git (`.env*` в `.gitignore`).
- ❌ Не логируем `prompt`, изображения, `OPENAI_API_KEY`, `INTERNAL_API_KEY`.
- ❌ Не меняем внешний контракт `POST /api/products/<id>/image/` — фронт photo-studio
  о proxy не должен знать.
