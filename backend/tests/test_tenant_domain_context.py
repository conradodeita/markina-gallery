"""Barreira de commit com duas contas reais em PostgreSQL sintético."""

from datetime import timedelta

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from app import admin_security, worker
from app.acervo_context import require_active_owner
from app.auth import AdminSecurityChallenge, AuditEvent, ParentGallery, Tenant, TenantAdmin, now
from app.tenancy import (
    TenantContextError,
    domain_session,
    require_admin_tenant,
    require_parent_tenant,
)
from tests.test_tenant_client_isolation import client_db as _client_db
from tests.test_tenant_ownership_schema import graph as _graph

client_db, graph = _client_db, _graph


@pytest.mark.parametrize("flushed", [False, True])
def test_suspensao_A_recusa_commit_inclusive_flush_e_B_continua(client_db, graph, flushed):
    if flushed and client_db.bind.dialect.name != "postgresql":
        pytest.skip("Escritores simultâneos após flush exigem PostgreSQL")
    client_db.commit()
    factory = sessionmaker(bind=client_db.bind, expire_on_commit=False)
    first, second = graph
    with pytest.raises(TenantContextError), domain_session(factory) as db:
        parent = db.get(ParentGallery, first["parent"].id)
        parent.name = "Não publicar"
        if flushed:
            db.flush()
        with factory() as peer:
            peer.get(Tenant, first["tenant"].id).status = "suspended"
            peer.commit()
        db.commit()
    with domain_session(factory) as db:
        require_active_owner(db, second["tenant"].id)
        db.get(ParentGallery, second["parent"].id).name = "B independente"
        db.commit()
    client_db.expire_all()
    assert first["parent"].name != "Não publicar"
    assert second["parent"].name == "B independente"


@pytest.mark.parametrize("change", ["revoked", "replaced"])
def test_vinculo_admin_demonstrado_revalidado_apos_core_update(client_db, graph, change):
    if client_db.bind.dialect.name != "postgresql":
        pytest.skip("Escritores simultâneos após UPDATE exigem PostgreSQL")
    client_db.commit()
    factory = sessionmaker(bind=client_db.bind)
    first, second = graph
    with pytest.raises(TenantContextError), domain_session(factory) as db:
        assert require_admin_tenant(db, first["admin"].id).id == first["tenant"].id
        db.execute(update(ParentGallery).where(ParentGallery.id == first["parent"].id,
            ParentGallery.tenant_id == first["tenant"].id).values(name="Não publicar"))
        with factory() as peer:
            membership = peer.scalar(select(TenantAdmin).where(
                TenantAdmin.admin_user_id == first["admin"].id))
            membership.active = False
            if change == "replaced":
                peer.add(TenantAdmin(admin_user_id=first["admin"].id,
                    tenant_id=second["tenant"].id, active=True))
            peer.commit()
        db.commit()
    client_db.expire_all()
    assert first["parent"].name != "Não publicar"


def test_dois_owners_explicitamente_ativos_sem_selecao_global(client_db, graph):
    client_db.commit()
    factory = sessionmaker(bind=client_db.bind)
    with domain_session(factory) as db:
        for row in graph:
            require_active_owner(db, row["tenant"].id)
            db.get(ParentGallery, row["parent"].id).name = row["admin"].email
        db.commit()
    client_db.expire_all()
    assert all(row["parent"].name == row["admin"].email for row in graph)


def test_commit_tecnico_sem_owner_nao_elege_conta(client_db, graph):
    client_db.commit()
    factory = sessionmaker(bind=client_db.bind)
    for row in graph:
        row["tenant"].status = "suspended"
    client_db.commit()
    with domain_session(factory) as db:
        record = AuditEvent(event="synthetic.technical", subject="no-commercial-owner")
        db.add(record)
        db.commit()
        assert record.tenant_id is None


def test_contexto_revalidado_na_proxima_transacao_da_mesma_sessao(client_db, graph):
    client_db.commit()
    factory = sessionmaker(bind=client_db.bind)
    with domain_session(factory) as db:
        require_admin_tenant(db, graph[0]["admin"].id)
        db.commit()
        with factory() as peer:
            peer.get(Tenant, graph[0]["tenant"].id).status = "suspended"
            peer.commit()
        require_active_owner(db, graph[1]["tenant"].id)
        db.get(ParentGallery, graph[1]["parent"].id).name = "B nova transação"
        db.commit()


def test_resolvedor_de_origem_exige_owner_explicitamente(client_db, graph):
    first, second = graph
    assert require_parent_tenant(client_db, first["parent"].id, tenant_id=first["tenant"].id) == first["tenant"].id
    with pytest.raises(TenantContextError):
        require_parent_tenant(client_db, second["parent"].id, tenant_id=first["tenant"].id)


def security_material(db, graph):
    rows = [AdminSecurityChallenge(tenant_id=row["tenant"].id,
        admin_id=row["admin"].id, purpose="change_email_otp", subject_fingerprint="s" * 64,
        secret_hash="h" * 64, encrypted_target="synthetic-ciphertext",
        expires_at=now()-timedelta(minutes=1)) for row in graph]
    technical = AdminSecurityChallenge(purpose="password_recovery_otp", subject_fingerprint="t" * 64,
        secret_hash="h" * 64, encrypted_target="synthetic-ciphertext",
        expires_at=now()-timedelta(minutes=1))
    db.add_all([*rows, technical])
    db.commit()
    return rows, technical


def test_limpeza_contextual_nao_toca_tecnico_nem_B(client_db, graph):
    rows, technical = security_material(client_db, graph)
    assert admin_security.cleanup_admin_security_material(client_db, tenant_id=graph[0]["tenant"].id) == 1
    client_db.expire_all()
    assert rows[0].encrypted_target is None
    assert rows[1].encrypted_target == technical.encrypted_target == "synthetic-ciphertext"


@pytest.mark.parametrize("during", [False, True])
def test_worker_limpeza_seguranca_preserva_A_suspensa_e_conclui_B(client_db, graph, monkeypatch, during):
    if during and client_db.bind.dialect.name != "postgresql":
        pytest.skip("Suspensão concorrente exige PostgreSQL")
    rows, technical = security_material(client_db, graph)
    factory = sessionmaker(bind=client_db.bind)
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(worker, "_last_admin_security_cleanup", 0.0)
    first_owner = graph[0]["tenant"].id
    if not during:
        graph[0]["tenant"].status = "suspended"
        client_db.commit()
    else:
        original = admin_security.require_active_owner
        checks = 0

        def suspend_before_commit(db, tenant_id):
            nonlocal checks
            if tenant_id == first_owner:
                checks += 1
                if checks == 2:
                    with factory() as peer:
                        peer.get(Tenant, first_owner).status = "suspended"
                        peer.commit()
            return original(db, tenant_id)

        monkeypatch.setattr(admin_security, "require_active_owner", suspend_before_commit)
    assert worker.process_admin_security_cleanup()
    client_db.expire_all()
    assert rows[0].encrypted_target == "synthetic-ciphertext"
    assert rows[1].encrypted_target is None
    assert technical.tenant_id is None and technical.encrypted_target is None
