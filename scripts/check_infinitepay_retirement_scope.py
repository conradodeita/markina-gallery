#!/usr/bin/env python3
"""Fail-closed path policy for the InfinitePay retirement release."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The retirement release may contain the existing, reviewed retirement diff
# and the dedicated release machinery. Keep this list explicit: a new runtime
# path or a second migration needs a separate review before production.
RUNTIME_PATHS = {
    "backend/app/admin_account.py",
    "backend/app/auth.py",
    "backend/app/homolog_cleanup.py",
    "backend/app/integration_secrets.py",
    "backend/app/main.py",
    "backend/app/ownership_schema.py",
    "backend/app/payment_availability.py",
    "backend/app/statistics_report.py",
    "backend/app/unified_checkout.py",
    "backend/app/worker.py",
    "backend/app/infinitepay_binding.py",
    "backend/app/infinitepay_credentials.py",
    "backend/app/infinitepay_settings.py",
    "backend/app/payment_provider.py",
    "backend/app/provider_callback.py",
    "backend/app/provider_cart_recovery.py",
    "backend/app/provider_checkout.py",
    "backend/app/provider_confirmation.py",
    "backend/app/provider_pending_cart.py",
    "backend/app/rotate_infinitepay_secrets.py",
    "backend/migrations/versions/20261022_0087_retire_infinitepay.py",
    "docker/docker-compose.yml",
    "frontend/app/admin/payments/page.tsx",
    "frontend/app/admin/settings/page.tsx",
    "frontend/app/library/cart/page.tsx",
    "frontend/app/library/purchase-card.tsx",
    "frontend/app/library/purchases/page.tsx",
    "frontend/app/admin/payments/cart-recovery-page.test.tsx",
    "frontend/app/admin/payments/cart-recovery.module.css",
    "frontend/app/admin/payments/cart-recovery.test.tsx",
    "frontend/app/admin/payments/cart-recovery.tsx",
    "frontend/app/admin/settings/infinitepay-panel.test.tsx",
    "frontend/app/admin/settings/infinitepay-panel.tsx",
    "frontend/app/library/cart/checkout-navigation.test.ts",
    "frontend/app/library/cart/checkout-navigation.ts",
}

ALLOWED_EXACT = {
    ".ai-memory.toml",
    ".github/workflows/ci.yml",
    "INSTRUCOES_EXECUTOR_CLAUDE_CODE.md",
    "ROADMAP_ARQUITETURA.md",
    "scripts/check_infinitepay_retirement_scope.py",
    "scripts/test_infinitepay_retirement_scope.py",
    "scripts/retirement_inventory_policy.py",
    "scripts/test_retirement_inventory_policy.py",
    "scripts/retirement_host_references.py",
    "scripts/test_retirement_host_references.py",
    "scripts/retirement_financial_evidence.py",
    "scripts/test_retirement_financial_evidence.py",
    "scripts/retirement_binding_removal.py",
    "scripts/test_retirement_binding_removal.py",
    "scripts/retirement_pix_evidence.py",
    "scripts/test_retirement_pix_evidence.py",
    "scripts/deploy-prod-infinitepay-retirement.sh",
    "scripts/test_deploy_prod_infinitepay_retirement.sh",
    "scripts/production-preflight-ssh-wrapper.sh",
    "scripts/test_production_retirement_workflow_policy.py",
    "scripts/test_production_release_workflow_policy.py",
    "scripts/validate_retirement_approval.py",
    "scripts/test_retirement_approval.py",
    "scripts/test_classify_prod_release.py",
    "scripts/classify_prod_release.py",
    "scripts/check_prod_app_release_scope.py",
    "scripts/test_release_candidate_policy.py",
    "scripts/test_prod_app_release_scope.py",
    "scripts/deploy-prod-app-services.sh",
    "scripts/test_deploy_prod_app_services.sh",
    "scripts/check_prod_facial_release_gates.py",
    "scripts/test_prod_facial_release_gates.py",
    "scripts/deploy-prod-facial-services.sh",
    "scripts/test_deploy_prod_facial_services.sh",
    "scripts/provision_infinitepay_binding.py",
    "scripts/provision_infinitepay_keyring.py",
    "scripts/render_payments0086_ingress.py",
    "scripts/test_provision_infinitepay_binding.py",
    "scripts/test_provision_infinitepay_keyring.py",
    "scripts/test_render_payments0086_ingress.py",
    "scripts/reset_homolog_owner.py",
    "scripts/test_deploy_homolog_policy.py",
    "scripts/test_release_candidate_policy.py",
    "backend/tests/test_infinitepay_binding.py",
    "backend/tests/test_infinitepay_credential_checkout.py",
    "backend/tests/test_infinitepay_credential_management.py",
    "backend/tests/test_infinitepay_credentials_migration.py",
    "backend/tests/test_infinitepay_http_provider.py",
    "backend/tests/test_infinitepay_mixed_migration.py",
    "backend/tests/test_infinitepay_pending_cart.py",
    "backend/tests/test_infinitepay_webhook.py",
    "backend/tests/test_payment_provider.py",
    "backend/tests/test_provider_cart_recovery.py",
    "backend/tests/test_provider_cart_recovery_api.py",
    "backend/tests/test_provider_checkout.py",
    "backend/tests/test_provider_confirmation.py",
    "backend/tests/test_reopened_purchase_visibility.py",
    "backend/tests/test_tenant_infinitepay_configuration.py",
    "backend/tests/test_tenant_infinitepay_migration.py",
    "backend/tests/test_tenant_infinitepay_settings.py",
    "scripts/deploy-prod-lock.sh",
    "scripts/deploy-prod-state.sh",
    "scripts/test_prod_release_state.py",
    "scripts/prepare_emergency_api_image.py",
    "scripts/test_prepare_emergency_api_image.py",
    "openspec/changes/retire-infinitepay-checkout/inventory.md",
    "backend/tests/payment_migration_fixtures.py",
    "backend/tests/test_checkout_retirement.py",
    "backend/tests/test_worker_graceful_shutdown.py",
    "backend/tests/test_retire_infinitepay_migration.py",
    "backend/tests/test_payment_availability.py",
    "backend/tests/test_provider_payment_correction_migration.py",
    "backend/tests/test_provider_payment_migration.py",
    "backend/tests/test_tenant_owner_reset.py",
    "backend/tests/test_tenant_photographer_migration.py",
    "frontend/app/library/cart/cart.test.tsx",
    "frontend/app/library/library.test.tsx",
    "frontend/app/admin/payments/page.test.tsx",
    "frontend/app/admin/settings/page.test.tsx",
    "frontend/app/admin/retirement.test.ts",
    "frontend/app/admin/payments/order-photos.tsx",
    "frontend/app/admin/payments/payments.module.css",
    "frontend/app/admin/galleries/private-folder-client-overview.tsx",
    "frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx",
    "frontend/app/admin/galleries/[galleryId]/orders/page.tsx",
    "frontend/app/admin/admin-navigation.tsx",
    "frontend/app/globals.css",
    "openspec/changes/retire-infinitepay-checkout/tasks.md",
    "openspec/changes/retire-infinitepay-checkout/design.md",
    "openspec/changes/retire-infinitepay-checkout/proposal.md",
    "openspec/changes/retire-infinitepay-checkout/specs/gallery-sales/infinitepay-retirement/spec.md",
    "openspec/changes/release-infinitepay-retirement-prod/tasks.md",
    "openspec/changes/release-infinitepay-retirement-prod/design.md",
    "openspec/changes/release-infinitepay-retirement-prod/proposal.md",
    "openspec/changes/release-infinitepay-retirement-prod/.openspec.yaml",
    "openspec/changes/release-infinitepay-retirement-prod/specs/deployment-operations/spec.md",
    "openspec/changes/add-production-app-release-workflow/runtime-gates.json",
    "openspec/changes/add-infinitepay-pix-and-pending-cart/design.md",
    "openspec/changes/add-infinitepay-pix-and-pending-cart/proposal.md",
    "openspec/changes/add-infinitepay-pix-and-pending-cart/publication-20261022.md",
    "openspec/changes/add-infinitepay-pix-and-pending-cart/release-plan.md",
    "openspec/changes/add-infinitepay-pix-and-pending-cart/release-preparation-20261022.md",
    "openspec/changes/add-infinitepay-pix-and-pending-cart/specs/deployment-operations/payments0086-preparation/spec.md",
    "openspec/changes/add-infinitepay-pix-and-pending-cart/tasks.md",
    "openspec/changes/add-infinitepay-tenant-credentials/release-plan.md",
    "frontend/scripts/payments-visual-qa.cjs",
    "RELATORIO_IMPLEMENTACAO_VENDAS_PAGAMENTOS.md",
    "design-qa.md",
}

ALLOWED_DOCS = {
    "docs/PRODUCAO-FACIAL-INVENTARIO-E-PLANO.md",
    "docs/DEPLOY-PROD-APP.md",
    "docs/PRODUCTION-PREFLIGHT-SSH.md",
    "docs/RELEASE-INFINITEPAY-RETIREMENT.md",
}
COMPOSE_REMOVAL = [
    "-      - path: ${INFINITEPAY_BINDINGS_ENV_FILE:-.env.infinitepay-bindings}",
    "-        required: false",
    "-        format: raw",
]
RETIREMENT_MIGRATION = "backend/migrations/versions/20261022_0087_retire_infinitepay.py"
FOLLOWUP_EXACT = {
    ".gitleaksignore",
    ".github/workflows/ci.yml",
    "openspec/changes/release-infinitepay-retirement-prod/proposal.md",
    "docs/DEPLOY-PROD-APP.md",
    "docs/RELEASE-INFINITEPAY-RETIREMENT.md",
    "openspec/changes/add-production-app-release-workflow/runtime-gates.json",
    "openspec/changes/release-infinitepay-retirement-prod/design.md",
    "openspec/changes/release-infinitepay-retirement-prod/specs/deployment-operations/spec.md",
    "openspec/changes/release-infinitepay-retirement-prod/tasks.md",
    "scripts/check_infinitepay_retirement_scope.py",
    "scripts/check_prod_app_release_scope.py",
    "scripts/deploy-prod-app-services.sh",
    "scripts/production-preflight-ssh-wrapper.sh",
    "scripts/retirement_inventory_policy.py",
    "scripts/test_deploy_prod_app_services.sh",
    "scripts/test_infinitepay_retirement_scope.py",
    "scripts/test_prod_app_release_scope.py",
    "scripts/test_prod_release_state.py",
    "scripts/test_production_release_workflow_policy.py",
    "scripts/validate_retirement_approval.py",
    "scripts/test_retirement_approval.py",
    "scripts/test_release_candidate_policy.py",
    "scripts/test_retirement_inventory_policy.py",
}


def changed_paths(root: Path, base: str, target: str) -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMRTUXB", base, target],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line for line in result.stdout.splitlines() if line}


def evaluate(paths: set[str], compose_diff: str) -> tuple[bool, str]:
    migrations = {path for path in paths if path.startswith("backend/migrations/")}
    if migrations - {"backend/migrations/versions/20261022_0087_retire_infinitepay.py"}:
        return False, "migration_fora_do_escopo"
    for path in paths:
        if path in RUNTIME_PATHS or path in ALLOWED_EXACT or path in ALLOWED_DOCS:
            continue
        return False, "arquivo_fora_do_escopo"
    if "backend/migrations/versions/20261022_0087_retire_infinitepay.py" not in paths:
        return False, "migration_0087_ausente"
    if "docker/docker-compose.yml" not in paths:
        return False, "compose_sem_remocao_do_binding"
    changed_compose_lines = [
        line for line in compose_diff.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    if changed_compose_lines != COMPOSE_REMOVAL:
        return False, "compose_fora_do_escopo"
    return True, "somente_aposentadoria_infinitepay"


def evaluate_followup_scope(root: Path, base: str, target: str) -> tuple[bool, str]:
    """Allow only exact release-gate maintenance after retirement is already integrated."""
    try:
        subprocess.run(["git", "merge-base", "--is-ancestor", base, target], cwd=root,
                       check=True, capture_output=True, text=True)
        paths = changed_paths(root, base, target)
        if not paths or paths - FOLLOWUP_EXACT:
            return False, "ajuste_pos_integracao_fora_do_escopo"
        migration = subprocess.run(
            ["git", "cat-file", "-e", f"{base}:{RETIREMENT_MIGRATION}"], cwd=root,
            check=False, capture_output=True,
        )
        if migration.returncode != 0:
            return False, "aposentadoria_nao_integrada_na_base"
        compose = subprocess.run(
            ["git", "show", f"{base}:docker/docker-compose.yml"], cwd=root,
            check=True, capture_output=True, text=True,
        ).stdout
        if "INFINITEPAY_BINDINGS_ENV_FILE" in compose or ".env.infinitepay-bindings" in compose:
            return False, "binding_ainda_referenciado_na_base"
    except subprocess.CalledProcessError:
        return False, "historico_ou_estado_base_nao_comprovado"
    return True, "ajuste_gate_pos_integracao"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    try:
        paths = changed_paths(ROOT, args.base, args.target)
        compose_diff = subprocess.run(
            ["git", "diff", "--no-ext-diff", "--unified=0", args.base, args.target,
             "--", "docker/docker-compose.yml"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
        ready, reason = evaluate(paths, compose_diff)
        if not ready:
            followup_ready, followup_reason = evaluate_followup_scope(ROOT, args.base, args.target)
            if followup_ready:
                ready, reason = followup_ready, followup_reason
    except subprocess.CalledProcessError:
        ready, reason = False, "historico_nao_comprovado"
    print(f"retirement_release_ready={'true' if ready else 'false'}")
    print(f"criterio={reason}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
