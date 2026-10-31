from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_worker_security_inventory import (  # noqa: I001
    InventoryError,
    PreviewWorkerInventory,
)


EXPECTED_SHA = "a" * 40
IMAGE_PREVIOUS = "sha256:" + "1" * 64
IMAGE_CANDIDATE = "sha256:" + "2" * 64
SERVICE_NAMES = [
    "api",
    "web",
    "worker",
    "db",
    "redis",
    "nginx",
    "preview-adjustment-worker",
]


class InventoryFixture:
    def __init__(self, root: Path, state: Path):
        self.root = root
        self.state = state
        self.compose_path = root / "docker" / "docker-compose.yml"
        self.compose_path.parent.mkdir(parents=True)
        self.compose_path.write_text("services: {}\n", encoding="utf-8")
        state.mkdir(parents=True)
        self.containers = {}
        self.images = {
            IMAGE_PREVIOUS: {
                "Id": IMAGE_PREVIOUS,
                "Os": "linux",
                "Architecture": "arm64",
            },
            IMAGE_CANDIDATE: {
                "Id": IMAGE_CANDIDATE,
                "Os": "linux",
                "Architecture": "arm64",
            },
        }
        for index, name in enumerate(SERVICE_NAMES, start=1):
            ident = f"{index:064x}"
            image = (
                IMAGE_PREVIOUS
                if name == "preview-adjustment-worker"
                else f"sha256:{index + 10:064x}"
            )
            if image not in self.images:
                self.images[image] = {
                    "Id": image,
                    "Os": "linux",
                    "Architecture": "arm64",
                }
            self.containers[ident] = {
                "Id": ident,
                "Image": image,
                "Config": {
                    "Labels": {
                        "com.docker.compose.project": "markina-gallery",
                        "com.docker.compose.service": name,
                        "com.docker.compose.config-hash": f"{index:064x}",
                        "com.docker.compose.project.config_files": str(
                            self.compose_path
                        ),
                    }
                },
                "State": {
                    "Status": "running",
                    "StartedAt": "2026-10-01T00:00:00Z",
                    "Health": {"Status": "healthy"},
                },
                "HostConfig": {
                    "RestartPolicy": {"Name": "unless-stopped", "MaximumRetryCount": 0}
                },
            }
        self.output_revision = "20261026_0090|0|0"

    def runner(self, args, timeout):
        del timeout
        args = list(args)
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return EXPECTED_SHA.encode()
        if args[:3] == ["git", "status", "--porcelain"]:
            return b""
        if args[:2] == ["docker", "ps"]:
            return "\n".join(self.containers).encode()
        if args[:4] == ["docker", "compose", "version", "--short"]:
            return b"v2.35.1"
        if args[:2] == ["docker", "inspect"]:
            return json.dumps([self.containers[args[2]]]).encode()
        if args[:3] == ["docker", "image", "inspect"]:
            return json.dumps([self.images[args[3]]]).encode()
        if args[:2] == ["docker", "exec"]:
            if args[-2:] == ["cat", "/etc/nginx/nginx.conf"]:
                return b"worker_processes auto; http { include conf.d/*.conf; }\n"
            if args[-2:] == ["cat", "/etc/nginx/conf.d/default.conf"]:
                return b"server { listen 80; location /healthz { return 200; } }\n"
            return self.output_revision.encode()
        raise AssertionError(f"unexpected read-only command: {args}")


class PreviewWorkerInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.fixture = InventoryFixture(base / "repo", base / "state")
        self.collector = PreviewWorkerInventory(
            root=self.fixture.root,
            state=self.fixture.state,
            runner=self.fixture.runner,
        )

    def tearDown(self):
        self.temp.cleanup()

    def collect(self):
        return self.collector.collect(
            expected_sha=EXPECTED_SHA, candidate_image_id=IMAGE_CANDIDATE
        )

    def test_collects_sanitized_runtime_queue_and_compose_provenance(self):
        result = self.collect()
        self.assertEqual(result["database_revision"], "20261026_0090")
        self.assertEqual(result["preview_queue"], {"queued": 0, "processing": 0})
        self.assertEqual(result["preview_worker_previous_image_id"], IMAGE_PREVIOUS)
        self.assertEqual(
            result["services"]["preview-adjustment-worker"]["compose_files"][0]["path"],
            "docker/docker-compose.yml",
        )
        self.assertNotIn("environment", result["services"]["api"])
        self.assertEqual(
            result["nginx_config_sha256"],
            hashlib.sha256(
                b"worker_processes auto; http { include conf.d/*.conf; }\n"
            ).hexdigest(),
        )
        self.assertEqual(
            result["nginx_site_sha256"],
            hashlib.sha256(
                b"server { listen 80; location /healthz { return 200; } }\n"
            ).hexdigest(),
        )

    def test_dirty_checkout_blocks_inventory(self):
        base_runner = self.fixture.runner

        def dirty_runner(args, timeout):
            if list(args)[:3] == ["git", "status", "--porcelain"]:
                return b" M local.env"
            return base_runner(args, timeout)

        self.collector.runner = dirty_runner
        with self.assertRaisesRegex(InventoryError, "checkout_diverge_ou_sujo"):
            self.collect()

    def test_candidate_must_match_worker_architecture(self):
        self.fixture.images[IMAGE_CANDIDATE]["Architecture"] = "amd64"
        with self.assertRaisesRegex(
            InventoryError, "arquitetura_candidata_divergente_do_worker"
        ):
            self.collect()

    def test_unhealthy_required_service_blocks_inventory(self):
        api = next(
            item
            for item in self.fixture.containers.values()
            if item["Config"]["Labels"]["com.docker.compose.service"] == "api"
        )
        api["State"]["Health"]["Status"] = "unhealthy"
        with self.assertRaisesRegex(InventoryError, "servico_necessario_nao_saudavel"):
            self.collect()

    def test_active_optional_writer_is_reported_for_fail_closed_gate(self):
        ident = "f" * 64
        self.fixture.containers[ident] = {
            "Id": ident,
            "Image": IMAGE_PREVIOUS,
            "Config": {
                "Labels": {
                    "com.docker.compose.project": "markina-gallery",
                    "com.docker.compose.service": "face-index-worker",
                    "com.docker.compose.config-hash": "f" * 64,
                    "com.docker.compose.project.config_files": str(
                        self.fixture.compose_path
                    ),
                }
            },
            "State": {
                "Status": "running",
                "StartedAt": "2026-10-01T00:00:00Z",
                "Health": {"Status": "healthy"},
            },
            "HostConfig": {
                "RestartPolicy": {"Name": "unless-stopped", "MaximumRetryCount": 0}
            },
        }
        self.assertEqual(
            self.collect()["optional_writers_active"], ["face-index-worker"]
        )

    def test_unknown_project_service_blocks_instead_of_ignoring_writer(self):
        item = next(iter(self.fixture.containers.values()))
        item["Config"]["Labels"]["com.docker.compose.service"] = (
            "new-unclassified-worker"
        )
        with self.assertRaisesRegex(
            InventoryError, "container_fora_do_escopo_ou_servico_desconhecido"
        ):
            self.collect()

    def test_in_flight_marker_is_visible(self):
        (self.fixture.state / "production-in-flight.json").write_text(
            "{}", encoding="utf-8"
        )
        self.assertEqual(
            self.collect()["pending_markers"], ["production-in-flight.json"]
        )

    def test_exited_historical_alias_does_not_replace_active_api(self):
        api = next(
            c
            for c in self.fixture.containers.values()
            if c["Config"]["Labels"]["com.docker.compose.service"] == "api"
        )
        old = copy.deepcopy(api)
        old["Id"] = "e" * 64
        old["State"]["Status"] = "exited"
        old["Config"]["Labels"].pop("com.docker.compose.config-hash")
        old["Config"]["Labels"].pop("com.docker.compose.project.config_files")
        self.fixture.containers[old["Id"]] = old
        report = self.collect()
        self.assertEqual(report["services"]["api"]["container_id"], api["Id"])
        self.assertEqual(report["historical_containers"][0]["container_id"], old["Id"])

    def test_stopped_optional_preserves_identity_without_retired_manifest(self):
        optional = copy.deepcopy(next(iter(self.fixture.containers.values())))
        optional["Id"] = "e" * 64
        labels = optional["Config"]["Labels"]
        labels["com.docker.compose.service"] = "raw-development-worker"
        labels["com.docker.compose.project.config_files"] = str(
            self.fixture.root / "retired.yml"
        )
        optional["State"]["Status"] = "exited"
        self.fixture.containers[optional["Id"]] = optional
        item = self.collect()["services"]["raw-development-worker"]
        self.assertEqual(item["container_id"], optional["Id"])
        self.assertEqual(item["compose_files"], [])
        self.assertEqual(len(item["compose_labels_sha256"]), 64)
        optional["State"]["Status"] = "running"
        with self.assertRaisesRegex(
            InventoryError, "compose_path_fora_das_raizes_ou_ausente"
        ):
            self.collect()

    def test_paused_producers_still_require_full_compose_provenance(self):
        for item in self.fixture.containers.values():
            if item["Config"]["Labels"]["com.docker.compose.service"] in {
                "api",
                "worker",
            }:
                item["State"]["Status"] = "exited"
        report = self.collector.collect(
            expected_sha=EXPECTED_SHA,
            candidate_image_id=IMAGE_CANDIDATE,
            allow_paused_producers=True,
        )
        self.assertTrue(report["services"]["api"]["compose_files"])
        self.fixture.compose_path.unlink()
        with self.assertRaises(InventoryError):
            self.collector.collect(
                expected_sha=EXPECTED_SHA,
                candidate_image_id=IMAGE_CANDIDATE,
                allow_paused_producers=True,
            )

    def test_duplicate_active_api_still_blocks(self):
        item = copy.deepcopy(next(iter(self.fixture.containers.values())))
        item["Id"] = "e" * 64
        self.fixture.containers[item["Id"]] = item
        with self.assertRaisesRegex(InventoryError, "servico_ativo_duplicado"):
            self.collect()

    def test_cli_compose_version_is_explicit_and_allowlisted(self):
        from preview_worker_security_release import parser

        self.assertEqual(
            parser().parse_args(["inventory"]).expected_compose_version, "2.35.1"
        )
        self.assertEqual(
            parser()
            .parse_args(["inventory", "--expected-compose-version", "5.6.1"])
            .expected_compose_version,
            "5.6.1",
        )
        with self.assertRaises(SystemExit):
            parser().parse_args(["inventory", "--expected-compose-version", "9.9.9"])


if __name__ == "__main__":
    unittest.main()
