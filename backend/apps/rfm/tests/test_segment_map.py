"""Tests for SEGMENT_MAP integrity in rfm/services."""

from django.test import SimpleTestCase

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
