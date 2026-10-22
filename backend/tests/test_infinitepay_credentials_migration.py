"""Schema expansivo em PostgreSQL descartável, sem segredo real."""

import os
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app import auth
from tests.tenant_fixtures import insert_legacy_model
from tests.test_global_pix_migration import alembic
from tests.test_tenant_infinitepay_migration import migration_database  # noqa: F401

SOURCE = "20261017_0084"
TARGET = "20261020_0085"
pytestmark = pytest.mark.skipif(not os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL"), reason="Exige PostgreSQL descartável")


def test_upgrade_legacy_preservation_and_empty_downgrade(migration_database):  # noqa: F811
    url, engine = migration_database
    alembic(url, "upgrade", SOURCE)
    with engine.begin() as conn:
        tenant, admin = uuid4(), uuid4()
        insert_legacy_model(conn, auth.Tenant, id=tenant, status="active")
        insert_legacy_model(conn, auth.AdminUser, id=admin, email="synthetic@example.test",
                            password_hash="synthetic", totp_secret="synthetic")
        insert_legacy_model(conn, auth.TenantAdmin, tenant_id=tenant, admin_user_id=admin)
        insert_legacy_model(conn, auth.InfinitePaySettings, id=uuid4(), tenant_id=tenant,
                            admin_user_id=admin, version=4, handle="legacy", status="pending")
        before = [tuple(row) for row in conn.execute(sa.text("SELECT id, tenant_id, handle, version FROM infinitepay_settings"))]
    alembic(url, "upgrade", TARGET)
    with engine.connect() as conn:
        assert [tuple(row) for row in conn.execute(sa.text("SELECT id, tenant_id, handle, version FROM infinitepay_settings"))] == before
        assert conn.scalar(sa.text("SELECT credential_source FROM infinitepay_settings")) == "server_binding"
        assert conn.scalar(sa.text("SELECT count(*) FROM infinitepay_credential")) == 0
        for table, name in (("infinitepay_settings", "fk_infinitepay_settings_credential_owner"),
                            ("provider_payment", "fk_provider_payment_credential_owner")):
            fk = next(f for f in sa.inspect(conn).get_foreign_keys(table) if f["name"] == name)
            assert fk["constrained_columns"] == ["credential_id", "tenant_id"]
            assert fk["referred_columns"] == ["id", "tenant_id"]
        second, second_admin, client, credential = uuid4(), uuid4(), uuid4(), uuid4()
        insert_legacy_model(conn, auth.Tenant, id=second, status="active")
        insert_legacy_model(conn, auth.AdminUser, id=second_admin, email="other@example.test",
                            password_hash="synthetic", totp_secret="synthetic")
        insert_legacy_model(conn, auth.TenantAdmin, tenant_id=second, admin_user_id=second_admin)
        insert_legacy_model(conn, auth.Client, id=client, tenant_id=second, full_name="Sintética",
                            phone_e164="+5511999990001")
        insert_legacy_model(conn, auth.InfinitePayCredential, id=credential, tenant_id=tenant,
                            environment="development", key_id="synthetic", nonce=b"n" * 12,
                            ciphertext=b"synthetic-envelope", created_at=auth.now())
        with pytest.raises(sa.exc.IntegrityError), conn.begin_nested():
            insert_legacy_model(conn, auth.InfinitePaySettings, id=uuid4(), tenant_id=second,
                                admin_user_id=second_admin, version=1, handle="b", status="pending",
                                credential_source="managed", credential_id=credential)
        with pytest.raises(sa.exc.IntegrityError), conn.begin_nested():
            insert_legacy_model(conn, auth.ProviderPayment, id=uuid4(), tenant_id=second, client_id=client,
                checkout_key="synthetic", cart_revision="r", total_cents=5, handle_snapshot="b",
                configuration_version=1, verification_profile="synthetic-only", credential_id=credential)
    alembic(url, "downgrade", SOURCE)
    with engine.connect() as conn:
        assert not sa.inspect(conn).has_table("infinitepay_credential")


def test_downgrade_refuses_managed_secret(migration_database):  # noqa: F811
    url, engine = migration_database
    alembic(url, "upgrade", TARGET)
    with engine.begin() as conn:
        tenant = uuid4()
        insert_legacy_model(conn, auth.Tenant, id=tenant, status="active")
        insert_legacy_model(conn, auth.InfinitePayCredential, id=uuid4(), tenant_id=tenant,
                            environment="development", key_id="synthetic", nonce=b"x" * 12,
                            ciphertext=b"synthetic-ciphertext", created_at=auth.now())
    result = alembic(url, "downgrade", SOURCE, succeeds=False)
    assert "preserve credenciais e referências financeiras" in result.stderr
    with engine.connect() as conn:
        assert conn.scalar(sa.text("SELECT version_num FROM alembic_version")) == TARGET
        assert conn.scalar(sa.text("SELECT count(*) FROM infinitepay_credential")) == 1
