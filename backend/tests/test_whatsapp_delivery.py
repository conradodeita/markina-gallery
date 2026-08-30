import base64
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError

from app.auth import (
    AuthSession,
    Base,
    Role,
    SessionLocal,
    WhatsAppChannelSettings,
    WhatsAppDelivery,
    engine,
    now,
    token_hash,
)
from app.main import app
from app.messaging import (
    WhatsAppConfigurationError,
    WhatsAppConnectionStatus,
    WhatsAppDeliveryResult,
    WhatsAppPairingResult,
)
from app.worker import process_next_whatsapp_delivery
from app.whatsapp_delivery import (
    apply_delivery_status,
    decrypt_otp,
    encrypt_otp,
    otp_encryption_key,
    transition_status,
)


@pytest.fixture(autouse=True)
def clean_database():
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(connection)
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
    Base.metadata.create_all(engine)
    yield


def test_otp_payload_round_trip_rejects_tampering_and_wrong_key(monkeypatch) -> None:
    key = os.urandom(32)
    configured = base64.urlsafe_b64encode(key).decode("ascii")
    monkeypatch.setenv("WHATSAPP_OTP_ENCRYPTION_KEY", configured)
    assert otp_encryption_key() == key

    token = encrypt_otp("123456", key=key, context="challenge-1")
    assert "123456" not in token
    assert decrypt_otp(token, key=key, context="challenge-1") == "123456"

    raw = bytearray(base64.urlsafe_b64decode(token))
    raw[-1] ^= 1
    tampered = base64.urlsafe_b64encode(raw).decode("ascii")
    with pytest.raises(WhatsAppConfigurationError, match="adulterado"):
        decrypt_otp(tampered, key=key, context="challenge-1")
    with pytest.raises(WhatsAppConfigurationError, match="adulterado"):
        decrypt_otp(token, key=os.urandom(32), context="challenge-1")


def test_otp_encryption_key_is_required_and_validated(monkeypatch) -> None:
    monkeypatch.delenv("WHATSAPP_OTP_ENCRYPTION_KEY", raising=False)
    with pytest.raises(WhatsAppConfigurationError, match="não está configurada"):
        otp_encryption_key()
    monkeypatch.setenv("WHATSAPP_OTP_ENCRYPTION_KEY", "invalida")
    with pytest.raises(WhatsAppConfigurationError):
        otp_encryption_key()


def test_delivery_states_are_monotonic_and_terminal() -> None:
    assert transition_status("accepted", "queued").status == "accepted"
    assert transition_status("accepted", "delivered").status == "delivered"
    assert transition_status("delivered", "read").status == "read"
    assert transition_status("read", "failed").status == "read"
    assert transition_status("unknown", "accepted").status == "accepted"
    assert transition_status("unknown", "queued").status == "unknown"

    delivery = WhatsAppDelivery(
        kind="otp",
        source_type="auth_challenge",
        source_id=str(uuid4()),
        recipient_phone="+5511555550000",
        template_kind="client_otp",
        idempotency_key="otp-monotonic-1",
    )
    instant = now()
    assert apply_delivery_status(delivery, "accepted", at=instant)
    assert delivery.accepted_at == instant
    assert apply_delivery_status(delivery, "read", at=instant + timedelta(seconds=2))
    assert not apply_delivery_status(delivery, "delivered", at=instant + timedelta(seconds=3))
    assert delivery.status == "read"


def test_delivery_constraints_reject_duplicate_idempotency_and_invalid_state() -> None:
    common = {
        "kind": "otp",
        "source_type": "auth_challenge",
        "recipient_phone": "+5511555550001",
        "template_kind": "client_otp",
        "idempotency_key": "unique-delivery",
    }
    with SessionLocal() as db:
        db.add(WhatsAppDelivery(source_id="one", **common))
        db.commit()
        db.add(WhatsAppDelivery(source_id="two", **common))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        invalid = WhatsAppDelivery(source_id="three", **{**common, "idempotency_key": "invalid"})
        invalid.status = "sent"
        db.add(invalid)
        with pytest.raises(IntegrityError):
            db.commit()


