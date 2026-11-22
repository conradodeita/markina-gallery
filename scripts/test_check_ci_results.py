import re
import unittest
from pathlib import Path

from scripts.check_ci_results import validate_results


def passing_values():
    return {
        "CI_SCOPE_RESULT": "success",
        "BACKEND_REQUIRED": "false",
        "BACKEND_RESULT": "skipped",
        "FRONTEND_REQUIRED": "true",
        "FRONTEND_RESULT": "success",
        "RUNTIME_IMAGES_REQUIRED": "false",
        "RUNTIME_IMAGES_RESULT": "skipped",
        "OPENSPEC_RESULT": "success",
        "GITLEAKS_RESULT": "success",
    }


class CheckCIResultsTests(unittest.TestCase):
    def test_legacy_gemma_branch_protection_context_only_mirrors_current_aggregate(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        alias = workflow.split("  gemma-runtime:\n", 1)[1].split("\n  gitleaks:", 1)[0]
        self.assertIn("needs: [homolog-inventory-policy]", alias)
        self.assertIn("if: ${{ always() }}", alias)
        self.assertIn("${{ needs.homolog-inventory-policy.result }}", alias)
        self.assertIn('!= "success"', alias)
        self.assertIn("exit 1", alias)
        self.assertNotIn("docker build", alias)
        self.assertNotIn("pip install", alias)

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
        errors = validate_results(values)
        self.assertTrue(any("classifier" in error for error in errors))

    def test_rejects_missing_openspec_or_gitleaks(self):
        for check in ("OPENSPEC_RESULT", "GITLEAKS_RESULT"):
            with self.subTest(check=check):
                values = passing_values()
                values[check] = "skipped"
                self.assertTrue(any(check.lower().replace("_result", "") in error for error in validate_results(values)))

    def test_native_image_matrix_remains_a_required_aggregate(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        images = workflow.split("  runtime-images:\n", 1)[1].split("\n  openspec:", 1)[0]
        pairs = set(re.findall(r"runner: ([\w.-]+)\s+arch: (amd64|arm64)", images))
        self.assertEqual(pairs, {("ubuntu-latest", "amd64"), ("ubuntu-24.04-arm", "arm64")})
        self.assertIn("runs-on: ${{ matrix.runner }}", images)
        self.assertIn("fail-fast: false", images)
        self.assertIn("amd64:x86_64|arm64:aarch64", images)
        self.assertNotIn("setup-qemu-action", images)
        self.assertIn("RUNTIME_IMAGES_RESULT: ${{ needs.runtime-images.result }}", workflow)
        for result in ("failure", "cancelled", "skipped", ""):
            with self.subTest(result=result):
                values = passing_values() | {"RUNTIME_IMAGES_REQUIRED": "true", "RUNTIME_IMAGES_RESULT": result}
                self.assertTrue(any("runtime-images" in error for error in validate_results(values)))


if __name__ == "__main__":
    unittest.main()
