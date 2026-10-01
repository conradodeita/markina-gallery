"""Contrato do corpus futuro, sem antecipar jornadas ou envios."""

from sqlalchemy import select

from app import auth
from app.installation_operator import operator_is_active
from tests.pilot_fixture import RecordingWhatsApp, prepare_pilot, verify_preparation
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


def test_corpus_idempotente_2_por_3_com_12_JPEGs_sem_jornadas(client_db, tmp_path):
    accounts = prepare_pilot(client_db, tmp_path)
    fingerprints = [(row.id, row.password_hash, row.totp_secret) for row in client_db.scalars(select(auth.AdminUser))]
    assert prepare_pilot(client_db, tmp_path) == accounts
    assert [(row.id, row.password_hash, row.totp_secret) for row in client_db.scalars(select(auth.AdminUser))] == fingerprints
    assert verify_preparation(client_db, tmp_path, accounts)["journeys_executed"] is False
    assert operator_is_active(client_db, accounts[0].admin_id)
    assert not operator_is_active(client_db, accounts[1].admin_id)


def test_adaptador_registra_somente_intencao_sintetica_sem_rede(monkeypatch):
    monkeypatch.setattr("socket.create_connection", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Rede proibida")))
    provider = RecordingWhatsApp()
    result = provider.send_otp("+5511999990001", "123456", idempotency_key="synthetic-pilot-otp")
    assert result.provider_status == "accepted" and len(provider.calls) == 1
    assert provider.calls[0][2] == "synthetic-pilot-otp"


def test_corpus_reusa_conta_vazia_da_migration_sem_apagar_identidade(client_db, tmp_path):
    initial = auth.Tenant()
    client_db.add(initial)
    client_db.commit()
    initial_id, created_at = initial.id, initial.created_at
    accounts = prepare_pilot(client_db, tmp_path, initial_tenant_id=initial_id)
    assert accounts[0].tenant_id == initial_id
    assert client_db.get(auth.Tenant, initial_id).created_at == created_at
    assert prepare_pilot(client_db, tmp_path, initial_tenant_id=initial_id) == accounts
    verify_preparation(client_db, tmp_path, accounts)
