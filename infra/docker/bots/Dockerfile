FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Bot-specific dependencies (no Django/Celery bloat)
COPY bots/customer_bot/requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY bots/ ./bots/
COPY shared/ ./shared/

ENV PYTHONPATH=/app

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

WORKDIR /app/bots/customer_bot

CMD ["python", "run.py"]
