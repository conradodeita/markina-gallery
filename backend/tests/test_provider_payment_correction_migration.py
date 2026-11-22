"""Migração do histórico append-only de correções em banco sintético."""

from uuid import uuid4

import sqlalchemy as sa

from app import auth
from tests.payment_migration_fixtures import payment_migration_database as _migration_database
from tests.tenant_fixtures import insert_legacy_model
from tests.test_global_pix_migration import alembic

migration_database = _migration_database
SOURCE = "20261012_0076"
TARGET = "20261014_0080"


def test_upgrade_e_downgrade_vazios_preservam_compras(migration_database):
    url, engine = migration_database
    alembic(url, "upgrade", SOURCE)
    with engine.begin() as conn:
        tenant_id, admin_id, client_id = uuid4(), uuid4(), uuid4()
        insert_legacy_model(conn, auth.Tenant, id=tenant_id)
        insert_legacy_model(conn, auth.AdminUser, id=admin_id, email="synthetic@example.test",
                            password_hash="synthetic", totp_secret="synthetic")
        insert_legacy_model(conn, auth.TenantAdmin, tenant_id=tenant_id, admin_user_id=admin_id)
        insert_legacy_model(conn, auth.Client, id=client_id, tenant_id=tenant_id,
                            full_name="Sintética", phone_e164="+5511999990091")
        payment_id = uuid4()
        insert_legacy_model(conn, auth.ProviderPayment, id=payment_id, tenant_id=tenant_id,
            client_id=client_id, checkout_key="synthetic", cart_revision="a"*64,
            total_cents=1000, handle_snapshot="synthetic", configuration_version=1,
            verification_profile="synthetic-only", state="confirmed",
            provider_transaction_nsu="synthetic-transaction", confirmed_at=auth.now())
    alembic(url, "upgrade", TARGET)
    with engine.connect() as conn:
        inspector = sa.inspect(conn)
        table = auth.ProviderPaymentCorrection.__table__
        assert {column["name"] for column in inspector.get_columns(table.name)} == set(table.c.keys())
        assert conn.scalar(sa.text("SELECT COUNT(*) FROM provider_payment")) == 1
        assert conn.scalar(sa.text("SELECT COUNT(*) FROM provider_payment_correction")) == 0
    alembic(url, "downgrade", SOURCE)
    with engine.connect() as conn:
        assert conn.scalar(sa.text("SELECT COUNT(*) FROM provider_payment")) == 1
        assert not sa.inspect(conn).has_table("provider_payment_correction")


def test_downgrade_com_correcao_recusa_apagar_historico(migration_database):
    url, engine = migration_database
    alembic(url, "upgrade", TARGET)
    with engine.begin() as conn:
        tenant_id, admin_id, client_id, payment_id = uuid4(), uuid4(), uuid4(), uuid4()
        insert_legacy_model(conn, auth.Tenant, id=tenant_id)
        insert_legacy_model(conn, auth.AdminUser, id=admin_id, email="synthetic@example.test",
                            password_hash="synthetic", totp_secret="synthetic")
        insert_legacy_model(conn, auth.TenantAdmin, tenant_id=tenant_id, admin_user_id=admin_id)
        insert_legacy_model(conn, auth.Client, id=client_id, tenant_id=tenant_id,
                            full_name="Sintética", phone_e164="+5511999990092")
        insert_legacy_model(conn, auth.ProviderPayment, id=payment_id, tenant_id=tenant_id,
            client_id=client_id, checkout_key="synthetic", cart_revision="a"*64,
            total_cents=1000, handle_snapshot="synthetic", configuration_version=1,
            verification_profile="synthetic-only", state="confirmed",
            provider_transaction_nsu="synthetic-transaction", confirmed_at=auth.now())
        insert_legacy_model(conn, auth.ProviderPaymentCorrection, tenant_id=tenant_id,
            client_id=client_id, payment_id=payment_id, actor_admin_id=admin_id,
            idempotency_key="synthetic-correction", reason="Teste sintético",
            previous_revision=1, previous_transaction_nsu="synthetic-transaction")
    result = alembic(url, "downgrade", SOURCE, succeeds=False)
    assert "preserve histórico de correções financeiras" in result.stderr
    with engine.connect() as conn:
        assert conn.scalar(sa.text("SELECT COUNT(*) FROM provider_payment_correction")) == 1
        assert conn.scalar(sa.text("SELECT version_num FROM alembic_version")) == TARGET
