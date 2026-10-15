"""Privilégio técnico explícito em PostgreSQL próprio; sem serviços externos."""

import sys
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import main
from app import provision_installation_operator as cli
from app.auth import AuditEvent, InstallationOperator, Role, TenantAdmin
from app.capacity_observability import collector
from app.installation_operator import operator_is_active
from app.provision_photographer import provision_photographer
from app.system_monitor.models import PlatformOwner
from app.tenancy import TenantContextError
from tests.test_tenant_client_auth import client_db as _client_db
from tests.test_tenant_client_auth import graph as _graph
from tests.test_tenant_client_auth import links as _links
from tests.test_tenant_client_auth import request
from tests.test_tenant_client_navigation import cookie

client_db = _client_db
graph = _graph
links = _links


def provision(db, record, action="grant", *, apply=True):
    return cli.provision_operator(db, admin_id=record["admin"].id, action=action,
                                  authorization_reference="synthetic-approval-6.1", apply=apply)


@pytest.fixture
def diagnostic(client_db, graph, links, monkeypatch):
    client_db.add(PlatformOwner(singleton=1, admin_user_id=graph[0]["admin"].id,
                              authorization_reference="synthetic-owner"))
    client_db.commit()
    values = [cookie(client_db, record, Role.ADMIN) for record in graph]
    monkeypatch.setattr(collector, "engine", client_db.bind)
    monkeypatch.setattr(collector, "SessionLocal", sessionmaker(bind=client_db.bind))
    collector.reset_cache_for_tests()
    yield values
    collector.reset_cache_for_tests()


def test_sem_concessao_automatica_no_provisionamento_e_dry_run(client_db, graph, diagnostic):
    first = graph[0]
    provision_photographer(client_db, first["tenant"].id, first["admin"].email, apply=True)
    assert provision(client_db, first, apply=False).changed
    assert client_db.scalar(select(func.count()).select_from(InstallationOperator)) == 0
    response = Response()
    assert main.admin_installation_capabilities(request(diagnostic[0]), response) == {"capacity_diagnostics": False}
    assert response.headers["cache-control"] == "private, no-store"
    assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.event.like("installation_operator.%"))) == 0


def test_concessao_revogacao_idempotentes_preservam_identidade_e_auditoria(client_db, graph, diagnostic):
    first = graph[0]
    before = (first["admin"].password_hash, first["admin"].totp_secret,
              first["admin"].email, first["tenant"].status)
    assert provision(client_db, first).changed
    client_db.commit()
    row = client_db.get(InstallationOperator, first["admin"].id)
    timestamps = (row.granted_at, row.updated_at)
    assert not provision(client_db, first).changed
    assert (row.granted_at, row.updated_at) == timestamps
    assert operator_is_active(client_db, first["admin"].id)
    first["tenant"].status = "suspended"
    client_db.commit()
    assert provision(client_db, first, "revoke").changed  # Suspensão não impede revogação.
    client_db.commit()
    assert not operator_is_active(client_db, first["admin"].id)
    assert row.revoked_at and not provision(client_db, first, "revoke").changed
    first["tenant"].status = "active"
    client_db.commit()
    assert provision(client_db, first).changed
    client_db.commit()
    assert row.active and row.revoked_at is None
    assert (first["admin"].password_hash, first["admin"].totp_secret,
            first["admin"].email, first["tenant"].status) == before
    events = list(client_db.scalars(select(AuditEvent).where(AuditEvent.event.like("installation_operator.%"))))
    assert sorted(event.event for event in events) == ["installation_operator.grant"] * 2 + ["installation_operator.revoke"]
    assert all(event.tenant_id is None and "synthetic-approval-6.1" in event.subject for event in events)
    assert client_db.scalar(select(func.count()).select_from(TenantAdmin)) == 2


