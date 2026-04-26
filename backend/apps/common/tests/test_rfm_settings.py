"""Тест чтения RFM-thresholds из settings (H6)."""
from django.test import SimpleTestCase, override_settings

from apps.rfm.services import (
    _frequency_thresholds,
    _monetary_thresholds,
    _recency_thresholds,
)


class RfmThresholdsFromSettingsTests(SimpleTestCase):
    def test_default_values(self):
        self.assertEqual(_recency_thresholds(), [7, 30, 90, 180])
        self.assertEqual(_frequency_thresholds(), [2, 5, 10, 20])

    @override_settings(RFM_RECENCY_THRESHOLDS=[1, 2, 3, 4])
    def test_recency_override(self):
        self.assertEqual(_recency_thresholds(), [1, 2, 3, 4])

    @override_settings(RFM_FREQUENCY_THRESHOLDS=[10, 20, 30, 40])
    def test_frequency_override(self):
        self.assertEqual(_frequency_thresholds(), [10, 20, 30, 40])

    @override_settings(RFM_MONETARY_THRESHOLDS=[100, 200, 300, 400])
    def test_monetary_override(self):
        self.assertEqual(_monetary_thresholds(), [100, 200, 300, 400])
