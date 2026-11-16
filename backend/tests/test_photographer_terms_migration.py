"""Versionamento e imutabilidade dos Termos em PostgreSQL descartável."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError


@pytest.fixture
def terms_postgres_schema():
    raw = os.getenv("PHOTOGRAPHER_TERMS_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Requer PostgreSQL local sintético exclusivo para a migration dos Termos")
    url = make_url(raw)
    if (url.get_backend_name() != "postgresql" or url.host != "127.0.0.1"
            or url.port != 15473 or url.database != "pyp_terms_test"):
        pytest.fail("DDL permitido somente em 127.0.0.1:15473/pyp_terms_test")
    schema = "terms_migration_" + uuid4().hex
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


def test_0110_creates_term_versions_and_guards_append_only_history(terms_postgres_schema, monkeypatch):
    engine = terms_postgres_schema
    with engine.connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    database_url = engine.url.update_query_dict({"options": f"-csearch_path={schema}"})
    monkeypatch.setenv("DATABASE_URL", database_url.render_as_string(hide_password=False))
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    command.upgrade(config, "20261026_0090")
    admin_id = uuid4()
    with engine.begin() as connection:
        tenant_id = connection.scalar(text("SELECT id FROM tenant ORDER BY id LIMIT 1"))
        if tenant_id is None:
            tenant_id = uuid4()
            connection.execute(text(
                "INSERT INTO tenant(id,status,created_at) VALUES (:id,'active',CURRENT_TIMESTAMP)"
            ), {"id": tenant_id})
        connection.execute(text(
            "INSERT INTO admin_user(id,email,password_hash,email_verified,totp_secret) "
            "VALUES (:id,'terms-migration@example.test','synthetic',true,'JBSWY3DPEHPK3PXP')"
        ), {"id": admin_id})
        connection.execute(text(
            "INSERT INTO tenant_admin(id,tenant_id,admin_user_id,active,created_at) "
            "VALUES (:id,:tenant,:admin,true,CURRENT_TIMESTAMP)"
        ), {"id": uuid4(), "tenant": tenant_id, "admin": admin_id})
        connection.execute(text(
            "INSERT INTO platform_owner(singleton,admin_user_id,authorization_reference,established_at) "
            "VALUES (1,:admin,'synthetic-terms-migration',CURRENT_TIMESTAMP)"
        ), {"admin": admin_id})
    command.upgrade(config, "20261107_0109")
    command.upgrade(config, "20261107_0110")

    columns = {column["name"]: column for column in inspect(engine).get_columns("photographer_terms_acceptance")}
    assert columns["provider_identity"]["type"].length == 520
    assert columns["photographer_identity"]["type"].length == 600
    accepted_id = uuid4()
    with engine.begin() as connection:
        tenant_id = connection.scalar(text("SELECT tenant_id FROM tenant_admin WHERE admin_user_id=:id"), {"id": admin_id})
        connection.execute(text(
            "INSERT INTO photographer_terms_version(id,version_number,terms_version,template_text,template_sha256,"
            "provider_legal_name,provider_contact_email,published_by_admin_id,published_at) "
            "VALUES (:id,1,'v1','template','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',"
            "'Synthetic','support@example.test',:admin,CURRENT_TIMESTAMP)"
        ), {"id": uuid4(), "admin": admin_id})
        connection.execute(text(
            "INSERT INTO photographer_terms_acceptance(id,admin_user_id,tenant_id,terms_version,terms_text,"
            "terms_sha256,provider_identity,photographer_identity,accepted_at,environment) "
            "VALUES (:id,:admin,:tenant,'v0','accepted snapshot',:sha,:provider,:photographer,CURRENT_TIMESTAMP,'test')"
        ), {"id": accepted_id, "admin": admin_id, "tenant": tenant_id, "sha": "b" * 64,
             "provider": "P" * 300, "photographer": "F" * 500})

    for statement in (
        "UPDATE photographer_terms_version SET template_text='changed'",
        "DELETE FROM photographer_terms_version",
        "TRUNCATE photographer_terms_version",
    ):
        with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
            connection.execute(text(statement))
    for statement in (
        "UPDATE photographer_terms_acceptance SET terms_text='changed'",
        "DELETE FROM photographer_terms_acceptance",
        "TRUNCATE photographer_terms_acceptance",
    ):
        with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
            connection.execute(text(statement))
    with pytest.raises(RuntimeError, match="Preserve dados"):
        command.downgrade(config, "20261107_0109")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT terms_version FROM photographer_terms_version")) == "v1"
        assert connection.scalar(text("SELECT length(provider_identity) FROM photographer_terms_acceptance WHERE id=:id"),
                                  {"id": accepted_id}) == 300
        assert connection.scalar(text("SELECT length(photographer_identity) FROM photographer_terms_acceptance WHERE id=:id"),
                                  {"id": accepted_id}) == 500
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261107_0110"
