import os

# Set ONEC_ALLOW_IPS before importing settings (module-level constant in security.py)
os.environ['ONEC_ALLOW_IPS'] = '127.0.0.1,::1'

from settings import *  # noqa: F401, F403

# Override Celery env vars so the broker/backend don't try to connect to Redis
os.environ['CELERY_BROKER_URL'] = 'memory://'
os.environ.pop('CELERY_RESULT_BACKEND', None)

SECRET_KEY = 'test'
ONEC_API_KEY = "test-key"
INTEGRATION_API_KEY = "test-key"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

USE_TZ = False
APPEND_SLASH = False
SECURE_SSL_REDIRECT = False
ALLOW_TELEGRAM_HEADER_AUTH = True

CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'disabled://'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

REST_FRAMEWORK = {
    **globals().get("REST_FRAMEWORK", {}),
    "DEFAULT_THROTTLE_CLASSES": [],
    # Keep rates for view-level throttle_classes (AnonAuthThrottle, VerifyCodeThrottle)
    "DEFAULT_THROTTLE_RATES": {
        "anon": "1000/min",
        "anon_auth": "1000/min",
        "verify_code": "1000/min",
        "qr_login": "1000/min",
        "telegram_user": "1000/min",
        "product_image_upload": "1000/min",
    },
}
