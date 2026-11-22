"""Somente CA, chaves e credenciais sintéticas; nenhum transporte externo."""

import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from scripts.wildcard_certificate_custody import (
    HOST,
    MARKER,
    CustodyError,
    SyntheticInstaller,
    SyntheticVault,
    lab_root,
    renew_synthetic,
    validate_bundle,
)


def synthetic_ca():
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic lab CA")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=120)).add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), False)
            .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, False, False), True)
            .sign(key, hashes.SHA256()))
    return key, cert


def synthetic_bundle(ca_key, ca, host=HOST, days=30):
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)]))
            .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=days))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), False)
            .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), False)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]), False).sign(ca_key, hashes.SHA256()))
    return (cert.public_bytes(serialization.Encoding.PEM) + ca.public_bytes(serialization.Encoding.PEM),
            key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


@unittest.skipUnless(os.name == "posix", "A prova de permissões exige laboratório POSIX")
class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        for name in ("vault", "certificates"):
            root = self.base / name
            root.mkdir(mode=0o700)
            (root / ".pyp-wildcard-lab").write_text(MARKER)
        self.vault = SyntheticVault(self.base / "vault", b"0" * 32)
        self.ref = uuid4()
        self.vault.store(self.ref, "synthetic-cloudflare-token", datetime.now(timezone.utc) + timedelta(hours=1))
        self.ca_key, self.ca = synthetic_ca()
        self.trust = self.ca.public_bytes(serialization.Encoding.PEM)
        self.calls = []
        self.installer = SyntheticInstaller(self.base / "certificates", self.trust,
                                            lambda: self.calls.append("check"),
                                            lambda: self.calls.append("reload"), lambda fingerprint: self.calls.append(fingerprint))

    def test_ciphertext_expiration_reference_and_cleanup(self):
        self.assertNotIn(b"synthetic-cloudflare-token", (self.vault.root / f"{self.ref}.json").read_bytes())
        with self.vault.materialize(self.ref) as path:
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertIn("synthetic-cloudflare-token", path.read_text())
        self.assertFalse(path.exists())
        expired = uuid4()
        self.vault.store(expired, "synthetic-expired", datetime.now(timezone.utc) - timedelta(seconds=1))
        with self.assertRaises(CustodyError), self.vault.materialize(expired):
            self.fail("expired credential exposed")
        wrong = SyntheticVault(self.vault.root, b"1" * 32)
        with self.assertRaises(CustodyError), wrong.materialize(self.ref):
            self.fail("wrong key accepted")

    def test_materialization_removed_after_transport_failure(self):
        seen = []

        def transport(path):
            seen.append(path)
            raise RuntimeError("synthetic-cloudflare-token")

        with self.assertRaisesRegex(CustodyError, "^issuance_failed$"):
            renew_synthetic(self.vault, self.ref, transport, self.installer)
        self.assertFalse(seen[0].exists())
        self.assertFalse((self.installer.root / "current").exists())

    def test_invalid_certificates_never_touch_current(self):
        valid = synthetic_bundle(self.ca_key, self.ca)
        self.installer.install(*valid)
        old = os.readlink(self.installer.root / "current")
        other = synthetic_bundle(self.ca_key, self.ca)
        untrusted_key, untrusted_ca = synthetic_ca()
        for chain, key in (synthetic_bundle(self.ca_key, self.ca, "markina.pickyourpic.com.br"),
                           synthetic_bundle(self.ca_key, self.ca, days=1),
                           synthetic_bundle(untrusted_key, untrusted_ca),
                           (valid[0], other[1]), (b"invalid", valid[1])):
            with self.assertRaisesRegex(CustodyError, "bundle_invalid"):
                self.installer.install(chain, key)
            self.assertEqual(os.readlink(self.installer.root / "current"), old)

    def test_renewal_replay_and_rollback_after_probe_failure(self):
        first = synthetic_bundle(self.ca_key, self.ca)
        receipt = self.installer.install(*first)
        count = len(self.calls)
        self.assertTrue(self.installer.install(*first)["replayed"])
        self.assertEqual(len(self.calls), count)
        new = synthetic_bundle(self.ca_key, self.ca)
        new_fingerprint = validate_bundle(*new, self.trust)

        def probe(fingerprint):
            if fingerprint == new_fingerprint:
                raise RuntimeError("synthetic-secret-must-not-leak")

        self.installer.probe = probe
        with self.assertRaisesRegex(CustodyError, "^installation_failed$"):
            self.installer.install(*new)
        self.assertEqual(os.readlink(self.installer.root / "current"), f"release-{receipt['fingerprint']}")
        self.installer.probe = lambda fingerprint: None
        self.assertFalse(self.installer.install(*new)["replayed"])
        self.assertEqual(os.readlink(self.installer.root / "previous"), f"release-{receipt['fingerprint']}")

    def test_unsafe_roots_and_symlinks_fail_closed(self):
        with self.assertRaises(CustodyError):
            lab_root(self.base)
        (self.installer.root / "current").symlink_to("../../outside")
        with self.assertRaisesRegex(CustodyError, "unsafe_pointer"):
            self.installer.install(*synthetic_bundle(self.ca_key, self.ca))

    def test_reference_tamper_and_non_synthetic_token_are_rejected(self):
        swapped = uuid4()
        (self.vault.root / f"{self.ref}.json").rename(self.vault.root / f"{swapped}.json")
        with self.assertRaises(CustodyError), self.vault.materialize(swapped):
            self.fail("cross-reference ciphertext accepted")
        with self.assertRaisesRegex(CustodyError, "synthetic_only"):
            self.vault.store(uuid4(), "not-a-synthetic-token", datetime.now(timezone.utc))

    def test_concurrent_replay_installs_once(self):
        bundle = synthetic_bundle(self.ca_key, self.ca)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: self.installer.install(*bundle), (0, 1)))
        self.assertEqual(sorted(result['replayed'] for result in results), [False, True])
        self.assertEqual(self.calls.count('reload'), 1)

    def test_recovery_failure_is_reported_without_claiming_health(self):
        first = synthetic_bundle(self.ca_key, self.ca)
        receipt = self.installer.install(*first)

        def fail_check():
            raise RuntimeError('synthetic-secret')

        self.installer.check_config = fail_check
        with self.assertRaisesRegex(CustodyError, '^recovery_failed$'):
            self.installer.install(*synthetic_bundle(self.ca_key, self.ca))
        self.assertEqual(os.readlink(self.installer.root / 'current'), f"release-{receipt['fingerprint']}")


if __name__ == "__main__":
    unittest.main()
