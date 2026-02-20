# Settings override for running tests outside Docker (SQLite).
# Usage: python backend/manage.py test --settings=test_settings ...

from settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Celery: run tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable password validators for speed
AUTH_PASSWORD_VALIDATORS = []

# Use in-memory cache instead of Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
