import unittest

from classify_prod_release import APP_RUNTIME, FACIAL_RUNTIME, classify


class ReleaseClassifierTests(unittest.TestCase):
    def test_application_only(self):
        self.assertEqual(classify(set(APP_RUNTIME)), "app")

    def test_facial_only(self):
        self.assertEqual(classify(set(FACIAL_RUNTIME)), "facial")

    def test_mixed_is_distinct(self):
        self.assertEqual(classify({"backend/app/statistics_report.py", "backend/app/facial/search.py"}), "mixed")

    def test_operations_only_does_not_trigger_release(self):
        self.assertEqual(classify({"docs/DEPLOY-PROD-APP.md", ".github/workflows/ci.yml"}), "none")


if __name__ == "__main__":
    unittest.main()
