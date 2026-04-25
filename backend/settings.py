import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv(override=False)

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "t", "yes", "y"}


def _env_list(name: str, default=None):
    value = os.getenv(name)
    if not value:
        return [] if default is None else list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


DEBUG = _env_bool("DEBUG", False)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if any(cmd in sys.argv for cmd in {"test", "collectstatic", "check"}):
        SECRET_KEY = "test-secret-key"
    elif DEBUG:
        SECRET_KEY = "insecure-development-key"
    else:
        raise ImproperlyConfigured("SECRET_KEY environment variable must be set")

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1", "app"])
if not ALLOWED_HOSTS and not DEBUG:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be configured in production")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_object_actions',
    'django_celery_beat',
    'django_prometheus',
    'apps.common.apps.CommonConfig',
    'apps.main.apps.MainConfig',
    'apps.api.apps.ApiConfig',
    'apps.orders.apps.OrdersConfig',
    'apps.loyalty.apps.LoyaltyConfig',
    'apps.notifications.apps.NotificationsConfig',
    'apps.integrations.onec.apps.OnecConfig',
    'apps.integrations.payments.apps.PaymentsConfig',
    'apps.accounts.apps.AccountsConfig',
    'apps.bot_api.apps.BotApiConfig',
    'apps.analytics.apps.AnalyticsConfig',
    'apps.campaigns.apps.CampaignsConfig',
    'apps.rfm.apps.RfmConfig',
    'apps.showcase.apps.ShowcaseConfig',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": _env_int("DJANGO_DB_CONN_MAX_AGE", 60),
    }
}

db_options = {}
ssl_mode = os.getenv("POSTGRES_SSLMODE")
if ssl_mode:
    db_options["sslmode"] = ssl_mode
if db_options:
    DATABASES["default"]["OPTIONS"] = db_options

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

_csrf_from_env = _env_list("CSRF_TRUSTED_ORIGINS")
if _csrf_from_env:
    CSRF_TRUSTED_ORIGINS = _csrf_from_env
else:
    CSRF_TRUSTED_ORIGINS = []
    for host in ALLOWED_HOSTS:
        scheme = "http" if host in {"localhost", "127.0.0.1"} else "https"
        CSRF_TRUSTED_ORIGINS.append(f"{scheme}://{host}")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True


LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = "Asia/Yakutsk"

USE_I18N = True

USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "collected_static"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
COURIER_BOT_TOKEN = os.getenv("COURIER_BOT_TOKEN", "")
PICKER_BOT_TOKEN = os.getenv("PICKER_BOT_TOKEN", "")

GUEST_TELEGRAM_ID = _env_int("GUEST_TELEGRAM_ID", 0)

# Cache (used for email verification codes)
_cache_redis_url = os.getenv("CACHE_REDIS_URL") or os.getenv("CELERY_BROKER_URL", "")
if _cache_redis_url and _cache_redis_url.startswith("redis"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _cache_redis_url,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = 600        # hard kill after 10 min
CELERY_TASK_SOFT_TIME_LIMIT = 300   # SoftTimeLimitExceeded after 5 min
CELERY_TIMEZONE = TIME_ZONE         # crontab расписание по Asia/Yakutsk
CELERY_ENABLE_UTC = True            # внутри хранит UTC, crontab по CELERY_TIMEZONE


SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = _env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = os.getenv(
    "DJANGO_SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin"
)

SECURE_HSTS_SECONDS = _env_int(
    "DJANGO_SECURE_HSTS_SECONDS", 31536000 if not DEBUG else 0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    SECURE_HSTS_SECONDS > 0
    and _env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
)
SECURE_HSTS_PRELOAD = (
    SECURE_HSTS_SECONDS >= 31536000
    and _env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
)

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        *(
            ["rest_framework.renderers.BrowsableAPIRenderer"]
            if DEBUG
            else []
        ),
    ],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.HeaderPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "apps.common.throttling.TelegramUserThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "anon_auth": "10/min",
        "verify_code": "5/min",
        "telegram_user": "120/min",
        "product_image_upload": "30/min",
    },
}

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}

INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "")
ONEC_API_KEY = os.getenv("ONEC_API_KEY", "") or INTEGRATION_API_KEY
ONEC_ORDER_URL = os.getenv("ONEC_ORDER_URL", "")
ONEC_ORDER_COMPLETE_URL = os.getenv("ONEC_ORDER_COMPLETE_URL", "")
ONEC_BONUS_URL = os.getenv("ONEC_BONUS_URL", "")
ONEC_RFM_SYNC_URL = os.getenv("ONEC_RFM_SYNC_URL", "")
ONEC_RFM_SYNC_CHUNK_SIZE = _env_int("ONEC_RFM_SYNC_CHUNK_SIZE", 500)
ONEC_RFM_SYNC_ENABLED = _env_bool("ONEC_RFM_SYNC_ENABLED", False)

