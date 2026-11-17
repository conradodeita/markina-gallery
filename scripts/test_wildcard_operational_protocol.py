"""Peers Unix reais e pedidos maliciosos; sem proxy ou serviço externo."""

import json
import os
import socket
import struct
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wildcard_operational_protocol import MAX_REQUEST, handle_connection


@unittest.skipUnless(hasattr(socket, "SO_PEERCRED"), "Exige SO_PEERCRED Linux")
class ProtocolTests(unittest.TestCase):
    def request(self, payload, *, uid=None, installer=None, declared_size=None):
        calls = []

        def install(chain, key):
            calls.append((chain, key))
            return {"fingerprint": "a" * 64, "replayed": False}

        client, server = socket.socketpair()
        self.addCleanup(client.close)
        self.addCleanup(server.close)
        worker = threading.Thread(
            target=handle_connection,
            args=(server, os.getuid() if uid is None else uid, installer or install),
        )
        worker.start()
        client.sendall(
            struct.pack("!I", len(payload) if declared_size is None else declared_size)
            + payload
        )
        client.shutdown(socket.SHUT_WR)
        result = json.loads(client.recv(4096))
        worker.join(6)
        self.assertFalse(worker.is_alive())
        return result, calls

    def test_fixed_bundle_request_and_receipt(self):
        payload = json.dumps(
            {"v": 1, "fullchain": "synthetic-chain", "private_key": "synthetic-key"}
        ).encode()
        result, calls = self.request(payload)
        self.assertEqual(
            result, {"ok": True, "fingerprint": "a" * 64, "replayed": False}
        )
        self.assertEqual(calls, [(b"synthetic-chain", b"synthetic-key")])

    def test_arbitrary_destinations_commands_and_duplicate_fields_are_rejected(self):
        base = {"v": 1, "fullchain": "synthetic-chain", "private_key": "synthetic-key"}
        cases = [
            json.dumps(dict(base, **{field: "../../unsafe"})).encode()
            for field in ("path", "container", "command", "hook", "uid")
        ]
        cases += [
            b'{"v":1,"v":1,"fullchain":"x","private_key":"y"}',
            json.dumps(dict(base, v=True)).encode(),
            b"[]",
            b"invalid-json",
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                result, calls = self.request(payload)
                self.assertFalse(result["ok"])
                self.assertEqual(calls, [])

    def test_excessive_and_truncated_inputs_do_not_install(self):
        for payload, size in ((b"", MAX_REQUEST + 1), (b"{", 100), (b"", 0)):
            result, calls = self.request(payload, declared_size=size)
            self.assertFalse(result["ok"])
            self.assertEqual(calls, [])

    def test_installer_exception_and_receipt_are_sanitized(self):
        payload = b'{"v":1,"fullchain":"x","private_key":"synthetic-secret"}'

        def fail(*args):
            raise RuntimeError("synthetic-secret")

        result, _ = self.request(payload, installer=fail)
        self.assertEqual(result, {"ok": False, "error": "installation_failed"})

    @unittest.skipUnless(
        hasattr(os, "fork") and os.getuid() == 0, "Exige UID descartável no container"
    )
    def test_real_different_uid_is_denied_before_reading_request(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "installer.sock"
            Path(directory).chmod(0o755)  # Só este socket sintético, sem segredo.
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(str(path))
                path.chmod(0o666)
                listener.listen(1)
                pid = os.fork()
                if pid == 0:
                    try:
                        os.setgroups([])
                        os.setgid(65534)
                        os.setuid(65534)
                        with socket.socket(socket.AF_UNIX) as client:
                            client.connect(str(path))
                            result = json.loads(client.recv(4096))
                        os._exit(
                            0 if result == {"ok": False, "error": "peer_denied"} else 1
                        )
                    except OSError:
                        os._exit(2)
                listener.settimeout(5)
                with listener.accept()[0] as connection:
                    handle_connection(
                        connection,
                        0,
                        lambda *args: self.fail("Unauthorized peer installed"),
                    )
                _, status = os.waitpid(pid, 0)
                self.assertEqual(os.waitstatus_to_exitcode(status), 0)

    @unittest.skipUnless(
        hasattr(os, "fork") and os.getuid() == 0, "Exige UID descartável no container"
    )
    def test_authorized_nonroot_peer_is_handled_by_root_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "installer.sock"
            Path(directory).chmod(0o755)
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(str(path))
                path.chmod(0o666)
                listener.listen(1)
                pid = os.fork()
                if pid == 0:
                    try:
                        os.setgroups([])
                        os.setgid(65534)
                        os.setuid(65534)
                        payload = b'{"v":1,"fullchain":"synthetic-chain","private_key":"synthetic-key"}'
                        with socket.socket(socket.AF_UNIX) as client:
                            client.connect(str(path))
                            client.sendall(struct.pack("!I", len(payload)) + payload)
                            result = json.loads(client.recv(4096))
                        os._exit(0 if result.get("ok") is True else 1)
                    except OSError:
                        os._exit(2)

                def install(chain, key):
                    self.assertEqual(os.getuid(), 0)
                    self.assertEqual(
                        (chain, key), (b"synthetic-chain", b"synthetic-key")
                    )
                    return {"fingerprint": "a" * 64, "replayed": False}

                listener.settimeout(5)
                with listener.accept()[0] as connection:
                    handle_connection(connection, 65534, install)
                _, status = os.waitpid(pid, 0)
                self.assertEqual(os.waitstatus_to_exitcode(status), 0)


if __name__ == "__main__":
    unittest.main()
