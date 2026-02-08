from settings import *  # noqa: F401, F403
import os

# Override Celery env vars so the broker/backend don't try to connect to Redis
os.environ['CELERY_BROKER_URL'] = 'memory://'
os.environ.pop('CELERY_RESULT_BACKEND', None)

SECRET_KEY = 'test'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

USE_TZ = False
APPEND_SLASH = False
SECURE_SSL_REDIRECT = False

CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'disabled://'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

REST_FRAMEWORK = {
    **globals().get("REST_FRAMEWORK", {}),
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}
