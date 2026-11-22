"""Contratos negativos do empacotamento; não executa Docker nem baixa pesos."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facial_runtime_candidate import (
    MANIFEST_SHA256,
    OVERLAYS,
    SERVICE_OVERLAYS,
    CandidateError,
    build_local,
    prepare_context,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = "sha256:" + "a" * 64
DONOR = "sha256:" + "b" * 64
CANDIDATE = "sha256:" + "c" * 64


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = ROOT / "backend/facial-assets/model-manifest.json"
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.baseline = {
            "image": BASE,
            "runtime": {
                "architecture": "aarch64", "python": "3.13.18 test-runtime",
                "packages": {"redis": "8.1.0", "SQLAlchemy": "2.1.6"},
                "module_sha256": {k: "d" * 64 for k in OVERLAYS | {"app/auth.py", "app/main.py"}},
            },
        }
        assets = {"markina-face-models/" + x["filename"]: {"bytes": x["bytes"], "sha256": x["sha256"]}
                  for x in manifest["models"].values()}
        assets["markina-face-models/.markina-face-models.json"] = {"bytes": 187, "sha256": "e" * 64}
        self.donor = {
            "image": DONOR, "architecture": "arm64", "os": "linux",
            "manifest_sha256": MANIFEST_SHA256,
            "installed_versions": {"numpy": "2.2.6", "opencv-python-headless": "4.12.0.88", "redis": "6.4.0"},
            "assets": assets,
        }
        self.overlays = {}
        for name in OVERLAYS:
            p = self.root / Path(name).name
            p.write_text("# reviewed synthetic overlay\n", encoding="utf-8")
            self.overlays[name] = p
        self.wheels = {}
        for filename, name, version in [
            ("numpy-2.2.6-cp313-cp313-manylinux_2_17_aarch64.whl", "numpy", "2.2.6"),
            ("opencv_python_headless-4.12.0.88-cp37-abi3-manylinux_2_17_aarch64.whl", "opencv-python-headless", "4.12.0.88"),
        ]:
            self.add_wheel(filename, name, version)
        self.destination = self.root / "context"

    def add_wheel(self, filename, name, version):
        path = self.root / filename
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("package.dist-info/METADATA", f"Name: {name}\nVersion: {version}\n")
        self.wheels[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    def prepare(self):
        return prepare_context(self.destination, baseline=self.baseline, donor=self.donor,
                               manifest_path=self.manifest, overlays=self.overlays, wheels=self.wheels)

    def rejected(self):
        with self.assertRaises(CandidateError):
            self.prepare()
        self.assertFalse(self.destination.exists(), "Validação inválida escreveu contexto parcial")

    def test_context_adds_only_reviewed_overlays_and_preserves_redis(self):
        plan = self.prepare()
        recipe = json.loads((self.destination / "recipe.json").read_text())
        self.assertEqual(recipe["candidate_packages"], {
            "redis": "8.1.0", "sqlalchemy": "2.1.6", "numpy": "2.2.6", "opencv-python-headless": "4.12.0.88",
        })
        for name in ["app/auth.py", "app/main.py"]:
            self.assertEqual(recipe["candidate_modules"][name], recipe["baseline_modules"][name])
        self.assertEqual({str(p.relative_to(self.destination / "overlays")).replace("\\", "/")
                          for p in (self.destination / "overlays").rglob("*.py")}, OVERLAYS)
        dockerfile = (self.destination / "Dockerfile").read_text()
        self.assertIn("--no-index --no-deps --require-hashes", dockerfile)
        self.assertIn("COPY overlays/app/facial/config.py /app/app/facial/config.py", dockerfile)
        self.assertIn("COPY overlays/app/facial/rollout.py /app/app/facial/rollout.py", dockerfile)
        self.assertNotIn("app/facial/face_worker.py", dockerfile)
        self.assertNotIn("redis", (self.destination / "requirements-restore.txt").read_text())
        self.assertIn(plan.baseline_alias, dockerfile)
        self.assertNotIn("apt-get", dockerfile)
        self.assertNotIn("model_assets prepare", dockerfile)
        compile((self.destination / "verify.py").read_text(), "verify.py", "exec")

    def test_overlay_crlf_normalizes_to_git_blob_bytes(self):
        source = self.overlays["app/facial/config.py"]
        source.write_bytes(b"# first line\r\n# second line\r\n")
        self.prepare()
        expected = b"# first line\n# second line\n"
        copied = self.destination / "overlays/app/facial/config.py"
        recipe = json.loads((self.destination / "recipe.json").read_text())
        self.assertEqual(copied.read_bytes(), expected)
        self.assertEqual(
            recipe["candidate_modules"]["app/facial/config.py"],
            hashlib.sha256(expected).hexdigest(),
        )

    def test_facial_worker_candidate_includes_only_its_signal_handler_overlay(self):
        service = "face-search-worker"
        worker_overlay = "app/facial/face_worker.py"
        self.baseline["runtime"]["module_sha256"][worker_overlay] = "f" * 64
        path = self.root / "face_worker.py"
        path.write_text("# reviewed cooperative stop overlay\n", encoding="utf-8")
        overlays = {name: self.overlays[name] for name in OVERLAYS}
        overlays[worker_overlay] = path
        prepare_context(
            self.destination,
            baseline=self.baseline,
            donor=self.donor,
            manifest_path=self.manifest,
            overlays=overlays,
            wheels=self.wheels,
            service=service,
        )
        dockerfile = (self.destination / "Dockerfile").read_text()
        self.assertIn(
            "COPY overlays/app/facial/face_worker.py /app/app/facial/face_worker.py",
            dockerfile,
        )
        recipe = json.loads((self.destination / "recipe.json").read_text())
        self.assertEqual(recipe["service"], service)
        changed = {
            name for name, value in recipe["candidate_modules"].items()
            if value != recipe["baseline_modules"].get(name)
        }
        self.assertEqual(changed, set(SERVICE_OVERLAYS[service]))

    def test_api_candidate_rejects_facial_worker_overlay(self):
        worker_overlay = "app/facial/face_worker.py"
        self.baseline["runtime"]["module_sha256"][worker_overlay] = "f" * 64
        path = self.root / "face_worker.py"
        path.write_text("# unreviewed for api\n", encoding="utf-8")
        self.overlays[worker_overlay] = path
        self.rejected()

    def test_existing_facial_dependencies_need_no_wheels_or_reinstall(self):
        self.baseline["runtime"]["packages"].update({
            "numpy": "2.2.6", "opencv-python-headless": "4.12.0.88",
        })
        self.wheels = {}
        self.prepare()
        recipe = json.loads((self.destination / "recipe.json").read_text())
        dockerfile = (self.destination / "Dockerfile").read_text()
        self.assertEqual(recipe["candidate_packages"], recipe["baseline_packages"])
        self.assertNotIn("pip install", dockerfile)
        self.assertNotIn("COPY wheelhouse", dockerfile)
        self.assertFalse((self.destination / "wheelhouse").exists())
        self.assertFalse((self.destination / "requirements-restore.txt").exists())

    def test_crlf_manifest_matches_runtime_canonical_bytes(self):
        p = self.root / "manifest.json"
        p.write_bytes(self.manifest.read_text(encoding="utf-8").replace("\n", "\r\n").encode())
        self.manifest = p
        self.prepare()
        self.assertEqual(hashlib.sha256((self.destination / "model-manifest.json").read_bytes()).hexdigest(), MANIFEST_SHA256)

    def test_unlisted_overlay_rejected_before_write(self):
        self.overlays["app/auth.py"] = next(iter(self.overlays.values()))
        self.rejected()

    def test_missing_overlay_rejected(self):
        self.overlays.pop(next(iter(OVERLAYS)))
        self.rejected()

    def test_mutable_image_rejected(self):
        self.baseline["image"] = "python:3.13"
        self.rejected()

    def test_cross_architecture_and_python_rejected(self):
        for section, key, value in [
            ("baseline", "architecture", "x86_64"), ("baseline", "python", "3.12.3"),
            ("donor", "architecture", "amd64"), ("donor", "os", "windows"),
        ]:
            with self.subTest(key=key, value=value):
                baseline, donor = copy.deepcopy(self.baseline), copy.deepcopy(self.donor)
                target = self.baseline["runtime"] if section == "baseline" else self.donor
                target[key] = value
                self.rejected()
                self.baseline, self.donor = baseline, donor

    def test_existing_dependency_cannot_be_replaced(self):
        self.baseline["runtime"]["packages"]["numpy"] = "2.3.0"
        self.rejected()

    def test_unverified_donor_version_rejected(self):
        self.donor["installed_versions"]["numpy"] = "2.3.0"
        self.rejected()

    def test_model_evidence_tampering_rejected(self):
        for mutation in ["checksum", "marker", "manifest", "extra"]:
            donor = copy.deepcopy(self.donor)
            with self.subTest(mutation=mutation):
                if mutation == "checksum":
                    key = next(k for k in self.donor["assets"] if k.endswith(".onnx"))
                    self.donor["assets"][key]["sha256"] = "f" * 64
                elif mutation == "marker":
                    self.donor["assets"].pop("markina-face-models/.markina-face-models.json")
                elif mutation == "manifest":
                    self.donor["manifest_sha256"] = "f" * 64
                else:
                    self.donor["assets"]["markina-face-models/unknown.onnx"] = {"bytes": 1, "sha256": "f" * 64}
                self.rejected()
                self.donor = donor

    def test_wheel_tamper_rejected(self):
        path = next(iter(self.wheels))
        path.write_bytes(path.read_bytes() + b"corruption")
        self.rejected()

    def test_wrong_wheel_tags_or_metadata_rejected(self):
        original = dict(self.wheels)
        for filename, version in [
            ("numpy-2.2.6-cp313-cp313-manylinux_2_17_x86_64.whl", "2.2.6"),
            ("numpy-2.2.6-cp312-cp312-manylinux_2_17_aarch64.whl", "2.2.6"),
            ("numpy-2.2.6-cp313-cp313-manylinux_2_17_aarch64.whl", "2.3.0"),
        ]:
            with self.subTest(filename=filename, version=version):
                self.wheels = {p: h for p, h in original.items() if not p.name.startswith("numpy-")}
                self.add_wheel(filename, "numpy", version)
                self.rejected()

    def test_missing_wheel_rejected(self):
        self.wheels.pop(next(iter(self.wheels)))
        self.rejected()

    def test_existing_context_is_never_overwritten(self):
        self.destination.mkdir()
        sentinel = self.destination / "sentinel.txt"
        sentinel.write_text("preserved")
        with self.assertRaises(CandidateError):
            self.prepare()
        self.assertEqual(sentinel.read_text(), "preserved")

    def test_hardlink_overlay_rejected(self):
        source = next(iter(self.overlays.values()))
        try:
            os.link(source, self.root / "hardlink.py")
        except PermissionError:
            self.skipTest("Sandbox Windows não permite hardlink; executar no Linux isolado")
        self.rejected()

    def test_build_refuses_context_drift_before_any_docker_command(self):
        plan = self.prepare()
        (self.destination / "overlays/app/facial/config.py").write_text("unreviewed")
        calls = []
        with self.assertRaises(CandidateError):
            build_local(plan, "pyp-facial-restore:test", lambda command: calls.append(command),
                        docker_context="desktop-linux", builder="desktop-linux")
        self.assertEqual(calls, [])

    def test_checked_build_uses_local_ids_and_isolated_verification(self):
        plan = self.prepare()
        calls = []

        def runner(command):
            calls.append(command)
            if command[:5] == ["docker", "--context", "desktop-linux", "buildx", "inspect"]:
                return "Name: desktop-linux\nDriver: docker\n"
            if command[:5] == ["docker", "--context", "desktop-linux", "image", "inspect"]:
                name = command[5]
                image = BASE if name in {BASE, plan.baseline_alias} else DONOR if name in {DONOR, plan.donor_alias} else CANDIDATE
                return json.dumps([{"Id": image, "Os": "linux", "Architecture": "arm64", "Config": {}}])
            return "ok"

        self.assertEqual(build_local(plan, "pyp-facial-restore:test", runner,
                                     docker_context="desktop-linux", builder="desktop-linux"), CANDIDATE)
        build = next(c for c in calls if c[:5] == ["docker", "--context", "desktop-linux", "buildx", "build"])
        self.assertIn("--builder", build)
        self.assertIn("desktop-linux", build)
        self.assertIn("--network=none", build)
        verify = calls[-1]
        self.assertIn(CANDIDATE, verify)
        self.assertIn("--network=none", verify)
        self.assertIn("--read-only", verify)
        self.assertFalse(any(c in verify for c in ["-v", "--mount", "--env-file", "--privileged"]))

    def test_alias_mismatch_prevents_build(self):
        plan = self.prepare()
        calls = []

        def runner(command):
            calls.append(command)
            if command[:5] == ["docker", "--context", "desktop-linux", "buildx", "inspect"]:
                return "Name: desktop-linux\nDriver: docker\n"
            if command[:5] == ["docker", "--context", "desktop-linux", "image", "inspect"]:
                image = BASE if command[5] == BASE else DONOR
                return json.dumps([{"Id": image, "Os": "linux", "Architecture": "arm64", "Config": {}}])
            return ""

        with self.assertRaises(CandidateError):
            build_local(plan, "pyp-facial-restore:test", runner,
                        docker_context="desktop-linux", builder="desktop-linux")
        self.assertFalse(any(c[:5] == ["docker", "--context", "desktop-linux", "buildx", "build"] for c in calls))

    def test_unknown_onbuild_hook_prevents_any_tag_or_build(self):
        plan = self.prepare()
        calls = []

        def runner(command):
            calls.append(command)
            if command[:5] == ["docker", "--context", "desktop-linux", "buildx", "inspect"]:
                return "Name: desktop-linux\nDriver: docker\n"
            return json.dumps([{"Id": BASE, "Os": "linux", "Architecture": "arm64",
                                "Config": {"OnBuild": ["RUN unreviewed"]}}])

        with self.assertRaises(CandidateError):
            build_local(plan, "pyp-facial-restore:test", runner,
                        docker_context="desktop-linux", builder="desktop-linux")
        self.assertFalse(any("tag" in c or "build" in c for c in calls))

    def test_remote_builder_refused_before_images_or_mutation(self):
        plan = self.prepare()
        calls = []

        def runner(command):
            calls.append(command)
            return "docker-container"

        with self.assertRaises(CandidateError):
            build_local(plan, "pyp-facial-restore:test", runner,
                        docker_context="desktop-linux", builder="desktop-linux")
        self.assertEqual(calls, [["docker", "--context", "desktop-linux", "buildx", "inspect",
                                  "desktop-linux"]])

    def test_existing_candidate_tag_is_never_overwritten(self):
        plan = self.prepare()
        calls = []
        candidate_tag = "pyp-facial-restore:api-20261102"

        def runner(command):
            calls.append(command)
            if command[:5] == ["docker", "--context", "desktop-linux", "buildx", "inspect"]:
                return "Driver: docker\n"
            if command[:7] == ["docker", "--context", "desktop-linux", "image", "ls",
                               "--format", "{{.Repository}}:{{.Tag}}"]:
                return candidate_tag
            return ""

        with self.assertRaises(CandidateError):
            build_local(plan, candidate_tag, runner,
                        docker_context="desktop-linux", builder="desktop-linux")
        self.assertFalse(any("tag" in c or "build" in c for c in calls))


if __name__ == "__main__":
    unittest.main()
