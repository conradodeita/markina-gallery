"""Atomicidade PostgreSQL das mutações financeiras globais do proprietário."""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app import main, platform_console
from app.auth import (
    Base,
    PhotographerCreditEntry,
    PlatformAdminEvent,
    now,
    password_hasher,
)
from app.main import (
    PhotographerCreditGrantInput,
    PhotographerCreditPackageInput,
    PhotographerCreditReviewInput,
    PhotographerCreditRevocationInput,
)
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def test_postgres_credit_replay_and_session_revocation_are_atomic(postgres_schema, monkeypatch):
    engine = postgres_schema
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        owner_tenant, tenant, owner, _photographer = create_accounts(db)
        secret = "JBSWY3DPEHPK3PXP"
        owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
        owner.totp_secret = secret
        db.commit()

        owner_session = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
        monkeypatch.setattr(main, "require_admin", lambda _request: owner_session)
        monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
        monkeypatch.setattr(platform_console, "require_console_owner", lambda *_: None)
        monkeypatch.setattr(platform_console, "current_session", lambda *_args, **_kwargs: owner_session)
        request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

        grant = PhotographerCreditGrantInput(
            request_id=uuid4(), tenant_id=tenant.id, quantity=2,
            idempotency_key="postgres-owner-grant", reference="synthetic PostgreSQL grant",
            current_password="SyntheticOwnerPassword!2026", totp_code=pyotp.TOTP(secret).now(),
        )
        result = main.admin_grant_photographer_credits(grant, request, Response(), db)
        replay = main.admin_grant_photographer_credits(grant, request, Response(), db)
        assert replay["replayed"] is True
        assert replay["entry"]["id"] == result["entry"]["id"]
        assert db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
            PhotographerCreditEntry.tenant_id == tenant.id,
            PhotographerCreditEntry.entry_type == "owner_grant",
        )) == 1

        current_step = pyotp.TOTP(secret).timecode(now())
        revoke = PhotographerCreditRevocationInput(
            request_id=uuid4(), tenant_id=tenant.id, quantity=1,
            idempotency_key="postgres-owner-revoke", reference="synthetic PostgreSQL revoke",
            current_password="SyntheticOwnerPassword!2026",
            totp_code=pyotp.TOTP(secret).at((current_step + 1) * pyotp.TOTP(secret).interval),
        )
        monkeypatch.setattr(platform_console, "current_session", lambda *_args, **_kwargs: SimpleNamespace(
            id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id,
        ))
        with pytest.raises(HTTPException) as revoked_session:
            main.admin_revoke_photographer_credits(
                UUID(result["entry"]["id"]), revoke, request, Response(), db,
            )
        assert revoked_session.value.status_code == 403
        assert db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
            PhotographerCreditEntry.tenant_id == tenant.id,
            PhotographerCreditEntry.entry_type == "grant_revocation",
        )) == 0
        assert db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
            PlatformAdminEvent.request_id == revoke.request_id,
        )) == 0

        monkeypatch.setattr(platform_console, "current_session", lambda *_args, **_kwargs: owner_session)
        committed = main.admin_revoke_photographer_credits(
            UUID(result["entry"]["id"]), revoke, request, Response(), db,
        )
        assert committed["replayed"] is False
        replayed_revoke = main.admin_revoke_photographer_credits(
            UUID(result["entry"]["id"]), revoke, request, Response(), db,
        )
        assert replayed_revoke["replayed"] is True
        assert db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
            PhotographerCreditEntry.tenant_id == tenant.id,
            PhotographerCreditEntry.entry_type == "grant_revocation",
        )) == 1


def test_postgres_package_audit_action_and_replay(postgres_schema, monkeypatch):
    engine = postgres_schema
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        owner_tenant, _tenant, owner, _photographer = create_accounts(db)
        secret = "JBSWY3DPEHPK3PXP"
        owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
        owner.totp_secret = secret
        db.commit()
        owner_session = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
        monkeypatch.setattr(main, "require_admin", lambda _request: owner_session)
        monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
        monkeypatch.setattr(platform_console, "require_console_owner", lambda *_: None)
        monkeypatch.setattr(platform_console, "revalidate_owner_before_commit", lambda *_: None)
        request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
        payload = PhotographerCreditPackageInput(
            request_id=uuid4(), name="PostgreSQL sintético", description=None,
            credit_quantity=15, price_cents=1800, currency_code="BRL", active=False,
            current_password="SyntheticOwnerPassword!2026", totp_code=pyotp.TOTP(secret).now(),
        )
        created = main.admin_create_credit_package(payload, request, Response(), db)
        replayed = main.admin_create_credit_package(payload, request, Response(), db)
        assert created["replayed"] is False and replayed["replayed"] is True
        assert db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
            PlatformAdminEvent.action == "credit.package_created",
        )) == 1


def test_postgres_purchase_review_audit_action_and_replay(postgres_schema, monkeypatch):
    from app.auth import MercadoPagoCreditPurchase
    from tests.test_mercadopago_credit_purchases import create_purchase_context, prepare

    engine = postgres_schema
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        owner_tenant, buyer_tenant, owner, buyer, package, _account_id = create_purchase_context(db)
        purchase = prepare(db, buyer_tenant, buyer, package, "postgres-review-step-up")
        purchase.state = "charged_back"
        purchase.review_status = "pending"
        secret = "JBSWY3DPEHPK3PXP"
        owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
        owner.totp_secret = secret
        db.commit()
        owner_session = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
        monkeypatch.setattr(main, "require_admin", lambda _request: owner_session)
        monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
        monkeypatch.setattr(platform_console, "require_console_owner", lambda *_: None)
        monkeypatch.setattr(platform_console, "revalidate_owner_before_commit", lambda *_: None)
        request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
        payload = PhotographerCreditReviewInput(
            request_id=uuid4(), decision="restrict", reason="Restrição sintética",
            current_password="SyntheticOwnerPassword!2026", totp_code=pyotp.TOTP(secret).now(),
        )
        result = main.admin_review_credit_purchase(
            purchase.id, payload, request, Response(), db,
        )
        replayed = main.admin_review_credit_purchase(
            purchase.id, payload, request, Response(), db,
        )
        assert result["replayed"] is False and replayed["replayed"] is True
        assert db.get(MercadoPagoCreditPurchase, purchase.id).review_status == "restricted"
        assert db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
            PlatformAdminEvent.action == "credit.purchase_reviewed",
        )) == 1
