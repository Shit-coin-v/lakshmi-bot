import os
import sys
from pathlib import Path
from celery import Celery
from celery.schedules import crontab

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

app = Celery('lakshmi')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'send-birthday-congratulations-every-day': {
        'task': 'apps.notifications.tasks.send_birthday_congratulations',
        'schedule': crontab(hour=9, minute=0),
    },
    'redispatch-unassigned-orders': {
        'task': 'apps.notifications.tasks.redispatch_unassigned_orders',
        'schedule': 120.0,  # every 2 minutes
    },
    'expire-pending-payments': {
        'task': 'apps.integrations.payments.tasks.expire_pending_payments',
        'schedule': 300.0,  # every 5 minutes
    },
    'rollback-stuck-assembly-orders': {
        'task': 'apps.integrations.onec.tasks.rollback_stuck_assembly_orders',
        'schedule': 300.0,  # every 5 minutes
    },
    'calculate-showcase-rankings': {
        'task': 'apps.showcase.tasks.calculate_showcase_rankings',
        'schedule': crontab(hour=4, minute=0),  # 04:00 по CELERY_TIMEZONE (Asia/Yakutsk)
    },
    'calculate-personal-rankings': {
        'task': 'apps.showcase.tasks.calculate_personal_rankings_task',
        'schedule': crontab(hour=4, minute=30),  # 04:30, после глобального расчёта
    },
}
