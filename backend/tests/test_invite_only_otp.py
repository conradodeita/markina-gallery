"""Regressões OTP com contas sintéticas, sem envio externo."""

import base64
from datetime import timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app import auth, main
from app.auth import (
    AuthChallenge,
    AuthSession,
    Client,
    GalleryClientState,
    ParentGalleryRegistration,
    WhatsAppDelivery,
    now,
)
from tests.test_tenant_client_auth import (
    CODE,
    PHONE,
    challenge,
    request,
    verify,
)
from tests.test_tenant_client_auth import (
    client_db as _client_db,
)
from tests.test_tenant_client_auth import (
    graph as _graph,
)
from tests.test_tenant_client_auth import (
    links as _links,
)

client_db = _client_db
graph = _graph
links = _links


def register(db, record):
    row = ParentGalleryRegistration(
        tenant_id=record['tenant'].id, parent_gallery_id=record['parent'].id,
        client_id=record['client'].id, status='active',
    )
    db.add(row)
    db.commit()
    return row


def deliveries(db, row):
    return list(db.scalars(select(WhatsAppDelivery).where(
        WhatsAppDelivery.source_type == 'auth_challenge',
        WhatsAppDelivery.source_id == str(row.id),
    )))


def resend(db, row, token):
    return main.client_resend(auth.ChallengeResendInput(
        challenge_id=row.id, access_token=token,
    ), request(), db)


def test_invite_only_mesmo_telefone_nao_empresta_vinculo_entre_contas(client_db, graph, links):
    for record in graph:
        record['parent'].access_mode = 'invite_only'
    register(client_db, graph[0])
    responses = [main.client_challenge(main.ClientLinkChallengeInput(
        full_name='Cliente sintética', phone=PHONE, access_token=token,
    ), request(), client_db) for token, _ in links]
    assert responses[0]['message'] == responses[1]['message']
    assert responses[0].keys() == responses[1].keys()
    rows = [client_db.get(AuthChallenge, UUID(result['challenge_id'])) for result in responses]
    assert len(deliveries(client_db, rows[0])) == 1
    assert deliveries(client_db, rows[0])[0].tenant_id == graph[0]['tenant'].id
    assert deliveries(client_db, rows[1]) == []
    assert resend(client_db, rows[1], links[1][0])['message'].startswith('Se os dados')
    assert deliveries(client_db, rows[1]) == []
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0
    assert client_db.scalar(select(func.count()).select_from(ParentGalleryRegistration)) == 1
    assert client_db.scalar(select(func.count()).select_from(Client)) == 2


def test_vinculo_posterior_exige_reenvio_e_permite_otp(client_db, graph, links):
    record = graph[0]
    record['parent'].access_mode = 'invite_only'
    client_db.commit()
    row = challenge(client_db, links[0][0])
    assert deliveries(client_db, row) == []
    register(client_db, record)
    with pytest.raises(HTTPException) as exc:
        verify(client_db, row, links[0][0])
    assert exc.value.status_code == 401
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0
    assert row.used_at is None
    resend(client_db, row, links[0][0])
    sent = deliveries(client_db, row)
    assert len(sent) == 1 and sent[0].recipient_phone == PHONE
    assert sent[0].tenant_id == record['tenant'].id
    result, response = verify(client_db, row, links[0][0])
    assert result['destination'] == f"/public-galleries/{record['parent'].id}"
    assert 'set-cookie' in response.headers


@pytest.mark.parametrize('phone', [PHONE, '+5511999990099'])
def test_convite_individual_somente_destinatario_recebe(client_db, graph, links, phone):
    record = graph[0]
    record['parent'].access_mode = 'invite_only'
    token, cap = links[0]
    with client_db.no_autoflush:
        cap.scope = 'parent_invite'
        cap.client_id = record['client'].id
    client_db.commit()
    row = challenge(client_db, token, phone)
    assert len(deliveries(client_db, row)) == int(phone == PHONE)
    assert client_db.scalar(select(func.count()).select_from(ParentGalleryRegistration)) == 0
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0
    if phone == PHONE:
        result, _ = verify(client_db, row, token)
        assert result['destination'] == f"/public-galleries/{record['parent'].id}"
        assert client_db.scalar(select(ParentGalleryRegistration.status)) == 'active'


