FROM python:3.10

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем entrypoint из папки backend

COPY backend/ ./backend/
COPY src/ ./src/
COPY entrypoint.sh .

CMD ["sh", "./entrypoint.sh"]