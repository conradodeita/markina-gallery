"""HMAC de CPF do fotógrafo com versões de chave e escopo de tenant."""

from __future__ import annotations

import base64
import binascii
import hmac
import json
import os
import re
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth import PhotographerBusinessProfile, pii_fingerprint

LEGACY_KEY_VERSION = "legacy-v0"
_KEYRING_ENV = "PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON"
_ACTIVE_VERSION_ENV = "PHOTOGRAPHER_CPF_FINGERPRINT_ACTIVE_KEY_VERSION"
_KEY_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
_CPF_DOMAIN = b"pickyourpic:photographer-cpf:"


class PhotographerCpfFingerprintError(RuntimeError):
    """Chave ausente, inválida ou incompatível com as versões persistidas."""


def normalize_cpf(cpf: str) -> str:
    """Normaliza CPF e valida dígitos verificadores sem devolver o valor em erro."""
    if not isinstance(cpf, str) or not re.fullmatch(r"[0-9.\-/ ]{11,20}", cpf):
        raise PhotographerCpfFingerprintError("CPF inválido para comparação protegida.")
    digits = "".join(char for char in cpf if char.isascii() and char.isdigit())
    if len(digits) != 11 or len(set(digits)) == 1:
        raise PhotographerCpfFingerprintError("CPF inválido para comparação protegida.")
    for length in (9, 10):
        total = sum(int(digits[index]) * (length + 1 - index) for index in range(length))
        check = (total * 10) % 11
        if check == 10:
            check = 0
        if int(digits[length]) != check:
            raise PhotographerCpfFingerprintError("CPF inválido para comparação protegida.")
    return digits


def _digits(cpf: str) -> str:
    return normalize_cpf(cpf)


def _load_configured_keys() -> tuple[dict[str, bytes], str]:
    raw_ring = os.getenv(_KEYRING_ENV, "").strip()
    keys: dict[str, bytes] = {}
    active = os.getenv(_ACTIVE_VERSION_ENV, "").strip()
    if raw_ring:
        try:
            parsed = json.loads(raw_ring)
        except (TypeError, json.JSONDecodeError):
            raise PhotographerCpfFingerprintError("Configuração de versão do CPF indisponível.") from None
        if not isinstance(parsed, dict) or not parsed or len(parsed) > 16:
            raise PhotographerCpfFingerprintError("Configuração de versão do CPF indisponível.")
        for version, encoded in parsed.items():
            if (not isinstance(version, str) or not _KEY_VERSION.fullmatch(version)
                    or version == LEGACY_KEY_VERSION or not isinstance(encoded, str)):
                raise PhotographerCpfFingerprintError("Configuração de versão do CPF indisponível.")
            try:
                key = base64.b64decode(encoded.encode("ascii"), altchars=b"-_", validate=True)
            except (ValueError, UnicodeEncodeError, binascii.Error):
                raise PhotographerCpfFingerprintError("Configuração de versão do CPF indisponível.") from None
            if len(key) != 32:
                raise PhotographerCpfFingerprintError("Configuração de versão do CPF indisponível.")
            keys[version] = key
        if not active or not _KEY_VERSION.fullmatch(active) or active not in keys:
            raise PhotographerCpfFingerprintError("Versão ativa do CPF indisponível.")
    else:
        if active and active != LEGACY_KEY_VERSION:
            raise PhotographerCpfFingerprintError("Versão ativa do CPF indisponível.")
        active = LEGACY_KEY_VERSION
    return keys, active


def _fingerprint(cpf: str, version: str, keys: dict[str, bytes]) -> str:
    digits = _digits(cpf)
    if version == LEGACY_KEY_VERSION:
        try:
            # Mantém exatamente o fingerprint já produzido pelo onboarding.
            return pii_fingerprint("photographer-cpf:" + digits)
        except RuntimeError:
            raise PhotographerCpfFingerprintError("Chave histórica do CPF indisponível.") from None
    key = keys.get(version)
    if key is None:
        raise PhotographerCpfFingerprintError("Versão histórica do CPF indisponível.")
    return hmac.new(key, _CPF_DOMAIN + digits.encode("ascii"), sha256).hexdigest()


def active_cpf_fingerprint(
    db: Session,
    cpf: str,
    *,
    exclude_profile_id: UUID | None = None,
) -> tuple[str, str, bool]:
    """Retorna versão/assinatura ativa e verifica duplicidade em todas as versões usadas."""

    digits = _digits(cpf)
    keys, active = _load_configured_keys()
    if db.get_bind().dialect.name == "postgresql":
        try:
            lock_digest = bytes.fromhex(pii_fingerprint("photographer-cpf-unique:" + digits)[:16])
        except RuntimeError:
            raise PhotographerCpfFingerprintError("Chave de unicidade do CPF indisponível.") from None
        lock_id = int.from_bytes(lock_digest, byteorder="big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
    stored_versions = set(db.scalars(
        select(PhotographerBusinessProfile.cpf_fingerprint_key_version)
        .where(PhotographerBusinessProfile.cpf_fingerprint_key_version.is_not(None))
        .distinct()
    ))
    versions = stored_versions | {active}
    candidates = {version: _fingerprint(cpf, version, keys) for version in versions}
    statement = select(PhotographerBusinessProfile.id).where(
        PhotographerBusinessProfile.cpf_fingerprint.in_(set(candidates.values()))
    )
    if exclude_profile_id is not None:
        statement = statement.where(PhotographerBusinessProfile.id != exclude_profile_id)
    duplicate = db.scalar(statement.limit(1)) is not None
    return active, candidates[active], duplicate


def cpf_matches_tenant(db: Session, tenant_id: UUID, cpf: str) -> bool:
    """Compara somente com o perfil daquele tenant; nunca retorna o fingerprint."""

    profile = db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.tenant_id == tenant_id,
    ))
    if not profile or not profile.cpf_fingerprint or not profile.cpf_fingerprint_key_version:
        return False
    keys, _active = _load_configured_keys()
    candidate = _fingerprint(cpf, profile.cpf_fingerprint_key_version, keys)
    return hmac.compare_digest(candidate, profile.cpf_fingerprint)
