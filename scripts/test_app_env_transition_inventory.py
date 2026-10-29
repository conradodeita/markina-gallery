from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend.app.environment_transition_inventory as inventory_contract
from backend.app.environment_transition_inventory import (
    BIOMETRIC_COUNTERS,
    CONFIG_DIGEST_NAMES,
    CREDENTIAL_COUNTERS,
    EXPECTED_SERVICES,
    RETIRED_SERVICES,
    build_environment_inventory,
)
from scripts import app_env_transition_inventory as collector
from scripts.app_env_transition_inventory import (
    SAFE_FAILURE_CODES,
    binding_mismatches,
    integration_evidence,
    live_payment_gate,
)
from scripts.app_env_transition_inventory_report import summary, validate_report

SHA = "a" * 40


def make_inventory(**overrides) -> dict:
    services = []
    for name in sorted(EXPECTED_SERVICES):
        retired = name in RETIRED_SERVICES
        services.append({
            "name": name,
            "status": "missing" if retired else "running",
            "health": "none" if retired else "healthy",
            "image_digest": None if retired else "sha256:" + "1" * 64,
            "revision": None if retired else SHA,
            "ports": ([{"host_ip": "127.0.0.1", "host_port": 8080}] if name == "nginx" else []),
        })
    values = {
        "source_environment": "staging",
        "target_environment": "production",
        "code_revision": SHA,
        "schema_revision": "20261028_0090",
        "services": services,
        "configuration_digests": {name: "b" * 64 for name in CONFIG_DIGEST_NAMES},
        "credential_counts": {name: 0 for name in CREDENTIAL_COUNTERS},
        "biometric_counts": {name: 0 for name in BIOMETRIC_COUNTERS},
        "whatsapp_binding_counts": [],
        "integration_evidence": {
            name: {
                "enabled": False,
                "credential_matches_target": None,
                "provider_validated_for_target": None,
            }
            for name in ("facial", "smtp", "whatsapp")
        },
        "live_payment_gate": False,
        "unknown_consumer_count": 0,
    }
    values.update(overrides)
    return build_environment_inventory(**values)


def make_report(inventory: dict | None, *, incomplete: bool = False) -> dict:
    if incomplete:
        return {
            "target_sha": SHA,
            "collection_status": "incomplete",
            "inventory": None,
            "blockers": ["coleta_incompleta"],
            "approval_fingerprint": None,
            "failure_category": "falha_interna",
        }
    return {
        "target_sha": SHA,
        "collection_status": "complete",
        "inventory": inventory,
        "blockers": inventory["blockers"],
        "approval_fingerprint": inventory["approval_fingerprint"],
        "failure_category": None,
    }


