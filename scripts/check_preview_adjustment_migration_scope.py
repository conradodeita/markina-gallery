#!/usr/bin/env python3
"""Fail-closed scope gate for the one-time preview-strength migration release."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from preview_adjustment_migration_inventory import select_candidate_ci

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "c1944189761799be96eeeb921cad9906484d8b09"
CANDIDATE_SHA = "0dd015a62447e0c8d4c6af16b381140c8118f2ec"
BASE_REVISION = "20261025_0089"
TARGET_REVISION = "20261026_0090"
MIGRATION = "backend/migrations/versions/20261026_0090_preview_adjustment_strength_100.py"

# Paths are the complete runtime/documentation delta from the recorded healthy
# runtime to the reviewed candidate. The payment layout touched by PR #295 and
# the checkout UI updates from PR #297 are listed because they are already
# integrated into this candidate; no further paths are accepted.
ALLOWED_CANDIDATE_PATHS = {
    "backend/app/auth.py",
    "backend/app/folder_processing.py",
    "backend/app/folder_processing_api.py",
    "backend/app/preview_adjustment/api.py",
    MIGRATION,
    "backend/tests/test_folder_processing_api.py",
    "backend/tests/test_preview_adjustment.py",
    "backend/tests/test_preview_adjustment_strength_migration.py",
    "docs/MODULO-AJUSTE-DE-PREVIAS.md",
    "frontend/app/admin/galleries/folder-processing-panel.test.tsx",
    "frontend/app/admin/galleries/folder-processing-panel.tsx",
    "frontend/app/admin/payments/payments.module.css",
    "frontend/app/library/checkout/card-payment.test.tsx",
    "frontend/app/library/checkout/card-payment.tsx",
    "frontend/app/library/checkout/checkout.module.css",
    "openspec/changes/expand-preview-adjustment-strength-range/.openspec.yaml",
    "openspec/changes/expand-preview-adjustment-strength-range/design.md",
    "openspec/changes/expand-preview-adjustment-strength-range/proposal.md",
    "openspec/changes/expand-preview-adjustment-strength-range/specs/media-storage/gallery-preview-adjustment/spec.md",
    "openspec/changes/expand-preview-adjustment-strength-range/tasks.md",
    "openspec/changes/add-mercadopago-orders-checkout/external-validation.md",
    "openspec/changes/fix-card-brick-readiness/design.md",
    "openspec/changes/fix-card-brick-readiness/proposal.md",
    "openspec/changes/fix-card-brick-readiness/specs/card-brick-readiness/spec.md",
    "openspec/changes/fix-card-brick-readiness/tasks.md",
    "openspec/changes/fix-card-brick-readiness/validation.md",
    "openspec/changes/fix-orders-payment-details-overflow/design.md",
    "openspec/changes/fix-orders-payment-details-overflow/proposal.md",
    "openspec/changes/fix-orders-payment-details-overflow/specs/payment-detail-containment/spec.md",
    "openspec/changes/fix-orders-payment-details-overflow/tasks.md",
    "openspec/changes/fix-orders-payment-details-overflow/validation.md",
    "openspec/changes/retire-lightcraft-and-gemma/deployment.md",
    "openspec/changes/retire-lightcraft-and-gemma/tasks.md",
}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def changed_paths(root: Path, base: str, target: str) -> set[str]:
    return set(git(root, "diff", "--name-only", "--diff-filter=ACDMRTUXB", base, target).splitlines())


def evaluate(paths: set[str], base: str, target: str, ci_conclusion: str,
             migration_source: str, main_contains_candidate: bool = True) -> tuple[bool, str]:
    if base != BASE_SHA:
        return False, "baseline_sha_divergente"
    if target != CANDIDATE_SHA:
        return False, "candidato_sha_divergente"
    if not main_contains_candidate:
        return False, "candidato_nao_integrado_a_main"
    if ci_conclusion != "success":
        return False, "ci_nao_verde"
    if paths != ALLOWED_CANDIDATE_PATHS:
        return False, "diff_fora_da_allowlist"
    if MIGRATION not in paths:
        return False, "migration_0090_ausente"
    if not re.search(rf'^revision\s*=\s*[\"\']{TARGET_REVISION}[\"\']\s*$', migration_source, re.M):
        return False, "revision_alvo_divergente"
    if not re.search(rf'^down_revision\s*=\s*[\"\']{BASE_REVISION}[\"\']\s*$', migration_source, re.M):
        return False, "cadeia_alembic_divergente"
    return True, "migration_preview_adjustment_0090_aprovada"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--ci-conclusion", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        request = Request(
            'https://api.github.com/repos/conradodeita/markina-gallery/actions/runs?head_sha='
            + CANDIDATE_SHA + '&per_page=100',
            headers={'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'},
        )
        with urlopen(request, timeout=20) as response:
            if not response.geturl().startswith('https://api.github.com/'):
                raise ValueError('fonte_ci_divergente')
            payload = response.read(2 * 1024 * 1024 + 1)
        if len(payload) > 2 * 1024 * 1024:
            raise ValueError('resposta_ci_excessiva')
        ci = select_candidate_ci(json.loads(payload)['workflow_runs'])
    except Exception:
        print('preview_migration_release_ready=false')
        print('criterio=ci_candidato_nao_verificado_ou_nao_verde')
        return 1
    try:
        git(args.root, "merge-base", "--is-ancestor", args.target, "origin/main")
        main_contains = True
    except subprocess.CalledProcessError:
        main_contains = False
    try:
        paths = changed_paths(args.root, args.base, args.target)
        migration = git(args.root, "show", f"{args.target}:{MIGRATION}")
    except subprocess.CalledProcessError:
        paths, migration = set(), ""
    ready, reason = evaluate(paths, args.base, args.target, args.ci_conclusion,
                             migration, main_contains)
    print(f"preview_migration_release_ready={'true' if ready else 'false'}")
    print(f"criterio={reason}")
    print(f"ci_candidato_run={ci['run_id']}")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