@pytest.mark.parametrize('state', ['pending', 'revoked', 'blocked'])
def test_reenvio_sem_vinculo_ativo_invalida_entrega_pendente(
    client_db, graph, links, monkeypatch, state,
):
    monkeypatch.setenv('WHATSAPP_OTP_ENCRYPTION_KEY', base64.urlsafe_b64encode(b'S' * 32).decode())
    record = graph[0]
    record['parent'].access_mode = 'invite_only'
    registration = register(client_db, record)
    row = challenge(client_db, links[0][0])
    assert len(deliveries(client_db, row)) == 1
    assert deliveries(client_db, row)[0].status == 'queued'
    assert deliveries(client_db, row)[0].encrypted_payload
    if state == 'blocked':
        individual = client_db.scalar(select(GalleryClientState).where(
            GalleryClientState.parent_gallery_id == record['parent'].id,
            GalleryClientState.client_id == record['client'].id,
        ))
        individual.status = 'blocked'
    else:
        registration.status = state
    client_db.commit()
    resend(client_db, row, links[0][0])
    sent = deliveries(client_db, row)
    assert len(sent) == 1 and sent[0].status == 'expired'
    assert sent[0].encrypted_payload is None
    assert row.resend_count == 1
    registration.status = 'active'
    if state == 'blocked':
        individual.status = 'active'
    client_db.commit()
    with pytest.raises(HTTPException):
        verify(client_db, row, links[0][0], code=CODE)
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0


@pytest.mark.parametrize('state', ['revoked', 'expired'])
def test_convite_invalidado_nao_entrega_reenvio(client_db, graph, links, state):
    record = graph[0]
    record['parent'].access_mode = 'invite_only'
    token, cap = links[0]
    cap.scope, cap.client_id = 'parent_invite', record['client'].id
    client_db.commit()
    row = challenge(client_db, token)
    if state == 'expired':
        cap.expires_at = now() - timedelta(seconds=1)
    else:
        cap.status = state
    client_db.commit()
    with pytest.raises(HTTPException) as exc:
        resend(client_db, row, token)
    assert exc.value.status_code == 401
    assert len(deliveries(client_db, row)) == 1
    assert row.resend_count == 0
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0


@pytest.mark.parametrize('scope', ['private_invite', 'private_client_invite', 'private_gallery_link'])
@pytest.mark.parametrize('lifecycle', ['active', 'deleted'])
def test_contexto_privado_preserva_envio_e_reenvio(client_db, graph, links, scope, lifecycle):
    record = graph[0]
    record['parent'].access_mode = 'invite_only'
    record['parent'].lifecycle_status = lifecycle
    record['parent'].active = lifecycle == 'active'
    token, cap = links[0]
    with client_db.no_autoflush:
        cap.scope = scope
        cap.derived_gallery_id = record['gallery'].id
        cap.client_id = None if scope == 'private_gallery_link' else record['client'].id
    if scope == 'private_gallery_link':
        extra = Client(tenant_id=record['tenant'].id,
                       full_name='Outra cliente sintética', phone_e164='+5511999990040')
        client_db.add(extra)
        phone = extra.phone_e164
    else:
        phone = PHONE
    client_db.commit()
    row = challenge(client_db, token, phone)
    assert len(deliveries(client_db, row)) == 1
    resend(client_db, row, token)
    assert len(deliveries(client_db, row)) == 2
    assert all(item.tenant_id == record['tenant'].id for item in deliveries(client_db, row))
    assert client_db.scalar(select(func.count()).select_from(ParentGalleryRegistration)) == 0
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0
    result, _ = verify(client_db, row, token)
    assert result['destination'] == f"/gallery/{record['gallery'].id}"


@pytest.mark.parametrize('scope', ['private_invite', 'private_client_invite'])
def test_convite_privado_outro_telefone_nao_recebe(client_db, graph, links, scope):
    record = graph[0]
    record['parent'].access_mode = 'invite_only'
    token, cap = links[0]
    with client_db.no_autoflush:
        cap.scope, cap.client_id = scope, record['client'].id
        cap.derived_gallery_id = record['gallery'].id
    client_db.commit()
    row = challenge(client_db, token, '+5511999990099')
    assert deliveries(client_db, row) == []
    resend(client_db, row, token)
    assert deliveries(client_db, row) == []
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0
