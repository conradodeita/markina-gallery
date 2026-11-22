from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_preview_adjustment_migration_scope import (
    ALLOWED_CANDIDATE_PATHS,
    BASE_REVISION,
    BASE_SHA,
    CANDIDATE_SHA,
    MIGRATION,
    TARGET_REVISION,
    evaluate,
)


VALID_MIGRATION = f'revision = "{TARGET_REVISION}"\ndown_revision = "{BASE_REVISION}"\n'


class PreviewAdjustmentMigrationScopeTests(unittest.TestCase):
    def test_exact_candidate_and_diff_are_accepted(self):
        self.assertEqual(evaluate(ALLOWED_CANDIDATE_PATHS, BASE_SHA, CANDIDATE_SHA,
                                  "success", VALID_MIGRATION),
                         (True, "migration_preview_adjustment_0090_aprovada"))

    def test_rejects_divergent_sha_ci_and_main_membership(self):
        cases = (
            (BASE_SHA[:-1] + "0", CANDIDATE_SHA, "success", True, "baseline_sha_divergente"),
            (BASE_SHA, CANDIDATE_SHA[:-1] + "0", "success", True, "candidato_sha_divergente"),
            (BASE_SHA, CANDIDATE_SHA, "failure", True, "ci_nao_verde"),
            (BASE_SHA, CANDIDATE_SHA, "success", False, "candidato_nao_integrado_a_main"),
        )
        for base, target, ci, on_main, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(evaluate(ALLOWED_CANDIDATE_PATHS, base, target, ci,
                                          VALID_MIGRATION, on_main), (False, reason))

    def test_rejects_pr_295_css_and_any_unlisted_path(self):
        for path in ("frontend/app/admin/payments/unreviewed.css",
                     "backend/migrations/versions/extra.py"):
            with self.subTest(path=path):
                self.assertEqual(evaluate(ALLOWED_CANDIDATE_PATHS | {path}, BASE_SHA,
                                          CANDIDATE_SHA, "success", VALID_MIGRATION),
                                 (False, "diff_fora_da_allowlist"))

    def test_rejects_missing_migration_or_broken_alembic_chain(self):
        self.assertEqual(evaluate(ALLOWED_CANDIDATE_PATHS - {MIGRATION}, BASE_SHA,
                                  CANDIDATE_SHA, "success", VALID_MIGRATION),
                         (False, "diff_fora_da_allowlist"))
        self.assertEqual(evaluate(ALLOWED_CANDIDATE_PATHS, BASE_SHA, CANDIDATE_SHA,
                                  "success", f'revision = "{TARGET_REVISION}"\ndown_revision = "wrong"\n'),
                         (False, "cadeia_alembic_divergente"))


if __name__ == "__main__":
    unittest.main()
