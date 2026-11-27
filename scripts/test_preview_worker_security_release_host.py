from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_worker_security_release_host import (
    HostError,
    PreviewWorkerSecurityHost,
    fingerprint,
)


class PreviewWorkerSecurityHostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.state = self.base / "state"
        (self.root / "docker").mkdir(parents=True)
        self.state.mkdir()
        if os.name == "posix":
            self.state.chmod(0o700)
        self.compose = self.root / "docker" / "docker-compose.yml"
        self.compose.write_text("services: {}\n", encoding="utf-8")
        self.events = []

        def command(args, data, timeout):
            self.events.append((list(args), data, timeout))
            if len(args) >= 3 and args[-2] == "--hash":
                service = args[-1]
                return f"{service} {'a' * 64}".encode()
            return b""

        self.host = PreviewWorkerSecurityHost(
            expected_sha="b" * 40,
            candidate_image_id="sha256:" + "2" * 64,
            callback_policy="provider_retry_proven",
            window_approved=True,
            root=self.root,
            state=self.state,
            command=command,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_compose_invocation_is_scoped_to_active_service_provenance(self):
        self.host.inventory_data = {
            "services": {
                "worker": {
                    "status": "running",
                    "compose_config_hash": "a" * 64,
                    "compose_files": [
                        {"path": "docker/docker-compose.yml", "sha256": "c" * 64}
                    ],
                }
            }
        }
        self.host._assert_compose_runtime_matches(self.host.inventory_data)
        args = self.events[0][0]
        self.assertEqual(
            args[:5],
            [
                "docker",
                "compose",
                "--project-directory",
                str(self.root / "docker"),
                "-p",
            ],
        )
        self.assertIn(str(self.compose), args)
        self.assertEqual(args[-3:], ["config", "--hash", "worker"])
        self.assertIn("markina-gallery", args)

    def test_test_project_scope_accepts_only_isolated_rehearsal_names(self):
        isolated = PreviewWorkerSecurityHost(
            expected_sha="b" * 40,
            candidate_image_id="sha256:" + "2" * 64,
            callback_policy="callback_outage_accepted",
            window_approved=True,
            project="pyp-preview-rehearsal-0123456789",
            expected_compose_version="5.6.1",
            maintenance_url="http://127.0.0.1:18321",
            public_base_url="http://127.0.0.1:18321",
            root=self.root,
            state=self.state,
            command=self.host.command,
        )
        self.assertEqual(isolated.project, "pyp-preview-rehearsal-0123456789")
        with self.assertRaisesRegex(HostError, "projeto_compose_fora_da_allowlist"):
            PreviewWorkerSecurityHost(
                expected_sha="b" * 40,
                candidate_image_id="sha256:" + "2" * 64,
                callback_policy="callback_outage_accepted",
                window_approved=True,
                project="markina-gallery-typo",
                root=self.root,
                state=self.state,
                command=self.host.command,
            )
        with self.assertRaisesRegex(HostError, "smoke_url_protocol_invalid"):
            PreviewWorkerSecurityHost(
                expected_sha="b" * 40,
                candidate_image_id="sha256:" + "2" * 64,
                callback_policy="callback_outage_accepted",
                window_approved=True,
                project="pyp-preview-rehearsal-0123456789",
                maintenance_url="http://127.0.0.1:18321",
                public_base_url="http://external.example",
                root=self.root,
                state=self.state,
                command=self.host.command,
            )

    def test_shared_release_lock_is_nonblocking(self):
        import preview_worker_security_release_host as release_host

        if release_host.fcntl is None:
            self.skipTest("flock is available only on Linux")
        lock_path = self.state / "production-release.lock"
        lock_path.write_text("", encoding="utf-8")
        if os.name == "posix":
            lock_path.chmod(0o600)
        with (
            self.host.lock(),
            self.assertRaisesRegex(HostError, "outro_release_em_andamento"),
            self.host.lock(),
        ):
            self.fail("nested lock unexpectedly acquired")

    def test_profiled_service_is_explicitly_selected_without_starting_services(self):
        self.host.inventory_data = {
            "services": {
                "preview-adjustment-worker": {
                    "compose_files": [{"path": "docker/docker-compose.yml"}]
                }
            }
        }
        args = self.host._compose("preview-adjustment-worker")
        self.assertEqual(args[args.index("--profile") + 1], "*")

    def test_restart_policy_restore_preserves_failure_retry_limit(self):
        self.assertEqual(
            self.host._restart_spec({"name": "on-failure", "maximum_retry_count": 7}),
            "on-failure:7",
        )
        self.assertEqual(
            self.host._restart_spec(
                {"name": "unless-stopped", "maximum_retry_count": 0}
            ),
            "unless-stopped",
        )
        with self.assertRaisesRegex(HostError, "restart_policy_invalida"):
            self.host._restart_spec({"name": "always", "maximum_retry_count": 3})

    def test_root_lock_requires_matching_private_state_owner(self):
        import preview_worker_security_release_host as module

        lock_path = self.state / "production-release.lock"
        lock_path.write_text("")
        real_lstat = Path.lstat
        owner = 1001
        mode = stat.S_IFDIR | 0o700

        def metadata(path):
            if path == lock_path:
                return SimpleNamespace(st_uid=1001, st_mode=stat.S_IFREG | 0o600)
            if path == self.state:
                return SimpleNamespace(st_uid=owner, st_mode=mode)
            return real_lstat(path)

        fake_fcntl = SimpleNamespace(LOCK_EX=2, LOCK_NB=4, flock=Mock())
        with (
            patch.object(module, "fcntl", fake_fcntl),
            patch.object(module.os, "geteuid", return_value=0, create=True),
            patch.object(Path, "lstat", metadata),
        ):
            with self.host.lock():
                pass
            owner = 1002
            with (
                self.assertRaisesRegex(
                    HostError, "lock_compartilhado_owner_divergente"
                ),
                self.host.lock(),
            ):
                self.fail("mismatched owner accepted")
            owner = 1001
            mode = stat.S_IFDIR | 0o770
            with (
                self.assertRaisesRegex(
                    HostError, "lock_compartilhado_owner_divergente"
                ),
                self.host.lock(),
            ):
                self.fail("shared directory accepted")

    def test_resume_command_restores_on_failure_retry_limit(self):
        retry_policy = {"name": "on-failure", "maximum_retry_count": 7}
        image_id = "sha256:" + "3" * 64
        self.host.inventory_data = {
            "services": {
                service: {
                    "container_id": service + "-container",
                    "image_id": image_id,
                    "restart_policy": retry_policy,
                }
                for service in ("api", "worker")
            }
        }
        self.host._container = lambda _service: {
            "Image": image_id,
            "State": {"Status": "exited"},
        }
        self.host._wait_healthy = lambda _ident: None
        self.host.resume_producers()
        updates = [
            args
            for args, _data, _timeout in self.events
            if len(args) >= 3 and args[:2] == ["docker", "update"]
        ]
        self.assertEqual(len(updates), 2)
        self.assertTrue(all("--restart=on-failure:7" in args for args in updates))

    def test_restart_policy_drift_blocks_before_stopping_container(self):
        self.host.inventory_data = {
            "services": {
                "api": {
                    "container_id": "api-container",
                    "image_id": "sha256:" + "3" * 64,
                    "restart_policy": {
                        "name": "on-failure",
                        "maximum_retry_count": 5,
                    },
                }
            }
        }
        current = {
            "Image": "sha256:" + "3" * 64,
            "State": {"Status": "running"},
            "HostConfig": {
                "RestartPolicy": {"Name": "on-failure", "MaximumRetryCount": 1}
            },
        }
        self.host._container = lambda _service: current
        with self.assertRaisesRegex(HostError, "restart_policy_mudou_apos_inventario"):
            self.host._stop("api", "SIGTERM", {0, 143})
        self.assertEqual(self.events, [])

    def test_recovery_accepts_only_the_temporarily_disabled_restart_policy(self):
        self.host.inventory_data = {
            "services": {
                "api": {
                    "restart_policy": {
                        "name": "on-failure",
                        "maximum_retry_count": 5,
                    }
                }
            }
        }
        temporarily_disabled = {
            "HostConfig": {"RestartPolicy": {"Name": "no", "MaximumRetryCount": 0}}
        }
        self.host._assert_restart_policy(
            "api", temporarily_disabled, allow_restart_disabled=True
        )
        with self.assertRaisesRegex(HostError, "restart_policy_mudou_apos_inventario"):
            self.host._assert_restart_policy("api", temporarily_disabled)

    def test_compose_hash_drift_fails_before_any_release_mutation(self):
        self.host.inventory_data = {
            "services": {
                "api": {
                    "status": "running",
                    "compose_config_hash": "a" * 64,
                    "compose_files": [
                        {"path": "docker/docker-compose.yml", "sha256": "c" * 64}
                    ],
                }
            }
        }
        self.host.command = lambda args, data, timeout: b"api wrong-hash"
        with self.assertRaisesRegex(
            HostError, "compose_config_nao_reproduz_runtime_ativo"
        ):
            self.host._assert_compose_runtime_matches(self.host.inventory_data)

    def test_overlay_carries_only_exact_worker_image_without_build(self):
        overlay = self.host._overlay(self.host.candidate_image_id)
        value = json.loads(overlay.read_text(encoding="utf-8"))
        self.assertEqual(
            value,
            {
                "services": {
                    "preview-adjustment-worker": {
                        "image": self.host.candidate_image_id,
                    }
                }
            },
        )

    def test_candidate_and_rollback_images_use_distinct_overlay_files(self):
        previous = "sha256:" + "1" * 64
        candidate_overlay = self.host._overlay(self.host.candidate_image_id)
        previous_overlay = self.host._overlay(previous)
        self.assertNotEqual(candidate_overlay, previous_overlay)
        self.assertEqual(
            json.loads(previous_overlay.read_text(encoding="utf-8")),
            {"services": {"preview-adjustment-worker": {"image": previous}}},
        )

    def test_overlay_rejects_config_hash_change_outside_target(self):
        self.host.inventory_data = {
            "services": {
                "api": {
                    "status": "running",
                    "compose_config_hash": "a" * 64,
                    "compose_files": [
                        {"path": "docker/docker-compose.yml", "sha256": "c" * 64}
                    ],
                }
            }
        }
        overlay = self.host._overlay(self.host.candidate_image_id)
        self.host.command = lambda args, data, timeout: b"api changed"
        with self.assertRaisesRegex(HostError, "overlay_altera_servico_fora_do_escopo"):
            self.host._assert_overlay_scope(overlay)

    def test_candidate_platform_must_match_the_approved_arm64_runtime(self):
        inventory = {
            "candidate_platform": "linux/amd64",
            "pending_markers": [],
            "optional_writers_active": [],
            "preview_queue": {"queued": 0, "processing": 0},
            "services": {},
        }
        self.host._collector = lambda: type(
            "Collector", (), {"collect": lambda *_args, **_kwargs: inventory}
        )()
        with self.assertRaisesRegex(HostError, "arquitetura_candidata_nao_arm64"):
            self.host.preflight()

    def test_rawtherapee_version_probe_accepts_its_documented_exit_two_banner(self):
        self.host.command = lambda args, data, timeout: (
            self.events.append((list(args), data, timeout))
            or b"RawTherapee, version 5.13, command line."
        )

        self.host._verify_rawtherapee_version("worker-container")

        args = self.events[-1][0]
        self.assertEqual(args[:5], ["docker", "exec", "worker-container", "sh", "-c"])
        self.assertIn('case "$status" in 0|2', args[-1])

    def test_rawtherapee_version_probe_rejects_an_unexpected_version(self):
        self.host.command = lambda _args, _data, _timeout: (
            b"RawTherapee, version 5.12, command line."
        )

        with self.assertRaisesRegex(HostError, "rawtherapee_runtime_divergente"):
            self.host._verify_rawtherapee_version("worker-container")

    def test_worker_replacement_is_the_only_compose_up_operation(self):
        self.host.inventory_data = {
            "services": {
                "api": {
                    "status": "running",
                    "compose_config_hash": "a" * 64,
                    "compose_files": [
                        {"path": "docker/docker-compose.yml", "sha256": "c" * 64}
                    ],
                },
                "preview-adjustment-worker": {
                    "status": "running",
                    "compose_config_hash": "a" * 64,
                    "compose_files": [
                        {"path": "docker/docker-compose.yml", "sha256": "c" * 64}
                    ],
                },
            }
        }
        self.events.clear()
        self.host._up_worker(self.host.candidate_image_id)
        up_calls = [args for args, _data, _timeout in self.events if "up" in args]
        self.assertEqual(len(up_calls), 1)
        self.assertEqual(
            up_calls[0][-7:],
            [
                "up",
                "-d",
                "--no-deps",
                "--no-build",
                "--pull",
                "never",
                "preview-adjustment-worker",
            ],
        )
        self.assertFalse(
            any(
                "migrate" in args or "down" in args
                for args, _data, _timeout in self.events
            )
        )

    def test_maintenance_config_keeps_only_health_routes_open(self):
        server = "server { listen 80; location / { proxy_pass http://web; } }"
        config = self.host._maintenance_config(server).decode()
        self.assertIn("user nginx;", config)
        self.assertIn("^/(healthz|api/health)$", config)
        self.assertIn("return 503", config)
        with self.assertRaisesRegex(HostError, "nginx_server_config_ambiguo"):
            self.host._maintenance_config("server {} server {}")

    def test_maintenance_barrier_waits_for_http_503_after_reload(self):
        statuses = iter((b"200", b"503"))
        self.host.command = lambda _args, _data, _timeout: next(statuses)
        sleeps = []
        self.host.sleeper = sleeps.append

        self.host._confirm_maintenance_barrier()

        self.assertTrue(self.host.barrier_active)
        self.assertEqual(sleeps, [0.25])

    def test_maintenance_barrier_timeout_does_not_mark_barrier_active(self):
        now = [0.0]
        self.host.monotonic = lambda: now[0]
        self.host.sleeper = lambda duration: now.__setitem__(0, now[0] + duration)
        self.host.command = lambda _args, _data, _timeout: b"200"

        with self.assertRaisesRegex(HostError, "barreira_de_ingress_nao_confirmada"):
            self.host._confirm_maintenance_barrier()

        self.assertFalse(self.host.barrier_active)

    def test_recovery_runtime_verification_expects_previous_image(self):
        previous = "sha256:" + "1" * 64
        candidate = self.host.candidate_image_id
        services = {}
        for name in ("api", "web", "worker", "db", "redis", "nginx"):
            services[name] = {
                "status": "running",
                "health": "healthy",
                "restart_policy": {"name": "unless-stopped"},
                "compose_config_hash": "a" * 64,
                "container_id": name,
                "image_id": "sha256:" + "3" * 64,
            }
        services["preview-adjustment-worker"] = {
            "status": "running",
            "health": "healthy",
            "restart_policy": {"name": "unless-stopped"},
            "compose_config_hash": "a" * 64,
            "compose_files": [
                {"path": "docker/docker-compose.yml", "sha256": "c" * 64}
            ],
            "container_id": "preview",
            "image_id": previous,
        }
        current = {
            "services": services,
            "database_revision": "20261030_0001",
            "nginx_config_sha256": "b" * 64,
            "nginx_site_sha256": "c" * 64,
        }
        self.host.inventory_data = {
            **current,
            "services": {name: {**service} for name, service in services.items()},
            "preview_worker_previous_image_id": previous,
        }
        self.host._collector = lambda: type(
            "Collector", (), {"collect": lambda *_args, **_kwargs: current}
        )()

        def command(args, data, timeout):
            if "--hash" in args and args[-1] == "preview-adjustment-worker":
                return f"preview-adjustment-worker {'a' * 64}".encode()
            return b"200"

        self.host.command = command
        self.host.verify_restored_runtime(previous)
        with self.assertRaisesRegex(HostError, "worker_esperado_nao_confirmado"):
            self.host.verify_restored_runtime(candidate)

    def test_recovery_recreated_worker_must_match_rollback_overlay_hash(self):
        previous = "sha256:" + "1" * 64
        services = {
            name: {
                "status": "running",
                "health": "healthy",
                "restart_policy": {"name": "unless-stopped"},
                "compose_config_hash": "a" * 64,
                "container_id": name,
                "image_id": "sha256:" + "3" * 64,
            }
            for name in ("api", "web", "worker", "db", "redis", "nginx")
        }
        services["preview-adjustment-worker"] = {
            "status": "running",
            "health": "healthy",
            "restart_policy": {"name": "unless-stopped"},
            "compose_config_hash": "d" * 64,
            "compose_files": [
                {"path": "docker/docker-compose.yml", "sha256": "c" * 64}
            ],
            "container_id": "recreated-preview",
            "image_id": previous,
        }
        current = {
            "services": services,
            "database_revision": "20261030_0001",
            "nginx_config_sha256": "b" * 64,
            "nginx_site_sha256": "c" * 64,
        }
        self.host.inventory_data = {
            **current,
            "services": {
                name: {**item, "container_id": "original-preview"}
                if name == "preview-adjustment-worker"
                else {**item}
                for name, item in services.items()
            },
            "preview_worker_previous_image_id": previous,
        }
        self.host._collector = lambda: type(
            "Collector", (), {"collect": lambda *_args, **_kwargs: current}
        )()

        def command(args, data, timeout):
            if "--hash" in args and args[-1] == "preview-adjustment-worker":
                return f"preview-adjustment-worker {'d' * 64}".encode()
            return b"200"

        self.host.command = command
        self.host.verify_restored_runtime(previous)

    def test_recovery_receipt_is_idempotent_but_rejects_divergence(self):
        self.host.fingerprint = "f" * 64
        self.host.expected_sha = "b" * 40
        self.host.inventory_data = {
            "preview_worker_previous_image_id": "sha256:" + "1" * 64
        }
        self.host.write_recovery_receipt("candidate_verifying")
        expected = self.host._receipt_path("recovery").read_bytes()
        self.host.write_recovery_receipt("candidate_verifying")
        self.assertEqual(self.host._receipt_path("recovery").read_bytes(), expected)
        self.host._receipt_path("recovery").write_text("different", encoding="utf-8")
        with self.assertRaisesRegex(HostError, "recibo_preexistente_divergente"):
            self.host.write_recovery_receipt("candidate_verifying")

    def test_recover_inflight_resumes_only_from_a_consistent_journal(self):
        previous = "sha256:" + "1" * 64
        inventory = {
            "expected_sha": "b" * 40,
            "candidate_image_id": self.host.candidate_image_id,
            "preview_worker_previous_image_id": previous,
            "database_revision": "20261030_0001",
        }
        self.host.expected_sha = inventory["expected_sha"]
        self.host.callback_policy = "provider_retry_proven"
        self.host.window_approved = True
        self.host.inventory_data = inventory
        self.host.fingerprint = fingerprint(
            {
                "inventory": inventory,
                "callback_policy": self.host.callback_policy,
                "window_open": True,
            }
        )
        self.host.journal("candidate_verifying")
        recovered = []
        self.host.recover = lambda phase, image: recovered.append((phase, image))
        self.host.recover_inflight()
        self.assertEqual(recovered, [("candidate_verifying", previous)])
        self.assertFalse(self.host.journal_store.path.exists())
        self.assertTrue(self.host._receipt_path("recovery").is_file())

    def test_recover_inflight_rejects_journal_fingerprint_drift(self):
        previous = "sha256:" + "1" * 64
        inventory = {
            "expected_sha": "b" * 40,
            "candidate_image_id": self.host.candidate_image_id,
            "preview_worker_previous_image_id": previous,
        }
        self.host.expected_sha = inventory["expected_sha"]
        self.host.callback_policy = "provider_retry_proven"
        self.host.window_approved = True
        self.host.inventory_data = inventory
        self.host.fingerprint = "f" * 64
        self.host.journal("candidate_verifying")
        with self.assertRaisesRegex(HostError, "journal_inflight_invalido"):
            self.host.recover_inflight()


if __name__ == "__main__":
    unittest.main()
