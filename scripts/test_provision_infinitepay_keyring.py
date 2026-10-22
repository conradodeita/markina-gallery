"""Bootstrap exercitado apenas em diretorios descartaveis e material sintetico."""

import importlib.util
import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).with_name("provision_infinitepay_keyring.py")
spec = importlib.util.spec_from_file_location("bootstrap", SOURCE)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@unittest.skipUnless(
    os.name == "posix",
    "Permissoes/owner/symlink exigem Linux; executar na imagem ARM64",
)
class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="pyp-synthetic-vault-")
        self.root = Path(self.folder.name)
        self.root.chmod(0o700)
        self.keyring = self.root / "integration-secrets.env"
        self.backup = self.root / "backup.json"
        self.link = self.root / "docker" / ".env.integration-secrets"
        self.link.parent.mkdir()
        self.stack = ExitStack()
        self.stack.enter_context(
            patch.multiple(
                bootstrap,
                STATE=self.root,
                KEYRING=self.keyring,
                BACKUP=self.backup,
                LINK=self.link,
            )
        )
        self.stack.enter_context(
            patch.object(
                bootstrap.os,
                "uname",
                return_value=SimpleNamespace(nodename="clearbudget-vnic"),
            )
        )
        self.metadata = [
            {
                "Config": {
                    "Labels": {"com.docker.compose.project": "markina-gallery"},
                    "Env": ["APP_ENV=staging"],
                }
            }
        ]
        self.inspect = self.stack.enter_context(
            patch.object(
                bootstrap.subprocess,
                "check_output",
                return_value=json.dumps(self.metadata).encode(),
            )
        )
        self.prompt = self.stack.enter_context(
            patch.object(
                bootstrap.getpass,
                "getpass",
                side_effect=[
                    "synthetic-only-long-password",
                    "synthetic-only-long-password",
                ],
            )
        )
        self.terminal = self.stack.enter_context(
            patch.object(bootstrap.sys, "stdin", SimpleNamespace(isatty=lambda: True))
        )
        original = bootstrap.transform
        self.stack.enter_context(
            patch.object(
                bootstrap,
                "transform",
                side_effect=lambda payload: original(payload, local=True),
            )
        )
        self.stack.enter_context(redirect_stdout(io.StringIO()))

    def tearDown(self):
        self.stack.close()
        self.folder.cleanup()

    def assert_no_material(self):
        self.assertFalse(self.keyring.exists())
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.link.is_symlink())

    def test_success_writes_restricted_files_and_never_replaces_existing_material(self):
        bootstrap.provision()
        self.assertEqual(stat.S_IMODE(self.keyring.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.backup.stat().st_mode), 0o600)
        self.assertEqual(self.link.resolve(), self.keyring)
        active = self.keyring.read_bytes()
        backup = self.backup.read_bytes()
        self.assertNotIn(active, backup)
        self.assertEqual(
            json.loads(backup)["format"], "pick-your-pic.integration-keyring-backup.v1"
        )
        with self.assertRaisesRegex(RuntimeError, "existing"):
            bootstrap.provision()
        self.assertEqual(self.keyring.read_bytes(), active)
        self.assertEqual(self.backup.read_bytes(), backup)

    def test_noninteractive_rejected_before_password_or_writes(self):
        bootstrap.sys.stdin.isatty = lambda: False
        with self.assertRaisesRegex(RuntimeError, "interactive"):
            bootstrap.provision()
        self.prompt.assert_not_called()
        self.assert_no_material()

    def test_password_mismatch_preserves_empty_state(self):
        self.prompt.side_effect = [
            "synthetic-only-long-password",
            "different-synthetic-password",
        ]
        with self.assertRaisesRegex(RuntimeError, "password"):
            bootstrap.provision()
        self.assert_no_material()

    def test_short_password_rejected(self):
        self.prompt.side_effect = ["short", "short"]
        with self.assertRaisesRegex(RuntimeError, "password"):
            bootstrap.provision()
        self.assert_no_material()

    def test_pending_release_rejected_before_inspect_or_password(self):
        (self.root / "app-in-flight.sha").write_text("synthetic")
        with self.assertRaisesRegex(RuntimeError, "pending"):
            bootstrap.provision()
        self.inspect.assert_not_called()
        self.prompt.assert_not_called()
        self.assert_no_material()

    def test_public_directory_rejected(self):
        self.root.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, "unsafe"):
            bootstrap.provision()
        self.prompt.assert_not_called()
        self.assert_no_material()

    def test_wrong_environment_rejected_without_writes(self):
        self.metadata[0]["Config"]["Env"] = ["APP_ENV=development"]
        self.inspect.return_value = json.dumps(self.metadata).encode()
        with self.assertRaisesRegex(RuntimeError, "environment"):
            bootstrap.provision()
        self.prompt.assert_not_called()
        self.assert_no_material()

    def test_cryptographic_backup_recovers_and_rejects_three_tamper_cases(self):
        # self_test chama transform(local=True); retirar somente o redirecionamento
        # para docker usado pelo caminho operacional, mantendo a criptografia real.
        self.stack.close()
        with redirect_stdout(io.StringIO()):
            bootstrap.self_test()


if __name__ == "__main__":
    unittest.main()
