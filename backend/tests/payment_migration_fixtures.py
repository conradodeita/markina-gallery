"""Banco PostgreSQL efêmero para testes da cadeia de pagamentos legada."""

import os
from uuid import uuid4

import pytest
import sqlalchemy as sa


@pytest.fixture(name="migration_database")
def payment_migration_database():
    url = os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requer PostgreSQL descartável configurado")
    parsed = sa.engine.make_url(url)
    assert (parsed.host, parsed.port, parsed.database) == ("127.0.0.1", 15470, "pyp_photographer_test")
    name = f"payment_migration_{uuid4().hex}"
    maintenance = sa.create_engine(url, isolation_level="AUTOCOMMIT")
    with maintenance.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    engine = sa.create_engine(parsed.set(database=name).render_as_string(hide_password=False))
    try:
        yield engine.url.render_as_string(hide_password=False), engine
    finally:
        engine.dispose()
        with maintenance.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE "{name}"')
        maintenance.dispose()
