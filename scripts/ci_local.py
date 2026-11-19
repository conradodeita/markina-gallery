"""Run fast, path-aware local checks before pushing a Pick-your-Pic change."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.classify_ci_scope import classify

SCOPE_TESTS = (
    "scripts.test_classify_ci_scope",
    "scripts.test_check_ci_results",
    "scripts.test_check_backend_ci_results",
    "scripts.test_ci_feedback",
    "scripts.test_ci_workflow_policy",
    "scripts.test_ci_local",
)


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]


def _git_paths(root: Path, *args: str) -> set[str]:
    result = subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return {line.replace("\\", "/") for line in result.stdout.splitlines() if line}


def _node_command(name: str) -> str:
    """Resolve npm/npx command shims when subprocess runs on Windows."""
    return f"{name}.cmd" if sys.platform == "win32" else name


def changed_paths(base: str, root: Path = ROOT) -> list[str]:
    """Include the base-to-HEAD diff plus staged, unstaged, and untracked files."""
    if not base.strip():
        raise ValueError("A base ref is required; pass --base or --paths")
    paths = _git_paths(root, "diff", "--name-only", f"{base}...HEAD")
    paths.update(_git_paths(root, "diff", "--name-only", "HEAD"))
    paths.update(_git_paths(root, "ls-files", "--others", "--exclude-standard"))
    return sorted(paths)


def plan_checks(paths: list[str]) -> tuple[list[Check], list[str]]:
    """Plan quick local checks without treating them as substitutes for full CI."""
    if not paths:
        return [], []

    scopes = classify(paths)
    checks: list[Check] = []
    pending: list[str] = []
    python_paths = sorted({
        path for path in paths
        if path.endswith(".py") and not path.startswith(("openspec/", "docs/"))
        and (ROOT / path).is_file()
    })
    has_ci_or_scripts = any(
        path.startswith(("scripts/", ".github/workflows/"))
        for path in paths
    )
    has_openspec = any(path.startswith("openspec/") for path in paths)
    changes = sorted({
        path.split("/", 3)[2].split("/", 1)[0]
        for path in paths
        if path.startswith("openspec/changes/") and len(path.split("/", 3)) >= 3
    })

    if has_ci_or_scripts:
        checks.append(Check(
            "contratos rápidos de CI",
            (sys.executable, "-m", "unittest", *SCOPE_TESTS, "-q"),
        ))
    if python_paths:
        checks.append(Check("Ruff nos módulos Python alterados", ("ruff", "check", *python_paths)))
    if scopes["backend"] and any(path.startswith("backend/") for path in paths):
        checks.append(Check("Ruff do backend", ("ruff", "check", "backend/app", "backend/tests")))
    if scopes["frontend"]:
        checks.append(Check(
            "lint do frontend",
            (_node_command("npm"), "run", "lint", "--prefix", "frontend"),
        ))
    if has_openspec:
        cli = (_node_command("npx"), "-y", "@fission-ai/openspec@1.14.0", "validate")
        if changes:
            checks.extend(Check(
                f"OpenSpec estrito: {change}",
                (*cli, change, "--strict", "--no-interactive"),
            ) for change in changes)
        else:
            checks.append(Check("OpenSpec estrito", (*cli, "--all", "--strict", "--no-interactive")))

    if scopes["backend_tests"]:
        pending.append("suíte completa backend; obrigatória no CI porque não há mapa de impacto validado")
    if scopes["frontend"]:
        pending.append("testes e build do frontend; obrigatórios no CI")
    for scope in ("backend_image", "frontend_image", "preview"):
        if scopes[scope]:
            pending.append(f"build de imagem para o escopo {scope}; obrigatório no CI")
    if has_ci_or_scripts:
        pending.append("gates completos de scripts/workflow e Gitleaks do SHA no GitHub Actions")
    return checks, pending


def run_checks(checks: list[Check], *, root: Path = ROOT, dry_run: bool = False) -> int:
    for check in checks:
        print(f"\n==> {check.name}: {' '.join(check.command)}", flush=True)
        if dry_run:
            continue
        result = subprocess.run(list(check.command), cwd=root, check=False)
        if result.returncode:
            print(f"Falha em {check.name} (exit {result.returncode}).", file=sys.stderr)
            return result.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="Base para comparar com HEAD")
    parser.add_argument("--paths", nargs="*", help="Paths explícitos, útil para seleção determinística")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar checks sem executá-los")
    args = parser.parse_args()
    try:
        paths = sorted(set(args.paths)) if args.paths else changed_paths(args.base)
        if not paths:
            print("Nenhum path alterado encontrado.")
            return 0
        checks, pending = plan_checks(paths)
        print("Paths alterados:")
        print("\n".join(f"  {path}" for path in paths))
        if not checks:
            print("Nenhum check local rápido conhecido para esses paths.")
        result = run_checks(checks, dry_run=args.dry_run)
        if result:
            return result
        if pending:
            print("\nAinda obrigatórios no CI:")
            print("\n".join(f"  - {item}" for item in pending))
        return 0
    except (RuntimeError, ValueError) as error:
        print(f"CI local não conseguiu selecionar checks: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
