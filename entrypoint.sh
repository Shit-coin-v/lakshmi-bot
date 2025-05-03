#!/bin/env

echo "Collect static files..."
cd backend
python manage.py collectstatic --noinput

# Запуск Telegram бота
cd ../src
python run.py

gunicorn --bind 0.0.0.0:8000 backend.backend.wsgi:application --access-logfile - --error-logfile -

exec "$@"
