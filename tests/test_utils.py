from __future__ import annotations

import unittest

from nba_ingestion.models import DataQualityError
from nba_ingestion.utils import clean_string, to_float, to_int, to_league_id


class UtilsTests(unittest.TestCase):
    def test_clean_string_trims_and_handles_blank_values(self) -> None:
        self.assertEqual(clean_string("  Kevin Durant  "), "Kevin Durant")
        self.assertIsNone(clean_string("   "))
        self.assertIsNone(clean_string(None))

    def test_to_int_handles_integer_compatible_values(self) -> None:
        self.assertEqual(to_int(12, "FIELD"), 12)
        self.assertEqual(to_int("12", "FIELD"), 12)
        self.assertEqual(to_int("12.0", "FIELD"), 12)

    def test_to_int_handles_nullable_and_required_blanks(self) -> None:
        self.assertIsNone(to_int("", "FIELD"))

        with self.assertRaisesRegex(DataQualityError, "FIELD is required"):
            to_int("", "FIELD", allow_none=False)

    def test_to_int_raises_on_invalid_values(self) -> None:
        with self.assertRaisesRegex(DataQualityError, "integer-compatible"):
            to_int("not an int", "FIELD")

    def test_to_float_handles_numeric_strings(self) -> None:
        self.assertEqual(to_float("12.5", "FIELD"), 12.5)
        self.assertEqual(to_float(12, "FIELD"), 12.0)

    def test_to_float_raises_on_invalid_required_values(self) -> None:
        with self.assertRaisesRegex(DataQualityError, "FIELD is required"):
            to_float(None, "FIELD", allow_none=False)

        with self.assertRaisesRegex(DataQualityError, "float-compatible"):
            to_float("not a float", "FIELD")

    def test_to_league_id_pads_single_digit_and_rejects_nulls(self) -> None:
        self.assertEqual(to_league_id("0"), "00")
        self.assertEqual(to_league_id("00"), "00")

        with self.assertRaisesRegex(DataQualityError, "LEAGUE_ID is required"):
            to_league_id(None)


if __name__ == "__main__":
    unittest.main()
