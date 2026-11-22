"""Tests for the explicit InfinitePay retirement release approval gate."""

import unittest

from validate_retirement_approval import validate_approval


class RetirementApprovalTests(unittest.TestCase):
    FINGERPRINT = "a" * 64

    def test_accepts_matching_lowercase_sha256_fingerprint(self):
        validate_approval(self.FINGERPRINT, self.FINGERPRINT)

    def test_rejects_missing_or_malformed_fingerprint(self):
        for value in (None, "", "A" * 64, "a" * 63, "g" * 64):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_approval(value, self.FINGERPRINT)

    def test_rejects_missing_or_malformed_inventory_fingerprint(self):
        for value in (None, "", "A" * 64, "a" * 63, "g" * 64):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_approval(self.FINGERPRINT, value)

    def test_rejects_inventory_changed_after_approval(self):
        observed = "b" * 64
        with self.assertRaisesRegex(ValueError, "mudou desde a aprovação"):
            validate_approval(self.FINGERPRINT, observed)


if __name__ == "__main__":
    unittest.main()
