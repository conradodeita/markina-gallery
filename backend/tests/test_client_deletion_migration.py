"""Migration aditiva do recibo de exclusão sem PII ou FK para a cliente."""

import os
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from subprocess import run
from uuid import uuid4

import sqlalchemy as sa


def alembic(url: str, *arguments: str) -> None:
    result = run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_client_deletion_receipt_migration_is_additive_and_reversible(tmp_path) -> None:
    url = f"sqlite:///{(tmp_path / 'client-receipt.sqlite').as_posix()}"
    alembic(url, "upgrade", "20260906_0046")
    engine = sa.create_engine(url)
    instant = datetime.now(UTC)
    admin_id = uuid4()
    with engine.begin() as db:
        db.execute(
            sa.text(
                "INSERT INTO admin_user "
                "(id, email, password_hash, email_verified, totp_secret) "
                "VALUES (:id, :email, :password_hash, :verified, :totp)"
            ),
            {
                "id": admin_id.hex,
                "email": "migration@markina.test",
                "password_hash": "synthetic",
                "verified": True,
                "totp": "synthetic",
            },
        )
    alembic(url, "upgrade", "head")
    receipt = sa.Table("client_deletion_receipt", sa.MetaData(), autoload_with=engine)
    if engine.dialect.name == "sqlite":
        for column in receipt.columns:
            if isinstance(column.type, sa.CHAR) and column.type.length == 32:
                column.type = sa.Uuid()
    target_id = uuid4()
    values = {
        "id": uuid4(),
        "idempotency_key": sha256(b"migration-client-delete-0001").hexdigest(),
        "target_client_id": target_id,
        "actor_admin_id": admin_id,
        "inventory_fingerprint": "a" * 64,
        "status": "completed",
        "removed_counts": {"clients": 1},
        "created_at": instant,
        "completed_at": instant,
    }
    with engine.begin() as db:
        db.execute(receipt.insert().values(**values))
        stored = db.execute(sa.select(receipt)).mappings().one()
        assert stored["target_client_id"] == target_id
        assert stored["removed_counts"] == {"clients": 1}
        assert "name" not in receipt.c
        assert "phone" not in receipt.c
        assert not any(
            foreign_key.parent.name == "target_client_id"
            for foreign_key in receipt.foreign_keys
        )
    alembic(url, "downgrade", "20260906_0046")
    assert "client_deletion_receipt" not in sa.inspect(engine).get_table_names()
    engine.dispose()
