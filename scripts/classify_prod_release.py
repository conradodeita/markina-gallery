#!/usr/bin/env python3
"""Classify main changes so app and facial releases never share approval."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from dependency_release import impact, is_dependency_manifest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "openspec/changes/add-production-app-release-workflow/runtime-gates.json"

APP_RUNTIME = {
    "backend/app/main.py",
    "backend/app/statistics_report.py",
    "backend/app/private_folder_overview.py",
    "frontend/app/globals.css",
    "frontend/app/admin/statistics/page.tsx",
    "frontend/app/admin/galleries/private-folder-client-overview.tsx",
    "frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx",
}
FACIAL_RUNTIME = {
    "backend/app/auth.py",
    "backend/app/facial/config.py",
    "backend/app/facial/provider.py",
    "backend/app/facial/reference.py",
    "backend/app/facial/search.py",
    "backend/app/facial/search_worker.py",
    "backend/migrations/versions/20261016_0082_facial_conditional_consent.py",
    "frontend/app/facial-search-client.ts",
    "frontend/app/public-galleries/facial-search-panel.tsx",
    "frontend/app/gallery-presentation.tsx",
    "frontend/app/public-galleries/[galleryId]/page.tsx",
    "docker/docker-compose.yml",
}


def changed_paths(base: str, target: str) -> set[str]:
    result = subprocess.run(["git", "diff", "--name-only", base, target], check=True,
                            capture_output=True, text=True)
    return set(result.stdout.splitlines())


def git_is_ancestor(base: str, target: str, *, root: Path = ROOT) -> bool:
    result = subprocess.run(["git", "merge-base", "--is-ancestor", base, target], cwd=root,
                            check=False, capture_output=True)
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    return result.returncode == 0


def classify_from_baseline(changed: set[str], *, baseline_is_ancestor: bool) -> str:
    """Classify only commits after the verified production runtime."""
    if not baseline_is_ancestor:
        return "none"
    return classify(changed)


def production_baseline(target: str) -> str:
    result = subprocess.run(["git", "show", f"{target}:{MANIFEST_PATH}"], cwd=ROOT,
                            check=True, capture_output=True, text=True)
    manifest = json.loads(result.stdout)
    return production_baseline_from_manifest(manifest)


def production_baseline_from_manifest(manifest: dict) -> str:
    baseline = manifest.get("production_baseline_sha")
    revision = manifest.get("expected_database_revision")
    if not isinstance(baseline, str) or len(baseline) != 40 or any(ch not in "0123456789abcdef" for ch in baseline):
        raise ValueError("baseline SHA de produção ausente ou inválido no manifesto alvo")
    if not isinstance(revision, str) or len(revision) != 13 or revision[8] != "_" \
            or not revision[:8].isdigit() or not revision[9:].isdigit():
        raise ValueError("revisão de banco esperada ausente ou inválida no manifesto alvo")
    return baseline


def classify(changed: set[str]) -> str:
    app = bool(changed & APP_RUNTIME)
    facial = bool(changed & FACIAL_RUNTIME)
    if any("/Dockerfile" in p or p.endswith(".dockerignore") or p.startswith("docker/") or p.startswith("backend/facial-assets/")
           or p.startswith("backend/migrations/")
           or (p.startswith("backend/app/") and "worker" in p and p not in FACIAL_RUNTIME) for p in changed):
        return "protected"
    if any(is_dependency_manifest(p) for p in changed):
        return "mixed" if app or facial else "dependencies"
    if app and facial:
        return "mixed"
    if app:
        return "app"
    if facial:
        return "facial"
    return "none"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    baseline = production_baseline(args.target)
    if not git_is_ancestor(args.base, args.target):
        raise ValueError("SHA anterior do evento não é ancestral do alvo")
    baseline_is_ancestor = git_is_ancestor(baseline, args.target, root=ROOT)
    changed = changed_paths(baseline, args.target) if baseline_is_ancestor else set()
    scope = classify_from_baseline(changed, baseline_is_ancestor=baseline_is_ancestor)
    print(f"release_baseline_sha={baseline}")
    print(f"release_scope={scope}")
    if scope == "dependencies":
        print("dependency_impact=" + json.dumps(impact(ROOT, baseline, args.target), sort_keys=True))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"release_scope={scope}\n")
            handle.write(f"base_sha={baseline}\n")
    return 1 if scope in {"mixed", "protected"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
