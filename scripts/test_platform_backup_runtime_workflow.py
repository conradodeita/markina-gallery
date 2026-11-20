"""Guard the fixed SSH and protected environment contract for backup operations."""

import ast
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
RUNTIME = (WORKFLOWS / "production-platform-backup-runtime.yml").read_text(encoding="utf-8")
WRAPPER_INSTALL = (WORKFLOWS / "production-platform-backup-wrapper-install.yml").read_text(encoding="utf-8")
SSH_WRAPPER = (ROOT / "scripts/production-preflight-ssh-wrapper.sh").read_text(encoding="utf-8")
INSTALL_WRAPPER = (ROOT / "scripts/install-prod-platform-backup-wrapper.sh").read_text(encoding="utf-8")


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SystemExit(reason)


def main() -> int:
    require("on:\n  workflow_dispatch:" in RUNTIME and "on:\n  workflow_dispatch:" in WRAPPER_INSTALL,
            "workflow_dispatch_missing")
    for workflow in (RUNTIME, WRAPPER_INSTALL):
        require("github.ref == 'refs/heads/main'" in workflow, "main_ref_gate_missing")
        require("permissions: {}" in workflow and "contents: write" not in workflow,
                "workflow_permissions_too_broad")
        require("python scripts/verify_main_ci_evidence.py --sha \"$GITHUB_SHA\"" in workflow,
                "exact_sha_ci_evidence_missing")
        require("environment: production" in workflow and "environment: production-preflight" in workflow,
                "protected_environments_missing")
        require("cancel-in-progress: false" in workflow, "operation_cancellation_not_disabled")

    for mode in ("inventory", "install", "bind-and-rehearse", "reconcile"):
        require(mode in RUNTIME, "runtime_operation_missing:" + mode)
    require("inputs.approval_fingerprint" in RUNTIME and "inputs.approval_bundle_sha256" in RUNTIME,
            "runtime_approval_inputs_missing")
    require("REQUESTED_FINGERPRINT\" == \"$INVENTORY_FINGERPRINT" in RUNTIME
            and "REQUESTED_BUNDLE\" == \"$BUNDLE_SHA256" in RUNTIME,
            "runtime_preflight_approval_not_compared")
    require("needs.preflight.outputs.connection_binding" in RUNTIME and "PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY" in RUNTIME,
            "runtime_ssh_destination_not_bound")
    require("actions/upload-artifact@v4" in RUNTIME and "actions/download-artifact@v4" in RUNTIME
            and "sha256sum \"$bundle\"" in RUNTIME,
            "runtime_bundle_not_bound_to_workflow_run")
    for forbidden in ("systemctl enable", "systemctl start", "pg_dump", "docker compose up", "REAL_BACKUP"):
        require(forbidden not in RUNTIME and forbidden not in SSH_WRAPPER,
                "runtime_gate_contains_forbidden_operation:" + forbidden)

    for command in (
        "MARKINA_PLATFORM_BACKUP_INVENTORY_SHA=",
        "MARKINA_PLATFORM_BACKUP_INSTALL_SHA=",
        "MARKINA_PLATFORM_BACKUP_BIND_SHA=",
        "MARKINA_PLATFORM_BACKUP_RECONCILE_SHA=",
    ):
        require(command in SSH_WRAPPER, "fixed_ssh_mode_missing:" + command)
    require("git ls-remote origin refs/heads/main" in SSH_WRAPPER
            and "git hash-object -- \"$source_dir/inventory.py\"" in SSH_WRAPPER,
            "runtime_source_not_sha_and_blob_bound")
    for variable, source in (
        ("BACKUP_ARTIFACT_BLOB_SHA", "scripts/platform_backup_runtime_artifact.py"),
        ("BACKUP_INVENTORY_BLOB_SHA", "scripts/platform_backup_runtime_inventory.py"),
        ("BACKUP_INSTALLER_BLOB_SHA", "scripts/install_platform_backup_runtime.py"),
    ):
        match = re.search(rf'^(?:readonly )?{variable}="([0-9a-f]{{40}})"$', SSH_WRAPPER, re.MULTILINE)
        require(match is not None, "runtime_blob_pin_missing:" + variable)
        actual = subprocess.run(
            ["git", "hash-object", source],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        require(match.group(1) != "0" * 40 and match.group(1) == actual,
                "runtime_blob_pin_diverged:" + variable)
    require("sudo -n /usr/bin/python3.10 -B -c \"$installer_bootstrap\"" in SSH_WRAPPER
            and "approval-fingerprint \"$backup_fingerprint\"" in SSH_WRAPPER,
            "installer_does_not_receive_fixed_approval_context")
    require("production-release.lock" in SSH_WRAPPER or "production-release.lock" in INSTALL_WRAPPER,
            "common_release_lock_not_used")
    require("backup_runtime_inventory" in SSH_WRAPPER and "verify_installed_release" in SSH_WRAPPER,
            "runtime_receipt_not_revalidated_for_operations")
    for name in ("inventory_bootstrap", "installer_bootstrap"):
        match = re.search(rf"{name}=\"\$\(cat <<'PY'\n(.*?)\nPY\n\)\"", SSH_WRAPPER, re.DOTALL)
        require(match is not None, "python_bootstrap_missing:" + name)
        ast.parse(match.group(1))

    require("approval_fingerprint" in WRAPPER_INSTALL and "production-preflight-ssh-wrapper.sh" in WRAPPER_INSTALL,
            "wrapper_bootstrap_approval_missing")
    require("environment: production" in WRAPPER_INSTALL
            and "PRODUCTION_SSH_PRIVATE_KEY" in WRAPPER_INSTALL,
            "wrapper_bootstrap_not_protected")
    require("flock -n \"$release_lock\"" in INSTALL_WRAPPER
            and "application_and_shared_containers_unchanged=true" in INSTALL_WRAPPER,
            "wrapper_bootstrap_does_not_preserve_shared_host_state")
    require("SSH_ORIGINAL_COMMAND=\"id\"" in INSTALL_WRAPPER and "\"$BASH\" -n \"$temporary\"" in INSTALL_WRAPPER,
            "wrapper_bootstrap_arbitrary_command_probe_missing")
    print("platform_backup_runtime_workflow=valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
