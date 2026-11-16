"""Validação offline de bundle TLS; nenhum acesso a DNS, ACME ou proxy."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import ExtendedKeyUsageOID
from cryptography.x509.verification import PolicyBuilder, Store, VerificationError

HOST = "*.pickyourpic.com.br"
# O verificador TLS exige um hostname concreto. O SAN é conferido separadamente.
PROBE_HOST = "certificate-check.pickyourpic.com.br"
_CERTIFICATE = re.compile(
    rb"-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----"
)


class BundleError(RuntimeError):
    """Código sanitizado, sem conteúdo PEM ou detalhes de chaves."""


def _certificates(pem: bytes, limit: int) -> list[x509.Certificate]:
    if not isinstance(pem, bytes) or not 1 <= len(pem) <= limit:
        raise ValueError()
    # Não aceitar lixo, chaves ou blocos de outra natureza entre certificados.
    blocks = _CERTIFICATE.findall(pem)
    if not blocks or _CERTIFICATE.sub(b"", pem).strip():
        raise ValueError()
    certificates = [x509.load_pem_x509_certificate(block) for block in blocks]
    fingerprints = {cert.fingerprint(hashes.SHA256()) for cert in certificates}
    if len(fingerprints) != len(certificates):
        raise ValueError()
    return certificates


def validate_bundle(chain: bytes, key: bytes, trust: bytes) -> str:
    """Retorna SHA-256 da folha após validação WebPKI e da chave correspondente.

    O trust store é uma entrada pública do operador, nunca extraído do bundle.
    O chamador deve fixar e proteger seu hash antes da instalação operacional.
    Não busca AIA, intermediárias, CRLs ou OCSP pela rede.
    """
    try:
        certificates = _certificates(chain, 65536)
        anchors = _certificates(trust, 1048576)
        if (
            len(certificates) > 8
            or not isinstance(key, bytes)
            or not 1 <= len(key) <= 16384
        ):
            raise ValueError()
        if not re.fullmatch(
            rb"\s*-----BEGIN PRIVATE KEY-----\s+[A-Za-z0-9+/=\s]+-----END PRIVATE KEY-----\s*",
            key,
        ):
            raise ValueError()
        leaf = certificates[0]
        san = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        if list(san) != [x509.DNSName(HOST)]:
            raise ValueError()
        if leaf.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError()
        usage = leaf.extensions.get_extension_for_class(x509.KeyUsage).value
        eku = leaf.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        if not usage.digital_signature or usage.key_cert_sign or usage.crl_sign:
            raise ValueError()
        if ExtendedKeyUsageOID.SERVER_AUTH not in eku:
            raise ValueError()
        now = datetime.now(timezone.utc)
        if leaf.not_valid_after_utc <= now + timedelta(days=7):
            raise ValueError()
        private_key = serialization.load_pem_private_key(key, password=None)
        public_format = (
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        if private_key.public_key().public_bytes(
            *public_format
        ) != leaf.public_key().public_bytes(*public_format):
            raise ValueError()
        verifier = (
            PolicyBuilder()
            .store(Store(anchors))
            .time(now)
            .max_chain_depth(6)
            .build_server_verifier(x509.DNSName(PROBE_HOST))
        )
        verified = verifier.verify(leaf, certificates[1:])
        # Rejeitar certificados não relacionados no payload, mesmo que exista um caminho válido.
        if any(cert not in verified for cert in certificates):
            raise ValueError()
        if any(
            cert.not_valid_after_utc <= now + timedelta(days=7) for cert in verified
        ):
            raise ValueError()
        return sha256(leaf.public_bytes(serialization.Encoding.DER)).hexdigest()
    except (
        ValueError,
        TypeError,
        UnsupportedAlgorithm,
        VerificationError,
        x509.ExtensionNotFound,
        x509.DuplicateExtension,
        OverflowError,
    ):
        raise BundleError("bundle_invalid") from None
