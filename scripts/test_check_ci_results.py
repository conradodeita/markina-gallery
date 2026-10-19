import unittest

from scripts.check_ci_results import validate_results


def passing_values():
    return {
        "CI_SCOPE_RESULT": "success",
        "BACKEND_REQUIRED": "false",
        "BACKEND_RESULT": "skipped",
        "FRONTEND_REQUIRED": "true",
        "FRONTEND_RESULT": "success",
        "GEMMA_REQUIRED": "false",
        "GEMMA_RESULT": "skipped",
        "RUNTIME_IMAGES_REQUIRED": "false",
        "RUNTIME_IMAGES_RESULT": "skipped",
        "OPENSPEC_RESULT": "success",
        "GITLEAKS_RESULT": "success",
    }


class CheckCIResultsTests(unittest.TestCase):
    def test_accepts_skips_only_for_scopes_classified_as_not_required(self):
        self.assertEqual(validate_results(passing_values()), [])

    def test_rejects_a_required_job_that_was_skipped_or_missing(self):
        for result in ("skipped", ""):
            with self.subTest(result=result):
                values = passing_values()
                values["FRONTEND_RESULT"] = result
                self.assertTrue(any("frontend" in error for error in validate_results(values)))

    def test_rejects_any_failed_job_even_if_not_classified_as_required(self):
        values = passing_values()
        values["BACKEND_RESULT"] = "failure"
        self.assertTrue(any("backend" in error for error in validate_results(values)))

    def test_rejects_classifier_failure_and_unknown_scope(self):
        values = passing_values()
        values["CI_SCOPE_RESULT"] = "failure"
        values["GEMMA_REQUIRED"] = "unknown"
        errors = validate_results(values)
        self.assertTrue(any("classifier" in error for error in errors))
        self.assertTrue(any("gemma" in error for error in errors))

    def test_rejects_missing_openspec_or_gitleaks(self):
        for check in ("OPENSPEC_RESULT", "GITLEAKS_RESULT"):
            with self.subTest(check=check):
                values = passing_values()
                values[check] = "skipped"
                self.assertTrue(any(check.lower().replace("_result", "") in error for error in validate_results(values)))


if __name__ == "__main__":
    unittest.main()
