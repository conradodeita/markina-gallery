"""Provas POSIX com material exclusivamente sintético."""

import base64
import json
import os
import secrets
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.admin_totp_custody import load_environment
from scripts.wildcard_operational_files import CredentialError

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "posix", "permissões POSIX requerem Linux")
class CustodyTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.file = self.directory / "keyring.json"
        self.values = {
            "ADMIN_TOTP_SECRET_ENV": "production",
            "ADMIN_TOTP_ACTIVE_KEY_ID": "synthetic-review",
            "ADMIN_TOTP_KEYS": json.dumps({
                "synthetic-review": base64.b64encode(secrets.token_bytes(32)).decode(),
            }),
        }
        self.file.write_text(json.dumps(self.values))
        self.file.chmod(0o600)

    def test_permissions_links_and_ownership(self):
        self.assertEqual(load_environment(self.directory, "production"), self.values)
        self.file.chmod(0o644)
        with self.assertRaises(CredentialError):
            load_environment(self.directory, "production")
        self.file.chmod(0o600)
        hardlink = self.directory / "copy"
        os.link(self.file, hardlink)
        with self.assertRaises(CredentialError):
            load_environment(self.directory, "production")
        hardlink.unlink()
        self.file.rename(hardlink)
        self.file.symlink_to(hardlink)
        with self.assertRaises(CredentialError):
            load_environment(self.directory, "production")
        self.file.unlink()
        hardlink.rename(self.file)
        alias = self.directory / "alias"
        alias.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(CredentialError):
            load_environment(alias, "production")
        alias.unlink()
        self.directory.chmod(0o755)
        with self.assertRaises(CredentialError):
            load_environment(self.directory, "production")
        self.directory.chmod(0o700)
        if os.getuid() == 0:
            os.chown(self.file, 65534, 65534)
            try:
                with self.assertRaises(CredentialError):
                    load_environment(self.directory, "production")
            finally:
                os.chown(self.file, 0, 0)

    def test_invalid_key_environment_and_duplicates(self):
        for payload in [
            json.dumps({**self.values, "ADMIN_TOTP_SECRET_ENV": "staging"}),
            json.dumps({**self.values, "ADMIN_TOTP_KEYS": '{"x":"bad","x":"bad"}'}),
            json.dumps(self.values)[:-1] + ',"ADMIN_TOTP_ACTIVE_KEY_ID":"other"}',
            json.dumps({**self.values, "ADMIN_TOTP_KEYS": "[]"}),
            json.dumps({**self.values, "ADMIN_TOTP_KEYS": '{"synthetic-review":"bad"}'}),
        ]:
            with self.subTest(payload_shape=len(payload)):
                self.file.write_text(payload)
                with self.assertRaisesRegex(CredentialError, "^totp_custody_unavailable$"):
                    load_environment(self.directory, "production")

    def launch(self, directory, code, *, environment="production"):
        return subprocess.run([
            sys.executable, "-B", "-m", "scripts.admin_totp_custody",
            "--directory", str(directory), "--environment", "production",
            "--", sys.executable, "-B", "-c", code,
        ], cwd=ROOT, env={**os.environ, "APP_ENV": environment},
            capture_output=True, text=True, check=False)

    def test_external_restore_and_child_environment(self):
        # A cópia é independente do arquivo fonte e preserva versões históricas.
        restored = self.directory / "external-restore"
        restored.mkdir(mode=0o700)
        target = restored / "keyring.json"
        target.write_bytes(self.file.read_bytes())
        target.chmod(0o400)
        encrypt = self.launch(self.directory, """
from uuid import UUID
from backend.app.totp_crypto import TotpSecretCipher
print(TotpSecretCipher.from_environment().encrypt('synthetic-factor',admin_id=UUID(int=1)))
"""
        )
        self.assertEqual(encrypt.returncode, 0, encrypt.stderr)
        envelope = encrypt.stdout.strip()
        self.file.unlink()
        decrypt = self.launch(restored, f"""
import os,sys
from uuid import UUID
from backend.app.totp_crypto import TotpSecretCipher
assert os.environ['APP_ENV']=='production'
assert TotpSecretCipher.from_environment().decrypt({envelope!r},admin_id=UUID(int=1))=='synthetic-factor'
print('recovery_ok')
""")
        self.assertEqual(decrypt.returncode, 0, decrypt.stderr)
        self.assertEqual(decrypt.stdout.strip(), "recovery_ok")

    def test_failure_hides_material_and_does_not_run_child(self):
        result = self.launch(self.directory, "print('child_ran')", environment="staging")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.strip(), "totp_custody_unavailable")
        self.assertEqual(result.stderr, "")
        self.assertNotIn(self.values["ADMIN_TOTP_KEYS"], result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
