"""OTP e cookies contextualizados em PostgreSQL sintético, sem transporte externo."""

import json
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app import auth, main
from app.auth import (
    AuthChallenge,
    AuthSession,
    Client,
    GalleryAccessCapability,
    GalleryMembershipNotificationOutbox,
    ParentGalleryRegistration,
    Role,
    WhatsAppDelivery,
    now,
    token_hash,
)
from tests.test_tenant_client_isolation import client_db as _client_db
from tests.test_tenant_ownership_schema import graph as _graph

client_db = _client_db
graph = _graph
PHONE = "+5511999990001"
CODE = "123456"


def request(cookie=None):
    headers = [(b"cookie", f"markina_session={cookie}".encode())] if cookie else []
    return Request({"type": "http", "method": "POST", "path": "/auth/client/verify",
                    "headers": headers, "client": ("127.0.0.1", 1234)})


@pytest.fixture
def links(client_db, graph, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv("WHATSAPP_TENANT_BINDINGS", json.dumps({str(row["tenant"].id): label for row, label in zip(graph, ("A", "B"), strict=True)}))
    for label in ("A", "B"):
        monkeypatch.setenv(f"WHATSAPP_BINDING_{label}_PROVIDER", "sandbox")
        monkeypatch.setenv(f"WHATSAPP_BINDING_{label}_CREDENTIAL_ENV", "development")
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "synthetic-auth-fixture-salt")
    monkeypatch.setattr(auth.secrets, "randbelow", lambda _: 123456)
    factory = sessionmaker(bind=client_db.bind, expire_on_commit=False)
    monkeypatch.setattr(auth, "SessionLocal", factory)
    monkeypatch.setattr(main, "SessionLocal", factory)
    result = []
    for record in graph:
        record["parent"].access_mode = "standard"
        token = f"synthetic-{record['admin'].email}" + "x" * 40
        cap = GalleryAccessCapability(tenant_id=record["tenant"].id,
              parent_gallery_id=record["parent"].id, scope="public_gallery",
              token_hash=token_hash(token), actor_admin_id=record["admin"].id)
        client_db.add(cap)
        client_db.flush()
        result.append((token, cap))
    client_db.commit()
    return result


def challenge(db, token, phone=PHONE):
    result = main.client_challenge(main.ClientLinkChallengeInput(
        full_name="Cliente sintética", phone=phone, access_token=token), request(), db)
    return db.get(AuthChallenge, UUID(result["challenge_id"]))


def verify(db, row, token=None, cookie=None, code=CODE):
    response = Response()
    result = main.client_verify(auth.ChallengeVerification(
        challenge_id=row.id, code=code, access_token=token), response, request(cookie), db)
    return result, response


def test_desafios_mesmo_telefone_tem_owner_outbox_e_hash_sem_codigo_aberto(client_db, graph, links):
    rows = [challenge(client_db, token) for token, _cap in links]
    assert rows[0].id != rows[1].id
    for row, record, (_token, cap) in zip(rows, graph, links, strict=True):
        assert row.tenant_id == record["tenant"].id
        assert row.gallery_capability_id == cap.id and row.secret_hash != CODE
        delivery = client_db.scalar(select(WhatsAppDelivery).where(
            WhatsAppDelivery.tenant_id == row.tenant_id,
            WhatsAppDelivery.source_id == str(row.id)))
        assert delivery and delivery.idempotency_key == f"otp:{row.id}:0"
        assert delivery.encrypted_payload != CODE


@pytest.mark.parametrize("operation", ["verify", "resend"])
def test_desafio_A_no_link_B_recusado_antes_de_consumir_ou_reenviar(client_db, links, operation):
    row = challenge(client_db, links[0][0])
    before = (row.secret_hash, row.attempts, row.resend_count, row.used_at)
    with pytest.raises(HTTPException) as exc:
        if operation == "verify":
            verify(client_db, row, links[1][0])
        else:
            main.client_resend(auth.ChallengeResendInput(challenge_id=row.id,
                access_token=links[1][0]), request(), client_db)
    assert exc.value.status_code == 401
    client_db.refresh(row)
    assert (row.secret_hash, row.attempts, row.resend_count, row.used_at) == before
    assert client_db.scalar(select(func.count()).select_from(WhatsAppDelivery)) == 1
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0


@pytest.mark.parametrize("mode", ["invalid", "generic", "uuid"])
def test_entrada_sem_link_valido_nao_cria_desafio_ou_entrega(client_db, graph, links, mode):
    payload = {"full_name": "Cliente sintética", "phone": PHONE}
    if mode == "invalid":
        payload["access_token"] = "invalid" + "x" * 40
    elif mode == "uuid":
        payload["parent_gallery_id"] = graph[0]["parent"].id
    with pytest.raises(HTTPException) as exc:
        main.client_challenge(main.ClientLinkChallengeInput(**payload), request(), client_db)
    assert exc.value.status_code == 401
    assert client_db.scalar(select(func.count()).select_from(AuthChallenge)) == 0
    assert client_db.scalar(select(func.count()).select_from(WhatsAppDelivery)) == 0


