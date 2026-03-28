import json
from decimal import Decimal

from django.test import Client, TestCase
from django.utils import timezone

from apps.api.models import OneCClientMap
from apps.common import permissions, security
from apps.main.models import (
    BotActivity,
    BroadcastMessage,
    CustomUser,
    NewsletterDelivery,
    NewsletterOpenEvent,
    Product,
)
from apps.notifications.models import CourierNotificationMessage
from apps.orders.models import Order, OrderItem


def _api_key_header():
    return {"HTTP_X_API_KEY": "test-key"}


class BotApiAuthTests(TestCase):
    """All bot_api endpoints require ApiKeyPermission."""

    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()
        self.user = CustomUser.objects.create(telegram_id=100001)

    def test_no_api_key_returns_403(self):
        urls = [
            "/api/bot/users/by-telegram-id/100001/",
            "/api/bot/orders/active/",
            "/api/bot/orders/completed-today/?courier_tg_id=1",
            "/api/bot/courier-messages/?courier_tg_id=1",
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 403, f"Expected 403 for {url}, got {resp.status_code}")

    def test_wrong_api_key_returns_403(self):
        resp = self.client.get(
            "/api/bot/users/by-telegram-id/100001/",
            HTTP_X_API_KEY="wrong-key",
        )
        self.assertEqual(resp.status_code, 403)


# --- Customer Bot endpoints ---


class UserByTelegramIdTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()
        self.user = CustomUser.objects.create(
            telegram_id=200001,
            first_name="Ivan",
            bonuses=Decimal("42.50"),
            qr_code="test-qr",
        )

    def test_get_existing_user(self):
        resp = self.client.get(
            "/api/bot/users/by-telegram-id/200001/",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["telegram_id"], 200001)
        self.assertEqual(data["first_name"], "Ivan")
        self.assertEqual(data["bonuses"], "42.50")
        self.assertEqual(data["qr_code"], "test-qr")

    def test_user_not_found_returns_404(self):
        resp = self.client.get(
            "/api/bot/users/by-telegram-id/999999/",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 404)


class UserRegisterTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()

    def test_register_new_user(self):
        payload = {
            "telegram_id": 300001,
            "first_name": "Test",
            "last_name": "User",
            "qr_code": "generated-qr",
            "personal_data_consent": True,
        }
        resp = self.client.post(
            "/api/bot/users/register/",
            data=json.dumps(payload),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["telegram_id"], 300001)
        self.assertEqual(data["qr_code"], "generated-qr")
        self.assertEqual(data["auth_method"], "telegram")
        self.assertTrue(CustomUser.objects.filter(telegram_id=300001).exists())

    def test_register_with_referrer(self):
        referrer = CustomUser.objects.create(telegram_id=300000)
        payload = {
            "telegram_id": 300002,
            "first_name": "Ref",
            "referrer_id": 300000,
        }
        resp = self.client.post(
            "/api/bot/users/register/",
            data=json.dumps(payload),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 201)
        user = CustomUser.objects.get(telegram_id=300002)
        # After FK migration: referrer_id stores PK, not telegram_id
        self.assertEqual(user.referrer_id, referrer.pk)
        self.assertEqual(user.referrer.telegram_id, 300000)

    def test_register_duplicate_telegram_id_returns_400(self):
        CustomUser.objects.create(telegram_id=300003)
        payload = {"telegram_id": 300003, "first_name": "Dup"}
        resp = self.client.post(
            "/api/bot/users/register/",
            data=json.dumps(payload),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 400)


class UserPatchTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()
        self.user = CustomUser.objects.create(telegram_id=400001, bonuses=Decimal("0"))

    def test_patch_qr_code(self):
        resp = self.client.patch(
            f"/api/bot/users/{self.user.pk}/",
            data=json.dumps({"qr_code": "new-qr-value"}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.qr_code, "new-qr-value")

    def test_patch_bonuses(self):
        resp = self.client.patch(
            f"/api/bot/users/{self.user.pk}/",
            data=json.dumps({"bonuses": "123.45"}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bonuses, Decimal("123.45"))

    def test_patch_nonexistent_user_returns_404(self):
        resp = self.client.patch(
            "/api/bot/users/999999/",
            data=json.dumps({"bonuses": "1"}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 404)


class BotActivityTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()
        self.user = CustomUser.objects.create(telegram_id=500001)

    def test_create_activity(self):
        resp = self.client.post(
            "/api/bot/activities/",
            data=json.dumps({"telegram_id": 500001, "action": "show_qr"}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["action"], "show_qr")
        self.assertEqual(BotActivity.objects.filter(customer=self.user).count(), 1)

    def test_activity_user_not_found(self):
        resp = self.client.post(
            "/api/bot/activities/",
            data=json.dumps({"telegram_id": 999999, "action": "show_qr"}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 400)


class NewsletterOpenTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()
        self.user = CustomUser.objects.create(telegram_id=600001)
        self.message = BroadcastMessage.objects.create(message_text="Test broadcast")
        self.delivery = NewsletterDelivery.objects.create(
            message=self.message,
            customer=self.user,
            open_token="a" * 32,
        )

    def test_open_newsletter(self):
        resp = self.client.post(
            "/api/bot/newsletter/open/",
            data=json.dumps({
                "token": "a" * 32,
                "telegram_user_id": 600001,
                "raw_callback_data": "open:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            }),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["newly_opened"])
        self.assertEqual(data["message_text"], "Test broadcast")
        self.delivery.refresh_from_db()
        self.assertIsNotNone(self.delivery.opened_at)
        self.assertEqual(NewsletterOpenEvent.objects.filter(delivery=self.delivery).count(), 1)

    def test_double_open_is_idempotent(self):
        # First open
        self.client.post(
            "/api/bot/newsletter/open/",
            data=json.dumps({"token": "a" * 32, "telegram_user_id": 600001}),
            content_type="application/json",
            **_api_key_header(),
        )
        # Second open
        resp = self.client.post(
            "/api/bot/newsletter/open/",
            data=json.dumps({"token": "a" * 32, "telegram_user_id": 600001}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["newly_opened"])
        self.assertEqual(NewsletterOpenEvent.objects.filter(delivery=self.delivery).count(), 1)

    def test_invalid_token_returns_404(self):
        resp = self.client.post(
            "/api/bot/newsletter/open/",
            data=json.dumps({"token": "nonexistent", "telegram_user_id": 600001}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 404)


class OneCMapUpsertTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()
        self.user = CustomUser.objects.create(telegram_id=700001)

    def test_create_mapping(self):
        resp = self.client.post(
            "/api/bot/onec-map/upsert/",
            data=json.dumps({"user_id": self.user.pk, "one_c_guid": "guid-123"}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["created"])
        self.assertEqual(data["one_c_guid"], "guid-123")

    def test_update_existing_mapping(self):
        OneCClientMap.objects.create(user=self.user, one_c_guid="old-guid")
        resp = self.client.post(
            "/api/bot/onec-map/upsert/",
            data=json.dumps({"user_id": self.user.pk, "one_c_guid": "new-guid"}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["created"])
        self.assertEqual(OneCClientMap.objects.get(user=self.user).one_c_guid, "new-guid")

    def test_nonexistent_user_returns_404(self):
        resp = self.client.post(
            "/api/bot/onec-map/upsert/",
            data=json.dumps({"user_id": 999999, "one_c_guid": "guid"}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 404)


# --- Courier Bot endpoints ---


class ActiveOrdersTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=800001)

    def test_list_active_orders(self):
        Order.objects.create(customer=self.customer, status="ready", address="A", phone="1")
        Order.objects.create(customer=self.customer, status="delivery", address="B", phone="2")
        Order.objects.create(customer=self.customer, status="completed", address="C", phone="3")
        Order.objects.create(customer=self.customer, status="new", address="D", phone="4")

        resp = self.client.get("/api/bot/orders/active/", **_api_key_header())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)  # ready + delivery
        statuses = {o["status"] for o in data}
        self.assertEqual(statuses, {"ready", "delivery"})

    def test_empty_list(self):
        resp = self.client.get("/api/bot/orders/active/", **_api_key_header())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


class BotOrderDetailTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=810001)
        self.product = Product.objects.create(
            product_code="BOT-1", name="Test Product", price=Decimal("100.00"), store_id=1,
        )
        self.order = Order.objects.create(
            customer=self.customer,
            status="ready",
            address="Test St",
            phone="+79001112233",
            total_price=Decimal("250.00"),
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price_at_moment=Decimal("100.00"),
        )

    def test_get_order_with_items(self):
        resp = self.client.get(
            f"/api/bot/orders/{self.order.pk}/detail/",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], self.order.pk)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["product_name"], "Test Product")
        self.assertEqual(data["items"][0]["quantity"], 2)

    def test_order_not_found(self):
        resp = self.client.get("/api/bot/orders/999999/detail/", **_api_key_header())
        self.assertEqual(resp.status_code, 404)


class CompletedTodayTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=820001)
        self.courier_tg_id = 555

    def test_completed_count(self):
        now = timezone.now()
        Order.objects.create(
            customer=self.customer, status="completed",
            delivered_by=self.courier_tg_id, completed_at=now,
            address="A", phone="1",
            delivery_price="150.00",
        )
        Order.objects.create(
            customer=self.customer, status="completed",
            delivered_by=self.courier_tg_id, completed_at=now,
            address="B", phone="2",
            delivery_price="150.00",
        )
        # Different courier
        Order.objects.create(
            customer=self.customer, status="completed",
            delivered_by=999, completed_at=now,
            address="C", phone="3",
            delivery_price="100.00",
        )

        resp = self.client.get(
            f"/api/bot/orders/completed-today/?courier_tg_id={self.courier_tg_id}",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total"], "300.00")

    def test_missing_param_returns_400(self):
        resp = self.client.get("/api/bot/orders/completed-today/", **_api_key_header())
        self.assertEqual(resp.status_code, 400)

    def test_zero_completed(self):
        resp = self.client.get(
            f"/api/bot/orders/completed-today/?courier_tg_id={self.courier_tg_id}",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)


class CourierMessageTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()

    def test_list_messages(self):
        CourierNotificationMessage.objects.create(courier_tg_id=111, telegram_message_id=1001)
        CourierNotificationMessage.objects.create(courier_tg_id=111, telegram_message_id=1002)
        CourierNotificationMessage.objects.create(courier_tg_id=222, telegram_message_id=2001)

        resp = self.client.get(
            "/api/bot/courier-messages/?courier_tg_id=111",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_list_without_param_returns_empty(self):
        resp = self.client.get("/api/bot/courier-messages/", **_api_key_header())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_delete_message(self):
        msg = CourierNotificationMessage.objects.create(courier_tg_id=111, telegram_message_id=1001)
        resp = self.client.delete(
            f"/api/bot/courier-messages/{msg.pk}/",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(CourierNotificationMessage.objects.filter(pk=msg.pk).exists())

    def test_delete_nonexistent_returns_404(self):
        resp = self.client.delete("/api/bot/courier-messages/99999/", **_api_key_header())
        self.assertEqual(resp.status_code, 404)

    def test_bulk_delete(self):
        m1 = CourierNotificationMessage.objects.create(courier_tg_id=111, telegram_message_id=1001)
        m2 = CourierNotificationMessage.objects.create(courier_tg_id=111, telegram_message_id=1002)
        m3 = CourierNotificationMessage.objects.create(courier_tg_id=222, telegram_message_id=2001)

        resp = self.client.post(
            "/api/bot/courier-messages/bulk-delete/",
            data=json.dumps({"ids": [m1.pk, m2.pk]}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["deleted"], 2)
        self.assertTrue(CourierNotificationMessage.objects.filter(pk=m3.pk).exists())

    def test_bulk_delete_empty_list_returns_400(self):
        resp = self.client.post(
            "/api/bot/courier-messages/bulk-delete/",
            data=json.dumps({"ids": []}),
            content_type="application/json",
            **_api_key_header(),
        )
        self.assertEqual(resp.status_code, 400)