class AppEnvInventoryReportTests(unittest.TestCase):
    def test_inventory_error_categories_are_closed_and_allowlisted(self):
        source = ast.parse(Path(collector.__file__).read_text(encoding="utf-8"))
        categories = set()
        for node in ast.walk(source):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if (node.func.id == "InventoryError" and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                categories.add(node.args[0].value)
            if node.func.id == "require" and len(node.args) >= 2:
                self.assertIsInstance(node.args[1], ast.Constant)
                self.assertIsInstance(node.args[1].value, str)
                categories.add(node.args[1].value)

        self.assertTrue(categories)
        self.assertLessEqual(categories, SAFE_FAILURE_CODES)

    def test_invalid_sha_is_rejected_before_any_remote_command(self):
        with patch.object(collector, "run") as run, self.assertRaises(collector.InventoryError):
            collector.verify_main("invalid")
        run.assert_not_called()

    def test_compose_resolution_failures_use_sanitized_categories(self):
        cases = (
            (FileNotFoundError, "compose_caminho_ausente"),
            (PermissionError, "compose_resolucao_negada"),
            (OSError, "compose_resolucao_indisponivel"),
        )
        for error_type, expected in cases:
            with self.subTest(category=expected), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                compose_path = root / "docker-compose.yml"
                compose_path.write_text("services: {}", encoding="utf-8")
                services = {"api": {"compose_files": str(compose_path)}}
                error = error_type("private-path-sentinel /secret/compose.yml")
                with (
                    patch.object(collector, "ROOT", root),
                    patch.object(collector, "ALLOWED_REMOTE_ROOTS", (root,)),
                    patch.object(Path, "resolve", side_effect=error),
                    self.assertRaises(collector.InventoryError) as raised,
                ):
                    collector.compose_digest(services)

                self.assertEqual(str(raised.exception), expected)
                self.assertEqual(collector.sanitized_failure_code(raised.exception), expected)
                self.assertNotIn("private-path-sentinel", str(raised.exception))
                self.assertNotIn("/secret/compose.yml", str(raised.exception))

    def test_compose_read_failures_use_sanitized_categories(self):
        cases = (
            (FileNotFoundError, "compose_arquivo_ausente"),
            (PermissionError, "compose_leitura_negada"),
            (OSError, "compose_leitura_indisponivel"),
        )
        for error_type, expected in cases:
            with self.subTest(category=expected), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                compose_path = root / "docker-compose.yml"
                compose_path.write_text("services: {}", encoding="utf-8")
                services = {"api": {"compose_files": str(compose_path)}}
                error = error_type("private-path-sentinel /secret/compose.yml")
                with (
                    patch.object(collector, "ROOT", root),
                    patch.object(collector, "ALLOWED_REMOTE_ROOTS", (root,)),
                    patch.object(Path, "read_bytes", side_effect=error),
                    self.assertRaises(collector.InventoryError) as raised,
                ):
                    collector.compose_digest(services)

                self.assertEqual(str(raised.exception), expected)
                self.assertEqual(collector.sanitized_failure_code(raised.exception), expected)
                self.assertNotIn("private-path-sentinel", str(raised.exception))
                self.assertNotIn("/secret/compose.yml", str(raised.exception))

    def test_main_turns_failed_source_into_sanitized_report(self):
        output = io.StringIO()
        with (
            patch.object(collector, "verify_main"),
            patch.object(collector, "load_contract", return_value=inventory_contract),
            patch.object(collector, "collect", side_effect=collector.InventoryError("secret-sentinel /private/path")),
            patch.object(sys, "argv", ["app_env_transition_inventory.py", "app-env-inventory", "--sha", SHA]),
            redirect_stdout(output),
        ):
            collector.main()

        report = json.loads(output.getvalue())
        self.assertEqual(report["collection_status"], "incomplete")
        self.assertEqual(report["blockers"], ["coleta_incompleta"])
        self.assertEqual(report["failure_category"], "falha_interna")
        self.assertIsNone(report["approval_fingerprint"])
        self.assertNotIn("secret-sentinel", output.getvalue())
        self.assertNotIn("/private/path", output.getvalue())

    def test_main_preserves_only_known_static_failure_categories(self):
        categories = (
            "keyring_indisponivel",
            "compose_caminho_ausente",
            "compose_resolucao_negada",
            "compose_resolucao_indisponivel",
            "compose_arquivo_ausente",
            "compose_leitura_negada",
            "compose_leitura_indisponivel",
        )
        for category in categories:
            with self.subTest(category=category):
                output = io.StringIO()
                with (
                    patch.object(collector, "verify_main"),
                    patch.object(collector, "load_contract", return_value=inventory_contract),
                    patch.object(collector, "collect", side_effect=collector.InventoryError(category)),
                    patch.object(
                        sys, "argv", ["app_env_transition_inventory.py", "app-env-inventory", "--sha", SHA]
                    ),
                    redirect_stdout(output),
                ):
                    collector.main()

                report = json.loads(output.getvalue())
                self.assertEqual(report["failure_category"], category)
                self.assertEqual(report["collection_status"], "incomplete")
                self.assertIsNone(report["inventory"])
                self.assertIsNone(report["approval_fingerprint"])

    def test_main_maps_unclassified_exception_to_generic_category(self):
        output = io.StringIO()
        with (
            patch.object(collector, "verify_main"),
            patch.object(collector, "load_contract", return_value=inventory_contract),
            patch.object(
                collector,
                "collect",
                side_effect=RuntimeError("private id, secret, /private/path"),
            ),
            patch.object(sys, "argv", ["app_env_transition_inventory.py", "app-env-inventory", "--sha", SHA]),
            redirect_stdout(output),
        ):
            collector.main()

        report = json.loads(output.getvalue())
        self.assertEqual(report["failure_category"], "falha_interna")
        self.assertIsNone(report["inventory"])
        self.assertIsNone(report["approval_fingerprint"])
        self.assertNotIn("private id", output.getvalue())
        self.assertNotIn("secret", output.getvalue())
        self.assertNotIn("/private/path", output.getvalue())

    def test_active_container_keeps_identifier_only_in_memory(self):
        container = {
            "Id": "private-container-id",
            "Config": {
                "Labels": {
                    "com.docker.compose.project": "markina-gallery",
                    "com.docker.compose.service": "api",
                    "com.docker.compose.project.config_files": "/opt/markina-gallery/docker/docker-compose.yml",
                },
                "Env": ["APP_ENV=staging", "APP_VERSION=" + SHA],
            },
            "State": {"Status": "running", "Health": {"Status": "healthy"}},
            "Image": "sha256:" + "1" * 64,
            "NetworkSettings": {"Ports": {}},
        }
        with patch.object(collector, "run", side_effect=["private-container-id", json.dumps([container])]):
            services, unknown = collector.active_containers()

        self.assertEqual(services["api"]["id"], "private-container-id")
        self.assertEqual(services["api"]["environment"]["APP_ENV"], "staging")
        self.assertEqual(unknown, 0)

    @unittest.skipUnless(hasattr(os, "getuid"), "permissões POSIX verificadas no worker Linux do CI")
    def test_keyring_is_compared_in_memory_and_only_digest_is_returned(self):
        secret = "secret-sentinel-not-for-output"
        data = (
            "INTEGRATION_SECRET_ENV=staging\n"
            "INTEGRATION_SECRET_ACTIVE_KEY_ID=key-a\n"
            f"INTEGRATION_SECRET_KEYS={secret}\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            key_file = state / "integration-secrets.env"
            key_file.write_text(data, encoding="utf-8")
            key_file.chmod(0o600)
            values = {
                "INTEGRATION_SECRET_ENV": "staging",
                "INTEGRATION_SECRET_ACTIVE_KEY_ID": "key-a",
                "INTEGRATION_SECRET_KEYS": secret,
            }
            with patch.object(collector, "STATE", state):
                result = collector.verify_keyring(values, values)

        self.assertEqual(result, hashlib.sha256(data.encode()).hexdigest())
        self.assertNotIn(secret, result)

    def test_database_probe_sends_read_only_sql_and_returns_only_aggregate_fixture(self):
        payload = {
            "schema_revision": "20261028_0090",
            "credential_counts": {"mercadopago_access_token": 0, "mercadopago_webhook_secret": 0},
            "biometric_counts": {
                "active_jobs": 0,
                "photo_embeddings": 0,
                "search_notifications": 0,
                "search_reference_locators": 0,
                "reference_files": 0,
            },
            "whatsapp_bindings": {"channel_bindings": [], "settings_total": 0, "settings_enabled": 0},
            "unknown_reference_entries": 0,
        }
        with patch.object(collector, "run", return_value=json.dumps(payload)) as run:
            result = collector.database_probe("private-container-id")

        program = run.call_args.kwargs["data"]
        self.assertIn("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY", program)
        self.assertIn("FROM mercadopago_account", program)
        self.assertNotIn("private-container-id", json.dumps(result))

    def test_collect_emits_only_sanitized_contract_fields(self):
        secret = "secret-sentinel-not-for-output"
        shared = {
            "APP_ENV": "staging",
            "APP_VERSION": SHA,
            "INTEGRATION_SECRET_ENV": "staging",
            "INTEGRATION_SECRET_ACTIVE_KEY_ID": "key-a",
            "INTEGRATION_SECRET_KEYS": secret,
            "MERCADOPAGO_ALLOW_LIVE_PAYMENTS": "false",
            "WHATSAPP_PROVIDER": "sandbox",
            "WHATSAPP_CREDENTIAL_ENV": "staging",
            "EMAIL_PROVIDER": "sandbox",
            "EMAIL_CREDENTIAL_ENV": "staging",
            "FACIAL_PROCESSING_ENABLED": "false",
            "FACIAL_CREDENTIAL_ENV": "staging",
            "FACIAL_AEAD_ACTIVE_KEY_ID": "facial-key-a",
            "FACIAL_AEAD_KEYS_JSON": "facial-secret-sentinel",
            "FACIAL_REFERENCE_ROOT": "/private/path/sentinel",
            "SMTP_PASSWORD": "smtp-secret-sentinel",
        }
        services = {}
        for name in EXPECTED_SERVICES - RETIRED_SERVICES:
            if name in {"api", "worker"}:
                env = dict(shared)
            elif name in {"face-search-worker", "face-index-worker", "face-maintenance-worker"}:
                env = {
                    "APP_ENV": "staging",
                    "APP_VERSION": SHA,
                    "FACIAL_PROCESSING_ENABLED": "false",
                    "FACIAL_CREDENTIAL_ENV": "staging",
                    "FACIAL_AEAD_ACTIVE_KEY_ID": "facial-key-a",
                    "FACIAL_AEAD_KEYS_JSON": "facial-secret-sentinel",
                    "FACIAL_REFERENCE_ROOT": "/private/path/sentinel",
                }
            else:
                env = {}
            services[name] = {
                "id": "private-container-id-" + name,
                "restart_count": 0,
                "name": name,
                "status": "running",
                "health": "healthy",
                "image_digest": "sha256:" + "1" * 64,
                "revision": env.get("APP_VERSION"),
                "ports": ([{"host_ip": "127.0.0.1", "host_port": 8080}] if name == "nginx" else []),
                "environment": env,
                "compose_files": "/private/path/docker-compose.yml",
            }
        database = {
            "schema_revision": "20261028_0090",
            "credential_counts": {"mercadopago_access_token": 2, "mercadopago_webhook_secret": 2},
            "biometric_counts": {name: 0 for name in BIOMETRIC_COUNTERS},
            "whatsapp_bindings": {"channel_bindings": [], "settings_total": 0, "settings_enabled": 0},
            "unknown_reference_entries": 1,
        }
        with (
            patch.object(collector, "active_containers", return_value=(services, 0)),
            patch.object(collector, "database_probe", return_value=database),
            patch.object(collector, "verify_keyring", return_value="c" * 64),
            patch.object(collector, "compose_digest", return_value="d" * 64),
        ):
            report = collector.collect(SHA, inventory_contract)

        rendered = json.dumps(report, sort_keys=True)
        self.assertEqual(report["collection_status"], "complete")
        self.assertTrue(report["inventory"]["blockers"])
        self.assertIsNone(report["approval_fingerprint"])
        self.assertNotIn(secret, rendered)
        self.assertNotIn("smtp-secret-sentinel", rendered)
        self.assertNotIn("facial-secret-sentinel", rendered)
        self.assertNotIn("private-container-id", rendered)
        self.assertNotIn("/private/path", rendered)

    def test_incomplete_source_is_reported_without_fingerprint(self):
        report = make_report(None, incomplete=True)
        validated = validate_report([json.dumps(report)], SHA)
        rendered = summary(validated)

        self.assertIn("coleta_incompleta", rendered)
        self.assertIn("falha_interna", rendered)
        self.assertIn("Fingerprint: indisponível", rendered)
        self.assertNotIn("approval_fingerprint=", rendered)

    def test_complete_but_blocked_inventory_is_reported_without_fingerprint(self):
        report = make_report(make_inventory(unknown_consumer_count=1))
        validated = validate_report([json.dumps(report)], SHA)
        rendered = summary(validated)

        self.assertIn("consumidor_nao_classificado", rendered)
        self.assertIsNone(validated["approval_fingerprint"])
        self.assertIn("Fingerprint:", rendered)

    def test_complete_inventory_must_match_contract_fingerprint(self):
        report = make_report(make_inventory())
        validated = validate_report([json.dumps(report)], SHA)

        self.assertIsNotNone(validated["approval_fingerprint"])
        self.assertIn("Nenhum", summary(validated))

        report["approval_fingerprint"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "relatorio_invalido"):
            validate_report([json.dumps(report)], SHA)

    def test_report_cli_writes_empty_fingerprint_for_blocked_inventory(self):
        report = make_report(make_inventory(unknown_consumer_count=1))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "inventory.jsonl"
            output = root / "github-output.txt"
            summary_file = root / "summary.md"
            source.write_text(json.dumps(report) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("app_env_transition_inventory_report.py")),
                 str(source), SHA, str(output), str(summary_file)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "approval_fingerprint=\n")
            self.assertIn("consumidor_nao_classificado", summary_file.read_text(encoding="utf-8"))

    def test_incomplete_report_cannot_carry_partial_data_or_fingerprint(self):
        report = make_report(None, incomplete=True)
        report["approval_fingerprint"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "relatorio_invalido"):
            validate_report([json.dumps(report)], SHA)

    def test_incomplete_report_rejects_unrecognized_failure_category(self):
        report = make_report(None, incomplete=True)
        for category in (
            "secret-sentinel /private/path",
            None,
            [],
            {"secret": "value"},
        ):
            with self.subTest(category=category):
                report["failure_category"] = category
                with self.assertRaisesRegex(ValueError, "relatorio_invalido"):
                    validate_report([json.dumps(report)], SHA)

    def test_report_rejects_multiple_lines_and_wrong_candidate(self):
        report = json.dumps(make_report(None, incomplete=True))
        with self.assertRaisesRegex(ValueError, "relatorio_invalido"):
            validate_report([report, report], SHA)
        with self.assertRaisesRegex(ValueError, "relatorio_invalido"):
            validate_report([report], "b" * 40)

    def test_whatsapp_database_binding_overrides_sandbox_provider_label(self):
        evidence = integration_evidence(
            {"WHATSAPP_PROVIDER": "sandbox", "WHATSAPP_CREDENTIAL_ENV": "staging"},
            [{"environment_category": "outro_ambiente_conhecido", "status": "ready", "count": 1}],
        )

        self.assertTrue(evidence["whatsapp"]["enabled"])
        self.assertFalse(evidence["whatsapp"]["credential_matches_target"])
        self.assertIsNone(evidence["whatsapp"]["provider_validated_for_target"])

    def test_shared_runtime_bindings_are_compared_without_returning_values(self):
        shared = {
            "APP_ENV": "staging",
            "INTEGRATION_SECRET_ENV": "staging",
            "INTEGRATION_SECRET_ACTIVE_KEY_ID": "key-a",
            "INTEGRATION_SECRET_KEYS": "secret-sentinel",
            "MERCADOPAGO_ALLOW_LIVE_PAYMENTS": "false",
        }
        facial = {
            "FACIAL_PROCESSING_ENABLED": "false",
            "FACIAL_CREDENTIAL_ENV": "staging",
            "FACIAL_AEAD_ACTIVE_KEY_ID": "facial-key-a",
            "FACIAL_AEAD_KEYS_JSON": "facial-secret-sentinel",
            "FACIAL_REFERENCE_ROOT": "/private/path/sentinel",
        }
        api = {**shared, **facial}
        services = {
            "api": {"environment": api},
            "worker": {"environment": dict(shared)},
            **{
                name: {"environment": dict(facial)}
                for name in ("face-search-worker", "face-index-worker", "face-maintenance-worker")
            },
        }
        self.assertEqual(binding_mismatches(services), 0)

        services["worker"]["environment"]["SMTP_PASSWORD"] = "different-secret"
        self.assertEqual(binding_mismatches(services), 1)
        self.assertFalse(live_payment_gate(shared, {**shared, "MERCADOPAGO_ALLOW_LIVE_PAYMENTS": "false"}))
        self.assertTrue(live_payment_gate(shared, {**shared, "MERCADOPAGO_ALLOW_LIVE_PAYMENTS": "true"}))
        self.assertIsNone(live_payment_gate(shared, {}))


if __name__ == "__main__":
    unittest.main()
