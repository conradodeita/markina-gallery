"""Provisionamento/seed em schemas exclusivos, sem contas ou credenciais reais."""

import json
from uuid import uuid4

import pyotp
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app import provision_photographer as offline
from app import seed_admin
from app.auth import AdminUser, Base, GlobalPixSettings, Tenant, TenantAdmin
from app.tenancy import TenantContextError
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
PASSWORD = "Lab-only-Password-2026!"
EMAIL = "synthetic@example.test"


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def first_admin(db):
    tenant = Tenant()
    db.add(tenant)
    db.flush()
    admin = AdminUser(email=EMAIL, password_hash="unchanged-synthetic-hash", totp_secret="unchanged-synthetic-totp")
    admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
    db.add(admin)
    db.commit()
    return tenant, admin


def test_dry_run_sem_credenciais_nao_cria_nem_altera(client_db):
    destination = uuid4()
    plan = offline.provision_photographer(client_db, destination, EMAIL, create_tenant=True)
    assert plan.create_tenant and plan.create_admin and plan.create_membership
    client_db.flush()
    assert count(client_db, Tenant) == count(client_db, AdminUser) == count(client_db, TenantAdmin) == 0


def test_criacao_idempotente_preserva_credenciais_e_configuracao(client_db):
    owner, admin = first_admin(client_db)
    client_db.add(GlobalPixSettings(tenant_id=owner.id, admin_user_id=admin.id,
                                    status="active", copy_paste="synthetic-pix-of-a"))
    client_db.commit()
    destination = uuid4()
    created = offline.provision_photographer(client_db, destination, "second@example.test",
                                             create_tenant=True, apply=True, password=PASSWORD,
                                             totp_secret=pyotp.random_base32())
    client_db.commit()
    assert created.create_tenant and created.create_admin
    second = offline.existing_admin_by_email(client_db, "second@example.test")
    fingerprint = (second.id, second.password_hash, second.totp_secret)
    repeated = offline.provision_photographer(client_db, destination, "second@example.test",
                                              apply=True, password="invalid-ignored", totp_secret="invalid-ignored")
    client_db.commit()
    client_db.expire_all()
    assert not repeated.create_tenant and not repeated.create_admin and not repeated.create_membership
    assert (second.id, second.password_hash, second.totp_secret) == fingerprint
    assert count(client_db, Tenant) == count(client_db, AdminUser) == count(client_db, TenantAdmin) == 2
    assert admin.password_hash == "unchanged-synthetic-hash" and admin.totp_secret == "unchanged-synthetic-totp"
    for name, table in Base.metadata.tables.items():
        if "tenant_id" in table.c and name != "tenant_admin":
            assert client_db.scalar(select(func.count()).select_from(table).where(table.c.tenant_id == destination)) == 0, name
    assert client_db.scalar(select(GlobalPixSettings.copy_paste).where(GlobalPixSettings.tenant_id == owner.id)) == "synthetic-pix-of-a"


@pytest.mark.parametrize("kind", ["missing_link", "revoked", "suspended", "ambiguous_membership",
                                  "other_target", "duplicate_email", "occupied_account"])
def test_destino_ambiguo_nao_reparado_nem_reativado(client_db, kind):
    tenant, admin = first_admin(client_db)
    email, destination = EMAIL, tenant.id
    link = client_db.scalar(select(TenantAdmin))
    if kind == "missing_link":
        client_db.execute(delete(TenantAdmin).where(TenantAdmin.id == link.id))
    elif kind == "revoked":
        link.active = False
    elif kind == "suspended":
        tenant.status = "suspended"
    elif kind == "ambiguous_membership":
        other = Tenant()
        client_db.add(other)
        client_db.flush()
        client_db.add(TenantAdmin(tenant_id=other.id, admin_user_id=admin.id))
    elif kind == "other_target":
        destination = uuid4()
    elif kind == "duplicate_email":
        client_db.add(AdminUser(email=EMAIL.upper(), password_hash="other-fake", totp_secret="other-fake"))
    else:
        email = "new-admin@example.test"
    client_db.commit()
    before = tuple(count(client_db, model) for model in (Tenant, AdminUser, TenantAdmin))
    with pytest.raises(TenantContextError):
        offline.provision_photographer(client_db, destination, email, create_tenant=True, apply=True,
                                        password=PASSWORD, totp_secret=pyotp.random_base32())
    client_db.rollback()
    assert tuple(count(client_db, model) for model in (Tenant, AdminUser, TenantAdmin)) == before
    assert admin.password_hash == "unchanged-synthetic-hash" and admin.totp_secret == "unchanged-synthetic-totp"


