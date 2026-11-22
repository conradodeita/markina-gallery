"""Contracts for preparation, fail-closed dispatch and simulated recovery."""
import copy
import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess
import tarfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import build_python_security_candidates as builder
from scripts.python_security_release import (
    ORDER,
    PINS,
    Blocked,
    main,
    plan,
    simulate,
    validate_candidate,
)

SHA = "a" * 40
OLD = "sha256:" + "1" * 64
NEW = "sha256:" + "2" * 64
NOW = datetime(2026, 10, 20, 19, tzinfo=timezone.utc)


def inventory():
    item = {"status": "running", "health": "healthy", "image_id": OLD,
            "image": {"architecture": "arm64"}, "packages": dict(PINS, aiohttp="3.14.3")}
    return {"schema_version": 1, "project": "markina-gallery", "host_architecture": "aarch64",
            "collected_at": NOW.isoformat(), "checkout_sha": SHA,
            "services": {s: copy.deepcopy(item) for s in (*ORDER, "web", "db", "redis", "nginx")}}


def state():
    item = {"image": OLD, "running": True, "active_tasks": 0,
            "drain_acknowledged": True, "admission_fenced": True}
    return {"simulation": True, "sha": SHA, "fingerprint": "synthetic-only",
            "data": {"legitimate_new_order": "preserve", "job_payloads": "never_read"},
            "services": {s: copy.deepcopy(item) for s in (*ORDER, "web", "db", "redis", "nginx")}}


def ops(*services):
    return [{"service": s, "previous": OLD, "candidate": NEW} for s in services]


class SimulatedRollout(unittest.TestCase):
    def run_plan(self, value, operations, **kwargs):
        return simulate(value, operations, SHA, "synthetic-only", **kwargs)

    def test_single_consumer(self):
        value = state()
        result = self.run_plan(value, ops("api"))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["state"]["services"]["api"]["image"], NEW)
        self.assertEqual(value["services"]["api"]["image"], OLD)
        self.assertIsNone(result["operational_approval_code"])

    def test_sequential_consumers(self):
        result = self.run_plan(state(), ops("api", "worker", "face-index-worker"))
        self.assertEqual(result["events"], [action + ":" + s for s in ("api", "worker", "face-index-worker") for action in ("preserve", "replace", "healthy")])

    def test_active_worker_blocks_before_any_mutation(self):
        value = state()
        value["services"]["worker"]["active_tasks"] = 1
        previous = copy.deepcopy(value)
        with self.assertRaisesRegex(Blocked, "active task"):
            self.run_plan(value, ops("api", "worker"))
        self.assertEqual(value, previous)

    def test_no_drain_ack_blocks_even_empty_queue(self):
        value = state()
        value["services"]["worker"]["drain_acknowledged"] = False
        with self.assertRaisesRegex(Blocked, "cooperative"):
            self.run_plan(value, ops("worker"))

    def test_no_admission_barrier_blocks(self):
        value = state()
        value["services"]["worker"]["admission_fenced"] = False
        with self.assertRaisesRegex(Blocked, "fenced"):
            self.run_plan(value, ops("worker"))

    def test_health_failure_restores_same_consumer(self):
        value = state()
        result = self.run_plan(value, ops("api"), fail_health="api")
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["state"], value)
        self.assertEqual(result["events"][-1], "restore:api")

    def test_intermediate_failure_restores_reverse_order(self):
        value = state()
        result = self.run_plan(value, ops("api", "worker", "face-index-worker"), fail_health="worker")
        self.assertEqual(result["events"][-2:], ["restore:worker", "restore:api"])
        self.assertNotIn("replace:face-index-worker", result["events"])
        self.assertEqual(result["state"], value)

    def test_sha_image_and_fingerprint_divergence(self):
        for key in ("sha", "fingerprint", "image"):
            value = state()
            if key == "image":
                value["services"]["api"]["image"] = NEW
            else:
                value[key] = "b" * 40
            with self.subTest(key=key), self.assertRaises(Blocked):
                self.run_plan(value, ops("api"))

    def test_optional_inactive_is_not_started(self):
        value = state()
        value["services"]["preview-adjustment-worker"]["running"] = False
        result = self.run_plan(value, ops("api", "preview-adjustment-worker"))
        self.assertEqual(result["events"], ["preserve:api", "replace:api", "healthy:api"])
        self.assertEqual(result["state"]["services"]["preview-adjustment-worker"], value["services"]["preview-adjustment-worker"])

    def test_no_duplicate_or_foreign_service(self):
        for services in (("api", "api"), ("web",), ("db",), ("nginx",), ("foreign-project",)):
            with self.subTest(services=services), self.assertRaises(Blocked):
                self.run_plan(state(), ops(*services))

    def test_data_and_non_python_preserved(self):
        value = state()
        result = self.run_plan(value, ops(*ORDER))
        self.assertEqual(result["state"]["data"], value["data"])
        for s in ("web", "db", "redis", "nginx"):
            self.assertEqual(result["state"]["services"][s], value["services"][s])

    def test_rollback_preserves_legitimate_data_created_during_rollout(self):
        result = self.run_plan(state(), ops("api", "worker"), fail_health="worker",
                               concurrent_data={"new_legitimate_order": "keep"})
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["state"]["data"]["new_legitimate_order"], "keep")

    def test_simulation_rejects_real_inventory(self):
        with self.assertRaisesRegex(Blocked, "synthetic"):
            self.run_plan(inventory(), [])


