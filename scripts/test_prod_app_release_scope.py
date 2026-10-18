"""Regression coverage for strict API/web-only production scope."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import check_prod_app_release_scope as policy


class AppReleaseScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_git("init", "-q")
        for name in policy.RUNTIME_FILES | policy.RETIRED_STATISTICS_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("approved runtime\n", encoding="utf-8")
        self.commit()
        self.base = self.run_git("rev-parse", "HEAD")
        self.manifest = {"runtime_blobs": {name: self.run_git("rev-parse", f"HEAD:{name}") for name in policy.RUNTIME_FILES}}

    def run_git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        return subprocess.run(["git", *args], cwd=self.root, env=env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self):
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "fixture")

    def test_runtime_blobs_must_match_and_non_runtime_docs_are_allowed(self):
        doc = self.root / "openspec/change.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("spec\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest), (True, "somente_api_web"))

    def test_release_classifier_and_its_test_are_allowed_policy_files(self):
        for name in ("scripts/classify_prod_release.py", "scripts/test_classify_prod_release.py"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("classification policy\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))

    def test_exact_release_coordination_scripts_are_allowed(self):
        names = (
            "scripts/deploy-prod-lock.sh",
            "scripts/deploy-prod-web.sh",
            "scripts/test_deploy_prod_web.sh",
            "scripts/test_deploy_prod_web_policy.py",
        )
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("reviewed release coordination\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))

    def test_unlisted_release_coordination_script_is_rejected(self):
        path = self.root / "scripts/deploy-prod-unreviewed.sh"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("unreviewed operation\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))

    def test_docker_monitor_worker_migration_and_unlisted_runtime_are_rejected(self):
        for name in ("docker/docker-compose.yml", "backend/app/system_monitor.py",
                     "backend/app/face_worker.py", "backend/migrations/versions/change.py",
                     "backend/app/facial/reference.py", "backend/app/unlisted.py"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("out of scope\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))

    def test_runtime_change_requires_exact_manifest_blob(self):
        path = self.root / "backend/app/main.py"
        path.write_text("unreviewed runtime\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "runtime_diverge_do_blob_aprovado"))

    def test_retired_statistics_pages_are_exactly_allowlisted_and_removed_from_runtime_manifest(self):
        self.assertNotIn("frontend/app/admin/statistics/page.tsx", policy.RUNTIME_FILES)
        self.assertEqual(policy.RETIRED_STATISTICS_FILES, {
            "frontend/app/admin/statistics/page.tsx",
            "frontend/app/admin/statistics/page.test.tsx",
        })
        for name in policy.RETIRED_STATISTICS_FILES:
            (self.root / name).unlink()
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))

    def test_unlisted_statistics_path_remains_out_of_scope(self):
        path = self.root / "frontend/app/admin/statistics/unreviewed.tsx"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("unreviewed\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))

    def test_exact_gallery_feature_tests_are_allowed(self):
        for name in ("frontend/app/admin/galleries/gallery-editor.test.tsx",
                     "frontend/app/admin/galleries/private-folder-client-overview.test.tsx"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test contract\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))

    def test_unlisted_gallery_runtime_is_rejected(self):
        path = self.root / "frontend/app/admin/galleries/unreviewed.tsx"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("unreviewed\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))


if __name__ == "__main__":
    unittest.main()
