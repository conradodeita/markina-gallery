"""Contrato do adaptador por comandos injetados; POSIX precisa executar em Linux."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facial_runtime_restoration import SERVICES, RestorationError
from facial_runtime_restoration_host import (
    ACTIVATION_PROBE,
    CANDIDATE_TMPFS,
    IMAGE_PROBE,
    RestorationHost,
    configuration,
    environment,
)


def container(service, index):
    commands = {
        "api": ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        "worker": ["python", "-m", "app.worker"],
        "face-search-worker": ["python", "-m", "app.facial.search_worker_entrypoint"],
        "face-index-worker": ["python", "-m", "app.facial.index_worker_entrypoint"],
        "face-maintenance-worker": ["python", "-m", "app.facial.maintenance_worker_entrypoint"],
    }
    return {"Id":f"{index:064x}", "Image":"sha256:" + f"{index+10:064x}",
        "Config":{"Env":["APP_ENV=production", "FACIAL_PROCESSING_ENABLED=false", "TOKEN=secret-sentinel"], "Cmd":commands[service], "Entrypoint":None, "Labels":{"com.docker.compose.service":service, "com.docker.compose.project":"markina-gallery", "com.docker.compose.config-hash":"a" * 64}},
        "State":{"Status":"running" if service in {"api", "worker"} else "exited", "Health":{"Status":"healthy"}, "Pid":100+index, "StartedAt":"2026-11-02T12:00:00Z", "ExitCode":0},
        "HostConfig":{"RestartPolicy":{"Name":"unless-stopped"}, "PortBindings":{}},
        "Mounts":[], "NetworkSettings":{"Networks":{"markina-gallery_internal":{}}}}


class HostContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.events = []
        self.containers = {s:container(s,i) for i,s in enumerate(SERVICES,1)}

        def command(args, data, timeout):
            self.events.append((tuple(args), data))
            raise RestorationError("comando_nao_previsto_no_teste")
        self.host = RestorationHost(support_sha="a"*40, root=self.root, state=self.root, command=command)
        self.private_snapshot = self.host._private
        self.host._private = lambda _operation, _receipt: {"containers": self.containers, "models": {}}
        self.host._current = lambda service, **_kwargs: self.containers[service]
        self.host._sql = lambda _query: 0
        self.records = []
        self.host.journal = lambda _operation, value, **_kwargs: self.records.append(copy.deepcopy(value))

    def drain_receipt(self):
        return {
            "inventory":{"services":{s:{"image_id":c["Image"], "container_id":c["Id"]} for s,c in self.containers.items()}},
            "manifest":{"services":{s:{"image_id":"sha256:"+"f"*64} for s in SERVICES}},
        }

    def test_current_requests_full_container_id_before_inspect(self):
        item = self.containers["api"]
        full_id = item["Id"]
        calls = []

        def command(args, _data, _timeout):
            call = tuple(args)
            calls.append(call)
            if call[:2] == ("docker", "ps"):
                self.assertIn("--no-trunc", call)
                return (full_id + "\n").encode()
            if call[:2] == ("docker", "inspect"):
                self.assertEqual(call[2], full_id)
                return json.dumps([item]).encode()
            raise AssertionError(call)

        self.host.command = command
        self.assertEqual(RestorationHost._current(self.host, "api")["Id"], full_id)
        self.assertEqual(calls[0][:3], ("docker", "ps", "-aq"))

    def test_current_selects_journaled_candidate_among_historical_stopped_services(self):
        candidate = copy.deepcopy(self.containers["api"])
        candidate_id = candidate["Id"]
        candidate["State"]["Status"] = "exited"
        historical = copy.deepcopy(candidate)
        historical["Id"] = "f" * 64
        containers = {candidate_id: candidate, historical["Id"]: historical}

        def command(args, _data, _timeout):
            if args[:2] == ("docker", "ps"):
                return (candidate_id + "\n" + historical["Id"] + "\n").encode()
            if args[:2] == ("docker", "inspect"):
                return json.dumps([containers[args[2]]]).encode()
            raise AssertionError(args)

        self.host.command = command
        selected = RestorationHost._current(self.host, "api", expected_id=candidate_id)
        self.assertEqual(selected["Id"], candidate_id)

    def test_current_refuses_an_active_container_other_than_journaled_candidate(self):
        candidate = copy.deepcopy(self.containers["api"])
        candidate["State"]["Status"] = "exited"
        active = copy.deepcopy(candidate)
        active["Id"] = "f" * 64
        active["State"]["Status"] = "running"
        containers = {candidate["Id"]: candidate, active["Id"]: active}

        def command(args, _data, _timeout):
            if args[:2] == ("docker", "ps"):
                return (candidate["Id"] + "\n" + active["Id"] + "\n").encode()
            if args[:2] == ("docker", "inspect"):
                return json.dumps([containers[args[2]]]).encode()
            raise AssertionError(args)

        self.host.command = command
        with self.assertRaisesRegex(RestorationError, "consumidor_ambiguo"):
            RestorationHost._current(self.host, "api", expected_id=candidate["Id"])

    def use_docker_simulator(self, *, failing_exit_service=None, timeout_service=None, post_stop_diff_service=None):
        clock = [0.0]
        self.host.monotonic = lambda: clock[0]
        self.host.sleeper = lambda seconds: clock.__setitem__(0, clock[0] + seconds)

        def command(args, data, timeout):
            self.events.append((tuple(args), data))
            if args[:2] == ("docker", "diff"):
                item = next(c for c in self.containers.values() if c["Id"] == args[2])
                if item["Config"]["Labels"]["com.docker.compose.service"] == post_stop_diff_service and item["State"]["Status"] == "exited":
                    return b"C /tmp/unexpected-change\n"
                return b""
            if args[:2] == ("docker", "update"):
                item = next(c for c in self.containers.values() if c["Id"] == args[-1])
                item["HostConfig"]["RestartPolicy"]["Name"] = args[2].partition("=")[2]
                return b""
            if args[:2] == ("docker", "kill"):
                item = next(c for c in self.containers.values() if c["Id"] == args[-1])
                service = item["Config"]["Labels"]["com.docker.compose.service"]
                if service != timeout_service:
                    item["State"]["Status"] = "exited"
                    item["State"]["ExitCode"] = 143 if service == failing_exit_service else 0
                    item["State"]["Pid"] = 0
                return b""
            if args[:2] == ("docker", "inspect"):
                item = next((c for c in self.containers.values() if c["Id"] == args[2]), None)
                if item is None:
                    raise RestorationError("container_absent")
                return json.dumps([item]).encode()
            if args[:2] == ("docker", "start"):
                item = next(c for c in self.containers.values() if c["Id"] == args[-1])
                item["State"]["Status"] = "running"
                item["State"]["ExitCode"] = 0
                item["State"]["Pid"] = 101
                return args[-1].encode()
            raise AssertionError(args)

        self.host.command = command

    def tearDown(self):
        self.temp.cleanup()

    def notification_runtime(self, *, interrupt_after_create=False, interrupt_after_signal=False, timeout=False, unhealthy=False):
        """Docker sintético, com quiescência/recriação/verificação reais do adaptador."""
        saved = {"containers": copy.deepcopy(self.containers), "models": {}}
        markers = ["WHATSAPP_CREDENTIAL_ENV", "WHATSAPP_BINDING_LEGACY_A_CREDENTIAL_ENV", "WHATSAPP_BINDING_PILOT_B_CREDENTIAL_ENV"]
        saved["containers"]["api"]["Config"]["Env"] += [f"{key}=production" for key in markers]
        saved["containers"]["api"]["Config"]["Env"] += ["WHATSAPP_OTP_ENCRYPTION_KEY=api-key-sentinel", "WHATSAPP_BINDING_LEGACY_A_API_KEY=api-binding-sentinel"]
        saved["containers"]["face-search-worker"]["Config"]["Env"] += [f"{key}=staging" for key in markers]
        saved["containers"]["face-search-worker"]["Config"]["Env"] += ["WHATSAPP_OTP_ENCRYPTION_KEY=search-key-sentinel", "WHATSAPP_BINDING_LEGACY_A_API_KEY=search-binding-sentinel", "MERCADOPAGO_SENTINEL=preserved"]
        receipt = self.drain_receipt()
        for name, baseline in saved["containers"].items():
            saved["models"][name] = {"services": {name: {"image": baseline["Image"]}}}
            current = copy.deepcopy(baseline)
            current["Image"] = receipt["manifest"]["services"][name]["image_id"]
            current["Config"]["Env"] = [f"{key}={value}" for key, value in self.host._target_environment(saved, name, True, align_notifications=False).items()]
            current["HostConfig"].update(ReadonlyRootfs=True, Tmpfs=CANDIDATE_TMPFS)
            current["State"]["Status"] = "running"
            self.containers[name] = current
        self.host._private = lambda _operation, _receipt: saved
        self.host._work("local-test").mkdir(mode=0o700)
        self.host._write = lambda path, value, **_kwargs: path.write_bytes(value)
        self.host._read = lambda path: path.read_bytes()
        self.host._sql = lambda query: ["20261026_0090"] if query == "SELECT json_agg(version_num) FROM alembic_version" else self.fail("a troca parcial não exige inatividade global do banco")
        self.use_docker_simulator(timeout_service="face-search-worker" if timeout else None)
        docker_command = self.host.command
        created = []
        signal_interrupted = []

        def command(args, data, limit):
            if args[:2] == ("docker", "compose"):
                self.events.append((tuple(args), data))
                if "up" in args:
                    self.assertEqual(args[-1], "face-search-worker")
                    self.assertIn("--no-deps", args)
                    self.assertIn("--no-build", args)
                    self.assertNotIn("--volumes", args)
                    path = Path(args[args.index("-f") + 1])
                    model = json.loads(path.read_bytes())["services"]["face-search-worker"]
                    current = self.containers["face-search-worker"]
                    current["Id"] = f"{10000 + len(created):064x}"
                    current["Config"]["Env"] = [f"{key}={value}" for key, value in model["environment"].items()]
                    current["State"].update(Status="running", Pid=100, StartedAt="2026-11-03T14:40:00Z")
                    current["State"]["Health"]["Status"] = "unhealthy" if unhealthy and not created else "healthy"
                    created.append(current["Id"])
                    if interrupt_after_create and len(created) == 1:
                        raise RestorationError("interrupcao_sintetica_apos_recriar")
                return b""
            if args[0] == "curl":
                return b"200"
            if args[:2] == ("docker", "kill") and interrupt_after_signal and not signal_interrupted:
                docker_command(args, data, limit)
                signal_interrupted.append(True)
                raise KeyboardInterrupt
            return docker_command(args, data, limit)

        self.host.command = command
        record = {"phase": "aligning_notifications", "replaced": list(SERVICES), "enabled": True,
                  "active_ids": {name: current["Id"] for name, current in self.containers.items()}}
        return saved, receipt, record, created

    def test_notification_alignment_preserves_keys_otp_payments_and_other_consumers(self):
        saved, receipt, record, created = self.notification_runtime()
        before = copy.deepcopy(self.containers)
        result = self.host.align_notifications("local-test", receipt, record)
        self.assertEqual(result, "complete")
        actual = environment(self.containers["face-search-worker"])
        old = self.host._target_environment(saved, "face-search-worker", True, align_notifications=False)
        changed = {key for key in set(old) | set(actual) if old.get(key) != actual.get(key)}
        self.assertEqual(changed, {"WHATSAPP_CREDENTIAL_ENV", "WHATSAPP_BINDING_LEGACY_A_CREDENTIAL_ENV", "WHATSAPP_BINDING_PILOT_B_CREDENTIAL_ENV"})
        self.assertTrue(all(actual[key] == "production" for key in changed))
        for name in SERVICES:
            if name != "face-search-worker":
                self.assertEqual(self.containers[name], before[name])
        self.assertEqual(len(created), 1)
        self.assertNotIn("intent", record)
        self.assertEqual(self.host.align_notifications("local-test", receipt, record), "complete")
        self.assertEqual(len(created), 1)

    def test_notification_alignment_rollback_restores_only_search_configuration(self):
        _saved, receipt, record, created = self.notification_runtime()
        before = copy.deepcopy(self.containers)
        self.host.align_notifications("local-test", receipt, record)
        self.assertEqual(self.host.align_notifications("local-test", receipt, record, rollback=True), "rolled_back")
        self.assertEqual(configuration(self.containers["face-search-worker"]), configuration(before["face-search-worker"]))
        self.assertEqual(len(created), 2)
        work = self.host._work("local-test")
        self.assertTrue((work / "face-search-worker-enabled-notifications-v1.compose.json").exists())
        self.assertTrue((work / "face-search-worker-enabled.compose.json").exists())

    def test_notification_alignment_retry_recognizes_exact_recreated_consumer(self):
        _saved, receipt, record, created = self.notification_runtime(interrupt_after_create=True)
        with self.assertRaisesRegex(RestorationError, "interrupcao_sintetica"):
            self.host.align_notifications("local-test", receipt, record)
        persisted = self.records[-1]
        self.assertEqual(persisted["intent"], "face-search-worker")
        self.assertEqual(self.host.align_notifications("local-test", receipt, persisted), "complete")
        self.assertEqual(len(created), 1)

    def test_notification_alignment_timeout_resumes_same_consumer_without_recreation(self):
        _saved, receipt, record, created = self.notification_runtime(timeout=True)
        before = copy.deepcopy(self.containers)
        with self.assertRaisesRegex(RestorationError, "timeout_sem_sigkill"):
            self.host.align_notifications("local-test", receipt, record)
        self.assertEqual(created, [])
        self.assertEqual(self.containers, before)
        self.assertFalse(any("SIGKILL" in part for args, _ in self.events for part in args))

    def test_notification_alignment_retry_restores_interrupted_stop_before_replacing(self):
        _saved, receipt, record, created = self.notification_runtime(interrupt_after_signal=True)
        with self.assertRaises(KeyboardInterrupt):
            self.host.align_notifications("local-test", receipt, record)
        self.assertEqual(self.containers["face-search-worker"]["State"]["Status"], "exited")
        persisted = self.records[-1]
        self.assertTrue(persisted["stop_restore"])
        self.assertEqual(self.host.align_notifications("local-test", receipt, persisted), "complete")
        self.assertEqual(len(created), 1)
        self.assertEqual(sum(args[:2] == ("docker", "start") for args, _ in self.events), 1)

    def test_notification_alignment_refuses_unproven_stopped_consumer(self):
        _saved, receipt, record, created = self.notification_runtime()
        self.containers["face-search-worker"]["State"]["Status"] = "exited"
        with self.assertRaisesRegex(RestorationError, "parada_anterior_nao_comprovada"):
            self.host.align_notifications("local-test", receipt, record)
        self.assertEqual(created, [])

    def test_notification_alignment_refuses_credential_or_image_drift_before_stopping(self):
        _saved, receipt, record, created = self.notification_runtime()
        self.containers["face-search-worker"]["Config"]["Env"].append("WHATSAPP_API_KEY=unexpected")
        with self.assertRaisesRegex(RestorationError, "configuracao_candidata_divergente"):
            self.host.align_notifications("local-test", receipt, record)
        self.assertEqual(created, [])
        self.assertFalse(any(args[:2] == ("docker", "kill") for args, _ in self.events))

    def test_notification_alignment_failed_health_keeps_intent_and_allows_rollback(self):
        _saved, receipt, record, created = self.notification_runtime(unhealthy=True)
        with self.assertRaisesRegex(RestorationError, "healthcheck_nao_confirmado"):
            self.host.align_notifications("local-test", receipt, record)
        self.assertEqual(record["intent"], "face-search-worker")
        self.assertEqual(len(created), 1)
        self.assertEqual(self.host.align_notifications("local-test", receipt, record, rollback=True), "rolled_back")
        self.assertEqual(len(created), 2)

    def test_notification_rollback_accepts_recreation_interrupted_before_identity_receipt(self):
        _saved, receipt, record, created = self.notification_runtime(interrupt_after_create=True)
        with self.assertRaisesRegex(RestorationError, "interrupcao_sintetica"):
            self.host.align_notifications("local-test", receipt, record)
        self.assertEqual(self.host.align_notifications("local-test", receipt, self.records[-1], rollback=True), "rolled_back")
        self.assertEqual(len(created), 2)

    def test_notification_alignment_refuses_nonproduction_source_before_stopping(self):
        saved, receipt, record, created = self.notification_runtime()
        saved["containers"]["api"]["Config"]["Env"] = [
            "WHATSAPP_BINDING_PILOT_B_CREDENTIAL_ENV=staging" if value.startswith("WHATSAPP_BINDING_PILOT_B_CREDENTIAL_ENV=") else value
            for value in saved["containers"]["api"]["Config"]["Env"]
        ]
        with self.assertRaisesRegex(RestorationError, "ambiente_do_canal_nao_comprovado"):
            self.host.align_notifications("local-test", receipt, record)
        self.assertEqual(created, [])
        self.assertEqual(self.events, [])

    def test_notification_markers_are_scoped_to_search_worker(self):
        saved, _receipt, _record, _created = self.notification_runtime()
        for name in SERVICES:
            old = self.host._target_environment(saved, name, True, align_notifications=False)
            aligned = self.host._target_environment(saved, name, True)
            if name != "face-search-worker":
                self.assertEqual(aligned, old)

    def test_exact_container_exit_zero_is_the_drain_receipt(self):
        self.use_docker_simulator()
        record = {"phase":"applying_dark", "replaced":[]}
        self.host.quiesce("local-test", self.drain_receipt(), record)
        self.assertEqual([x[0][3] for x in self.events if x[0][:2] == ("docker", "kill")],
                         [self.containers["api"]["Id"], self.containers["worker"]["Id"]])
        self.assertEqual([x["exit_code"] for x in record["drain_receipts"]], [0, 0])
        self.assertEqual([x["service"] for x in record["drain_receipts"]], ["api", "worker"])
        self.assertFalse(any(x[0][:2] == ("docker", "exec") for x in self.events))

    def test_recovery_quiesce_keeps_already_restored_baseline_running(self):
        self.use_docker_simulator()
        record = {
            "phase": "recovering",
            "replaced": ["api"],
            "intent": "api",
            "active_ids": {"api": "e" * 64},
        }

        self.host.quiesce("local-test", self.drain_receipt(), record)

        self.assertEqual(self.containers["api"]["State"]["Status"], "running")
        self.assertFalse(any(event[0][:2] in {("docker", "kill"), ("docker", "update")} for event in self.events))

    def test_nonzero_exit_restores_same_container_without_force_recreate(self):
        self.use_docker_simulator(failing_exit_service="worker")
        receipt = self.drain_receipt()
        worker_id = self.containers["worker"]["Id"]
        with self.assertRaisesRegex(RestorationError, "saida_graciosa_nao_confirmada"):
            self.host.quiesce("local-test", receipt, {"phase":"applying_dark", "replaced":[]})
        self.assertTrue(all(c["State"]["Status"] == "running" for c in self.containers.values() if c["Config"]["Labels"]["com.docker.compose.service"] in {"api", "worker"}))
        self.assertEqual(self.containers["worker"]["Id"], worker_id)
        self.assertFalse(any("force-recreate" in x[0] for x in self.events))
        self.assertTrue(any(x[0][:2] == ("docker", "start") and x[0][-1] == worker_id for x in self.events))

    def test_nonempty_layer_after_stop_restarts_original_before_aborting(self):
        self.use_docker_simulator(post_stop_diff_service="api")
        with self.assertRaisesRegex(RestorationError, "camada_gravavel_nao_preservada"):
            self.host.quiesce("local-test", self.drain_receipt(), {"phase":"applying_dark", "replaced":[]})
        self.assertEqual(self.containers["api"]["State"]["Status"], "running")
        self.assertEqual(self.containers["worker"]["State"]["Status"], "running")
        self.assertFalse(any("force-recreate" in x[0] for x in self.events))

    def test_candidate_compose_definition_is_read_only_with_bounded_tmpfs(self):
        baseline = self.containers["api"]
        models = {"api": {"services": {"api": {"environment": {}, "image": baseline["Image"]}}}}
        self.host._private = lambda _operation, _receipt: {"containers": self.containers, "models": models}
        self.host._write = lambda _path, value, **_kwargs: self.events.append(("compose-bytes", value))
        self.host._refresh_nginx_api_upstream = lambda _saved: None
        candidate = copy.deepcopy(baseline)
        candidate["Id"] = "e" * 64
        candidate["Image"] = "sha256:" + "f" * 64
        candidate["Config"]["Env"] = [f"{key}={value}" for key, value in {
            "APP_ENV": "production", "FACIAL_CREDENTIAL_ENV": "production",
            "FACIAL_PROCESSING_ENABLED": "false", "FACIAL_REQUIRE_EXPLICIT_ROLLOUT": "true",
        }.items()]
        candidate["HostConfig"]["ReadonlyRootfs"] = True
        candidate["HostConfig"]["Tmpfs"] = CANDIDATE_TMPFS
        self.host._current = lambda _service: candidate
        receipt = {"manifest":{"services":{"api":{"image_id":candidate["Image"]}}}}
        self.host.command = lambda args, _data, _timeout: b"ok"
        work = self.host._work("local-test")
        work.mkdir(mode=0o700)
        self.host.replace("local-test", receipt, "api", enabled=False)
        compose_data = next(value for key, value in self.events if key == "compose-bytes")
        target = json.loads(compose_data)["services"]["api"]
        self.assertIs(target["read_only"], True)
        self.assertEqual(target["tmpfs"], [f"{path}:{options}" for path, options in sorted(CANDIDATE_TMPFS.items())])

    def test_recovery_refuses_to_recreate_candidate_with_writable_changes(self):
        candidate = copy.deepcopy(self.containers["api"])
        candidate["Id"] = "e" * 64
        candidate["Image"] = "sha256:" + "f" * 64
        candidate["State"]["Status"] = "exited"
        candidate["HostConfig"]["ReadonlyRootfs"] = True
        candidate["HostConfig"]["Tmpfs"] = CANDIDATE_TMPFS
        self.host._current = lambda _service, **_kwargs: candidate
        self.host.read_journal = lambda _operation: {"active_ids":{"api":candidate["Id"]}}
        self.host._private = lambda _operation, _receipt: {"containers": self.containers, "models":{"api":{"services":{"api":{}}}}}
        self.host._write = lambda *_args, **_kwargs: None

        def command(args, _data, _timeout):
            self.events.append((tuple(args), None))
            if args[:2] == ("docker", "diff"):
                return b"C /unexpected\n"
            return b"ok"

        self.host.command = command
        work = self.host._work("local-test")
        work.mkdir(mode=0o700)
        receipt = {"manifest":{"services":{"api":{"image_id":candidate["Image"]}}}}
        with self.assertRaisesRegex(RestorationError, "candidato_nao_preservavel"):
            self.host.replace("local-test", receipt, "api", enabled=False, previous=True)
        self.assertFalse(any("force-recreate" in x[0] for x in self.events))

    def test_api_replacement_refreshes_upstream_without_replacing_nginx(self):
        nginx = copy.deepcopy(self.containers["api"])
        nginx["Id"] = "b" * 64
        nginx["Image"] = "sha256:" + "c" * 64
        nginx["Config"]["Labels"]["com.docker.compose.service"] = "nginx"
        calls = []
        self.host.inspect = lambda _identity: nginx

        def run(*args, **_kwargs):
            calls.append(args)
            return "200" if args[0] == "curl" else "ok"

        self.host.run = run
        self.host._refresh_nginx_api_upstream({"containers":{"nginx":nginx}})
        self.assertEqual(calls[0], ("docker", "exec", nginx["Id"], "nginx", "-t"))
        self.assertEqual(calls[1], ("docker", "exec", nginx["Id"], "nginx", "-s", "reload"))
        self.assertEqual([call[0] for call in calls[2:]], ["curl", "curl"])
        self.assertTrue(all("restart" not in call for call in calls))

    def test_api_reload_waits_for_transient_upstream_health(self):
        nginx = copy.deepcopy(self.containers["api"])
        nginx["Id"] = "b" * 64
        nginx["Image"] = "sha256:" + "c" * 64
        nginx["Config"]["Labels"]["com.docker.compose.service"] = "nginx"
        clock = [0.0]
        statuses = iter(("502", "502", "200", "200"))
        calls = []
        self.host.inspect = lambda _identity: nginx

        def run(*args, **_kwargs):
            calls.append(args)
            return next(statuses) if args[0] == "curl" else "ok"

        self.host.run = run
        self.host.monotonic = lambda: clock[0]
        self.host.sleeper = lambda seconds: clock.__setitem__(0, clock[0] + seconds)

        self.host._refresh_nginx_api_upstream({"containers":{"nginx":nginx}})

        self.assertEqual(sum(call[0] == "curl" for call in calls), 4)
        self.assertEqual(clock[0], 1.0)

    def test_api_reload_health_retry_is_bounded(self):
        nginx = copy.deepcopy(self.containers["api"])
        nginx["Id"] = "b" * 64
        nginx["Image"] = "sha256:" + "c" * 64
        nginx["Config"]["Labels"]["com.docker.compose.service"] = "nginx"
        calls = []
        clock = [0.0]
        self.host.inspect = lambda _identity: nginx

        def run(*args, **_kwargs):
            calls.append(args)
            return "503" if args[0] == "curl" else "ok"

        self.host.run = run
        self.host.monotonic = lambda: clock[0]
        self.host.sleeper = lambda _seconds: clock.__setitem__(0, 120.0)

        with self.assertRaisesRegex(RestorationError, "nginx_reload_health_falhou"):
            self.host._refresh_nginx_api_upstream({"containers":{"nginx":nginx}})

        self.assertEqual(sum(call[0] == "curl" for call in calls), 4)

    def test_recovery_retry_accepts_only_an_already_restored_baseline(self):
        baseline = copy.deepcopy(self.containers["api"])
        baseline["State"]["Status"] = "running"
        baseline["State"]["Health"] = {"Status": "healthy"}
        baseline["HostConfig"]["RestartPolicy"] = {"Name": "unless-stopped", "MaximumRetryCount": 0}
        calls = []

        def current(_service, *, expected_id=None):
            if expected_id is not None:
                raise RestorationError("id_de_consumidor_registrado_ausente")
            return baseline

        self.host._current = current
        self.host.read_journal = lambda _operation: {
            "active_ids": {"api": "e" * 64},
            "intent": "api",
        }
        self.host._private = lambda _operation, _receipt: {"containers": {"api": baseline}, "models": {}}
        self.host.run = lambda *args, **_kwargs: calls.append(args) or "ok"
        self.host._refresh_nginx_api_upstream = lambda _saved: calls.append(("nginx-refresh",))

        result = self.host.replace("local-test", {}, "api", enabled=False, previous=True)

        self.assertEqual(result, baseline["Id"])
        self.assertIn(("nginx-refresh",), calls)

    def test_recovery_retry_does_not_accept_an_unjournaled_state(self):
        self.host._current = lambda _service, *, expected_id=None: (_ for _ in ()).throw(
            RestorationError("id_de_consumidor_registrado_ausente")
        )
        self.host.read_journal = lambda _operation: {
            "active_ids": {"api": "e" * 64},
            "intent": "worker",
        }
        with self.assertRaisesRegex(RestorationError, "id_de_consumidor_registrado_ausente"):
            self.host.replace("local-test", {}, "api", enabled=False, previous=True)

    def test_timeout_never_escalates_to_sigkill_and_resumes_original(self):
        self.use_docker_simulator(timeout_service="api")
        with self.assertRaisesRegex(RestorationError, "timeout_sem_sigkill"):
            self.host.quiesce("local-test", self.drain_receipt(), {"phase":"applying_dark", "replaced":[]})
        signals = [x[0][2] for x in self.events if x[0][:2] == ("docker", "kill")]
        self.assertEqual(signals, ["--signal=SIGTERM"])
        self.assertEqual(self.containers["api"]["State"]["Status"], "running")

    def test_environment_rejects_duplicates_without_exposing_values(self):
        item = self.containers["api"]
        item["Config"]["Env"].append("TOKEN=other-secret")
        with self.assertRaises(RestorationError) as raised:
            environment(item)
        self.assertNotIn("secret",str(raised.exception))

    def test_mount_order_is_canonical_but_source_and_permissions_are_not_ignored(self):
        item = self.containers["api"]
        item["Mounts"] = [{"Destination":"/b","Source":"/source-b","RW":False},{"Destination":"/a","Source":"/source-a","RW":True}]
        changed = copy.deepcopy(item)
        changed["Mounts"].reverse()
        self.assertEqual(configuration(item),configuration(changed))
        changed["Mounts"][0]["RW"] = False
        self.assertNotEqual(configuration(item),configuration(changed))
        changed["Mounts"][1]["Destination"] = "/a"
        with self.assertRaises(RestorationError):
            configuration(changed)

    def test_empty_dns_representations_match_but_explicit_servers_remain_strict(self):
        baseline = copy.deepcopy(self.containers["api"])
        candidate = copy.deepcopy(baseline)
        baseline["HostConfig"]["Dns"] = []
        candidate["HostConfig"]["Dns"] = None
        self.assertEqual(configuration(baseline), configuration(candidate))

        baseline["HostConfig"]["Dns"] = ["192.0.2.53"]
        candidate["HostConfig"]["Dns"] = ["192.0.2.54"]
        self.assertNotEqual(configuration(baseline), configuration(candidate))

    def test_command_failure_does_not_return_raw_stderr_or_arguments(self):
        def failed(*args):
            raise subprocess.CalledProcessError(1,["secret-sentinel"],stderr=b"secret-sentinel")
        self.host.command = failed
        with self.assertRaises(RestorationError) as raised:
            self.host.run("docker","inspect","secret-sentinel")
        self.assertNotIn("secret-sentinel",str(raised.exception))

    def test_invalid_service_is_rejected_before_private_reads_or_commands(self):
        for service in ("db","api; touch file","nginx"):
            with self.subTest(service=service), self.assertRaises(RestorationError):
                self.host.replace("local-test",{},service,enabled=False)
        self.assertFalse(self.events)

    def test_image_probe_has_no_network_mount_or_pull_and_preserves_errors(self):
        image = "sha256:"+"f"*64
        def command(args, data, timeout):
            self.events.append((tuple(args),data))
            if args[:3] == ("docker","image","inspect"):
                return json.dumps([{"Id":image,"Os":"linux","Architecture":"arm64"}]).encode()
            return b'{}'
        self.host.command = command
        self.host._probe_image(image)
        call = self.events[-1][0]
        self.assertIn("--pull=never",call)
        self.assertEqual(call[call.index("--network")+1],"none")
        self.assertNotIn("-v",call)
        self.assertNotIn("--mount",call)
        self.assertIn("--read-only",call)
        self.assertIn("'app/'+p.relative_to(root).as_posix()",IMAGE_PROBE)
        compile(IMAGE_PROBE,"image-probe","exec")
        compile(ACTIVATION_PROBE,"activation-probe","exec")

    @unittest.skipUnless(os.name == "posix","Validação de filesystem exige Linux/POSIX")
    def test_private_state_rejects_symlink_hardlink_and_partial_temp(self):
        self.root.chmod(0o700)
        path = self.root/"private.json"
        self.host._write(path,b'{"format":1}')
        linked = self.root/"linked.json"
        linked.symlink_to(path)
        with self.assertRaises((RestorationError,OSError)):
            self.host._read(linked)
        linked.unlink()
        os.link(path,linked)
        with self.assertRaises(RestorationError):
            self.host._read(linked)
        linked.unlink()
        path.with_suffix(".json.tmp").write_bytes(b"partial")
        with self.assertRaises((RestorationError,OSError)):
            self.host._write(path,b'{}',create=False)
        self.assertEqual(path.read_bytes(),b'{"format":1}')

    @unittest.skipUnless(os.name == "posix","Validação de filesystem exige Linux/POSIX")
    def test_missing_private_file_has_specific_refusal(self):
        self.root.chmod(0o700)
        with self.assertRaisesRegex(RestorationError, "arquivo_privado_ausente"):
            self.host._read(self.root/"recovery-proof.json")

    @unittest.skipUnless(os.name == "posix","Lock nativo exige Linux/POSIX")
    def test_lock_is_exclusive_and_uses_existing_markina_release_lock(self):
        self.root.chmod(0o700)
        path = self.root/"production-release.lock"
        path.write_bytes(b"")
        path.chmod(0o600)
        with self.host.lock(), self.assertRaises(RestorationError), self.host.lock():
            self.fail("lock duplicado")

    @unittest.skipUnless(os.name == "posix","Lock nativo exige Linux/POSIX")
    def test_oserror_inside_locked_operation_is_not_reported_as_lock_conflict(self):
        self.root.chmod(0o700)
        path = self.root/"production-release.lock"
        path.write_bytes(b"")
        path.chmod(0o600)
        with self.host.lock(), self.assertRaisesRegex(OSError, "operation failure") as raised:
            raise OSError("operation failure")
        self.assertNotIsInstance(raised.exception, RestorationError)

    @unittest.skipUnless(os.name == "posix","Metadados POSIX exigem Linux/POSIX")
    def test_dedicated_state_preserves_shared_directory_and_global_lock(self):
        shared = self.root/"deploy-state"
        shared.mkdir(mode=0o700)
        shared.chmod(0o700)
        lock_path = shared/"production-release.lock"
        lock_path.write_bytes(b"")
        lock_path.chmod(0o600)
        state = shared/"facial-runtime-restoration"
        host = RestorationHost(support_sha="a"*40, root=self.root, state=state,
                               shared_state=shared, command=self.host.command)
        shared_before = shared.stat()
        lock_before = lock_path.stat()
        self.assertFalse(host._ensure_private_state())
        self.assertFalse(state.exists())
        with host.lock():
            self.assertFalse(state.exists())
        host._ensure_private_state(create=True)
        state_after = state.stat()
        self.assertEqual((state_after.st_uid, state_after.st_mode & 0o777),
                         (os.geteuid(), 0o700))
        shared_after = shared.stat()
        lock_after = lock_path.stat()
        self.assertEqual((shared_after.st_uid, shared_after.st_gid, shared_after.st_mode & 0o777),
                         (shared_before.st_uid, shared_before.st_gid, shared_before.st_mode & 0o777))
        self.assertEqual((lock_after.st_uid, lock_after.st_gid, lock_after.st_mode & 0o777, lock_path.read_bytes()),
                         (lock_before.st_uid, lock_before.st_gid, lock_before.st_mode & 0o777, b""))

    @unittest.skipUnless(os.name == "posix","Symlinks POSIX exigem Linux/POSIX")
    def test_dedicated_state_rejects_symlink_without_following_it(self):
        shared = self.root/"deploy-state"
        shared.mkdir(mode=0o700)
        shared.chmod(0o700)
        target = self.root/"outside-state"
        target.mkdir(mode=0o700)
        state = shared/"facial-runtime-restoration"
        state.symlink_to(target, target_is_directory=True)
        host = RestorationHost(support_sha="a"*40, root=self.root, state=state,
                               shared_state=shared, command=self.host.command)
        with self.assertRaisesRegex(RestorationError, "diretorio_inseguro"):
            host._ensure_private_state()

    @unittest.skipUnless(os.name == "posix","Permissões POSIX exigem Linux/POSIX")
    def test_lock_rejects_wrong_mode_without_repair(self):
        shared = self.root/"deploy-state"
        shared.mkdir(mode=0o700)
        shared.chmod(0o700)
        lock_path = shared/"production-release.lock"
        lock_path.write_bytes(b"preserve")
        lock_path.chmod(0o644)
        host = RestorationHost(support_sha="a"*40, root=self.root,
                               state=shared/"facial-runtime-restoration",
                               shared_state=shared, command=self.host.command)
        with self.assertRaisesRegex(RestorationError, "lock_inseguro"), host.lock():
            self.fail("lock inseguro foi aceito")
        self.assertEqual((lock_path.stat().st_mode & 0o777, lock_path.read_bytes()), (0o644, b"preserve"))

    @unittest.skipUnless(os.name == "posix","Permissões POSIX exigem Linux/POSIX")
    def test_candidate_manifest_stays_in_shared_parent_and_is_read_without_relocation(self):
        shared = self.root/"deploy-state"
        shared.mkdir(mode=0o700)
        shared.chmod(0o700)
        state = shared/"facial-runtime-restoration"
        state.mkdir(mode=0o700)
        manifest_path = shared/"facial-runtime-candidates.json"
        manifest = {"format":1,"services":{}}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        manifest_path.chmod(0o600)
        host = RestorationHost(support_sha="a"*40, root=self.root, state=state,
                               shared_state=shared, command=self.host.command)
        self.assertEqual(host.candidate_manifest(), manifest)
        self.assertFalse((state/"facial-runtime-candidates.json").exists())
        manifest_path.unlink()
        manifest_path.symlink_to(state, target_is_directory=True)
        with self.assertRaises(OSError):
            host.candidate_manifest()

    @unittest.skipUnless(os.name == "posix","Permissões POSIX exigem Linux/POSIX")
    def test_pending_markers_are_checked_in_shared_parent_and_new_private_state(self):
        shared = self.root/"deploy-state"
        shared.mkdir(mode=0o700)
        shared.chmod(0o700)
        state = shared/"facial-runtime-restoration"
        host = RestorationHost(support_sha="a"*40, root=self.root, state=state,
                               shared_state=shared, command=self.host.command)
        host._assert_no_pending_operations()
        marker = shared/"orders-in-flight.json"
        marker.write_text("pending", encoding="utf-8")
        with self.assertRaisesRegex(RestorationError, "operacao_concorrente_pendente"):
            host._assert_no_pending_operations()
        marker.unlink()
        host._ensure_private_state(create=True)
        work = state/"facial-restore-current"
        work.mkdir(mode=0o700)
        (work/"in-flight.json").write_text("pending", encoding="utf-8")
        (work/"in-flight.json").chmod(0o600)
        with self.assertRaisesRegex(RestorationError, "restauracao_pendente"):
            host._assert_no_pending_operations()

    @unittest.skipUnless(os.name == "posix","Ownership POSIX exige Linux/POSIX")
    def test_shared_directory_rejects_unexpected_owner(self):
        self.root.chmod(0o700)
        with self.assertRaisesRegex(RestorationError, "diretorio_owner_ou_modo_invalido"):
            self.host._safe_directory(self.root, private=True, owner_uid=os.geteuid()+1)
        with self.assertRaisesRegex(RestorationError, "diretorio_owner_ou_modo_invalido"):
            self.host._safe_directory(self.root, private=True, owner_gid=os.getegid()+1)

    @unittest.skipUnless(os.name == "posix","Lookup de usuários POSIX exige Linux/POSIX")
    def test_fixed_shared_directory_resolves_ubuntu_owner(self):
        host = RestorationHost(support_sha="a"*40, root=self.root,
                               state=Path("/var/lib/markina-gallery/deploy-state/facial-runtime-restoration"),
                               shared_state=Path("/var/lib/markina-gallery/deploy-state"),
                               command=self.host.command)
        with patch("pwd.getpwnam", return_value=SimpleNamespace(pw_uid=4242, pw_gid=4343)) as lookup:
            self.assertEqual(host._shared_state_owner_ids(), (4242, 4343))
        lookup.assert_called_once_with("ubuntu")

    @unittest.skipUnless(os.name == "posix","Identidade POSIX exige Linux/POSIX")
    def test_production_adapter_rejects_non_root_identity(self):
        with patch("facial_runtime_restoration_host.os.geteuid", return_value=1000), \
             patch("facial_runtime_restoration_host.os.getegid", return_value=1000), \
             patch("facial_runtime_restoration_host.socket.gethostname", return_value="clearbudget-vnic"), \
             self.assertRaisesRegex(RestorationError, "destino_nao_autorizado"):
            RestorationHost(support_sha="a"*40,
                            root=Path("/opt/markina-gallery"),
                            state=Path("/var/lib/markina-gallery/deploy-state/facial-runtime-restoration"),
                            shared_state=Path("/var/lib/markina-gallery/deploy-state"))

    @unittest.skipUnless(os.name == "posix","Persistência e autenticação exigem Linux/POSIX")
    def test_private_snapshot_is_encrypted_reopened_and_bound_to_receipt(self):
        self.root.chmod(0o700)
        self.host._raw = self.containers
        self.host._private = self.private_snapshot
        receipt = {"fingerprint":"f"*64, "manifest":{}, "inventory":{"services":{s:{"compose_files":[{"path":"/fixture/compose"}]} for s in SERVICES}}}
        profile_calls = []
        def command(args,data,timeout):
            if args[-2:] == ("--format","json"):
                config_index = args.index("config")
                profile_index = args.index("--profile")
                self.assertEqual(args[profile_index+1], "facial")
                self.assertLess(profile_index, config_index)
                profile_calls.append("model")
                return json.dumps({"services":{s:{"environment":{"TOKEN":"secret-sentinel"}} for s in SERVICES}}).encode()
            if "--hash" in args:
                config_index = args.index("config")
                profile_index = args.index("--profile")
                self.assertEqual(args[profile_index+1], "facial")
                self.assertLess(profile_index, config_index)
                profile_calls.append("hash")
                return (args[-1]+" "+"a"*64).encode()
            raise AssertionError(args)
        self.host.command = command
        self.host.prepare("local-test",receipt)
        self.assertEqual(profile_calls, ["model", "hash"] * len(SERVICES))
        work = self.host._work("local-test")
        for path in work.iterdir():
            self.assertNotIn(b"secret-sentinel",path.read_bytes())
        self.assertEqual(self.host._private("local-test",receipt)["containers"],self.containers)
        changed = copy.deepcopy(receipt)
        changed["fingerprint"] = "e"*64
        with self.assertRaises(RestorationError):
            self.host._private("local-test",changed)

    @unittest.skipUnless(os.name == "posix","Persistência e autenticação exigem Linux/POSIX")
    def test_compose_hash_failure_does_not_reserve_operation_directory(self):
        self.root.chmod(0o700)
        self.host._raw = self.containers
        receipt = {"fingerprint":"f"*64, "manifest":{}, "inventory":{"services":{s:{"compose_files":[{"path":"/fixture/compose"}]} for s in SERVICES}}}
        def command(args,data,timeout):
            if args[-2:] == ("--format","json"):
                return json.dumps({"services":{s:{} for s in SERVICES}}).encode()
            if "--hash" in args:
                config_index = args.index("config")
                profile_index = args.index("--profile")
                self.assertEqual(args[profile_index+1], "facial")
                self.assertLess(profile_index, config_index)
                raise RestorationError("compose_hash_indisponivel")
            raise AssertionError(args)
        self.host.command = command
        with self.assertRaisesRegex(RestorationError, "compose_hash_indisponivel"):
            self.host.prepare("local-test",receipt)
        self.assertFalse(self.host._work("local-test").exists())


if __name__ == "__main__":
    unittest.main()
