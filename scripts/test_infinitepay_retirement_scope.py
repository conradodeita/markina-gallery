"""Fail-closed scope policy tests for InfinitePay retirement."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from check_infinitepay_retirement_scope import evaluate, evaluate_followup_scope


class RetirementScopeTests(unittest.TestCase):
    COMPOSE_DIFF = """diff --git a/docker/docker-compose.yml b/docker/docker-compose.yml
--- a/docker/docker-compose.yml
+++ b/docker/docker-compose.yml
@@ -102,3 +101,0 @@ services:
-      - path: ${INFINITEPAY_BINDINGS_ENV_FILE:-.env.infinitepay-bindings}
-        required: false
-        format: raw
"""

    def valid_paths(self):
        return {
            "backend/migrations/versions/20261022_0087_retire_infinitepay.py",
            "docker/docker-compose.yml",
            "backend/app/main.py",
            "frontend/app/library/cart/page.tsx",
        }

    def test_exact_retirement_runtime_is_accepted(self):
        ready, reason = evaluate(self.valid_paths(), self.COMPOSE_DIFF)
        self.assertTrue(ready)
        self.assertEqual(reason, "somente_aposentadoria_infinitepay")

    def test_any_second_migration_is_rejected(self):
        paths = self.valid_paths() | {"backend/migrations/versions/20261023_0088_unrelated.py"}
        self.assertEqual(evaluate(paths, self.COMPOSE_DIFF), (False, "migration_fora_do_escopo"))

    def test_unreviewed_runtime_or_infrastructure_is_rejected(self):
        for path in ("backend/app/unreviewed.py", "docker/.env", "docker-compose.yml"):
            with self.subTest(path=path):
                self.assertEqual(evaluate(self.valid_paths() | {path}, self.COMPOSE_DIFF),
                                 (False, "arquivo_fora_do_escopo"))

    def test_compose_change_must_only_remove_the_infinitepay_env_file(self):
        extra_service = self.COMPOSE_DIFF + "+  new-service:\n+    image: unreviewed\n"
        self.assertEqual(evaluate(self.valid_paths(), extra_service), (False, "compose_fora_do_escopo"))
        changed_other_env_file = self.COMPOSE_DIFF.replace(
            "INFINITEPAY_BINDINGS_ENV_FILE", "OTHER_PROVIDER_BINDINGS_ENV_FILE")
        self.assertEqual(evaluate(self.valid_paths(), changed_other_env_file),
                         (False, "compose_fora_do_escopo"))

    def test_migration_and_compose_are_required(self):
        paths = self.valid_paths() - {"backend/migrations/versions/20261022_0087_retire_infinitepay.py"}
        self.assertEqual(evaluate(paths, self.COMPOSE_DIFF), (False, "migration_0087_ausente"))
        paths = self.valid_paths() - {"docker/docker-compose.yml"}
        self.assertEqual(evaluate(paths, ""), (False, "compose_sem_remocao_do_binding"))

    def test_unlisted_docs_and_tests_are_rejected(self):
        for path in ("docs/unreviewed-plan.md", "backend/tests/unreviewed.py", "openspec/random.md"):
            with self.subTest(path=path):
                self.assertEqual(evaluate(self.valid_paths() | {path}, self.COMPOSE_DIFF),
                                 (False, "arquivo_fora_do_escopo"))

    def test_exact_gate_followup_is_allowed_only_after_retirement_is_in_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Fixture")
            self.git(root, "config", "user.email", "fixture@example.invalid")
            self.write(root, "backend/migrations/versions/20261022_0087_retire_infinitepay.py", "reviewed migration\n")
            self.write(root, "docker/docker-compose.yml", "services:\n  api:\n    image: api\n")
            self.commit(root)
            base = self.git(root, "rev-parse", "HEAD")
            for path in (
                "scripts/check_prod_app_release_scope.py",
                ".github/workflows/ci.yml",
                "scripts/test_production_release_workflow_policy.py",
                "scripts/validate_retirement_approval.py",
                "scripts/test_retirement_approval.py",
                "openspec/changes/release-infinitepay-retirement-prod/proposal.md",
                "openspec/changes/release-infinitepay-retirement-prod/design.md",
                "openspec/changes/release-infinitepay-retirement-prod/specs/deployment-operations/spec.md",
                "openspec/changes/release-infinitepay-retirement-prod/tasks.md",
            ):
                self.write(root, path, "reviewed gate update\n")
            self.commit(root)
            target = self.git(root, "rev-parse", "HEAD")
            self.assertEqual(evaluate_followup_scope(root, base, target),
                             (True, "ajuste_gate_pos_integracao"))

            self.write(root, "backend/app/main.py", "unreviewed runtime\n")
            self.commit(root)
            self.assertEqual(evaluate_followup_scope(root, target, "HEAD"),
                             (False, "ajuste_pos_integracao_fora_do_escopo"))

    def test_gate_followup_is_rejected_if_binding_reference_remains_in_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Fixture")
            self.git(root, "config", "user.email", "fixture@example.invalid")
            self.write(root, "backend/migrations/versions/20261022_0087_retire_infinitepay.py", "reviewed migration\n")
            self.write(root, "docker/docker-compose.yml", "INFINITEPAY_BINDINGS_ENV_FILE\n")
            self.commit(root)
            base = self.git(root, "rev-parse", "HEAD")
            self.write(root, "scripts/check_prod_app_release_scope.py", "reviewed gate update\n")
            self.commit(root)
            self.assertEqual(evaluate_followup_scope(root, base, "HEAD"),
                             (False, "binding_ainda_referenciado_na_base"))

    @staticmethod
    def git(root, *args):
        return subprocess.check_output(["git", *args], cwd=root, text=True,
                                       env=dict(os.environ, GIT_TERMINAL_PROMPT="0")).strip()

    @classmethod
    def write(cls, root, name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @classmethod
    def commit(cls, root):
        cls.git(root, "add", ".")
        cls.git(root, "commit", "-qm", "fixture")


if __name__ == "__main__":
    unittest.main()
