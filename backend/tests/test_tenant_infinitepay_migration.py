"""Migration InfinitePay em bancos próprios, preservando PIX e seu histórico."""

import os
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app import auth
from tests.tenant_fixtures import insert_legacy_model
from tests.test_global_pix_migration import alembic

SOURCE = "20261011_0074"
TARGET = "20261012_0075"


@pytest.fixture
def migration_database(tmp_path):
    url = os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL")
    maintenance = None
    if url:
        parsed = sa.engine.make_url(url)
        assert (parsed.host, parsed.port, parsed.database) == (
            "127.0.0.1", 15470, "pyp_photographer_test")
        name = f"infinitepay_migration_{uuid4().hex}"
        maintenance = sa.create_engine(url, isolation_level="AUTOCOMMIT")
        with maintenance.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
        url = parsed.set(database=name).render_as_string(hide_password=False)
    else:
        url = f"sqlite:///{(tmp_path / 'migration.sqlite').as_posix()}"
    engine = sa.create_engine(url)
    try:
        yield url, engine
    finally:
        engine.dispose()
        if maintenance is not None:
            with maintenance.connect() as connection:
                connection.exec_driver_sql(f'DROP DATABASE "{name}"')
            maintenance.dispose()


def snapshots(engine):
    with engine.connect() as connection:
        return {table: [tuple(row) for row in connection.execute(sa.text(f"SELECT * FROM {table}"))]
                for table in ("global_pix_settings", "sale_order", "admin_security_challenge")}


@pytest.mark.parametrize("legacy", [False, True])
def test_upgrade_e_downgrade_vazios_preservam_pix_e_snapshots(migration_database, legacy):
    url, engine = migration_database
    alembic(url, "upgrade", SOURCE)
    if legacy:
        with Session(engine) as db:
            tenant = auth.Tenant()
            admin = auth.AdminUser(email="synthetic@example.test", password_hash="synthetic",
                                   totp_secret="synthetic")
            db.add_all([tenant, admin])
            db.flush()
            client = auth.Client(tenant_id=tenant.id, full_name="Sintética",
                                 phone_e164="+5511999990010")
            db.add_all([auth.TenantAdmin(tenant_id=tenant.id, admin_user_id=admin.id), client])
            db.flush()
            db.add(auth.GlobalPixSettings(tenant_id=tenant.id, admin_user_id=admin.id,
                   version=7, status="active", copy_paste="synthetic-pix-preserved"))
            insert_legacy_model(db.connection(), auth.SaleOrder, tenant_id=tenant.id, client_id=client.id, total_cents=700,
                   pix_copy_paste_snapshot="synthetic-old-snapshot", payment_status="confirmed",
                   derived_gallery_id_snapshot=uuid4(), derived_gallery_name_snapshot="Histórica",
                   parent_gallery_id_snapshot=uuid4(), parent_gallery_name_snapshot="Origem histórica")
            db.commit()
    before = snapshots(engine)
    alembic(url, "upgrade", TARGET)
    assert snapshots(engine) == before
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM infinitepay_settings")) == 0
        checks = {item["name"] for item in sa.inspect(connection).get_check_constraints("admin_security_challenge")}
        assert {"ck_admin_challenge_pix_context", "ck_admin_challenge_infinitepay_context"} <= checks
        actual = {item["name"] for item in sa.inspect(connection).get_foreign_keys("infinitepay_settings")}
        expected = {c.name for c in auth.InfinitePaySettings.__table__.foreign_key_constraints if c.name}
        assert expected <= actual
    alembic(url, "downgrade", SOURCE)
    assert snapshots(engine) == before
    with engine.connect() as connection:
        assert not sa.inspect(connection).has_table("infinitepay_settings")


def test_downgrade_recusa_configuracao_existente(migration_database):
    url, engine = migration_database
    alembic(url, "upgrade", TARGET)
    with Session(engine) as db:
        tenant = auth.Tenant()
        admin = auth.AdminUser(email="synthetic@example.test", password_hash="synthetic",
                               totp_secret="synthetic")
        db.add_all([tenant, admin])
        db.flush()
        db.add(auth.TenantAdmin(tenant_id=tenant.id, admin_user_id=admin.id))
        db.flush()
        setting = auth.InfinitePaySettings(tenant_id=tenant.id, admin_user_id=admin.id,
                                          handle="synthetic", version=2)
        db.add(setting)
        db.commit()
        setting_id = setting.id
    result = alembic(url, "downgrade", SOURCE, succeeds=False)
    assert "preserve configurações e desafios InfinitePay auditáveis" in result.stderr
    with Session(engine) as db:
        assert db.get(auth.InfinitePaySettings, setting_id).version == 2
        assert db.scalar(sa.text("SELECT version_num FROM alembic_version")) == TARGET
