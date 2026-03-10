import os
import sys

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"

    def ready(self):
        from django.conf import settings

        # Skip validation for management commands that don't serve traffic
        _skip_cmds = {"test", "collectstatic", "check", "migrate", "makemigrations"}
        if any(cmd in sys.argv for cmd in _skip_cmds):
            return

        if getattr(settings, "DEBUG", False):
            return

        # 1. ALLOW_TELEGRAM_HEADER_AUTH must be off in production
        if getattr(settings, "ALLOW_TELEGRAM_HEADER_AUTH", False):
            raise ImproperlyConfigured(
                "ALLOW_TELEGRAM_HEADER_AUTH=True is not allowed in production "
                "(DEBUG=False). Customer API must use JWT Bearer tokens."
            )

        # 2. ONEC_ALLOW_IPS must be configured in production
        onec_ips = os.getenv("ONEC_ALLOW_IPS", "")
        if not onec_ips.strip():
            raise ImproperlyConfigured(
                "ONEC_ALLOW_IPS must be set in production (DEBUG=False). "
                "All 1C requests will be denied without an IP whitelist."
            )

        # 3. ONEC_API_KEY must be strong enough
        onec_key = getattr(settings, "ONEC_API_KEY", "")
        if not onec_key or len(onec_key) < 16:
            raise ImproperlyConfigured(
                "ONEC_API_KEY (or INTEGRATION_API_KEY) must be set and at least "
                "16 characters in production (DEBUG=False)."
            )
