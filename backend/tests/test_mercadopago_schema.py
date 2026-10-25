"""DDL Orders em banco descartável: isolamento e preservação do legado."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.auth import Base, Client, ProviderPayment, SaleOrder, Tenant, now
from app.auth import engine as runtime_engine


def migration():
    path = Path(__file__).parents[1] / "migrations/versions/20261024_0088_mercadopago_orders.py"
    spec = importlib.util.spec_from_file_location("mp_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_preserva_registros_e_acrescenta_contratos():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE tenant (id CHAR(32) PRIMARY KEY)")
        connection.exec_driver_sql(
            "CREATE TABLE client (id CHAR(32) PRIMARY KEY, tenant_id CHAR(32), UNIQUE(id, tenant_id))")
        connection.exec_driver_sql(
            "CREATE TABLE provider_payment (id CHAR(32) PRIMARY KEY, state TEXT, total_cents INTEGER)")
        connection.exec_driver_sql(
            "CREATE TABLE sale_order (id CHAR(32) PRIMARY KEY, tenant_id CHAR(32), "
            "client_id CHAR(32), payment_group_id CHAR(32), provider_payment_id CHAR(32), "
            "payment_status TEXT, total_cents INTEGER)")
        connection.exec_driver_sql(
            "CREATE TABLE admin_security_challenge (id CHAR(32) PRIMARY KEY, tenant_id CHAR(32), "
            "purpose TEXT, CONSTRAINT ck_admin_security_purpose CHECK "
            "(purpose IN ('change_pix_otp', 'change_email_otp', 'change_password_otp', "
            "'password_recovery_otp')), CONSTRAINT ck_admin_challenge_pix_context CHECK "
            "(purpose != 'change_pix_otp' OR tenant_id IS NOT NULL))")
        connection.exec_driver_sql(
            "INSERT INTO provider_payment VALUES ('legacy', 'confirmed', 2100)")
        connection.exec_driver_sql(
            "INSERT INTO sale_order VALUES ('order', 'tenant', 'client', NULL, 'legacy', "
            "'confirmed', 2100)")
        before = connection.exec_driver_sql("SELECT * FROM provider_payment").all()
        with Operations.context(MigrationContext.configure(connection)):
            migration().upgrade()
        assert connection.exec_driver_sql("SELECT * FROM provider_payment").all() == before
        assert connection.exec_driver_sql(
            "SELECT id, provider_payment_id, payment_status, total_cents, mercadopago_payment_id "
            "FROM sale_order").all() == [("order", "legacy", "confirmed", 2100, None)]
        assert {"mercadopago_account", "payment_preferences", "mercadopago_payment",
                "mercadopago_webhook"} <= set(sa.inspect(connection).get_table_names())
        constraints = {row["name"] for row in sa.inspect(connection).get_foreign_keys("sale_order")}
        assert "fk_sale_order_mp_owner" in constraints
        connection.exec_driver_sql(
            "INSERT INTO admin_security_challenge VALUES ('new', 'tenant', 'change_payment_otp')")
    with pytest.raises(RuntimeError, match="preservação"):
        migration().downgrade()


def test_constraints_rejeitam_conta_cruzada_e_mesma_revisao_ativa():
    engine = sa.create_engine("sqlite://")
    @sa.event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    names = ["tenant", "client", "mercadopago_account", "payment_preferences",
             "mercadopago_payment", "mercadopago_webhook"]
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[name] for name in names])
    first, second, client, account = (uuid4() for _ in range(4))
    with engine.begin() as connection:
        tenant_table = Base.metadata.tables["tenant"]
        connection.execute(tenant_table.insert(), [
            {"id": first, "name": "A", "slug": "a"}, {"id": second, "name": "B", "slug": "b"}])
        connection.execute(Base.metadata.tables["client"].insert(), {
            "id": client, "tenant_id": first, "full_name": "Cliente",
            "phone_e164": "+5511999990001"})
        connection.execute(Base.metadata.tables["mercadopago_account"].insert(), {
            "id": account, "tenant_id": first, "seller_id": "123", "public_key": "public",
            "access_token_envelope": {}, "webhook_secret_envelope": {}, "test_account": True})
    table = Base.metadata.tables["mercadopago_payment"]
    def insert(tenant, key, revision="a" * 64):
        with engine.begin() as connection:
            connection.execute(table.insert(), {
                "id": uuid4(), "tenant_id": tenant, "client_id": client, "account_id": account,
                "checkout_key": key, "cart_revision": revision, "total_cents": 100,
                "method": "credit_card"})
    with pytest.raises(IntegrityError):
        insert(second, str(uuid4()))
    insert(first, str(uuid4()))
    insert(first, str(uuid4()), "b" * 64)
    with pytest.raises(IntegrityError):
        insert(first, str(uuid4()))


def test_migration_0089_substitui_indice_e_downgrade_preserva_multiplas_tentativas():
    path = Path(__file__).parents[1] / "migrations/versions/20261025_0089_mercadopago_parallel_attempts.py"
    spec = importlib.util.spec_from_file_location("mp_parallel_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE mercadopago_payment (id TEXT, tenant_id TEXT, client_id TEXT, "
            "cart_revision TEXT, active BOOLEAN NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_mp_active_client ON mercadopago_payment "
            "(tenant_id, client_id) WHERE active = true"
        )
        connection.exec_driver_sql(
            "INSERT INTO mercadopago_payment VALUES ('one', 'tenant', 'client', 'a', true)"
        )
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
        connection.exec_driver_sql(
            "INSERT INTO mercadopago_payment VALUES ('two', 'tenant', 'client', 'b', true)"
        )
        indexes = {row["name"] for row in sa.inspect(connection).get_indexes("mercadopago_payment")}
        assert "uq_mp_active_client_revision" in indexes
        with pytest.raises(RuntimeError, match="Downgrade recusado"), \
                Operations.context(MigrationContext.configure(connection)):
            module.downgrade()


def test_upgrade_postgresql_sobre_schema_completo_preserva_infinitepay():
    if runtime_engine.dialect.name != "postgresql":
        pytest.skip("Ensaio DDL PostgreSQL exige banco local descartável.")
    assert (runtime_engine.url.host, runtime_engine.url.port, runtime_engine.url.database) == (
        "127.0.0.1", 55888, "markina_unified_test")
    schema = "mp_migration_" + uuid4().hex
    try:
        with runtime_engine.begin() as connection:
            connection.execute(CreateSchema(schema))
            connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
            Base.metadata.create_all(connection)
            with Session(bind=connection) as db:
                tenant = Tenant(id=uuid4())
                db.add(tenant)
                db.flush()
                client = Client(tenant_id=tenant.id, full_name="Histórico",
                                phone_e164="+5511999990081")
                db.add(client)
                db.flush()
                payment = ProviderPayment(
                    tenant_id=tenant.id, client_id=client.id, checkout_key=str(uuid4()),
                    cart_revision="a" * 64, total_cents=2100, handle_snapshot="legacy",
                    configuration_version=1, verification_profile="legacy", state="confirmed",
                    provider_transaction_nsu="synthetic-legacy-nsu", confirmed_at=now())
                db.add(payment)
                db.flush()
                order = SaleOrder(
                    tenant_id=tenant.id, client_id=client.id, total_cents=2100,
                    payment_status="confirmed", provider_payment_id=payment.id,
                    derived_gallery_id_snapshot=uuid4(), derived_gallery_name_snapshot="Privada",
                    parent_gallery_id_snapshot=uuid4(), parent_gallery_name_snapshot="Evento")
                db.add(order)
                db.flush()
            before = connection.exec_driver_sql(
                "SELECT id, provider_payment_id, total_cents, payment_status FROM sale_order").all()
            connection.exec_driver_sql("ALTER TABLE sale_order DROP COLUMN mercadopago_payment_id CASCADE")
            for name in ["mercadopago_webhook", "mercadopago_payment", "payment_preferences", "mercadopago_account"]:
                connection.exec_driver_sql(f"DROP TABLE {name}")
            with Operations.context(MigrationContext.configure(connection)):
                migration().upgrade()
            assert connection.exec_driver_sql(
                "SELECT id, provider_payment_id, total_cents, payment_status FROM sale_order").all() == before
            assert connection.exec_driver_sql(
                "SELECT state, total_cents, provider_transaction_nsu FROM provider_payment").all() == [
                    ("confirmed", 2100, "synthetic-legacy-nsu")]
            actual = {item["name"] for item in sa.inspect(connection).get_foreign_keys("sale_order")}
            assert "fk_sale_order_mp_owner" in actual
    finally:
        with runtime_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True, if_exists=True))
