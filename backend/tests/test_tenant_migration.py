"""Ensaia a cadeia real Alembic em PostgreSQL descartável e SQLite."""

import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app import auth
from tests.tenant_fixtures import insert_legacy_model as insert_model


@pytest.fixture(params=["sqlite", "postgresql"])
def migration_database(request, tmp_path):
    if request.param == "sqlite":
        url = f"sqlite:///{(tmp_path / 'migration.sqlite').as_posix()}"
        yield url
        return
    url = os.getenv("TENANT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("TENANT_TEST_DATABASE_URL não configurada")
    parsed = sa.engine.make_url(url)
    assert parsed.host == "127.0.0.1" and parsed.port == 55469
    assert parsed.database == "pyp_tenant_test"
    control = sa.create_engine(parsed, isolation_level="AUTOCOMMIT")
    database = f"tenant_migration_{uuid4().hex}"
    with control.connect() as connection:
        connection.execute(sa.text(f'CREATE DATABASE "{database}"'))
    yield parsed.set(database=database).render_as_string(hide_password=False)
    with control.connect() as connection:
        connection.execute(sa.text(f'DROP DATABASE "{database}"'))
    control.dispose()


def migrate(url, *args, succeeds=True):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "DATABASE_URL": url}, capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == succeeds, result.stderr
    return result


def legacy(connection):
    admin, client, parent, gallery, folder, photo, order = (uuid4() for _ in range(7))
    insert_model(connection, auth.AdminUser, id=admin, email="fake@example.test",
                 password_hash="synthetic-hash", totp_secret="synthetic-totp", email_verified=True)
    insert_model(connection, auth.AuthSession, id=uuid4(), role="admin", subject_id=admin,
                 token_hash="synthetic-session-hash", expires_at=auth.now() + timedelta(days=7))
    insert_model(connection, auth.Client, id=client, full_name="Sintético", phone_e164="+5511999999999")
    insert_model(connection, auth.ParentGallery, id=parent, name="Origem")
    insert_model(connection, auth.DerivedGallery, id=gallery, parent_gallery_id=parent,
                 client_id=client, name="Privada")
    insert_model(connection, auth.PhotoFolder, id=folder, parent_gallery_id=parent,
                 derived_gallery_id=gallery, name="Lote")
    insert_model(connection, auth.PhotoAsset, id=photo, parent_gallery_id=parent,
                 derived_gallery_id=gallery, folder_id=folder, filename="fake.jpg",
                 storage_key="private/fake.jpg")
    insert_model(connection, auth.SaleOrder, id=order, client_id=client,
                 derived_gallery_id_snapshot=gallery, derived_gallery_name_snapshot="Privada",
                 parent_gallery_id_snapshot=parent, parent_gallery_name_snapshot="Origem",
                 payment_status="confirmed", total_cents=15300)
    return admin, parent, gallery, photo


def test_upgrade_vazio(migration_database):
    migrate(migration_database, "upgrade", "head")
    engine = sa.create_engine(migration_database, poolclass=sa.pool.NullPool)
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM tenant WHERE status='active'")) == 1
        assert connection.scalar(sa.text("SELECT count(*) FROM tenant_admin")) == 0
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "20260929_0069"
    engine.dispose()


def test_upgrade_preserva_legado_e_acesso(migration_database):
    migrate(migration_database, "upgrade", "20260928_0068")
    engine = sa.create_engine(migration_database, poolclass=sa.pool.NullPool)
    with engine.begin() as connection:
        legacy(connection)
        tables = sa.MetaData()
        tables.reflect(connection)
        before = {name: connection.execute(table.select()).all()
                  for name, table in tables.tables.items() if name != "alembic_version"}
    migrate(migration_database, "upgrade", "head")
    with engine.connect() as connection:
        for name, rows in before.items():
            assert connection.execute(tables.tables[name].select()).all() == rows, name
        owner = connection.scalar(sa.text("SELECT id FROM tenant"))
        for name in ("parent_gallery", "derived_gallery", "photo_asset", "tenant_admin"):
            assert connection.scalar(sa.text(f"SELECT tenant_id FROM {name}")) == owner
            assert connection.scalar(sa.text(f"SELECT count(*) FROM {name} WHERE tenant_id IS NULL")) == 0
    result = migrate(migration_database, "downgrade", "20260928_0068", succeeds=False)
    assert "Preserve o schema" in result.stderr
    engine.dispose()


