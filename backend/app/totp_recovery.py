"""Geração e validação de códigos de recuperação TOTP com Argon2id."""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_HASHER = PasswordHasher(time_cost=2, memory_cost=19_456, parallelism=1, hash_len=32, salt_len=16)


def create_recovery_codes(count: int = 10) -> list[str]:
    """Gera códigos independentes de 144 bits e seus hashes não são retornados."""
    codes: list[str] = []
    selectors: set[str] = set()
    while len(codes) < count:
        code = secrets.token_urlsafe(18)
        if code[:4] not in selectors:
            selectors.add(code[:4])
            codes.append(code)
    return codes


def hash_recovery_code(code: str) -> str:
    return _HASHER.hash(code[4:])


def recovery_code_selector(code: str) -> str:
    return code[:4] if len(code) == 24 else ""


def verify_recovery_code_hash(encoded_hash: str, candidate: str) -> bool:
    """Valida sem propagar detalhes de formato/hash e sem comparar em texto claro."""
    try:
        return len(candidate) == 24 and _HASHER.verify(encoded_hash, candidate[4:])
    except (InvalidHashError, VerificationError):
        return False
