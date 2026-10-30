"""Prova POSIX isolada do storage; usa apenas envelopes/chaves sintéticos."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.facial import environment_package_store as storage
from backend.app.facial.environment_package_store import (
    PackageStorageError,
    persist_encrypted_package,
    reopen_package,
)


@unittest.skipUnless(os.name == "posix", "Garantias POSIX exigem Linux")
class PackageStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.packages, self.keys = self.base / "packages", self.base / "keys"
        for root in (self.packages, self.keys):
            root.mkdir(mode=0o700)
        self.payload = {"version": 1, "nonce": "synthetic-nonce", "ciphertext": "synthetic-ciphertext"}
        self.key = b"x" * 32

    def save(self, operation="synthetic"):
        return persist_encrypted_package(self.packages, self.keys, operation,
            encrypted_payload=self.payload, backup_key=self.key)

    def test_roundtrip_and_no_overwrite(self):
        package = self.save()
        self.assertEqual(package.payload, self.payload)
        self.assertEqual(package.key, self.key)
        self.assertEqual(repr(package), "ReopenedPackage(<redacted>)")
        self.assertNotIn(self.key.decode(), (self.packages / "synthetic.json").read_text())
        with self.assertRaises(PackageStorageError):
            self.save()
        self.assertEqual(json.loads((self.packages / "synthetic.json").read_text()), self.payload)

    def test_explicit_size_limit_is_enforced_for_writes_and_reopening(self):
        self.assertEqual(storage._PACKAGE_LIMIT, 512_000_000)
        length = len(json.dumps(self.payload, sort_keys=True, allow_nan=False).encode())
        with patch.object(storage, '_PACKAGE_LIMIT', length):
            self.save()
        with patch.object(storage, '_PACKAGE_LIMIT', length-1):
            with self.assertRaises(PackageStorageError):
                reopen_package(self.packages, self.keys, 'synthetic')
            with self.assertRaises(PackageStorageError):
                self.save('oversized')
        self.assertFalse((self.packages / 'oversized.json').exists())
        self.assertFalse((self.keys / 'oversized.key').exists())

    def test_unsafe_permissions_and_symlinks_are_rejected(self):
        self.packages.chmod(0o755)
        with self.assertRaises(PackageStorageError):
            self.save()
        self.packages.chmod(0o700)
        self.save()
        target = self.packages / "synthetic.json"
        original = target.read_bytes()
        target.unlink()
        outside = self.base / "outside"
        outside.write_bytes(original)
        outside.chmod(0o600)
        target.symlink_to(outside)
        with self.assertRaises(PackageStorageError):
            reopen_package(self.packages, self.keys, "synthetic")
        alias = self.base / "alias"
        alias.symlink_to(self.keys, target_is_directory=True)
        with self.assertRaises(PackageStorageError):
            reopen_package(self.packages, alias, "synthetic")

    def test_path_traversal_and_plain_payload_fail_before_writes(self):
        for operation in ("../outside", "/outside", "", "a/b"):
            with self.assertRaises(PackageStorageError):
                self.save(operation)
        with self.assertRaises(PackageStorageError):
            persist_encrypted_package(self.packages, self.keys, "synthetic",
                encrypted_payload={"plaintext": "private-sentinel"}, backup_key=self.key)
        self.assertEqual(list(self.packages.iterdir()), [])
        self.assertEqual(list(self.keys.iterdir()), [])

    def test_partial_package_and_changed_key_fail_closed(self):
        (self.packages / "synthetic.json").write_text("{}")
        (self.packages / "synthetic.json").chmod(0o600)
        with self.assertRaises(PackageStorageError):
            reopen_package(self.packages, self.keys, "synthetic")
        (self.keys / "synthetic.key").write_bytes(b"short")
        (self.keys / "synthetic.key").chmod(0o600)
        with self.assertRaises(PackageStorageError):
            reopen_package(self.packages, self.keys, "synthetic")


if __name__ == "__main__":
    unittest.main()
