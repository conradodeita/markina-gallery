"""Falhas/crashes sintéticos no instalador, sem reload de serviço real."""

import json
import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cryptography.hazmat.primitives import serialization

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.test_wildcard_certificate_custody import synthetic_bundle, synthetic_ca
from scripts.wildcard_operational_bundle import validate_bundle
from scripts.wildcard_operational_installer import DurableInstaller, InstallationError


@unittest.skipUnless(os.name == "posix", "Exige POSIX para durabilidade/locks")
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.ca_key, self.ca = synthetic_ca()
        self.trust = self.ca.public_bytes(serialization.Encoding.PEM)
        self.calls = []
        self.installer = DurableInstaller(
            self.root,
            self.trust,
            lambda: self.calls.append("check"),
            lambda: self.calls.append("reload"),
            lambda fp: self.calls.append(fp),
        )
        self.first = synthetic_bundle(self.ca_key, self.ca)
        self.second = synthetic_bundle(self.ca_key, self.ca)

    def test_replay_and_concurrent_install(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(lambda _: self.installer.install(*self.first), range(2))
            )
        self.assertEqual(sum(r["replayed"] for r in results), 1)
        self.assertEqual(self.calls.count("reload"), 1)
        self.assertFalse((self.root / "pending.json").exists())

    def test_failed_probe_rolls_back_and_confirms_previous(self):
        first = self.installer.install(*self.first)
        second_fp = validate_bundle(*self.second, self.trust)

        def probe(fp):
            self.calls.append(fp)
            if fp == second_fp:
                raise OSError("private details")

        self.installer.probe = probe
        with self.assertRaisesRegex(InstallationError, "^installation_failed$"):
            self.installer.install(*self.second)
        self.assertEqual(
            os.readlink(self.root / "current"), "release-" + first["fingerprint"]
        )
        self.assertEqual(self.calls[-1], first["fingerprint"])
        self.assertFalse((self.root / "pending.json").exists())

    def test_replay_rejects_modified_files_and_sanitizes_probe_failure(self):
        self.installer.install(*self.first)

        def fail(_):
            raise RuntimeError("sensitive details")

        self.installer.probe = fail
        with self.assertRaisesRegex(InstallationError, "^installation_failed$"):
            self.installer.install(*self.first)
        (self.root / os.readlink(self.root / "current") / "privkey.pem").write_bytes(
            b"bad-key"
        )
        self.installer.probe = lambda _: None
        with self.assertRaisesRegex(InstallationError, "^release_invalid$"):
            self.installer.install(*self.first)

    def test_crash_after_pointer_exchange_is_recovered_by_new_instance(self):
        first = self.installer.install(*self.first)

        def crash():
            raise SystemExit("synthetic-power-loss")

        crashing = DurableInstaller(
            self.root, self.trust, crash, lambda: None, lambda fp: None
        )
        with self.assertRaises(SystemExit):
            crashing.install(*self.second)
        self.assertTrue((self.root / "pending.json").exists())
        restored = DurableInstaller(
            self.root,
            self.trust,
            lambda: self.calls.append("recovery-check"),
            lambda: None,
            lambda fp: self.calls.append(fp),
        )
        result = restored.install(*self.first)
        self.assertTrue(result["replayed"])
        self.assertEqual(
            os.readlink(self.root / "current"), "release-" + first["fingerprint"]
        )
        self.assertFalse((self.root / "pending.json").exists())

    def test_unrecoverable_probe_keeps_journal_and_reports_failure(self):
        self.installer.install(*self.first)

        def fail(_):
            raise OSError("sensitive details")

        self.installer.probe = fail
        with self.assertRaisesRegex(InstallationError, "^recovery_failed$"):
            self.installer.install(*self.second)
        self.assertTrue((self.root / "pending.json").exists())

    def test_paths_invalid_bundles_and_journals_do_not_escape_root(self):
        self.installer.install(*self.first)
        previous = os.readlink(self.root / "current")
        with self.assertRaises(InstallationError):
            self.installer.install(b"invalid", b"private-key")
        self.assertEqual(os.readlink(self.root / "current"), previous)
        (self.root / "pending.json").write_text(
            json.dumps({"previous": "../../unsafe", "target": previous})
        )
        (self.root / "pending.json").chmod(0o600)
        with self.assertRaisesRegex(InstallationError, "^recovery_failed$"):
            self.installer.install(*self.second)
        self.assertEqual(os.readlink(self.root / "current"), previous)


if __name__ == "__main__":
    unittest.main()
