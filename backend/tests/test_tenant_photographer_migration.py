"""Cadeia Alembic e rollback da transição, somente em bancos sintéticos próprios."""

import importlib.util
import os
import re
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app import auth
from app.ownership_schema import SHARED_TABLES
from tests.tenant_fixtures import insert_legacy_model as insert_model

BACKEND = Path(__file__).resolve().parents[1]
FOUNDATION = "20260929_0069"
TRANSITION = "20260930_0070"


def migrate(url, revision, *, downgrade=False, succeeds=True):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade" if downgrade else "upgrade", revision],
        cwd=BACKEND, env={**os.environ, "DATABASE_URL": url}, capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == succeeds, result.stderr
    return result


@pytest.fixture(scope="module")
def baseline_template():
    url = os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL")
    if not url:
        pytest.skip("PHOTOGRAPHER_TEST_DATABASE_URL não configurada")
    parsed = sa.engine.make_url(url)
    assert parsed.host == "127.0.0.1" and parsed.port == 15470
    assert parsed.database == "pyp_photographer_test"
    control = sa.create_engine(parsed, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    name = f"pilot_template_{uuid4().hex}"
    with control.connect() as connection:
        connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
    try:
        migrate(parsed.set(database=name).render_as_string(hide_password=False), FOUNDATION)
        yield parsed, name, control
    finally:
        with control.connect() as connection:
            connection.execute(sa.text(f'DROP DATABASE "{name}"'))
        control.dispose()


@pytest.fixture
def migration_db(baseline_template):
    parsed, template, control = baseline_template
    name = f"pilot_migration_{uuid4().hex}"
    with control.connect() as connection:
        connection.execute(sa.text(f'CREATE DATABASE "{name}" TEMPLATE "{template}"'))
    url = parsed.set(database=name).render_as_string(hide_password=False)
    engine = sa.create_engine(url, poolclass=NullPool)
    try:
        yield url, engine
    finally:
        engine.dispose()
        with control.connect() as connection:
            connection.execute(sa.text(f'DROP DATABASE "{name}"'))


def snapshot(connection):
    metadata = sa.MetaData()
    metadata.reflect(connection)
    return metadata, {
        name: sorted((tuple(row) for row in connection.execute(table.select())), key=repr)
        for name, table in metadata.tables.items()
    }


def assert_preserved(connection, before):
    metadata, rows = before
    for name, old in rows.items():
        if name == "alembic_version":
            continue
        after = sorted((tuple(row) for row in connection.execute(metadata.tables[name].select())), key=repr)
        assert after == old, name


def assert_catalog(connection):
    inspector = sa.inspect(connection)
    for name, target in auth.Base.metadata.tables.items():
        # Esta conferência é da revision 0070, anterior ao privilégio técnico 0071.
        if name == "installation_operator":
            continue
        actual_columns = {column["name"]: column for column in inspector.get_columns(name)}
        assert set(actual_columns) == set(target.c.keys()), name
        assert all(actual_columns[column.name]["nullable"] == column.nullable for column in target.c), name
        actual_fk = {
            (tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
            for f in inspector.get_foreign_keys(name)
        }
        expected_fk = {
            (tuple(e.parent.name for e in f.elements), f.referred_table.name, tuple(e.column.name for e in f.elements))
            for f in target.foreign_key_constraints
        }
        assert actual_fk == expected_fk, name
        assert set(inspector.get_pk_constraint(name)["constrained_columns"]) == set(target.primary_key.columns.keys())
        actual_unique = {tuple(u["column_names"]) for u in inspector.get_unique_constraints(name)}
        expected_unique = {tuple(column.name for column in u.columns)
                           for u in target.constraints if isinstance(u, sa.UniqueConstraint)}
        assert actual_unique == expected_unique, name
        actual_indexes = {i["name"]: (tuple(i["column_names"]), i["unique"])
                          for i in inspector.get_indexes(name) if not i.get("duplicates_constraint")}
        expected_indexes = {i.name: (tuple(column.name for column in i.columns), i.unique) for i in target.indexes}
        assert expected_indexes.items() <= actual_indexes.items(), name
        # Índices legados não únicos podem ser preservados mesmo quando não
        # declarados no ORM; nenhuma unicidade global extra pode sobreviver.
        assert all(not unique for key, (_, unique) in actual_indexes.items() if key not in expected_indexes), name
        by_name = {i["name"]: i for i in inspector.get_indexes(name)}
        for index in target.indexes:
            expected_where = index.dialect_kwargs.get("postgresql_where")
            if expected_where is None:
                continue
            expression = str(expected_where.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
            actual_where = by_name[index.name].get("dialect_options", {}).get("postgresql_where")
            normalize = lambda sql: re.sub(r"[()\s]", "", str(sql).replace("::text", "")).lower()
            assert normalize(expression) == normalize(actual_where), index.name


def legacy(connection):
    owner = connection.scalar(sa.text("SELECT id FROM tenant"))
    admin, client, parent, gallery, folder, photo, order, event, session = (uuid4() for _ in range(9))
    insert_model(connection, auth.AdminUser, id=admin, email="synthetic@example.test",
                 password_hash="synthetic-hash", totp_secret="synthetic-totp", email_verified=True)
    insert_model(connection, auth.TenantAdmin, tenant_id=owner, admin_user_id=admin)
    insert_model(connection, auth.Client, id=client, full_name="Sintética", phone_e164="+5511999990001")
    insert_model(connection, auth.ClientPhone, client_id=client, phone_e164="+5511999990001",
                 verified_at=auth.now())
    insert_model(connection, auth.ParentGallery, id=parent, tenant_id=owner, name="Origem sintética")
    insert_model(connection, auth.DerivedGallery, id=gallery, tenant_id=owner, parent_gallery_id=parent,
                 client_id=client, name="Privada sintética")
    insert_model(connection, auth.PhotoFolder, id=folder, parent_gallery_id=parent, name="Lote sintético")
    insert_model(connection, auth.PhotoAsset, id=photo, tenant_id=owner, parent_gallery_id=parent,
                 folder_id=folder, filename="synthetic.jpg", storage_key="legacy/synthetic.jpg")
    connection.execute(sa.text("UPDATE parent_gallery SET cover_photo_id=:photo WHERE id=:parent"),
                       {"photo": photo, "parent": parent})
    insert_model(connection, auth.GalleryClientState, parent_gallery_id=parent, client_id=client)
    insert_model(connection, auth.PhotoSelection, parent_gallery_id=parent, client_id=client, photo_asset_id=photo)
    insert_model(connection, auth.GalleryAccess, gallery_id=parent, client_id=client)
    insert_model(connection, auth.GalleryAccess, gallery_id=gallery, client_id=client)
    old_capability = uuid4()
    insert_model(connection, auth.GalleryAccessCapability, id=old_capability, parent_gallery_id=parent,
                 scope="public_gallery", token_hash="a" * 64, status="revoked", actor_admin_id=admin)
    insert_model(connection, auth.GalleryAccessCapability, parent_gallery_id=parent,
                 scope="public_gallery", token_hash="b" * 64, rotated_from_id=old_capability, actor_admin_id=admin)
    insert_model(connection, auth.SaleOrder, id=order, client_id=client, parent_gallery_id=parent,
                 parent_gallery_id_snapshot=parent, parent_gallery_name_snapshot="Origem sintética",
                 derived_gallery_name_snapshot="Sintética", payment_status="confirmed", total_cents=12345)
    insert_model(connection, auth.SaleOrderItem, sale_order_id=order, photo_asset_id=photo,
                 photo_asset_id_snapshot=photo, filename_snapshot="synthetic.jpg", unit_price_cents=12345)
    insert_model(connection, auth.GlobalPixSettings, admin_user_id=admin, status="active", copy_paste="synthetic-pix")
    insert_model(connection, auth.BrandingSettings, login_title="Marca sintética", logo_key="legacy/synthetic-logo.png")
    connection.execute(sa.text("UPDATE preview_adjustment_settings SET generation=3, strength=25 WHERE id=1"))
    insert_model(connection, auth.AssetFileCleanup, paths=["legacy/synthetic.jpg"])
    insert_model(connection, auth.GalleryMembershipNotificationOutbox, parent_gallery_id=None,
                 event_key="synthetic-orphan-history", event_type="private_created",
                 parent_name_snapshot="Origem removida", derived_name_snapshot="Privada removida")
    insert_model(connection, auth.MediaJob, photo_asset_id=photo, kind="generate_derivatives")
    insert_model(connection, auth.FacialJob, parent_gallery_id=parent, photo_asset_id=photo,
                 kind="index", idempotency_key="synthetic-facial")
    setting = connection.scalar(sa.text("SELECT event_type FROM notification_setting LIMIT 1"))
    insert_model(connection, auth.NotificationEvent, id=event, event_type=setting, event_key="synthetic-event",
                 parent_gallery_id=parent, client_id=client, template_version=1, push_title="Sintética",
                 push_body="Sintética", whatsapp_body="Sintética", target_path="/library",
                 expires_at=auth.now() + timedelta(hours=1))
    insert_model(connection, auth.NotificationDelivery, event_id=event, recipient_role="client", recipient_id=client,
                 channel="whatsapp")
    insert_model(connection, auth.PushSubscription, role="client", subject_id=client,
                 endpoint_fingerprint="synthetic", encrypted_subscription="unchanged-synthetic-envelope")
    insert_model(connection, auth.AuthSession, id=session, role="admin", subject_id=admin,
                 token_hash="synthetic-session-hash", expires_at=auth.now() + timedelta(hours=1))
    insert_model(connection, auth.AuthSession, role="client", subject_id=client,
                 token_hash="synthetic-client-session", expires_at=auth.now() + timedelta(hours=1))
    insert_model(connection, auth.AdminSecurityChallenge, purpose="change_pix_otp", admin_id=admin, session_id=session,
                 subject_fingerprint="synthetic", secret_hash="synthetic-otp-hash",
                 expires_at=auth.now() + timedelta(minutes=1))
    insert_model(connection, auth.AuthChallenge, kind="client_otp", secret_hash="synthetic-hash",
                 expires_at=auth.now() + timedelta(minutes=1))
    return {"owner": owner, "admin": admin, "client": client, "parent": parent, "gallery": gallery, "photo": photo}


def test_upgrade_vazio_catalogo_e_defaults_preservados(migration_db):
    url, engine = migration_db
    with engine.connect() as connection:
        before = snapshot(connection)
    migrate(url, TRANSITION)
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert_catalog(connection)
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == TRANSITION
        assert connection.scalar(sa.text("SELECT count(*) FROM tenant")) == 1


def test_upgrade_preserva_todas_colunas_legadas_e_owner_duravel(migration_db):
    url, engine = migration_db
    with engine.begin() as connection:
        records = legacy(connection)
        before = snapshot(connection)
    migrate(url, TRANSITION)
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert_catalog(connection)
        for name in set(auth.Base.metadata.tables) - SHARED_TABLES:
            assert connection.scalar(sa.text(f'SELECT count(*) FROM "{name}" WHERE tenant_id IS NULL')) == 0, name
            assert connection.scalar(sa.text(f'SELECT count(*) FROM "{name}" WHERE tenant_id != :owner'),
                                     {"owner": records["owner"]}) == 0, name
        assert connection.scalar(sa.text("SELECT client_subject_id FROM auth_session WHERE role='client'")) == records["client"]


@pytest.mark.parametrize("kind", ["orphan", "ambiguous_gallery", "two_tenants", "duplicate_phone", "missing_recipient", "missing_actor"])
def test_legado_inconsistente_abortado_sem_ddl_parcial(migration_db, kind):
    url, engine = migration_db
    with engine.begin() as connection:
        records = legacy(connection)
        connection.execute(sa.text("SET LOCAL session_replication_role=replica"))
        if kind == "orphan":
            connection.execute(sa.text("UPDATE photo_folder SET parent_gallery_id=:missing"), {"missing": uuid4()})
        elif kind == "ambiguous_gallery":
            another_client = uuid4()
            insert_model(connection, auth.Client, id=another_client, full_name="Sintética ambígua",
                         phone_e164="+5511999990050")
            insert_model(connection, auth.DerivedGallery, id=records["parent"], tenant_id=records["owner"],
                         parent_gallery_id=records["parent"], client_id=another_client, name="Ambígua")
        elif kind == "two_tenants":
            insert_model(connection, auth.Tenant)
        elif kind == "duplicate_phone":
            other = uuid4()
            insert_model(connection, auth.Client, id=other, full_name="Sintética B", phone_e164="+5511999990002")
            # O índice antigo protege só verificados; ambos não verificados reproduzem a ambiguidade.
            connection.execute(sa.text("UPDATE client_phone SET verified_at=NULL"))
            insert_model(connection, auth.ClientPhone, client_id=other, phone_e164="+5511999990001")
        elif kind == "missing_recipient":
            connection.execute(sa.text("UPDATE notification_delivery SET recipient_id=:missing"), {"missing": uuid4()})
        else:
            insert_model(connection, auth.GalleryLifecycleOperation, operation_type="delete_parent_gallery",
                         target_parent_gallery_id=records["parent"], actor_admin_id=uuid4(), idempotency_key="synthetic-missing-actor")
        before = snapshot(connection)
    failure = migrate(url, TRANSITION, succeeds=False)
    assert "Legado incompatível" in failure.stderr
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == FOUNDATION
        assert "tenant_id" not in {c["name"] for c in sa.inspect(connection).get_columns("client")}


def revision_module():
    path = BACKEND / "migrations/versions/20260930_0070_photographer_isolation_schema.py"
    spec = importlib.util.spec_from_file_location("schema0070_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_falha_apos_backfill_reverte_colunas_e_dados(migration_db, monkeypatch):
    _, engine = migration_db
    with engine.begin() as connection:
        legacy(connection)
        before = snapshot(connection)
    module = revision_module()

    def fail_after_backfill(bind):
        assert bind.scalar(sa.text("SELECT count(*) FROM client WHERE tenant_id IS NOT NULL")) == 1
        bind.execute(sa.text("ALTER TABLE client ADD CONSTRAINT synthetic_rollback_probe CHECK (false)"))

    monkeypatch.setattr(module, "_apply_schema", fail_after_backfill)
    with (
        pytest.raises(sa.exc.IntegrityError),
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        module.upgrade()
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert "tenant_id" not in {c["name"] for c in sa.inspect(connection).get_columns("client")}
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == FOUNDATION


def test_sessao_sem_sujeito_revogada_sem_apagar_hash(migration_db):
    url, engine = migration_db
    identifier, subject = uuid4(), uuid4()
    with engine.begin() as connection:
        insert_model(connection, auth.AuthSession, id=identifier, role="client", subject_id=subject,
                     token_hash="synthetic-unresolved-hash", expires_at=auth.now() + timedelta(hours=1))
    migrate(url, TRANSITION)
    with engine.connect() as connection:
        row = connection.execute(sa.text("SELECT id, subject_id, token_hash, revoked_at, tenant_id FROM auth_session")).one()
        assert row.id == identifier and row.subject_id == subject and row.token_hash == "synthetic-unresolved-hash"
        assert row.revoked_at is not None and row.tenant_id is None


def test_downgrade_recusado_preserva_propriedade(migration_db):
    url, engine = migration_db
    migrate(url, TRANSITION)
    with engine.connect() as connection:
        before = snapshot(connection)
    failure = migrate(url, FOUNDATION, downgrade=True, succeeds=False)
    assert "Preserve o schema" in failure.stderr
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == TRANSITION


def test_dialeto_nao_operacional_recusado_antes_de_alterar(tmp_path):
    url = f"sqlite:///{(tmp_path / 'legacy.sqlite').as_posix()}"
    engine = sa.create_engine(url)
    with engine.begin() as connection:
        with (
            Operations.context(MigrationContext.configure(connection)),
            pytest.raises(RuntimeError, match="requer PostgreSQL"),
        ):
            revision_module().upgrade()
        assert sa.inspect(connection).get_table_names() == []
    engine.dispose()


def test_limpeza_multitenant_recusada_antes_de_midia(migration_db, monkeypatch):
    from app import homolog_cleanup
    from app.tenancy import TenantContextError

    url, engine = migration_db
    migrate(url, TRANSITION)
    with Session(engine) as db:
        db.add(auth.Tenant())
        db.commit()
        monkeypatch.setenv("APP_ENV", "homolog")
        roots = Mock(side_effect=AssertionError("Mídia não pode ser acessada"))
        monkeypatch.setattr(homolog_cleanup, "media_roots", roots)
        with pytest.raises(TenantContextError):
            homolog_cleanup.inventory(db)
        with pytest.raises(TenantContextError):
            homolog_cleanup.execute(db, homolog_cleanup.CONFIRMATION)
        roots.assert_not_called()
        db.rollback()
        assert db.scalar(sa.select(sa.func.count()).select_from(auth.Tenant)) == 2


def test_limpeza_legado_completo_preserva_administracao(migration_db, monkeypatch, tmp_path):
    from app import homolog_cleanup
    from app.provision_installation_operator import provision_operator

    url, engine = migration_db
    with engine.begin() as connection:
        records = legacy(connection)
    # A rotina atual exige o catálogo completo, incluindo o privilégio técnico 0071.
    migrate(url, "20261001_0071")
    monkeypatch.setenv("APP_ENV", "homolog")
    roots = {name: tmp_path / name for name in homolog_cleanup.EXPECTED_MEDIA_ROOTS}
    for root in roots.values():
        root.mkdir()
        (root / "synthetic.jpg").write_bytes(b"synthetic-test-only")
    monkeypatch.setattr(homolog_cleanup, "EXPECTED_MEDIA_ROOTS", roots)
    monkeypatch.setattr(homolog_cleanup, "media_roots", lambda: roots)
    with Session(engine) as db:
        provision_operator(db, admin_id=records["admin"], action="grant",
                           authorization_reference="synthetic-cleanup-proof", apply=True)
        db.commit()
        before = homolog_cleanup.inventory(db)
        result = homolog_cleanup.execute(db, homolog_cleanup.CONFIRMATION)
        assert result["preserved"] == before["preserved"]
        assert all(value == 0 for value in result["database"].values())
        assert all(value["files"] == 0 for value in result["media"].values())
        assert db.get(auth.InstallationOperator, records["admin"]).active
        assert db.scalar(sa.select(auth.AuditEvent.id).where(
            auth.AuditEvent.event == "installation_operator.grant"))
