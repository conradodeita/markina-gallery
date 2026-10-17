#!/usr/bin/env python3
"""Fail-closed scope check for the commercial API/web production release."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "openspec/changes/add-production-app-release-workflow/runtime-gates.json"
RUNTIME_FILES = {
    "backend/app/main.py",
    "backend/app/statistics_report.py",
    "frontend/app/globals.css",
    "frontend/app/admin/statistics/page.tsx",
}
ALLOWED_PREFIXES = ("backend/tests/", "frontend/app/admin/statistics/", "openspec/", "docs/")
ALLOWED_OPERATIONS = {
    ".github/workflows/ci.yml",
    "scripts/check_prod_app_release_scope.py",
    "scripts/deploy-prod-app-services.sh",
    "scripts/production-preflight-ssh-wrapper.sh",
    "scripts/test_prod_app_release_scope.py",
    "scripts/test_deploy_prod_app_services.sh",
    "scripts/test_production_release_workflow_policy.py",
    "scripts/check_prod_facial_release_gates.py",
    "scripts/deploy-prod-facial-services.sh",
    "scripts/test_prod_facial_release_gates.py",
    "scripts/test_deploy_prod_facial_services.sh",
    "openspec/changes/improve-client-face-reference-capture/production-gates.json",
    "openspec/changes/improve-client-face-reference-capture/tasks.md",
    "openspec/changes/improve-client-face-reference-capture/specs/deployment-operations/spec.md",
}


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def evaluate(root: Path, base: str, target: str, manifest: dict) -> tuple[bool, str]:
    if set(manifest.get("runtime_blobs", {})) != RUNTIME_FILES:
        return False, "manifesto_runtime_incompleto"
    try:
        git(root, "merge-base", "--is-ancestor", base, target)
        changed = set(git(root, "diff", "--name-only", base, target).splitlines())
        for path in changed:
            if path in RUNTIME_FILES or path in ALLOWED_OPERATIONS or path.startswith(ALLOWED_PREFIXES):
                continue
            return False, "arquivo_fora_do_escopo"
        for path, expected in manifest["runtime_blobs"].items():
            actual = git(root, "rev-parse", f"{target}:{path}")
            if actual != expected:
                return False, "runtime_diverge_do_blob_aprovado"
        return True, "somente_api_web"
    except (subprocess.CalledProcessError, KeyError, TypeError):
        return False, "historico_ou_runtime_nao_comprovado"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD^", help="SHA da revisão ativa/base de comparação")
    parser.add_argument("--target", default="HEAD", help="SHA candidato")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    ready, reason = evaluate(ROOT, args.base, args.target, manifest)
    print(f"app_release_ready={'true' if ready else 'false'}")
    print(f"criterio={reason}")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
