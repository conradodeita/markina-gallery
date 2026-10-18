import json
import os
import shutil
import subprocess
import sys
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
            git("config", "maintenance.auto", "false")
            git("config", "gc.auto", "0")
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

    def test_cli_uses_deployed_baseline_and_exports_it_to_app_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                       GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")

            def git(*args):
                return subprocess.run(["git", *args], cwd=root, env=env, check=True,
                                      capture_output=True, text=True).stdout.strip()

            def commit():
                git("add", ".")
                git("commit", "-qm", "fixture")
                return git("rev-parse", "HEAD")

            git("init", "-q")
            (root / "backend/app").mkdir(parents=True)
            (root / "backend/app/main.py").write_text("existing app\n", encoding="utf-8")
            auth = root / "backend/app/auth.py"
            auth.write_text("previous OTP\n", encoding="utf-8")
            previous_main = commit()
            auth.write_text("already deployed OTP fix\n", encoding="utf-8")
            baseline = commit()
            manifest = root / "openspec/changes/add-production-app-release-workflow/runtime-gates.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({"production_baseline_sha": baseline,
                                           "expected_database_revision": "20261017_0084"}), encoding="utf-8")
            (root / "scripts").mkdir()
            shutil.copyfile(Path(__file__).with_name("classify_prod_release.py"), root / "scripts/classify_prod_release.py")
            commit()
            output = root / ".git/github-output"
            cli_env = dict(env, GITHUB_OUTPUT=str(output))

            def classify_cli():
                output.write_text("", encoding="utf-8")
                result = subprocess.run([sys.executable, "scripts/classify_prod_release.py", "--base", previous_main,
                                         "--target", "HEAD"], cwd=root, env=cli_env, check=False, capture_output=True, text=True)
                return result, output.read_text(encoding="utf-8")

            result, outputs = classify_cli()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("release_scope=none", outputs)
            self.assertIn(f"base_sha={baseline}", outputs)
            (root / "backend/app/main.py").write_text("new app feature\n", encoding="utf-8")
            commit()
            result, outputs = classify_cli()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("release_scope=app", outputs)
            self.assertIn(f"base_sha={baseline}", outputs)
            auth.write_text("new facial/auth change\n", encoding="utf-8")
            commit()
            result, outputs = classify_cli()
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("release_scope=mixed", outputs)

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