def test_login_por_links_reais_cria_cookies_cadastros_e_registros_independentes(client_db, graph, links):
    cookies = []
    for record, (token, _cap) in zip(graph, links, strict=True):
        row = challenge(client_db, token)
        result, response = verify(client_db, row, token)
        assert result["destination"] == f"/public-galleries/{record['parent'].id}"
        cookie = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
        cookies.append(cookie)
        session = auth.current_session(request(cookie), Role.CLIENT)
        assert session.tenant_id == record["tenant"].id
        assert session.subject_id == session.client_subject_id == record["client"].id
        client_db.refresh(row)
        assert row.used_at and row.subject is None and row.client_name is None
        assert client_db.scalar(select(ParentGalleryRegistration.id).where(
            ParentGalleryRegistration.tenant_id == session.tenant_id,
            ParentGalleryRegistration.client_id == session.subject_id))
    assert cookies[0] != cookies[1]
    assert client_db.scalar(select(func.count()).select_from(GalleryMembershipNotificationOutbox)) == 2


def test_cadastro_em_B_nao_reutiliza_telefone_ja_existente_em_A(client_db, graph, links):
    phone = "+5511999990040"
    original = Client(tenant_id=graph[0]["tenant"].id, full_name="Nome próprio A", phone_e164=phone)
    client_db.add(original)
    client_db.commit()
    row = challenge(client_db, links[1][0], phone)
    verify(client_db, row, links[1][0])
    created = client_db.scalar(select(Client).where(Client.tenant_id == graph[1]["tenant"].id,
                                                   Client.phone_e164 == phone))
    assert created and created.id != original.id and created.full_name == "Cliente sintética"
    assert original.full_name == "Nome próprio A"


@pytest.mark.parametrize("mode", ["suspended", "revoked", "inactive_parent"])
def test_revalidacao_antes_do_OTP_nao_consume_contexto_indisponivel(client_db, graph, links, mode):
    row = challenge(client_db, links[0][0])
    if mode == "suspended":
        graph[0]["tenant"].status = "suspended"
    elif mode == "revoked":
        links[0][1].status = "revoked"
    else:
        graph[0]["parent"].active = False
    client_db.commit()
    with pytest.raises(HTTPException) as exc:
        verify(client_db, row, links[0][0])
    assert exc.value.status_code == 401
    client_db.refresh(row)
    assert row.used_at is None and row.attempts == 0


def test_rotacao_e_suspensao_de_A_preservam_cookie_B(client_db, graph, links):
    cookies = []
    for record in graph:
        response = Response()
        cookies.append(auth.create_session(client_db, response, Role.CLIENT, record["client"].id,
                                            tenant_id=record["tenant"].id))
    auth.create_session(client_db, Response(), Role.CLIENT, graph[0]["client"].id,
                        tenant_id=graph[0]["tenant"].id)
    with pytest.raises(HTTPException):
        auth.current_session(request(cookies[0]), Role.CLIENT)
    assert auth.current_session(request(cookies[1]), Role.CLIENT).tenant_id == graph[1]["tenant"].id
    graph[1]["tenant"].status = "suspended"
    client_db.commit()
    with pytest.raises(HTTPException):
        auth.current_session(request(cookies[1]), Role.CLIENT)


def test_sessao_cliente_exige_cadastro_da_conta_sem_fallback(client_db, graph, links):
    with pytest.raises(HTTPException):
        auth.create_session(client_db, Response(), Role.CLIENT, graph[0]["client"].id,
                            tenant_id=graph[1]["tenant"].id)
    with pytest.raises(HTTPException):
        auth.create_session(client_db, Response(), Role.CLIENT, graph[0]["client"].id)
    legacy = AuthSession(role="client", subject_id=uuid4(), token_hash=token_hash("legacy"),
                         revoked_at=now(), expires_at=now()+timedelta(hours=1))
    client_db.add(legacy)
    client_db.commit()
    with pytest.raises(HTTPException):
        auth.current_session(request("legacy"), Role.CLIENT)


