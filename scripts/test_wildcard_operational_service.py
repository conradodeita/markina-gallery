"""Negativas da configuração root-owned, sem criar serviços."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import wildcard_operational_service as service


@unittest.skipUnless(
    os.name == "posix" and os.getuid() == 0, "Exige root no container próprio"
)
class ServiceTests(unittest.TestCase):
    def test_root_metadata_rejects_links_writable_mode_and_excessive_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / "issuer.json"
            path.write_bytes(b"{}")
            path.chmod(0o644)
            with patch.object(service, "CONFIG", root):
                self.assertEqual(service.root_public_file("issuer.json"), b"{}")
                path.chmod(0o666)
                with self.assertRaises(service.ServiceError):
                    service.root_public_file("issuer.json")
                path.unlink()
                path.symlink_to(root / "elsewhere")
                with self.assertRaises(OSError):
                    service.root_public_file("issuer.json")
                path.unlink()
                path.write_bytes(b"x" * 8193)
                path.chmod(0o644)
                with self.assertRaises(service.ServiceError):
                    service.root_public_file("issuer.json")

    def test_helper_cannot_start_without_systemd_socket_activation(self):
        with (
            patch.dict(os.environ, {"LISTEN_PID": "0", "LISTEN_FDS": "0"}),
            self.assertRaisesRegex(
                service.ServiceError, "^socket_activation_required$"
            ),
        ):
            service.helper()

    def test_issuer_refuses_docker_group_before_loading_approval(self):
        with (
            patch("pwd.getpwnam", return_value=SimpleNamespace(pw_uid=12001)),
            patch("os.getuid", return_value=12001),
            patch("grp.getgrnam", return_value=SimpleNamespace(gr_gid=998)),
            patch("os.getgroups", return_value=[998]),
            patch.object(service, "root_public_file", side_effect=AssertionError),
            self.assertRaisesRegex(service.ServiceError, "^issuer_privilege_invalid$"),
        ):
            service.issuer_once()


if __name__ == "__main__":
    unittest.main()
