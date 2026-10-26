"""Release contracts with real Git histories and the project's build definitions."""
import copy
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import importlib.util
from pathlib import Path

import dependency_release as policy
from classify_prod_release import classify

ROOT = Path(__file__).resolve().parents[1]
SHA256 = "sha256:" + "a" * 64


class DependencyReleaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.env = dict(os.environ, GIT_AUTHOR_NAME="Release fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                        GIT_COMMITTER_NAME="Release fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "gc.auto", "0")
        self.git("config", "maintenance.auto", "false")
        files = list(policy.COMPOSE_FILES) + list(policy.WEB_BUILD_BLOBS) + list(policy.DEPENDENCY_MANIFESTS)
        files += ["backend/Dockerfile", "backend/Dockerfile.face",
                  "backend/Dockerfile.preview-adjustment",
                  "scripts/dependency_release.py"]
        for file in files:
            destination = self.root / file
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Fixture histories use the Git bytes rather than platform line endings.
            data = (ROOT / file).read_bytes().replace(b"\r\n", b"\n")
            destination.write_bytes(data)
        self.write("backend/app/main.py", "# unchanged API contract\n")
        self.base = self.commit()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "release fixture")
        return self.git("rev-parse", "HEAD")

    def change_web(self):
        path = self.root / "frontend/package.json"
        content = json.loads(path.read_text(encoding="utf-8"))
        content["dependencies"]["next"] = "^16.4.3"
        self.write("frontend/package.json", json.dumps(content))

    def change_python(self):
        path = self.root / "backend/requirements-push.txt"
        self.write("backend/requirements-push.txt", path.read_text(encoding="utf-8").replace("aiohttp==3.14.4", "aiohttp==3.14.5"))

    def inventory(self):
        return {"schema_version": 1, "project": "markina-gallery", "checkout_sha": self.base,
                "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(), "host_architecture": "aarch64",
                "services": {"web": {"status": "running", "health": "healthy", "image_id": SHA256,
                    "packages": {"next": "16.4.2", "react": "19.3.1", "react-dom": "19.3.1"},
                    "image": {"id": SHA256, "architecture": "arm64", "repo_digests": []}},
                    "api": {"source_sha": self.base}},
                "state": {"web-current.identity": "{} {} {} {}".format(self.base, SHA256, "b"*64, self.base)}}

    def test_frontend_dependency_only_affects_web(self):
        self.change_web()
        target = self.commit()
        report = policy.impact(self.root, self.base, target)
        self.assertEqual(set(report["images"]), {"frontend/Dockerfile"})
        self.assertEqual(report["images"]["frontend/Dockerfile"]["services"], ["web"])
        self.assertFalse(report["automatic_deploy"])
        self.assertEqual(classify({"frontend/package.json"}), "dependencies")

    def test_python_include_reaches_all_real_consumers_without_web(self):
        self.change_python()
        report = policy.impact(self.root, self.base, self.commit())
        self.assertEqual(set(report["images"]), {"backend/Dockerfile", "backend/Dockerfile.face",
            "backend/Dockerfile.preview-adjustment"})
        self.assertEqual(set(report["images"]["backend/Dockerfile.face"]["services"]),
                         {"face-search-worker", "face-index-worker", "face-maintenance-worker"})

    def test_mixed_sha_keeps_frontend_provenance_independent(self):
        self.change_web()
        web_target = self.commit()
        web_tree = policy.web_scope(self.root, self.base, web_target)["source_tree_oid"]
        self.change_python()
        target = self.commit()
        proof = policy.web_scope(self.root, self.base, target)
        self.assertEqual(proof["source_tree_oid"], web_tree)
        self.assertEqual(proof["pending_python_manifests"], ["backend/requirements-push.txt"])
        self.assertEqual(policy.api_provenance(self.root, self.base, target)["api_source_sha"], self.base)
        self.assertEqual(classify({"frontend/package.json", "backend/requirements-push.txt"}), "dependencies")
        plan = policy.plan(self.root, self.base, target, self.inventory(), "web")
        self.assertTrue(plan["ready_for_operational_inventory"])
        self.assertFalse(plan["release_authorized"])
        self.assertEqual(set(plan["selected_services"]), {"web"})

    def test_specialized_image_change_reports_only_its_services_and_is_protected(self):
        file = "backend/Dockerfile.face"
        self.write(file, (self.root / file).read_text(encoding="utf-8") + "\n# reviewed separately\n")
        report = policy.impact(self.root, self.base, self.commit())
        self.assertEqual(set(report["images"]), {file})
        self.assertTrue(report["images"][file]["specialized"])
        self.assertEqual(report["protected_changes"], [file])
        self.assertEqual(classify({file}), "protected")

    def test_protected_api_migration_and_compose_still_fail(self):
        for path in ("backend/app/main.py", "backend/migrations/versions/new.py", "docker/docker-compose.yml"):
            with self.subTest(path=path):
                original = (self.root / path).read_text(encoding="utf-8") if (self.root / path).exists() else ""
                self.write(path, original + "\n# protected change\n")
                target = self.commit()
                with self.assertRaisesRegex(ValueError, "protected_change"):
                    policy.web_scope(self.root, self.base, target)
        self.assertEqual(classify({"backend/migrations/versions/new.py"}), "protected")

    def test_backend_code_never_inherits_manifest_exception(self):
        self.change_python()
        self.write("backend/app/main.py", "# changed API\n")
        target = self.commit()
        with self.assertRaisesRegex(ValueError, "backend_runtime_diverges"):
            policy.api_provenance(self.root, self.base, target)

    def test_web_build_and_dockerignore_require_reviewed_blobs(self):
        self.write("frontend/Dockerfile", "FROM node:24-alpine\nCOPY ../backend /app\n")
        target = self.commit()
        with self.assertRaises(ValueError):
            policy.web_scope(self.root, self.base, target)
        with self.assertRaisesRegex(ValueError, "not_approved"):
            policy.web_scope(self.root, target, target)

    def test_resolved_context_refuses_additional_contexts_args_and_mounts(self):
        valid = {"services": {"web": {"build": {"context": "/opt/markina-gallery/frontend", "dockerfile": "Dockerfile"}}}}
        self.assertTrue(policy.web_build(valid)["isolated"])
        for key, value in (("additional_contexts", {"backend": "../backend"}), ("args", {"TOKEN": "fixture"}),
                           ("context", "/opt/markina-gallery"), ("secrets", ["fixture"])):
            changed = copy.deepcopy(valid)
            changed["services"]["web"]["build"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                policy.web_build(changed)
        valid["services"]["web"]["volumes"] = ["../backend:/app/backend"]
        with self.assertRaises(ValueError):
            policy.web_build(valid)

    def test_ignored_environment_file_cannot_enter_build_context(self):
        self.write(".gitignore", "frontend/.env*\n")
        target = self.commit()
        self.write("frontend/.env.local", "fixture only\n")
        with self.assertRaisesRegex(ValueError, "unversioned_web_context"):
            policy.web_scope(self.root, self.base, target)
        (self.root / "frontend/.env.local").unlink()
        self.write("frontend/node_modules/cache", "excluded by reviewed Dockerignore\n")
        policy.web_scope(self.root, self.base, target)

    def test_symlink_inside_git_tree_is_refused(self):
        blob = self.git("rev-parse", self.base + ":frontend/package.json")
        # The Git index mode protects the same contract on Windows without symlink privileges.
        self.git("update-index", "--add", "--cacheinfo", "120000," + blob + ",frontend/outside")
        self.git("commit", "-qm", "symlink fixture")
        with self.assertRaisesRegex(ValueError, "unsafe_web_context"):
            policy.web_scope(self.root, self.base, self.git("rev-parse", "HEAD"))

    def test_python_plan_excludes_inactive_and_blocks_uncovered_workers(self):
        self.change_python()
        target = self.commit()
        inventory = self.inventory()
        record = copy.deepcopy(inventory["services"]["web"])
        record["packages"] = {"aiohttp": "3.14.4", "multidict": "6.9.1", "urllib3": "2.8.0", "yarl": "1.25.1"}
        inventory["services"]["api"].update(copy.deepcopy(record))
        inventory["services"]["worker"] = copy.deepcopy(record)
        inventory["services"]["face-search-worker"] = copy.deepcopy(record)
        inventory["services"]["migrate"] = dict(record, status="exited")
        plan = policy.plan(self.root, self.base, target, inventory, "python")
        self.assertEqual(set(plan["selected_services"]), {"api", "worker", "face-search-worker"})
        self.assertIn("migrate", plan["excluded_inactive_services"])
        self.assertIn("face-search-worker:specialized_homologation_and_rollback_required", plan["blockers"])
        self.assertFalse(plan["ready_for_operational_inventory"])

    def test_missing_stale_forged_or_wrong_architecture_inventory_fails(self):
        self.change_web()
        target = self.commit()
        invalid = []
        wrong = self.inventory()
        wrong["collected_at"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).isoformat()
        invalid.append(wrong)
        wrong = self.inventory()
        wrong["services"]["web"]["image"]["id"] = "sha256:" + "b"*64
        invalid.append(wrong)
        wrong = self.inventory()
        wrong["services"]["web"]["image"]["architecture"] = "amd64"
        invalid.append(wrong)
        wrong = self.inventory()
        wrong["state"] = {}
        invalid.append(wrong)
        for inventory in invalid:
            with self.assertRaises(ValueError):
                policy.plan(self.root, self.base, target, inventory, "web")

    def test_shell_web_gate_uses_candidate_policy_and_fails_before_mutation(self):
        self.change_web()
        self.change_python()
        target = self.commit()
        script = (ROOT / "scripts/deploy-prod-web.sh").read_text(encoding="utf-8")
        functions = []
        for name in ("dependency_policy", "verify_scope"):
            functions.append(re.search(r"^" + name + r"\(\) \{.*?^\}", script, re.M | re.S).group())
        bash = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else "bash"
        command = "set -e\nPROJECT_ROOT='{}'\nTARGET_SHA={}\nfail() {{ exit 42; }}\n{}\nverify_scope {} {}".format(
            self.root.as_posix(), target, "\n".join(functions), self.base, target)
        result = subprocess.run([bash, "-c", command], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.write("backend/app/main.py", "# incompatible fixture\n")
        protected = self.commit()
        result = subprocess.run([bash, "-c", command.replace(target, protected)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 42, result.stderr)

    def test_dependency_scopes_have_no_deploy_branch_in_workflow(self):
        text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        for job, scope in (("production-release", "facial"), ("production-app-release", "app"),
                           ("production-preflight", "facial"), ("production-app-preflight", "app")):
            condition = text.split("  " + job + ":", 1)[1].splitlines()[1]
            self.assertIn("scope == '" + scope + "'", condition)
            self.assertNotIn("dependencies", condition)
        self.assertIn("run: python scripts/test_dependency_release.py", text)
        self.assertIn("--platform linux/arm64 --load --tag frontend:validation-arm64", text)
        self.assertIn("assert.deepStrictEqual(actual, JSON.parse(process.env.EXPECTED_PACKAGES))", text)

    def test_new_requirement_include_is_reported_but_cannot_bypass_web_gate(self):
        file = self.root / "backend/requirements.txt"
        self.write("backend/requirements.txt", file.read_text(encoding="utf-8") + "\n-r requirements-extra.txt\n")
        self.write("backend/requirements-extra.txt", "example==1.0.0\n")
        for dockerfile in (self.root / "backend").glob("Dockerfile*"):
            self.write(dockerfile.relative_to(self.root), dockerfile.read_text(encoding="utf-8").replace(
                "COPY requirements.txt requirements-push.txt", "COPY requirements-extra.txt requirements.txt requirements-push.txt"))
        base = self.commit()
        self.write("backend/requirements-extra.txt", "example==1.0.1\n")
        target = self.commit()
        report = policy.impact(self.root, base, target)
        self.assertIn("backend/requirements-extra.txt", report["images"]["backend/Dockerfile.face"]["requirements"])
        self.assertEqual(classify({"backend/requirements-extra.txt"}), "dependencies")
        with self.assertRaises(ValueError):
            policy.web_scope(self.root, base, target)

    def test_compose_image_update_is_identified_and_stays_protected(self):
        file = "docker/docker-compose.yml"
        self.write(file, (self.root / file).read_text(encoding="utf-8").replace("nginx:1.27-alpine", "nginx:1.31-alpine"))
        report = policy.impact(self.root, self.base, self.commit())
        self.assertEqual(set(report["images"]), {"nginx:1.31-alpine"})
        self.assertEqual(report["images"]["nginx:1.31-alpine"]["services"], ["nginx"])
        self.assertEqual(classify({file}), "protected")

    def test_constraints_are_build_inputs_and_escaping_includes_fail(self):
        file = "backend/requirements.txt"
        self.write(file, (self.root / file).read_text(encoding="utf-8") + "\n-c constraints.txt\n")
        self.write("backend/constraints.txt", "example==1.0.0\n")
        for dockerfile in (self.root / "backend").glob("Dockerfile*"):
            self.write(dockerfile.relative_to(self.root), dockerfile.read_text(encoding="utf-8").replace(
                "COPY requirements.txt requirements-push.txt", "COPY constraints.txt requirements.txt requirements-push.txt"))
        base = self.commit()
        self.write("backend/constraints.txt", "example==1.0.1\n")
        report = policy.impact(self.root, base, self.commit())
        self.assertIn("backend/constraints.txt", report["images"]["backend/Dockerfile.face"]["requirements"])
        self.assertEqual(classify({"backend/constraints.txt"}), "dependencies")
        self.write(file, "-r ../outside.txt\n")
        with self.assertRaisesRegex(ValueError, "outside_context"):
            policy.impact(self.root, base, self.commit())

    def test_missing_or_uncopied_requirement_reference_fails(self):
        path = "backend/requirements.txt"
        self.write(path, "-r requirements-missing.txt\n")
        with self.assertRaises(ValueError):
            policy.impact(self.root, self.base, self.commit())
        self.write("backend/requirements-missing.txt", "example==1.0.0\n")
        with self.assertRaisesRegex(ValueError, "not_copied"):
            policy.impact(self.root, self.base, self.commit())

    def test_collector_uses_only_metadata_and_selected_packages(self):
        spec = importlib.util.spec_from_file_location("readonly_collector", ROOT / "scripts/inventory-dependency-runtimes.py")
        collector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(collector)
        commands = []

        def fake_run(args):
            commands.append(args)
            if args[0] == "git":
                return self.base
            if args[:3] == ["docker", "ps", "-aq"]:
                return "web-id\nmigrate-id"
            if args[:2] == ["docker", "inspect"]:
                service = "web" if args[-1] == "web-id" else "migrate"
                return json.dumps({"service": service, "status": "running" if service == "web" else "exited", "image_id": SHA256})
            if args[:3] == ["docker", "image", "inspect"]:
                return json.dumps({"id": SHA256, "architecture": "arm64", "repo_digests": []})
            if args[:2] == ["docker", "exec"]:
                self.assertEqual(args[3:5], ["node", "-e"])
                return json.dumps({"next": "16.4.0", "react": "19.2.8", "react-dom": "19.2.8"})
            self.fail("unexpected operational command: " + str(args))

        with patch.object(collector, "run", side_effect=fake_run), patch.object(collector.pathlib.Path, "is_file", return_value=False):
            result = collector.collect()
        self.assertEqual(set(result["services"]), {"web", "migrate"})
        self.assertEqual(result["services"]["migrate"]["status"], "exited")
        for args in commands:
            self.assertNotIn(".Config.Env", " ".join(args))
            self.assertFalse(set(args) & {"up", "stop", "restart", "prune", "run", "build"})


if __name__ == "__main__":
    unittest.main()
