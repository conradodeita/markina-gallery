"""Regression coverage for strict API/web-only production scope."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_prod_app_release_scope as policy


class AppReleaseScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_git("init", "-q")
        # Git recente destaca maintenance em background até em fixtures pequenas.
        # Nenhum processo deve continuar escrevendo depois do cleanup do teste.
        self.run_git("config", "maintenance.auto", "false")
        self.run_git("config", "gc.auto", "0")
        for name in policy.RUNTIME_FILES | policy.RETIRED_STATISTICS_FILES | policy.RETIRED_INFINITEPAY_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("approved runtime\n", encoding="utf-8")
        self.commit()
        self.base = self.run_git("rev-parse", "HEAD")
        self.manifest = {"runtime_blobs": {name: self.run_git("rev-parse", f"HEAD:{name}") for name in policy.RUNTIME_FILES}}

    def run_git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        result = subprocess.run(["git", *args], cwd=self.root, env=env, check=True,
                                capture_output=True, text=True)
        self.last_git_stderr = result.stderr
        return result.stdout.strip()

    def test_fixture_does_not_start_background_maintenance(self):
        (self.root / "fixture-change").write_text("isolated fixture\n", encoding="utf-8")
        self.run_git("add", "fixture-change")
        with patch.dict(os.environ, {"GIT_TRACE": "1"}):
            self.run_git("commit", "-qm", "fixture without detached processes")
        self.assertNotIn("maintenance run", self.last_git_stderr)
        self.assertEqual(self.run_git("config", "--bool", "maintenance.auto"), "false")
        self.assertEqual(self.run_git("config", "--get", "gc.auto"), "0")

    def commit(self):
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "fixture")

    def test_runtime_blobs_must_match_and_non_runtime_docs_are_allowed(self):
        doc = self.root / "openspec/change.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("spec\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest), (True, "somente_api_web"))

    def test_handoff_support_is_exactly_allowlisted_without_worker_or_workflow_wildcard(self):
        names = {'.github/workflows/production-app-handoff-recovery.yml'} | {
            'scripts/test_production_app_handoff_' + suffix + '.py'
            for suffix in ('inventory', 'journal', 'execution', 'recovery', 'engine', 'cli', 'legacy', 'shell')
        } | {'scripts/test_production_app_first_handoff.py'}
        for name in names:
            self.assertIn(name, policy.ALLOWED_OPERATIONS)
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('reviewed operational support\n', encoding='utf-8')
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, 'HEAD', self.manifest), (True, 'somente_api_web'))
        for name in ('.github/workflows/production-app-handoff-arbitrary.yml',
                     'scripts/test_production_app_handoff_unreviewed.py'):
            path = self.root / name
            path.write_text('unreviewed behavior\n', encoding='utf-8')
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, 'HEAD', self.manifest), (False, 'arquivo_fora_do_escopo'))

    def test_platform_backup_runtime_requires_exact_reviewed_blob_and_worker_scope(self):
        name = "backend/app/platform_backup/runtime_worker.py"
        path = self.root / name
        path.write_text("reviewed but changed backup runtime\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "runtime_diverge_do_blob_aprovado"))
        self.manifest["runtime_blobs"][name] = self.run_git("rev-parse", f"HEAD:{name}")
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))
        unreviewed = self.root / "backend/app/platform_backup/unreviewed_worker.py"
        unreviewed.write_text("unreviewed worker\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))

    def test_backup_support_files_require_exact_set_and_pins(self):
        for name in policy.BACKUP_SUPPORT_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("reviewed backup support\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "manifesto_suporte_backup_incompleto"))
        self.manifest["support_blobs"] = {
            name: self.run_git("rev-parse", f"HEAD:{name}") for name in policy.BACKUP_SUPPORT_FILES
        }
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))
        changed = next(iter(policy.BACKUP_SUPPORT_FILES))
        (self.root / changed).write_text("different support content\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "suporte_backup_diverge_do_blob_aprovado"))

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
            ".github/workflows/production-app-runtime-adoption.yml",
            ".github/workflows/production-app-compose-bridge-install.yml",
            "scripts/verify_main_ci_evidence.py",
            "scripts/test_verify_main_ci_evidence.py",
            "scripts/production_app_compose_bridge.py",
            "scripts/test_production_app_compose_bridge.py",
            "scripts/install-prod-app-compose-bridge.sh",
            "scripts/deploy-prod-lock.sh",
            "scripts/deploy-prod-state.sh",
            "scripts/export_prod_app_api_base_image.sh",
            "scripts/production-app-artifact-ssh-wrapper.sh",
            "scripts/production_app_artifact.py",
            "scripts/test_prod_app_api_base_image_export.py",
            "scripts/test_production_app_artifact.py",
            "scripts/test_production_app_artifact_ssh_wrapper.py",
            "scripts/test_prod_release_state.py",
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

    def test_exact_scanner_metadata_is_allowed_but_similar_unlisted_file_is_rejected(self):
        (self.root / ".gitleaksignore").write_text("immutable non-secret fingerprint\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))
        (self.root / ".gitleaks-unreviewed").write_text("unreviewed exception\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))

    def test_docker_monitor_worker_migration_and_unlisted_runtime_are_rejected(self):
        path = self.root / "docker/docker-compose.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reviewed API secret env_file wiring\n", encoding="utf-8")
        for name in ("backend/app/system_monitor.py",
                     "backend/app/face_worker.py", "backend/migrations/versions/change.py",
                     "backend/app/facial/reference.py", "backend/app/unlisted.py"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("out of scope\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))

    def test_api_compose_secret_file_requires_exact_approved_runtime_blob(self):
        path = self.root / "docker/docker-compose.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("API-only secret env_file\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "runtime_diverge_do_blob_aprovado"))
        self.manifest["runtime_blobs"]["docker/docker-compose.yml"] = self.run_git(
            "rev-parse", "HEAD:docker/docker-compose.yml")
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))

    def test_runtime_change_requires_exact_manifest_blob(self):
        path = self.root / "backend/app/main.py"
        path.write_text("unreviewed runtime\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "runtime_diverge_do_blob_aprovado"))

    def test_retirement_migration_stays_outside_generic_api_web_release(self):
        name = "backend/migrations/versions/20261022_0087_retire_infinitepay.py"
        self.assertNotIn(name, policy.RUNTIME_FILES)
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("retirement migration\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))

    def test_only_deletion_of_exact_retired_infinitepay_files_is_admitted(self):
        for name in policy.RETIRED_INFINITEPAY_FILES:
            (self.root / name).unlink()
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))

        name = min(policy.RETIRED_INFINITEPAY_FILES)
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reintroduced InfinitePay behavior\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))

    def test_modification_of_retired_infinitepay_path_is_not_treated_as_removal(self):
        name = min(policy.RETIRED_INFINITEPAY_FILES)
        (self.root / name).write_text("modified retired behavior\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))

    def test_each_dependency_vault_and_migration_path_remains_rejected(self):
        for name in ("backend/requirements-push.txt", "backend/requirements.txt",
                     "backend/Dockerfile", "frontend/package.json", "frontend/package-lock.json",
                     "backend/migrations/versions/20261020_0085_infinitepay_credentials.py",
                     "backend/migrations/versions/20261021_0086_infinitepay_mixed_checkout.py"):
            with self.subTest(path=name):
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("outside emergency payment scope\n", encoding="utf-8")
                self.commit()
                self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                                 (False, "arquivo_fora_do_escopo"))
                path.unlink()
                self.commit()
        changed_runtime = self.root / "backend/app/main.py"
        changed_runtime.write_text("outside emergency payment scope\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "runtime_diverge_do_blob_aprovado"))

    def test_payment_history_and_cart_runtime_require_exact_reviewed_blobs(self):
        for name in (
            "backend/app/client_lifecycle.py", "backend/app/order_visibility.py",
            "backend/app/unified_checkout.py",
            "frontend/app/admin/galleries/[galleryId]/orders/page.tsx",
            "frontend/app/library/cart/page.tsx", "frontend/app/library/purchase-card.tsx",
            "frontend/app/library/purchases/page.tsx",
        ):
            with self.subTest(path=name):
                self.assertIn(name, policy.RUNTIME_FILES)
                (self.root / name).write_text("reviewed cart recovery runtime\n", encoding="utf-8")
                self.commit()
                self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                                 (False, "runtime_diverge_do_blob_aprovado"))
                self.manifest["runtime_blobs"][name] = self.run_git("rev-parse", f"HEAD:{name}")
                self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                                 (True, "somente_api_web"))

    def test_cart_page_requires_its_exact_blob_and_test_allowlist(self):
        name = "frontend/app/library/cart/page.tsx"
        self.assertIn(name, policy.RUNTIME_FILES)
        (self.root / name).write_text("PIX-only cart runtime\n", encoding="utf-8")
        test = self.root / "frontend/app/library/cart/cart.test.tsx"
        test.write_text("PIX cart contract\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "runtime_diverge_do_blob_aprovado"))
        self.manifest["runtime_blobs"][name] = self.run_git("rev-parse", f"HEAD:{name}")
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))
        (self.root / "frontend/app/library/cart/unreviewed.ts").write_text("unreviewed cart behavior\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))

    def test_cart_recovery_frontend_tests_are_exact_non_runtime_operations(self):
        for name in (
            "frontend/app/admin/galleries/[galleryId]/orders/orders.test.tsx",
            "frontend/app/library/cart/cart.test.tsx",
            "frontend/app/library/library.test.tsx",
        ):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("cart recovery regression\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))

    def test_service_baseline_cannot_hide_api_input_change(self):
        path = self.root / "backend/requirements-push.txt"
        path.write_text("four approved pins\n", encoding="utf-8")
        self.commit()
        self.manifest["emergency_api"] = {
            "baseline_sha": self.base,
            "input_blobs": {"backend/requirements-push.txt": self.run_git("rev-parse", "HEAD:backend/requirements-push.txt")},
        }
        web_base = self.run_git("rev-parse", "HEAD")
        self.assertEqual(policy.evaluate(self.root, web_base, "HEAD", self.manifest), (True, "somente_api_web"))
        path.write_text("unapproved dependency change\n", encoding="utf-8")
        self.commit()
        advanced_web = self.run_git("rev-parse", "HEAD")
        self.assertEqual(policy.evaluate(self.root, advanced_web, "HEAD", self.manifest),
                         (False, "runtime_diverge_do_blob_aprovado"))
        (self.root / "backend/app/auth.py").write_text("unapproved runtime\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, "HEAD", "HEAD", self.manifest),
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

    def test_approved_ci_optimization_paths_are_allowed(self):
        names = (
            ".env.example", "AGENTS.md", "DEPLOY.md", "README.md",
            "frontend/app/public-galleries/public-gallery.test.tsx",
            "scripts/backend_ci.py", "scripts/backend_ci_durations.json",
            "scripts/check_backend_ci_results.py", "scripts/ci_feedback.py",
            "scripts/ci_local.py", "scripts/classify_ci_scope.py", "scripts/resume-homolog.sh",
            "scripts/test_backend_ci.py", "scripts/test_check_backend_ci_results.py",
            "scripts/test_ci_feedback.py", "scripts/test_ci_local.py",
            "scripts/test_ci_workflow_policy.py", "scripts/test_classify_ci_scope.py",
            "scripts/test_resume_homolog_policy.py",
        )
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("approved operational file\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (True, "somente_api_web"))

    def test_retired_homolog_workflows_are_allowed_only_as_deletions(self):
        names = (
            ".github/workflows/facial-rollout-homolog.yml",
            ".github/workflows/inventory-homolog-readonly.yml",
            ".github/workflows/maintenance-homolog.yml",
        )
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("legacy workflow\n", encoding="utf-8")
        self.commit()
        legacy_base = self.run_git("rev-parse", "HEAD")
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))
        for name in names:
            (self.root / name).write_text("changed workflow\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, legacy_base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))
        for name in names:
            (self.root / name).unlink()
        self.commit()
        self.assertEqual(policy.evaluate(self.root, legacy_base, "HEAD", self.manifest),
                         (True, "somente_api_web"))

    def test_ci_allowlist_does_not_admit_unknown_scripts_or_environment(self):
        for name in ("scripts/unreviewed.py", ".env", "frontend/app/unreviewed.test.tsx"):
            with self.subTest(path=name):
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("unreviewed\n", encoding="utf-8")
                self.commit()
                self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                                 (False, "arquivo_fora_do_escopo"))
                path.unlink()
                self.commit()

    def test_unlisted_gallery_runtime_is_rejected(self):
        path = self.root / "frontend/app/admin/galleries/unreviewed.tsx"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("unreviewed\n", encoding="utf-8")
        self.commit()
        self.assertEqual(policy.evaluate(self.root, self.base, "HEAD", self.manifest),
                         (False, "arquivo_fora_do_escopo"))


if __name__ == "__main__":
    unittest.main()
