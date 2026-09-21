"""Ensaio aditivo em banco descartável, sem reclassificar compras antigas."""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import sqlalchemy as sa

from tests.test_global_pix_migration import alembic


def test_unified_migration_preserves_legacy_and_enforces_owner(tmp_path):
    url = (
        os.getenv("UNIFIED_PIX_MIGRATION_TEST_URL")
        or f"sqlite:///{(tmp_path / 'unified.sqlite').as_posix()}"
    )
    if os.getenv("UNIFIED_PIX_MIGRATION_TEST_URL"):
        parsed = sa.engine.make_url(url)
        assert parsed.host == "127.0.0.1" and parsed.port == 55458
        assert parsed.database == "markina_unified_migration_test"
    alembic(url, "upgrade", "20260919_0057")
    engine = sa.create_engine(url)
    legacy, client, other = (uuid4().hex for _ in range(3))
    instant = datetime.now(UTC)
    with engine.begin() as db:
        db.execute(
            sa.text(
                "INSERT INTO client (id, full_name, phone_e164) VALUES "
                "(:id, 'Cliente', '+5511999990000'), "
                "(:other, 'Outra', '+5511999990001')"
            ),
            {"id": client, "other": other},
        )
        db.execute(
            sa.text(
                "INSERT INTO sale_order "
                "(id, client_id, derived_gallery_id_snapshot, derived_gallery_name_snapshot, "
                "parent_gallery_id_snapshot, parent_gallery_name_snapshot, payment_status, "
                "total_cents, created_at, pix_copy_paste_snapshot) VALUES "
                "(:id, :client, :gallery, 'Privada removida', :parent, 'Evento', "
                "'confirmed', 700, :instant, 'SNAPSHOT ORIGINAL')"
            ),
            {
                "id": legacy,
                "client": client,
                "gallery": uuid4().hex,
                "parent": uuid4().hex,
                "instant": instant,
            },
        )
    alembic(url, "upgrade", "head")
    with engine.connect() as db:
        assert db.execute(
            sa.text(
                "SELECT payment_group_id, payment_status, total_cents, "
                "pix_copy_paste_snapshot FROM sale_order"
            )
        ).one() == (None, "confirmed", 700, "SNAPSHOT ORIGINAL")
    alembic(url, "downgrade", "20260919_0057")
    alembic(url, "upgrade", "head")
    group = uuid4().hex
    with engine.begin() as db:
        if engine.dialect.name == "sqlite":
            db.exec_driver_sql("PRAGMA foreign_keys=ON")
        db.execute(
            sa.text(
                "INSERT INTO payment_group "
                "(id, client_id, state, revision, total_cents, pix_copy_paste_snapshot, "
                "pix_configuration_snapshot, created_at) VALUES "
                "(:id, :client, 'draft', 'revision', 700, 'PIX', '{}', :instant)"
            ),
            {"id": group, "client": other, "instant": instant},
        )
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as db:
        if engine.dialect.name == "sqlite":
            db.exec_driver_sql("PRAGMA foreign_keys=ON")
        db.execute(
            sa.text("UPDATE sale_order SET payment_group_id=:group WHERE id=:id"),
            {"group": group, "id": legacy},
        )
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as db:
        db.execute(
            sa.text(
                "INSERT INTO payment_group SELECT :id, client_id, state, revision, "
                "total_cents, pix_copy_paste_snapshot, pix_instructions_snapshot, "
                "pix_configuration_snapshot, created_at, reported_at FROM payment_group"
            ),
            {"id": uuid4().hex},
        )
    alembic(url, "downgrade", "20260919_0057", succeeds=False)
    engine.dispose()
