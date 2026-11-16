"""DDL e concorrência financeira em PostgreSQL local descartável e sintético.

O prefixo test_tenant_ exclui o seed legado global de backend/conftest.py.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, func, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.auth import (
    MercadoPagoCreditPurchase,
    MercadoPagoCreditPurchaseEvent,
    PhotographerCreditEntry,
    now,
)
from app.integration_secrets import IntegrationCipher
from app.mercadopago_credit_purchases import apply_credit_order, owned_credit_purchase
from tests.test_mercadopago_credit_purchases import create_purchase_context, order_resource, prepare


@pytest.fixture
def postgres_schema():
    raw = os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Requer PostgreSQL local sintético exclusivo")
    url = make_url(raw)
    expected_port_raw = os.getenv("PHOTOGRAPHER_TEST_DATABASE_PORT", "15470")
    if not expected_port_raw.isdecimal() or not 1 <= int(expected_port_raw) <= 65535:
        pytest.fail("PHOTOGRAPHER_TEST_DATABASE_PORT deve ser uma porta TCP válida")
    if (
        url.get_backend_name() != "postgresql"
        or url.host != "127.0.0.1"
        or url.port != int(expected_port_raw)
        or url.database != "pyp_photographer_test"
    ):
        pytest.fail(
            "DDL permitido somente no banco pyp_photographer_test em 127.0.0.1 "
            "e na porta declarada por PHOTOGRAPHER_TEST_DATABASE_PORT"
        )
    schema = "credit_purchase_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def migrated_db(postgres_schema, monkeypatch):
    from tests.test_photographer_onboarding_migration import _config, _demo_helpers

    engine = postgres_schema
    config, scoped_url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    _demo_helpers().create_synthetic_owner(scoped_url)
    command.upgrade(config, "20261110_0124")
    # Só a identidade de bootstrap vazia deste schema descartável: os cenários
    # criam seu proprietário/comprador; tenant/configuração legados permanecem.
    # Nenhum ledger ou histórico é removido.
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT count(*) FROM photographer_credit_entry")) == 0
        for table in ("platform_owner", "tenant_credit_wallet", "tenant_admin", "admin_user"):
            connection.execute(text(f"DELETE FROM {table}"))
    with Session(engine, expire_on_commit=False) as db:
        yield db


def test_upgrade_from_production_schema_preserves_owner_and_backfills_wallets(
    postgres_schema, monkeypatch
):
    engine = postgres_schema
    with engine.connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    url = engine.url.update_query_dict({"options": f"-csearch_path={schema}"})
    monkeypatch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    command.upgrade(config, "20261026_0090")
    owner_id, other_tenant_id = uuid4(), uuid4()
    with engine.begin() as connection:
        owner_tenant_id = connection.scalar(text("SELECT id FROM tenant"))
        assert owner_tenant_id is not None
        connection.execute(
            text(
                "INSERT INTO admin_user (id,email,password_hash,email_verified,totp_secret) "
                "VALUES (:id,'owner-migration@example.test','synthetic',true,'JBSWY3DPEHPK3PXP')"
            ),
            {"id": owner_id},
        )
        connection.execute(
            text(
                "INSERT INTO tenant_admin (id,tenant_id,admin_user_id,active,created_at) "
                "VALUES (:id,:tenant,:admin,true,CURRENT_TIMESTAMP)"
            ),
            {"id": uuid4(), "tenant": owner_tenant_id, "admin": owner_id},
        )
        connection.execute(
            text(
                "INSERT INTO platform_owner (singleton,admin_user_id,authorization_reference,established_at) "
                "VALUES (1,:admin,'synthetic-migration',CURRENT_TIMESTAMP)"
            ),
            {"admin": owner_id},
        )
        connection.execute(
            text(
                "INSERT INTO tenant (id,status,created_at) VALUES (:id,'active',CURRENT_TIMESTAMP)"
            ),
            {"id": other_tenant_id},
        )
    command.upgrade(config, "20261101_0095")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261101_0095"
        assert connection.scalar(text("SELECT admin_user_id FROM platform_owner")) == owner_id
        assert dict(
            connection.execute(text("SELECT tenant_id,mode FROM tenant_credit_wallet")).all()
        ) == {
            owner_tenant_id: "unmetered",
            other_tenant_id: "finite",
        }
        assert (
            connection.scalar(
                text("SELECT totp_secret FROM admin_user WHERE id=:id"), {"id": owner_id}
            )
            is None
        )
        assert connection.scalar(
            text("SELECT totp_secret_envelope FROM admin_user WHERE id=:id"), {"id": owner_id}
        ).startswith("totp:v1:")


def test_downgrade_refuses_to_drop_credit_purchase_history(postgres_schema, monkeypatch):
    from tests.test_photographer_onboarding_migration import _config, _demo_helpers

    engine = postgres_schema
    config, scoped_url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    _demo_helpers().create_synthetic_owner(scoped_url)
    command.upgrade(config, "20261101_0095")

    # Esta prova para em 0095: reflita as tabelas históricas para não depender
    # de colunas/defaults ou gates adicionados pelo ORM/runtime atual.
    metadata = MetaData()
    tables = {name: Table(name, metadata, autoload_with=engine, resolve_fks=False) for name in (
        "tenant", "admin_user", "tenant_admin", "photographer_credit_package",
        "mercadopago_account", "mercadopago_credit_purchase", "mercadopago_credit_purchase_event",
    )}
    buyer_tenant_id, buyer_id, package_id, account_id, purchase_id = (uuid4() for _ in range(5))
    with engine.begin() as connection:
        owner_id = connection.scalar(text("SELECT admin_user_id FROM platform_owner"))
        owner_tenant_id = connection.scalar(text(
            "SELECT tenant_id FROM tenant_admin WHERE admin_user_id=:owner"
        ), {"owner": owner_id})
        connection.execute(tables["tenant"].insert().values(
            id=buyer_tenant_id, status="active", created_at=now(),
        ))
        connection.execute(tables["admin_user"].insert().values(
            id=buyer_id, email="buyer-downgrade@example.test", password_hash="synthetic",
            email_verified=True,
        ))
        connection.execute(tables["tenant_admin"].insert().values(
            id=uuid4(), tenant_id=buyer_tenant_id, admin_user_id=buyer_id, active=True,
            created_at=now(),
        ))
        connection.execute(tables["photographer_credit_package"].insert().values(
            id=package_id, name="Pacote de regressão", credit_quantity=12, price_cents=1500,
            currency_code="BRL", active=True, created_by_admin_id=owner_id,
            updated_by_admin_id=owner_id,
        ))
        cipher = IntegrationCipher()
        connection.execute(tables["mercadopago_account"].insert().values(
            id=account_id, tenant_id=owner_tenant_id, seller_id="123456789",
            public_key="APP_USR-synthetic-public", test_account=True, status="active",
            created_at=now(), access_token_envelope=cipher.encrypt(
                "APP_USR-synthetic-token", tenant_id=owner_tenant_id, credential_id=account_id,
            ).payload(), webhook_secret_envelope=cipher.encrypt(
                "synthetic-webhook-secret", tenant_id=owner_tenant_id, credential_id=account_id,
            ).payload(),
        ))
        connection.execute(tables["mercadopago_credit_purchase"].insert().values(
            id=purchase_id, tenant_id=buyer_tenant_id, buyer_admin_id=buyer_id,
            owner_admin_id=owner_id, receiver_tenant_id=owner_tenant_id,
            receiver_account_id=account_id, package_id=package_id,
            package_name="Pacote de regressão", credit_quantity=12, total_cents=1500,
            currency_code="BRL", idempotency_key="synthetic-downgrade-guard",
            external_reference=str(purchase_id), state="prepared",
        ))
        connection.execute(tables["mercadopago_credit_purchase_event"].insert().values(
            id=uuid4(), tenant_id=buyer_tenant_id, purchase_id=purchase_id,
            event_type="prepared", event_key="prepared",
        ))

    with pytest.raises(RuntimeError, match="Preserve as compras de créditos"):
        command.downgrade(config, "20261031_0094")

    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT version_num FROM alembic_version")
        ) == "20261101_0095"
        assert connection.scalar(
            text("SELECT count(*) FROM mercadopago_credit_purchase WHERE id=:id"),
            {"id": purchase_id},
        ) == 1
        assert connection.scalar(
            text(
                "SELECT count(*) FROM mercadopago_credit_purchase_event "
                "WHERE purchase_id=:id AND tenant_id=:tenant_id"
            ),
            {"id": purchase_id, "tenant_id": buyer_tenant_id},
        ) == 1


def test_migration_enforces_receiver_scope_snapshot_and_append_only_history(migrated_db):
    db = migrated_db
    owner_tenant, buyer_tenant, _owner, buyer, package, _account = create_purchase_context(db)
    purchase = prepare(db, buyer_tenant, buyer, package, "ddl")
    db.commit()
    assert purchase.receiver_tenant_id == owner_tenant.id != purchase.tenant_id
    row = dict(db.execute(select(MercadoPagoCreditPurchase.__table__)).mappings().one())
    row.update(
        id=uuid4(),
        external_reference=str(uuid4()),
        idempotency_key="invalid-receiver",
        receiver_tenant_id=buyer_tenant.id,
    )
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(insert(MercadoPagoCreditPurchase.__table__).values(**row))
    with pytest.raises(DBAPIError, match="immutable"), db.begin_nested():
        db.execute(
            text("UPDATE mercadopago_credit_purchase SET total_cents=1 WHERE id=:id"),
            {"id": purchase.id},
        )
    purchase.method = "credit_card"
    purchase.state = "submitting"
    purchase.submitted_at = now()
    assert apply_credit_order(db, purchase, order_resource(purchase))
    db.commit()
    for statement in (
        "UPDATE mercadopago_credit_purchase_event SET event_key='tampered'",
        "DELETE FROM mercadopago_credit_purchase_event",
        "TRUNCATE mercadopago_credit_purchase_event",
    ):
        with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
            db.execute(text(statement))
    assert db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1
    assert db.get(MercadoPagoCreditPurchase, purchase.id).state == "confirmed"


def test_concurrent_confirmations_credit_once_on_migrated_schema(migrated_db):
    db = migrated_db
    _receiver, tenant, _owner, buyer, package, _account = create_purchase_context(db)
    purchase = prepare(db, tenant, buyer, package, "concurrent")
    purchase.method = "credit_card"
    purchase.state = "submitting"
    purchase.submitted_at = now()
    db.commit()
    purchase_id, tenant_id = purchase.id, tenant.id
    resource = order_resource(purchase)
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    gate = Barrier(2)

    def confirm():
        with factory() as session:
            gate.wait(timeout=10)
            locked = owned_credit_purchase(session, tenant_id, purchase_id, lock=True)
            changed = apply_credit_order(session, locked, resource)
            session.commit()
            return changed

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(confirm) for _ in range(2)]
        outcomes = [future.result(timeout=20) for future in futures]
    assert sorted(outcomes) == [False, True]
    db.expire_all()
    assert db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1
    assert db.scalar(select(func.sum(PhotographerCreditEntry.delta))) == package.credit_quantity
    assert (
        db.scalar(
            select(func.count(MercadoPagoCreditPurchaseEvent.id)).where(
                MercadoPagoCreditPurchaseEvent.event_type == "confirmed",
            )
        )
        == 1
    )
