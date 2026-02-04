from settings import *  # noqa: F401, F403

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

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
