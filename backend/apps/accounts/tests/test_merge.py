"""Tests for account merge logic."""

from decimal import Decimal

from django.test import TestCase

from apps.main.models import CustomUser
from apps.orders.models import Order
from apps.notifications.models import Notification
from apps.accounts.merge import merge_accounts


class MergeAccountsTests(TestCase):
    def setUp(self):
        self.email_user = CustomUser.objects.create(
            email="user@example.com",
            full_name="Email User",
            bonuses=Decimal("100.00"),
            total_spent=Decimal("500.00"),
            purchase_count=5,
        )
        self.tg_user = CustomUser.objects.create(
            telegram_id=12345,
            full_name="TG User",
            phone="+79001112233",
            bonuses=Decimal("50.00"),
            total_spent=Decimal("200.00"),
            purchase_count=3,
        )

    def test_merge_transfers_telegram_id(self):
        merge_accounts(keep=self.email_user, remove=self.tg_user)
        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.telegram_id, 12345)

    def test_merge_sums_bonuses(self):
        merge_accounts(keep=self.email_user, remove=self.tg_user)
        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.bonuses, Decimal("150.00"))

    def test_merge_sums_total_spent(self):
        merge_accounts(keep=self.email_user, remove=self.tg_user)
        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.total_spent, Decimal("700.00"))
        self.assertEqual(self.email_user.purchase_count, 8)

    def test_merge_transfers_orders(self):
        order = Order.objects.create(
            customer=self.tg_user,
            address="Test",
            phone="+79001112233",
            total_price=Decimal("100.00"),
        )
        merge_accounts(keep=self.email_user, remove=self.tg_user)
        order.refresh_from_db()
        self.assertEqual(order.customer_id, self.email_user.pk)

    def test_merge_transfers_notifications(self):
        notif = Notification.objects.create(
            user=self.tg_user,
            title="Test",
            body="body",
        )
        merge_accounts(keep=self.email_user, remove=self.tg_user)
        notif.refresh_from_db()
        self.assertEqual(notif.user_id, self.email_user.pk)

    def test_merge_deletes_remove_account(self):
        remove_pk = self.tg_user.pk
        merge_accounts(keep=self.email_user, remove=self.tg_user)
        self.assertFalse(CustomUser.objects.filter(pk=remove_pk).exists())

    def test_merge_fills_missing_phone(self):
        merge_accounts(keep=self.email_user, remove=self.tg_user)
        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.phone, "+79001112233")

    def test_merge_keeps_existing_phone(self):
        self.email_user.phone = "+79009998877"
        self.email_user.save(update_fields=["phone"])
        merge_accounts(keep=self.email_user, remove=self.tg_user)
        self.email_user.refresh_from_db()
        self.assertEqual(self.email_user.phone, "+79009998877")
