"""Identidade/diretório com contexto sintético; login/middleware são etapa própria."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from starlette.requests import Request

from app import main
from app.auth import (
    AuditEvent,
    AuthChallenge,
    AuthSession,
    Client,
    ClientPhone,
    Tenant,
    WhatsAppDelivery,
    now,
    token_hash,
)
from app.client_identity import (
    ClientIdentityConflict,
    assert_phone_available,
    change_verified_phone,
    resolve_client_by_phone,
    verify_canonical_phone,
)
from app.client_lifecycle import ClientLifecycleError, list_client_directory
from tests.test_tenant_client_isolation import client_db as _client_db
from tests.test_tenant_ownership_schema import graph as _graph

client_db = _client_db
graph = _graph
PHONE = "+5511999990001"
NEW_PHONE = "+5511999990020"


def directory(db, owner, *, query=None, cursor=None, limit=30):
    return list_client_directory(db, tenant_id=owner, query=query, cursor=cursor, limit=limit)


def request():
    return Request({"type": "http", "method": "GET", "path": "/admin/clients", "headers": []})


@pytest.fixture
def actor(client_db, graph, monkeypatch):
    first = graph[0]
    session = AuthSession(tenant_id=first["tenant"].id, role="admin", subject_id=first["admin"].id,
                          admin_subject_id=first["admin"].id, token_hash="synthetic-directory-admin",
                          expires_at=now() + timedelta(hours=1))
    client_db.add(session)
    client_db.flush()
    # Somente a entrada do contexto já autenticado é substituída; os contratos
    # exercitam os vínculos/queries reais, sem alegar aceite do middleware.
    monkeypatch.setattr(main, "require_admin", lambda _: session)
    return session


def test_telefone_igual_resolve_clientes_distintos_e_terceira_conta_nao_enumera(client_db, graph):
    for record in graph:
        owner = record["tenant"].id
        verify_canonical_phone(client_db, record["client"], PHONE, tenant_id=owner)
        client_db.flush()
        assert resolve_client_by_phone(client_db, PHONE, tenant_id=owner).id == record["client"].id
    empty = Tenant()
    client_db.add(empty)
    client_db.flush()
    assert resolve_client_by_phone(client_db, PHONE, tenant_id=empty.id) is None
    assert assert_phone_available(client_db, PHONE, tenant_id=empty.id) is None
    assert directory(client_db, empty.id, query=PHONE)["clients"] == []


def test_troca_de_telefone_preserva_outro_cadastro_e_sua_prova(client_db, graph):
    first, second = graph
    for record in graph:
        verify_canonical_phone(client_db, record["client"], PHONE, tenant_id=record["tenant"].id)
    client_db.commit()
    untouched = client_db.scalar(select(ClientPhone).where(ClientPhone.tenant_id == second["tenant"].id))
    before = (untouched.id, untouched.phone_e164, untouched.active, untouched.verified_at, untouched.retired_at)
    change_verified_phone(client_db, first["client"], NEW_PHONE, tenant_id=first["tenant"].id)
    client_db.commit()
    client_db.expire_all()
    assert first["client"].phone_e164 == NEW_PHONE and second["client"].phone_e164 == PHONE
    assert (untouched.id, untouched.phone_e164, untouched.active, untouched.verified_at, untouched.retired_at) == before
    assert resolve_client_by_phone(client_db, PHONE, tenant_id=first["tenant"].id) is None
    assert resolve_client_by_phone(client_db, PHONE, tenant_id=second["tenant"].id).id == second["client"].id


@pytest.mark.parametrize("operation", [verify_canonical_phone, change_verified_phone])
def test_cliente_de_outro_dono_recusado_antes_de_alterar(client_db, graph, operation):
    first, second = graph
    with pytest.raises(ClientIdentityConflict, match="indisponível"):
        operation(client_db, second["client"], PHONE, tenant_id=first["tenant"].id)
    assert second["client"].phone_e164 == PHONE
    assert client_db.scalar(select(func.count()).select_from(ClientPhone)) == 0


def test_duplicidade_local_recusada_sem_aposentar_numero_atual(client_db, graph):
    first = graph[0]
    owner = first["tenant"].id
    verify_canonical_phone(client_db, first["client"], PHONE, tenant_id=owner)
    client_db.add(Client(tenant_id=owner, full_name="Outra sintética", phone_e164=NEW_PHONE))
    client_db.commit()
    with pytest.raises(ClientIdentityConflict):
        change_verified_phone(client_db, first["client"], NEW_PHONE, tenant_id=owner)
    assert first["client"].phone_e164 == PHONE
    assert client_db.scalar(select(ClientPhone.active).where(ClientPhone.client_id == first["client"].id)) is True


def test_diretorio_busca_nome_telefone_e_agregados_apenas_do_dono(client_db, graph):
    first, second = graph
    assert directory(client_db, first["tenant"].id, query=second["client"].full_name)["clients"] == []
    for record in graph:
        result = directory(client_db, record["tenant"].id, query=PHONE)
        assert [item["id"] for item in result["clients"]] == [str(record["client"].id)]
        assert result["clients"][0]["aggregates"] == {"public_galleries": 0, "private_galleries": 1, "orders": 1}


def test_cursor_nao_pode_ser_reutilizado_em_outra_conta(client_db, graph):
    first, second = graph
    client_db.add(Client(tenant_id=first["tenant"].id, full_name="ZZ sintética", phone_e164=NEW_PHONE))
    client_db.flush()
    page = directory(client_db, first["tenant"].id, limit=1)
    cursor = page["page"]["next_cursor"]
    assert cursor and directory(client_db, first["tenant"].id, cursor=cursor, limit=1)["clients"][0]["name"] == "ZZ sintética"
    with pytest.raises(ClientLifecycleError, match="Cursor"):
        directory(client_db, second["tenant"].id, cursor=cursor)


def test_conta_suspensa_ou_contexto_ausente_nao_tem_fallback(client_db, graph):
    owner = graph[0]["tenant"]
    owner.status = "suspended"
    client_db.commit()
    with pytest.raises(ClientIdentityConflict):
        resolve_client_by_phone(client_db, PHONE, tenant_id=owner.id)
    with pytest.raises(ClientLifecycleError):
        directory(client_db, owner.id)
    with pytest.raises(ClientIdentityConflict):
        resolve_client_by_phone(client_db, PHONE, tenant_id=uuid4())
    with pytest.raises(TypeError):
        resolve_client_by_phone(client_db, PHONE)


def test_contrato_criacao_e_edicao_por_uuid_preserva_outro_dono(client_db, graph, actor):
    first, second = graph
    client_db.add(Client(tenant_id=second["tenant"].id, full_name="Somente B", phone_e164=NEW_PHONE))
    client_db.flush()
    payload = main.ClientInput(full_name="Nova sintética", phone_e164=NEW_PHONE, tenant_id=second["tenant"].id)
    created = main.create_client(payload, request(), client_db)
    record = client_db.get(Client, UUID(created["id"]))
    assert record.tenant_id == first["tenant"].id
    before = second["client"].full_name
    updated = main.update_client_name(first["client"].id, main.ClientNameInput(full_name="Nome independente"), request(), client_db)
    assert updated["name"] == "Nome independente" and second["client"].full_name == before
    assert client_db.scalar(select(AuditEvent.tenant_id).where(AuditEvent.event == "client.name_changed")) == first["tenant"].id
    with pytest.raises(HTTPException) as foreign:
        main.update_client_name(second["client"].id, main.ClientNameInput(full_name="Inválido"), request(), client_db)
    with pytest.raises(HTTPException) as missing:
        main.update_client_name(uuid4(), main.ClientNameInput(full_name="Inválido"), request(), client_db)
    assert (foreign.value.status_code, foreign.value.detail) == (missing.value.status_code, missing.value.detail)
    assert second["client"].full_name == before


def test_troca_com_otp_proprio_preserva_sessao_e_delivery_alheios(client_db, graph, actor, monkeypatch):
    first, second = graph
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "synthetic-test-only")
    challenge = AuthChallenge(tenant_id=first["tenant"].id, kind="client_otp", subject=NEW_PHONE,
                              secret_hash=token_hash("123456"), expires_at=now() + timedelta(minutes=1))
    client_db.add(challenge)
    client_db.flush()
    sessions, deliveries = [], []
    for record in graph:
        verify_canonical_phone(client_db, record["client"], PHONE, tenant_id=record["tenant"].id)
        session = AuthSession(tenant_id=record["tenant"].id, role="client", subject_id=record["client"].id,
                              client_subject_id=record["client"].id, token_hash=f"synthetic-{record['tenant'].id}",
                              expires_at=now() + timedelta(hours=1))
        # Source string repetida não concede permissão para minimizar dados de B.
        delivery = WhatsAppDelivery(tenant_id=record["tenant"].id, kind="otp", source_type="auth_challenge",
                                    source_id=str(challenge.id), template_kind="otp", idempotency_key="same-key",
                                    recipient_phone=NEW_PHONE, encrypted_payload="synthetic-envelope")
        client_db.add_all([session, delivery])
        sessions.append(session)
        deliveries.append(delivery)
    client_db.commit()
    result = main.change_client_phone(first["client"].id,
                                      main.PhoneChangeInput(phone_e164=NEW_PHONE, challenge_id=challenge.id, code="123456"),
                                      request(), client_db)
    client_db.expire_all()
    assert result["id"] == str(first["client"].id)
    assert first["client"].phone_e164 == NEW_PHONE and second["client"].phone_e164 == PHONE
    assert sessions[0].revoked_at is not None and sessions[1].revoked_at is None
    assert deliveries[0].encrypted_payload is None and deliveries[0].recipient_phone is None
    assert deliveries[1].encrypted_payload == "synthetic-envelope" and deliveries[1].recipient_phone == NEW_PHONE
    assert challenge.used_at is not None and challenge.subject is None


def test_desafio_de_troca_alheio_nao_consumido(client_db, graph, actor):
    first, second = graph
    challenge = AuthChallenge(tenant_id=second["tenant"].id, kind="client_otp", subject=NEW_PHONE,
                              secret_hash=token_hash("123456"), expires_at=now() + timedelta(minutes=1))
    client_db.add(challenge)
    client_db.commit()
    with pytest.raises(HTTPException):
        main.change_client_phone(first["client"].id,
                                 main.PhoneChangeInput(phone_e164=NEW_PHONE, challenge_id=challenge.id, code="123456"),
                                 request(), client_db)
    assert challenge.used_at is None and challenge.attempts == 0
    assert first["client"].phone_e164 == PHONE and second["client"].phone_e164 == PHONE
