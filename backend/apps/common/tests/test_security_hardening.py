"""Tests for security hardening changes."""

from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, TestCase, override_settings

from apps.common.authentication import generate_tokens
from apps.common.permissions import CustomerPermission
from apps.common.security import _ip_allowed
from apps.main.models import CustomUser


class CustomerPermissionFallbackTests(TestCase):
    """X-Telegram-User-Id header fallback must be behind feature flag."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUser.objects.create(
            telegram_id=90001,
            full_name="Fallback User",
        )
        self.permission = CustomerPermission()

    @override_settings(ALLOW_TELEGRAM_HEADER_AUTH=False)
    def test_header_fallback_denied_when_flag_off(self):
        request = self.factory.get("/", HTTP_X_TELEGRAM_USER_ID="90001")
        self.assertFalse(self.permission.has_permission(request, None))

    @override_settings(ALLOW_TELEGRAM_HEADER_AUTH=True)
    def test_header_fallback_allowed_when_flag_on(self):
        request = self.factory.get("/", HTTP_X_TELEGRAM_USER_ID="90001")
        self.assertTrue(self.permission.has_permission(request, None))
        self.assertEqual(request.telegram_user, self.user)

    @override_settings(ALLOW_TELEGRAM_HEADER_AUTH=False)
    def test_jwt_works_regardless_of_flag(self):
        tokens = generate_tokens(self.user)
        request = self.factory.get(
            "/", HTTP_AUTHORIZATION=f"Bearer {tokens['access']}"
        )
        self.assertTrue(self.permission.has_permission(request, None))
        self.assertEqual(request.telegram_user, self.user)


class CustomerPermissionIntegrationTests(TestCase):
    """Integration test: full HTTP through Django test client."""

    def setUp(self):
        self.user = CustomUser.objects.create(
            telegram_id=90002,
            full_name="Integration User",
        )

    @override_settings(ALLOW_TELEGRAM_HEADER_AUTH=False)
    def test_api_denies_header_fallback(self):
        resp = self.client.get(
            f"/api/customer/{self.user.pk}/",
            HTTP_X_TELEGRAM_USER_ID="90002",
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(ALLOW_TELEGRAM_HEADER_AUTH=True)
    def test_api_allows_header_fallback_when_enabled(self):
        resp = self.client.get(
            f"/api/customer/{self.user.pk}/",
            HTTP_X_TELEGRAM_USER_ID="90002",
        )
        self.assertEqual(resp.status_code, 200)


class LinkTelegramConfirmPermissionTests(TestCase):
    """link-telegram/confirm must require X-Api-Key."""

    def setUp(self):
        cache.clear()
        self.email_user = CustomUser.objects.create(
            email="linktest@example.com",
            full_name="Link Test",
            auth_method="email",
        )
        cache.set("link_telegram:999999", self.email_user.pk, timeout=600)

    def test_no_api_key_returns_403(self):
        resp = self.client.post(
            "/api/auth/link-telegram/confirm/",
            data={"code": "999999", "telegram_id": 111222},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_with_api_key_works(self):
        resp = self.client.post(
            "/api/auth/link-telegram/confirm/",
            data={"code": "999999", "telegram_id": 111222},
            content_type="application/json",
            HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(resp.status_code, 200)
        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.telegram_id, 111222)


class IPAllowedProductionTests(TestCase):
    """Empty IP whitelist must deny in production (DEBUG=False)."""

    def setUp(self):
        self.factory = RequestFactory()

    @patch("apps.common.security._ALLOWED_IPS", ())
    @patch("django.conf.settings.DEBUG", False)
    def test_empty_whitelist_denies_in_production(self):
        request = self.factory.get("/", REMOTE_ADDR="1.2.3.4")
        self.assertFalse(_ip_allowed(request))

    @patch("apps.common.security._ALLOWED_IPS", ())
    @patch("django.conf.settings.DEBUG", True)
    def test_empty_whitelist_allows_in_debug(self):
        request = self.factory.get("/", REMOTE_ADDR="1.2.3.4")
        self.assertTrue(_ip_allowed(request))


class ConfigValidationTests(TestCase):
    """Production config validation in CommonConfig.ready()."""

    def _run_ready(self, **setting_overrides):
        """Run CommonConfig.ready() with patched settings and sys.argv."""
        from apps.common.apps import CommonConfig

        app = CommonConfig("apps.common", __import__("apps.common"))
        with patch("sys.argv", ["gunicorn"]):
            with self.settings(**setting_overrides):
                app.ready()

    def test_rejects_header_auth_in_production(self):
        with self.assertRaises(ImproperlyConfigured):
            self._run_ready(
                DEBUG=False,
                ALLOW_TELEGRAM_HEADER_AUTH=True,
                ONEC_API_KEY="strong-key-at-least-16",
            )

    @patch.dict("os.environ", {"ONEC_ALLOW_IPS": ""})
    def test_rejects_empty_onec_ips_in_production(self):
        with self.assertRaises(ImproperlyConfigured):
            self._run_ready(
                DEBUG=False,
                ALLOW_TELEGRAM_HEADER_AUTH=False,
                ONEC_API_KEY="strong-key-at-least-16",
            )

    @patch.dict("os.environ", {"ONEC_ALLOW_IPS": "10.0.0.1"})
    def test_rejects_weak_onec_key_in_production(self):
        with self.assertRaises(ImproperlyConfigured):
            self._run_ready(
                DEBUG=False,
                ALLOW_TELEGRAM_HEADER_AUTH=False,
                ONEC_API_KEY="short",
            )

    @patch.dict("os.environ", {"ONEC_ALLOW_IPS": "10.0.0.1"})
    def test_passes_with_valid_production_config(self):
        self._run_ready(
            DEBUG=False,
            ALLOW_TELEGRAM_HEADER_AUTH=False,
            ONEC_API_KEY="strong-key-at-least-16",
        )

    def test_skips_validation_in_debug(self):
        self._run_ready(
            DEBUG=True,
            ALLOW_TELEGRAM_HEADER_AUTH=True,
            ONEC_API_KEY="",
        )
