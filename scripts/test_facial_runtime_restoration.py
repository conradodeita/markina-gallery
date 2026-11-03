"""Testes do contrato com host sintético; não são prova operacional ou de modelos."""
from __future__ import annotations

import copy
import sys
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facial_runtime_restoration import (
    FACIAL,
    GATES,
    MODEL_MANIFEST_SHA256,
    PROJECT,
    SCHEMA,
    SERVICES,
    Approval,
    RestorationError,
    digest,
    execute,
    fingerprint,
    prepare,
    validate_images,
    validate_inventory,
)


def fixture():
    inventory = {"format": 1, "project": PROJECT, "schema": SCHEMA, "architecture": "arm64",
        "support_sha": "a" * 40, "collected_at": datetime.now(timezone.utc).isoformat(),
        "services": {}}
    for n, service in enumerate((*SERVICES, "web", "nginx", "db", "redis"), 1):
        inventory["services"][service] = {"container_id": f"{n:064x}", "image_id": "sha256:" + f"{n:064x}", "status": "exited" if service in FACIAL else "running", "health": "healthy", "environment": "staging" if service in FACIAL else "production", "facial_enabled": "false", "configuration_digest": digest({"service": service}), "compose_files": [{"path": "/fixture/compose.json", "sha256": "c" * 64}], "ports": {"80/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]} if service == "nginx" else {}}
    manifest = {"format": 1, "support_sha": inventory["support_sha"], "services": {}}
    for n, service in enumerate(SERVICES, 20):
        baseline = {"architecture": "arm64", "python": "3.11.15", "packages": {"cryptography": "46.0.3"}, "modules": {"app/main.py": "1" * 64, "app/facial/config.py": "2" * 64, "app/facial/rollout.py": "3" * 64, "app/facial/face_worker.py": "5" * 64}, "models_verified": False, "model_manifest_sha256": None, "opencv": None}
        runtime = copy.deepcopy(baseline)
        runtime.update(models_verified=True, opencv="4.12.0", numpy="2.2.6", model_manifest_sha256=MODEL_MANIFEST_SHA256)
        runtime["packages"].update({"numpy": "2.2.6", "opencv-python-headless": "4.12.0.88"})
        runtime["modules"]["app/facial/config.py"] = "4" * 64
        manifest["services"][service] = {"baseline_image_id": inventory["services"][service]["image_id"], "image_id": "sha256:" + f"{n:064x}", "baseline_runtime": baseline, "runtime": runtime, "package_changes": {"numpy": "2.2.6", "opencv-python-headless": "4.12.0.88"}, "module_changes": {"app/facial/config.py": "4" * 64}}
    return inventory, manifest


class SyntheticHost:
    """Only an in-memory unit model. No Docker, filesystem, database or network."""
    def __init__(self):
        self.state, self.manifest = fixture()
        self.original = copy.deepcopy(self.state)
        self.events, self.records = [], {}
        self.receipt = None
        self.failure = None
        self.proof = None
        self.payments = {"old": 100}
        self.fail_drain = False
        self.fail_previous = False

    @contextmanager
    def lock(self):
        self.events.append("lock")
        yield

    def inventory(self):
        self.events.append("inventory")
        return copy.deepcopy(self.state)

    def prove_images(self, manifest):
        self.events.append("prove_images")
        return {s:copy.deepcopy(p["runtime"]) for s,p in manifest["services"].items()}

    def prepare(self, operation, receipt):
        self.receipt = copy.deepcopy(receipt)
        self.events.append("prepare")

    def load(self, operation):
        return copy.deepcopy(self.receipt)

    def journal(self, operation, value, *, create=False):
        if create and operation in self.records:
            raise RestorationError("journal_existente")
        self.records[operation] = copy.deepcopy(value)
        self.events.append("journal:" + value["phase"])

    def read_journal(self, operation):
        return copy.deepcopy(self.records[operation])

    def recovery_proof(self, operation, receipt):
        self.events.append("restore_proof")

    def quiesce(self, operation, receipt, record):
        self.events.append("quiesce")
        if self.fail_drain:
            raise RestorationError("drain_nao_comprovado")

    def replace(self, operation, receipt, service, *, enabled, previous=False):
        self.events.append(("restore:" if previous else "replace:") + service)
        item = self.state["services"][service]
        baseline = receipt["inventory"]["services"][service]
        item["image_id"] = (
            baseline["image_id"]
            if previous
            else receipt["manifest"]["services"][service]["image_id"]
        )
        item["facial_enabled"] = (
            baseline["facial_enabled"] if previous else "true" if enabled else "false"
        )
        self.payments["concurrent"] = 500
        if self.failure == service and (not previous or self.fail_previous):
            raise RestorationError("health_failure_synthetic")

    def verify(self, operation, receipt, *, enabled, previous=False):
        self.events.append("verify")
        peers = set(self.original["services"]) - set(SERVICES)
        return {"schema": self.state["schema"], "peers_unchanged": all(self.original["services"][s] == self.state["services"][s] for s in peers)}

    def activation_proof(self, operation, approval):
        self.events.append("db_proof")
        return self.proof or {"scope_digest": approval.scope_digest(), "scope_count": len(approval.allowlist), "stage": approval.stage, "calibration_verified": True, "gates": sorted(GATES)}

    def complete(self, operation, result):
        self.events.append("complete")
        del self.records[operation]

    def functional_proof(self, operation, approval):
        self.events.append("functional_proof")
        return {"fingerprint":approval.fingerprint, "scope_digest":approval.scope_digest(), "request_ready":True, "reference_purged":True, "ui_artifact_sha256":"d" * 64}

    def align_notifications(self, operation, receipt, record, *, rollback=False):
        self.events.append("rollback-notifications" if rollback else "align-notifications")
        if self.failure:
            raise RestorationError("falha_sintetica_no_alinhamento")
        record["notification_alignment"] = {"status": "rolled_back" if rollback else "complete"}
        return record["notification_alignment"]["status"]


class ContractTests(unittest.TestCase):
    def test_notification_phases_keep_fingerprint_enabled_runtime_and_pending_functional_proof(self):
        host, approval = self.ready()
        execute(host, "local-test", "dark", approval)
        execute(host, "local-test", "activate", approval)
        for phase, status in (("align-notifications", "complete"), ("rollback-notifications", "rolled_back")):
            result = execute(host, "local-test", phase, approval)
            self.assertEqual(result["status"], status)
            self.assertTrue(result["enabled"])
            self.assertEqual(host.records["local-test"]["phase"], "runtime_verified")
            self.assertEqual(host.receipt["fingerprint"], approval.fingerprint)
            self.assertIn("local-test", host.records)

    def test_notification_phase_failure_stays_journaled_and_cannot_be_declared_verified(self):
        host, approval = self.ready()
        execute(host, "local-test", "dark", approval)
        execute(host, "local-test", "activate", approval)
        host.failure = True
        with self.assertRaisesRegex(RestorationError, "falha_sintetica_no_alinhamento"):
            execute(host, "local-test", "align-notifications", approval)
        self.assertEqual(host.records["local-test"]["phase"], "aligning_notifications")
        with self.assertRaisesRegex(RestorationError, "alinhamento_de_notificacao_pendente"):
            execute(host, "local-test", "verify", approval)
        host.failure = None
        self.assertEqual(execute(host, "local-test", "rollback-notifications", approval)["status"], "rolled_back")

    def test_notification_phase_rejects_scope_or_disabled_runtime(self):
        host, approval = self.ready()
        execute(host, "local-test", "dark", approval)
        with self.assertRaisesRegex(RestorationError, "runtime_nao_verificado"):
            execute(host, "local-test", "align-notifications", approval)
        execute(host, "local-test", "activate", approval)
        with self.assertRaisesRegex(RestorationError, "escopo_de_verificacao_divergente"):
            execute(host, "local-test", "align-notifications", Approval(approval.fingerprint, ("22345678-1234-4234-8234-123456789abc",)))

    def test_signal_handler_overlay_is_allowed_only_for_facial_worker_candidates(self):
        inventory, manifest = fixture()
        service = FACIAL[0]
        manifest["services"][service]["runtime"]["modules"]["app/facial/face_worker.py"] = "6" * 64
        manifest["services"][service]["module_changes"]["app/facial/face_worker.py"] = "6" * 64
        observations = {name: copy.deepcopy(item["runtime"]) for name, item in manifest["services"].items()}
        validate_images(inventory, manifest, observations)

        service = "api"
        manifest["services"][service]["runtime"]["modules"]["app/facial/face_worker.py"] = "6" * 64
        manifest["services"][service]["module_changes"]["app/facial/face_worker.py"] = "6" * 64
        observations = {name: copy.deepcopy(item["runtime"]) for name, item in manifest["services"].items()}
        with self.assertRaisesRegex(RestorationError, "codigo_fora_da_allowlist"):
            validate_images(inventory, manifest, observations)

    def ready(self):
        host = SyntheticHost()
        result = prepare(host, "local-test", host.manifest)
        return host, Approval(result["fingerprint"], ("12345678-1234-4234-8234-123456789abc",))

    def test_inventory_rejects_schema_ports_and_stale_evidence(self):
        inventory, _ = fixture()
        for field, value in (("schema", "wrong"), ("project", "other"), ("architecture", "amd64"), ("collected_at", (datetime.now(timezone.utc)-timedelta(hours=2)).isoformat())):
            changed = copy.deepcopy(inventory)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(RestorationError):
                validate_inventory(changed)
        inventory["services"]["db"]["ports"] = {"5432/tcp": [{"HostIp":"0.0.0.0", "HostPort":"5432"}]}
        with self.assertRaises(RestorationError):
            validate_inventory(inventory)

    def test_configuration_or_baseline_drift_refuses_before_journal(self):
        host, approval = self.ready()
        host.events.clear()
        host.state["services"]["api"]["configuration_digest"] = "f" * 64
        with self.assertRaises(RestorationError):
            execute(host, "local-test", "dark", approval)
        self.assertFalse(host.records)
        self.assertFalse(any(x.startswith("replace:") for x in host.events))

    def test_candidate_preserves_all_other_code_packages_models_and_python(self):
        inv, manifest = fixture()
        for key, value in (("python", "3.13.1"), ("model_manifest_sha256", "f" * 64), ("models_verified", False), ("architecture", "amd64")):
            observations = {s:copy.deepcopy(p["runtime"]) for s,p in manifest["services"].items()}
            observations["api"][key] = value
            candidate = copy.deepcopy(manifest)
            candidate["services"]["api"]["runtime"] = observations["api"]
            with self.subTest(key=key), self.assertRaises(RestorationError):
                validate_images(inv, candidate, observations)
        candidate = copy.deepcopy(manifest)
        candidate["services"]["api"]["runtime"]["modules"]["app/main.py"] = "f" * 64
        with self.assertRaises(RestorationError):
            validate_images(inv, candidate, {s:p["runtime"] for s,p in candidate["services"].items()})

    def test_candidate_adds_only_the_fixed_manifest_when_baseline_has_none(self):
        inv, manifest = fixture()
        observations = {s:copy.deepcopy(p["runtime"]) for s,p in manifest["services"].items()}
        validate_images(inv, manifest, observations)
        manifest["services"]["api"]["baseline_runtime"]["model_manifest_sha256"] = "f" * 64
        with self.assertRaises(RestorationError):
            validate_images(inv, manifest, observations)
        manifest["services"]["api"]["baseline_runtime"]["model_manifest_sha256"] = ["malformed"]
        with self.assertRaises(RestorationError):
            validate_images(inv, manifest, observations)
        manifest["services"]["api"]["baseline_runtime"]["model_manifest_sha256"] = None
        observations["api"]["model_manifest_sha256"] = "f" * 64
        with self.assertRaises(RestorationError):
            validate_images(inv, manifest, observations)

    def test_dark_replaces_only_api_worker_and_retains_resumable_journal(self):
        host, approval = self.ready()
        result = execute(host, "local-test", "dark", approval)
        self.assertEqual(result["status"], "dark_verified")
        self.assertEqual([x for x in host.events if x.startswith("replace:")], ["replace:api", "replace:worker"])
        self.assertFalse(host.records["local-test"]["enabled"])
        self.assertTrue(all(
            host.state["services"][service]["facial_enabled"] == "false"
            for service in SERVICES
        ))
        self.assertLess(host.events.index("restore_proof"), host.events.index("journal:approved"))

    def test_native_drain_failure_does_not_substitute_a_container(self):
        host, approval = self.ready()
        host.fail_drain = True
        with self.assertRaises(RestorationError):
            execute(host, "local-test", "dark", approval)
        self.assertFalse(any(x.startswith("replace:") for x in host.events))
        self.assertEqual(host.records["local-test"]["phase"], "applying_dark")

    def test_calibration_and_scope_failure_do_not_activate(self):
        for key, value in (("calibration_verified", False), ("scope_count", 0), ("scope_digest", "f" * 64), ("gates", []), ("stage", "general")):
            host, approval = self.ready()
            execute(host, "local-test", "dark", approval)
            host.proof = host.activation_proof("local-test", approval)
            host.proof[key] = value
            host.events.clear()
            with self.subTest(key=key), self.assertRaises(RestorationError):
                execute(host, "local-test", "activate", approval)
            self.assertFalse(any(x.startswith("replace:") for x in host.events))

    def test_activation_health_is_not_functional_completion(self):
        host, approval = self.ready()
        execute(host, "local-test", "dark", approval)
        result = execute(host, "local-test", "activate", approval)
        self.assertEqual(result["status"], "runtime_verified")
        self.assertIn("local-test", host.records)
        self.assertTrue(host.records["local-test"]["enabled"])

    def test_completion_requires_separate_functional_proof_and_fresh_calibration(self):
        host, approval = self.ready()
        execute(host, "local-test", "dark", approval)
        execute(host, "local-test", "activate", approval)
        host.proof = host.activation_proof("local-test", approval)
        host.proof["calibration_verified"] = False
        with self.assertRaises(RestorationError):
            execute(host, "local-test", "verify", approval)
        self.assertIn("local-test", host.records)
        host.proof["calibration_verified"] = True
        result = execute(host, "local-test", "verify", approval)
        self.assertTrue(result["enabled"])
        self.assertNotIn("local-test", host.records)

    def test_failure_records_intent_and_recovery_preserves_concurrent_payments(self):
        host, approval = self.ready()
        host.failure = "worker"
        with self.assertRaises(RestorationError):
            execute(host, "local-test", "dark", approval)
        self.assertEqual(host.records["local-test"]["intent"], "worker")
        execute(host, "local-test", "recover", approval)
        self.assertEqual(host.payments, {"old":100, "concurrent":500})
        self.assertFalse(host.records)
        for service in SERVICES:
            self.assertEqual(host.state["services"][service]["image_id"], host.original["services"][service]["image_id"])

    def test_activation_interruption_at_each_service_is_recoverable(self):
        for failed_service in SERVICES:
            with self.subTest(service=failed_service):
                host, approval = self.ready()
                execute(host, "local-test", "dark", approval)
                host.failure = failed_service
                with self.assertRaisesRegex(RestorationError, "health_failure_synthetic"):
                    execute(host, "local-test", "activate", approval)

                self.assertEqual(host.records["local-test"]["intent"], failed_service)
                host.failure = None
                result = execute(host, "local-test", "recover", approval)

                self.assertFalse(result["enabled"])
                self.assertEqual(host.payments, {"old": 100, "concurrent": 500})
                self.assertEqual(
                    host.state["services"], host.original["services"],
                )
                touched = [
                    event.split(":", 1)[1]
                    for event in host.events
                    if event.startswith(("replace:", "restore:"))
                ]
                self.assertTrue(set(touched) <= set(SERVICES))

    def test_interrupted_recovery_at_each_service_resumes_without_data_or_peer_changes(self):
        for failed_service in reversed(SERVICES):
            with self.subTest(service=failed_service):
                host, approval = self.ready()
                execute(host, "local-test", "dark", approval)
                execute(host, "local-test", "activate", approval)
                host.failure = failed_service
                host.fail_previous = True
                with self.assertRaisesRegex(RestorationError, "health_failure_synthetic"):
                    execute(host, "local-test", "recover", approval)

                self.assertEqual(host.records["local-test"]["phase"], "recovering")
                self.assertEqual(host.records["local-test"]["intent"], failed_service)
                host.failure = None
                result = execute(host, "local-test", "recover", approval)

                self.assertFalse(result["enabled"])
                self.assertEqual(host.payments, {"old": 100, "concurrent": 500})
                self.assertEqual(
                    host.state["services"], host.original["services"],
                )

    def test_fingerprint_covers_configuration_but_ignores_collection_clock(self):
        inv, _ = fixture()
        changed = copy.deepcopy(inv)
        changed["collected_at"] = "different clock"
        self.assertEqual(fingerprint(inv), fingerprint(changed))
        changed["services"]["worker"]["configuration_digest"] = "b" * 64
        self.assertNotEqual(fingerprint(inv), fingerprint(changed))

    def test_changed_receipt_or_unknown_journal_phase_cannot_recover(self):
        host, approval = self.ready()
        host.receipt["manifest"]["support_sha"] = "b" * 40
        with self.assertRaises(RestorationError):
            execute(host, "local-test", "dark", approval)
        host, approval = self.ready()
        execute(host, "local-test", "dark", approval)
        host.records["local-test"]["phase"] = "unrecognized"
        with self.assertRaises(RestorationError):
            execute(host, "local-test", "recover", approval)


if __name__ == "__main__":
    unittest.main()
