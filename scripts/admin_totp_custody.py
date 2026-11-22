"""Entrega keyring privado ao ambiente de um consumidor, sem shell ou saída secreta."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

from backend.app.totp_crypto import TotpSecretCipher, TotpSecretError
from scripts.wildcard_operational_files import (
    CredentialError,
    _private_directory,
    _read,
)

FIELDS = {"ADMIN_TOTP_SECRET_ENV", "ADMIN_TOTP_ACTIVE_KEY_ID", "ADMIN_TOTP_KEYS"}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def load_environment(directory: Path, environment: str) -> dict[str, str]:
    """Valida permissões e o contrato do cipher sem modificar o ambiente atual."""
    try:
        descriptor = _private_directory(directory)
        try:
            payload = _read(descriptor, "keyring.json", 16384, credential=True)
        finally:
            os.close(descriptor)
        values = json.loads(payload, object_pairs_hook=_unique)
        if (not isinstance(values, dict) or set(values) != FIELDS
                or not all(isinstance(value, str) for value in values.values())
                or values["ADMIN_TOTP_SECRET_ENV"] != environment):
            raise ValueError()
        keys = json.loads(values["ADMIN_TOTP_KEYS"], object_pairs_hook=_unique)
        if not isinstance(keys, dict):
            raise TypeError()
        TotpSecretCipher(
            environment=environment,
            active_key_id=values["ADMIN_TOTP_ACTIVE_KEY_ID"],
            keys={name: base64.b64decode(value, validate=True) for name, value in keys.items()},
        )
        return values
    except (OSError, ValueError, TypeError, KeyError, CredentialError, TotpSecretError):
        raise CredentialError("totp_custody_unavailable") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]
    try:
        if not command or os.environ.get("APP_ENV", args.environment) != args.environment:
            raise CredentialError("totp_custody_unavailable")
        values = load_environment(args.directory, args.environment)
        os.execvpe(command[0], command, {**os.environ, **values, "APP_ENV": args.environment})
    except (OSError, CredentialError):
        print("totp_custody_unavailable")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
