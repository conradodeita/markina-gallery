"""Recifragem operacional por tenant; dry-run padrão, sem segredos em argumentos."""

import argparse
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.auth import SessionLocal
from app.infinitepay_credentials import rotate_secrets
from app.integration_secrets import IntegrationSecretError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", required=True, type=UUID)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args(argv)
    if args.apply and args.confirmation != str(args.tenant_id):
        parser.error("--apply exige --confirmation com o mesmo UUID do tenant.")
    try:
        with SessionLocal() as db:
            result = rotate_secrets(db, tenant_id=args.tenant_id, apply=args.apply)
            if args.apply:
                db.commit()
            else:
                db.rollback()
    except (IntegrationSecretError, HTTPException, SQLAlchemyError):
        print(json.dumps({"error": "Recifragem não concluída; nenhuma alteração foi aplicada."}))
        return 1
    print(json.dumps({"tenant_id": str(args.tenant_id), **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