@pytest.mark.parametrize("mode", ["missing", "unverified", "revoked", "suspended", "ambiguous"])
def test_grant_recusa_identidade_ou_vinculo_invalido(client_db, graph, diagnostic, mode):
    first = graph[0]
    admin_id = first["admin"].id
    if mode == "missing":
        admin_id = uuid4()
    elif mode == "unverified":
        first["admin"].email_verified = False
    elif mode == "revoked":
        client_db.scalar(select(TenantAdmin).where(TenantAdmin.admin_user_id == admin_id)).active = False
    elif mode == "suspended":
        first["tenant"].status = "suspended"
    else:
        client_db.add(TenantAdmin(admin_user_id=admin_id, tenant_id=graph[1]["tenant"].id))
    client_db.commit()
    with pytest.raises(TenantContextError):
        cli.provision_operator(client_db, admin_id=admin_id, action="grant",
                                authorization_reference="synthetic", apply=True)
    client_db.rollback()
    assert client_db.scalar(select(func.count()).select_from(InstallationOperator)) == 0


@pytest.mark.parametrize("role", [Role.ADMIN, Role.CLIENT])
def test_fotografo_comum_e_cliente_recusados_antes_da_coleta(client_db, graph, diagnostic, monkeypatch, role):
    value = diagnostic[1] if role == Role.ADMIN else cookie(client_db, graph[1])
    calls = []
    monkeypatch.setattr(main, "get_capacity_snapshot", lambda **kwargs: calls.append(kwargs))
    with pytest.raises(HTTPException) as exc:
        main.admin_capacity_observability(request(value), Response())
    assert exc.value.status_code == 403 and not calls


def test_operador_coleta_cache_e_revogacao_fresca_sem_privilegio_comercial(client_db, graph, diagnostic, monkeypatch):
    provision(client_db, graph[0])
    client_db.commit()
    first_request = request(diagnostic[0])
    assert main.admin_installation_capabilities(first_request, Response()) == {"capacity_diagnostics": True}
    calls = []
    original = collector._collect_once
    def collect():
        calls.append(True)
        return original()
    monkeypatch.setattr(collector, "_collect_once", collect)
    first = main.admin_capacity_observability(first_request, Response())
    cached = main.admin_capacity_observability(first_request, Response())
    assert not first.cached and cached.cached and len(calls) == 1
    serialized = first.model_dump_json()
    assert all(str(record["client"].id) not in serialized and record["admin"].email not in serialized for record in graph)
    with pytest.raises(HTTPException) as exc:
        main.parent_gallery_editor(graph[1]["parent"].id, first_request, client_db)
    assert exc.value.status_code == 404
    provision(client_db, graph[0], "revoke")
    client_db.commit()
    with pytest.raises(HTTPException) as exc:
        main.admin_capacity_observability(first_request, Response())
    assert exc.value.status_code == 403 and len(calls) == 1
    assert main.admin_installation_capabilities(first_request, Response()) == {"capacity_diagnostics": False}


def test_revogacao_durante_coleta_nao_publica_snapshot_nem_cache(client_db, graph, diagnostic, monkeypatch):
    provision(client_db, graph[0])
    client_db.commit()
    original = collector._collect_once
    def revoke_during_collection():
        snapshot = original()
        provision(client_db, graph[0], "revoke")
        client_db.commit()
        return snapshot
    monkeypatch.setattr(collector, "_collect_once", revoke_during_collection)
    with pytest.raises(HTTPException) as exc:
        main.admin_capacity_observability(request(diagnostic[0]), Response())
    assert exc.value.status_code == 403
    assert collector._cached is None and collector._collecting is False


def test_cli_dry_run_confirmacao_e_saida_sem_identidade(client_db, graph, diagnostic, monkeypatch, capsys):
    monkeypatch.setattr(cli, "SessionLocal", sessionmaker(bind=client_db.bind))
    first = graph[0]
    arguments = ["operator", "--admin-id", str(first["admin"].id), "--action", "grant",
                 "--authorization-reference", "synthetic-approval"]
    monkeypatch.setattr(sys, "argv", arguments)
    cli.main()
    assert capsys.readouterr().out.strip() == '{"action": "grant", "applied": false, "changed": true}'
    assert not operator_is_active(client_db, first["admin"].id)
    monkeypatch.setattr(sys, "argv", arguments + ["--apply"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2 and not operator_is_active(client_db, first["admin"].id)
    capsys.readouterr()
    monkeypatch.setattr(sys, "argv", arguments + ["--apply", "--confirm-admin", str(first["admin"].id)])
    cli.main()
    output = capsys.readouterr().out
    assert '"applied": true' in output and first["admin"].email not in output and str(first["admin"].id) not in output
    assert operator_is_active(client_db, first["admin"].id)

