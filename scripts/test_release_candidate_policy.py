"""Real Git and release verifier: technical CI must preserve publication refusal."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import check_prod_app_release_scope as app_policy
from check_prod_app_release_scope import RUNTIME_FILES, evaluate
from test_production_release_workflow_policy import release_candidate_snapshot


class ReleaseCandidatePolicyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git("init", "-q")
        self.git("config", "maintenance.auto", "false")
        self.git("config", "gc.auto", "0")
        for path in RUNTIME_FILES:
            content = (
                "      - path: ${INFINITEPAY_BINDINGS_ENV_FILE:-.env.infinitepay-bindings}\n"
                "        required: false\n"
                "        format: raw\n"
                if path == "docker/docker-compose.yml" else "reviewed runtime\n"
            )
            self.write(path, content)
        for path in app_policy.RETIRED_INFINITEPAY_FILES:
            self.write(path, "legacy InfinitePay runtime\n")
        self.commit()
        self.base = self.git("rev-parse", "HEAD")
        self.manifest = {"production_baseline_sha": self.base,
                         "runtime_blobs": {p: self.git("rev-parse", f"HEAD:{p}") for p in RUNTIME_FILES}}
        self.path = "openspec/changes/add-production-app-release-workflow/runtime-gates.json"
        self.write(self.path, json.dumps(self.manifest))
        self.commit()
        self.source = self.git("rev-parse", "HEAD")

    def git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        return subprocess.check_output(["git", *args], cwd=self.root, env=env, text=True).strip()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "synthetic release policy fixture")

    def test_exact_snapshot_remains_a_positive_case(self):
        self.assertEqual(release_candidate_snapshot(self.root, self.manifest),
                         (self.source, True, "somente_api_web"))

    def test_documentation_descendant_preserves_snapshot_and_admission(self):
        self.write("openspec/continuity.md", "documented evidence\n")
        self.commit()
        self.assertEqual(release_candidate_snapshot(self.root, self.manifest),
                         (self.source, True, "somente_api_web"))

    def test_migration_head_passes_technical_contract_only_if_publication_is_refused(self):
        self.write("backend/migrations/versions/new_vault.py", "protected schema\n")
        self.commit()
        self.assertEqual(evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))
        self.assertEqual(release_candidate_snapshot(self.root, self.manifest),
                         (self.source, False, "arquivo_fora_do_escopo"))

    def test_unreviewed_app_blob_still_fails_technical_contract(self):
        self.write("backend/app/payment_availability.py", "unreviewed runtime\n")
        self.commit()
        with self.assertRaisesRegex(AssertionError, "recusa protegida"):
            release_candidate_snapshot(self.root, self.manifest)

    def test_manifest_cannot_turn_migration_into_positive_snapshot(self):
        self.write("backend/migrations/versions/new_vault.py", "protected schema\n")
        self.manifest["note"] = "attempted scope expansion"
        self.write(self.path, json.dumps(self.manifest))
        self.commit()
        with self.assertRaisesRegex(AssertionError, "snapshot do manifesto"):
            release_candidate_snapshot(self.root, self.manifest)

    def test_runtime_pin_adulteration_in_manifest_still_fails(self):
        self.manifest["runtime_blobs"]["backend/app/payment_availability.py"] = "a" * 40
        self.write(self.path, json.dumps(self.manifest))
        self.commit()
        with self.assertRaisesRegex(AssertionError, "snapshot do manifesto"):
            release_candidate_snapshot(self.root, self.manifest)

    def test_manifest_can_pin_exact_infinitepay_retirement_snapshot(self):
        for path in app_policy.RETIRED_INFINITEPAY_FILES:
            (self.root / path).unlink()
        self.write("docker/docker-compose.yml", "")
        migration = "backend/migrations/versions/20261022_0087_retire_infinitepay.py"
        self.write(migration, "retirement migration\n")
        self.manifest["runtime_blobs"] = {
            path: self.git("hash-object", str(self.root / path)) for path in RUNTIME_FILES
        }
        self.write(self.path, json.dumps(self.manifest))
        self.commit()

        source, ready, reason = release_candidate_snapshot(self.root, self.manifest)
        self.assertEqual(source, self.git("rev-parse", "HEAD"))
        self.assertFalse(ready)
        self.assertEqual(reason, "arquivo_fora_do_escopo")

    def test_uncommitted_or_foreign_manifest_is_not_trusted(self):
        changed = dict(self.manifest, note="uncommitted proposal")
        with self.assertRaisesRegex(AssertionError, "manifesto diverge"):
            release_candidate_snapshot(self.root, changed)


if __name__ == "__main__":
    unittest.main()