def test_reenvio_rotaciona_so_A_e_preserva_entrega_e_codigo_B(client_db, links, monkeypatch):
    first = challenge(client_db, links[0][0])
    second = challenge(client_db, links[1][0])
    old_b = client_db.scalar(select(WhatsAppDelivery).where(WhatsAppDelivery.tenant_id == second.tenant_id))
    before = (old_b.status, old_b.encrypted_payload, old_b.recipient_phone, old_b.updated_at)
    monkeypatch.setattr(auth.secrets, "randbelow", lambda _: 654321)
    main.client_resend(auth.ChallengeResendInput(challenge_id=first.id, access_token=links[0][0]),
                       request(), client_db)
    client_db.refresh(first)
    client_db.refresh(second)
    client_db.refresh(old_b)
    assert first.secret_hash == token_hash("654321") and first.resend_count == 1
    assert second.secret_hash == token_hash(CODE) and second.resend_count == 0
    assert (old_b.status, old_b.encrypted_payload, old_b.recipient_phone, old_b.updated_at) == before
    assert client_db.scalar(select(func.count()).select_from(WhatsAppDelivery).where(
        WhatsAppDelivery.tenant_id == first.tenant_id)) == 2
    with pytest.raises(HTTPException):
        verify(client_db, first, links[0][0], code=CODE)
    verify(client_db, second, links[1][0])
    verify(client_db, first, links[0][0], code="654321")


def test_codigo_de_A_nao_valida_desafio_B(client_db, links, monkeypatch):
    codes = iter((123456, 234567))
    monkeypatch.setattr(auth.secrets, "randbelow", lambda _: next(codes))
    first = challenge(client_db, links[0][0])
    second = challenge(client_db, links[1][0])
    with pytest.raises(HTTPException) as exc:
        verify(client_db, second, links[1][0], code=CODE)
    assert exc.value.status_code == 401
    client_db.refresh(first)
    client_db.refresh(second)
    assert first.attempts == 0 and first.used_at is None
    assert second.attempts == 1 and second.used_at is None


def test_rate_limit_global_nao_pode_ser_contornado_trocando_conta(client_db, links, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "2")
    challenge(client_db, links[0][0])
    challenge(client_db, links[1][0])
    with pytest.raises(HTTPException) as exc:
        challenge(client_db, links[0][0])
    assert exc.value.status_code == 429
    assert client_db.scalar(select(func.count()).select_from(AuthChallenge)) == 2


def test_sessao_valida_e_contexto_generico_para_reautenticacao(client_db, graph, links):
    owner = graph[0]["tenant"].id
    cookie = auth.create_session(client_db, Response(), Role.CLIENT, graph[0]["client"].id, tenant_id=owner)
    result = main.client_challenge(main.ClientLinkChallengeInput(
        full_name="Nome sintético", phone=PHONE), request(cookie), client_db)
    row = client_db.get(AuthChallenge, UUID(result["challenge_id"]))
    assert row.tenant_id == owner and row.gallery_capability_id is None
    verify(client_db, row, cookie=cookie)


@pytest.mark.parametrize("mode", ["expired", "used", "attempts"])
def test_desafio_terminal_recusado_sem_sessao(client_db, links, mode):
    row = challenge(client_db, links[0][0])
    if mode == "expired":
        row.expires_at = now()-timedelta(seconds=1)
    elif mode == "used":
        row.used_at = now()
    else:
        row.attempts = 5
    client_db.commit()
    with pytest.raises(HTTPException) as exc:
        verify(client_db, row, links[0][0])
    assert exc.value.status_code == 401
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0


def test_link_da_mesma_conta_nao_substitui_link_original_revogado(client_db, graph, links):
    row = challenge(client_db, links[0][0])
    token = "another-valid-token" + "x"*40
    cap = GalleryAccessCapability(tenant_id=graph[0]["tenant"].id,
          parent_gallery_id=graph[0]["parent"].id, scope="public_gallery", token_hash=token_hash(token))
    client_db.add(cap)
    links[0][1].status = "revoked"
    client_db.commit()
    with pytest.raises(HTTPException):
        verify(client_db, row, token)
    client_db.refresh(row)
    assert row.used_at is None and row.attempts == 0


@pytest.mark.parametrize("scope", ["private_invite", "private_client_invite", "private_gallery_link"])
def test_convite_privado_preserva_owner_e_nao_autentica_outro_fotografo(client_db, graph, links, scope):
    record = graph[0]
    cap = links[0][1]
    with client_db.no_autoflush:
        cap.scope = scope
        cap.derived_gallery_id = record["gallery"].id
        cap.client_id = record["client"].id if scope != "private_gallery_link" else None
    client_db.commit()
    row = challenge(client_db, links[0][0])
    result, response = verify(client_db, row, links[0][0])
    assert result["destination"] == f"/gallery/{record['gallery'].id}"
    cookie = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
    assert auth.current_session(request(cookie)).tenant_id == record["tenant"].id
    assert client_db.scalar(select(func.count()).select_from(AuthSession).where(
        AuthSession.tenant_id == graph[1]["tenant"].id)) == 0
    with pytest.raises(HTTPException):
        verify(client_db, row, links[0][0])
