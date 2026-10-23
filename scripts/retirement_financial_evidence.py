"""Read-only, minimized fingerprints for financial rows preserved by 0087."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

TABLE_COLUMNS = {
    "payment_group": ("id",),
    "sale_order": ("id",),
    "provider_payment": ("id", "provider", "total_cents", "provider_transaction_nsu", "state"),
    "provider_payment_attempt": ("id",),
    "provider_payment_receipt": ("id",),
    "provider_payment_correction": ("id",),
}


def digest_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    row_digests = []
    for row in rows:
        canonical = json.dumps(dict(row), sort_keys=True, separators=(",", ":"), default=str)
        row_digests.append(hashlib.sha256(canonical.encode()).digest())
    digest = hashlib.sha256()
    for row_digest in sorted(row_digests):
        digest.update(row_digest)
    return {"count": len(row_digests), "sha256": digest.hexdigest()}


def count_confirmed_infinitepay_rows(rows: Iterable[Mapping[str, Any]]) -> int:
    return sum(1 for row in rows if row["provider"] == "infinitepay" and row["state"] == "confirmed")


def snapshot(database_url: str) -> dict[str, Any]:
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        result: dict[str, dict[str, Any]] = {}
        confirmed_count = 0
        with engine.connect() as connection:
            for table, columns in TABLE_COLUMNS.items():
                selected = ", ".join(f'"{column}"' for column in columns)
                rows = connection.execute(text(f'SELECT {selected} FROM "{table}" ORDER BY "id"')).mappings()
                if table == "provider_payment":
                    materialized = list(rows)
                    confirmed_count = count_confirmed_infinitepay_rows(materialized)
                    result[table] = digest_rows(materialized)
                else:
                    result[table] = digest_rows(rows)
        return {"tables": result, "confirmed_infinitepay_count": confirmed_count}
    finally:
        engine.dispose()


def main() -> None:
    from os import environ

    database_url = environ["DATABASE_URL"]
    print(json.dumps(snapshot(database_url), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
