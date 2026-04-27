# Минимальный образ для openai-proxy.
# Деплоится отдельно от основного backend (на VPS).
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Создаём непривилегированного пользователя.
RUN groupadd --system app && useradd --system --gid app --home /app app

COPY app ./app

USER app

EXPOSE 8080

# uvicorn слушает на 0.0.0.0 — наружу проброс закрыт firewall'ом VPS,
# доступ только с IP основного backend (см. docs/openai-proxy-deploy.md).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8080/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
