"""Tests for Order.clean() state-machine validation (H12 audit-report.md).

Order.full_clean() (через clean()) валидирует переходы статусов
по словарю ALLOWED_TRANSITIONS из apps.orders.services. Это защищает от
прямого обхода state-machine через order.status = "..."; order.save() в
Django Admin или ad-hoc-коде.

Важно: full_clean() НЕ вызывается из save() автоматически — это намеренно,
чтобы не сломать существующий production-flow в update_order_status(),
который уже валидирует переход.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase, override_settings

from apps.main.models import CustomUser, Product
from apps.orders.models import Order, OrderItem
from apps.orders.services import update_order_status


_TEST_SETTINGS = {
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
}


@override_settings(**_TEST_SETTINGS)
class OrderCleanStateMachineTests(TestCase):
    """Order.full_clean() проверяет переходы статусов через ALLOWED_TRANSITIONS."""

    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=900001)

    def _make_order(self, status="new"):
        return Order.objects.create(
            customer=self.customer,
            address="ул. Тестовая, 1",
            phone="+79990001122",
            products_price=Decimal("100.00"),
            total_price=Decimal("100.00"),
            status=status,
        )

    def test_invalid_transition_new_to_completed_raises(self):
        """Прямой переход new → completed недопустим — должен бросать
        ValidationError при full_clean()."""
        order = self._make_order(status="new")
        order.status = "completed"

        with self.assertRaises(ValidationError) as ctx:
            order.full_clean()

        self.assertIn("status", ctx.exception.error_dict)

    def test_invalid_transition_assembly_to_arrived_raises(self):
        """assembly → arrived не входит в ALLOWED_TRANSITIONS."""
        order = self._make_order(status="assembly")
        order.status = "arrived"

        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_valid_transition_new_to_accepted_passes(self):
        """new → accepted допустим — full_clean не должен ругаться на статус."""
        order = self._make_order(status="new")
        order.status = "accepted"

        # full_clean может проверить и другие поля; нас интересует именно
        # отсутствие ошибки по полю status.
        try:
            order.full_clean()
        except ValidationError as exc:
            self.assertNotIn(
                "status",
                exc.error_dict,
                f"Допустимый переход new → accepted не должен давать "
                f"ошибку по полю status: {exc.error_dict}",
            )

    def test_valid_transition_ready_to_completed_pickup_passes(self):
        """ready → completed разрешён (самовывоз)."""
        order = self._make_order(status="ready")
        order.status = "completed"

        try:
            order.full_clean()
        except ValidationError as exc:
            self.assertNotIn("status", exc.error_dict)

    def test_no_status_change_passes(self):
        """Если статус не менялся — проверка перехода не нужна."""
        order = self._make_order(status="assembly")
        # Тот же статус — ValidationError по status не должен подниматься.
        try:
            order.full_clean()
        except ValidationError as exc:
            self.assertNotIn("status", exc.error_dict)

    def test_new_unsaved_order_does_not_check_status_transition(self):
        """Для нового Order (без pk) clean() не должен падать на проверке
        перехода (предыдущего статуса нет)."""
        order = Order(
            customer=self.customer,
            address="ул. Новая, 2",
            phone="+79990001100",
            products_price=Decimal("50.00"),
            total_price=Decimal("50.00"),
            status="new",
        )
        # Отдельно вызываем clean() — full_clean дополнительно проверит choices,
        # required-поля и т.п., нас интересует поведение именно clean().
        try:
            order.clean()
        except ValidationError as exc:
            self.assertNotIn("status", exc.error_dict)

    def test_completed_is_terminal(self):
        """completed — терминальный статус, любой переход из него запрещён."""
        order = self._make_order(status="ready")
        # Сначала переведём в completed легально через services.
        with transaction.atomic():
            update_order_status(order.id, "completed")

        order.refresh_from_db()
        self.assertEqual(order.status, "completed")

        order.status = "new"
        with self.assertRaises(ValidationError):
            order.full_clean()


@override_settings(**_TEST_SETTINGS)
class UpdateOrderStatusRegressionTests(TestCase):
    """Regression: update_order_status (production-flow) не сломался от
    добавления Order.clean(). full_clean() в save() автоматически НЕ
    вызывается, поэтому существующие callsite'ы должны работать как раньше.
    """

    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=900100)
        self.product = Product.objects.create(
            product_code="SM-1",
            name="Test Product",
            price="100.00",
            store_id=1,
            is_active=True,
        )

    def _make_order(self, status="new"):
        order = Order.objects.create(
            customer=self.customer,
            address="ул. Тестовая, 1",
            phone="+79990002233",
            products_price=Decimal("100.00"),
            total_price=Decimal("100.00"),
            status=status,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price_at_moment=Decimal("100.00"),
        )
        return order

    def test_update_order_status_valid_transition_works(self):
        order = self._make_order(status="new")
        with transaction.atomic():
            update_order_status(order.id, "accepted")
        order.refresh_from_db()
        self.assertEqual(order.status, "accepted")

    def test_update_order_status_full_chain_works(self):
        """Полная цепочка new → accepted → assembly → ready → delivery → arrived → completed
        проходит через services.update_order_status."""
        order = self._make_order(status="new")
        for next_status in (
            "accepted", "assembly", "ready", "delivery", "arrived", "completed",
        ):
            with transaction.atomic():
                update_order_status(order.id, next_status)
        order.refresh_from_db()
        self.assertEqual(order.status, "completed")

    def test_direct_save_without_full_clean_still_works(self):
        """Прямой order.save(update_fields=["status"]) после
        update_order_status НЕ должен ломаться — full_clean() не вызывается
        автоматически (это и есть «не breaking change»)."""
        order = self._make_order(status="new")
        # Эмулируем существующий callsite: явно ставим статус и сохраняем.
        # update_order_status уже валидирует, save() сам по себе проверку не запускает.
        order.status = "accepted"
        order.save(update_fields=["status"])
        order.refresh_from_db()
        self.assertEqual(order.status, "accepted")
