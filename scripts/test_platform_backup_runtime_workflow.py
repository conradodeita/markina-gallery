"""Guard the fixed SSH and protected environment contract for backup operations."""

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
RUNTIME = (WORKFLOWS / "production-platform-backup-runtime.yml").read_text(encoding="utf-8")
WRAPPER_INSTALL = (WORKFLOWS / "production-platform-backup-wrapper-install.yml").read_text(encoding="utf-8")
CI = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
SSH_WRAPPER = (ROOT / "scripts/production-preflight-ssh-wrapper.sh").read_text(encoding="utf-8")
INSTALL_WRAPPER = (ROOT / "scripts/install-prod-platform-backup-wrapper.sh").read_text(encoding="utf-8")
WRAPPER_RESTORE = (ROOT / "scripts/platform_backup_wrapper_restore.py").read_text(encoding="utf-8")


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SystemExit(reason)


def main() -> int:
    require('bash scripts/build_platform_backup_runtime.sh "$GITHUB_SHA"' in CI,
            "runtime_builder_not_invoked_through_bash")
    require('result="$(bash scripts/build_platform_backup_runtime.sh "$GITHUB_SHA" "$output")"' in RUNTIME,
            "runtime_workflow_builder_not_invoked_through_bash")
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

    for mode in ("inventory", "diagnose", "install", "bind-and-rehearse", "reconcile"):
        require(mode in RUNTIME, "runtime_operation_missing:" + mode)
    diagnose_start = RUNTIME.index("  diagnose:\n")
    operate_start = RUNTIME.index("  operate:\n", diagnose_start)
    diagnose_job = RUNTIME[diagnose_start:operate_start]
    require("inputs.operation == 'diagnose'" in diagnose_job
            and "environment: production-preflight" in diagnose_job
            and "needs: [code-evidence]" in diagnose_job
            and "MARKINA_PLATFORM_BACKUP_DIAGNOSE_SHA=$GITHUB_SHA" in diagnose_job,
            "backup_diagnostic_not_protected_or_sha_bound")
    require("backup_runtime_container_diagnostics=" in diagnose_job
            and "umask 077" in diagnose_job
            and "runtime-artifact" not in diagnose_job
            and "operate" not in diagnose_job
            and "MARKINA_PLATFORM_BACKUP_INVENTORY_SHA=$GITHUB_SHA" in diagnose_job
            and "backup_runtime_inventory_summary=" in diagnose_job
            and "backup_runtime_normal_inventory=success" in diagnose_job
            and "SAFE_INVENTORY_ERROR_CODES" in diagnose_job
            and "backup_runtime_fingerprint=" in diagnose_job
            and 'print("backup_runtime_fingerprint=' not in diagnose_job
            and ' </dev/null >"$normal_output" 2>"$normal_error"' in diagnose_job
            and 'tee "$normal_output"' not in diagnose_job
            and RUNTIME.count("inputs.operation != 'diagnose'") >= 3,
            "backup_diagnostic_uses_normal_inventory_or_operate_path")
    workflow_parsers = [textwrap.dedent(source) for source in re.findall(
        r"<<'PY'[^\n]*\n(.*?)\n[ \t]*PY(?:[ \t]*\|[^\n]*)?(?:\n|$)",
        diagnose_job,
        re.DOTALL,
    )]
    require(len(workflow_parsers) == 3, "backup_diagnostic_workflow_python_parsers_missing")
    for source in workflow_parsers:
        ast.parse(source)
    with tempfile.TemporaryDirectory(prefix="backup-diagnostic-workflow-test-") as directory:
        output_file = Path(directory) / "ssh-output"
        error_parser, aggregate_parser, inventory_parser = workflow_parsers

        def run_parser(source: str, content: str, status: int = 0) -> subprocess.CompletedProcess[str]:
            output_file.write_text(content, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-c", source, str(output_file), str(status)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        safe_error = run_parser(
            error_parser,
            "platform-backup-runtime: container diagnostics failed (diagnostic_compose_list_failed)\n",
        )
        require(safe_error.returncode == 0
                and safe_error.stdout == "backup_runtime_diagnostic_failed=diagnostic_compose_list_failed\n",
                "backup_diagnostic_workflow_did_not_allowlist_error")
        unsafe_error = run_parser(
            error_parser,
            "Traceback: private host path and secret\n",
        )
        require(unsafe_error.returncode == 0
                and unsafe_error.stdout == "backup_runtime_diagnostic_failed=transport_or_output_error\n"
                and "secret" not in unsafe_error.stdout,
                "backup_diagnostic_workflow_leaked_error_details")

        roles = {
            "api": {
                "label_records": 2, "compose_records": 2, "matched_records": 2,
                "label_only_records": 0, "compose_only_records": 0,
                "running": 1, "stopped": 1, "unknown": 0,
            },
            "web": {
                "label_records": 0, "compose_records": 0, "matched_records": 0,
                "label_only_records": 0, "compose_only_records": 0,
                "running": 0, "stopped": 0, "unknown": 0,
            },
            "db": {
                "label_records": 1, "compose_records": 1, "matched_records": 1,
                "label_only_records": 0, "compose_only_records": 0,
                "running": 1, "stopped": 0, "unknown": 0,
            },
        }
        valid_aggregate = "backup_runtime_container_diagnostics=" + json.dumps(
            {"schema_version": 2, "roles": roles}, sort_keys=True, separators=(",", ":"),
        ) + "\n"
        aggregate_ok = run_parser(aggregate_parser, valid_aggregate)
        require(aggregate_ok.returncode == 0 and aggregate_ok.stdout == valid_aggregate,
                "backup_diagnostic_workflow_rejected_valid_aggregate")
        invalid_aggregate = run_parser(
            aggregate_parser,
            "backup_runtime_container_diagnostics=" + json.dumps({
                "schema_version": 2,
                "roles": {**roles, "api": {**roles["api"], "container_id": "private"}},
            }) + "\n",
        )
        require(invalid_aggregate.returncode != 0 and "private" not in invalid_aggregate.stdout,
                "backup_diagnostic_workflow_leaked_or_accepted_invalid_aggregate")

        active_id = "a" * 64
        inventory_payload = {
            "schema_version": 1,
            "checkout_sha": "c" * 40,
            "containers": {
                role: {"state": "running", "running": True,
                       "health": "healthy" if role != "db" else "none"}
                for role in ("api", "web", "db")
            },
            "database_schema": "20261113_0126",
            "disk_var_lib": {"available_kib": 50000, "use_percent": 50},
            "units": {
                "service": {"load": "not-found", "enabled": "unknown", "active": "inactive"},
                "timer": {"load": "not-found", "enabled": "unknown", "active": "inactive"},
            },
        }
        successful_inventory = run_parser(
            inventory_parser,
            "backup_runtime_inventory_summary=" + json.dumps(inventory_payload, sort_keys=True, separators=(",", ":"))
            + "\nbackup_runtime_fingerprint=" + "f" * 64
            + "\nbackup_runtime_install_preconditions=pass\n",
        )
        require(successful_inventory.returncode == 0
                and successful_inventory.stdout ==
                    "backup_runtime_normal_inventory=success\n"
                    "backup_runtime_install_preconditions=pass\n"
                and "f" * 64 not in successful_inventory.stdout,
                "backup_diagnostic_workflow_exposed_success_inventory_fingerprint")
        leaked_summary = json.loads(json.dumps(inventory_payload))
        leaked_summary["containers"]["api"]["id"] = active_id
        invalid_success = run_parser(
            inventory_parser,
            "backup_runtime_inventory_summary=" + json.dumps(leaked_summary, sort_keys=True, separators=(",", ":"))
            + "\nbackup_runtime_fingerprint=" + "f" * 64
            + "\nbackup_runtime_install_preconditions=pass\n",
        )
        require(invalid_success.returncode != 0
                and invalid_success.stdout == "backup_runtime_normal_inventory=invalid_output\n"
                and active_id not in invalid_success.stdout,
                "backup_diagnostic_workflow_accepted_or_exposed_container_identity")

        expected_inventory = run_parser(
            inventory_parser,
            "platform-backup-runtime: inventory failed (api_active_project_resolution_failed)\n",
            1,
        )
        require(expected_inventory.returncode == 0
                and expected_inventory.stdout ==
                    "backup_runtime_normal_inventory=failed (api_active_project_resolution_failed)\n",
                "backup_diagnostic_workflow_did_not_allowlist_inventory_failure")
        unexpected_inventory = run_parser(
            inventory_parser,
            "platform-backup-runtime: inventory failed (host-secret-private-path)\n",
            1,
        )
        require(unexpected_inventory.returncode != 0
                and unexpected_inventory.stdout == "backup_runtime_normal_inventory=unexpected_failure\n"
                and "host-secret" not in unexpected_inventory.stdout,
                "backup_diagnostic_workflow_leaked_unexpected_inventory_failure")
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
        "MARKINA_PLATFORM_BACKUP_DIAGNOSE_SHA=",
        "MARKINA_PLATFORM_BACKUP_INSTALL_SHA=",
        "MARKINA_PLATFORM_BACKUP_BIND_SHA=",
        "MARKINA_PLATFORM_BACKUP_RECONCILE_SHA=",
    ):
        require(command in SSH_WRAPPER, "fixed_ssh_mode_missing:" + command)
    require("git ls-remote origin refs/heads/main" in SSH_WRAPPER
            and "git hash-object -- \"$source_dir/inventory.py\"" in SSH_WRAPPER,
            "runtime_source_not_sha_and_blob_bound")
    require("MARKINA_PLATFORM_BACKUP_DIAGNOSE_SHA=([0-9a-f]{40})" in SSH_WRAPPER
            and "backup_mode=\"diagnose\"" in SSH_WRAPPER,
            "backup_diagnostic_command_not_exact_sha_bound")
    require("operation == \"diagnose\" and not args" in SSH_WRAPPER
            and "diagnostic_main()" in SSH_WRAPPER
            and "diagnose)\n      acquire_backup_release_lock" in SSH_WRAPPER,
            "backup_diagnostic_not_readonly_locked_dispatch")
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
            and "--sha \"$backup_sha\" --bundle-sha256 \"$backup_digest\"" in SSH_WRAPPER
            and "approval-fingerprint \"$backup_fingerprint\"" in SSH_WRAPPER,
            "installer_does_not_receive_fixed_approval_context")
    require("production-release.lock" in SSH_WRAPPER or "production-release.lock" in INSTALL_WRAPPER,
            "common_release_lock_not_used")
    require("backup_runtime_inventory" in SSH_WRAPPER and "verify_installed_release" in SSH_WRAPPER,
            "runtime_receipt_not_revalidated_for_operations")
    require('if operation == "inventory" and len(args) == 1:' in SSH_WRAPPER
            and "module.main(args[0])" in SSH_WRAPPER
            and SSH_WRAPPER.count('inventory "$backup_sha"') == 2,
            "runtime_inventory_not_bound_to_exact_support_sha")
    for name in ("inventory_bootstrap", "installer_bootstrap"):
        match = re.search(rf"{name}=\"\$\(cat <<'PY'\n(.*?)\nPY\n\)\"", SSH_WRAPPER, re.DOTALL)
        require(match is not None, "python_bootstrap_missing:" + name)
        ast.parse(match.group(1))

    require("approval_fingerprint" in WRAPPER_INSTALL and "production-preflight-ssh-wrapper.sh" in WRAPPER_INSTALL,
            "wrapper_bootstrap_approval_missing")
    require("environment: production" in WRAPPER_INSTALL
            and "PRODUCTION_SSH_PRIVATE_KEY" in WRAPPER_INSTALL,
            "wrapper_bootstrap_not_protected")
    install_job = WRAPPER_INSTALL[WRAPPER_INSTALL.index("  install-wrapper:\n"):]
    binding_start = install_job.index("      - name: Revalidar CI, fingerprint e destino do canal de escrita\n")
    write_start = install_job.index("      - name: Atualizar somente o forced command após aprovação protegida\n", binding_start)
    binding_step = install_job[binding_start:write_start]
    require("INVENTORY_CONNECTION: ${{ needs.preflight.outputs.connection_binding }}" in binding_step
            and 'production_binding="$(printf \'%s\' "$SSH_HOST|$SSH_PORT|$SSH_USER"' in binding_step
            and '[[ "$production_binding" == "$INVENTORY_CONNECTION" ]]' in binding_step,
            "wrapper_install_destination_not_bound_to_current_preflight_output")
    require("PREFLIGHT_HOST" not in binding_step and "PREFLIGHT_PORT" not in binding_step
            and "PREFLIGHT_USER" not in binding_step and "preflight_binding" not in binding_step,
            "wrapper_install_reads_variables_from_another_protected_environment")
    binding_lines = [
        line for line in binding_step.splitlines()
        if line.strip().startswith("production_binding=")
        or line.strip() == '[[ "$production_binding" == "$INVENTORY_CONNECTION" ]]'
    ]
    require(len(binding_lines) == 2, "wrapper_install_binding_shell_contract_incomplete")
    binding_script = "\n".join(binding_lines)
    connection = "production.example|22|ubuntu"
    expected_binding = hashlib.sha256(connection.encode("utf-8")).hexdigest()
    bash_executable = shutil.which("bash") or "bash"
    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        git_bash = Path(program_files) / "Git" / "bin" / "bash.exe"
        if git_bash.is_file():
            bash_executable = str(git_bash)

    def run_binding(inventory_connection: str) -> subprocess.CompletedProcess[str]:
        environment = {
            name: os.environ[name]
            for name in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
            if name in os.environ
        }
        environment.update({
            "SSH_HOST": "production.example",
            "SSH_PORT": "22",
            "SSH_USER": "ubuntu",
            "INVENTORY_CONNECTION": inventory_connection,
        })
        for name in ("PREFLIGHT_HOST", "PREFLIGHT_PORT", "PREFLIGHT_USER"):
            environment.pop(name, None)
        return subprocess.run(
            [bash_executable, "-e", "-u", "-o", "pipefail", "-c", binding_script],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    matching_binding = run_binding(expected_binding)
    require(matching_binding.returncode == 0, "wrapper_install_rejected_matching_preflight_binding")
    mismatched_binding = run_binding("0" * 64)
    require(mismatched_binding.returncode != 0, "wrapper_install_accepted_mismatched_preflight_binding")
    require("flock -n \"$release_lock\"" in INSTALL_WRAPPER
            and "application_and_shared_containers_unchanged=true" in INSTALL_WRAPPER,
            "wrapper_bootstrap_does_not_preserve_shared_host_state")
    require("restore_previous_wrapper() {" in INSTALL_WRAPPER
            and INSTALL_WRAPPER.count("restore_previous_wrapper") >= 9
            and "inventário pós-instalação falhou; wrapper anterior restaurado" in INSTALL_WRAPPER
            and "snapshot pós-instalação falhou; wrapper anterior restaurado" in INSTALL_WRAPPER,
            "wrapper_install_lacks_rollback_on_diagnostic_or_invariance_failure")
    require("SSH_ORIGINAL_COMMAND=\"id\"" in INSTALL_WRAPPER and "\"$BASH\" -n \"$temporary\"" in INSTALL_WRAPPER,
            "wrapper_bootstrap_arbitrary_command_probe_missing")
    source_loader = re.search(
        r"read_approved_inventory_source\(\) \{\n(.*?)\n\}", INSTALL_WRAPPER, re.DOTALL,
    )
    require(source_loader is not None, "approved_inventory_source_loader_missing")
    source_loader_script = source_loader.group(0)
    source_load_call = 'read_approved_inventory_source "$support_sha" "$inventory_source"'
    first_root_write = 'sudo -n install -o root -g root -m 0600 -- "$WRAPPER" "$backup"'
    require('git show "$approved_sha:$module_path" > "$destination"' in source_loader_script
            and 'git rev-parse "$approved_sha:$module_path"' in source_loader_script
            and 'git hash-object -- "$destination"' in source_loader_script
            and source_load_call in INSTALL_WRAPPER
            and INSTALL_WRAPPER.index(source_load_call) < INSTALL_WRAPPER.index(first_root_write)
            and 'inventory_source="$PROJECT_ROOT/scripts/platform_backup_runtime_inventory.py"' not in INSTALL_WRAPPER,
            "approved_inventory_source_not_pinned_before_wrapper_write")
    with tempfile.TemporaryDirectory(prefix="backup-approved-source-test-") as directory:
        repo = Path(directory) / "repo"
        repo.mkdir()
        module_path = Path("scripts/platform_backup_runtime_inventory.py")
        module_git_path = module_path.as_posix()
        module_file = repo / module_path
        module_file.parent.mkdir(parents=True)
        old_source = b"def diagnostic_main():\n    return 1\n"
        approved_source = b"def diagnostic_main():\n    return 0\n"
        module_file.write_bytes(old_source)

        def run_git(*arguments: str) -> str:
            result = subprocess.run(
                ["git", *arguments], cwd=repo, capture_output=True, text=True, check=False,
            )
            require(result.returncode == 0, "approved_inventory_source_fixture_git_failed")
            return result.stdout.strip()

        run_git("init", "-q", "-b", "main")
        run_git("config", "core.autocrlf", "false")
        run_git("config", "user.name", "OpenSpec Test")
        run_git("config", "user.email", "openspec-test@example.invalid")
        run_git("config", "commit.gpgsign", "false")
        run_git("add", module_git_path)
        run_git("commit", "-q", "-m", "old operational checkout")
        run_git("branch", "active-checkout")
        module_file.write_bytes(approved_source)
        run_git("add", module_git_path)
        run_git("commit", "-q", "-m", "approved main source")
        approved_sha = run_git("rev-parse", "HEAD")
        run_git("rm", "-q", module_git_path)
        run_git("commit", "-q", "-m", "module absent")
        missing_sha = run_git("rev-parse", "HEAD")
        run_git("switch", "-q", "active-checkout")
        require(module_file.read_bytes() == old_source, "approved_source_fixture_checkout_not_stale")

        source_environment = {
            name: os.environ[name]
            for name in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME")
            if name in os.environ
        }

        def read_source(commit: str, destination: Path, *, fake_hash: bool = False) -> subprocess.CompletedProcess[str]:
            shell_script = source_loader_script
            if fake_hash:
                shell_script += textwrap.dedent(
                    """
                    git() {
                      if [[ "${1:-}" == "hash-object" ]]; then
                        printf '0000000000000000000000000000000000000000\\n'
                        return 0
                      fi
                      command git "$@"
                    }
                    """,
                )
            shell_script += '\nread_approved_inventory_source "$1" "$2"\n'
            return subprocess.run(
                [bash_executable, "-e", "-u", "-o", "pipefail", "-c", shell_script,
                 "bash", commit, str(destination)],
                cwd=repo,
                env=source_environment,
                capture_output=True,
                text=True,
                check=False,
            )

        approved_output = Path(directory) / "approved-source"
        approved_result = read_source(approved_sha, approved_output)
        require(approved_result.returncode == 0 and approved_output.read_bytes() == approved_source,
                "stale_checkout_did_not_load_exact_approved_module")
        missing_output = Path(directory) / "missing-source"
        missing_result = read_source(missing_sha, missing_output)
        require(missing_result.returncode != 0 and not missing_result.stdout and not missing_result.stderr,
                "missing_approved_module_was_not_sanitized")
        mismatch_output = Path(directory) / "mismatched-source"
        mismatch_result = read_source(approved_sha, mismatch_output, fake_hash=True)
        require(mismatch_result.returncode != 0 and not mismatch_result.stdout and not mismatch_result.stderr,
                "mismatched_approved_module_hash_was_accepted_or_exposed")
    require("module.diagnostic_main()" in INSTALL_WRAPPER
            and "MARKINA_PLATFORM_BACKUP_INVENTORY_SHA=$support_sha" not in INSTALL_WRAPPER
            and "backup_runtime_fingerprint=" not in INSTALL_WRAPPER,
            "wrapper_install_still_requires_ambiguous_backup_fingerprint")
    bootstrap = re.search(
        r"diagnostic_bootstrap=\"\$\(cat <<'PY'\n(.*?)\nPY\n\)\"",
        INSTALL_WRAPPER,
        re.DOTALL,
    )
    require(bootstrap is not None, "wrapper_install_diagnostic_bootstrap_missing")
    ast.parse(bootstrap.group(1))
    validator = re.search(
        r'if ! /usr/bin/python3\.10 - "\$backup_diagnostic" <<\'PY\' >/dev/null\n(.*?)\nPY\nthen',
        INSTALL_WRAPPER,
        re.DOTALL,
    )
    require(validator is not None, "wrapper_install_diagnostic_schema_validator_missing")
    validator_source = validator.group(1)
    ast.parse(validator_source)
    roles = {
        "api": {
            "label_records": 2, "compose_records": 2, "matched_records": 2,
            "label_only_records": 0, "compose_only_records": 0,
            "running": 1, "stopped": 1, "unknown": 0,
        },
        "web": {
            "label_records": 0, "compose_records": 0, "matched_records": 0,
            "label_only_records": 0, "compose_only_records": 0,
            "running": 0, "stopped": 0, "unknown": 0,
        },
        "db": {
            "label_records": 1, "compose_records": 1, "matched_records": 1,
            "label_only_records": 0, "compose_only_records": 0,
            "running": 1, "stopped": 0, "unknown": 0,
        },
    }
    valid_report = "backup_runtime_container_diagnostics=" + json.dumps(
        {"schema_version": 2, "roles": roles}, separators=(",", ":"),
    )
    valid = subprocess.run(
        [sys.executable, "-c", validator_source, valid_report],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(valid.returncode == 0, "wrapper_install_rejects_valid_aggregate_diagnostic")
    invalid_reports = (
        "backup_runtime_container_diagnostics={}",
        "backup_runtime_container_diagnostics={invalid-json}",
        valid_report + "\nextra",
        "backup_runtime_container_diagnostics=" + json.dumps({
            "schema_version": 2, "roles": {**roles, "unexpected": roles["api"]},
        }),
        "backup_runtime_container_diagnostics=" + json.dumps({
            "schema_version": 2, "roles": {**roles, "api": {**roles["api"], "id": "not-allowed"}},
        }),
        "backup_runtime_container_diagnostics=" + json.dumps({
            "schema_version": 2, "roles": {**roles, "api": {**roles["api"], "label_records": True}},
        }),
        "backup_runtime_container_diagnostics=" + json.dumps({
            "schema_version": 2, "roles": {**roles, "api": {**roles["api"], "label_records": 513}},
        }),
        "backup_runtime_container_diagnostics=" + json.dumps({
            "schema_version": 2, "roles": {**roles, "api": {**roles["api"], "label_only_records": 1}},
        }),
        "backup_runtime_container_diagnostics=" + json.dumps({
            "schema_version": 1, "roles": roles,
        }),
    )
    for report in invalid_reports:
        result = subprocess.run(
            [sys.executable, "-c", validator_source, report],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        require(result.returncode != 0, "wrapper_install_accepts_invalid_aggregate_diagnostic")
    require("restore_backup_sha256:" in WRAPPER_INSTALL
            and "options: [inventory, install-wrapper, restore-wrapper]" in WRAPPER_INSTALL,
            "restore_wrapper_workflow_input_missing")
    restore_job = WRAPPER_INSTALL.split("  restore-wrapper:", 1)[1]
    restore_requirements = (
        "inputs.operation == 'restore-wrapper'",
        "needs: [code-evidence, preflight]",
        "environment: production",
        'python scripts/verify_main_ci_evidence.py --sha "$GITHUB_SHA"',
        "RESTORE_BACKUP_SHA256: ${{ inputs.restore_backup_sha256 }}",
        'REQUESTED_FINGERPRINT" == "$INVENTORY_FINGERPRINT',
        'production_binding" == "$INVENTORY_CONNECTION',
        "MARKINA_PLATFORM_BACKUP_RESTORE_WRAPPER_SHA=$GITHUB_SHA",
        'tee -a "$GITHUB_STEP_SUMMARY"',
    )
    for requirement in restore_requirements:
        require(requirement in restore_job, "restore_wrapper_protected_contract_missing:" + requirement)
    require("BACKUP_WRAPPER_RESTORE_BLOB_SHA" in SSH_WRAPPER
            and 'git hash-object -- "$source_dir/wrapper_restore.py"' in SSH_WRAPPER
            and "acquire_backup_release_lock" in SSH_WRAPPER
            and "--receipt-backup-sha256" in SSH_WRAPPER,
            "restore_wrapper_source_lock_or_receipt_not_pinned")
    restore_command = (
        "MARKINA_PLATFORM_BACKUP_RESTORE_WRAPPER_SHA=([0-9a-f]{40})"
        "_RECEIPT=([0-9a-f]{64})_FINGERPRINT=([0-9a-f]{64})"
    )
    require(restore_command in SSH_WRAPPER and 'backup_mode="restore-wrapper"' in SSH_WRAPPER,
            "restore_wrapper_ssh_command_not_fixed")
    require('BACKUP_DIR = Path("/var/backups/markina-gallery")' in WRAPPER_RESTORE
            and 'WRAPPER_PATH = Path("/usr/local/sbin/markina-gallery-preflight-ssh-wrapper")' in WRAPPER_RESTORE
            and "--backup-path" not in WRAPPER_RESTORE
            and '["sudo", "-n", "-H", "-u", "ubuntu", "env"' in WRAPPER_RESTORE
            and '"SSH_ORIGINAL_COMMAND=id"' in WRAPPER_RESTORE
            and 'docker = ["sudo", "-n", "-H", "-u", "ubuntu", "docker"]' in WRAPPER_RESTORE
            and "wrapper_restore_fallback_unverified" in WRAPPER_RESTORE
            and "docker" in WRAPPER_RESTORE,
            "restore_wrapper_paths_or_fail_closed_contract_missing")
    helper_blob = subprocess.run(
        [
            "git",
            "hash-object",
            "--path=scripts/platform_backup_wrapper_restore.py",
            "scripts/platform_backup_wrapper_restore.py",
        ],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    pin = re.search(r'BACKUP_WRAPPER_RESTORE_BLOB_SHA="([0-9a-f]{40})"', SSH_WRAPPER)
    require(helper_blob.returncode == 0 and pin is not None and pin.group(1) == helper_blob.stdout.strip(),
            "restore_wrapper_helper_blob_pin_mismatch")
    print("platform_backup_runtime_workflow=valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
