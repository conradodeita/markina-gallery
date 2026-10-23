"""Read-only production readiness check for the system's own PIX method."""

from __future__ import annotations

import json
from collections.abc import Iterable


def summarize(methods: Iterable[dict]) -> dict[str, int | bool]:
    values = list(methods)
    return {
        "tenant_count": len(values),
        "pix_available_count": sum(value.get("pix_available") is True for value in values),
        "card_available_count": sum(value.get("card_available") is True for value in values),
        "all_tenants_pix_available": bool(values) and all(value.get("pix_available") is True for value in values),
    }


def snapshot() -> dict[str, int | bool]:
    from app.auth import SessionLocal, Tenant
    from app.payment_availability import payment_methods
    from sqlalchemy import select

    with SessionLocal() as db:
        tenant_ids = db.scalars(select(Tenant.id)).all()
        methods = [payment_methods(db, tenant_id=tenant_id) for tenant_id in tenant_ids]
    return summarize(methods)


def main() -> None:
    result = snapshot()
    if result["tenant_count"] != 1 or result["all_tenants_pix_available"] is not True \
            or result["card_available_count"] != 0:
        raise SystemExit("PIX próprio indisponível ou escopo de fotógrafos inesperado")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
