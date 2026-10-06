"""Testes de política do inventário remoto somente leitura de homologação."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "inventory-homolog-readonly.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "inventory-homolog-readonly.yml"


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
        bin_dir = root / "bin"
        bin_dir.mkdir()
        docker_calls = root / "docker-calls.log"
        docker_stub = bin_dir / "docker"
        docker_stub.write_text(
            f'#!/usr/bin/env bash\nprintf "called\\n" >> "{self._shell_path(docker_calls)}"\n',
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
                [self._bash(), str(root / "inventory-homolog-readonly.sh"), "--expected-sha", "0" * 40],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("HEAD implantado diverge", result.stderr)
            self.assertIn("nenhuma consulta foi executada", result.stderr)
            self.assertFalse(docker_calls.exists())

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
        self.assertIn("https://markina-homolog.duckdns.org/healthz", workflow)
        self.assertIn("https://markina-homolog.duckdns.org/api/health", workflow)


if __name__ == "__main__":
    unittest.main()
