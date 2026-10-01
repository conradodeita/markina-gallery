"""Contratos de entrada/biblioteca e prova administrativa com owner real."""

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, Response
from sqlalchemy import func, select

from app import auth, main
from app.auth import AuthChallenge, ParentGalleryRegistration, Role, WhatsAppDelivery
from tests.test_tenant_client_auth import (
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


def cookie(db, record, role=Role.CLIENT):
    if role == Role.ADMIN:
        record["admin"].email_verified = True
        db.commit()
    subject = record["client"] if role == Role.CLIENT else record["admin"]
    return auth.create_session(db, Response(), role, subject.id, tenant_id=record["tenant"].id)


def test_cookie_A_nao_aplica_link_B_nem_cria_registro_cruzado(client_db, graph, links):
    first_cookie = cookie(client_db, graph[0])
    with pytest.raises(HTTPException) as exc:
        main.access_public_gallery_with_session(main.PublicGalleryAccessInput(access_token=links[1][0]),
                                                request(first_cookie), client_db)
    assert exc.value.status_code == 403
    client_db.refresh(links[1][1])
    assert links[1][1].last_used_at is None
    assert client_db.scalar(select(func.count()).select_from(ParentGalleryRegistration)) == 0


def test_biblioteca_e_destino_de_A_B_conservam_cadastros_independentes(client_db, graph, links):
    for record, (token, _cap) in zip(graph, links, strict=True):
        _result, response = verify(client_db, challenge(client_db, token), token)
        value = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
        payload = main.client_library(request(value), client_db)
        serialized = str(payload)
        assert str(record["parent"].id) in serialized
        other = graph[1] if record is graph[0] else graph[0]
        assert str(other["parent"].id) not in serialized and str(other["client"].id) not in serialized
        assert main.destination(request(value))["destination"] == f"/public-galleries/{record['parent'].id}"


def test_prova_administrativa_sem_galeria_usa_owner_e_numero_de_B_nao_conflita(client_db, graph, links):
    first = graph[0]
    value = cookie(client_db, first, Role.ADMIN)
    graph[1]["client"].phone_e164 = "+5511999990060"
    client_db.commit()
    phone = graph[1]["client"].phone_e164
    result = main.challenge_client_phone(first["client"].id,
        main.PhoneChangeChallengeInput(phone_e164=phone), request(value), client_db)
    row = client_db.get(AuthChallenge, UUID(result["challenge_id"]))
    assert row.tenant_id == first["tenant"].id and row.parent_gallery_id is None
    assert client_db.scalar(select(WhatsAppDelivery).where(
        WhatsAppDelivery.source_id == str(row.id))).tenant_id == first["tenant"].id
    main.change_client_phone(first["client"].id,
        main.PhoneChangeInput(phone_e164=phone, challenge_id=row.id, code="123456"), request(value), client_db)
    client_db.refresh(graph[1]["client"])
    client_db.refresh(first["client"])
    assert first["client"].phone_e164 == phone
    assert graph[1]["client"].phone_e164 == phone


@pytest.mark.parametrize("target", ["foreign", "missing"])
def test_prova_admin_UUID_indisponivel_recusa_antes_de_OTP(client_db, graph, links, target):
    value = cookie(client_db, graph[0], Role.ADMIN)
    client_id = graph[1]["client"].id if target == "foreign" else uuid4()
    with pytest.raises(HTTPException) as exc:
        main.challenge_client_phone(client_id, main.PhoneChangeChallengeInput(phone_e164="+5511999990020"),
                                    request(value), client_db)
    assert exc.value.status_code == 404 and exc.value.detail == "Cliente não encontrado."
    assert client_db.scalar(select(func.count()).select_from(AuthChallenge)) == 0
    assert client_db.scalar(select(func.count()).select_from(WhatsAppDelivery)) == 0
