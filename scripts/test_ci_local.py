"""Contracts for the local fast-feedback command."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.ci_local import changed_paths, plan_checks


class LocalCIFeedbackTests(unittest.TestCase):
    def test_changed_paths_includes_branch_diff_and_all_worktree_states(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                subprocess.run(["git", *args], cwd=root, check=True,
                               capture_output=True, text=True)

            git("init", "--quiet", "-b", "main")
            git("config", "user.name", "CI fixture")
            git("config", "user.email", "ci-fixture@example.test")
            (root / "base.py").write_text("value = 1\n", encoding="utf-8")
            git("add", "base.py")
            git("commit", "--quiet", "-m", "base")
            git("checkout", "--quiet", "-b", "feature")
            (root / "committed.py").write_text("value = 2\n", encoding="utf-8")
            git("add", "committed.py")
            git("commit", "--quiet", "-m", "feature")
            (root / "base.py").write_text("value = 3\n", encoding="utf-8")
            (root / "staged.py").write_text("value = 4\n", encoding="utf-8")
            git("add", "staged.py")
            (root / "untracked.py").write_text("value = 5\n", encoding="utf-8")

            self.assertEqual(
                ["base.py", "committed.py", "staged.py", "untracked.py"],
                changed_paths("main", root),
            )

    def test_isolated_feedback_tool_runs_focused_contracts_without_product_shards(self):
        checks, pending = plan_checks(["scripts/ci_feedback.py", "scripts/test_ci_feedback.py"])
        commands = [check.command for check in checks]
        self.assertTrue(any("scripts.test_ci_feedback" in command for command in commands))
        self.assertTrue(any(command[:2] == ("ruff", "check") for command in commands))
        self.assertFalse(any("backend/tests" in command for command in commands))
        self.assertFalse(any("suíte completa backend" in item for item in pending))

    def test_backend_change_runs_fast_lint_and_keeps_full_suite_mandatory(self):
        checks, pending = plan_checks(["backend/app/auth/session.py"])
        commands = [check.command for check in checks]
        self.assertIn(("ruff", "check", "backend/app", "backend/tests"), commands)
        self.assertTrue(any("suíte completa backend" in item for item in pending))

    def test_mixed_frontend_and_backend_selects_both_lints_and_all_remaining_gates(self):
        checks, pending = plan_checks([
            "frontend/app/gallery/page.tsx", "backend/app/payments/provider.py",
        ])
        commands = [check.command for check in checks]
        self.assertIn(("npm", "run", "lint", "--prefix", "frontend"), commands)
        self.assertIn(("ruff", "check", "backend/app", "backend/tests"), commands)
        self.assertTrue(any("suíte completa backend" in item for item in pending))
        self.assertTrue(any("testes e build do frontend" in item for item in pending))

    def test_openspec_change_runs_only_its_strict_validation(self):
        checks, _ = plan_checks(["openspec/changes/optimize-ci-feedback-cycle/tasks.md"])
        self.assertEqual(1, len(checks))
        self.assertIn("validate", checks[0].command)
        self.assertIn("optimize-ci-feedback-cycle", checks[0].command)
        self.assertIn("--strict", checks[0].command)

    def test_unknown_top_level_path_fails_open_to_full_ci(self):
        _checks, pending = plan_checks(["new-worker/runtime.py"])
        self.assertTrue(any("suíte completa backend" in item for item in pending))
        self.assertTrue(any("testes e build do frontend" in item for item in pending))
        self.assertTrue(any("build de imagem" in item for item in pending))


if __name__ == "__main__":
    unittest.main()
