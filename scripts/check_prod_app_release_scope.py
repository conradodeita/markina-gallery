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
    "backend/app/client_lifecycle.py",
    "backend/app/auth.py",
    "backend/app/main.py",
    "backend/app/google_drive_client.py",
    "backend/app/google_drive_picker.py",
    "backend/app/platform_backup/archive.py",
    "backend/app/platform_backup/catalog.py",
    "backend/app/platform_backup/filesystem.py",
    "backend/app/platform_backup/offline_recovery.py",
    "backend/app/platform_backup/payload.py",
    "backend/app/platform_backup/production_cli.py",
    "backend/app/platform_backup/remote_copy.py",
    "backend/app/platform_backup/restore.py",
    "backend/app/platform_backup/runtime_config.py",
    "backend/app/platform_backup/runtime_source.py",
    "backend/app/platform_backup/runtime_worker.py",
    "backend/app/platform_backup/workspace_store.py",
    "backend/app/payment_availability.py",
    "backend/app/order_visibility.py",
    "backend/app/payment_export.py",
    "backend/app/statistics_report.py",
    "backend/app/private_folder_overview.py",
    "backend/app/unified_checkout.py",
    "docker/docker-compose.yml",
    "frontend/app/globals.css",
    "frontend/app/admin/admin-navigation.tsx",
    "frontend/app/admin/payments/page.tsx",
    "frontend/app/admin/payments/order-photos.tsx",
    "frontend/app/admin/payments/payments.module.css",
    "frontend/app/admin/galleries/private-folder-client-overview.tsx",
    "frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx",
    "frontend/app/admin/galleries/[galleryId]/orders/page.tsx",
    "frontend/app/admin/platform/google-drive-folder-picker.tsx",
    "frontend/app/admin/platform/page.tsx",
    "frontend/app/admin/platform/use-console-access.ts",
    "frontend/app/admin/platform/console-link.tsx",
    "frontend/app/library/cart/page.tsx",
    "frontend/app/library/purchase-card.tsx",
    "frontend/app/library/purchases/page.tsx",
}
BACKUP_SUPPORT_FILES = {
    "scripts/backup_runtime/pyp-platform-backup.service",
    "scripts/backup_runtime/pyp-platform-backup.timer",
    "scripts/backup_runtime/requirements-py310-arm64.lock",
}
RETIRED_BACKUP_FILES = {
    "backend/app/google_drive_picker.py",
    "frontend/app/admin/platform/google-drive-folder-picker.tsx",
    ".github/workflows/production-google-picker-config.yml",
    ".github/workflows/production-platform-backup-runtime.yml",
    ".github/workflows/production-platform-backup-wrapper-install.yml",
    "scripts/build_platform_backup_runtime.sh",
    "scripts/install-prod-platform-backup-wrapper.sh",
    "scripts/install_platform_backup_runtime.py",
    "scripts/platform_backup_runtime_artifact.py",
    "scripts/platform_backup_runtime_inventory.py",
    "scripts/platform_backup_wrapper_restore.py",
}
RETIRED_STATISTICS_FILES = {
    "frontend/app/admin/statistics/page.tsx",
    "frontend/app/admin/statistics/page.test.tsx",
}
RETIRED_INFINITEPAY_FILES = {
    "backend/app/infinitepay_binding.py",
    "backend/app/infinitepay_settings.py",
    "backend/app/payment_provider.py",
    "backend/app/provider_cart_recovery.py",
    "backend/app/provider_checkout.py",
    "frontend/app/admin/payments/cart-recovery.module.css",
    "frontend/app/admin/payments/cart-recovery.tsx",
    "frontend/app/admin/settings/infinitepay-panel.tsx",
    "frontend/app/library/cart/checkout-navigation.ts",
}
ALLOWED_PREFIXES = (
    "backend/tests/",
    "openspec/",
    "docs/",
)
RETIRED_HOMOLOG_WORKFLOWS = {
    ".github/workflows/facial-rollout-homolog.yml",
    ".github/workflows/inventory-homolog-readonly.yml",
    ".github/workflows/maintenance-homolog.yml",
}
ALLOWED_OPERATIONS = {
    ".env.example",
    "AGENTS.md",
    "DEPLOY.md",
    "README.md",
    "frontend/app/public-galleries/public-gallery.test.tsx",
    "scripts/backend_ci.py",
    "scripts/backend_ci_durations.json",
    "scripts/check_backend_ci_results.py",
    "scripts/ci_feedback.py",
    "scripts/ci_local.py",
    "scripts/classify_ci_scope.py",
    "scripts/resume-homolog.sh",
    "scripts/test_backend_ci.py",
    "scripts/test_check_backend_ci_results.py",
    "scripts/test_ci_feedback.py",
    "scripts/test_ci_local.py",
    "scripts/test_ci_workflow_policy.py",
    "scripts/test_classify_ci_scope.py",
    "scripts/test_resume_homolog_policy.py",

    ".gitleaksignore",
    ".github/workflows/ci.yml",
    ".github/workflows/production-app-compose-bridge-install.yml",
    ".github/workflows/production-app-runtime-adoption.yml",
    ".github/workflows/production-app-handoff-recovery.yml",
    ".github/workflows/production-platform-backup-runtime.yml",
    ".github/workflows/production-platform-backup-wrapper-install.yml",
    "scripts/check_prod_app_release_scope.py",
    "scripts/reset_homolog_owner.py",
    "scripts/classify_prod_release.py",
    "scripts/deploy-prod-app-services.sh",
    "scripts/export_prod_app_api_base_image.sh",
    "scripts/production-app-artifact-ssh-wrapper.sh",
    "scripts/production_app_artifact.py",
    "scripts/production_app_compose_bridge.py",
    "scripts/production_app_preflight_support.py",
    "scripts/test_prod_app_api_base_image_export.py",
    "scripts/test_production_app_artifact.py",
    "scripts/test_production_app_artifact_ssh_wrapper.py",
    "scripts/test_production_app_compose_bridge.py",
    "scripts/test_production_app_preflight_support.py",
    "scripts/test_production_app_preflight_support_workflow.py",
    "scripts/test_platform_backup_runtime_workflow.py",
    "scripts/test_production_app_runtime_adoption.py",
    "scripts/test_production_app_first_handoff.py",
    "scripts/test_production_app_handoff_inventory.py",
    "scripts/test_production_app_handoff_journal.py",
    "scripts/test_production_app_handoff_execution.py",
    "scripts/test_production_app_handoff_recovery.py",
    "scripts/test_production_app_handoff_engine.py",
    "scripts/test_production_app_handoff_cli.py",
    "scripts/test_production_app_handoff_legacy.py",
    "scripts/test_production_app_handoff_shell.py",
    "scripts/install-prod-app-compose-bridge.sh",
    "scripts/check_infinitepay_retirement_scope.py",
    "scripts/deploy-prod-infinitepay-retirement.sh",
    "scripts/test_deploy_prod_infinitepay_retirement.sh",
    "scripts/test_retirement_legacy_worker.py",
    "scripts/production-preflight-ssh-wrapper.sh",
    "scripts/test_prod_app_release_scope.py",
    "scripts/test_classify_prod_release.py",
    "scripts/test_deploy_prod_app_services.sh",
    "scripts/test_production_release_workflow_policy.py",
    "scripts/verify_main_ci_evidence.py",
    "scripts/test_verify_main_ci_evidence.py",
    "scripts/build_python_security_candidates.py",
    "scripts/python_security_release.py",
    "scripts/test_python_security_release.py",
    "scripts/prepare_emergency_api_image.py",
    "scripts/test_prepare_emergency_api_image.py",
    "scripts/check_prod_facial_release_gates.py",
    "scripts/deploy-prod-facial-services.sh",
    "scripts/test_prod_facial_release_gates.py",
    "scripts/test_deploy_prod_facial_services.sh",
    "scripts/deploy-prod-lock.sh",
    "scripts/deploy-prod-state.sh",
    "scripts/test_prod_release_state.py",
    "scripts/deploy-prod-web.sh",
    "scripts/test_deploy_prod_web.sh",
    "scripts/test_deploy_prod_web_policy.py",
    "frontend/app/admin/galleries/gallery-editor.test.tsx",
    "frontend/app/admin/galleries/private-folder-client-overview.test.tsx",
    "frontend/app/admin/admin-navigation.test.tsx",
    "frontend/app/admin/payments/page.test.tsx",
    "frontend/app/admin/payments/order-photos.test.tsx",
    "frontend/app/admin/payments/redesign.test.tsx",
    "frontend/app/admin/galleries/[galleryId]/orders/orders.test.tsx",
    "frontend/app/library/cart/cart.test.tsx",
    "frontend/app/library/cart/checkout-navigation.test.ts",
    "frontend/app/library/library.test.tsx",
    "frontend/app/admin/retirement.test.ts",
    "frontend/app/admin/platform/page.test.tsx",
    "frontend/scripts/payments-visual-qa.cjs",
    "RELATORIO_IMPLEMENTACAO_VENDAS_PAGAMENTOS.md",
    "design-qa.md",
    "INSTRUCOES_EXECUTOR_CLAUDE_CODE.md",
    "ROADMAP_ARQUITETURA.md",
    *RETIRED_STATISTICS_FILES,
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
        statuses = {}
        for line in git(root, "diff", "--name-status", "--no-renames", base, target).splitlines():
            status, path = line.split("\t", 1)
            statuses[path] = status
        changed = set(statuses)
        backup_support_blobs = manifest.get("support_blobs", {})
        if changed & BACKUP_SUPPORT_FILES:
            if set(backup_support_blobs) != BACKUP_SUPPORT_FILES:
                return False, "manifesto_suporte_backup_incompleto"
            if changed & BACKUP_SUPPORT_FILES != BACKUP_SUPPORT_FILES:
                return False, "retirada_suporte_backup_incompleta"
            for path, expected in backup_support_blobs.items():
                ref = base if statuses[path] == "D" else target
                actual = git(root, "rev-parse", f"{ref}:{path}")
                if actual != expected:
                    return False, "suporte_backup_diverge_do_blob_aprovado"
        emergency = manifest.get("emergency_api")
        extra_blobs = {}
        if emergency is not None:
            api_base = emergency["baseline_sha"]
            git(root, "merge-base", "--is-ancestor", api_base, target)
            extra_blobs = emergency["input_blobs"]
            if set(extra_blobs) != {"backend/requirements-push.txt"}:
                return False, "inputs_emergenciais_invalidos"
            api_changes = set(git(root, "diff", "--name-only", api_base, target, "--", "backend/").splitlines())
            for path in api_changes:
                if path not in RUNTIME_FILES and path not in extra_blobs and not path.startswith("backend/tests/"):
                    return False, "api_fora_do_escopo"
            changed |= api_changes
        for path in changed:
            if path in RETIRED_BACKUP_FILES or path.startswith(("backend/app/platform_backup/", "backend/tests/test_platform_backup_",
                                                                 "scripts/backup_runtime/", "scripts/test_platform_backup_")):
                if statuses.get(path) == "D":
                    continue
                if path not in ALLOWED_OPERATIONS and path not in RUNTIME_FILES and path not in BACKUP_SUPPORT_FILES:
                    return False, "arquivo_fora_do_escopo"
                # Preserve already reviewed historical snapshots; new content
                # is still classified as protected and cannot auto-publish.
            if path in RETIRED_INFINITEPAY_FILES or path in RETIRED_HOMOLOG_WORKFLOWS:
                if statuses[path] != "D":
                    return False, "arquivo_fora_do_escopo"
                continue
            if (path in RUNTIME_FILES or path in extra_blobs or path in BACKUP_SUPPORT_FILES
                    or path in ALLOWED_OPERATIONS or path.startswith(ALLOWED_PREFIXES)):
                continue
            return False, "arquivo_fora_do_escopo"
        for path, expected in {**manifest["runtime_blobs"], **extra_blobs}.items():
            ref = base if statuses.get(path) == "D" else target
            actual = git(root, "rev-parse", f"{ref}:{path}")
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
