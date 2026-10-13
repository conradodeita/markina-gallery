"""Preparação por conta/sessão, com OTP sintético e sem transporte externo."""

from datetime import timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app import admin_account, main
from app.admin_security import encrypt_sensitive_payload
from app.auth import AdminSecurityChallenge, InfinitePaySettings, Role, TenantAdmin, now
from app.infinitepay_settings import (
    ConfigurationChallengeInput,
    ConfigurationConfirmInput,
    ConfigurationResendInput,
    ReceiverInput,
)
from tests.test_tenant_client_auth import request
from tests.test_tenant_client_navigation import cookie
from tests.test_tenant_configuration import PASSWORD
from tests.test_tenant_configuration import client_db as _client_db
from tests.test_tenant_configuration import configured as _configured
from tests.test_tenant_configuration import graph as _graph
from tests.test_tenant_configuration import links as _links

client_db = _client_db
configured = _configured
graph = _graph
links = _links


@pytest.fixture(autouse=True)
def synthetic_recipient(monkeypatch):
    monkeypatch.setattr(admin_account, "_admin_whatsapp_phone", lambda _db, *, tenant_id: "+5511999990010")


def issue(db, row, handle="synthetic_a", version=0, checkout_ready=False, card_enabled=False):
    result = main.admin_infinitepay_challenge(ConfigurationChallengeInput(current_password=PASSWORD,
        expected_version=version, configuration=ReceiverInput(handle=handle) if handle else None,
        checkout_ready=checkout_ready, card_enabled=card_enabled),
        row["admin_request"], db)
    return db.get(AdminSecurityChallenge, UUID(result["challenge_id"]))


def confirm(db, row, challenge, code="123456"):
    return main.admin_infinitepay_confirm(ConfigurationConfirmInput(challenge_id=challenge.id, code=code),
                                         row["admin_request"], db)


def test_configurar_alterar_remover_preserva_PIX_e_conta_B(client_db, configured):
    first, second = configured
    pix = [main.admin_global_pix(row["admin_request"], client_db) for row in configured]
    assert main.admin_infinitepay(first["admin_request"], client_db)["status"] == "unconfigured"
    challenge = issue(client_db, first, " $synthetic_a ")
    assert "synthetic_a" not in challenge.encrypted_target
    assert challenge.secret_hash != "123456"
    result = confirm(client_db, first, challenge)
    assert result == {"handle": "synthetic_a", "status": "pending", "version": 1,
        "card_enabled": False, "ownership_verified": False, "checkout_available": False,
        "message": "Cartão indisponível até o fotógrafo habilitar uma configuração pronta."}
    assert challenge.encrypted_target is None and challenge.used_at is not None
    assert confirm(client_db, first, issue(client_db, first, "synthetic_new", 1))["version"] == 2
    removed = confirm(client_db, first, issue(client_db, first, None, 2))
    assert removed["status"] == "inactive" and removed["handle"] is None and removed["version"] == 3
    assert main.admin_infinitepay(second["admin_request"], client_db)["status"] == "unconfigured"
    assert [main.admin_global_pix(row["admin_request"], client_db) for row in configured] == pix


def test_ativacao_e_autodeclaracao_vinculada_e_nao_prova_titularidade(client_db, configured):
    first = configured[0]
    saved = confirm(client_db, first, issue(client_db, first, checkout_ready=True, card_enabled=True))
    assert saved["status"] == "active" and saved["checkout_available"] is True
    assert saved["card_enabled"] is True
    assert saved["ownership_verified"] is False
    assert client_db.scalar(select(InfinitePaySettings)).verification_profile == "infinitepay-public-v1"
    disabled = confirm(client_db, first, issue(client_db, first, version=1,
        checkout_ready=True, card_enabled=False))
    assert disabled["status"] == "active" and disabled["card_enabled"] is False
    assert disabled["checkout_available"] is False
    assert disabled["handle"] == saved["handle"]
    pending = confirm(client_db, first, issue(client_db, first, "changed_tag", version=2))
    assert pending["status"] == "pending" and pending["checkout_available"] is False


