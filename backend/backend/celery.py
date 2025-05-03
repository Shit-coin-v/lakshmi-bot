import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.backend.settings')

app = Celery('backend')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'send-birthday-congratulations-every-day': {
        'task': 'api.tasks.send_birthday_congratulations',
        'schedule': crontab(hour=9, minute=0),
    },
}
