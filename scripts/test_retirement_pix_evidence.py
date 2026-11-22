"""Tests for the privacy-preserving PIX continuity summary."""

import unittest

from retirement_pix_evidence import summarize


class RetirementPixEvidenceTests(unittest.TestCase):
    def test_summary_contains_only_aggregate_availability(self):
        result = summarize([
            {"pix_available": True, "card_available": False, "tenant_id": "sensitive"},
        ])
        self.assertEqual(result, {
            "tenant_count": 1,
            "pix_available_count": 1,
            "card_available_count": 0,
            "all_tenants_pix_available": True,
        })
        self.assertNotIn("tenant_id", result)

    def test_unavailable_pix_is_a_release_gate(self):
        self.assertFalse(summarize([{"pix_available": False, "card_available": False}])["all_tenants_pix_available"])


if __name__ == "__main__":
    unittest.main()
