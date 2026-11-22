"""Planeja ou executa a rotação local das chaves envelope TOTP."""

from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.auth import SessionLocal
from app.totp_crypto import TotpSecretCipher, TotpSecretError
from app.totp_migration import rotate_admin_totp_envelopes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    try:
        cipher = TotpSecretCipher.from_environment()
        expected = f"ROTATE_ADMIN_TOTP_KEYS:{cipher.active_key_id}"
        if args.apply and args.confirm != expected:
            parser.error("--apply exige --confirm ROTATE_ADMIN_TOTP_KEYS:<key-id-ativo>")
        with SessionLocal.begin() as db:
            result = rotate_admin_totp_envelopes(db, cipher, apply=args.apply)
        print(json.dumps({"mode": "apply" if args.apply else "dry-run",
                          "active_key_id": cipher.active_key_id,
                          "key_counts": result}, sort_keys=True))
    except (SQLAlchemyError, TotpSecretError, ValueError):
        sys.exit("Rotação recusada; confira o keyring, os envelopes e o estado do banco.")


if __name__ == "__main__":
    main()
