"""Contract tests for non-PII financial preservation evidence."""

import unittest

from retirement_financial_evidence import (
    TABLE_COLUMNS,
    count_confirmed_infinitepay_rows,
    digest_rows,
)


class FinancialEvidenceTests(unittest.TestCase):
    def test_fingerprint_is_order_independent_and_counts_rows(self):
        rows = [{"id": "1", "amount": 100}, {"id": "2", "amount": 200}]
        self.assertEqual(digest_rows(rows), digest_rows(reversed(rows)))
        self.assertEqual(digest_rows(rows)["count"], 2)

    def test_change_to_financial_identity_changes_digest(self):
        original = [{"id": "1", "provider": "infinitepay", "total_cents": 100}]
        changed = [{"id": "1", "provider": "infinitepay", "total_cents": 101}]
        self.assertNotEqual(digest_rows(original)["sha256"], digest_rows(changed)["sha256"])

    def test_evidence_excludes_removed_checkout_credentials_and_private_fields(self):
        self.assertEqual(TABLE_COLUMNS["provider_payment"],
                         ("id", "provider", "total_cents", "provider_transaction_nsu", "state"))
        self.assertNotIn("checkout_url", TABLE_COLUMNS["provider_payment"])
        self.assertNotIn("credential_id", TABLE_COLUMNS["provider_payment"])
        self.assertNotIn("client_id", TABLE_COLUMNS["provider_payment"])

    def test_only_two_confirmed_infinitepay_payments_are_counted_without_exposing_rows(self):
        rows = [
            {"provider": "infinitepay", "state": "confirmed"},
            {"provider": "infinitepay", "state": "confirmed"},
            {"provider": "infinitepay", "state": "awaiting_payment"},
            {"provider": "other", "state": "confirmed"},
        ]
        self.assertEqual(count_confirmed_infinitepay_rows(rows), 2)


if __name__ == "__main__":
    unittest.main()