def _alembic(database_url: str, *arguments: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=Path(__file__).parents[1],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_whatsapp_transport_migration_upgrades_and_downgrades(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'whatsapp-migration.db'}"
    _alembic(database_url, "upgrade", "20260829_0015")
    legacy_id = uuid4().hex
    communication_id = uuid4().hex
    order_id = uuid4().hex
    client_id = uuid4().hex
    admin_id = uuid4().hex
    instant = now().replace(tzinfo=None)
    migration_engine = create_engine(database_url)
    with migration_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO admin_user "
                "(id, email, password_hash, email_verified, totp_secret) "
                "VALUES (:id, :email, :password, 1, :totp)"
            ),
            {"id": admin_id, "email": "migration@markina.test", "password": "hash", "totp": "secret"},
        )
        connection.execute(
            text("INSERT INTO client (id, full_name, phone_e164) VALUES (:id, :name, :phone)"),
            {"id": client_id, "name": "Cliente Migration", "phone": "+5511555550002"},
        )
        # As FKs de pedido/galeria são irrelevantes para a preservação da outbox no SQLite.
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(
            text(
                "INSERT INTO payment_communication "
                "(id, sale_order_id, client_id, idempotency_key, status, decided_by_admin_id, decided_at, created_at) "
                "VALUES (:id, :order_id, :client_id, :key, 'confirmed', :admin_id, :instant, :instant)"
            ),
            {
                "id": communication_id,
                "order_id": order_id,
                "client_id": client_id,
                "key": "legacy-communication",
                "admin_id": admin_id,
                "instant": instant,
            },
        )
        connection.execute(
            text(
                "INSERT INTO payment_notification_outbox "
                "(id, payment_communication_id, recipient_phone, template_kind, idempotency_key, status, attempts, last_error, created_at, updated_at) "
                "VALUES (:id, :communication_id, :phone, 'confirmed', :key, 'queued', 0, NULL, :instant, :instant)"
            ),
            {
                "id": legacy_id,
                "communication_id": communication_id,
                "phone": "+5511555550002",
                "key": "legacy-outbox",
                "instant": instant,
            },
        )
    _alembic(database_url, "upgrade", "head")
    with migration_engine.connect() as connection:
        assert connection.scalar(
            text("SELECT COUNT(*) FROM payment_notification_outbox WHERE id = :id"),
            {"id": legacy_id},
        ) == 1
    _alembic(database_url, "downgrade", "20260829_0015")
    with migration_engine.connect() as connection:
        assert connection.scalar(
            text("SELECT COUNT(*) FROM payment_notification_outbox WHERE id = :id"),
            {"id": legacy_id},
        ) == 1
    _alembic(database_url, "upgrade", "head")


def test_otp_request_queues_encrypted_delivery_without_network(monkeypatch) -> None:
    key = os.urandom(32)
    monkeypatch.setenv("WHATSAPP_PROVIDER", "evolution")
    monkeypatch.setenv(
        "WHATSAPP_OTP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(key).decode("ascii"),
    )
    monkeypatch.setattr("app.auth.secrets.randbelow", lambda _limit: 123456)
    with TestClient(app) as client:
        response = client.post(
            "/auth/client/challenge",
            json={"full_name": "Cliente Sintético", "phone": "+5511555550003"},
        )
    assert response.status_code == 202
    assert "123456" not in response.text
    with SessionLocal() as db:
        delivery = db.scalar(select(WhatsAppDelivery))
        assert delivery.status == "queued"
        assert delivery.encrypted_payload
        assert "123456" not in delivery.encrypted_payload
        assert (
            decrypt_otp(
                delivery.encrypted_payload,
                key=key,
                context=delivery.idempotency_key,
            )
            == "123456"
        )


def test_worker_sends_queued_otp_and_erases_ciphertext(monkeypatch, capsys) -> None:
    key = os.urandom(32)
    phone = "+5511555550004"
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "evolution")
    monkeypatch.setenv(
        "WHATSAPP_OTP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(key).decode("ascii"),
    )
    sent_messages = []

    class FakeEvolution:
        def connection_status(self):
            return WhatsAppConnectionStatus("open", phone)

        def send_transactional(self, recipient, message, *, idempotency_key):
            sent_messages.append((recipient, message, idempotency_key))
            return WhatsAppDeliveryResult("evolution-message-1", recipient, "pending")

    monkeypatch.setattr(
        "app.worker.whatsapp_provider_from_environment", lambda: FakeEvolution()
    )
    with SessionLocal() as db:
        db.add(
            WhatsAppChannelSettings(
                environment="homolog", expected_phone_e164=phone, status="pending_pairing"
            )
        )
        delivery = WhatsAppDelivery(
            kind="otp",
            source_type="auth_challenge",
            source_id=str(uuid4()),
            recipient_phone=phone,
            template_kind="client_otp",
            idempotency_key="otp-worker-1",
            encrypted_payload=encrypt_otp("654321", key=key, context="otp-worker-1"),
            expires_at=now() + timedelta(minutes=5),
        )
        db.add(delivery)
        db.commit()
        delivery_id = delivery.id
    assert process_next_whatsapp_delivery() is True
    assert sent_messages == [(phone, "Seu código de acesso Markina Gallery é 654321.", "otp-worker-1")]
    with SessionLocal() as db:
        delivered = db.get(WhatsAppDelivery, delivery_id)
        assert delivered.status == "accepted"
        assert delivered.encrypted_payload is None
        assert delivered.external_message_id == "evolution-message-1"
    output = capsys.readouterr().out + capsys.readouterr().err
    assert "654321" not in output
    assert phone not in output


