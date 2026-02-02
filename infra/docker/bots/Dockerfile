FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Use shared requirements from backend (includes aiogram, sqlalchemy, etc.)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY bots/ ./bots/

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

WORKDIR /app/bots/customer_bot

CMD ["python", "run.py"]
