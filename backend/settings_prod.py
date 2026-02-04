"""Production settings — import base settings and apply production overrides."""

from settings import *  # noqa: F401, F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
