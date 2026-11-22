"""Gateway privilegiado com Docker fixo; peer não fornece comandos ou caminhos."""

from __future__ import annotations

import json
import re
import subprocess

from scripts.wildcard_operational_protocol import MAX_REQUEST

DOCKER = "/usr/bin/docker"
IMAGE = "sha256:bd94715ff0d6f11047446b2c149d4adb45deaa8e18152b34befb13945b3dbd7b"
BASE = "/data/pyp-wildcard-helper/"
FILES = (
    "scripts/wildcard_operational_npm_helper.py",
    "scripts/wildcard_operational_installer.py",
    "scripts/wildcard_operational_bundle.py",
    "scripts/wildcard_operational_custody.py",
    "scripts/wildcard_operational_protocol.py",
    "scripts/wildcard_operational_files.py",
    "scripts/wildcard_operational_runtime.py",
    "backend/app/integration_secrets.py",
    "trust.pem",
    "runtime-manifest.json",
)


class GatewayError(RuntimeError):
    pass


class NpmGateway:
    def __init__(self, approval: dict, *, runner=subprocess.run):
        if (
            not isinstance(approval, dict)
            or set(approval) != {"container_id", "image_id", "files_sha256"}
            or approval["image_id"] != IMAGE
            or not isinstance(approval["container_id"], str)
            or not re.fullmatch("[0-9a-f]{64}", approval["container_id"])
            or not isinstance(approval["files_sha256"], dict)
            or set(approval["files_sha256"]) != set(FILES)
            or any(
                not isinstance(v, str) or not re.fullmatch("[0-9a-f]{64}", v)
                for v in approval["files_sha256"].values()
            )
        ):
            raise GatewayError("approval_invalid")
        self.container = approval["container_id"]
        self.hashes = dict(approval["files_sha256"])
        self.runner = runner

    def _run(self, arguments, *, payload=None):
        return self.runner(
            [
                DOCKER,
                "--host",
                "unix:///var/run/docker.sock",
                "--config",
                "/etc/pyp-acme-issuer/docker-client",
                *arguments,
            ],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            timeout=180,
            check=True,
        ).stdout

    def __call__(self, chain: bytes, key: bytes):
        try:
            metadata = self._run(
                [
                    "inspect",
                    "--format",
                    "{{json .Id}}|{{json .Image}}|{{json .Name}}|{{json .State.Running}}",
                    self.container,
                ]
            )
            expected = "|".join(
                json.dumps(v)
                for v in (self.container, IMAGE, "/nginx-proxy-manager", True)
            )
            if metadata.decode().strip() != expected:
                raise GatewayError("target_changed")
            result = self._run(
                ["exec", self.container, "sha256sum", *[BASE + name for name in FILES]]
            )
            expected_hashes = "\n".join(
                self.hashes[name] + "  " + BASE + name for name in FILES
            )
            if result.decode().strip() != expected_hashes:
                raise GatewayError("helper_changed")
            payload = json.dumps(
                {
                    "v": 1,
                    "fullchain": chain.decode("ascii"),
                    "private_key": key.decode("ascii"),
                }
            ).encode()
            if len(payload) > MAX_REQUEST:
                raise GatewayError("request_invalid")
            receipt = json.loads(
                self._run(
                    [
                        "exec",
                        "-i",
                        self.container,
                        "/opt/certbot/bin/python3",
                        "-B",
                        BASE + "scripts/wildcard_operational_npm_helper.py",
                    ],
                    payload=payload,
                )
            )
            if (
                not isinstance(receipt, dict)
                or set(receipt) != {"fingerprint", "replayed"}
                or not isinstance(receipt["fingerprint"], str)
                or not re.fullmatch("[0-9a-f]{64}", receipt["fingerprint"])
                or type(receipt["replayed"]) is not bool
            ):
                raise GatewayError("receipt_invalid")
            return receipt
        except GatewayError:
            raise
        except (
            OSError,
            ValueError,
            TypeError,
            UnicodeError,
            subprocess.SubprocessError,
        ):
            raise GatewayError("gateway_failed") from None
