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
        for name in policy.RUNTIME_FILES:
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


if __name__ == "__main__":
    unittest.main()
