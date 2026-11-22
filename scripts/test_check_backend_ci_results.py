import unittest
from pathlib import Path

from scripts.check_backend_ci_results import validate_backend_results


def passing_values(*, tests_required="true", tests_result="success"):
    return {
        "CI_SCOPE_RESULT": "success",
        "QUALITY_RESULT": "success",
        "TESTS_REQUIRED": tests_required,
        "TESTS_RESULT": tests_result,
    }


class CheckBackendCIResultsTests(unittest.TestCase):
    def test_accepts_complete_product_suite(self):
        self.assertEqual(validate_backend_results(passing_values()), [])

    def test_accepts_only_a_skipped_product_suite_when_scope_isolated(self):
        self.assertEqual(validate_backend_results(passing_values(
            tests_required="false", tests_result="skipped")), [])

    def test_quality_failure_blocks_product_tests_and_aggregate(self):
        values = passing_values(tests_result="skipped")
        values["QUALITY_RESULT"] = "failure"
        errors = validate_backend_results(values)
        self.assertTrue(any("quality gate" in error for error in errors))
        self.assertTrue(any("product tests" in error for error in errors))

    def test_required_product_suite_cannot_be_skipped_or_failed(self):
        for result in ("skipped", "failure", "cancelled", ""):
            with self.subTest(result=result):
                errors = validate_backend_results(passing_values(tests_result=result))
                self.assertTrue(any("product tests" in error for error in errors))

    def test_unselected_product_suite_must_remain_skipped(self):
        for result in ("success", "failure", "cancelled", ""):
            with self.subTest(result=result):
                errors = validate_backend_results(passing_values(
                    tests_required="false", tests_result=result))
                self.assertTrue(any("did not skip" in error for error in errors))

    def test_classifier_failure_or_unknown_scope_blocks_aggregate(self):
        values = passing_values()
        values["CI_SCOPE_RESULT"] = "failure"
        self.assertTrue(any("classifier" in error
                            for error in validate_backend_results(values)))
        values = passing_values()
        values["TESTS_REQUIRED"] = "unknown"
        self.assertTrue(any("scope" in error
                            for error in validate_backend_results(values)))

    def test_workflow_keeps_backend_check_and_waits_for_quality_before_shards(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        shards = workflow.split("  backend-tests:\n", 1)[1].split("\n  backend:\n", 1)[0]
        aggregate = workflow.split("  backend:\n", 1)[1].split("\n  frontend:\n", 1)[0]
        self.assertIn("needs: [ci-scope, backend-quality]", shards)
        self.assertIn("outputs.backend_tests == 'true'", shards)
        self.assertIn("fail-fast: false", shards)
        self.assertIn("python scripts/check_backend_ci_results.py", aggregate)
        self.assertIn("needs: [ci-scope, backend-quality, backend-tests]", aggregate)
        self.assertIn("backend:", workflow)
        self.assertIn("BACKEND_RESULT: ${{ needs.backend.result }}", workflow)


if __name__ == "__main__":
    unittest.main()
