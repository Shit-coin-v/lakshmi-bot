#!/bin/env

echo "Collect static files..."
python backend/manage.py collectstatic --noinput

gunicorn --bind 0.0.0.0:8000 backend.backend.wsgi:application --access-logfile - --error-logfile - &

# Запуск Telegram бота
cd src
python run.py

wait