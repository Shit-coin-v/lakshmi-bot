# Security Audit

> Дата аудита: 2026-02-02
> Статус: все критичные находки исправлены

## Находки и статус исправления

### P0 — Критичные

#### 1. Утечка API-ключей в stdout через print()
**Файл:** `backend/apps/common/security.py`
**Проблема:** `print()` выводил заголовки запросов и API-ключ сервера в stdout, откуда они попадали в логи Docker и системы мониторинга.
```python
# Было:
print(f"HEADER: '{key}' = '{value}'")
print(f"DEBUG: SERVER_KEY='{API_KEY}' | CLIENT_KEY='{api_key}'")
```
**Исправление:** Заменено на `logger.debug()` без вывода секретов.
**Статус:** ✅ Исправлено

#### 2. Production-конфиг в git
**Файл:** `infra/docker/docker-compose.override.yml`
**Проблема:** Файл с production-переопределениями находился под контролем версий.
**Исправление:** Добавлен в `.gitignore`, создан шаблон `docker-compose.override.yml.example`.
**Статус:** ✅ Исправлено

#### 3. CELERY_TASK_ALWAYS_EAGER в production settings
**Файл:** `backend/settings.py`
**Проблема:** Celery-задачи выполнялись синхронно во всех окружениях, включая production. Это приводило к блокировке API-запросов на время выполнения задач и отсутствию retry-логики.
**Исправление:** Перенесено в `backend/settings_test.py`. Production использует Redis как брокер.
**Статус:** ✅ Исправлено

### P1 — Высокий приоритет

#### 4. Docker images без фиксированных версий
**Файлы:** `docker-compose.yml`
**Проблема:** Использование тега `:latest` для nginx, grafana и др.
**Исправление:** Все образы закреплены на конкретные версии:
- `grafana/promtail:2.9.6`
- `grafana/loki:2.9.6`
- `prom/prometheus:v2.48.1`
- `grafana/grafana:10.4.3`
- `postgres:17`
- `redis:7`
- `metabase/metabase:v0.50.36`

**Статус:** ✅ Исправлено

#### 5. Bare `except Exception` без специфичных типов
**Файлы:** `order_sync.py`, `tasks.py`, `order_status.py`, `signals.py`
**Проблема:** Перехват всех исключений маскировал ошибки программирования.
**Исправление:**
- `order_sync.py`: `except (requests.RequestException, RuntimeError)`
- `tasks.py`: `except requests.RequestException`
- Оставшиеся defensive-блоки помечены `# pragma: no cover`

**Статус:** ✅ Исправлено

### P2 — Средний приоритет

#### 6. Race conditions при миграциях
**Файл:** `backend/entrypoint.sh`
**Проблема:** Миграции выполнялись в `entrypoint.sh` каждого контейнера. При масштабировании несколько контейнеров одновременно пытались применить миграции.
**Исправление:** Миграции вынесены в отдельный сервис `migrate` с профилем `setup`.
**Статус:** ✅ Исправлено

## Рекомендации (не реализовано)

- Настроить ротацию API-ключей для 1C интеграции
- Добавить rate limiting на API endpoints
- Настроить Content Security Policy headers
- Провести DAST-сканирование production окружения
