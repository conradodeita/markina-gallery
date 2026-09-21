"""Upgrade isolado: sem acesso ao banco local/homologação ou envio de mensagens."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.test_private_gallery_operations_sales_migration import alembic


def test_notification_upgrade_preserves_history_and_baselines(tmp_path):
    url = f"sqlite:///{(tmp_path / 'notifications.db').as_posix()}"
    alembic(url, "upgrade", "20260913_0055")
    engine = create_engine(url)
    parent, client, template = [uuid4().hex for _ in range(3)]
    instant = datetime.now(UTC)
    body = "Pagamento confirmado: {{cliente}}, pedido {{pedido}}. Texto preservado."
    with engine.begin() as db:
        db.execute(text("INSERT INTO client (id, full_name, phone_e164) VALUES "
                        "(:id, 'Cliente sintético', '+5511999999999')"), {"id": client})
        db.execute(text("INSERT INTO parent_gallery (id, name, active, created_at) "
                        "VALUES (:id, 'Galeria sintética', 1, :now)"),
                   {"id": parent, "now": instant})
        db.execute(text("INSERT INTO parent_gallery_registration "
                        "(id, parent_gallery_id, client_id, status, created_at, updated_at) "
                        "VALUES (:id, :parent, :client, 'active', :now, :now)"),
                   {"id": uuid4().hex, "parent": parent, "client": client, "now": instant})
        db.execute(text("INSERT INTO payment_message_template (id, kind, body, updated_at) "
                        "VALUES (:id, 'confirmed', :body, :now)"),
                   {"id": template, "body": body, "now": instant})
        db.execute(text("INSERT INTO audit_event (id, event, subject, created_at) "
                        "VALUES (:id, 'client.login', :client, :now)"),
                   {"id": uuid4().hex, "client": client, "now": instant})
        # A massa anterior ao upgrade usa somente o contrato da revisão 0055.
        # Modelos ORM atuais podem conter colunas introduzidas depois dessa revisão.
        order_id, communication_id = uuid4().hex, uuid4().hex
        assert "payment_group_id" not in {
            column["name"] for column in inspect(db).get_columns("sale_order")
        }
        db.execute(text("INSERT INTO sale_order "
                        "(id, client_id, derived_gallery_id_snapshot, derived_gallery_name_snapshot, "
                        "parent_gallery_id_snapshot, parent_gallery_name_snapshot, payment_status, "
                        "total_cents, created_at) VALUES "
                        "(:id, :client, :gallery, 'Histórico', :parent, 'Evento', 'pending', 4000, :now)"),
                   {"id": order_id, "client": client, "gallery": uuid4().hex,
                    "parent": parent, "now": instant})
        db.execute(text("INSERT INTO payment_communication "
                        "(id, sale_order_id, client_id, idempotency_key, status, created_at) "
                        "VALUES (:id, :order, :client, 'legacy', 'confirmed', :now)"),
                   {"id": communication_id, "order": order_id, "client": client, "now": instant})
        db.execute(text("INSERT INTO payment_notification_outbox "
                        "(id, payment_communication_id, recipient_phone, template_kind, "
                        "idempotency_key, status, attempts, rendered_body_snapshot, created_at, updated_at) "
                        "VALUES (:id, :communication, '+5511999999999', 'confirmed', "
                        "'old-decision', 'sent', 1, 'Mensagem histórica', :now, :now)"),
                   {"id": uuid4().hex, "communication": communication_id, "now": instant})
    alembic(url, "upgrade", "head")
    alembic(url, "upgrade", "head")  # repetir upgrade não cria eventos
    with engine.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM notification_setting")) == 6
        assert db.scalar(text("SELECT whatsapp_body FROM notification_setting "
                              "WHERE event_type = 'payment_confirmed'")) == body
        assert db.scalar(text("SELECT body FROM payment_message_template")) == body
        assert db.scalar(text("SELECT count(*) FROM audit_event")) == 1
        assert db.scalar(text("SELECT count(*) FROM client")) == 1
        assert db.scalar(text("SELECT count(*) FROM notification_milestone WHERE baseline")) == 2
        for table in ("notification_event", "notification_delivery", "push_subscription",
                      "private_upload_batch", "private_upload_batch_asset", "whatsapp_delivery"):
            assert db.scalar(text(f"SELECT count(*) FROM {table}")) == 0
        historical = db.execute(text("SELECT status, attempts, rendered_body_snapshot "
                                     "FROM payment_notification_outbox")).one()
        assert tuple(historical) == ("sent", 1, "Mensagem histórica")
        assert db.scalar(text("SELECT total_cents FROM sale_order")) == 4000
        assert db.execute(text("SELECT id, sale_order_id, client_id, status, payment_group_id "
                               "FROM payment_communication")).one() == (
            communication_id, order_id, client, "confirmed", None
        )
        assert db.scalar(text("SELECT payment_group_id FROM sale_order")) is None
    columns = {c["name"] for c in inspect(engine).get_columns("push_subscription")}
    assert "encrypted_subscription" in columns
    assert not columns.intersection({"endpoint", "p256dh", "auth", "private_key"})

    # Duas transações disputam a mesma chave lógica; só uma pode vencer.
    def insert():
        try:
            with engine.begin() as db:
                db.execute(text("INSERT INTO push_subscription "
                                "(id, endpoint_fingerprint, encrypted_subscription, role, "
                                "subject_id, generation, active, created_at, updated_at) "
                                "VALUES (:id, :fp, 'ciphertext', 'client', :client, 1, 1, "
                                ":now, :now)"),
                           {"id": uuid4().hex, "fp": "a" * 64, "client": client, "now": instant})
            return True
        except IntegrityError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: insert(), range(2))) == [False, True]
    with engine.begin() as db, pytest.raises(IntegrityError):
        db.execute(text("INSERT INTO notification_milestone "
                        "(parent_gallery_id, client_id, kind, baseline, created_at) "
                        "VALUES (:parent, :client, 'first_access', 0, :now)"),
                   {"parent": parent, "client": client, "now": instant})
    # O ciclo antigo termina em 0055; o schema novo preenchido não admite downgrade.
    with pytest.raises(AssertionError, match="Rollback deve preservar dados"):
        alembic(url, "downgrade", "20260913_0055")
    with engine.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM push_subscription")) == 1
        assert db.scalar(text("SELECT count(*) FROM notification_milestone")) == 2
