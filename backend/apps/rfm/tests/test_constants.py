"""Контракт RFM-сегментов: фиксируем 7 ключ→русский_лейбл пар.

Если кто-то изменит SEGMENT_LABEL_RU (переименует, удалит ключ,
изменит русский текст) — этот тест упадёт. Это защита контракта
с 1С: задача sync_rfm_segments_to_onec отправляет именно эти строки."""
from django.test import SimpleTestCase

from apps.rfm.constants import SEGMENT_LABEL_RU


class SegmentLabelRuContractTests(SimpleTestCase):
    """Проверяем фиксированный контракт перевода RFM-сегментов на русский."""

    def test_seven_keys_present(self):
        self.assertEqual(set(SEGMENT_LABEL_RU.keys()), {
            "champions", "loyal", "potential_loyalists", "new_customers",
            "at_risk", "hibernating", "lost",
        })

    def test_russian_labels_exact(self):
        # Точные строки, которые отправляются в 1С — менять только с
        # согласованием контракта.
        self.assertEqual(SEGMENT_LABEL_RU["champions"], "Чемпионы")
        self.assertEqual(SEGMENT_LABEL_RU["loyal"], "Лояльные")
        self.assertEqual(SEGMENT_LABEL_RU["potential_loyalists"], "Потенциально лояльные")
        self.assertEqual(SEGMENT_LABEL_RU["new_customers"], "Новые клиенты")
        self.assertEqual(SEGMENT_LABEL_RU["at_risk"], "Под угрозой")
        self.assertEqual(SEGMENT_LABEL_RU["hibernating"], "Спящие")
        self.assertEqual(SEGMENT_LABEL_RU["lost"], "Потерянные")
