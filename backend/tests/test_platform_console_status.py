"""Suspensão explícita e auditoria preservam autenticação e obrigações existentes."""

from datetime import UTC, datetime, timedelta
from functools import partial
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pyotp
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app import platform_console as console
from app.acervo_context import require_active_owner
from app.auth import ParentGallery, PlatformAdminEvent, Tenant, password_hasher
from app.payment_availability import lock_payment_account
from app.tenancy import TenantContextError, enable_domain_guard
from app.tenant_hosts import public_gallery_url_for_tenant, tenant_for_host
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db

PASSWORD = "OnlySyntheticTest!20261103"
SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


def context(db):
    owner_tenant, tenant, owner, photographer = create_accounts(db)
    owner.password_hash = password_hasher.hash(PASSWORD)
    owner.totp_secret = SECRET
    db.commit()
    return SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id), tenant.id, photographer.id


def payload(**changes):
    values = {"request_id": uuid4(), "expected_status": "active", "status": "suspended",
              "current_password": PASSWORD, "totp_code": pyotp.TOTP(SECRET).now()}
    values.update(changes)
    return console.StatusInput(**values)


def hostname_payload(**changes):
    values = {"request_id": uuid4(), "expected_hostname": "synthetic.pickyourpic.com.br",
              "expected_status": "reserved", "evidence_sha256": sha256(b"synthetic readiness report").hexdigest(),
              "confirm_readiness": True, "current_password": PASSWORD,
              "totp_code": pyotp.TOTP(SECRET).now()}
    values.update(changes)
    return console.HostnameActivationInput(**values)


def reserve_host(db, tenant_id, hostname="synthetic.pickyourpic.com.br"):
    tenant = db.get(Tenant, tenant_id)
    tenant.canonical_host = hostname
    tenant.canonical_host_status = "reserved"
    db.commit()
    return tenant


def test_status_reauthentication_idempotency_and_history_preserve_business(client_db, monkeypatch):
    at = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
    totp = pyotp.TOTP(SECRET)
    initial_code = totp.at(at)
    monkeypatch.setattr(console, "matching_unused_totp_step",
                        partial(console.matching_unused_totp_step, at=at))
    session, target, _ = context(client_db)
    gallery = ParentGallery(tenant_id=target, name="Preserved synthetic gallery")
    client_db.add(gallery)
    client_db.commit()
    intention = payload(totp_code=initial_code)
    assert console.change_tenant_status(client_db, session, target, intention)["replayed"] is False
    client_db.commit()
    assert client_db.get(Tenant, target, populate_existing=True).status == "suspended"
    assert client_db.get(ParentGallery, gallery.id).name == "Preserved synthetic gallery"
    assert console.change_tenant_status(client_db, session, target, intention)["replayed"] is True
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent)) == 1
    entry = client_db.scalar(select(PlatformAdminEvent))
    assert (entry.action, entry.result, entry.previous_status, entry.next_status) == ("tenant.suspend", "success", "active", "suspended")
    assert PASSWORD not in str(entry.__dict__) and SECRET not in str(entry.__dict__)
    with pytest.raises(HTTPException) as mismatch:
        console.change_tenant_status(client_db, session, session.tenant_id, intention)
    assert mismatch.value.status_code == 409
    # Novo comando não pode reutilizar o passo TOTP já consumido.
    with pytest.raises(HTTPException) as replay:
        console.change_tenant_status(client_db, session, target,
            payload(expected_status="suspended", status="active", totp_code=initial_code))
    assert replay.value.status_code == 403
    assert client_db.get(Tenant, target).status == "suspended"
    future = totp.at(at + timedelta(seconds=totp.interval))
    result = console.change_tenant_status(client_db, session, target,
        payload(expected_status="suspended", status="active", totp_code=future))
    client_db.commit()
    assert result["status"] == "active"


def test_invalid_credentials_self_suspension_and_stale_state_never_change_tenant(client_db):
    session, target, photographer_id = context(client_db)
    with pytest.raises(HTTPException) as bad:
        console.change_tenant_status(client_db, session, target, payload(current_password="invalid"))
    assert bad.value.status_code == 403
    with pytest.raises(HTTPException) as malformed:
        console.change_tenant_status(client_db, session, target, payload(totp_code="١٢٣٤٥٦"))
    assert malformed.value.status_code == 403
    assert client_db.get(Tenant, target).status == "active"
    assert client_db.scalar(select(PlatformAdminEvent.result)) == "denied"
    with pytest.raises(HTTPException) as stale:
        console.change_tenant_status(client_db, session, target, payload(expected_status="suspended"))
    assert stale.value.status_code == 409
    with pytest.raises(HTTPException) as self_change:
        console.change_tenant_status(client_db, session, session.tenant_id, payload())
    assert self_change.value.status_code == 409
    unauthorized = SimpleNamespace(subject_id=photographer_id, tenant_id=target)
    with pytest.raises(HTTPException) as denied:
        console.change_tenant_status(client_db, unauthorized, target, payload())
    assert denied.value.status_code == 403
    assert client_db.get(Tenant, target).status == "active"


