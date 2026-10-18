import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from classify_prod_release import (
    APP_RUNTIME,
    FACIAL_RUNTIME,
    classify,
    classify_from_baseline,
    git_is_ancestor,
    production_baseline_from_manifest,
)


class ReleaseClassifierTests(unittest.TestCase):
    def test_application_only(self):
        self.assertEqual(classify(set(APP_RUNTIME)), "app")

    def test_private_folder_owner_runtime_uses_app_gate(self):
        self.assertEqual(
            classify({
                "backend/app/private_folder_overview.py",
                "frontend/app/admin/galleries/private-folder-client-overview.tsx",
                "frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx",
            }),
            "app",
        )

    def test_unreconciled_main_history_does_not_trigger_release(self):
        self.assertEqual(classify_from_baseline(set(APP_RUNTIME), baseline_is_ancestor=False), "none")

    def test_baseline_reconciliation_without_runtime_changes_does_not_trigger_release(self):
        self.assertEqual(classify_from_baseline({"openspec/release-baseline.json"}, baseline_is_ancestor=True), "none")

    def test_app_delta_after_baseline_triggers_only_app_gate(self):
        self.assertEqual(classify_from_baseline({"backend/app/private_folder_overview.py"}, baseline_is_ancestor=True), "app")

    def test_production_baseline_requires_full_sha_and_alembic_revision(self):
        manifest = {
            "production_baseline_sha": "b4f15abd6a71585082758062feba7fcfcc225587",
            "expected_database_revision": "20261017_0084",
        }
        self.assertEqual(production_baseline_from_manifest(manifest), manifest["production_baseline_sha"])
        manifest["expected_database_revision"] = "20261017_008"
        with self.assertRaises(ValueError):
            production_baseline_from_manifest(manifest)

    def test_git_ancestry_is_checked_against_real_commit_graph(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                           GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
                return subprocess.run(["git", *args], cwd=root, env=env, check=True,
                                      capture_output=True, text=True).stdout.strip()

            git("init", "-q")
            (root / "fixture").write_text("baseline\n", encoding="utf-8")
            git("add", "fixture")
            git("commit", "-qm", "baseline")
            baseline = git("rev-parse", "HEAD")
            (root / "fixture").write_text("candidate\n", encoding="utf-8")
            git("commit", "-qam", "candidate")
            target = git("rev-parse", "HEAD")
            self.assertTrue(git_is_ancestor(baseline, target, root=root))
            self.assertFalse(git_is_ancestor(target, baseline, root=root))

    def test_facial_only(self):
        self.assertEqual(classify(set(FACIAL_RUNTIME)), "facial")

    def test_mixed_is_distinct(self):
        self.assertEqual(classify({"backend/app/statistics_report.py", "backend/app/facial/search.py"}), "mixed")

    def test_operations_only_does_not_trigger_release(self):
        self.assertEqual(classify({"docs/DEPLOY-PROD-APP.md", ".github/workflows/ci.yml"}), "none")

    def test_reference_results_and_compose_use_facial_gate(self):
        for path in (
            "frontend/app/gallery-presentation.tsx",
            "frontend/app/public-galleries/[galleryId]/page.tsx",
            "docker/docker-compose.yml",
        ):
            with self.subTest(path=path):
                self.assertEqual(classify({path}), "facial")


if __name__ == "__main__":
    unittest.main()
