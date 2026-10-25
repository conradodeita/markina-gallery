"""Migração expansiva em banco sintético próprio, com legado financeiro preservado."""

from uuid import uuid4

import pytest
import sqlalchemy as sa

from app import auth
from tests.payment_migration_fixtures import payment_migration_database as _migration_database
from tests.tenant_fixtures import insert_legacy_model
from tests.test_global_pix_migration import alembic

migration_database = _migration_database
SOURCE = "20261012_0075"
TARGET = "20261012_0076"
# Contrato histórico de 0076: a credencial só é acrescentada em 0085.
PAYMENT_COLUMNS_0076 = {
    "id", "tenant_id", "client_id", "provider", "checkout_key", "cart_revision", "total_cents",
    "handle_snapshot", "configuration_version", "verification_profile", "state", "revision_number",
    "checkout_url", "provider_transaction_nsu", "confirmed_at", "created_at", "updated_at",
}
PAYMENT_FOREIGN_KEYS_0076 = {
    (("tenant_id",), "tenant", ("id",)),
    (("client_id",), "client", ("id",)),
    (("client_id", "tenant_id"), "client", ("id", "tenant_id")),
}


@pytest.mark.parametrize("legacy", [False, True])
def test_schema_e_rollback_vazio_preservam_colunas_legadas(migration_database, legacy):
    url, engine = migration_database
    alembic(url, "upgrade", SOURCE)
    with engine.begin() as conn:
        if legacy:
            tenant_id, admin_id, client_id = uuid4(), uuid4(), uuid4()
            insert_legacy_model(conn, auth.Tenant, id=tenant_id)
            insert_legacy_model(conn, auth.AdminUser, id=admin_id, email="synthetic@example.test",
                                password_hash="synthetic", totp_secret="synthetic")
            insert_legacy_model(conn, auth.TenantAdmin, tenant_id=tenant_id, admin_user_id=admin_id)
            insert_legacy_model(conn, auth.Client, id=client_id, tenant_id=tenant_id,
                                full_name="Sintética", phone_e164="+5511999990001")
            insert_legacy_model(conn, auth.SaleOrder, tenant_id=tenant_id, client_id=client_id,
                total_cents=1700, payment_status="confirmed", pix_copy_paste_snapshot="PIX preservado",
                derived_gallery_id_snapshot=uuid4(), derived_gallery_name_snapshot="Galeria antiga",
                parent_gallery_id_snapshot=uuid4(), parent_gallery_name_snapshot="Origem antiga")
        order = sa.Table("sale_order", sa.MetaData(), autoload_with=conn)
        before = list(conn.execute(order.select()))
    alembic(url, "upgrade", TARGET)
    with engine.connect() as conn:
        assert list(conn.execute(order.select())) == before
        assert conn.scalar(sa.text("SELECT COUNT(*) FROM sale_order WHERE provider_payment_id IS NOT NULL")) == 0
        inspector = sa.inspect(conn)
        for name in ("provider_payment", "provider_payment_attempt", "provider_payment_receipt"):
            target = auth.Base.metadata.tables[name]
            columns = PAYMENT_COLUMNS_0076 if name == "provider_payment" else set(target.c.keys())
            assert {c["name"] for c in inspector.get_columns(name)} == columns
            assert {tuple(u["column_names"]) for u in inspector.get_unique_constraints(name)} == {
                tuple(c.name for c in u.columns) for u in target.constraints if isinstance(u, sa.UniqueConstraint)}
            foreign_keys = PAYMENT_FOREIGN_KEYS_0076 if name == "provider_payment" else {
                (tuple(e.parent.name for e in f.elements), f.referred_table.name, tuple(e.column.name for e in f.elements))
                for f in target.foreign_key_constraints}
            assert {(tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
                    for f in inspector.get_foreign_keys(name)} == foreign_keys
    alembic(url, "downgrade", SOURCE)
    with engine.connect() as conn:
        assert list(conn.execute(order.select())) == before
        assert not sa.inspect(conn).has_table("provider_payment")


def test_downgrade_com_compra_recusado_sem_perda(migration_database):
    url, engine = migration_database
    alembic(url, "upgrade", TARGET)
    with engine.begin() as conn:
        tenant_id, client_id = uuid4(), uuid4()
        insert_legacy_model(conn, auth.Tenant, id=tenant_id)
        insert_legacy_model(conn, auth.Client, id=client_id, tenant_id=tenant_id,
                            full_name="Sintética", phone_e164="+5511999990001")
        insert_legacy_model(conn, auth.ProviderPayment, tenant_id=tenant_id, client_id=client_id,
            checkout_key="synthetic", cart_revision="a"*64, total_cents=1000, handle_snapshot="synthetic",
            configuration_version=1, verification_profile="synthetic-only")
    result = alembic(url, "downgrade", SOURCE, succeeds=False)
    assert "preserve compras e evidências de cartão" in result.stderr
    with engine.connect() as conn:
        assert conn.scalar(sa.text("SELECT COUNT(*) FROM provider_payment")) == 1
        assert conn.scalar(sa.text("SELECT version_num FROM alembic_version")) == TARGET
