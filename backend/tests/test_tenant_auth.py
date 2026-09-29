"""Sessões legadas e vínculo revalidado; nenhuma credencial ou sessão real."""

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import auth
from app.auth import AdminUser, AuthSession, Role, Tenant, TenantAdmin
from app.tenancy import TenantContextError, require_admin_tenant, require_single_tenant
from tests.test_tenant_foundation import tenant_db as foundation_tenant_db

tenant_db = foundation_tenant_db


@pytest.fixture
def admin_access(tenant_db, monkeypatch):
    tenant = Tenant()
    tenant_db.add(tenant)
    tenant_db.flush()
    admin = AdminUser(email="admin@example.test", password_hash="synthetic", totp_secret="synthetic")
    admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
    tenant_db.add(admin)
    tenant_db.flush()
    tenant_db.add(AuthSession(role="admin", subject_id=admin.id,
                             token_hash=auth.token_hash("synthetic-session"),
                             expires_at=auth.now() + timedelta(days=7)))
    tenant_db.commit()
    monkeypatch.setattr(auth, "SessionLocal", sessionmaker(bind=tenant_db.bind, expire_on_commit=False))
    request = Request({"type": "http", "headers": [(b"cookie", b"markina_session=synthetic-session")]})
    return admin, tenant, request


def test_sessao_preexistente_valida(tenant_db, admin_access):
    admin, tenant, request = admin_access
    session = auth.current_session(request, Role.ADMIN)
    assert session.subject_id == admin.id
    assert require_admin_tenant(tenant_db, session.subject_id).id == tenant.id


@pytest.mark.parametrize("remove", [False, True])
def test_vinculo_revogado_ou_ausente_bloqueia(tenant_db, admin_access, remove):
    _, _, request = admin_access
    link = tenant_db.scalar(select(TenantAdmin))
    if remove:
        tenant_db.delete(link)
    else:
        link.active = False
    tenant_db.commit()
    with pytest.raises(HTTPException) as caught:
        auth.current_session(request, Role.ADMIN)
    assert caught.value.status_code == 403 and caught.value.detail == "Acesso negado."


def test_contexto_externo_nao_substitui_vinculo(tenant_db, admin_access):
    admin, tenant, request = admin_access
    request.scope["headers"].append((b"x-tenant-id", str(uuid4()).encode()))
    request.scope["query_string"] = f"tenant_id={uuid4()}".encode()
    assert require_admin_tenant(tenant_db, auth.current_session(request).subject_id).id == tenant.id
    assert auth.current_session(request).subject_id == admin.id


@pytest.mark.parametrize("invalid", ["suspended", "second"])
def test_conta_invalida_bloqueia_sessao_e_novo_login(tenant_db, admin_access, invalid):
    admin, tenant, request = admin_access
    if invalid == "suspended":
        tenant.status = "suspended"
    else:
        tenant_db.add(Tenant())
    tenant_db.commit()
    with pytest.raises(HTTPException):
        auth.current_session(request, Role.ADMIN)
    with pytest.raises(HTTPException):
        auth.create_session(tenant_db, Response(), Role.ADMIN, admin.id)
    with pytest.raises(TenantContextError):
        require_single_tenant(tenant_db)


def test_instalacao_sem_conta_nao_escolhe_fallback(tenant_db):
    with pytest.raises(TenantContextError):
        require_single_tenant(tenant_db)
