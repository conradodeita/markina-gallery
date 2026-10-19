import unittest

from scripts.classify_ci_scope import SCOPES, classify


class ClassifyCIScopeTests(unittest.TestCase):
    def test_frontend_dependency_change_runs_only_frontend(self):
        result = classify(["frontend/package-lock.json"])
        self.assertEqual(result, {scope: scope in {"frontend", "frontend_image"} for scope in SCOPES})

    def test_python_application_requirements_run_backend_gemma_and_photo_builds(self):
        result = classify(["backend/requirements.txt"])
        self.assertEqual(
            result,
            {"backend": True, "frontend": False, "gemma": True, "backend_image": True, "frontend_image": False, "preview": True, "raw": True},
        )

    def test_push_adapter_dependency_runs_gemma_due_shared_image_install(self):
        result = classify(["backend/requirements-push.txt"])
        self.assertTrue(result["backend"])
        self.assertTrue(result["gemma"])
        self.assertTrue(result["backend_image"])
        self.assertTrue(result["preview"])
        self.assertTrue(result["raw"])
        self.assertFalse(result["frontend"])

    def test_facial_source_requires_backend_and_gemma(self):
        result = classify(["backend/app/facial/face_worker.py"])
        self.assertTrue(result["backend"])
        self.assertTrue(result["gemma"])
        self.assertFalse(result["frontend"])

    def test_photo_dockerfiles_select_only_the_affected_image_build(self):
        preview = classify(["backend/Dockerfile.preview-adjustment"])
        raw = classify(["backend/Dockerfile.raw-development"])
        self.assertTrue(preview["preview"])
        self.assertFalse(preview["raw"])
        self.assertTrue(raw["raw"])
        self.assertFalse(raw["preview"])

    def test_photo_worker_source_requires_its_image_build(self):
        preview = classify(["backend/app/preview_adjustment/worker.py"])
        raw = classify(["backend/app/raw_development/worker.py"])
        self.assertTrue(preview["preview"])
        self.assertFalse(preview["raw"])
        self.assertTrue(raw["raw"])
        self.assertFalse(raw["preview"])

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
