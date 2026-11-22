"""Provas POSIX com chaves/token sintéticos; sem systemd/serviço real."""

import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wildcard_operational_custody import CredentialError, CredentialVault


@unittest.skipUnless(os.name == "posix", "Exige permissões POSIX reais")
class VaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        for name in ("vault", "runtime", "credentials", "offline"):
            (self.base / name).mkdir(mode=0o700)
        self.key = self.base / "credentials/envelope-key"
        self.key.write_bytes(b"0" * 32)
        self.key.chmod(0o400)
        self.ref = uuid4()
        self.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        self.vault = self.open()
        self.vault.store(self.ref, "synthetic-cloudflare-token", self.expiry)

    def open(self, name="vault", key_id="k1"):
        return CredentialVault(
            self.base / name, self.base / "runtime", self.base / "credentials", key_id
        )

    def test_ciphertext_cleanup_success_and_exception(self):
        self.assertNotIn(
            b"synthetic-cloudflare-token",
            (self.base / "vault" / f"{self.ref}.json").read_bytes(),
        )
        for fails in (False, True):
            try:
                with self.vault.materialize(self.ref) as path:
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                    self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
                    self.assertIn("synthetic-cloudflare-token", path.read_text())
                    if fails:
                        raise RuntimeError("synthetic failure")
            except RuntimeError:
                if not fails:
                    raise
            self.assertFalse(path.exists())
        self.assertEqual(list((self.base / "runtime").iterdir()), [])

    def test_wrong_key_expiry_corruption_and_ref_are_rejected(self):
        expired = uuid4()
        self.vault.store(
            expired,
            "synthetic-expired",
            datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        for ref in (expired, uuid4()):
            with (
                self.assertRaisesRegex(CredentialError, "^credential_unavailable$"),
                self.vault.materialize(ref),
            ):
                self.fail("Credential exposed")
        self.key.chmod(0o600)
        self.key.write_bytes(b"1" * 32)
        with self.assertRaises(CredentialError), self.open().materialize(self.ref):
            self.fail("Wrong key accepted")
        (self.base / "vault" / f"{self.ref}.json").write_bytes(b"{broken")
        with self.assertRaises(CredentialError), self.vault.materialize(self.ref):
            self.fail("Corruption accepted")

    def test_links_and_permissions_are_rejected(self):
        self.key.chmod(0o644)
        with self.assertRaises(CredentialError):
            self.open()
        self.key.chmod(0o400)
        self.key.rename(self.base / "offline/key")
        self.key.symlink_to(self.base / "offline/key")
        with self.assertRaises(CredentialError):
            self.open()
        self.key.unlink()
        self.key.hardlink_to(self.base / "offline/key")
        with self.assertRaises(CredentialError):
            self.open()
        self.key.unlink()
        shutil.copyfile(self.base / "offline/key", self.key)
        self.key.chmod(0o400)
        (self.base / "vault").chmod(0o755)
        with self.assertRaises(CredentialError):
            self.open()
        (self.base / "vault").chmod(0o700)
        (self.base / "alias").symlink_to(self.base / "vault")
        with self.assertRaises(CredentialError):
            self.open("alias")

    def test_restore_rotation_and_new_process_state(self):
        backup = self.base / "offline/key"
        shutil.copyfile(self.key, backup)
        backup.chmod(0o400)
        self.key.unlink()
        with self.assertRaises(CredentialError):
            self.open()
        shutil.copyfile(backup, self.key)
        self.key.chmod(0o400)
        with self.open().materialize(self.ref) as restored:
            token = restored.read_text().strip().split(" = ")[1]
        pid = os.fork()
        if pid == 0:
            try:
                with self.open().materialize(self.ref) as restored:
                    valid = "synthetic-cloudflare-token" in restored.read_text()
                os._exit(0 if valid else 1)
            except CredentialError:
                os._exit(2)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        (self.base / "rotated").mkdir(mode=0o700)
        self.key.chmod(0o600)
        self.key.write_bytes(b"2" * 32)
        self.key.chmod(0o400)
        rotated = self.open("rotated", "k2")
        rotated.store(self.ref, token, self.expiry)
        with self.open("rotated", "k2").materialize(self.ref) as path:
            self.assertIn("synthetic-cloudflare-token", path.read_text())
        with self.assertRaises(CredentialError), self.open().materialize(self.ref):
            self.fail("Old ciphertext decrypted by rotated key")

    @unittest.skipUnless(
        hasattr(os, "fork") and os.getuid() == 0,
        "Exige root apenas no container próprio",
    )
    def test_other_uid_cannot_read_key_or_materialized_token(self):
        with self.vault.materialize(self.ref) as path:
            pid = os.fork()
            if pid == 0:
                try:
                    os.setgroups([])
                    os.setgid(65534)
                    os.setuid(65534)
                    for candidate in (self.key, path):
                        try:
                            candidate.read_bytes()
                        except PermissionError:
                            continue
                        os._exit(1)
                    os._exit(0)
                except OSError:
                    os._exit(2)
            _, status = os.waitpid(pid, 0)
            self.assertEqual(os.waitstatus_to_exitcode(status), 0)


if __name__ == "__main__":
    unittest.main()
