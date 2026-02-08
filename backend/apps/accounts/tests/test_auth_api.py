"""Tests for email-based authentication endpoints."""

from django.test import TestCase, Client
from django.core.cache import cache

from apps.common import security
from apps.common.permissions import API_KEY as PERM_API_KEY
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
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("tokens", data)
        self.assertIn("access", data["tokens"])
        self.assertIn("refresh", data["tokens"])
        self.assertEqual(data["email"], "test@example.com")

        user = CustomUser.objects.get(email="test@example.com")
        self.assertEqual(user.auth_method, "email")
        self.assertFalse(user.email_verified)
        self.assertIsNone(user.telegram_id)
        self.assertTrue(user.check_password("securepass123"))

    def test_register_duplicate_email(self):
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
        self.assertEqual(resp.status_code, 409)

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
        cache.set(f"link_telegram:123456", self.email_user.pk, timeout=600)
        resp = self.client.post(
            "/api/auth/link-telegram/confirm/",
            data={"code": "123456", "telegram_id": 444555666},
            content_type="application/json",
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

        cache.set(f"link_telegram:654321", self.email_user.pk, timeout=600)
        resp = self.client.post(
            "/api/auth/link-telegram/confirm/",
            data={"code": "654321", "telegram_id": 777888999},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.telegram_id, 777888999)
        self.assertEqual(self.email_user.bonuses, 150)  # 50 + 100

        # Telegram account should be deleted
        self.assertFalse(CustomUser.objects.filter(pk=tg_user.pk).exists())
