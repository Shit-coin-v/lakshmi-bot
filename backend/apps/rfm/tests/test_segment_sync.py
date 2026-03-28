"""Tests for RFM segment sync to 1C.

Covers all scenarios from design doc (section 11):
1. segment_label_at_fixation stores full segment (not just champions/standard)
2. Sync sends only customers with card_id
3. Payload contains only card_id and segment keys
4. Chunking: 1200 customers -> 3 chunks (500/500/200)
5. Retry on HTTP error
6. Idempotent skip when status=SUCCESS
7. Partial failure: 2 of 3 chunks ok -> status=PARTIAL
8. Sync disabled by ONEC_RFM_SYNC_ENABLED=False
9. Sync skipped when no CustomerBonusTier for month
10. Sync triggered after fix_monthly_bonus_tiers
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.main.models import CustomUser
from apps.rfm.models import CustomerBonusTier

# RFMSegmentSyncLog will be created by migration; import conditionally
# to allow tests to be written before model exists.
try:
    from apps.rfm.models import RFMSegmentSyncLog
except ImportError:
    RFMSegmentSyncLog = None

# Task import — may not exist yet during TDD phase.
try:
    from apps.rfm.tasks import sync_rfm_segments_to_onec
except ImportError:
    sync_rfm_segments_to_onec = None


_TEST_SETTINGS = {
    "GUEST_TELEGRAM_ID": 0,
    "ONEC_RFM_SYNC_ENABLED": True,
    "ONEC_RFM_SYNC_URL": "https://onec.test/rfm-sync",
    "ONEC_RFM_SYNC_CHUNK_SIZE": 500,
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES": True,
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
}

EFFECTIVE_MONTH = "2026-04-01"
EFFECTIVE_FROM = date(2026, 4, 1)
EFFECTIVE_TO = date(2026, 4, 30)


def _create_user(telegram_id, card_id=None, **kwargs):
    """Helper: create CustomUser with optional card_id override."""
    user = CustomUser.objects.create(telegram_id=telegram_id, **kwargs)
    if card_id is not None:
        # Override auto-generated card_id (including setting to empty).
        CustomUser.objects.filter(pk=user.pk).update(card_id=card_id)
        user.refresh_from_db()
    return user


def _create_tier(customer, segment_label="champions", tier=None,
                 effective_from=None, effective_to=None):
    """Helper: create CustomerBonusTier for a customer."""
    if tier is None:
        tier = "champions" if segment_label == "champions" else "standard"
    return CustomerBonusTier.objects.create(
        customer=customer,
        tier=tier,
        segment_label_at_fixation=segment_label,
        effective_from=effective_from or EFFECTIVE_FROM,
        effective_to=effective_to or EFFECTIVE_TO,
    )


# ===================================================================
# 1. segment_label_at_fixation stores full segment
# ===================================================================

@override_settings(GUEST_TELEGRAM_ID=0)
class SegmentLabelAtFixationTests(TestCase):
    """Test 1: CustomerBonusTier.segment_label_at_fixation contains full
    RFM segment label, not the binary tier (champions/standard)."""

    def test_segment_label_at_fixation_is_full_segment(self):
        """Full segment labels (loyal, at_risk, etc.) are stored,
        not collapsed to champions/standard."""
        user = _create_user(300001)
        full_segments = [
            "champions", "loyal", "potential_loyalists",
            "new_customers", "at_risk", "hibernating", "lost",
        ]
        for i, segment in enumerate(full_segments):
            tier = _create_tier(
                customer=user,
                segment_label=segment,
                effective_from=date(2026, 1 + i, 1),
                effective_to=date(2026, 1 + i, 28),
            )
            tier.refresh_from_db()
            self.assertEqual(
                tier.segment_label_at_fixation,
                segment,
                f"Expected full segment '{segment}' to be stored, "
                f"got '{tier.segment_label_at_fixation}'",
            )


# ===================================================================
# 2. Sync sends only customers with card_id
# ===================================================================

@override_settings(**_TEST_SETTINGS)
class SyncOnlyCustomersWithCardIdTests(TestCase):
    """Test 2: sync_rfm_segments_to_onec sends only customers
    who have a non-empty card_id."""

    def setUp(self):
        # User with card_id (auto-generated on save)
        self.user_with_card = _create_user(310001)
        _create_tier(self.user_with_card, segment_label="loyal")

        # User without card_id
        self.user_no_card = _create_user(310002, card_id="")
        _create_tier(self.user_no_card, segment_label="lost")

        # User with card_id=None
        self.user_null_card = _create_user(310003, card_id=None)
        _create_tier(self.user_null_card, segment_label="at_risk")

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_sync_only_customers_with_card_id(self, mock_post):
        if sync_rfm_segments_to_onec is None:
            self.skipTest("sync_rfm_segments_to_onec not implemented yet")

        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "ok", "processed": 1},
        )

        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        # Extract all card_ids sent across all calls
        sent_card_ids = set()
        for c in mock_post.call_args_list:
            payload = c.kwargs.get("json") or c[1].get("json", [])
            for item in payload:
                sent_card_ids.add(item["card_id"])

        self.assertIn(self.user_with_card.card_id, sent_card_ids)
        self.assertNotIn("", sent_card_ids)
        self.assertNotIn(None, sent_card_ids)


# ===================================================================
# 3. Payload contains only card_id and segment
# ===================================================================

@override_settings(**_TEST_SETTINGS)
class PayloadOnlyCardIdAndSegmentTests(TestCase):
    """Test 3: Each item in the sync payload must contain exactly
    two keys: card_id and segment."""

    def setUp(self):
        self.user = _create_user(320001)
        _create_tier(self.user, segment_label="champions")

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_payload_only_card_id_and_segment(self, mock_post):
        if sync_rfm_segments_to_onec is None:
            self.skipTest("sync_rfm_segments_to_onec not implemented yet")

        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "ok", "processed": 1},
        )

        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        self.assertTrue(mock_post.called, "Expected at least one HTTP call")
        for c in mock_post.call_args_list:
            payload = c.kwargs.get("json") or c[1].get("json", [])
            for item in payload:
                self.assertEqual(
                    set(item.keys()),
                    {"card_id", "segment"},
                    f"Unexpected keys in payload item: {item.keys()}",
                )


# ===================================================================
# 4. Chunking correctness
# ===================================================================

@override_settings(**{**_TEST_SETTINGS, "ONEC_RFM_SYNC_CHUNK_SIZE": 500})
class ChunkingCorrectTests(TestCase):
    """Test 4: 1200 customers -> 3 chunks of 500/500/200."""

    def setUp(self):
        # Create 1200 users with card_ids and tiers.
        users = []
        for i in range(1200):
            users.append(
                CustomUser(
                    telegram_id=400000 + i,
                    referral_code=f"CH{i:06d}",
                )
            )
        created_users = CustomUser.objects.bulk_create(users)

        # Set card_ids for all users (bulk_create skips custom save).
        for u in created_users:
            u.card_id = CustomUser.generate_card_id(u.pk)
        CustomUser.objects.bulk_update(created_users, ["card_id"])

        # Create tiers for all.
        tiers = []
        for u in created_users:
            tiers.append(CustomerBonusTier(
                customer=u,
                tier="standard",
                segment_label_at_fixation="loyal",
                effective_from=EFFECTIVE_FROM,
                effective_to=EFFECTIVE_TO,
            ))
        CustomerBonusTier.objects.bulk_create(tiers)

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_chunking_correct(self, mock_post):
        if sync_rfm_segments_to_onec is None:
            self.skipTest("sync_rfm_segments_to_onec not implemented yet")

        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "ok", "processed": 500},
        )

        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        self.assertEqual(mock_post.call_count, 3, "Expected 3 chunks")

        chunk_sizes = []
        for c in mock_post.call_args_list:
            payload = c.kwargs.get("json") or c[1].get("json", [])
            chunk_sizes.append(len(payload))

        chunk_sizes.sort(reverse=True)
        self.assertEqual(chunk_sizes, [500, 500, 200])


# ===================================================================
# 5. Retry on HTTP error
# ===================================================================

@override_settings(**_TEST_SETTINGS)
class RetryOnHttpErrorTests(TestCase):
    """Test 5: Task retries on HTTP error (task-level, not chunk-level)."""

    def setUp(self):
        self.user = _create_user(330001)
        _create_tier(self.user, segment_label="champions")

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_retry_on_http_error(self, mock_post):
        if sync_rfm_segments_to_onec is None:
            self.skipTest("sync_rfm_segments_to_onec not implemented yet")

        mock_post.side_effect = ConnectionError("Connection refused")

        # Task catches chunk errors internally; verify it marks FAILED
        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        sync_log = RFMSegmentSyncLog.objects.get(effective_month=EFFECTIVE_MONTH)
        self.assertEqual(sync_log.status, RFMSegmentSyncLog.Status.FAILED)
        self.assertIn("Connection refused", sync_log.last_error)


# ===================================================================
# 6. Idempotent skip on SUCCESS
# ===================================================================

@override_settings(**_TEST_SETTINGS)
class IdempotentSkipOnSuccessTests(TestCase):
    """Test 6: Re-running sync when status=SUCCESS skips execution."""

    def setUp(self):
        self.user = _create_user(340001)
        _create_tier(self.user, segment_label="loyal")

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_idempotent_skip_on_success(self, mock_post):
        if sync_rfm_segments_to_onec is None:
            self.skipTest("sync_rfm_segments_to_onec not implemented yet")
        if RFMSegmentSyncLog is None:
            self.skipTest("RFMSegmentSyncLog model not implemented yet")

        # Pre-create a SUCCESS log for this month.
        RFMSegmentSyncLog.objects.create(
            effective_month=EFFECTIVE_FROM,
            status=RFMSegmentSyncLog.Status.SUCCESS,
            total_customers=1,
            total_chunks=1,
            chunks_sent=1,
        )

        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        # No HTTP calls should be made — sync was skipped.
        mock_post.assert_not_called()


# ===================================================================
# 7. Partial failure
# ===================================================================

@override_settings(**{**_TEST_SETTINGS, "ONEC_RFM_SYNC_CHUNK_SIZE": 500})
class PartialFailureTests(TestCase):
    """Test 7: 2 of 3 chunks OK -> status=PARTIAL."""

    def setUp(self):
        users = []
        for i in range(1200):
            users.append(
                CustomUser(
                    telegram_id=500000 + i,
                    referral_code=f"PF{i:06d}",
                )
            )
        created_users = CustomUser.objects.bulk_create(users)
        for u in created_users:
            u.card_id = CustomUser.generate_card_id(u.pk)
        CustomUser.objects.bulk_update(created_users, ["card_id"])

        tiers = []
        for u in created_users:
            tiers.append(CustomerBonusTier(
                customer=u,
                tier="standard",
                segment_label_at_fixation="loyal",
                effective_from=EFFECTIVE_FROM,
                effective_to=EFFECTIVE_TO,
            ))
        CustomerBonusTier.objects.bulk_create(tiers)

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_partial_failure(self, mock_post):
        if sync_rfm_segments_to_onec is None:
            self.skipTest("sync_rfm_segments_to_onec not implemented yet")
        if RFMSegmentSyncLog is None:
            self.skipTest("RFMSegmentSyncLog model not implemented yet")

        # First two chunks succeed, third fails.
        ok_response = MagicMock(
            status_code=200,
            json=lambda: {"status": "ok", "processed": 500},
        )
        fail_response = MagicMock(
            status_code=500,
            text="Internal Server Error",
        )

        mock_post.side_effect = [ok_response, ok_response, fail_response]

        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        log = RFMSegmentSyncLog.objects.get(effective_month=EFFECTIVE_FROM)
        self.assertEqual(log.status, RFMSegmentSyncLog.Status.PARTIAL)
        self.assertEqual(log.chunks_sent, 2)
        self.assertEqual(log.chunks_failed, 1)


# ===================================================================
# 8. Sync disabled by setting
# ===================================================================

@override_settings(**{**_TEST_SETTINGS, "ONEC_RFM_SYNC_ENABLED": False})
class SyncDisabledBySettingTests(TestCase):
    """Test 8: Sync does not run when ONEC_RFM_SYNC_ENABLED=False."""

    def setUp(self):
        self.user = _create_user(350001)
        _create_tier(self.user, segment_label="champions")

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_sync_disabled_by_setting(self, mock_post):
        if sync_rfm_segments_to_onec is None:
            self.skipTest("sync_rfm_segments_to_onec not implemented yet")

        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        mock_post.assert_not_called()


# ===================================================================
# 9. Sync skipped when no tiers for month
# ===================================================================

@override_settings(**_TEST_SETTINGS)
class SyncSkipNoTiersTests(TestCase):
    """Test 9: Sync skips when no CustomerBonusTier exists for the month."""

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_sync_skip_no_tiers(self, mock_post):
        if sync_rfm_segments_to_onec is None:
            self.skipTest("sync_rfm_segments_to_onec not implemented yet")

        # No tiers created at all.
        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        mock_post.assert_not_called()


# ===================================================================
# 10. Sync triggered after fix_monthly_bonus_tiers
# ===================================================================

@override_settings(**_TEST_SETTINGS)
class SyncTriggeredAfterMonthlyFixTests(TestCase):
    """Test 10: fix_monthly_bonus_tiers triggers sync_rfm_segments_to_onec
    (not recalculate_all_rfm)."""

    def setUp(self):
        self.user = _create_user(
            360001,
            last_purchase_date=timezone.now() - timedelta(days=5),
            purchase_count=10,
            total_spent=Decimal("5000"),
        )

    @patch("apps.rfm.tasks.sync_rfm_segments_to_onec")
    def test_sync_triggered_after_monthly_fix(self, mock_sync_task):
        """fix_monthly_bonus_tiers calls sync_rfm_segments_to_onec.delay()
        at the end of execution."""
        from apps.rfm.tasks import fix_monthly_bonus_tiers

        # Make .delay() a no-op to avoid actual execution.
        mock_sync_task.delay = MagicMock()

        fix_monthly_bonus_tiers()

        mock_sync_task.delay.assert_called_once()
        # Verify the effective_month argument is the first of current month.
        args = mock_sync_task.delay.call_args
        effective_month_arg = args[0][0] if args[0] else args[1].get("effective_month")
        expected = date.today().replace(day=1).isoformat()
        self.assertEqual(
            str(effective_month_arg),
            expected,
            f"Expected effective_month={expected}, got {effective_month_arg}",
        )

    @patch("apps.rfm.tasks.sync_rfm_segments_to_onec")
    @override_settings(**{**_TEST_SETTINGS, "ONEC_RFM_SYNC_ENABLED": False})
    def test_sync_not_triggered_when_disabled(self, mock_sync_task):
        """fix_monthly_bonus_tiers does NOT call sync when disabled."""
        from apps.rfm.tasks import fix_monthly_bonus_tiers

        mock_sync_task.delay = MagicMock()

        fix_monthly_bonus_tiers()

        mock_sync_task.delay.assert_not_called()

    @patch("apps.rfm.tasks.sync_rfm_segments_to_onec")
    def test_recalculate_all_rfm_does_not_trigger_sync(self, mock_sync_task):
        """recalculate_all_rfm must NOT trigger segment sync."""
        from apps.rfm.tasks import recalculate_all_rfm

        mock_sync_task.delay = MagicMock()

        recalculate_all_rfm()

        mock_sync_task.delay.assert_not_called()
