"""Tests for SEGMENT_MAP integrity and consistency with RFM_SEGMENT_CHOICES."""

from django.test import SimpleTestCase

from apps.rfm.constants import LOST, RFM_SEGMENT_CHOICES
from apps.rfm.services import SEGMENT_MAP


class SegmentMapUniquenessTests(SimpleTestCase):
    """Ensure no rfm_code appears in more than one segment."""

    def test_no_duplicate_codes_across_segments(self):
        seen: dict[str, str] = {}
        duplicates: list[str] = []

        for codes, label in SEGMENT_MAP:
            for code in codes:
                if code in seen:
                    duplicates.append(
                        f"Code '{code}' found in both '{seen[code]}' and '{label}'"
                    )
                seen[code] = label

        self.assertEqual(
            duplicates, [],
            f"SEGMENT_MAP has duplicate rfm_codes: {duplicates}",
        )

    def test_all_segments_have_at_least_one_code(self):
        for codes, label in SEGMENT_MAP:
            self.assertGreater(
                len(codes), 0,
                f"Segment '{label}' has no rfm_codes",
            )

    def test_all_codes_are_three_digit_strings(self):
        for codes, label in SEGMENT_MAP:
            for code in codes:
                self.assertRegex(
                    code, r"^[1-5]{3}$",
                    f"Code '{code}' in segment '{label}' is not a valid 3-digit RFM code (1-5)",
                )

    def test_segment_map_labels_are_in_choices(self):
        """Every label used in SEGMENT_MAP must be declared in RFM_SEGMENT_CHOICES."""
        valid_labels = {c[0] for c in RFM_SEGMENT_CHOICES}
        map_labels = {label for _, label in SEGMENT_MAP}
        unknown = map_labels - valid_labels
        self.assertEqual(
            unknown, set(),
            f"SEGMENT_MAP uses labels not in RFM_SEGMENT_CHOICES: {unknown}",
        )

    def test_choices_labels_covered_by_segment_map_or_fallback(self):
        """Every label in RFM_SEGMENT_CHOICES should appear in SEGMENT_MAP or be the LOST fallback."""
        map_labels = {label for _, label in SEGMENT_MAP}
        choices_labels = {c[0] for c in RFM_SEGMENT_CHOICES}
        uncovered = choices_labels - map_labels - {LOST}
        self.assertEqual(
            uncovered, set(),
            f"RFM_SEGMENT_CHOICES labels not in SEGMENT_MAP (and not LOST fallback): {uncovered}",
        )