ALLOW_TELEGRAM_HEADER_AUTH = _env_bool("ALLOW_TELEGRAM_HEADER_AUTH", False)

PERSONAL_RANKING_ENABLED = _env_bool("PERSONAL_RANKING_ENABLED", False)

# Referral
REFERRAL_BASE_URL = os.getenv("REFERRAL_BASE_URL", "")  # e.g. "https://lakshmi.app"
APPSTORE_URL = os.getenv("APPSTORE_URL", "")
GOOGLE_PLAY_URL = os.getenv("GOOGLE_PLAY_URL", "")

# Email
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = _env_int("EMAIL_PORT", 587)
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "") or os.getenv("EMAIL_HOST_USER", "noreply@example.com")

# YooKassa
YUKASSA_SHOP_ID = os.getenv("YUKASSA_SHOP_ID", "")
YUKASSA_SECRET_KEY = os.getenv("YUKASSA_SECRET_KEY", "")
YUKASSA_RETURN_URL = os.getenv("YUKASSA_RETURN_URL", "")  # deeplink for return to app
YUKASSA_PAYMENT_TIMEOUT_MINUTES = _env_int("YUKASSA_PAYMENT_TIMEOUT_MINUTES", 15)


# --- Lakshmi Photo Studio (OpenAI image processing) ---
# Стилизация фото товаров через OpenAI Image API. Endpoint:
# POST /api/products/<id>/image/ (см. apps/main/views.py:ProductImageUploadView).
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PRODUCT_IMAGE_MODEL = os.getenv("PRODUCT_IMAGE_MODEL", "gpt-image-1")
PRODUCT_IMAGE_OUTPUT_SIZE = os.getenv("PRODUCT_IMAGE_OUTPUT_SIZE", "1024x1024")
PRODUCT_IMAGE_MAX_UPLOAD_SIZE = _env_int(
    "PRODUCT_IMAGE_MAX_UPLOAD_SIZE", 10 * 1024 * 1024
)
PRODUCT_IMAGE_ALLOWED_FORMATS = _env_list(
    "PRODUCT_IMAGE_ALLOWED_FORMATS", ["jpg", "jpeg", "png", "webp"]
)
PRODUCT_IMAGE_PROCESSING_TIMEOUT = _env_int("PRODUCT_IMAGE_PROCESSING_TIMEOUT", 120)
_DEFAULT_PRODUCT_IMAGE_PROMPT = (
    "Clean studio product photo for grocery delivery catalog. "
    "Place the product centered on a clean light background, preferably "
    "white or very light warm gray. Keep realistic proportions. Preserve "
    "original packaging, label, logo, colors, and readable product text "
    "as much as possible. Remove hands, people, clutter, table, "
    "background noise, and extra objects. Add soft natural shadow under "
    "the product. Use consistent lighting, sharp focus, high detail, "
    "ecommerce marketplace style. Square 1:1 composition, 1024x1024. "
    "Do not invent new labels. Do not change the product identity. "
    "No watermark."
)
# Используем "or" вместо default-аргумента os.getenv: если переменная
# задана пустой строкой (PRODUCT_IMAGE_STYLE_PROMPT= в .env), fallback
# на дефолт всё равно сработает.
PRODUCT_IMAGE_STYLE_PROMPT = (
    os.getenv("PRODUCT_IMAGE_STYLE_PROMPT") or _DEFAULT_PRODUCT_IMAGE_PROMPT
)


# --- CORS (для отдельного домена Lakshmi Photo Studio) ---
# По умолчанию выключен; включается заданием CORS_ALLOWED_ORIGINS в env.
# Используется django-cors-headers, добавлен в INSTALLED_APPS/MIDDLEWARE
# только если список не пуст, чтобы не менять поведение существующих
# endpoints без явной настройки.
CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS")
if CORS_ALLOWED_ORIGINS:
    if "corsheaders" not in INSTALLED_APPS:
        INSTALLED_APPS.append("corsheaders")
    if "corsheaders.middleware.CorsMiddleware" not in MIDDLEWARE:
        # CorsMiddleware должен идти как можно выше — сразу после
        # PrometheusBeforeMiddleware и SecurityMiddleware.
        MIDDLEWARE.insert(2, "corsheaders.middleware.CorsMiddleware")
    CORS_ALLOW_CREDENTIALS = False
    CORS_ALLOW_HEADERS = (
        "accept",
        "accept-encoding",
        "authorization",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
        "x-api-key",
    )
