import unittest

from scripts.classify_ci_scope import SCOPES, classify


class ClassifyCIScopeTests(unittest.TestCase):
    def test_frontend_dependency_change_runs_only_frontend(self):
        result = classify(["frontend/package-lock.json"])
        self.assertEqual(result, {scope: scope in {"frontend", "frontend_image"} for scope in SCOPES})

    def test_python_application_requirements_run_backend_and_preview_builds(self):
        result = classify(["backend/requirements.txt"])
        self.assertEqual(
            result,
            {"backend": True, "backend_tests": True, "frontend": False,
             "backend_image": True, "frontend_image": False, "preview": True},
        )

    def test_exact_ci_feedback_tool_skips_only_product_shards(self):
        for path in ("scripts/ci_feedback.py", "scripts/test_ci_feedback.py"):
            with self.subTest(path=path):
                result = classify([path])
                self.assertEqual(
                    result,
                    {"backend": True, "backend_tests": False, "frontend": False,
                     "backend_image": False, "frontend_image": False, "preview": False},
                )

    def test_feedback_tool_mixed_with_backend_runtime_requires_full_backend_suite(self):
        result = classify(["scripts/test_ci_feedback.py", "backend/app/auth/session.py"])
        self.assertTrue(result["backend"])
        self.assertTrue(result["backend_tests"])
        self.assertFalse(result["frontend"])

    def test_push_adapter_dependency_runs_backend_and_preview_builds(self):
        result = classify(["backend/requirements-push.txt"])
        self.assertTrue(result["backend"])
        self.assertTrue(result["backend_tests"])
        self.assertTrue(result["backend_image"])
        self.assertTrue(result["preview"])
        self.assertFalse(result["frontend"])

    def test_facial_source_requires_backend(self):
        result = classify(["backend/app/facial/face_worker.py"])
        self.assertTrue(result["backend"])
        self.assertTrue(result["backend_tests"])
        self.assertFalse(result["frontend"])

    def test_security_and_data_contract_paths_keep_the_complete_backend_suite(self):
        for path in (
            "backend/app/auth/otp.py",
            "backend/app/tenancy/access.py",
            "backend/app/payments/provider.py",
            "backend/app/facial/face_worker.py",
            "backend/app/media/storage.py",
            "backend/migrations/versions/20261119_add_index.py",
        ):
            with self.subTest(path=path):
                result = classify([path])
                self.assertTrue(result["backend"])
                self.assertTrue(result["backend_tests"])

    def test_production_or_unknown_script_changes_fail_open(self):
        for path in ("scripts/deploy-prod-web.sh", "scripts/test_deploy_prod_web.sh",
                     "scripts/test_classify_ci_scope.py", "scripts/prove_app_engine_promotion.py"):
            with self.subTest(path=path):
                self.assertTrue(all(classify([path]).values()))

    def test_simultaneous_frontend_and_backend_changes_select_both(self):
        result = classify(["frontend/app/gallery/page.tsx", "backend/app/payments/provider.py"])
        self.assertTrue(result["backend"])
        self.assertTrue(result["backend_tests"])
        self.assertTrue(result["frontend"])
        self.assertTrue(result["frontend_image"])

    def test_photo_dockerfiles_select_only_the_affected_image_build(self):
        preview = classify(["backend/Dockerfile.preview-adjustment"])
        self.assertTrue(preview["preview"])

    def test_photo_worker_source_requires_its_image_build(self):
        preview = classify(["backend/app/preview_adjustment/worker.py"])
        self.assertTrue(preview["preview"])

    def test_backend_runtime_manifest_changes_require_backend_image_build(self):
        result = classify(["backend/Dockerfile"])
        self.assertTrue(result["backend_image"])
        self.assertFalse(result["frontend_image"])

    def test_workflow_or_classifier_change_runs_all_scopes(self):
        for path in (".github/workflows/ci.yml", "scripts/classify_ci_scope.py"):
            with self.subTest(path=path):
                self.assertTrue(all(classify([path]).values()))

    def test_unknown_runtime_or_compose_path_fails_open_to_all_scopes(self):
        for path in ("docker/compose.yaml", "new-worker/runtime.py", "docker-compose.yml"):
            with self.subTest(path=path):
                self.assertTrue(all(classify([path]).values()))

    def test_manual_and_push_runs_are_full(self):
        self.assertTrue(all(classify([], full=True).values()))


if __name__ == "__main__":
    unittest.main()
