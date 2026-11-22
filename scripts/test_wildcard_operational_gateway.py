"""Metadata/argv do gateway, sem Docker real ou segredo operacional."""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wildcard_operational_gateway import (
    BASE,
    FILES,
    IMAGE,
    GatewayError,
    NpmGateway,
)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.approval = {
            "container_id": "a" * 64,
            "image_id": IMAGE,
            "files_sha256": {name: "b" * 64 for name in FILES},
        }
        self.calls = []

    def runner(self, args, **kwargs):
        self.calls.append((args, kwargs))
        if args[5] == "inspect":
            data = "|".join(
                json.dumps(v) for v in ("a" * 64, IMAGE, "/nginx-proxy-manager", True)
            )
        elif args[7] == "sha256sum":
            data = "\n".join("b" * 64 + "  " + BASE + name for name in FILES)
        else:
            data = json.dumps({"fingerprint": "c" * 64, "replayed": False})
        return SimpleNamespace(stdout=data.encode())

    def test_only_fixed_exec_and_approved_id_receive_bundle_on_stdin(self):
        gateway = NpmGateway(self.approval, runner=self.runner)
        self.assertEqual(
            gateway(b"public-chain", b"synthetic-secret")["fingerprint"], "c" * 64
        )
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(
            self.calls[-1][0],
            [
                "/usr/bin/docker",
                "--host",
                "unix:///var/run/docker.sock",
                "--config",
                "/etc/pyp-acme-issuer/docker-client",
                "exec",
                "-i",
                "a" * 64,
                "/opt/certbot/bin/python3",
                "-B",
                BASE + "scripts/wildcard_operational_npm_helper.py",
            ],
        )
        for args, options in self.calls:
            self.assertNotIn("synthetic-secret", " ".join(args))
            self.assertEqual(options["stderr"], subprocess.DEVNULL)
            self.assertEqual(options["timeout"], 180)
        self.assertIn(b"synthetic-secret", self.calls[-1][1]["input"])

    def test_configuration_cannot_choose_container_name_path_command_or_image(self):
        for change in (
            {"container_id": "nginx-proxy-manager"},
            {"image_id": "sha256:other"},
            {"command": "rm"},
            {"files_sha256": {"../../unsafe": "b" * 64}},
        ):
            with (
                self.subTest(change=list(change)),
                self.assertRaisesRegex(GatewayError, "^approval_invalid$"),
            ):
                NpmGateway(dict(self.approval, **change), runner=self.runner)
        self.assertEqual(self.calls, [])

    def test_drift_stops_before_installation(self):
        def wrong(args, **kwargs):
            if args[5] == "inspect":
                return SimpleNamespace(stdout=b"changed")
            self.fail("Executed after drift")

        with self.assertRaisesRegex(GatewayError, "^target_changed$"):
            NpmGateway(self.approval, runner=wrong)(b"chain", b"key")

    def test_errors_are_sanitized(self):
        def fail(*args, **kwargs):
            raise subprocess.CalledProcessError(
                1, "synthetic-secret", output=b"private"
            )

        with self.assertRaisesRegex(GatewayError, "^gateway_failed$"):
            NpmGateway(self.approval, runner=fail)(b"chain", b"key")


if __name__ == "__main__":
    unittest.main()