def test_worker_expires_otp_without_calling_provider(monkeypatch) -> None:
    called = False

    def unexpected_provider():
        nonlocal called
        called = True
        raise AssertionError("provider não deve ser chamado")

    monkeypatch.setattr(
        "app.worker.whatsapp_provider_from_environment", unexpected_provider
    )
    with SessionLocal() as db:
        delivery = WhatsAppDelivery(
            kind="otp",
            source_type="auth_challenge",
            source_id=str(uuid4()),
            recipient_phone="+5511555550005",
            template_kind="client_otp",
            idempotency_key="otp-expired-1",
            encrypted_payload="ciphertext-synthetic",
            expires_at=now() - timedelta(seconds=1),
        )
        db.add(delivery)
        db.commit()
        delivery_id = delivery.id
    assert process_next_whatsapp_delivery() is True
    assert called is False
    with SessionLocal() as db:
        expired_delivery = db.get(WhatsAppDelivery, delivery_id)
        assert expired_delivery.status == "expired"
        assert expired_delivery.encrypted_payload is None


def authenticated_admin_client() -> TestClient:
    raw_token = "synthetic-admin-session"
    with SessionLocal() as db:
        db.add(
            AuthSession(
                token_hash=token_hash(raw_token),
                role=Role.ADMIN.value,
                subject_id=uuid4(),
                expires_at=now() + timedelta(hours=1),
            )
        )
        db.commit()
    client = TestClient(app)
    client.cookies.set("markina_session", raw_token)
    return client


def test_admin_whatsapp_channel_requires_admin_and_masks_identity(monkeypatch) -> None:
    phone = "+5511555550006"

    class ConnectedProvider:
        def connection_status(self):
            return WhatsAppConnectionStatus("open", phone)

        def start_pairing(self, expected):
            assert expected == phone
            return WhatsAppPairingResult("connecting", pairing_code="1234-5678")

    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "evolution")
    monkeypatch.setattr(
        "app.main.whatsapp_provider_from_environment", lambda: ConnectedProvider()
    )
    with TestClient(app) as anonymous:
        assert anonymous.get("/admin/whatsapp/channel").status_code == 403
    with authenticated_admin_client() as client:
        configured = client.patch(
            "/admin/whatsapp/channel", json={"expected_phone_e164": phone}
        )
        assert configured.status_code == 200
        assert configured.json()["expected_phone"] != phone
        assert configured.json()["status"] == "pending_pairing"
        ready = client.get("/admin/whatsapp/channel")
        assert ready.json()["status"] == "ready"
        assert ready.json()["connected_phone"] != phone
        assert "api_key" not in ready.text.lower()
        pairing = client.post("/admin/whatsapp/channel/pairing")
        assert pairing.status_code == 200
        assert pairing.headers["cache-control"] == "no-store"
        assert pairing.json()["pairing"]["pairing_code"] == "1234-5678"
        assert client.patch(
            "/admin/whatsapp/channel", json={"expected_phone_e164": "11999999999"}
        ).status_code == 422


def test_admin_whatsapp_channel_blocks_mismatched_sender(monkeypatch) -> None:
    class MismatchedProvider:
        def connection_status(self):
            return WhatsAppConnectionStatus("open", "+5511555559999")

    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "evolution")
    monkeypatch.setattr(
        "app.main.whatsapp_provider_from_environment", lambda: MismatchedProvider()
    )
    with authenticated_admin_client() as client:
        assert client.patch(
            "/admin/whatsapp/channel",
            json={"expected_phone_e164": "+5511555550007"},
        ).status_code == 200
        payload = client.get("/admin/whatsapp/channel").json()
        assert payload["status"] == "mismatch"
        assert "diverge" in payload["last_error"]
        assert "+5511555559999" not in str(payload)


