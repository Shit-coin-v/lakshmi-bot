"""Tests for RFM segment sync resume behaviour (H7 audit-report.md).

При retry задача sync_rfm_segments_to_onec не должна повторно отправлять
chunks, которые уже были успешно доставлены в 1С (RFMSegmentSyncLog.chunks_sent).
Иначе 1С получает дубли назначений сегментов.
"""

from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.main.models import CustomUser
from apps.rfm.models import CustomerBonusTier, RFMSegmentSyncLog
from apps.rfm.tasks import sync_rfm_segments_to_onec


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


def _bulk_create_customers_with_tiers(count: int, telegram_offset: int = 700000):
    """Создаёт count клиентов с card_id и CustomerBonusTier на тестовый месяц."""
    users = []
    for i in range(count):
        users.append(
            CustomUser(
                telegram_id=telegram_offset + i,
                referral_code=f"RS{i:06d}",
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
    return created_users


@override_settings(**_TEST_SETTINGS)
class ResumeFromChunksSentTests(TestCase):
    """При retry с chunks_sent>0 задача пропускает уже доставленные chunks."""

    def setUp(self):
        # 1200 клиентов → 3 chunk'а по 500/500/200.
        _bulk_create_customers_with_tiers(1200, telegram_offset=700000)

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_resume_skips_already_sent_chunks(self, mock_post):
        """Если sync_log в IN_PROGRESS и chunks_sent=2 — отправляем
        только третий chunk."""
        # Имитируем состояние после неудачного прогона: первые два chunk
        # успешно доставлены, задача упала и теперь идёт retry.
        RFMSegmentSyncLog.objects.create(
            effective_month=EFFECTIVE_FROM,
            status=RFMSegmentSyncLog.Status.IN_PROGRESS,
            total_customers=1200,
            total_chunks=3,
            chunks_sent=2,
            chunks_failed=0,
        )

        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "ok", "processed": 200},
        )

        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        # Должен быть один POST (третий chunk на 200 клиентов).
        self.assertEqual(
            mock_post.call_count,
            1,
            "При resume отправляться должен только оставшийся chunk",
        )

        # Проверяем, что отправлен именно остаточный пакет (200 клиентов).
        call = mock_post.call_args_list[0]
        payload = call.kwargs.get("json") or call[1].get("json", [])
        self.assertEqual(len(payload), 200)

        # Sync_log в финале — SUCCESS, chunks_sent=3.
        log = RFMSegmentSyncLog.objects.get(effective_month=EFFECTIVE_FROM)
        self.assertEqual(log.status, RFMSegmentSyncLog.Status.SUCCESS)
        self.assertEqual(log.chunks_sent, 3)
        self.assertEqual(log.chunks_failed, 0)


@override_settings(**_TEST_SETTINGS)
class FreshRunSendsAllChunksTests(TestCase):
    """Полный прогон с нуля: отправляем все chunks."""

    def setUp(self):
        # 1200 клиентов → 3 chunk'а.
        _bulk_create_customers_with_tiers(1200, telegram_offset=710000)

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_full_run_sends_all_chunks(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "ok", "processed": 500},
        )

        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        self.assertEqual(mock_post.call_count, 3)

        log = RFMSegmentSyncLog.objects.get(effective_month=EFFECTIVE_FROM)
        self.assertEqual(log.status, RFMSegmentSyncLog.Status.SUCCESS)
        self.assertEqual(log.chunks_sent, 3)
        self.assertEqual(log.chunks_failed, 0)

    @patch("apps.integrations.onec.onec_client.requests.post")
    def test_pending_log_does_not_skip_chunks(self, mock_post):
        """Если sync_log в PENDING (создан внешне, но прогона ещё не было) —
        отправляем все chunks с нуля."""
        RFMSegmentSyncLog.objects.create(
            effective_month=EFFECTIVE_FROM,
            status=RFMSegmentSyncLog.Status.PENDING,
        )
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "ok", "processed": 500},
        )

        sync_rfm_segments_to_onec(EFFECTIVE_MONTH)

        self.assertEqual(mock_post.call_count, 3)
