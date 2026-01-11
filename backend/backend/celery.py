import os
import sys
from pathlib import Path
from celery import Celery
from celery.schedules import crontab

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'send-birthday-congratulations-every-day': {
        'task': 'apps.api.tasks.send_birthday_congratulations',
        'schedule': crontab(hour=9, minute=0),
    },
}
