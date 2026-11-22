"""CA e chaves descartáveis; não acessa certificados reais ou a rede."""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wildcard_operational_bundle import HOST, BundleError, validate_bundle


def certificate(
    name,
    key,
    issuer_key=None,
    issuer=None,
    *,
    ca=False,
    days=90,
    san=None,
    server_auth=True,
    digital_signature=True,
    start=-1,
):
    now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    signer = issuer_key or key
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer.subject if issuer else subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now + timedelta(days=start))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(
            x509.BasicConstraints(ca=ca, path_length=3 if ca else None), True
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(signer.public_key()),
            False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature, False, False, False, False, ca, ca, False, False
            ),
            True,
        )
    )
    if not ca:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName(n) for n in (san if san is not None else [HOST])]
            ),
            False,
        )
        builder = builder.add_extension(
            x509.ExtendedKeyUsage(
                [
                    ExtendedKeyUsageOID.SERVER_AUTH
                    if server_auth
                    else ExtendedKeyUsageOID.CLIENT_AUTH
                ]
            ),
            False,
        )
    return builder.sign(signer, hashes.SHA256())


def pem(cert):
    return cert.public_bytes(serialization.Encoding.PEM)


def private(key):
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.root_key = ec.generate_private_key(ec.SECP256R1())
        self.root = certificate("Synthetic root", self.root_key, ca=True)
        self.intermediate_key = ec.generate_private_key(ec.SECP256R1())
        self.intermediate = certificate(
            "Synthetic intermediate",
            self.intermediate_key,
            self.root_key,
            self.root,
            ca=True,
        )
        self.leaf_key = ec.generate_private_key(ec.SECP256R1())
        self.leaf = self.issue()

    def issue(self, **kwargs):
        return certificate(
            HOST, self.leaf_key, self.intermediate_key, self.intermediate, **kwargs
        )

    def validate(self, leaf=None, tail=None, key=None, trust=None):
        return validate_bundle(
            pem(leaf or self.leaf) + (pem(self.intermediate) if tail is None else tail),
            private(key or self.leaf_key),
            pem(self.root) if trust is None else trust,
        )

    def test_intermediate_path_with_and_without_root(self):
        fingerprint = self.validate()
        self.assertEqual(len(fingerprint), 64)
        self.assertEqual(
            fingerprint, self.validate(tail=pem(self.intermediate) + pem(self.root))
        )

    def test_directly_signed_leaf(self):
        leaf = certificate(HOST, self.leaf_key, self.root_key, self.root)
        result = self.validate(leaf=leaf, tail=b"")
        self.assertEqual(result, leaf.fingerprint(hashes.SHA256()).hex())

    def test_bad_paths_are_rejected(self):
        other_key = ec.generate_private_key(ec.SECP256R1())
        other = certificate("Untrusted", other_key, ca=True)
        for kwargs in (
            {"tail": b""},
            {"trust": pem(other)},
            {"tail": pem(self.intermediate) + pem(other)},
            {"tail": pem(self.intermediate) * 2},
        ):
            with (
                self.subTest(kwargs=list(kwargs)),
                self.assertRaisesRegex(BundleError, "^bundle_invalid$"),
            ):
                self.validate(**kwargs)

    def test_wrong_san_and_extra_name_are_rejected(self):
        for names in (
            ["markina.pickyourpic.com.br"],
            [HOST, "pickyourpic.com.br"],
            ["*.*.pickyourpic.com.br"],
            ["*.example.invalid"],
        ):
            with self.subTest(names=names), self.assertRaises(BundleError):
                self.validate(leaf=self.issue(san=names))

    def test_validity_usage_and_key_are_rejected(self):
        for kwargs in (
            {"days": 1},
            {"days": -0.5},
            {"start": 1},
            {"server_auth": False},
            {"digital_signature": False},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(BundleError):
                self.validate(leaf=self.issue(**kwargs))
        with self.assertRaises(BundleError):
            self.validate(key=ec.generate_private_key(ec.SECP256R1()))

    def test_invalid_payload_is_sanitized(self):
        for chain, key, trust in (
            (b"secret-invalid-pem", private(self.leaf_key), pem(self.root)),
            (pem(self.leaf), b"invalid-key", pem(self.root)),
            (b"x" * 65537, b"x", b"x"),
            (pem(self.leaf) + b"garbage", private(self.leaf_key), pem(self.root)),
            (pem(self.leaf), private(self.leaf_key) + b"garbage", pem(self.root)),
        ):
            with (
                self.subTest(size=len(chain)),
                self.assertRaisesRegex(BundleError, "^bundle_invalid$"),
            ):
                validate_bundle(chain, key, trust)


if __name__ == "__main__":
    unittest.main()
