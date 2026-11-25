"""Static policy checks for the protected app preflight-support operations."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/production-app-compose-bridge-install.yml").read_text(encoding="utf-8")
RUNNER = (ROOT / "scripts/install-prod-app-compose-bridge.sh").read_text(encoding="utf-8")
HELPER = (ROOT / "scripts/production_app_preflight_support.py").read_text(encoding="utf-8")


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SystemExit(reason)


def main() -> int:
    operations = ("support-inventory", "prepare-support", "repair-support-backups-mode",
                  "restore-support-inventory", "restore-support")
    option_text = "options: [" + ", ".join(operations) + "]"
    require("on:\n  workflow_dispatch:\n    inputs:\n      operation:" in WORKFLOW,
            "support_requires_explicit_workflow_dispatch")
    require(option_text in WORKFLOW, "support_workflow_has_unlisted_operation")
    require("permissions: {}" in WORKFLOW and "contents: write" not in WORKFLOW,
            "support_workflow_permissions_too_broad")
    require("cancel-in-progress: false" in WORKFLOW, "support_operation_cancellation_enabled")
    require("github.ref == 'refs/heads/main'" in WORKFLOW, "support_workflow_not_main_only")
    require(WORKFLOW.count("python scripts/verify_main_ci_evidence.py --sha \"$GITHUB_SHA\" --app-bridge-install") == 2,
            "support_workflow_does_not_revalidate_exact_ci_twice")
    require("needs: [ci-evidence]" in WORKFLOW, "support_operation_skips_ci_evidence_job")
    require("environment: production" in WORKFLOW and "production-preflight" not in WORKFLOW,
            "support_operations_must_gate_production_ssh_credentials")
    require("PRODUCTION_SSH_PRIVATE_KEY" in WORKFLOW and "PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY" not in WORKFLOW,
            "support_workflow_does_not_reuse_existing_protected_channel")
    require("scripts/install-prod-app-compose-bridge.sh" in WORKFLOW
            and "scripts/production_app_preflight_support.py" in WORKFLOW,
            "support_workflow_missing_fixed_runner_or_pinned_helper")
    require("scripts/install-prod-preview-migration-wrapper.sh" not in WORKFLOW,
            "support_workflow_keeps_nontransactional_two-step_installer")
    require('git rev-parse "$GITHUB_SHA:scripts/production_app_preflight_support.py"' in WORKFLOW,
            "support_helper_blob_not_bound_to_exact_sha")
    require("--helper-blob \"$helper_blob\"" in WORKFLOW,
            "support_workflow_does_not_pass_helper_pin")
    require('tee -a "$GITHUB_STEP_SUMMARY"' in WORKFLOW,
            "support_inventory_output_not_presented_in_protected_summary")
    repair_case = WORKFLOW.split("            repair-support-backups-mode)", 1)[1].split(
        "            restore-support-inventory)", 1)[0]
    require('"$APPROVAL_FINGERPRINT" =~ ^[0-9a-f]{64}$' in repair_case
            and '"$PREPARATION_RECEIPT_SHA256"' in repair_case and "-z" in repair_case
            and "support_args+=(--approval-fingerprint \"$APPROVAL_FINGERPRINT\")" in repair_case,
            "support_mode_repair_does_not_require_only_the_current_fingerprint")
    require("--path" not in repair_case and "--mode 0700" not in repair_case
            and "--owner" not in repair_case and "--group" not in repair_case,
            "support_mode_repair_exposes_arbitrary_target_parameters")
    runner_repair = RUNNER.split("  repair-support-backups-mode)", 1)[1].split(
        "  restore-support-inventory)", 1)[0]
    require('[[ $# == 2 && "$1" == --approval-fingerprint && "$2" =~ ^[0-9a-f]{64}$ ]]' in runner_repair
            and "--receipt-sha256" not in runner_repair
            and "--path" not in runner_repair and "--mode" not in runner_repair,
            "support_runner_mode_repair_accepts_arbitrary_arguments")
    inventory_case = WORKFLOW.split("            support-inventory)", 1)[1].split(
        "            prepare-support)", 1)[0]
    prepare_case = WORKFLOW.split("            prepare-support)", 1)[1].split(
        "            repair-support-backups-mode)", 1)[0]
    require("repair-support-backups-mode" not in inventory_case, "support_inventory_chains_mode_repair")
    require("repair-support-backups-mode" not in prepare_case, "support_preparation_chains_mode_repair")

    require("readonly PROJECT_ROOT=\"/opt/markina-gallery\"" in RUNNER
            and "readonly SUPPORT_HELPER=\"scripts/production_app_preflight_support.py\"" in RUNNER,
            "support_runner_identity_or_helper_path_not_fixed")
    for operation in operations:
        require(operation in RUNNER, "support_runner_missing_operation:" + operation)
    require("git ls-remote --exit-code origin refs/heads/main" in RUNNER,
            "support_runner_does_not_revalidate_remote_main")
    require("git fetch --no-tags --no-write-fetch-head --refmap= origin refs/heads/main" in RUNNER,
            "support_runner_fetch_may_move_fetch_head")
    require('"fetch", "--no-tags", "--no-write-fetch-head", "--refmap=", "origin", "refs/heads/main"' in HELPER,
            "support_helper_fetch_may_move_fetch_head")
    require("refs_before" in RUNNER and "refs_after" in RUNNER and "support_fetch_changed_refs" in RUNNER,
            "support_runner_does_not_prove_fetch_preserved_refs")
    require("git rev-parse \"$support_sha:$SUPPORT_HELPER\"" in RUNNER
            and "git cat-file blob \"$support_sha:$SUPPORT_HELPER\"" in RUNNER
            and "/usr/bin/python3.10 -B -" in RUNNER,
            "support_runner_does_not_execute_pinned_git_object")
    for forbidden in ("git checkout", "git reset", "git clean", "git prune", "docker compose up",
                      "systemctl start", "systemctl enable", "pg_dump", "curl "):
        require(forbidden not in RUNNER, "support_runner_contains_forbidden_operation:" + forbidden)

    expected_targets = (
        'BRIDGE_PATH = Path("/usr/local/sbin/markina-gallery-app-compose-bridge")',
        'WRAPPER_PATH = Path("/usr/local/sbin/markina-gallery-preflight-ssh-wrapper")',
        'MAIN_REF = "refs/remotes/origin/main"',
        'STATE_DIR = Path("/var/lib/markina-gallery/app-compose-bridge")',
    )
    for target in expected_targets:
        require(target in HELPER, "support_helper_target_or_lock_changed:" + target)
    require('LOCK_DIR = Path("/var/lib/markina-gallery/deploy-state")' in HELPER
            and 'LOCK_PATH = LOCK_DIR / "production-release.lock"' in HELPER,
            "support_helper_common_lock_changed")
    for diagnostic_field in (
        "support_state_directory_diagnostics", "support_backup_directory_diagnostics",
    ):
        require(diagnostic_field in HELPER, "support_inventory_diagnostic_output_missing:" + diagnostic_field)
    require("def _format_directory_diagnostics(value: Any) -> str:" in HELPER
            and "item not in SUPPORT_DIRECTORY_DIAGNOSTICS" in HELPER,
            "support_inventory_diagnostic_output_not_allowlisted")
    require('"bridge": BRIDGE_PATH, "wrapper": WRAPPER_PATH' in HELPER,
            "support_helper_has_dynamic_targets")
    for forbidden in ("git checkout", "git reset", "git clean", "git prune", "docker compose up",
                      "systemctl start", "systemctl enable", "pg_dump"):
        require(forbidden not in HELPER, "support_helper_contains_forbidden_operation:" + forbidden)

    print("production_app_preflight_support_workflow=valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