def test_upgrade_inconsistente_sem_alteracao_parcial(migration_database):
    migrate(migration_database, "upgrade", "20260928_0068")
    engine = sa.create_engine(migration_database, poolclass=sa.pool.NullPool)
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(sa.text("SET LOCAL session_replication_role=replica"))
        admin, _, _, _ = legacy(connection)
        insert_model(connection, auth.DerivedGallery, id=uuid4(), parent_gallery_id=uuid4(),
                     client_id=connection.scalar(sa.text("SELECT id FROM client")), name="Órfã")
    result = migrate(migration_database, "upgrade", "head", succeeds=False)
    assert "Acervo inconsistente" in result.stderr
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "20260928_0068"
        assert "tenant" not in sa.inspect(connection).get_table_names()
        assert "tenant_id" not in {c["name"] for c in sa.inspect(connection).get_columns("parent_gallery")}
        table = sa.Table("admin_user", sa.MetaData(), autoload_with=connection)
        expected = admin.hex if engine.dialect.name == "sqlite" else admin
        assert connection.scalar(sa.select(table.c.id)) == expected
    engine.dispose()


def test_limpeza_preserva_admin_conta_sessao_e_canal(migration_database, monkeypatch, tmp_path):
    if migration_database.startswith("sqlite"):
        pytest.skip("Limpeza homologada requer PostgreSQL")
    from sqlalchemy.orm import Session

    from app import homolog_cleanup

    migrate(migration_database, "upgrade", "head")
    engine = sa.create_engine(migration_database, poolclass=sa.pool.NullPool)
    monkeypatch.setenv("APP_ENV", "homolog")
    roots = {name: tmp_path / name for name in homolog_cleanup.EXPECTED_MEDIA_ROOTS}
    monkeypatch.setattr(homolog_cleanup, "EXPECTED_MEDIA_ROOTS", roots)
    for name, setting in (
        ("source", "MEDIA_SOURCE_ROOT"), ("derivatives", "MEDIA_DERIVATIVES_ROOT"),
        ("history", "MEDIA_HISTORY_ROOT"), ("facial_references", "FACIAL_REFERENCE_ROOT"),
    ):
        roots[name].mkdir()
        (roots[name] / "fake.jpg").write_bytes(b"synthetic")
        monkeypatch.setenv(setting, str(roots[name]))
    with Session(engine, expire_on_commit=False) as db:
        tenant = db.scalar(sa.select(auth.Tenant))
        admin = auth.AdminUser(email="clean@example.test", password_hash="synthetic",
                               totp_secret="synthetic", email_verified=True)
        admin.tenant_memberships.append(auth.TenantAdmin(tenant_id=tenant.id))
        db.add(admin)
        db.flush()
        session = auth.AuthSession(role="admin", subject_id=admin.id, token_hash="synthetic",
                                   expires_at=auth.now() + timedelta(days=7))
        channel = auth.WhatsAppChannelSettings(environment="homolog", status="ready")
        parent = auth.ParentGallery(name="Descartável", tenant_id=tenant.id)
        db.add_all([session, channel, parent])
        db.commit()
        before = homolog_cleanup.inventory(db)
        result = homolog_cleanup.execute(db, homolog_cleanup.CONFIRMATION)
        assert result["preserved"] == before["preserved"]
        assert all(count == 0 for count in result["database"].values())
        db.expire_all()
        assert db.get(auth.AdminUser, admin.id).totp_secret == "synthetic"
        assert db.get(auth.AuthSession, session.id) is not None
        assert db.get(auth.Tenant, tenant.id).status == "active"
        assert db.scalar(sa.select(auth.TenantAdmin)).active
        assert db.scalar(sa.select(auth.WhatsAppChannelSettings)) is not None
    engine.dispose()
