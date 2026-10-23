#!/usr/bin/env python3
"""Separa manutenção autorizada dos gates de primeira ativação facial."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RUNTIME_FILES = (
    "backend/app/auth.py",
    "backend/app/facial/config.py",
    "backend/app/facial/provider.py",
    "backend/app/facial/reference.py",
    "backend/app/facial/search.py",
    "backend/app/facial/search_worker.py",
    "backend/app/main.py",
    "backend/migrations/versions/20261016_0082_facial_conditional_consent.py",
    "frontend/app/globals.css",
    "frontend/app/facial-search-client.ts",
    "frontend/app/public-galleries/facial-search-panel.tsx",
    "frontend/app/gallery-presentation.tsx",
    "frontend/app/public-galleries/[galleryId]/page.tsx",
    "docker/docker-compose.yml",
)
OPERATIONS_FILES = {
    ".github/workflows/ci.yml", ".gitleaksignore",
    "scripts/check_prod_facial_release_gates.py",
    "scripts/check_prod_app_release_scope.py",
    "scripts/classify_prod_release.py",
    "scripts/test_classify_prod_release.py",
    "scripts/deploy-prod-app-services.sh",
    "scripts/test_prod_app_release_scope.py",
    "scripts/test_deploy_prod_app_services.sh",
    "scripts/deploy-prod-facial-services.sh",
    "scripts/production-preflight-ssh-wrapper.sh",
    "scripts/test_deploy_homolog_policy.py",
    "scripts/test_deploy_prod_facial_services.sh",
    "scripts/test_production_release_workflow_policy.py",
    "backend/tests/test_derived_galleries.py",
    "backend/tests/test_statistics_report.py",
    "frontend/app/admin/statistics/page.test.tsx",
    "scripts/test_prod_facial_release_gates.py",
    "backend/tests/test_facial_integration.py",
    "backend/tests/test_direct_region_search.py",
    "backend/tests/test_tenant_facial_maintenance.py",
    "backend/tests/test_facial_provider.py",
    "backend/tests/test_facial_conditional_consent_migration.py",
    "backend/tests/test_facial_search.py",
    "backend/tests/test_facial_search_worker.py",
    "backend/tests/test_facial_config.py",
    "frontend/app/facial-search-client.test.ts",
    "frontend/app/public-galleries/facial-search-panel.test.tsx",
    "frontend/app/public-galleries/public-gallery.test.tsx",
    "frontend/app/gallery-presentation.test.tsx",
}
APP_RUNTIME_FILES = {
    "backend/app/main.py",
    "backend/app/statistics_report.py",
    "frontend/app/globals.css",
    "frontend/app/admin/statistics/page.tsx",
}


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def evaluate_maintenance(payload: dict, root: Path) -> tuple[bool, str]:
    maintenance = payload.get("maintenance_release", {})
    if not isinstance(maintenance, dict) or maintenance.get("authorized") is not True:
        return False, "autorizacao_de_manutencao_ausente"
    if maintenance.get("scope") != "existing_facial_runtime":
        return False, "escopo_de_manutencao_invalido"
    evidence = maintenance.get("evidence")
    baseline = maintenance.get("baseline_sha", "")
    if not isinstance(evidence, str) or not evidence.strip():
        return False, "evidencia_de_autorizacao_ausente"
    if not isinstance(baseline, str) or not re.fullmatch(r"[0-9a-f]{40}", baseline):
        return False, "baseline_invalido"
    blobs = maintenance.get("runtime_blobs")
    if not isinstance(blobs, dict) or set(blobs) != set(RUNTIME_FILES):
        return False, "manifesto_de_runtime_incompleto"
    try:
        git(root, "merge-base", "--is-ancestor", baseline, "HEAD")
        app_manifest = json.loads(
            (Path(__file__).resolve().parents[1] / "openspec/changes/add-production-app-release-workflow/runtime-gates.json")
            .read_text(encoding="utf-8")
        )
        app_blobs = app_manifest.get("runtime_blobs", {})
        for path in git(root, "diff", "--name-only", baseline, "HEAD").splitlines():
            if path in RUNTIME_FILES or path in OPERATIONS_FILES:
                continue
            if path in APP_RUNTIME_FILES and app_blobs.get(path) == git(root, "rev-parse", "HEAD:" + path):
                continue
            if path.startswith(("docs/", "openspec/")):
                continue
            return False, "arquivo_fora_do_escopo"
        for path, expected in blobs.items():
            try:
                encoded = "".join(expected) if isinstance(expected, list) and all(
                    isinstance(part, str) for part in expected
                ) else ""
                decoded = base64.b64decode(encoded, validate=True) if encoded else b""
            except (ValueError, binascii.Error):
                decoded = b""
            if len(decoded) != 20:
                return False, "blob_revisado_invalido"
            actual = git(root, "rev-parse", "HEAD:" + path)
            if path in APP_RUNTIME_FILES and actual != decoded.hex():
                if app_blobs.get(path) != actual:
                    return False, "runtime_diverge_do_blob_revisado"
            elif actual != decoded.hex():
                return False, "runtime_diverge_do_blob_revisado"
        git(root, "diff", "--quiet", "HEAD", "--", *RUNTIME_FILES)
    except subprocess.CalledProcessError:
        return False, "historico_ou_runtime_nao_comprovado"
    return True, "manutencao_autorizada_sem_ativacao"


def activation_status(payload: dict) -> tuple[bool, list[str]]:
    gates = payload.get("gates")
    ready = payload.get("release_ready") is True and isinstance(gates, dict) and bool(gates)
    pending = []
    for name, gate in (gates.items() if isinstance(gates, dict) else []):
        if (not isinstance(gate, dict) or gate.get("status") != "aprovado"
                or not isinstance(gate.get("evidence"), str)
                or not gate["evidence"].strip()):
            ready = False
            pending.append(str(name))
    return ready, pending


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="openspec/changes/improve-client-face-reference-capture/production-gates.json")
    parser.add_argument("--maintenance", action="store_true")
    args = parser.parse_args()
    payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
    ready, pending = activation_status(payload)
    reason = "ativacao_aprovada" if ready else "gates_de_ativacao_pendentes"
    if args.maintenance:
        ready, reason = evaluate_maintenance(payload, Path(__file__).resolve().parents[1])
    value = "true" if ready else "false"
    print("release_scope=" + ("maintenance_existing_runtime" if args.maintenance else "activation"))
    print("release_ready=" + value)
    print("criterio=" + reason)
    print("gates_de_ativacao_pendentes=" + (",".join(pending) if pending else "nenhum"))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write("release_ready=" + value + "\n")
    if args.maintenance and ready:
        print("Elegível somente para manutenção do runtime já ativo; não aprova ativação ou expansão.")
    return 1 if args.maintenance and not ready else 0


if __name__ == "__main__":
    sys.exit(main())
