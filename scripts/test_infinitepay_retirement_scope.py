"""Fail-closed scope policy tests for InfinitePay retirement."""

import unittest

from check_infinitepay_retirement_scope import evaluate


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


if __name__ == "__main__":
    unittest.main()
