import json
from decimal import Decimal

from django.test import Client, TestCase

from apps.common.authentication import generate_tokens
from apps.main.models import CustomUser


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

        # tg_user should be deleted
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