def test_whatsapp_webhook_is_authenticated_deduplicated_and_monotonic(
    monkeypatch,
) -> None:
    monkeypatch.setenv("WHATSAPP_WEBHOOK_SECRET", "synthetic-webhook-secret")
    with SessionLocal() as db:
        delivery = WhatsAppDelivery(
            kind="payment",
            source_type="payment_notification_outbox",
            source_id=str(uuid4()),
            recipient_phone="+5511555550008",
            template_kind="confirmed",
            idempotency_key="webhook-delivery-1",
            status="accepted",
            external_message_id="webhook-message-1",
        )
        db.add(delivery)
        db.commit()
        delivery_id = delivery.id
    payload = {
        "event": "messages.update",
        "data": {"key": {"id": "webhook-message-1"}, "status": "delivered"},
    }
    with TestClient(app) as client:
        assert client.post("/internal/whatsapp/webhook", json=payload).status_code == 403
        headers = {"X-Markina-Webhook-Secret": "synthetic-webhook-secret"}
        first = client.post("/internal/whatsapp/webhook", json=payload, headers=headers)
        duplicate = client.post("/internal/whatsapp/webhook", json=payload, headers=headers)
        assert first.json() == {"status": "delivery_updated"}
        assert duplicate.json() == {"status": "duplicate"}
        older = client.post(
            "/internal/whatsapp/webhook",
            json={
                "event": "messages.update",
                "data": {"key": {"id": "webhook-message-1"}, "status": "accepted"},
            },
            headers=headers,
        )
        assert older.status_code == 200
        ignored = client.post(
            "/internal/whatsapp/webhook",
            json={"event": "messages.upsert", "data": {"message": "não persistir"}},
            headers=headers,
        )
        assert ignored.json() == {"status": "ignored"}
        assert client.post(
            "/internal/whatsapp/webhook",
            content=b"x" * 65_537,
            headers={**headers, "content-type": "application/json"},
        ).status_code == 413
    with SessionLocal() as db:
        updated = db.get(WhatsAppDelivery, delivery_id)
        assert updated.status == "delivered"


def test_connection_webhook_updates_ready_state(monkeypatch) -> None:
    phone = "+5511555550009"
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("WHATSAPP_WEBHOOK_SECRET", "synthetic-webhook-secret")
    with SessionLocal() as db:
        settings = WhatsAppChannelSettings(
            environment="homolog", expected_phone_e164=phone, status="connecting"
        )
        db.add(settings)
        db.commit()
        settings_id = settings.id
    with TestClient(app) as client:
        response = client.post(
            "/internal/whatsapp/webhook",
            json={
                "event": "connection.update",
                "data": {"state": "open", "ownerJid": "5511555550009@s.whatsapp.net"},
            },
            headers={"X-Markina-Webhook-Secret": "synthetic-webhook-secret"},
        )
        assert response.json() == {"status": "connection_updated"}
    with SessionLocal() as db:
        assert db.get(WhatsAppChannelSettings, settings_id).status == "ready"


def test_workers_reserve_delivery_once_under_concurrency(monkeypatch) -> None:
    key = os.urandom(32)
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv(
        "WHATSAPP_OTP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(key).decode("ascii"),
    )
    sent = []
    sent_lock = threading.Lock()

    class SlowProvider:
        def send_transactional(self, recipient, message, *, idempotency_key):
            del message
            time.sleep(0.05)
            with sent_lock:
                sent.append(idempotency_key)
            return WhatsAppDeliveryResult("concurrent-message", recipient, "accepted")

    monkeypatch.setattr(
        "app.worker.whatsapp_provider_from_environment", lambda: SlowProvider()
    )
    with SessionLocal() as db:
        db.add(
            WhatsAppDelivery(
                kind="otp",
                source_type="auth_challenge",
                source_id=str(uuid4()),
                recipient_phone="+5511555550010",
                template_kind="client_otp",
                idempotency_key="otp-concurrent-1",
                encrypted_payload=encrypt_otp(
                    "112233", key=key, context="otp-concurrent-1"
                ),
                expires_at=now() + timedelta(minutes=5),
            )
        )
        db.commit()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: process_next_whatsapp_delivery(), range(2)))
    assert sent == ["otp-concurrent-1"]
    assert results.count(True) == 1


