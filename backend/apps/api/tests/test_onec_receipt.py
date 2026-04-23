import json
from decimal import Decimal

from django.conf import settings

from apps.common import security
from apps.loyalty.models import CustomUser, Transaction
from .base import OneCTestBase


class OneCReceiptTests(OneCTestBase):
    def setUp(self):
        super().setUp()
        CustomUser.objects.update_or_create(
            telegram_id=settings.GUEST_TELEGRAM_ID,
            defaults={"full_name": "Гость"},
        )

    def _post_receipt(self, payload: dict, *, api_key: str | None = None, idem: str):
        body = json.dumps(payload).encode()
        headers = {
            "HTTP_X_IDEMPOTENCY_KEY": idem,
        }
        if api_key is not None:
            headers["HTTP_X_API_KEY"] = api_key
        return self.client.post(
            "/onec/receipt",
            data=body,
            content_type="application/json",
            follow=True,
            **headers,
        )

    def _base_payload(self) -> dict:
        return {
            "receipt_guid": "R-123",
            "datetime": "2025-03-10T12:30:00+00:00",
            "store_id": "77",
            "customer": {"card_id": "LC-000099"},  # placeholder, override in each test
            "positions": [
                {
                    "product_code": "SKU-1",
                    "quantity": "1",
                    "price": "100.00",
                    "line_number": 1,
                    "bonus_earned": "1.00",
                }
            ],
            "totals": {
                "total_amount": "100.00",
                "discount_total": "0",
                "bonus_spent": "0",
                "bonus_earned": "1.00",
            },
        }

    def test_valid_receipt_returns_201(self):
        payload = self._base_payload()
        user = CustomUser.objects.create(telegram_id=9001)
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000001",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["created_count"], 1)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_receipt_without_position_bonus_allocates_totals(self):
        payload = self._base_payload()
        payload["positions"][0].pop("bonus_earned")
        payload["totals"]["bonus_earned"] = "6.00"

        user = CustomUser.objects.create(telegram_id=9001, bonuses=Decimal("0"))
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000011",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["created_count"], 1)

        tx = Transaction.objects.get()
        self.assertEqual(tx.receipt_bonus_earned, Decimal("6.00"))
        self.assertEqual(tx.bonus_earned, Decimal("6.00"))

        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("6.00"))

    def test_mixed_position_bonuses_allocate_remaining_bonus(self):
        payload = self._base_payload()
        payload["receipt_guid"] = "R-MIXED"
        payload["positions"].append(
            {
                "product_code": "SKU-2",
                "quantity": "1",
                "price": "200.00",
                "line_number": 2,
            }
        )
        payload["positions"][0]["bonus_earned"] = "1.00"
        payload["totals"]["bonus_earned"] = "3.00"

        user = CustomUser.objects.create(telegram_id=9001, bonuses=Decimal("0"))
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000012",
        )

        self.assertEqual(response.status_code, 201)

        tx_first = Transaction.objects.get(receipt_line=1)
        tx_second = Transaction.objects.get(receipt_line=2)
        self.assertEqual(tx_first.receipt_bonus_earned, Decimal("1.00"))
        self.assertEqual(tx_second.receipt_bonus_earned, Decimal("2.00"))

        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("3.00"))

    def test_multiple_positions_without_bonuses_are_distributed(self):
        payload = self._base_payload()
        payload["receipt_guid"] = "R-DIST"
        payload["positions"] = [
            {
                "product_code": "SKU-1",
                "quantity": "1",
                "price": "33.33",
                "line_number": 1,
            },
            {
                "product_code": "SKU-2",
                "quantity": "1",
                "price": "33.33",
                "line_number": 2,
            },
            {
                "product_code": "SKU-3",
                "quantity": "1",
                "price": "33.34",
                "line_number": 3,
            },
        ]
        payload["totals"] = {
            "total_amount": "100.00",
            "discount_total": "0.00",
            "bonus_spent": "0.00",
            "bonus_earned": "10.00",
        }

        user = CustomUser.objects.create(telegram_id=9001, bonuses=Decimal("0"))
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000013",
        )

        self.assertEqual(response.status_code, 201)

        bonuses = {
            tx.receipt_line: tx.receipt_bonus_earned
            for tx in Transaction.objects.filter(receipt_guid="R-DIST")
        }
        self.assertEqual(bonuses[1], Decimal("3.33"))
        self.assertEqual(bonuses[2], Decimal("3.33"))
        self.assertEqual(bonuses[3], Decimal("3.34"))

        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("10.00"))

    def test_bonus_accrual_happens_once(self):
        payload = self._base_payload()
        user = CustomUser.objects.create(telegram_id=9001, bonuses=Decimal("0"))
        payload["customer"] = {"card_id": user.card_id}

        first_response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000101",
        )
        self.assertEqual(first_response.status_code, 201)
        first_data = first_response.json()
        self.assertEqual(first_data["status"], "ok")

        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("1.00"))

        tx = Transaction.objects.get()
        self.assertEqual(tx.receipt_bonus_earned, Decimal("1.00"))
        self.assertEqual(tx.bonus_earned, Decimal("1.00"))

        second_response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000101",
        )
        self.assertEqual(second_response.status_code, 200)
        second_data = second_response.json()
        self.assertEqual(second_data["status"], "already exists")
        self.assertEqual(Transaction.objects.count(), 1)

        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("1.00"))

    def test_excess_position_bonus_logs_warning_and_accepts_receipt(self):
        payload = self._base_payload()
        payload["receipt_guid"] = "R-OVER"
        payload["positions"] = [
            {
                "product_code": "SKU-1",
                "quantity": "1",
                "price": "100.00",
                "line_number": 1,
                "bonus_earned": "4.00",
            },
            {
                "product_code": "SKU-2",
                "quantity": "1",
                "price": "100.00",
                "line_number": 2,
                "bonus_earned": "4.00",
            },
            {
                "product_code": "SKU-3",
                "quantity": "1",
                "price": "100.00",
                "line_number": 3,
                "bonus_earned": "4.00",
            },
        ]
        payload["totals"]["bonus_earned"] = "10.00"

        user = CustomUser.objects.create(telegram_id=9001, bonuses=Decimal("0"))
        payload["customer"] = {"card_id": user.card_id}

        with self.assertLogs("apps.integrations.onec.receipt", level="WARNING") as cm:
            response = self._post_receipt(
                payload,
                api_key=security.API_KEY,
                idem="00000000-0000-0000-0000-000000000015",
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            any(
                "positional bonuses exceed totals" in message
                for message in cm.output
            )
        )

        bonuses = {
            tx.receipt_line: tx.receipt_bonus_earned
            for tx in Transaction.objects.filter(receipt_guid="R-OVER")
        }
        self.assertEqual(sum(bonuses.values()), Decimal("12.00"))

        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("12.00"))

    def test_partial_delivery_accrues_only_new_positions(self):
        base_payload = self._base_payload()
        base_payload["receipt_guid"] = "R-PARTIAL"
        base_payload["positions"].append(
            {
                "product_code": "SKU-2",
                "quantity": "1",
                "price": "50.00",
                "line_number": 2,
                "bonus_earned": "1.00",
            }
        )
        base_payload["totals"]["total_amount"] = "150.00"
        base_payload["totals"]["bonus_earned"] = "2.00"

        user = CustomUser.objects.create(telegram_id=9001, bonuses=Decimal("0"))
        base_payload["customer"] = {"card_id": user.card_id}

        first_resp = self._post_receipt(
            base_payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000201",
        )
        self.assertEqual(first_resp.status_code, 201)

        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("2.00"))

        follow_payload = {
            **base_payload,
            "positions": [
                {
                    "product_code": "SKU-3",
                    "quantity": "1",
                    "price": "60.00",
                    "line_number": 3,
                    "bonus_earned": "1.00",
                },
            ],
        }
        follow_payload["totals"] = {
            "total_amount": "60.00",
            "discount_total": "0",
            "bonus_spent": "0",
            "bonus_earned": "1.00",
        }

        second_resp = self._post_receipt(
            follow_payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000202",
        )
        self.assertEqual(second_resp.status_code, 201)
        second_data = second_resp.json()
        self.assertEqual(second_data["created_count"], 1)

        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("3.00"))

        self.assertEqual(
            Transaction.objects.filter(receipt_guid="R-PARTIAL").count(), 3
        )

    def test_totals_do_not_override_bonus_balance(self):
        payload = self._base_payload()
        payload["totals"]["bonus_earned"] = "0.00"
        payload["positions"][0]["bonus_earned"] = "1.00"

        user = CustomUser.objects.create(telegram_id=9001, bonuses=Decimal("0"))
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000301",
        )
        self.assertEqual(response.status_code, 201)

        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("1.00"))

    def test_receipt_line_field_is_required(self):
        payload = self._base_payload()
        position = payload["positions"][0]
        position.pop("line_number")
        position["receipt_line"] = 1

        user = CustomUser.objects.create(telegram_id=9001)
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000401",
        )

        self.assertEqual(response.status_code, 400)
        details = response.json().get("details", {})
        self.assertIn("positions", details)

    def test_guest_receipt_returns_201(self):
        payload = self._base_payload()
        payload["receipt_guid"] = "R-guest"
        payload["customer"] = None

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000002",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["customer"]["telegram_id"], settings.GUEST_TELEGRAM_ID)
        self.assertEqual(data["totals"]["bonus_earned"], 0.0)

    def test_missing_required_field_returns_structured_error(self):
        payload = self._base_payload()
        payload.pop("receipt_guid")

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000003",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error_code"], "missing_field")
        self.assertIn("receipt_guid", data["details"])

    def test_duplicate_line_returns_duplicate_receipt_line_error(self):
        payload = self._base_payload()
        user = CustomUser.objects.create(telegram_id=9001)
        payload["customer"] = {"card_id": user.card_id}
        payload["positions"].append(
            {
                "product_code": "SKU-2",
                "quantity": "1",
                "price": "50.00",
                "line_number": 1,
            }
        )

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000004",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error_code"], "duplicate_receipt_line")
        self.assertTrue(data["details"])  # ensure diagnostics present

    def test_invalid_or_missing_api_key_returns_401(self):
        payload = self._base_payload()

        response_missing = self._post_receipt(
            payload,
            api_key=None,
            idem="00000000-0000-0000-0000-000000000005",
        )
        self.assertEqual(response_missing.status_code, 401)

        response_wrong = self._post_receipt(
            payload,
            api_key="wrong",
            idem="00000000-0000-0000-0000-000000000006",
        )
        self.assertEqual(response_wrong.status_code, 401)

    def test_purchase_type_delivery_saved(self):
        payload = self._base_payload()
        payload["purchase_type"] = "delivery"
        user = CustomUser.objects.create(telegram_id=9001)
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-100000000001",
        )

        self.assertEqual(response.status_code, 201)
        tx = Transaction.objects.get()
        self.assertEqual(tx.purchase_type, "delivery")

    def test_purchase_type_pickup_saved(self):
        payload = self._base_payload()
        payload["purchase_type"] = "pickup"
        user = CustomUser.objects.create(telegram_id=9001)
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-100000000002",
        )

        self.assertEqual(response.status_code, 201)
        tx = Transaction.objects.get()
        self.assertEqual(tx.purchase_type, "pickup")

    def test_purchase_type_in_store_saved(self):
        payload = self._base_payload()
        payload["purchase_type"] = "in_store"
        user = CustomUser.objects.create(telegram_id=9001)
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-100000000003",
        )

        self.assertEqual(response.status_code, 201)
        tx = Transaction.objects.get()
        self.assertEqual(tx.purchase_type, "in_store")

    def test_purchase_type_missing_defaults_to_in_store(self):
        payload = self._base_payload()
        user = CustomUser.objects.create(telegram_id=9001)
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-100000000004",
        )

        self.assertEqual(response.status_code, 201)
        tx = Transaction.objects.get()
        self.assertEqual(tx.purchase_type, "in_store")

    def test_purchase_type_invalid_returns_400(self):
        payload = self._base_payload()
        payload["purchase_type"] = "express"
        user = CustomUser.objects.create(telegram_id=9001)
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-100000000005",
        )

        self.assertEqual(response.status_code, 400)

    def test_receipt_with_card_id_finds_customer(self):
        user = CustomUser.objects.create(telegram_id=9001)
        payload = self._base_payload()
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-300000000001",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["customer"]["card_id"], user.card_id)

    def test_receipt_unknown_card_id_returns_error(self):
        payload = self._base_payload()
        payload["customer"] = {"card_id": "LC-999999"}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-300000000002",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "unknown_customer")

    def test_receipt_without_customer_goes_to_guest(self):
        payload = self._base_payload()
        payload["customer"] = None

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-300000000003",
        )

        self.assertEqual(response.status_code, 201)
        from django.conf import settings as _s
        self.assertEqual(response.json()["customer"]["telegram_id"], _s.GUEST_TELEGRAM_ID)

    def test_total_spent_uses_totals_amount_on_full_receipt(self):
        payload = self._base_payload()
        payload["receipt_guid"] = "R-FULL"
        payload["positions"] = [
            {"product_code": "SKU-1", "quantity": "1", "price": "100.00", "line_number": 1},
            {"product_code": "SKU-2", "quantity": "1", "price": "50.00", "line_number": 2},
        ]
        # sum(pos_total) = 150.00; totals.total_amount = 149.00 (скидка на чек)
        payload["totals"] = {
            "total_amount": "149.00",
            "discount_total": "1.00",
            "bonus_spent": "0",
            "bonus_earned": "0",
        }

        user = CustomUser.objects.create(telegram_id=9101, total_spent=Decimal("0"))
        payload["customer"] = {"card_id": user.card_id}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000501",
        )

        self.assertEqual(response.status_code, 201)
        user.refresh_from_db()
        # Полный чек — total_spent берётся из totals.total_amount, а не из суммы позиций.
        self.assertEqual(user.total_spent, Decimal("149.00"))

    def test_card_id_format(self):
        user = CustomUser.objects.create(telegram_id=9001)
        self.assertRegex(user.card_id, r'^LC-\d{6}$')

    def test_card_id_auto_generated(self):
        user = CustomUser.objects.create(telegram_id=9002)
        self.assertIsNotNone(user.card_id)
        self.assertEqual(user.card_id, f"LC-{user.pk:06d}")
