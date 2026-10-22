"""0086 preserva links antigos e recusa perda de estado financeiro novo."""

import json
import os
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app import auth
from tests.tenant_fixtures import insert_legacy_model
from tests.test_global_pix_migration import alembic
from tests.test_tenant_infinitepay_migration import migration_database  # noqa: F401

pytestmark = pytest.mark.skipif(not os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL"), reason="Exige PostgreSQL descartável")


def legacy_payment(conn):
    tenant, client, payment = uuid4(), uuid4(), uuid4()
    insert_legacy_model(conn, auth.Tenant, id=tenant, status="active")
    insert_legacy_model(conn, auth.Client, id=client, tenant_id=tenant, full_name="Sintética", phone_e164="+5511999990011")
    insert_legacy_model(conn, auth.ProviderPayment, id=payment, tenant_id=tenant, client_id=client,
        checkout_key="legacy", cart_revision="r", total_cents=100, handle_snapshot="legacy",
        configuration_version=1, verification_profile="infinitepay-public-v1")
    return payment


def test_upgrade_preserves_legacy_credit_only_and_empty_downgrade(migration_database):  # noqa: F811
    url, engine = migration_database
    alembic(url, "upgrade", "20261020_0085")
    with engine.begin() as conn:
        payment = legacy_payment(conn)
        before = list(conn.execute(sa.text("SELECT id,tenant_id,client_id,total_cents,state FROM provider_payment")))
    alembic(url, "upgrade", "20261021_0086")
    with engine.begin() as conn:
        assert list(conn.execute(sa.text("SELECT id,tenant_id,client_id,total_cents,state FROM provider_payment"))) == before
        row = conn.execute(sa.text("SELECT checkout_methods_snapshot,capture_method,cart_dismissed_at FROM provider_payment")).one()
        assert row[0] == ["credit_card"] and row[1] is None and row[2] is None
        with pytest.raises(sa.exc.IntegrityError), conn.begin_nested():
            conn.execute(sa.text("UPDATE provider_payment SET capture_method='cash' WHERE id=:id"), {"id":payment})
    alembic(url, "downgrade", "20261020_0085")
    with engine.connect() as conn:
        assert "capture_method" not in {column["name"] for column in sa.inspect(conn).get_columns("provider_payment")}


@pytest.mark.parametrize("state", ["mixed", "captured", "dismissed"])
def test_downgrade_refuses_used_new_contract(migration_database, state):  # noqa: F811
    url, engine = migration_database
    alembic(url, "upgrade", "20261021_0086")
    with engine.begin() as conn:
        legacy_payment(conn)
        if state == "mixed":
            conn.execute(sa.text("UPDATE provider_payment SET checkout_methods_snapshot=CAST(:methods AS JSON)"),
                         {"methods":json.dumps(["credit_card", "pix"])})
        elif state == "captured":
            conn.execute(sa.text("UPDATE provider_payment SET capture_method='pix'"))
        else:
            conn.execute(sa.text("UPDATE provider_payment SET cart_dismissed_at=CURRENT_TIMESTAMP"))
    with pytest.raises(Exception, match="Downgrade recusado"):
        alembic(url, "downgrade", "20261020_0085")
    with engine.connect() as conn:
        assert conn.scalar(sa.text("SELECT version_num FROM alembic_version")) == "20261021_0086"
