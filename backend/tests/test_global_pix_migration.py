"""Backfill PIX canônico e reversibilidade em bancos descartáveis."""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from subprocess import run
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.pix import build_static_pix_code


def alembic(url, *arguments, succeeds=True):
    result = run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
        check=False,
    )
    if succeeds:
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    else:
        assert result.returncode != 0
    return result


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("empty", "unconfigured"),
        ("same", "active"),
        ("different", "review_required"),
        ("invalid", "review_required"),
    ],
)
def test_pix_migration_preserves_legacy_and_snapshots(tmp_path, mode, expected):
    url = (
        os.getenv("MARKINA_PIX_MIGRATION_TEST_URL")
        or f"sqlite:///{(tmp_path / 'pix.sqlite').as_posix()}"
    )
    if os.getenv("MARKINA_PIX_MIGRATION_TEST_URL"):
        parsed = sa.engine.make_url(url)
        assert parsed.host == "127.0.0.1" and parsed.port == 55446
        assert parsed.database == "markina_pix_validation"
        maintenance = sa.create_engine(url, isolation_level="AUTOCOMMIT")
        database = f"markina_pix_{mode}_{uuid4().hex}"
        with maintenance.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database}"')
        maintenance.dispose()
        url = parsed.set(database=database).render_as_string(hide_password=False)
    alembic(url, "upgrade", "20260906_0045")
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    metadata.reflect(bind=engine)
    if engine.dialect.name == "sqlite":
        for table in metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, sa.CHAR) and column.type.length == 32:
                    column.type = sa.Uuid()
    admin_id = uuid4()
    instant = datetime.now(UTC)
    code = build_static_pix_code(
        "foto@example.test", receiver_name="MARKINA", receiver_city="SAO PAULO"
    )
    with engine.begin() as db:
        db.execute(
            metadata.tables["admin_user"]
            .insert()
            .values(
                id=admin_id,
                email="admin@pix.test",
                password_hash="synthetic",
                email_verified=True,
                totp_secret="synthetic",
            )
        )
        parent_id, client_id = uuid4(), uuid4()
        db.execute(
            metadata.tables["parent_gallery"]
            .insert()
            .values(
                id=parent_id,
                name="Origem",
                active=True,
                created_at=instant,
            )
        )
        db.execute(
            metadata.tables["client"]
            .insert()
            .values(
                id=client_id,
                full_name="Cliente",
                phone_e164="+5511999991111",
            )
        )
        order_table = metadata.tables["sale_order"]
        db.execute(
            order_table.insert().values(
                id=uuid4(),
                client_id=client_id,
                payment_status="pending",
                total_cents=700,
                client_name_snapshot="Cliente",
                client_phone_snapshot="+5511999991111",
                derived_gallery_id_snapshot=uuid4(),
                derived_gallery_name_snapshot="Privada removida",
                parent_gallery_id_snapshot=parent_id,
                parent_gallery_name_snapshot="Origem",
                pix_copy_paste_snapshot="LEGACY-SNAPSHOT",
                pix_instructions_snapshot="Original",
                created_at=instant,
            )
        )
        if mode != "empty":
            for index in range(2):
                parent = uuid4()
                db.execute(
                    metadata.tables["parent_gallery"]
                    .insert()
                    .values(
                        id=parent,
                        name=f"Galeria {index}",
                        active=True,
                        created_at=instant,
                    )
                )
                value = code
                if mode == "invalid":
                    value = "invalid-legacy-code"
                elif mode == "different" and index:
                    value = build_static_pix_code(
                        "other@example.test", receiver_name="OUTRO", receiver_city="SAO PAULO"
                    )
                db.execute(
                    metadata.tables["pix_checkout_settings"]
                    .insert()
                    .values(
                        id=uuid4(),
                        parent_gallery_id=parent,
                        copy_paste=value,
                        input_type="email" if mode == "same" and index == 0 else "br_code",
                        pix_key="foto@example.test" if mode == "same" and index == 0 else None,
                        receiver_name="MARKINA" if mode == "same" and index == 0 else None,
                        receiver_city="SAO PAULO" if mode == "same" and index == 0 else None,
                        instructions="Aguarde",
                        review_required=False,
                        updated_at=instant,
                    )
                )
        before_orders = list(db.execute(sa.select(order_table)).mappings())
        before_legacy = list(
            db.execute(sa.select(metadata.tables["pix_checkout_settings"])).mappings()
        )
    alembic(url, "upgrade", "head")
    with engine.connect() as db:
        row = db.execute(
            sa.text("SELECT status, copy_paste, version FROM global_pix_settings")
        ).one()
        assert row.status == expected
        assert row.copy_paste == (code if expected == "active" else None)
        assert row.version == (1 if expected == "active" else 0)
        assert list(db.execute(sa.select(order_table)).mappings()) == before_orders
        assert (
            list(db.execute(sa.select(metadata.tables["pix_checkout_settings"])).mappings())
            == before_legacy
        )
    if mode == "same":
        current = sa.Table("sale_order", sa.MetaData(), autoload_with=engine)
        with engine.begin() as db:
            db.execute(current.update().values(pix_configuration_snapshot={"version": 1}))
        refused = alembic(url, "downgrade", "20260906_0045", succeeds=False)
        assert "Preserve os snapshots PIX globais" in refused.stderr
        with engine.begin() as db:
            assert db.scalar(sa.select(current.c.pix_configuration_snapshot)) == {"version": 1}
            db.execute(current.update().values(pix_configuration_snapshot=sa.null()))
    alembic(url, "downgrade", "20260906_0045")
    with engine.connect() as db:
        assert list(db.execute(sa.select(order_table)).mappings()) == before_orders
        assert (
            list(db.execute(sa.select(metadata.tables["pix_checkout_settings"])).mappings())
            == before_legacy
        )
    engine.dispose()
