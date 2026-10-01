"""Senha/TOTP e membership administrativos reais, sem deploy ou canal externo."""

from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi import HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import auth, main
from app.auth import AuthChallenge, AuthSession, Role, TenantAdmin
from app.tenancy import TenantContextError, require_admin_tenant, require_single_tenant
from tests.test_tenant_client_auth import request
from tests.test_tenant_client_isolation import client_db as _client_db
from tests.test_tenant_ownership_schema import graph as _graph

client_db = _client_db
graph = _graph
PASSWORD = "Isolated-Local-Password-2026!"


@pytest.fixture
def accounts(client_db, graph, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(auth, "SessionLocal", sessionmaker(bind=client_db.bind, expire_on_commit=False))
    for record in graph:
        admin = record["admin"]
        admin.email = admin.email.lower()
        admin.email_verified = True
        admin.password_hash = auth.password_hasher.hash(PASSWORD)
        admin.totp_secret = pyotp.random_base32()
    client_db.commit()
    return graph


def password(db, admin, secret=PASSWORD):
    result = main.admin_password(auth.AdminPasswordInput(email=admin.email, password=secret), request(), db)
    return db.get(AuthChallenge, UUID(result["challenge_id"]))


def totp(db, row, admin, code=None):
    response = Response()
    result = main.admin_totp(auth.ChallengeVerification(challenge_id=row.id,
        code=code or pyotp.TOTP(admin.totp_secret).now()), request(), response, db)
    cookie = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
    return result, cookie


def membership(db, record):
    return db.scalar(select(TenantAdmin).where(TenantAdmin.tenant_id == record["tenant"].id,
                                              TenantAdmin.admin_user_id == record["admin"].id))


def test_senha_exige_TOTP_e_cookie_identifica_vinculo_proprio_A_B(client_db, accounts):
    for record in accounts:
        row = password(client_db, record["admin"])
        assert row.tenant_id == record["tenant"].id and row.used_at is None
        assert client_db.scalar(select(func.count()).select_from(AuthSession).where(
            AuthSession.tenant_id == record["tenant"].id)) == 0
        result, cookie = totp(client_db, row, record["admin"])
        assert result == {"destination": "/admin"}
        session = auth.current_session(request(cookie), Role.ADMIN)
        assert session.tenant_id == record["tenant"].id
        assert session.admin_subject_id == session.subject_id == record["admin"].id
        with pytest.raises(HTTPException):
            totp(client_db, row, record["admin"])


@pytest.mark.parametrize("mode", ["missing", "revoked", "ambiguous", "suspended", "unverified"])
def test_senha_valida_nao_cria_desafio_sem_vinculo_inequivoco(client_db, accounts, mode):
    record = accounts[0]
    link = membership(client_db, record)
    if mode == "missing":
        client_db.delete(link)
    elif mode == "revoked":
        link.active = False
    elif mode == "ambiguous":
        client_db.add(TenantAdmin(tenant_id=accounts[1]["tenant"].id, admin_user_id=record["admin"].id))
    elif mode == "suspended":
        record["tenant"].status = "suspended"
    else:
        record["admin"].email_verified = False
    client_db.commit()
    with pytest.raises(HTTPException) as exc:
        password(client_db, record["admin"])
    assert exc.value.status_code == 401
    assert client_db.scalar(select(func.count()).select_from(AuthChallenge)) == 0


@pytest.mark.parametrize("mode", ["revoked", "ambiguous", "suspended", "reassigned"])
def test_vinculo_mudou_entre_senha_e_TOTP_nao_consumir_desafio(client_db, accounts, mode):
    record = accounts[0]
    row = password(client_db, record["admin"])
    link = membership(client_db, record)
    if mode in {"revoked", "reassigned"}:
        link.active = False
    if mode in {"ambiguous", "reassigned"}:
        client_db.add(TenantAdmin(tenant_id=accounts[1]["tenant"].id, admin_user_id=record["admin"].id))
    if mode == "suspended":
        record["tenant"].status = "suspended"
    client_db.commit()
    with pytest.raises(HTTPException) as exc:
        totp(client_db, row, record["admin"])
    assert exc.value.status_code == 401
    client_db.refresh(row)
    assert row.used_at is None and row.attempts == 0
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0


@pytest.mark.parametrize("mode", ["revoked", "ambiguous", "suspended", "unverified"])
def test_cookie_revalida_apos_login_sem_afetar_B(client_db, accounts, mode):
    cookies = []
    for record in accounts:
        cookies.append(totp(client_db, password(client_db, record["admin"]), record["admin"])[1])
    first = accounts[0]
    if mode == "revoked":
        membership(client_db, first).active = False
    elif mode == "ambiguous":
        client_db.add(TenantAdmin(tenant_id=accounts[1]["tenant"].id, admin_user_id=first["admin"].id))
    elif mode == "suspended":
        first["tenant"].status = "suspended"
    else:
        first["admin"].email_verified = False
    client_db.commit()
    with pytest.raises(HTTPException) as exc:
        auth.current_session(request(cookies[0]), Role.ADMIN)
    assert exc.value.status_code == 403
    assert auth.current_session(request(cookies[1]), Role.ADMIN).tenant_id == accounts[1]["tenant"].id


def test_header_body_e_query_nao_elegem_conta_e_gate_operacional_permanece(client_db, accounts):
    first = accounts[0]
    forged = request()
    forged.scope["headers"].append((b"x-tenant-id", str(accounts[1]["tenant"].id).encode()))
    forged.scope["query_string"] = f"tenant_id={accounts[1]['tenant'].id}".encode()
    result = main.admin_password(auth.AdminPasswordInput(email=first["admin"].email, password=PASSWORD,
                                tenant_id=accounts[1]["tenant"].id), forged, client_db)
    row = client_db.get(AuthChallenge, UUID(result["challenge_id"]))
    assert row.tenant_id == first["tenant"].id
    assert require_admin_tenant(client_db, first["admin"].id).id == first["tenant"].id
    with pytest.raises(TenantContextError):
        require_single_tenant(client_db)
    with pytest.raises(TenantContextError):
        require_admin_tenant(client_db, uuid4())


def test_senha_errada_TOTP_errado_e_papel_incompativel_nao_autenticam(client_db, accounts):
    record = accounts[0]
    with pytest.raises(HTTPException):
        password(client_db, record["admin"], "wrong-synthetic-password")
    row = password(client_db, record["admin"])
    wrong_code = next(code for code in ("000000", "111111", "222222", "333333")
                      if not pyotp.TOTP(record["admin"].totp_secret).verify(code, valid_window=1))
    with pytest.raises(HTTPException):
        totp(client_db, row, record["admin"], wrong_code)
    client_db.refresh(row)
    assert row.attempts == 1 and row.used_at is None
    _, cookie = totp(client_db, row, record["admin"])
    with pytest.raises(HTTPException):
        auth.current_session(request(cookie), Role.CLIENT)


def test_recuperacao_sem_canal_nao_invalida_desafios_A_B(client_db, accounts, monkeypatch):
    from datetime import timedelta

    from app.admin_account import create_security_challenge
    from app.auth import AdminSecurityChallenge, WhatsAppDelivery, now, pii_fingerprint, token_hash

    monkeypatch.setenv("WHATSAPP_TENANT_BINDINGS", "{}")
    previous = []
    for record in accounts:
        challenge = AdminSecurityChallenge(tenant_id=record["tenant"].id, admin_id=record["admin"].id,
            purpose="password_recovery_otp", subject_fingerprint=pii_fingerprint(record["admin"].email),
            secret_hash=token_hash("654321"), expires_at=now() + timedelta(minutes=10))
        client_db.add(challenge)
        previous.append(challenge)
    client_db.commit()
    for admin in [accounts[0]["admin"], None]:
        challenge, _, queued = create_security_challenge(client_db, purpose="password_recovery_otp",
            subject_fingerprint=pii_fingerprint(admin.email if admin else "unknown@example.test"), admin=admin)
        assert not queued and challenge.admin_id is None and challenge.tenant_id is None
    for challenge in previous:
        client_db.refresh(challenge)
        assert challenge.used_at is None
    assert client_db.scalar(select(func.count()).select_from(WhatsAppDelivery)) == 0