def test_financial_reconciliation_exception_does_not_authorize_acervo_or_new_payment(client_db):
    _session, target, _ = context(client_db)
    tenant = client_db.get(Tenant, target)
    tenant.status = "suspended"
    client_db.commit()
    enable_domain_guard(client_db)
    with pytest.raises(HTTPException):
        lock_payment_account(client_db, target)
    lock_payment_account(client_db, target, reconciliation=True)
    with pytest.raises(HTTPException):
        require_active_owner(client_db, target)
    client_db.commit()
    assert "tenant_financial_reconciliation" not in client_db.info
    # Uma operação normal continua falhando no guard, inclusive depois da exceção.
    client_db.add(ParentGallery(tenant_id=target, name="Forbidden new gallery"))
    with pytest.raises(TenantContextError):
        client_db.commit()
    client_db.rollback()


def test_orm_audit_is_append_only(client_db):
    session, target, _ = context(client_db)
    console.change_tenant_status(client_db, session, target, payload())
    client_db.commit()
    entry = client_db.scalar(select(PlatformAdminEvent))
    entry.result = "denied"
    with pytest.raises(RuntimeError, match="append-only"):
        client_db.commit()
    client_db.rollback()
    entry = client_db.scalar(select(PlatformAdminEvent))
    client_db.delete(entry)
    with pytest.raises(RuntimeError, match="append-only"):
        client_db.commit()
    client_db.rollback()


def test_hostname_activation_requires_reviewed_hash_is_idempotent_and_preserves_tenant_data(client_db):
    session, target_id, _ = context(client_db)
    target = reserve_host(client_db, target_id)
    gallery = ParentGallery(tenant_id=target_id, name="Preserved synthetic gallery")
    client_db.add(gallery)
    client_db.commit()
    intention = hostname_payload()

    result = console.activate_tenant_hostname(client_db, session, target_id, intention)
    client_db.commit()
    assert result == {"tenant_id": str(target_id), "canonical_host": target.canonical_host,
                      "canonical_host_status": "ready", "replayed": False}
    assert target.status == "active" and target.canonical_host_status == "ready"
    assert client_db.get(ParentGallery, gallery.id).name == "Preserved synthetic gallery"
    assert tenant_for_host(client_db, target.canonical_host).id == target_id
    assert public_gallery_url_for_tenant(client_db, target, gallery.id).startswith(
        "https://synthetic.pickyourpic.com.br/"
    )
    assert console.activate_tenant_hostname(client_db, session, target_id, intention)["replayed"] is True
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent)) == 1
    event = client_db.scalar(select(PlatformAdminEvent))
    assert (event.action, event.previous_status, event.next_status, event.evidence_sha256) == (
        "tenant.host_ready", "reserved", "ready", intention.evidence_sha256,
    )
    assert PASSWORD not in str(event.__dict__) and SECRET not in str(event.__dict__)
    divergent = intention.model_copy(update={"evidence_sha256": sha256(b"different report").hexdigest()})
    with pytest.raises(HTTPException) as conflict:
        console.activate_tenant_hostname(client_db, session, target_id, divergent)
    assert conflict.value.status_code == 409
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
        PlatformAdminEvent.action == "tenant.host_ready",
    )) == 1


def test_hostname_activation_rejects_missing_hash_wrong_tenant_owner_stale_host_and_reused_totp(client_db):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        hostname_payload(evidence_sha256="")
    with pytest.raises(ValidationError):
        hostname_payload(evidence_sha256="g" * 64)
    session, target_id, photographer_id = context(client_db)
    target = reserve_host(client_db, target_id)
    wrong_host = hostname_payload(expected_hostname="other.pickyourpic.com.br")
    with pytest.raises(HTTPException) as mismatch:
        console.activate_tenant_hostname(client_db, session, target_id, wrong_host)
    assert mismatch.value.status_code == 409
    assert target.canonical_host_status == "reserved"

    target.canonical_host_status = "ready"
    client_db.commit()
    with pytest.raises(HTTPException) as stale:
        console.activate_tenant_hostname(client_db, session, target_id, hostname_payload())
    assert stale.value.status_code == 409
    assert target.canonical_host_status == "ready"
    target.canonical_host_status = "reserved"
    client_db.commit()

    unauthorized = SimpleNamespace(subject_id=photographer_id, tenant_id=target_id)
    with pytest.raises(HTTPException) as denied:
        console.activate_tenant_hostname(client_db, unauthorized, target_id, hostname_payload())
    assert denied.value.status_code == 403

    second = Tenant(canonical_host="second.pickyourpic.com.br", canonical_host_status="reserved")
    client_db.add(second)
    client_db.commit()
    code = pyotp.TOTP(SECRET).now()
    first_intent = hostname_payload(totp_code=code)
    console.activate_tenant_hostname(client_db, session, target_id, first_intent)
    client_db.commit()
    second_intent = hostname_payload(expected_hostname=second.canonical_host, totp_code=code)
    with pytest.raises(HTTPException) as reused:
        console.activate_tenant_hostname(client_db, session, second.id, second_intent)
    assert reused.value.status_code == 403
    assert client_db.get(Tenant, second.id).canonical_host_status == "reserved"
