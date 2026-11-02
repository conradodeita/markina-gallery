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
        self.host._current = lambda service: self.containers[service]
        self.host._sql = lambda _query: 0
        self.records = []
        self.host.journal = lambda _operation, value, **_kwargs: self.records.append(copy.deepcopy(value))

    def drain_receipt(self):
        return {
            "inventory":{"services":{s:{"image_id":c["Image"], "container_id":c["Id"]} for s,c in self.containers.items()}},
            "manifest":{"services":{s:{"image_id":"sha256:"+"f"*64} for s in SERVICES}},
        }

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

    def test_exact_container_exit_zero_is_the_drain_receipt(self):
        self.use_docker_simulator()
        record = {"phase":"applying_dark", "replaced":[]}
        self.host.quiesce("local-test", self.drain_receipt(), record)
        self.assertEqual([x[0][3] for x in self.events if x[0][:2] == ("docker", "kill")],
                         [self.containers["api"]["Id"], self.containers["worker"]["Id"]])
        self.assertEqual([x["exit_code"] for x in record["drain_receipts"]], [0, 0])
        self.assertEqual([x["service"] for x in record["drain_receipts"]], ["api", "worker"])
        self.assertFalse(any(x[0][:2] == ("docker", "exec") for x in self.events))

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
        self.host._current = lambda _service: candidate
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

    @unittest.skipUnless(os.name == "posix","Lock nativo exige Linux/POSIX")
    def test_lock_is_exclusive_and_uses_existing_markina_release_lock(self):
        self.root.chmod(0o700)
        path = self.root/"production-release.lock"
        path.write_bytes(b"")
        path.chmod(0o600)
        with self.host.lock(), self.assertRaises(RestorationError), self.host.lock():
            self.fail("lock duplicado")

    @unittest.skipUnless(os.name == "posix","Persistência e autenticação exigem Linux/POSIX")
    def test_private_snapshot_is_encrypted_reopened_and_bound_to_receipt(self):
        self.root.chmod(0o700)
        self.host._raw = self.containers
        self.host._private = self.private_snapshot
        receipt = {"fingerprint":"f"*64, "inventory":{"services":{s:{"compose_files":[{"path":"/fixture/compose"}]} for s in SERVICES}}}
        def command(args,data,timeout):
            if args[-2:] == ("--format","json"):
                return json.dumps({"services":{s:{"environment":{"TOKEN":"secret-sentinel"}} for s in SERVICES}}).encode()
            if "--hash" in args:
                return (args[-1]+" "+"a"*64).encode()
            raise AssertionError(args)
        self.host.command = command
        self.host.prepare("local-test",receipt)
        work = self.host._work("local-test")
        for path in work.iterdir():
            self.assertNotIn(b"secret-sentinel",path.read_bytes())
        self.assertEqual(self.host._private("local-test",receipt)["containers"],self.containers)
        changed = copy.deepcopy(receipt)
        changed["fingerprint"] = "e"*64
        with self.assertRaises(RestorationError):
            self.host._private("local-test",changed)


if __name__ == "__main__":
    unittest.main()