def test_ambiguous_failure_is_not_retried_blindly(monkeypatch) -> None:
    key = os.urandom(32)
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv(
        "WHATSAPP_OTP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(key).decode("ascii"),
    )

    class AmbiguousProvider:
        def send_transactional(self, *_args, **_kwargs):
            from app.messaging import WhatsAppDeliveryError

            raise WhatsAppDeliveryError(
                "Resultado desconhecido.", transient=False, ambiguous=True
            )

    monkeypatch.setattr(
        "app.worker.whatsapp_provider_from_environment", lambda: AmbiguousProvider()
    )
    with SessionLocal() as db:
        delivery = WhatsAppDelivery(
            kind="otp",
            source_type="auth_challenge",
            source_id=str(uuid4()),
            recipient_phone="+5511555550011",
            template_kind="client_otp",
            idempotency_key="otp-unknown",
            encrypted_payload=encrypt_otp(
                "445566", key=key, context="otp-unknown"
            ),
            expires_at=now() + timedelta(minutes=5),
        )
        db.add(delivery)
        db.commit()
        delivery_id = delivery.id
    assert process_next_whatsapp_delivery() is True
    assert process_next_whatsapp_delivery() is False
    with SessionLocal() as db:
        assert db.get(WhatsAppDelivery, delivery_id).status == "unknown"


def test_stale_processing_becomes_unknown_after_worker_restart(monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_PROCESSING_TIMEOUT_SECONDS", "30")
    with SessionLocal() as db:
        delivery = WhatsAppDelivery(
            kind="payment",
            source_type="payment_notification_outbox",
            source_id=str(uuid4()),
            recipient_phone="+5511555550012",
            template_kind="confirmed",
            idempotency_key="stale-processing-1",
            status="processing",
            attempts=1,
            updated_at=now() - timedelta(minutes=2),
        )
        db.add(delivery)
        db.commit()
        delivery_id = delivery.id
    assert process_next_whatsapp_delivery() is True
    with SessionLocal() as db:
        assert db.get(WhatsAppDelivery, delivery_id).status == "unknown"


def test_manual_retry_enforces_ambiguity_window_and_hides_recipient(monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_AMBIGUOUS_RETRY_AFTER_SECONDS", "60")
    phone = "+5511555550013"
    with SessionLocal() as db:
        delivery = WhatsAppDelivery(
            kind="payment",
            source_type="payment_notification_outbox",
            source_id=str(uuid4()),
            recipient_phone=phone,
            template_kind="confirmed",
            idempotency_key="manual-retry-1",
            status="unknown",
            attempts=1,
            updated_at=now(),
        )
        db.add(delivery)
        db.commit()
        delivery_id = delivery.id
    with authenticated_admin_client() as client:
        listing = client.get("/admin/whatsapp/deliveries")
        assert listing.status_code == 200
        assert phone not in listing.text
        blocked = client.post(
            f"/admin/whatsapp/deliveries/{delivery_id}/retry",
            json={"confirm_duplicate_risk": True},
        )
        assert blocked.status_code == 409
        with SessionLocal() as db:
            item = db.get(WhatsAppDelivery, delivery_id)
            item.updated_at = now() - timedelta(minutes=2)
            db.commit()
        requires_confirmation = client.post(
            f"/admin/whatsapp/deliveries/{delivery_id}/retry", json={}
        )
        assert requires_confirmation.status_code == 409
        retried = client.post(
            f"/admin/whatsapp/deliveries/{delivery_id}/retry",
            json={"confirm_duplicate_risk": True},
        )
        assert retried.json() == {"status": "queued"}


def test_worker_prioritizes_otp_over_payment(monkeypatch) -> None:
    key = os.urandom(32)
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv(
        "WHATSAPP_OTP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(key).decode("ascii"),
    )
    with SessionLocal() as db:
        payment = WhatsAppDelivery(
            kind="payment",
            source_type="payment_notification_outbox",
            source_id=str(uuid4()),
            recipient_phone="+5511555550014",
            template_kind="confirmed",
            idempotency_key="priority-payment",
        )
        otp = WhatsAppDelivery(
            kind="otp",
            source_type="auth_challenge",
            source_id=str(uuid4()),
            recipient_phone="+5511555550015",
            template_kind="client_otp",
            idempotency_key="priority-otp",
            encrypted_payload=encrypt_otp("778899", key=key, context="priority-otp"),
            expires_at=now() + timedelta(minutes=5),
        )
        db.add_all([payment, otp])
        db.commit()
        payment_id, otp_id = payment.id, otp.id
    assert process_next_whatsapp_delivery() is True
    with SessionLocal() as db:
        assert db.get(WhatsAppDelivery, otp_id).status == "accepted"
        assert db.get(WhatsAppDelivery, payment_id).status == "queued"