@pytest.mark.parametrize("password,totp", [(None, None), ("weak", "invalid!"), (PASSWORD, "invalid!")])
def test_credenciais_invalidas_nao_deixam_conta_parcial(client_db, password, totp):
    with pytest.raises(RuntimeError, match="Credenciais"):
        offline.provision_photographer(client_db, uuid4(), EMAIL, create_tenant=True, apply=True,
                                        password=password, totp_secret=totp)
    assert count(client_db, Tenant) == count(client_db, AdminUser) == count(client_db, TenantAdmin) == 0


def test_destino_ausente_exige_intencao_de_criacao(client_db):
    with pytest.raises(TenantContextError, match="criação explícita"):
        offline.provision_photographer(client_db, uuid4(), EMAIL)
    assert count(client_db, Tenant) == 0


def test_seed_repetido_em_duas_contas_sem_reler_credenciais(client_db, monkeypatch):
    tenant, admin = first_admin(client_db)
    client_db.add(Tenant())
    client_db.commit()
    monkeypatch.setattr(seed_admin, "SessionLocal", sessionmaker(bind=client_db.bind))
    monkeypatch.setenv("ADMIN_SEED_EMAIL", EMAIL)
    monkeypatch.delenv("ADMIN_SEED_PASSWORD", raising=False)
    monkeypatch.delenv("ADMIN_SEED_TOTP_SECRET", raising=False)
    seed_admin.seed_admin()
    client_db.expire_all()
    assert admin.password_hash == "unchanged-synthetic-hash" and admin.totp_secret == "unchanged-synthetic-totp"
    assert offline.existing_admin_owner(client_db, admin.id).id == tenant.id
    monkeypatch.setenv("ADMIN_SEED_EMAIL", "new-admin@example.test")
    with pytest.raises(TenantContextError):
        seed_admin.seed_admin()
    assert count(client_db, AdminUser) == 1


def test_cli_dry_run_sanitizado_e_confirmacao_obrigatoria(client_db, monkeypatch, capsys):
    destination = uuid4()
    monkeypatch.setattr(offline, "SessionLocal", sessionmaker(bind=client_db.bind))
    monkeypatch.setenv("ADMIN_SEED_EMAIL", EMAIL)
    monkeypatch.setenv("ADMIN_SEED_PASSWORD", PASSWORD)
    totp = pyotp.random_base32()
    monkeypatch.setenv("ADMIN_SEED_TOTP_SECRET", totp)
    monkeypatch.setattr("sys.argv", ["provision", "--tenant-id", str(destination), "--create-tenant"])
    offline.main()
    output = capsys.readouterr()
    assert json.loads(output.out)["applied"] is False
    assert EMAIL not in output.out and PASSWORD not in output.out and totp not in output.out
    assert count(client_db, Tenant) == 0
    monkeypatch.setattr("sys.argv", ["provision", "--tenant-id", str(destination), "--create-tenant", "--apply"])
    with pytest.raises(SystemExit) as failure:
        offline.main()
    assert failure.value.code == 2
    assert count(client_db, Tenant) == 0
    monkeypatch.setattr("sys.argv", ["provision", "--tenant-id", str(destination), "--create-tenant",
                                      "--apply", "--confirm-tenant", str(destination)])
    offline.main()
    output = capsys.readouterr()
    assert json.loads(output.out)["applied"] is True
    assert EMAIL not in output.out and PASSWORD not in output.out and totp not in output.out
    assert count(client_db, Tenant) == count(client_db, AdminUser) == count(client_db, TenantAdmin) == 1


def test_cli_erro_de_banco_nao_expoe_payload_secreto(monkeypatch, capsys):
    destination = uuid4()

    def unavailable():
        raise SQLAlchemyError("synthetic-secret-payload-must-not-be-logged")

    monkeypatch.setattr(offline, "SessionLocal", unavailable)
    monkeypatch.setattr("sys.argv", ["provision", "--tenant-id", str(destination)])
    with pytest.raises(SystemExit) as failure:
        offline.main()
    output = capsys.readouterr()
    assert failure.value.code == 1 and "Provisionamento recusado" in output.err
    assert "synthetic-secret-payload" not in output.err and "Traceback" not in output.err
