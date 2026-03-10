"""Tests for email-based authentication endpoints."""

import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, Client
from django.core.cache import cache

from apps.common.authentication import generate_tokens, decode_token
from apps.main.models import CustomUser


class RegisterTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_register_success(self):
        resp = self.client.post(
            "/api/auth/register/",
            data={
                "email": "test@example.com",
                "password": "securepass123",
                "full_name": "Test User",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertNotIn("tokens", data)
        self.assertEqual(data["email"], "test@example.com")

        # User should NOT be in DB yet
        self.assertFalse(CustomUser.objects.filter(email="test@example.com").exists())
        # Data should be in cache
        pending = cache.get("pending_reg:test@example.com")
        self.assertIsNotNone(pending)
        self.assertEqual(pending["full_name"], "Test User")

    def test_register_duplicate_email_returns_200(self):
        """Anti-enumeration: duplicate email returns same 200 as success."""
        CustomUser.objects.create(
            email="test@example.com",
            telegram_id=999,
            auth_method="telegram",
        )
        resp = self.client.post(
            "/api/auth/register/",
            data={
                "email": "test@example.com",
                "password": "securepass123",
                "full_name": "Test User",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_register_short_password(self):
        resp = self.client.post(
            "/api/auth/register/",
            data={
                "email": "test@example.com",
                "password": "short",
                "full_name": "Test User",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class LoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(
            email="login@example.com",
            full_name="Login User",
            auth_method="email",
        )
        self.user.set_password("correctpass123")
        self.user.save()

    def test_login_success(self):
        resp = self.client.post(
            "/api/auth/login/",
            data={"email": "login@example.com", "password": "correctpass123"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("tokens", data)
        self.assertEqual(data["user_id"], self.user.pk)

    def test_login_wrong_password(self):
        resp = self.client.post(
            "/api/auth/login/",
            data={"email": "login@example.com", "password": "wrongpass"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_nonexistent_email(self):
        resp = self.client.post(
            "/api/auth/login/",
            data={"email": "nobody@example.com", "password": "whatever"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)


class LoginQrTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(
            telegram_id=123456789,
            qr_code="/media/qr/test123",
            full_name="QR User",
            auth_method="telegram",
            bonuses=50,
        )

    def test_login_qr_success(self):
        resp = self.client.post(
            "/api/auth/login-qr/",
            data={"qr_code": "/media/qr/test123"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("tokens", data)
        self.assertIn("access", data["tokens"])
        self.assertIn("refresh", data["tokens"])
        self.assertEqual(data["user_id"], self.user.pk)
        self.assertEqual(data["customer"]["telegram_id"], 123456789)
        self.assertEqual(data["customer"]["bonus_balance"], 50.0)

    def test_login_qr_not_found(self):
        resp = self.client.post(
            "/api/auth/login-qr/",
            data={"qr_code": "nonexistent"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_qr_empty(self):
        resp = self.client.post(
            "/api/auth/login-qr/",
            data={"qr_code": ""},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class RefreshTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(
            email="refresh@example.com",
            auth_method="email",
        )
        self.tokens = generate_tokens(self.user)

    def test_refresh_success(self):
        resp = self.client.post(
            "/api/auth/refresh/",
            data={"refresh": self.tokens["refresh"]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("tokens", data)
        # New access token should be valid
        user_id = decode_token(data["tokens"]["access"])
        self.assertEqual(user_id, self.user.pk)

    def test_refresh_invalid_token(self):
        resp = self.client.post(
            "/api/auth/refresh/",
            data={"refresh": "invalid.token.here"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)


class VerifyEmailTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()
        self.user = CustomUser.objects.create(
            email="verify@example.com",
            auth_method="email",
            email_verified=False,
        )

    def test_verify_success(self):
        cache.set("email_verify:verify@example.com", "123456", timeout=600)
        resp = self.client.post(
            "/api/auth/verify-email/",
            data={"email": "verify@example.com", "code": "123456"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_verify_wrong_code(self):
        cache.set("email_verify:verify@example.com", "123456", timeout=600)
        resp = self.client.post(
            "/api/auth/verify-email/",
            data={"email": "verify@example.com", "code": "999999"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class ResetPasswordTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()
        self.user = CustomUser.objects.create(
            email="reset@example.com",
            auth_method="email",
        )
        self.user.set_password("oldpassword123")
        self.user.save()

    def test_reset_confirm_success(self):
        cache.set("pwd_reset:reset@example.com", "654321", timeout=600)
        resp = self.client.post(
            "/api/auth/reset-password/confirm/",
            data={
                "email": "reset@example.com",
                "code": "654321",
                "new_password": "newpassword123",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword123"))


class JWTPermissionTests(TestCase):
    """Test that CustomerPermission accepts JWT Bearer tokens."""

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(
            email="jwt@example.com",
            full_name="JWT User",
            auth_method="email",
        )
        self.tokens = generate_tokens(self.user)

    def test_bearer_token_grants_access(self):
        resp = self.client.get(
            f"/api/customer/{self.user.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["email"], "jwt@example.com")

    def test_no_auth_returns_error(self):
        resp = self.client.get(f"/api/customer/{self.user.pk}/")
        self.assertIn(resp.status_code, [401, 403])

    def test_invalid_token_returns_error(self):
        resp = self.client.get(
            f"/api/customer/{self.user.pk}/",
            HTTP_AUTHORIZATION="Bearer invalid.token",
        )
        self.assertIn(resp.status_code, [401, 403])


class LinkEmailTests(TestCase):
    """Test linking email to an existing Telegram account."""

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(
            telegram_id=111222333,
            full_name="Telegram User",
            auth_method="telegram",
        )

    def test_link_email_with_bearer(self):
        tokens = generate_tokens(self.user)
        resp = self.client.post(
            "/api/auth/link-email/",
            data={"email": "newemail@example.com", "password": "newpass123"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "newemail@example.com")
        self.assertTrue(self.user.check_password("newpass123"))

    def test_link_email_with_telegram_header(self):
        resp = self.client.post(
            "/api/auth/link-email/",
            data={"email": "another@example.com", "password": "newpass123"},
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID="111222333",
        )
        self.assertEqual(resp.status_code, 200)


class LinkTelegramTests(TestCase):
    """Test linking Telegram to an email account."""

    def setUp(self):
        self.client = Client()
        cache.clear()
        self.email_user = CustomUser.objects.create(
            email="emailuser@example.com",
            full_name="Email User",
            auth_method="email",
        )

    def test_request_link_code(self):
        tokens = generate_tokens(self.email_user)
        resp = self.client.post(
            "/api/auth/link-telegram/request/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("code", resp.json())

    def test_confirm_link_simple(self):
        """Link Telegram when no separate Telegram account exists."""
        cache.set("link_telegram:123456", self.email_user.pk, timeout=600)
        resp = self.client.post(
            "/api/auth/link-telegram/confirm/",
            data={"code": "123456", "telegram_id": 444555666},
            content_type="application/json",
            HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(resp.status_code, 200)
        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.telegram_id, 444555666)

    def test_confirm_link_with_merge(self):
        """Link Telegram when a separate Telegram account exists → merge."""
        tg_user = CustomUser.objects.create(
            telegram_id=777888999,
            full_name="Telegram User",
            auth_method="telegram",
            bonuses=100,
        )
        self.email_user.bonuses = 50
        self.email_user.save()

        cache.set("link_telegram:654321", self.email_user.pk, timeout=600)
        resp = self.client.post(
            "/api/auth/link-telegram/confirm/",
            data={"code": "654321", "telegram_id": 777888999},
            content_type="application/json",
            HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(resp.status_code, 200)

        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.telegram_id, 777888999)
        self.assertEqual(self.email_user.bonuses, 150)  # 50 + 100

        # Telegram account should be deleted
        self.assertFalse(CustomUser.objects.filter(pk=tg_user.pk).exists())


class RegisterFlowTests(TestCase):
    """Registration saves to cache, not DB. User created only after email verification."""

    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_register_does_not_create_user(self):
        """POST /api/auth/register/ saves to cache, no user in DB."""
        with patch("apps.accounts.email_service.send_verification_code"):
            response = self.client.post(
                "/api/auth/register/",
                data=json.dumps({
                    "email": "new@example.com",
                    "password": "securepass123",
                    "full_name": "Test User",
                }),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "new@example.com")
        self.assertNotIn("tokens", data)
        self.assertFalse(CustomUser.objects.filter(email="new@example.com").exists())
        pending = cache.get("pending_reg:new@example.com")
        self.assertIsNotNone(pending)
        self.assertEqual(pending["full_name"], "Test User")

    def test_verify_creates_user_with_tokens(self):
        """POST /api/auth/verify-email/ creates user and returns tokens."""
        cache.set("pending_reg:new@example.com", {
            "email": "new@example.com",
            "password": "securepass123",
            "full_name": "Test User",
            "phone": None,
        }, timeout=600)
        cache.set("email_verify:new@example.com", "123456", timeout=600)

        response = self.client.post(
            "/api/auth/verify-email/",
            data=json.dumps({"email": "new@example.com", "code": "123456"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tokens", data)
        self.assertIn("user_id", data)

        user = CustomUser.objects.get(email="new@example.com")
        self.assertTrue(user.email_verified)
        self.assertEqual(user.full_name, "Test User")
        self.assertTrue(user.check_password("securepass123"))
        self.assertIsNone(cache.get("pending_reg:new@example.com"))

    def test_verify_wrong_code(self):
        """Wrong verification code returns 400."""
        cache.set("pending_reg:new@example.com", {
            "email": "new@example.com",
            "password": "securepass123",
            "full_name": "Test User",
            "phone": None,
        }, timeout=600)
        cache.set("email_verify:new@example.com", "123456", timeout=600)

        response = self.client.post(
            "/api/auth/verify-email/",
            data=json.dumps({"email": "new@example.com", "code": "000000"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomUser.objects.filter(email="new@example.com").exists())

    def test_register_duplicate_email_in_db(self):
        """Anti-enumeration: duplicate email returns same 200 as success."""
        CustomUser.objects.create(email="taken@example.com", auth_method="email")
        response = self.client.post(
            "/api/auth/register/",
            data=json.dumps({
                "email": "taken@example.com",
                "password": "securepass123",
                "full_name": "Dup User",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)


class LinkTelegramByQrTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.email_user = CustomUser.objects.create(
            email="test@example.com",
            auth_method="email",
            email_verified=True,
            full_name="Email User",
        )
        self.email_user.set_password("testpass123")
        self.email_user.save()
        tokens = generate_tokens(self.email_user)
        self.auth_header = f"Bearer {tokens['access']}"

    def test_link_by_qr_success(self):
        """JWT user links telegram_id that doesn't exist yet."""
        response = self.client.post(
            "/api/auth/link-telegram/by-qr/",
            data=json.dumps({"telegram_id": 999888777}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.telegram_id, 999888777)

    def test_link_by_qr_merge(self):
        """JWT user links telegram_id that belongs to another user — merge."""
        tg_user = CustomUser.objects.create(
            telegram_id=111222333,
            full_name="TG User",
            bonuses=Decimal("100.00"),
        )
        self.email_user.bonuses = Decimal("50.00")
        self.email_user.save()

        response = self.client.post(
            "/api/auth/link-telegram/by-qr/",
            data=json.dumps({"telegram_id": 111222333}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 200)

        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.telegram_id, 111222333)
        self.assertEqual(self.email_user.bonuses, Decimal("150.00"))

        self.assertFalse(CustomUser.objects.filter(pk=tg_user.pk).exists())

    def test_link_by_qr_already_linked(self):
        """User already has telegram_id — returns 400."""
        self.email_user.telegram_id = 555666777
        self.email_user.save()

        response = self.client.post(
            "/api/auth/link-telegram/by-qr/",
            data=json.dumps({"telegram_id": 999888777}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 400)

    def test_link_by_qr_unauthenticated(self):
        """No auth header — returns 403."""
        response = self.client.post(
            "/api/auth/link-telegram/by-qr/",
            data=json.dumps({"telegram_id": 999888777}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class GenerateUserQrTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(
            email="qr@example.com",
            auth_method="email",
            email_verified=True,
        )
        tokens = generate_tokens(self.user)
        self.auth_header = f"Bearer {tokens['access']}"

    def test_generate_qr_success(self):
        """Email-only user gets QR code = str(pk)."""
        response = self.client.post(
            "/api/auth/generate-qr/",
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["qr_code"], str(self.user.pk))

        self.user.refresh_from_db()
        self.assertEqual(self.user.qr_code, str(self.user.pk))

    def test_generate_qr_already_exists(self):
        """Idempotent — returns existing QR code."""
        self.user.qr_code = "existing_qr"
        self.user.save()

        response = self.client.post(
            "/api/auth/generate-qr/",
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["qr_code"], "existing_qr")
