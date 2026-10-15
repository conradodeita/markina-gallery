"""Contratos de preparação própria da conta, sem cobrança nem transporte real."""

from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth import AdminSecurityChallenge, GlobalPixSettings, InfinitePaySettings, now
from tests.test_tenant_client_auth import client_db as _client_db
from tests.test_tenant_client_auth import graph as _graph

client_db = _client_db
graph = _graph


def test_configuracao_independente_por_fotografo_preserva_pix(client_db, graph):
    for index, row in enumerate(graph):
        client_db.add(InfinitePaySettings(tenant_id=row["tenant"].id,
            admin_user_id=row["admin"].id, handle=f"synthetic-{index}"))
        client_db.add(GlobalPixSettings(tenant_id=row["tenant"].id,
            admin_user_id=row["admin"].id, status="active", version=3,
            copy_paste=f"synthetic-{index}@example.test"))
    client_db.commit()
    settings = list(client_db.scalars(select(InfinitePaySettings).order_by(InfinitePaySettings.handle)))
    settings[0].handle = "synthetic-new-a"
    client_db.commit()
    assert settings[1].handle == "synthetic-1" and settings[1].status == "pending"
    assert {(pix.copy_paste, pix.version) for pix in client_db.scalars(select(GlobalPixSettings))} == {
        ("synthetic-0@example.test", 3), ("synthetic-1@example.test", 3)}


def test_singleton_infinitepay_recusa_duplicata_na_mesma_conta(client_db, graph):
    first = graph[0]
    for _ in range(2):
        client_db.add(InfinitePaySettings(tenant_id=first["tenant"].id,
            admin_user_id=first["admin"].id, handle="synthetic"))
    with pytest.raises(IntegrityError):
        client_db.flush()


def test_admin_estrangeiro_recusado_na_persistencia(client_db, graph):
    first, second = graph
    client_db.add(InfinitePaySettings(tenant_id=first["tenant"].id,
        admin_user_id=second["admin"].id, handle="synthetic"))
    with pytest.raises(IntegrityError):
        client_db.flush()


def test_status_ativo_nao_existe_sem_verificacao(client_db, graph):
    row = graph[0]
    client_db.add(InfinitePaySettings(tenant_id=row["tenant"].id,
        admin_user_id=row["admin"].id, handle="synthetic", status="active"))
    with pytest.raises(IntegrityError):
        client_db.flush()


def test_desafio_infinitepay_exige_contexto_na_persistencia(client_db):
    client_db.add(AdminSecurityChallenge(purpose="change_infinitepay_otp",
        subject_fingerprint="synthetic", secret_hash="synthetic", expires_at=now()+timedelta(minutes=1)))
    with pytest.raises(IntegrityError):
        client_db.flush()