@pytest.mark.parametrize("action", ["confirm", "resend"])
@pytest.mark.parametrize("foreign", ["tenant", "session"])
def test_desafio_estrangeiro_nao_consumido(client_db, configured, action, foreign):
    first, second = configured
    challenge = issue(client_db, first)
    actor = second if foreign == "tenant" else dict(first,
        admin_request=request(cookie(client_db, first, Role.ADMIN)))
    with pytest.raises(HTTPException) as exc:
        if action == "confirm":
            confirm(client_db, actor, challenge)
        else:
            main.admin_infinitepay_resend(ConfigurationResendInput(challenge_id=challenge.id),
                                         actor["admin_request"], client_db)
    assert exc.value.status_code == 401
    assert challenge.used_at is None and challenge.attempts == 0 and challenge.resend_count == 0


@pytest.mark.parametrize("invalid", ["expired", "proposal", "revoked", "used", "version"])
def test_confirmacao_invalida_preserva_configuracao(client_db, configured, invalid):
    first = configured[0]
    challenge = issue(client_db, first)
    if invalid == "expired":
        challenge.expires_at = now() - timedelta(seconds=1)
    elif invalid == "proposal":
        challenge.encrypted_target = encrypt_sensitive_payload(
            {"target": '{"handle":"foreign","version":0}'},
            context=f"admin-challenge:{challenge.id}:change_infinitepay_otp")
    elif invalid == "revoked":
        client_db.scalar(select(TenantAdmin).where(TenantAdmin.tenant_id == first["tenant"].id)).active = False
    elif invalid == "used":
        challenge.used_at = now()
    else:
        client_db.add(InfinitePaySettings(tenant_id=first["tenant"].id,
            admin_user_id=first["admin"].id, handle="existing", version=1))
    client_db.commit()
    with pytest.raises(HTTPException):
        confirm(client_db, first, challenge)
    client_db.rollback()
    settings = client_db.scalar(select(InfinitePaySettings))
    assert (settings.handle if settings else None) == ("existing" if invalid == "version" else None)


def test_tentativas_limitadas_e_codigo_correto_apos_limite_recusado(client_db, configured):
    first = configured[0]
    challenge = issue(client_db, first)
    for attempt in range(1, 6):
        with pytest.raises(HTTPException):
            confirm(client_db, first, challenge, "000000")
        client_db.refresh(challenge)
        assert challenge.attempts == attempt
    with pytest.raises(HTTPException):
        confirm(client_db, first, challenge)
    assert challenge.used_at is not None and challenge.encrypted_target is None


def test_reenvio_limitado_e_vinculo_revogado(client_db, configured):
    first = configured[0]
    challenge = issue(client_db, first)
    payload = ConfigurationResendInput(challenge_id=challenge.id)
    for count in range(1, 4):
        main.admin_infinitepay_resend(payload, first["admin_request"], client_db)
        assert challenge.resend_count == count
    with pytest.raises(HTTPException):
        main.admin_infinitepay_resend(payload, first["admin_request"], client_db)
    challenge = issue(client_db, first)
    client_db.scalar(select(TenantAdmin).where(TenantAdmin.tenant_id == first["tenant"].id)).active = False
    client_db.commit()
    with pytest.raises(HTTPException):
        main.admin_infinitepay_resend(ConfigurationResendInput(challenge_id=challenge.id),
                                     first["admin_request"], client_db)
    assert challenge.resend_count == 0


def test_senha_versao_incorretas_e_canal_ausente_nao_configuram(client_db, configured, monkeypatch):
    first = configured[0]
    for password, version in (("wrong", 0), (PASSWORD, 9)):
        with pytest.raises(HTTPException):
            main.admin_infinitepay_challenge(ConfigurationChallengeInput(current_password=password,
                expected_version=version, configuration=ReceiverInput(handle="synthetic")),
                first["admin_request"], client_db)
    monkeypatch.setattr(admin_account, "_admin_whatsapp_phone", lambda _db, *, tenant_id: None)
    with pytest.raises(HTTPException) as exc:
        issue(client_db, first)
    assert exc.value.status_code == 409
    assert client_db.scalar(select(InfinitePaySettings)) is None


def test_payload_nao_aceita_tenant_ativacao_chave_ou_proposta_na_confirmacao():
    for field in ("tenant_id", "status", "api_key"):
        with pytest.raises(ValidationError):
            ReceiverInput.model_validate({"handle": "synthetic", field: "foreign"})
    with pytest.raises(ValidationError):
        ConfigurationConfirmInput.model_validate({"challenge_id": "00000000-0000-0000-0000-000000000001",
                                                  "code": "123456", "configuration": {"handle": "foreign"}})
