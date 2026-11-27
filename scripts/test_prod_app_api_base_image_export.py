from __future__ import annotations

import gzip
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "scripts/export_prod_app_api_base_image.sh"
BASH = shutil.which("bash")
TARGET_SHA = "a" * 40
IMAGE_ID = "sha256:" + "1" * 64


@unittest.skipUnless(BASH and os.name != "nt", "requires a POSIX shell and filesystem")
class ApiBaseImageExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.docker_log = self.root / "docker.log"
        source = EXPORTER.read_text(encoding="utf-8")
        source = source.replace(
            'readonly PROJECT_ROOT="/opt/markina-gallery"',
            f'readonly PROJECT_ROOT="{self.project.as_posix()}"',
        )
        source = source.replace(
            'readonly EXPECTED_HOST="clearbudget-vnic"',
            'readonly EXPECTED_HOST="preflight-test"',
        )
        if source == EXPORTER.read_text(encoding="utf-8"):
            raise AssertionError("fixture constants were not replaced")
        self.script = self.root / "exporter.sh"
        self.script.write_text(source, encoding="utf-8", newline="\n")
        self.install_command("hostname", "printf 'preflight-test\\n'\n")
        self.install_command("git", self.git_shim())
        self.install_command("docker", self.docker_shim())
        self.install_command("sudo", r'''
if [[ "$*" == *" compose -- ps -q ${TEST_REQUESTED_SERVICE:-api}" ]]; then
  printf '%s\n' "$TEST_CONTAINER_IDS"
elif [[ "$*" == *" service-project -- ${TEST_REQUESTED_SERVICE:-api}" ]]; then
  printf '%s\n' "${TEST_EXPECTED_PROJECT:-markina-gallery}"
else
  exit 96
fi
''')

    def install_command(self, name: str, body: str) -> None:
        command = self.bin / name
        command.write_text("#!/usr/bin/env bash\nset -Eeuo pipefail\n" + body, encoding="utf-8")
        command.chmod(0o755)

    @staticmethod
    def git_shim() -> str:
        return r'''
case "$*" in
  "rev-parse --show-toplevel") pwd -P ;;
  "status --porcelain") : ;;
  "remote get-url origin") printf '%s\n' 'https://github.com/conradodeita/markina-gallery.git' ;;
  "rev-parse HEAD") printf '%s\n' "$TEST_CHECKOUT_SHA" ;;
  "rev-parse origin/main") printf '%s\n' "$TEST_TARGET_SHA" ;;
  "rev-parse "*":scripts/production_app_compose_bridge.py") printf '%s\n' 'bridge-blob' ;;
  "hash-object -- "*) printf '%s\n' "${TEST_BRIDGE_BLOB:-bridge-blob}" ;;
  "merge-base --is-ancestor "*) : ;;
  "ls-remote origin refs/heads/main") printf '%s refs/heads/main\n' "$TEST_TARGET_SHA" ;;
  *) echo "unexpected git command: $*" >&2; exit 97 ;;
esac
'''

    def docker_shim(self) -> str:
        return r'''
printf '%s\n' "$*" >> "$TEST_DOCKER_LOG"
if [[ "$1" == ps ]]; then
  printf '%s\n' "$TEST_CONTAINER_IDS"
elif [[ "$1" == inspect && "$2" == --format ]]; then
  case "$3" in
    *com.docker.compose.project*) printf '%s\n' "${TEST_PROJECT:-markina-gallery}" ;;
    *com.docker.compose.service*) printf '%s\n' "${TEST_SERVICE:-api}" ;;
    '{{.Image}}') printf '%s\n' "$TEST_IMAGE_ID" ;;
    *) echo "unexpected inspect format: $3" >&2; exit 98 ;;
  esac
elif [[ "$1" == image && "$2" == inspect && "$3" == --format ]]; then
  printf '%s\n' "${TEST_PLATFORM:-linux/arm64}"
elif [[ "$1" == image && "$2" == save ]]; then
  printf 'synthetic-docker-image-archive\0\n'
else
  echo "unexpected docker command: $*" >&2
  exit 99
fi
'''

    def run_export(self, **overrides: str) -> subprocess.CompletedProcess[bytes]:
        env = os.environ.copy()
        env.update({
            "PATH": str(self.bin) + os.pathsep + env.get("PATH", ""),
            "MARKINA_EXPECTED_REPOSITORY": "conradodeita/markina-gallery",
            "TEST_CHECKOUT_SHA": "b" * 40,
            "TEST_TARGET_SHA": TARGET_SHA,
            "TEST_IMAGE_ID": IMAGE_ID,
            "TEST_CONTAINER_IDS": "active-api-container",
            "TEST_DOCKER_LOG": str(self.docker_log),
        })
        env.update(overrides)
        return subprocess.run(
            [BASH, str(self.script), "--mode", "export", "--sha", TARGET_SHA,
             "--expected-image-id", IMAGE_ID, "--service", env.get("TEST_REQUESTED_SERVICE", "api")],
            cwd=self.project, env=env, capture_output=True, check=False, timeout=20,
        )

    def test_exports_only_the_inventoried_arm64_api_image(self):
        result = self.run_export()
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        self.assertEqual(gzip.decompress(result.stdout), b"synthetic-docker-image-archive\x00\n")
        calls = self.docker_log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(calls), 5)
        self.assertIn("image save " + IMAGE_ID, calls[-1])
        self.assertEqual(list(self.project.iterdir()), [])

    def test_exports_web_only_when_the_registered_service_and_image_match(self):
        result = self.run_export(TEST_REQUESTED_SERVICE="web", TEST_SERVICE="web")
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        self.assertEqual(gzip.decompress(result.stdout), b"synthetic-docker-image-archive\0\n")
        self.docker_log.unlink()
        result = self.run_export(TEST_REQUESTED_SERVICE="web", TEST_SERVICE="api")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("image save", self.docker_log.read_text(encoding="utf8"))

    def test_rejects_non_application_service_before_docker(self):
        result = self.run_export(TEST_REQUESTED_SERVICE="db")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.docker_log.exists())

    def test_rejects_inventory_drift_before_export(self):
        result = self.run_export(TEST_IMAGE_ID="sha256:" + "2" * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"imagem API mudou", result.stderr)
        calls = self.docker_log.read_text(encoding="utf-8").splitlines()
        self.assertFalse(any(call.startswith("image save ") for call in calls))

    def test_rejects_wrong_project_service_platform_and_multiple_containers(self):
        invalid = (
            {"TEST_PROJECT": "other-project"},
            {"TEST_SERVICE": "worker"},
            {"TEST_PLATFORM": "linux/amd64"},
            {"TEST_CONTAINER_IDS": "api-one\napi-two"},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                self.docker_log.unlink(missing_ok=True)
                result = self.run_export(**overrides)
                self.assertNotEqual(result.returncode, 0)
                calls = self.docker_log.read_text(encoding="utf-8").splitlines() if self.docker_log.exists() else []
                self.assertFalse(any(call.startswith("image save ") for call in calls))

    def test_registered_generation_is_selected_without_project_prefix_fallback(self):
        project = 'markina-gallery-app-' + 'a' * 32
        result = self.run_export(TEST_PROJECT=project, TEST_EXPECTED_PROJECT=project)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        result = self.run_export(TEST_PROJECT=project)
        self.assertNotEqual(result.returncode, 0)
        result = self.run_export(TEST_BRIDGE_BLOB='unreviewed')
        self.assertNotEqual(result.returncode, 0)

    def test_rejects_invalid_arguments_before_docker_access(self):
        result = subprocess.run(
            [BASH, str(self.script), "--mode", "inventory", "--sha", TARGET_SHA,
             "--expected-image-id", IMAGE_ID],
            cwd=self.project,
            env=dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ.get("PATH", "")),
            capture_output=True, check=False, timeout=20,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.docker_log.exists())


if __name__ == "__main__":
    unittest.main()
