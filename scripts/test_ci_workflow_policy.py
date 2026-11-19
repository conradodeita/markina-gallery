"""Guard CI concurrency, required check names, and the retired homolog target."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CI = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
EVIDENCE_POLICY = (ROOT / "scripts" / "verify_main_ci_evidence.py").read_text(encoding="utf-8")


class CIWorkflowPolicyTests(unittest.TestCase):
    def test_pr_cancellation_is_scoped_to_the_same_pr(self):
        header = CI.split("jobs:\n", 1)[0]
        self.assertIn("pull_request:", header)
        self.assertIn("workflow_dispatch:", header)
        self.assertIn("group: ci-${{ github.event.pull_request.number || github.run_id }}", header)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", header)
        self.assertEqual(1, header.count("cancel-in-progress:"))

    def test_non_pr_push_and_dispatch_still_classify_full(self):
        scope = CI.split("  ci-scope:\n", 1)[1].split("\n  backend-quality:\n", 1)[0]
        self.assertIn("if [[ \"$EVENT_NAME\" == \"pull_request\" ]]", scope)
        self.assertIn("python scripts/classify_ci_scope.py --full", scope)

    def test_backend_matrix_and_aggregation_use_four_shards(self):
        shards = CI.split("  backend-tests:\n", 1)[1].split("\n  backend:\n", 1)[0]
        self.assertIn("shard: [0, 1, 2, 3]", shards)
        self.assertIn("--count 4", shards)
        self.assertIn("backend_ci.py verify --count 4", CI)
        for index in range(4):
            self.assertIn(f"'backend-tests ({index})'", EVIDENCE_POLICY)

    def test_required_aggregate_contexts_and_production_environments_remain(self):
        for job in ("backend", "frontend", "openspec", "homolog-inventory-policy",
                    "gemma-runtime", "gitleaks"):
            with self.subTest(job=job):
                self.assertRegex(CI, rf"(?m)^  {re.escape(job)}:")
        self.assertIn("needs: [homolog-inventory-policy]", CI)
        self.assertIn("environment: production", CI)
        self.assertIn("approval_fingerprint", CI)

    def test_no_active_workflow_targets_the_removed_homolog_environment(self):
        workflow_files = [path for path in WORKFLOWS.iterdir()
                          if path.suffix in {".yml", ".yaml"}]
        self.assertFalse([path.name for path in workflow_files
                          if "homolog" in path.stem.lower()])
        for path in workflow_files:
            text = path.read_text(encoding="utf-8")
            with self.subTest(workflow=path.name):
                self.assertNotRegex(text, r"(?m)^\s+environment:\s*homolog\s*$")
                self.assertNotIn("secrets.HOMOLOG_SSH_", text)
        self.assertNotRegex(CI, r"(?m)^  deploy-homolog:")


if __name__ == "__main__":
    unittest.main()