class CandidatePolicy(unittest.TestCase):
    def setUp(self):
        self.baseline = {"image_id": OLD, "python": "3.13.16", "layers": ["base", "models", "code"],
                         "packages": dict(PINS, aiohttp="3.14.3", torch="2.14.1", pip="25.2")}
        self.candidate = {"image_id": NEW, "python": "3.13.16", "architecture": "arm64", "pip_check": 0,
                          "layers": self.baseline["layers"] + ["four-wheels", "approved-manifest"],
                          "embedded_pins": dict(PINS),
                          "packages": dict(self.baseline["packages"], **PINS)}

    def test_only_four_changes_pass(self):
        self.assertTrue(validate_candidate(self.baseline, self.candidate))

    def test_unrelated_upgrade_missing_or_added_package_block(self):
        for packages in (dict(self.candidate["packages"], torch="3.0"), dict(self.candidate["packages"], unrelated="1"), PINS):
            with self.subTest(packages=packages), self.assertRaisesRegex(Blocked, "distribution"):
                validate_candidate(self.baseline, dict(self.candidate, packages=packages))

    def test_architecture_python_models_and_pip_check_gates(self):
        for key, value in (("architecture", "amd64"), ("python", "3.14.0"), ("layers", ["new-models", "four-wheels"]), ("pip_check", 1)):
            with self.subTest(key=key), self.assertRaises(Blocked):
                validate_candidate(self.baseline, dict(self.candidate, **{key: value}))

    def test_wrong_fixed_package_blocked(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["packages"]["multidict"] = "7.0.0"
        with self.assertRaises(Blocked):
            validate_candidate(self.baseline, candidate)

    def test_old_embedded_manifest_rejected_even_if_installed_versions_fixed(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["embedded_pins"]["aiohttp"] = "3.14.3"
        with self.assertRaisesRegex(Blocked, "embedded requirements"):
            validate_candidate(self.baseline, candidate)


class RealPreparation(unittest.TestCase):
    def test_all_active_need_update_and_plan_never_authorizes(self):
        result = plan(inventory(), SHA, {}, NOW)
        self.assertEqual(result["affected_order"], list(ORDER))
        self.assertFalse(result["production_ready"])
        self.assertIsNone(result["operational_approval_code"])
        self.assertIn("web", result["protected_services"])

    def test_optional_missing_not_included(self):
        value = inventory()
        del value["services"]["preview-adjustment-worker"]
        result = plan(value, SHA, {}, NOW)
        self.assertIn("preview-adjustment-worker", result["inactive_optional"])

    def test_corrected_consumer_not_recreated(self):
        value = inventory()
        value["services"]["api"]["packages"] = dict(PINS)
        self.assertNotIn("api", plan(value, SHA, {}, NOW)["affected_order"])

    def test_inventory_freshness_health_architecture_required(self):
        for variant in ("stale", "unhealthy", "arch", "missing"):
            value = inventory()
            if variant == "stale":
                value["collected_at"] = "2026-10-19T19:00:00+00:00"
            elif variant == "unhealthy":
                value["services"]["worker"]["health"] = "unhealthy"
            elif variant == "arch":
                value["host_architecture"] = "amd64"
            else:
                del value["services"]["api"]
            with self.subTest(variant=variant), self.assertRaises(Blocked):
                plan(value, SHA, {}, NOW)

    def test_operational_modes_never_read_files_or_execute_commands(self):
        for mode in ("release", "rollback", "recover", "rollback-inventory", "recover-inventory"):
            with self.subTest(mode=mode), patch("subprocess.check_output") as command, patch.object(Path, "read_text") as read, patch("sys.stderr", new=io.StringIO()):
                self.assertEqual(main(["--mode", mode, "--sha", SHA]), 1)
                command.assert_not_called()
                read.assert_not_called()

    def test_planning_fingerprint_sensitive_to_candidate_and_runtime(self):
        first = plan(inventory(), SHA, {}, NOW)
        second = plan(inventory(), SHA, {"api": {"image_id": NEW}}, NOW)
        self.assertNotEqual(first["planning_fingerprint"], second["planning_fingerprint"])

    def test_legacy_entry_dispatch_precedes_legacy_parser(self):
        source = Path(__file__).with_name("deploy-prod-app-services.sh").read_text()
        body = source.split("main() {", 1)[1]
        self.assertLess(body.index("python_security_preparation"), body.index("parse_arguments"))
        self.assertIn("return", body.split("parse_arguments")[0])

    def test_shell_dispatch_never_enters_legacy_parser(self):
        bash = str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe") if os.name == "nt" else shutil.which("bash")
        self.assertTrue(bash)
        script = Path(__file__).with_name("deploy-prod-app-services.sh").resolve().as_posix()
        command = ("source " + shlex.quote(script) + "; "
                   "python_security_preparation() { printf python-scope; }; "
                   "parse_arguments() { printf unsafe-legacy >&2; return 9; }; "
                   "main --scope python-security --mode release --sha " + SHA)
        result = subprocess.run([bash, "-c", command], capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "python-scope")
        self.assertNotIn("unsafe-legacy", result.stderr)


class ImportedIdentity(unittest.TestCase):
    def test_remote_daemon_is_rejected(self):
        with patch.object(builder, "run", return_value="ssh://remote"), self.assertRaisesRegex(Blocked, "local Docker"):
            builder.ensure_local_daemon()

    def test_containerd_manifest_requires_exact_opaque_config_digest(self):
        opaque = b'synthetic-config-not-production'
        config_hash = hashlib.sha256(opaque).hexdigest()
        baseline = {"image_id": "sha256:" + config_hash, "layers": ["synthetic-layer"]}
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            for name, content in (("blobs/sha256/" + config_hash, opaque),
                                  ("manifest.json", json.dumps([{"Config": "blobs/sha256/" + config_hash}]).encode())):
                member = tarfile.TarInfo(name)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        stream.seek(0)
        process = SimpleNamespace(stdout=stream, wait=lambda: 0)
        with patch.object(builder, "run", side_effect=[NEW, '["synthetic-layer"]']) as run, patch.object(builder.subprocess, "Popen", return_value=process):
            self.assertEqual(builder.imported_baseline(baseline), NEW)
            self.assertIn("--all", run.call_args_list[0].args)

    def test_matching_layers_without_exact_config_are_rejected(self):
        baseline = {"image_id": OLD, "layers": ["synthetic-layer"]}
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            member = tarfile.TarInfo("manifest.json")
            content = b'[{"Config":"missing"}]'
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        stream.seek(0)
        process = SimpleNamespace(stdout=stream, wait=lambda: 0)
        with patch.object(builder, "run", side_effect=[NEW, '["synthetic-layer"]']), patch.object(builder.subprocess, "Popen", return_value=process), self.assertRaisesRegex(Blocked, "exact baseline"):
            builder.imported_baseline(baseline)


if __name__ == "__main__":
    unittest.main()
