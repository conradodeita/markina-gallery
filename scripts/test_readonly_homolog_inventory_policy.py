"""Testes de política do inventário remoto somente leitura de homologação."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "inventory-homolog-readonly.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "inventory-homolog-readonly.yml"
ORIGIN_VALIDATOR = ROOT / "scripts" / "validate-homolog-public-origin.py"


class ReadonlyHomologInventoryPolicyTests(unittest.TestCase):
    def _bash(self) -> str:
        if os.name == "nt":
            git_bash = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git" / "bin" / "bash.exe"
            if git_bash.is_file():
                return str(git_bash)
        return shutil.which("bash") or "bash"

    def _shell_path(self, path: Path) -> str:
        if os.name == "nt":
            cygpath = shutil.which("cygpath")
            if not cygpath:
                git_cygpath = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git" / "usr" / "bin" / "cygpath.exe"
                cygpath = str(git_cygpath) if git_cygpath.is_file() else None
            if cygpath:
                return subprocess.check_output([cygpath, "-u", str(path)], text=True).strip()
        return str(path)

    def _prepare_checkout(self, root: Path) -> tuple[Path, dict[str, str], Path]:
        project = root / "project"
        project.mkdir()
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        (project / ".keep").write_text("test\n", encoding="utf-8")
        env = os.environ.copy()
        env.update(
            GIT_AUTHOR_NAME="Policy Test",
            GIT_AUTHOR_EMAIL="policy@example.invalid",
            GIT_COMMITTER_NAME="Policy Test",
            GIT_COMMITTER_EMAIL="policy@example.invalid",
        )
        subprocess.run(["git", "-C", str(project), "add", ".keep"], check=True, env=env)
        subprocess.run(
            ["git", "-C", str(project), "commit", "-q", "-m", "test fixture"],
            check=True,
            env=env,
        )
        copied_script = root / "inventory-homolog-readonly.sh"
        source = SCRIPT.read_text(encoding="utf-8")
        source = source.replace(
            'readonly PROJECT_ROOT="/opt/markina-gallery"',
            f'readonly PROJECT_ROOT="{self._shell_path(project)}"',
            1,
        )
        copied_script.write_text(source, encoding="utf-8")
        (project / "docker").mkdir()
        (project / "docker" / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
        (project / "docker" / ".env.homolog").write_text("", encoding="utf-8")
        bin_dir = root / "bin"
        bin_dir.mkdir()
        docker_calls = root / "docker-calls.log"
        docker_stub = bin_dir / "docker"
        docker_stub.write_text(
            f'''#!/usr/bin/env bash
printf '%s\\n' "$*" >> "{self._shell_path(docker_calls)}"
if [[ "$*" == *"config --format json"* ]]; then
  cat "$MOCK_COMPOSE_CONFIG"
fi
''',
            encoding="utf-8",
        )
        docker_stub.chmod(0o755)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
        return project, env, docker_calls

    def test_invalid_sha_stops_before_project_or_docker_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _project, env, docker_calls = self._prepare_checkout(root)
            result = subprocess.run(
                [self._bash(), str(root / "inventory-homolog-readonly.sh"), "--expected-sha", "invalid"],
                cwd=_project,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA integral esperado", result.stderr)
            self.assertFalse(docker_calls.exists())

    def test_sha_mismatch_stops_before_any_compose_query(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project, env, docker_calls = self._prepare_checkout(root)
            result = subprocess.run(
                [self._bash(), str(root / "inventory-homolog-readonly.sh"), "--expected-sha", "0" * 40,
                 "--expected-public-base-url", "https://gallery.example.com"],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            observed_sha = subprocess.check_output(
                ["git", "-C", str(project), "rev-parse", "HEAD"], text=True
            ).strip()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("HEAD implantado diverge", result.stderr)
            self.assertIn(f"esperado={'0' * 40}", result.stderr)
            self.assertIn(f"observado={observed_sha}", result.stderr)
            self.assertIn("nenhuma consulta foi executada", result.stderr)
            self.assertFalse(docker_calls.exists())

    def test_invalid_public_origin_is_rejected_without_echoing_value(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            value = "https://private.example.com/path?token=should-not-print"
            env = os.environ.copy()
            env["HOMOLOG_PUBLIC_BASE_URL"] = value
            result = subprocess.run(
                [sys.executable, str(ORIGIN_VALIDATOR)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ausente ou inválida", result.stderr)
            self.assertNotIn(value, result.stdout + result.stderr)

    def test_missing_public_origin_is_rejected(self) -> None:
        env = os.environ.copy()
        env.pop("HOMOLOG_PUBLIC_BASE_URL", None)
        result = subprocess.run(
            [sys.executable, str(ORIGIN_VALIDATOR)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ausente ou inválida", result.stderr)

    def test_valid_public_origin_is_accepted_without_printing_value(self) -> None:
        value = "https://markina.example.com"
        env = os.environ.copy()
        env["HOMOLOG_PUBLIC_BASE_URL"] = value
        result = subprocess.run(
            [sys.executable, str(ORIGIN_VALIDATOR)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(value, result.stdout + result.stderr)

    def test_origin_mismatch_stops_before_service_or_database_queries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project, env, docker_calls = self._prepare_checkout(root)
            config_file = root / "compose-config.json"
            config_file.write_text(
                """{
                  "name": "markina-gallery",
                  "services": {
                    "nginx": {},
                    "api": {"environment": {
                      "APP_ENV": "homolog",
                      "DATABASE_URL": "postgresql://test@db/markina",
                      "PUBLIC_APP_ORIGIN": "https://actual.example.com"
                    }},
                    "db": {"environment": {"POSTGRES_DB": "markina"}},
                    "redis": {}
                  }
                }""",
                encoding="utf-8",
            )
            env["MOCK_COMPOSE_CONFIG"] = str(config_file)
            sha = subprocess.check_output(
                ["git", "-C", str(project), "rev-parse", "HEAD"], text=True
            ).strip()
            result = subprocess.run(
                [self._bash(), str(root / "inventory-homolog-readonly.sh"),
                 "--expected-sha", sha, "--expected-public-base-url",
                 "https://expected.example.com"],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("origem esperada diverge", result.stderr)
            calls = docker_calls.read_text(encoding="utf-8")
            self.assertIn("config --format json", calls)
            self.assertNotIn(" ps", calls)
            self.assertNotIn(" run ", calls)
            self.assertNotIn("actual.example.com", result.stdout + result.stderr)

    def test_script_and_workflow_have_fixed_readonly_scope(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('readonly PROJECT_ROOT="/opt/markina-gallery"', script)
        self.assertIn('readonly PROJECT_NAME="markina-gallery"', script)
        self.assertIn('readonly COMPOSE_FILE="docker/docker-compose.yml"', script)
        self.assertIn('readonly ENV_FILE="docker/.env.homolog"', script)
        self.assertIn('"/var/lib/markina/source": "media-source"', script)
        self.assertIn('"volume não externo {source}"', script)
        self.assertEqual(script.count("compose run --rm --no-deps"), 1)
        for forbidden in (
            "docker compose down",
            "docker compose up",
            "docker system prune",
            "alembic upgrade",
            "git pull",
            "git reset",
        ):
            self.assertNotIn(forbidden, script)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertNotIn("\n  pull_request:", workflow)
        self.assertIn("StrictHostKeyChecking=yes", workflow)
        self.assertIn("environment: homolog", workflow)
        self.assertIn("expected_sha", workflow)
        self.assertIn("HOMOLOG_PUBLIC_BASE_URL", workflow)
        self.assertLess(
            workflow.index("Validar origem pública homologada"),
            workflow.index("Executar inventário somente leitura"),
        )
        self.assertIn("--expected-public-base-url", workflow)
        self.assertIn('"$public_base_url/healthz"', workflow)
        self.assertIn('"$public_base_url/api/health"', workflow)
        self.assertNotIn("markina-homolog.duckdns.org", workflow + script)


if __name__ == "__main__":
    unittest.main()
