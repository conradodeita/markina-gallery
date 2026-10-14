"""Integridade de clientes independentes em schema PostgreSQL sintético exclusivo."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth import Base, Client, ClientPhone, Tenant, now


@pytest.fixture
def client_db(tmp_path):
    url = os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL")
    if url is None:
        url = f"sqlite:///{tmp_path / 'clients.sqlite'}"
    engine = create_engine(url, poolclass=NullPool)
    schema = None
    if engine.dialect.name == "postgresql":
        assert engine.url.host == "127.0.0.1" and engine.url.port == 15470
        assert engine.url.database == "pyp_photographer_test"
        schema = f"client_isolation_{uuid4().hex}"
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = engine.execution_options(schema_translate_map={None: schema})
    else:
        @event.listens_for(engine, "connect")
        def enable_fk(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            yield db
    finally:
        if schema is not None:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def clients(db):
    tenants = [Tenant(), Tenant()]
    db.add_all(tenants)
    db.flush()
    first = Client(tenant_id=tenants[0].id, full_name="Cliente sintética A", phone_e164="+5511999990001")
    second = Client(tenant_id=tenants[1].id, full_name="Cliente sintética B", phone_e164="+5511999990001")
    db.add_all([first, second])
    db.flush()
    return first, second


def test_mesmo_telefone_preserva_identidades_independentes(client_db):
    first, second = clients(client_db)
    for client in (first, second):
        client_db.add(ClientPhone(
            tenant_id=client.tenant_id, client_id=client.id,
            phone_e164=client.phone_e164, verified_at=now(),
        ))
    client_db.commit()
    first_id, second_id = first.id, second.id
    first.full_name = "Nome sintético alterado somente em A"
    first.phone_e164 = "+5511999990002"
    client_db.commit()
    client_db.expire_all()
    assert first_id != second_id
    assert client_db.get(Client, first_id).full_name != client_db.get(Client, second_id).full_name
    assert client_db.get(Client, second_id).phone_e164 == "+5511999990001"


def test_telefone_canonico_duplicado_na_mesma_conta_recusado(client_db):
    first, _ = clients(client_db)
    client_db.add(Client(
        tenant_id=first.tenant_id, full_name="Duplicada sintética", phone_e164=first.phone_e164,
    ))
    with pytest.raises(IntegrityError):
        client_db.flush()


@pytest.mark.parametrize("verified", [False, True])
def test_telefone_ativo_reservado_por_conta(client_db, verified):
    first, _ = clients(client_db)
    another = Client(
        tenant_id=first.tenant_id, full_name="Outra sintética A", phone_e164="+5511999990002",
    )
    client_db.add(another)
    client_db.flush()
    client_db.add(ClientPhone(
        tenant_id=first.tenant_id, client_id=first.id,
        phone_e164="+5511999990003", verified_at=now() if verified else None,
    ))
    client_db.flush()
    client_db.add(ClientPhone(
        tenant_id=another.tenant_id, client_id=another.id,
        phone_e164="+5511999990003", verified_at=now() if verified else None,
    ))
    with pytest.raises(IntegrityError):
        client_db.flush()


def test_telefone_nao_pode_apontar_cliente_de_outro_dono(client_db):
    first, second = clients(client_db)
    # Core insert prova a constraint, sem hooks do ORM ou resolvedores da API.
    with pytest.raises(IntegrityError):
        client_db.execute(ClientPhone.__table__.insert().values(
            id=uuid4(), tenant_id=second.tenant_id, client_id=first.id,
            phone_e164="+5511999990003", active=True, verified_at=now(), created_at=now(),
        ))


@pytest.mark.parametrize("entity", [Client, ClientPhone])
def test_proprietario_obrigatorio_sem_atribuicao_implicita(client_db, entity):
    values = {"full_name": "Sem proprietário", "phone_e164": "+5511999990001"}
    if entity is ClientPhone:
        first, _ = clients(client_db)
        values = {"client_id": first.id, "phone_e164": first.phone_e164}
    client_db.add(entity(**values))
    with pytest.raises(IntegrityError):
        client_db.flush()
    column = entity.__table__.c.tenant_id
    assert not column.nullable and column.default is None and column.server_default is None


def test_unico_telefone_ativo_por_cliente_preservado(client_db):
    first, _ = clients(client_db)
    client_db.add(ClientPhone(
        tenant_id=first.tenant_id, client_id=first.id,
        phone_e164=first.phone_e164, verified_at=now(),
    ))
    client_db.flush()
    client_db.add(ClientPhone(
        tenant_id=first.tenant_id, client_id=first.id,
        phone_e164="+5511999990002", verified_at=now(),
    ))
    with pytest.raises(IntegrityError):
        client_db.flush()
