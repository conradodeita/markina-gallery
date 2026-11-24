"""Read-only inventory contracts; all command results and filesystem inputs are synthetic."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import platform_backup_runtime_inventory as inventory


class InventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pyp-backup-inventory-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "etc").mkdir()
        (self.root / "etc/machine-id").write_text("abcdef0123456789abcdef0123456789\n", encoding="ascii")

    @staticmethod
    def _result(argv: list[str], stdout: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, returncode, stdout, "synthetic stderr")

    def _runner(self, *, timer_enabled: str = "unknown", third_party_image: str = "8"):
        service_ids = {"api": "c" * 64, "web": "e" * 64, "db": "d" * 64}
        service_projects = {
            "api": "markina-gallery-app-" + "1" * 32,
            "web": "markina-gallery-app-" + "2" * 32,
            "db": "markina-gallery",
        }
        service_by_id = {identifier: service for service, identifier in service_ids.items()}
        def run(argv):
            if argv[0] == inventory.APP_COMPOSE_BRIDGE:
                operation = argv[argv.index("--sha") + 2]
                service = argv[-1]
                if operation == "service-project":
                    return self._result(list(argv), service_projects[service] + "\n")
                if operation == "compose":
                    return self._result(list(argv), service_ids[service] + "\n")
                raise AssertionError(f"unexpected bridge operation: {operation}")
            if argv[0] == "/usr/bin/stat":
                return self._result(list(argv), "regular file|0|0|755|1\n")
            if argv[0] == "/usr/bin/git" and argv[1] == "-C" and list(argv[-2:]) == ["rev-parse", "HEAD"]:
                return self._result(list(argv), "a" * 40 + "\n")
            if argv[0] == "/usr/bin/git" and "rev-parse" in argv:
                return self._result(list(argv), "f" * 40 + "\n")
            if argv[0] == "/usr/bin/git" and "hash-object" in argv:
                return self._result(list(argv), "f" * 40 + "\n")
            if "container" in argv and "ls" in argv:
                if "--filter" in argv:
                    service_filter = next(value for value in argv if value.startswith("label=com.docker.compose.service="))
                    service = service_filter.rsplit("=", 1)[-1]
                    return self._result(list(argv), service_ids[service] + "\n")
                return self._result(list(argv), "\n".join([*service_ids.values(), "9" * 64]) + "\n")
            if "container" in argv and "inspect" in argv:
                template = argv[argv.index("--format") + 1]
                if template == inventory.SHARED_CONTAINER_INSPECT:
                    shared = {
                        "c" * 64: "sha256:" + "a" * 64 + "|running|2026-11-20T00:00:00Z",
                        "e" * 64: "sha256:" + "b" * 64 + "|running|2026-11-20T00:00:00Z",
                        "d" * 64: "sha256:" + "f" * 64 + "|running|2026-11-20T00:00:00Z",
                        "9" * 64: "sha256:" + third_party_image * 64 + "|exited|2026-11-19T00:00:00Z",
                    }
                    return self._result(list(argv), "".join(f"{key}|{value}\n" for key, value in shared.items()))
                service = service_by_id[argv[-1]]
                health = "none" if service == "db" else "healthy"
                container_id = service_ids[service]
                image_id = {"api": "a" * 64, "web": "b" * 64, "db": "f" * 64}[service]
                value = (f"{container_id}|sha256:{image_id}|running|true|2026-11-20T00:00:00Z|"
                         f"{service_projects[service]}|{service}|{health}\n")
                return self._result(list(argv), value)
            if " exec " in " ".join(argv):
                return self._result(list(argv), "20261113_0126\n")
            if argv[:3] == ["/usr/bin/df", "-P", "-k"]:
                return self._result(list(argv), "Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 100000 50000 50000 50% /var/lib\n")
            if argv[0] == "/usr/bin/systemctl":
                if argv[-1] == "pyp-platform-backup.timer":
                    return self._result(list(argv), f"ActiveState=inactive\nLoadState=not-found\nUnitFileState={timer_enabled}\n")
                return self._result(list(argv), "ActiveState=inactive\nLoadState=not-found\nUnitFileState=\n")
            raise AssertionError(f"unexpected command class: {argv[0]}")
        return run

    def test_systemd_reader_requests_named_properties_and_preserves_empty_state(self) -> None:
        unit = "pyp-platform-backup.service"
        runner = mock.Mock(return_value=self._result(
            [], "ActiveState=inactive\nLoadState=not-found\nUnitFileState=\n",
        ))
        self.assertEqual(
            inventory.read_systemd_unit_state(unit, runner),
            {"load": "not-found", "enabled": "unknown", "active": "inactive"},
        )
        runner.assert_called_once_with([
            "/usr/bin/systemctl", "show", "--all", "--property=LoadState,UnitFileState,ActiveState", unit,
        ])

    def test_systemd_reader_rejects_invalid_or_incomplete_responses(self) -> None:
        base = "LoadState=loaded\nActiveState=inactive\n"
        for response in (
            base,
            base + "UnitFileState=static\nUnitFileState=disabled\n",
            base + "UnexpectedProperty=disabled\n",
            base + "UnitFileState=new-state\n",
            base + "UnitFileState\n",
        ):
            with self.subTest(response=response), self.assertRaisesRegex(
                inventory.InventoryError, "^systemd_inventory_invalid$",
            ):
                inventory.read_systemd_unit_state(
                    "pyp-platform-backup.timer", mock.Mock(return_value=self._result([], response)),
                )

    def test_inventory_is_sanitized_and_fingerprint_binds_host_and_runtime(self) -> None:
        result = inventory.collect_inventory(self._runner(), root=self.root)
        serialized = str(result)
        self.assertNotIn("abcdef0123456789abcdef0123456789", serialized)
        self.assertEqual(result["inventory"]["checkout_sha"], "a" * 40)
        self.assertEqual(result["inventory"]["database_schema"], "20261113_0126")
        self.assertEqual(result["inventory"]["containers"]["api"]["health"], "healthy")
        self.assertEqual(result["inventory"]["shared_containers"]["count"], 4)
        self.assertNotIn("9" * 64, serialized)
        self.assertEqual(len(result["fingerprint"]), 64)
        self.assertEqual(len(result["runtime_fingerprint"]), 64)
        self.assertTrue(inventory.install_preconditions(result["inventory"]))

    def test_public_inventory_summary_omits_container_and_configuration_identities(self) -> None:
        result = inventory.collect_inventory(self._runner(), root=self.root)
        output = io.StringIO()
        with (mock.patch.object(inventory, "collect_inventory", return_value=result),
              contextlib.redirect_stdout(output)):
            self.assertEqual(inventory.main("a" * 40), 0)
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("backup_runtime_inventory_summary="))
        self.assertEqual(lines[1], "backup_runtime_fingerprint=" + result["fingerprint"])
        summary = json.loads(lines[0].split("=", 1)[1])
        self.assertEqual(set(summary), {
            "schema_version", "checkout_sha", "containers", "database_schema", "disk_var_lib", "units",
        })
        for service in inventory.CONTAINER_ROLES:
            self.assertEqual(set(summary["containers"][service]), {"state", "running", "health"})
        for container in result["inventory"]["containers"].values():
            self.assertNotIn(container["id"], output.getvalue())
            self.assertNotIn(container["image"], output.getvalue())
            self.assertNotIn(container["started_at"], output.getvalue())

    def test_fingerprint_changes_when_machine_identity_changes(self) -> None:
        first = inventory.collect_inventory(self._runner(), root=self.root)["fingerprint"]
        (self.root / "etc/machine-id").write_text("0123456789abcdef0123456789abcdef\n", encoding="ascii")
        second = inventory.collect_inventory(self._runner(), root=self.root)["fingerprint"]
        self.assertNotEqual(first, second)

    def test_enabled_backup_timer_blocks_install(self) -> None:
        result = inventory.collect_inventory(self._runner(timer_enabled="enabled"), root=self.root)
        self.assertFalse(inventory.install_preconditions(result["inventory"]))

    def test_runtime_fingerprint_binds_shared_container_invariance(self) -> None:
        first = inventory.collect_inventory(self._runner(), root=self.root)
        second = inventory.collect_inventory(self._runner(third_party_image="7"), root=self.root)
        self.assertNotEqual(first["runtime_fingerprint"], second["runtime_fingerprint"])

    def test_fixed_inventory_rejects_wrong_container_identity_or_schema(self) -> None:
        base = self._runner()
        def wrong(argv):
            result = base(argv)
            if "container" in argv and "inspect" in argv and argv[-1] == "c" * 64:
                return self._result(list(argv), "c" * 64 + "|sha256:" + "a" * 64 +
                                    "|running|true|now|other-project|api|healthy\n")
            if "exec" in argv:
                return self._result(list(argv), "unknown schema\n")
            return result
        with self.assertRaisesRegex(inventory.InventoryError, "api_container_project_label_mismatch"):
            inventory.collect_inventory(wrong, root=self.root)

    def test_container_record_failures_identify_only_fixed_role_and_field(self) -> None:
        roles = ("api", "web", "db")
        cases = (
            ("record_shape", "container_record_shape_invalid", None),
            ("container_id", "container_id_invalid", "not-a-container-id"),
            ("image_id", "container_image_id_invalid", "not-an-image-id"),
            ("project_label", "container_project_label_mismatch", "other-project-secret"),
            ("service_label", "container_service_label_mismatch", "unexpected-service-secret"),
            ("running_flag", "container_running_flag_invalid", "sometimes"),
            ("state", "container_state_invalid", "migrating"),
            ("health_state", "container_health_state_invalid", "private-health"),
            ("started_at", "container_started_at_invalid", "x" * 65),
        )
        for role in roles:
            for field, code_suffix, invalid_value in cases:
                with self.subTest(role=role, field=field):
                    health = "none" if role == "db" else "healthy"
                    row = ["a" * 64, "sha256:" + "b" * 64, "running", "true",
                           "2026-11-20T00:00:00Z", "markina-gallery", role, health]
                    if field == "record_shape":
                        output = "too|few|fields\n"
                    else:
                        index = {
                            "container_id": 0,
                            "image_id": 1,
                            "state": 2,
                            "running_flag": 3,
                            "started_at": 4,
                            "project_label": 5,
                            "service_label": 6,
                            "health_state": 7,
                        }[field]
                        row[index] = invalid_value
                        output = "|".join(row) + "\n"

                    def runner(argv, captured_output=output):
                        if "container" in argv and "ls" in argv:
                            return self._result(list(argv), "a" * 64 + "\n")
                        return self._result(list(argv), captured_output)

                    expected = f"{role}_{code_suffix}"
                    active_identity = ({"project": "markina-gallery", "id": "a" * 64}
                                       if role in inventory.APP_SERVICES else None)
                    with self.assertRaises(inventory.InventoryError) as raised:
                        inventory._container(role, runner, active_identity=active_identity)
                    self.assertEqual(str(raised.exception), expected)
                    self.assertIn(expected, inventory.SAFE_INVENTORY_ERROR_CODES)
                    self.assertNotIn("secret", str(raised.exception))

    def test_app_container_selection_uses_active_bridge_and_revalidates_project_label(self) -> None:
        base = self._runner()
        commands: list[list[str]] = []

        def recording_runner(argv):
            commands.append(list(argv))
            return base(argv)

        identity = inventory._active_app_identity("api", "a" * 40, recording_runner)
        result = inventory._container("api", recording_runner, active_identity=identity)
        self.assertEqual([command[command.index("--sha") + 2] for command in commands[:2]],
                         ["service-project", "compose"])
        self.assertTrue(all(command[0] == inventory.APP_COMPOSE_BRIDGE for command in commands[:2]))
        self.assertFalse(any("container" in command and "ls" in command for command in commands))
        self.assertIn("markina-gallery-app-" + "1" * 32, identity["project"])
        self.assertEqual(result["id"], "c" * 64)

    def test_database_container_selection_requires_one_fixed_label_match(self) -> None:
        for output, expected in (
            ("", "db_container_record_missing"),
            (("a" * 64) + "\n" + ("b" * 64) + "\n", "db_container_record_ambiguous"),
            ("not-a-container-id\n", "db_container_id_invalid"),
        ):
            with self.subTest(expected=expected):
                def runner(argv, selected=output):
                    if "container" in argv and "ls" in argv:
                        return self._result(list(argv), selected)
                    raise AssertionError("an invalid service selection must fail before inspect")

                with self.assertRaises(inventory.InventoryError) as raised:
                    inventory._container("db", runner)
                self.assertEqual(str(raised.exception), expected)
                self.assertIn(expected, inventory.SAFE_INVENTORY_ERROR_CODES)

    def test_container_selection_command_failure_is_sanitized(self) -> None:
        def runner(argv):
            if "container" in argv and "ls" in argv:
                return self._result(list(argv), "private-container-output", returncode=1)
            raise AssertionError("failed service listing must stop before inspect")

        with self.assertRaises(inventory.InventoryError) as raised:
            inventory._container("db", runner)
        self.assertEqual(str(raised.exception), "container_service_list_failed")
        self.assertIn(str(raised.exception), inventory.SAFE_INVENTORY_ERROR_CODES)

    def test_unknown_container_role_or_validation_class_uses_generic_safe_code(self) -> None:
        error = inventory._container_inventory_error("private-role", "untrusted-value")
        self.assertEqual(str(error), "container_inventory_invalid")
        self.assertIn(str(error), inventory.SAFE_INVENTORY_ERROR_CODES)

        def unexpected_runner(_argv):
            raise AssertionError("unknown roles must be rejected before invoking Docker")

        with self.assertRaisesRegex(inventory.InventoryError, "container_inventory_invalid"):
            inventory._container("private-role", unexpected_runner)

    def test_inventory_failure_logs_only_allowlisted_code(self) -> None:
        for code in (
            "container_service_list_failed",
            "container_inspect_failed",
            "api_container_record_missing",
            "api_container_record_ambiguous",
            "api_active_project_resolution_failed",
            "web_active_container_id_invalid",
            "shared_container_list_empty",
            "api_container_project_label_mismatch",
        ):
            with self.subTest(code=code):
                output = io.StringIO()
                error = inventory.InventoryError(code)
                with (mock.patch.object(inventory, "collect_inventory", side_effect=error),
                      contextlib.redirect_stdout(output)):
                    result = inventory.main()
                self.assertEqual(result, 1)
                self.assertEqual(output.getvalue(),
                                 f"platform-backup-runtime: inventory failed ({code})\n")

    def test_inventory_failure_never_logs_untrusted_exception_text(self) -> None:
        failures = (
            (inventory.InventoryError("/etc/pyp-backup/source.json: secret"), "inventory_error"),
            (OSError("/etc/pyp-backup/keyring.json: secret"), "inventory_io_failed"),
            (subprocess.TimeoutExpired("docker", 20, stderr="private output"),
             "inventory_command_failed"),
        )
        for error, expected in failures:
            with self.subTest(expected=expected):
                output = io.StringIO()
                with (mock.patch.object(inventory, "collect_inventory", side_effect=error),
                      contextlib.redirect_stdout(output)):
                    result = inventory.main()
                self.assertEqual(result, 1)
                self.assertEqual(output.getvalue(),
                                 f"platform-backup-runtime: inventory failed ({expected})\n")
                self.assertNotIn("/etc", output.getvalue())
                self.assertNotIn("secret", output.getvalue())
                self.assertNotIn("private output", output.getvalue())

    def test_active_app_bridge_rejects_missing_duplicate_invalid_and_untrusted_outputs(self) -> None:
        cases = (
            ("", 0, "api_active_project_invalid"),
            ("markina-gallery-app-" + "1" * 32 + "\nextra\n", 0,
             "api_active_project_invalid"),
            ("private-project\n", 0, "api_active_project_invalid"),
        )
        for project_output, status, expected in cases:
            with self.subTest(expected=expected, output=project_output[:12]):
                def bad_project(argv, output=project_output, result_status=status):
                    return self._result(list(argv), output, returncode=result_status)

                with self.assertRaises(inventory.InventoryError) as raised:
                    inventory._active_app_identity("api", "a" * 40, bad_project)
                self.assertEqual(str(raised.exception), expected)
                self.assertIn(expected, inventory.SAFE_INVENTORY_ERROR_CODES)
                self.assertNotIn("private-project", str(raised.exception))

        def failed_bridge(argv):
            return self._result(list(argv), "private bridge output", returncode=1)

        with self.assertRaisesRegex(inventory.InventoryError,
                                    "api_active_project_resolution_failed"):
            inventory._active_app_identity("api", "a" * 40, failed_bridge)

        responses = iter([
            "markina-gallery-app-" + "1" * 32 + "\n",
            "a" * 64 + "\n" + "b" * 64 + "\n",
        ])

        def duplicate_id(argv):
            return self._result(list(argv), next(responses))

        with self.assertRaisesRegex(inventory.InventoryError,
                                    "api_active_container_id_invalid"):
            inventory._active_app_identity("api", "a" * 40, duplicate_id)

    def test_inventory_rechecks_active_app_identity_before_returning_fingerprint(self) -> None:
        base = self._runner()
        api_id_calls = 0

        def changing_api(argv):
            nonlocal api_id_calls
            result = base(argv)
            if (argv[0] == inventory.APP_COMPOSE_BRIDGE
                    and argv[argv.index("--sha") + 2] == "compose" and argv[-1] == "api"):
                api_id_calls += 1
                if api_id_calls == 2:
                    return self._result(list(argv), "f" * 64 + "\n")
            return result

        with self.assertRaisesRegex(inventory.InventoryError, "inventory_changed_during_scan"):
            inventory.collect_inventory(changing_api, root=self.root)

    def test_inventory_requires_installed_bridge_blob_to_match_the_reviewed_sha(self) -> None:
        def mismatched_bridge(argv):
            if argv[0] == "/usr/bin/stat":
                return self._result(list(argv), "regular file|0|0|755|1\n")
            if argv[0] == "/usr/bin/git" and "rev-parse" in argv:
                return self._result(list(argv), "f" * 40 + "\n")
            if argv[0] == "/usr/bin/git" and "hash-object" in argv:
                return self._result(list(argv), "e" * 40 + "\n")
            raise AssertionError("bridge identity must be verified before resolving services")

        with self.assertRaisesRegex(inventory.InventoryError,
                                    "active_compose_bridge_identity_invalid"):
            inventory._verify_app_compose_bridge("a" * 40, mismatched_bridge)

        def unsafe_metadata(argv):
            return self._result(list(argv), "symbolic link|0|0|755|1\n")

        with self.assertRaisesRegex(inventory.InventoryError,
                                    "active_compose_bridge_identity_invalid"):
            inventory._verify_app_compose_bridge("a" * 40, unsafe_metadata)

    def test_container_diagnostics_aggregate_fixed_roles_and_states(self) -> None:
        label_ids_by_role = {
            "api": ["a" * 64, "b" * 64, "c" * 64, "d" * 64, "e" * 64],
            "web": [],
            "db": ["0" * 64],
        }
        compose_ids_by_role = {
            "api": ["a" * 64, "b" * 64, "c" * 64, "f" * 64],
            "web": [],
            "db": ["0" * 64],
        }
        states = {
            "a" * 64: "running",
            "b" * 64: "created",
            "c" * 64: "exited",
            "d" * 64: "dead",
            "e" * 64: "paused",
            "0" * 64: "restarting",
        }
        commands: list[list[str]] = []

        def runner(argv):
            commands.append(list(argv))
            if "compose" in argv and "ps" in argv:
                role = argv[-1]
                self.assertIn("--project-name", argv)
                self.assertEqual(argv[argv.index("--project-name") + 1], "markina-gallery")
                self.assertIn("--project-directory", argv)
                self.assertEqual(argv[argv.index("--project-directory") + 1],
                                 "/opt/markina-gallery/docker")
                self.assertIn("--file", argv)
                self.assertEqual(argv[argv.index("--file") + 1],
                                 "/opt/markina-gallery/docker/docker-compose.yml")
                self.assertIn("--all", argv)
                self.assertIn("--quiet", argv)
                self.assertIn("--no-trunc", argv)
                self.assertIn("--orphans=false", argv)
                return self._result(list(argv), "".join(
                    f"{value}\n" for value in compose_ids_by_role[role]))
            if "container" in argv and "ls" in argv:
                project_filter = "label=com.docker.compose.project=markina-gallery"
                service_filter = next(value for value in argv
                                      if value.startswith("label=com.docker.compose.service="))
                self.assertIn(project_filter, argv)
                role = service_filter.rsplit("=", 1)[-1]
                identifiers = label_ids_by_role[role]
                return self._result(list(argv), "".join(f"{value}\n" for value in identifiers))
            if "container" in argv and "inspect" in argv:
                identifiers = argv[argv.index("--format") + 2:]
                rows = [f"{identifier}|{states[identifier]}|markina-gallery|"
                        f"{next(role for role, values in label_ids_by_role.items() if identifier in values)}"
                        for identifier in identifiers]
                return self._result(list(argv), "".join(f"{row}\n" for row in rows))
            raise AssertionError(f"unexpected command class: {argv[0]}")

        result = inventory.collect_container_diagnostics(runner)

        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(set(result["roles"]), {"api", "web", "db"})
        self.assertEqual(result["roles"]["api"], {
            "label_records": 5, "compose_records": 4, "matched_records": 3,
            "label_only_records": 2, "compose_only_records": 1,
            "running": 1, "stopped": 3, "unknown": 1,
        })
        self.assertEqual(result["roles"]["web"], {
            "label_records": 0, "compose_records": 0, "matched_records": 0,
            "label_only_records": 0, "compose_only_records": 0,
            "running": 0, "stopped": 0, "unknown": 0,
        })
        self.assertEqual(result["roles"]["db"], {
            "label_records": 1, "compose_records": 1, "matched_records": 1,
            "label_only_records": 0, "compose_only_records": 0,
            "running": 0, "stopped": 0, "unknown": 1,
        })
        serialized = json.dumps(result, sort_keys=True)
        for identifier in states:
            self.assertNotIn(identifier, serialized)
        self.assertNotIn("paused", serialized)
        self.assertNotIn("restarting", serialized)
        self.assertNotIn("f" * 64, serialized)
        compose_commands = [command for command in commands if "compose" in command and "ps" in command]
        self.assertEqual(len(compose_commands), 6)
        self.assertEqual(
            {next(value.rsplit("=", 1)[-1] for value in command
                 if value.startswith("label=com.docker.compose.service="))
             for command in commands if "container" in command and "ls" in command},
            {"api", "web", "db"},
        )
        output = io.StringIO()
        with (mock.patch.object(inventory, "collect_container_diagnostics", return_value=result),
              contextlib.redirect_stdout(output)):
            self.assertEqual(inventory.diagnostic_main(), 0)
        self.assertEqual(output.getvalue(),
                         "backup_runtime_container_diagnostics="
                         + json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
        self.assertNotIn("fingerprint", output.getvalue())
        self.assertNotIn("preconditions", output.getvalue())
        for identifier in states:
            self.assertNotIn(identifier, output.getvalue())

    def test_container_diagnostics_bound_record_count_without_partial_output(self) -> None:
        identifiers = [f"{value:064x}" for value in range(513)]

        def runner(argv):
            if "container" in argv and "ls" in argv:
                return self._result(list(argv), "".join(f"{value}\n" for value in identifiers))
            raise AssertionError("excessive list must fail before inspection")

        with self.assertRaises(inventory.InventoryError) as raised:
            inventory.collect_container_diagnostics(runner)
        self.assertEqual(str(raised.exception), "diagnostic_container_list_invalid")
        self.assertNotIn(identifiers[0], str(raised.exception))

    def test_container_diagnostics_rejects_bad_compose_lists_and_limits(self) -> None:
        identifier = "a" * 64
        invalid_cases = (
            ("not-an-id\n", 0, "diagnostic_compose_list_invalid"),
            (identifier + "\n" + identifier + "\n", 0, "diagnostic_compose_list_invalid"),
            ("private-compose-output\n", 1, "diagnostic_compose_list_failed"),
        )
        for output, returncode, expected_code in invalid_cases:
            def runner(argv, output=output, returncode=returncode):
                if "container" in argv and "ls" in argv:
                    return self._result(list(argv), identifier + "\n")
                if "compose" in argv and "ps" in argv:
                    return self._result(list(argv), output, returncode=returncode)
                raise AssertionError("invalid Compose list must fail before inspection")

            with self.subTest(expected_code=expected_code, output=output):
                with self.assertRaises(inventory.InventoryError) as raised:
                    inventory.collect_container_diagnostics(runner)
                self.assertEqual(str(raised.exception), expected_code)
                self.assertNotIn("private", str(raised.exception))

        identifiers = [f"{value:064x}" for value in range(513)]

        def excessive_compose_list(argv):
            if "container" in argv and "ls" in argv:
                return self._result(list(argv), "")
            if "compose" in argv and "ps" in argv:
                return self._result(list(argv), "".join(f"{value}\n" for value in identifiers))
            raise AssertionError("excessive Compose list must fail before inspection")

        with self.assertRaises(inventory.InventoryError) as raised:
            inventory.collect_container_diagnostics(excessive_compose_list)
        self.assertEqual(str(raised.exception), "diagnostic_compose_list_invalid")
        self.assertNotIn(identifiers[0], str(raised.exception))

    def test_container_diagnostics_rejects_a_changing_source_snapshot(self) -> None:
        identifier = "a" * 64
        label_calls = 0

        def runner(argv):
            nonlocal label_calls
            if "container" in argv and "ls" in argv:
                label_calls += 1
                return self._result(list(argv), identifier + "\n" if label_calls == 1 else "")
            if "compose" in argv and "ps" in argv:
                return self._result(list(argv), identifier + "\n")
            if "container" in argv and "inspect" in argv:
                return self._result(list(argv), f"{identifier}|running|markina-gallery|api\n")
            raise AssertionError("unexpected command class")

        with self.assertRaises(inventory.InventoryError) as raised:
            inventory.collect_container_diagnostics(runner)
        self.assertEqual(str(raised.exception), "diagnostic_inventory_changed")
        self.assertNotIn(identifier, str(raised.exception))

    def test_container_diagnostics_discard_partial_counts_and_sanitize_failures(self) -> None:
        api_id = "a" * 64

        def runner(argv):
            if "container" in argv and "ls" in argv:
                service = next(value.rsplit("=", 1)[-1] for value in argv
                               if value.startswith("label=com.docker.compose.service="))
                if service == "api":
                    return self._result(list(argv), api_id + "\n")
                if service == "web":
                    return self._result(list(argv), "private-list-output\n", returncode=1)
                return self._result(list(argv), "")
            if "compose" in argv and "ps" in argv:
                return self._result(list(argv), "")
            if "container" in argv and "inspect" in argv:
                return self._result(list(argv), f"{api_id}|running|markina-gallery|api\n")
            raise AssertionError(f"unexpected command class: {argv[0]}")

        with self.assertRaises(inventory.InventoryError) as raised:
            inventory.collect_container_diagnostics(runner)
        self.assertEqual(str(raised.exception), "diagnostic_container_list_failed")
        self.assertNotIn("private", str(raised.exception))
        self.assertIn(str(raised.exception), inventory.SAFE_DIAGNOSTIC_ERROR_CODES)

        output = io.StringIO()
        with (mock.patch.object(inventory, "collect_container_diagnostics",
                                side_effect=inventory.InventoryError("diagnostic_container_list_failed")),
              contextlib.redirect_stdout(output)):
            self.assertEqual(inventory.diagnostic_main(), 1)
        self.assertEqual(output.getvalue(),
                         "platform-backup-runtime: container diagnostics failed "
                         "(diagnostic_container_list_failed)\n")
        self.assertNotIn("backup_runtime_container_diagnostics", output.getvalue())
        self.assertNotIn("fingerprint", output.getvalue())
        self.assertNotIn("private", output.getvalue())

    def test_container_diagnostics_sanitize_inspection_failures(self) -> None:
        identifier = "a" * 64

        def inspect_failure(argv):
            if "container" in argv and "ls" in argv:
                return self._result(list(argv), identifier + "\n")
            if "compose" in argv and "ps" in argv:
                return self._result(list(argv), identifier + "\n")
            if "container" in argv and "inspect" in argv:
                return self._result(list(argv), "private-inspect-output\n", returncode=1)
            raise AssertionError(f"unexpected command class: {argv[0]}")

        with self.assertRaises(inventory.InventoryError) as failed:
            inventory.collect_container_diagnostics(inspect_failure)
        self.assertEqual(str(failed.exception), "diagnostic_container_inspect_failed")
        self.assertNotIn("private", str(failed.exception))

        def invalid_label(argv):
            if "container" in argv and "ls" in argv:
                return self._result(list(argv), identifier + "\n")
            if "compose" in argv and "ps" in argv:
                return self._result(list(argv), identifier + "\n")
            if "container" in argv and "inspect" in argv:
                return self._result(list(argv),
                                    f"{identifier}|running|private-project-label|api\n")
            raise AssertionError(f"unexpected command class: {argv[0]}")

        with self.assertRaises(inventory.InventoryError) as invalid:
            inventory.collect_container_diagnostics(invalid_label)
        self.assertEqual(str(invalid.exception), "diagnostic_container_inventory_invalid")
        self.assertNotIn("private-project-label", str(invalid.exception))

    def test_installed_release_requires_matching_root_owned_receipts(self) -> None:
        if os.name != "posix" or os.geteuid() != 0:
            self.skipTest("root-only release evidence requires POSIX root")
        sha = "a" * 40
        bundle_sha = "b" * 64
        install = self.root / "opt/pyp-backup-runtime"
        release = install / "releases" / sha
        rollback_root = install / "rollback"
        release.mkdir(parents=True, mode=0o700)
        rollback_root.mkdir(mode=0o700)
        os.chmod(install, 0o700)
        os.chmod(install / "releases", 0o700)
        rollback_data = b'{"schema_version":1,"source_sha":"' + sha.encode() + b'"}\n'
        rollback_path = rollback_root / f"{sha}.json"
        rollback_path.write_bytes(rollback_data)
        os.chmod(rollback_root, 0o700)
        os.chmod(rollback_path, 0o600)
        os.symlink(f"releases/{sha}", install / "current")
        manifest = {"schema_version": 1, "source_sha": sha, "files": []}
        (release / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        os.chmod(release / "manifest.json", 0o400)
        receipt = {
            "schema_version": 1, "status": "installed_inert", "source_sha": sha,
            "bundle_sha256": bundle_sha, "approval_fingerprint": "c" * 64,
            "current_release": f"releases/{sha}", "previous_release": None,
            "rollback_receipt_sha256": hashlib.sha256(rollback_data).hexdigest(),
            "service_enabled": False, "service_active": False,
            "timer_enabled": False, "timer_active": False, "destination_enabled": False,
        }
        (release / "install-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        os.chmod(release / "install-receipt.json", 0o600)
        os.chmod(release, 0o700)
        verified = inventory.verify_installed_release(sha, bundle_sha, install)
        self.assertEqual(verified, {"source_sha": sha, "bundle_sha256": bundle_sha, "status": "installed_inert"})
        with self.assertRaisesRegex(inventory.InventoryError, "installed_release_current_mismatch"):
            inventory.verify_installed_release("d" * 40, bundle_sha, install)
        rollback_path.write_bytes(b"changed")
        with self.assertRaisesRegex(inventory.InventoryError, "installed_release_rollback_mismatch"):
            inventory.verify_installed_release(sha, bundle_sha, install)


if __name__ == "__main__":
    unittest.main()
