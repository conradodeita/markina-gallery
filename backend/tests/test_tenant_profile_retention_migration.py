"""Prova aditiva e rollback protegido em PostgreSQL sintético exclusivo."""

from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema
from tests.test_tenant_media_deletion_migration import _upgrade_with_owner

postgres_schema = _postgres_schema


def test_profile_reduction_migration_preserves_legacy_and_blocks_history_loss(monkeypatch, postgres_schema):
    engine = postgres_schema
    config = _upgrade_with_owner(monkeypatch, engine, "20261110_0122")
    profile_id = uuid4()
    with engine.begin() as connection:
        owner_id = connection.scalar(text("SELECT admin_user_id FROM platform_owner"))
        tenant_id = connection.scalar(text("SELECT tenant_id FROM tenant_admin WHERE admin_user_id=:owner"),
                                      {"owner": owner_id})
        connection.execute(text(
            "INSERT INTO photographer_business_profile "
            "(id,admin_user_id,tenant_id,full_name,cpf_envelope,address_envelope,cpf_fingerprint,"
            "cpf_fingerprint_key_version,created_at,updated_at) "
            "VALUES (:id,:owner,:tenant,'Synthetic identity','synthetic-cpf','synthetic-address',"
            ":fingerprint,'legacy-v0',now(),now())"
        ), {"id": profile_id, "owner": owner_id, "tenant": tenant_id, "fingerprint": "f" * 64})
    command.upgrade(config, "20261110_0123")
    with engine.connect() as connection:
        row = connection.execute(text("SELECT * FROM photographer_business_profile WHERE id=:id"),
                                 {"id": profile_id}).one()
        assert row.cpf_envelope == "synthetic-cpf" and row.address_envelope == "synthetic-address"
        assert row.cpf_fingerprint == "f" * 64
    command.downgrade(config, "20261110_0122")
    command.upgrade(config, "20261110_0123")

    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE photographer_business_profile SET cpf_envelope=NULL,address_envelope=NULL WHERE id=:id"
        ), {"id": profile_id})
    with pytest.raises(RuntimeError, match="perfis reduzidos"):
        command.downgrade(config, "20261110_0122")
    with engine.connect() as connection:
        row = connection.execute(text("SELECT full_name,cpf_fingerprint,cpf_fingerprint_key_version "
                                      "FROM photographer_business_profile WHERE id=:id"), {"id": profile_id}).one()
        assert row.full_name == "Synthetic identity" and row.cpf_fingerprint == "f" * 64
        assert row.cpf_fingerprint_key_version == "legacy-v0"
    with engine.begin() as connection:
        connection.execute(text("UPDATE photographer_business_profile SET cpf_envelope='synthetic-cpf' WHERE id=:id"),
                           {"id": profile_id})
    insert_event = text(
        "INSERT INTO platform_admin_event "
        "(id,request_id,actor_admin_id,object_id,tenant_id,action,previous_status,next_status,result,origin,created_at) "
        "VALUES (:id,:request,:owner,:object,:tenant,'tenant.profile_reduced',:previous,:next,'success','web_console',now())"
    )
    for previous, next_status in ((None, "reduced"), ("retained", None), ("closed", "reduced")):
        with pytest.raises(IntegrityError) as failure, engine.begin() as connection:
            connection.execute(insert_event, {"id": uuid4(), "request": uuid4(), "owner": owner_id,
                "object": uuid4(), "tenant": tenant_id, "previous": previous, "next": next_status})
        assert failure.value.orig.diag.constraint_name == "ck_platform_admin_profile_reduced_context"
    with engine.begin() as connection:
        connection.execute(insert_event, {"id": uuid4(), "request": uuid4(), "owner": owner_id,
            "object": uuid4(), "tenant": tenant_id, "previous": "retained", "next": "reduced"})
    with pytest.raises(RuntimeError, match="auditorias de redução"):
        command.downgrade(config, "20261110_0122")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261110_0123"
        assert connection.scalar(text("SELECT count(*) FROM platform_admin_event WHERE action='tenant.profile_reduced'")) == 1
