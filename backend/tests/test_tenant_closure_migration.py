"""Migration de encerramento somente em PostgreSQL sintético descartável."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import sleep
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    Base,
    PhotographerBusinessProfile,
    Tenant,
    TenantAdmin,
    TenantClosureRequest,
    now,
)
from app.photographer_cpf import active_cpf_fingerprint
from app.tenant_closure import request_closure
from tests.test_photographer_onboarding_migration import _config, _demo_helpers
from tests.test_tenant_closure import prepare
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def test_recovery_batch_migration_preserves_legacy_and_refuses_history_loss(monkeypatch, postgres_schema):
    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(url)
    command.upgrade(config, "20261109_0118")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM tenant WHERE lifecycle != 'open'")) == 0
        assert connection.scalar(text("SELECT count(*) FROM tenant_closure_recovery_batch")) == 0
    command.downgrade(config, "20261109_0117")
    command.upgrade(config, "20261109_0118")
    with engine.begin() as connection:
        tenant_id = connection.scalar(text("SELECT id FROM tenant LIMIT 1"))
        owner_id = connection.scalar(text("SELECT admin_user_id FROM platform_owner"))
        closure_id = uuid4()
        connection.execute(text(
            "INSERT INTO tenant_closure_request "
            "(id,tenant_id,request_id,requested_by,state,requested_at,closed_at,terms_version,"
            "terms_sha256,balance_snapshot,balance_acknowledged) VALUES "
            "(:id,:tenant,:request,:owner,'closed',now(),now(),'synthetic',:digest,0,true)"
        ), {"id": closure_id, "tenant": tenant_id, "request": uuid4(), "owner": owner_id, "digest": "a" * 64})
        connection.execute(text(
            "INSERT INTO tenant_closure_recovery_batch "
            "(id,tenant_id,closure_request_id,requested_by_owner_admin_id,request_id,duration_days,created_at) "
            "VALUES (:id,:tenant,:closure,:owner,:request,7,now())"
        ), {"id": uuid4(), "tenant": tenant_id, "closure": closure_id, "owner": owner_id, "request": uuid4()})
    with pytest.raises(RuntimeError, match="histórico de recuperação"):
        command.downgrade(config, "20261109_0117")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM tenant_closure_recovery_batch")) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261109_0118"


def test_tenant_reopen_audit_migration_is_additive_and_protects_history(monkeypatch, postgres_schema):
    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(url)
    command.upgrade(config, "20261109_0118")
    command.upgrade(config, "20261109_0119")
    with engine.begin() as connection:
        tenant_id = connection.scalar(text("SELECT id FROM tenant LIMIT 1"))
        owner_id = connection.scalar(text("SELECT admin_user_id FROM platform_owner"))
        connection.execute(text(
            "INSERT INTO platform_admin_event "
            "(id,request_id,actor_admin_id,object_id,tenant_id,action,previous_status,next_status,result,origin,created_at) "
            "VALUES (:id,:request,:owner,:object,:tenant,'tenant.reopened','closed','open','success','web_console',now())"
        ), {"id": uuid4(), "request": uuid4(), "owner": owner_id,
            "object": uuid4(), "tenant": tenant_id})
        assert connection.scalar(text(
            "SELECT count(*) FROM platform_admin_event WHERE action='tenant.reopened'"
        )) == 1
    with pytest.raises(RuntimeError, match="auditoria de reabertura"):
        command.downgrade(config, "20261109_0118")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261109_0119"


def test_cpf_fingerprint_version_migration_preserves_legacy_and_protects_rotation(monkeypatch, postgres_schema):
    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(url)
    command.upgrade(config, "20261109_0119")
    with engine.begin() as connection:
        tenant_id = connection.scalar(text("SELECT id FROM tenant LIMIT 1"))
        admin_id = connection.scalar(text("SELECT admin_user_id FROM platform_owner"))
        connection.execute(text(
            "INSERT INTO photographer_business_profile "
            "(id,admin_user_id,tenant_id,full_name,cpf_envelope,cpf_fingerprint,created_at,updated_at) "
            "VALUES (:id,:admin,:tenant,'Synthetic profile','synthetic-envelope',:fingerprint,now(),now())"
        ), {"id": uuid4(), "admin": admin_id, "tenant": tenant_id,
            "fingerprint": "c" * 64})

    command.upgrade(config, "20261110_0120")
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT cpf_fingerprint,cpf_fingerprint_key_version FROM photographer_business_profile"
        )).one()
        assert row.cpf_fingerprint == "c" * 64 and row.cpf_fingerprint_key_version == "legacy-v0"

    command.downgrade(config, "20261109_0119")
    command.upgrade(config, "20261110_0120")
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE photographer_business_profile SET cpf_fingerprint_key_version='v2'"
        ))
    with pytest.raises(RuntimeError, match="versões de impressão de CPF"):
        command.downgrade(config, "20261109_0119")
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT cpf_fingerprint_key_version FROM photographer_business_profile"
        )) == "v2"
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261110_0120"


def test_closure_identity_migration_is_additive_and_preserves_verification_history(monkeypatch, postgres_schema):
    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(url)
    command.upgrade(config, "20261110_0120")
    command.upgrade(config, "20261110_0121")
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM tenant_closure_identity_verification"
        )) == 0
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261110_0121"

    command.downgrade(config, "20261110_0120")
    command.upgrade(config, "20261110_0121")
    with engine.begin() as connection:
        tenant_id = connection.scalar(text("SELECT tenant_id FROM tenant_admin LIMIT 1"))
        admin_id = connection.scalar(text(
            "SELECT admin_user_id FROM tenant_admin WHERE tenant_id=:tenant LIMIT 1"
        ), {"tenant": tenant_id})
        closure_id = uuid4()
        connection.execute(text(
            "INSERT INTO tenant_closure_request "
            "(id,tenant_id,request_id,requested_by,state,requested_at,closed_at,terms_version,"
            "terms_sha256,balance_snapshot,balance_acknowledged) VALUES "
            "(:id,:tenant,:request,:admin,'closed',now(),now(),'synthetic',:digest,0,true)"
        ), {"id": closure_id, "tenant": tenant_id, "request": uuid4(),
            "admin": admin_id, "digest": "b" * 64})
        connection.execute(text(
            "INSERT INTO tenant_closure_identity_verification "
            "(id,tenant_id,closure_request_id,admin_user_id,request_id,state,"
            "current_name_envelope,current_email_envelope,email_fingerprint,code_digest,"
            "attempts,expires_at,verified_at,created_at) VALUES "
            "(:id,:tenant,:closure,:admin,:request,'email_pending','private-name','private-email',"
            ":email,:code,0,now()+interval '10 minutes',NULL,now())"
        ), {"id": uuid4(), "tenant": tenant_id, "closure": closure_id, "admin": admin_id,
            "request": uuid4(), "email": "c" * 64, "code": "d" * 64})

    with pytest.raises(RuntimeError, match="histórico de verificação de identidade"):
        command.downgrade(config, "20261110_0120")
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM tenant_closure_identity_verification"
        )) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261110_0121"


def test_biometric_closure_migration_is_additive_and_refuses_history_loss(
    monkeypatch, postgres_schema,
):
    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(url)
    command.upgrade(config, "20261110_0124")
    command.upgrade(config, "20261111_0125")

    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name='tenant_closure_request' "
            "AND column_name IN ('biometric_cleanup_started_at','biometric_cleanup_completed_at')"
        )) == 2
        assert connection.scalar(text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_name='facial_search_consent_proof'"
        )) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261111_0125"

    command.downgrade(config, "20261110_0124")
    command.upgrade(config, "20261111_0125")
    with engine.begin() as connection:
        tenant_id = connection.scalar(text("SELECT tenant_id FROM tenant_admin LIMIT 1"))
        owner_id = connection.scalar(text("SELECT admin_user_id FROM platform_owner"))
        closure_id = uuid4()
        request_id = uuid4()
        gallery_id = uuid4()
        client_id = uuid4()
        connection.execute(text(
            "INSERT INTO tenant_closure_request "
            "(id,tenant_id,request_id,requested_by,state,requested_at,closed_at,terms_version,"
            "terms_sha256,balance_snapshot,balance_acknowledged,biometric_cleanup_started_at) "
            "VALUES (:id,:tenant,:request,:owner,'closed',now(),now(),'synthetic',:digest,0,true,now())"
        ), {"id": closure_id, "tenant": tenant_id, "request": uuid4(),
            "owner": owner_id, "digest": "e" * 64})
        connection.execute(text(
            "INSERT INTO facial_search_consent_proof "
            "(id,tenant_id,source_search_request_id,parent_gallery_id,client_id,authorization_method,"
            "consent_version,legal_notice_version,subject_declaration,recorded_at,created_at) "
            "VALUES (:id,:tenant,:source,:gallery,:client,'explicit_consent','consent-v1',"
            "'notice-v1','conditional',now(),now())"
        ), {"id": uuid4(), "tenant": tenant_id, "source": request_id,
            "gallery": gallery_id, "client": client_id})

    with pytest.raises(RuntimeError, match="comprovantes mínimos"):
        command.downgrade(config, "20261110_0124")
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM facial_search_consent_proof"))
    with pytest.raises(RuntimeError, match="estado de limpeza biométrica"):
        command.downgrade(config, "20261110_0124")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261111_0125"
        assert connection.scalar(text("SELECT count(*) FROM facial_search_consent_proof")) == 0
        assert connection.scalar(text(
            "SELECT count(*) FROM tenant_closure_request "
            "WHERE biometric_cleanup_started_at IS NOT NULL"
        )) == 1


def test_concurrent_search_waits_for_cleanup_marker_and_is_rejected(monkeypatch, postgres_schema):
    from types import SimpleNamespace

    from app.auth import PhotographerTermsAcceptance, TenantCreditWallet
    from app.facial import search as facial_search
    from app.facial.closure_gate import lock_facial_tenant
    from app.tenant_closure import ClosureInput, request_closure

    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(url)
    command.upgrade(config, "20261111_0125")
    with Session(engine) as db:
        tenant = Tenant()
        admin = AdminUser(
            email="biometric-lock@example.test",
            password_hash="synthetic-only",
            email_verified=True,
            totp_enabled=False,
        )
        db.add(tenant)
        db.flush()
        admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
        db.add(admin)
        db.flush()
        db.add(TenantCreditWallet(tenant_id=tenant.id, mode="finite"))
        db.add(PhotographerTermsAcceptance(
            tenant_id=tenant.id,
            admin_user_id=admin.id,
            terms_version="synthetic-closure",
            terms_text="synthetic",
            terms_sha256="a" * 64,
            provider_identity="synthetic",
            photographer_identity="synthetic",
            environment="test",
        ))
        db.flush()
        session = SimpleNamespace(
            role="admin", subject_id=admin.id, tenant_id=tenant.id,
        )
        payload = ClosureInput(
            request_id=uuid4(),
            confirm_closure=True,
            acknowledge_remaining_balance=True,
            expected_balance=0,
            terms_version="synthetic-closure",
            terms_sha256="a" * 64,
        )
        request_closure(db, session, payload)
        db.commit()
        tenant_id = tenant.id
        closure = db.scalar(
            select(TenantClosureRequest).where(TenantClosureRequest.tenant_id == tenant_id)
        )
        closure_id = closure.id

    monkeypatch.setattr(
        facial_search,
        "_require_search_context",
        lambda *_args, **_kwargs: tenant_id,
    )
    tenant_locked = Event()
    search_started = Event()

    def begin_cleanup_marker():
        with Session(engine) as db:
            lock_facial_tenant(db, tenant_id)
            row = db.get(TenantClosureRequest, closure_id)
            tenant_locked.set()
            assert search_started.wait(timeout=10)
            # Dá ao segundo processo tempo para chegar ao SELECT FOR UPDATE.
            sleep(0.15)
            row.biometric_cleanup_started_at = now()
            db.commit()

    def create_search():
        assert tenant_locked.wait(timeout=10)
        with Session(engine) as db:
            search_started.set()
            with pytest.raises(facial_search.FacialSearchError, match="indisponível"):
                facial_search.create_search_request(
                    db,
                    parent_gallery_id=uuid4(),
                    client_id=uuid4(),
                    consent_version="synthetic-consent",
                    subject_declaration="conditional",
                    representation_reference=None,
                    payload=b"",
                    settings=None,
                )
            db.rollback()

    with ThreadPoolExecutor(max_workers=2) as pool:
        marker = pool.submit(begin_cleanup_marker)
        request = pool.submit(create_search)
        marker.result(timeout=20)
        request.result(timeout=20)

    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM facial_search_request WHERE tenant_id=:tenant"
        ), {"tenant": tenant_id}) == 0


def _current_schema(engine):
    rules = [(constraint, constraint._create_rule)
             for table in Base.metadata.tables.values() for constraint in table.constraints]
    try:
        Base.metadata.create_all(engine)
    finally:
        for constraint, rule in rules:
            constraint._create_rule = rule


def test_postgres_cpf_fingerprint_check_uses_transaction_scoped_lock(postgres_schema, monkeypatch):
    engine = postgres_schema
    _current_schema(engine)
    monkeypatch.delenv("PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON", raising=False)
    monkeypatch.delenv("PHOTOGRAPHER_CPF_FINGERPRINT_ACTIVE_KEY_VERSION", raising=False)
    with Session(engine) as db:
        tenant, admin = Tenant(), AdminUser(
            email="cpf-lock@example.test", password_hash="synthetic-only",
        )
        db.add_all([tenant, admin])
        db.flush()
        db.add(TenantAdmin(tenant_id=tenant.id, admin_user_id=admin.id))
        db.flush()
        version, fingerprint, duplicate = active_cpf_fingerprint(db, "52998224725")
        assert version == "legacy-v0" and not duplicate
        db.add(PhotographerBusinessProfile(
            admin_user_id=admin.id,
            tenant_id=tenant.id,
            full_name="Synthetic profile",
            cpf_envelope="synthetic-envelope",
            cpf_fingerprint=fingerprint,
            cpf_fingerprint_key_version=version,
        ))
        db.flush()
        _version, _candidate, duplicate = active_cpf_fingerprint(db, "52998224725")
        assert duplicate
        db.rollback()


def test_concurrent_closure_requests_have_one_history_and_one_replay(postgres_schema):
    engine = postgres_schema
    _current_schema(engine)
    with Session(engine) as db:
        session, payload, _ = prepare(db)
    barrier = Barrier(2)

    def submit():
        with Session(engine) as db:
            barrier.wait(timeout=10)
            result = request_closure(db, session, payload)
            db.commit()
            return result["replayed"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: submit(), range(2))) == [False, True]
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM tenant_closure_request")) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM audit_event WHERE event='tenant.closure_requested'")) == 1


def test_checkout_racing_finalization_cannot_create_order_on_closed_account(postgres_schema):
    from app.auth import Client, GalleryClientState, ParentGallery, SaleOrder, now
    from app.payment_availability import lock_payment_account
    from app.tenancy import enable_domain_guard
    from app.tenant_closure import finalize_closure

    engine = postgres_schema
    _current_schema(engine)
    with Session(engine) as db:
        session, payload, tenant = prepare(db)
        gallery = ParentGallery(tenant_id=tenant.id, name="Synthetic")
        client = Client(tenant_id=tenant.id, full_name="Synthetic", phone_e164="+5511999990088")
        db.add_all([gallery, client])
        db.flush()
        db.add(GalleryClientState(tenant_id=tenant.id, parent_gallery_id=gallery.id, client_id=client.id))
        db.commit()
        request_closure(db, session, payload)
        db.commit()
        tenant_id, gallery_id, client_id = tenant.id, gallery.id, client.id
    barrier = Barrier(2)

    def close():
        with Session(engine) as db:
            enable_domain_guard(db)
            barrier.wait(timeout=10)
            result = finalize_closure(db, tenant_id)
            db.commit()
            return result["state"]

    def checkout():
        from fastapi import HTTPException

        with Session(engine) as db:
            enable_domain_guard(db)
            barrier.wait(timeout=10)
            try:
                lock_payment_account(db, tenant_id)
            except HTTPException:
                db.rollback()
                return "denied"
            db.add(SaleOrder(tenant_id=tenant_id, client_id=client_id, parent_gallery_id=gallery_id,
                             parent_gallery_id_snapshot=gallery_id, parent_gallery_name_snapshot="Synthetic",
                             derived_gallery_name_snapshot="Synthetic", total_cents=0, frozen_at=now()))
            db.commit()
            return "created"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(close), pool.submit(checkout)
        outcome = first.result(timeout=30), second.result(timeout=30)
    assert outcome in {("closing", "denied"), ("closing", "created")}


def test_closure_preserves_legacy_and_refuses_loss_of_history(monkeypatch, postgres_schema):
    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(url)
    command.upgrade(config, "20261109_0116")
    with engine.connect() as connection:
        before = connection.execute(text("SELECT id,status FROM tenant ORDER BY id")).all()
    command.upgrade(config, "20261109_0117")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT id,status FROM tenant ORDER BY id")).all() == before
        assert connection.scalar(text("SELECT count(*) FROM tenant WHERE lifecycle != 'open'")) == 0
        assert connection.scalar(text("SELECT count(*) FROM tenant_closure_request")) == 0
    command.downgrade(config, "20261109_0116")
    command.upgrade(config, "20261109_0117")
    with engine.begin() as connection:
        tenant = connection.scalar(text("SELECT id FROM tenant LIMIT 1"))
        admin = connection.scalar(text("SELECT admin_user_id FROM platform_owner LIMIT 1"))
        connection.execute(text(
            "INSERT INTO tenant_closure_request "
            "(id,tenant_id,request_id,requested_by,state,requested_at,terms_version,terms_sha256,"
            "balance_snapshot,balance_acknowledged) VALUES "
            "(:id,:tenant,:request,:admin,'closing',now(),'synthetic-v1',:digest,7,true)"
        ), {"id": uuid4(), "tenant": tenant, "request": uuid4(), "admin": admin, "digest": "a" * 64})
    with pytest.raises(RuntimeError, match="histórico de encerramento"):
        command.downgrade(config, "20261109_0116")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261109_0117"
        assert connection.scalar(text("SELECT balance_snapshot FROM tenant_closure_request")) == 7
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE tenant SET lifecycle='invalid' WHERE id=:id"), {"id": tenant})
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO tenant_closure_request "
            "SELECT :id,tenant_id,:request,requested_by,state,requested_at,closed_at,reopened_at,"
            "terms_version,terms_sha256,balance_snapshot,balance_acknowledged FROM tenant_closure_request"
        ), {"id": uuid4(), "request": uuid4()})
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE tenant_closure_request SET state='closed'"))
