"""Fila financeira não impede o ciclo das funcionalidades existentes."""

from contextlib import contextmanager

import pytest

from app import mercadopago_credit_purchases, mercadopago_webhook, photographer_signup, worker


@pytest.mark.parametrize("has_payment", [True, False])
def test_fila_orders_nao_impede_midia_ou_privacidade(monkeypatch, has_payment):
    calls = []

    @contextmanager
    def session(_factory):
        yield object()

    monkeypatch.setattr(worker, "domain_session", session)
    for name in (
        "process_ready_batches", "process_highres_cleanup", "process_asset_file_cleanup",
        "process_next_notification", "process_next_gallery_lifecycle_operation",
        "process_next_photo_credit_reconciliation",
        "process_next_tenant_closure", "process_next_media_archive_operation",
        "process_next_media_job", "process_next_whatsapp_delivery", "process_next_email_delivery",
        "materialize_next_payment_notification", "process_next_gallery_membership_notification",
        "process_next_gallery_reopening_notification", "reconcile_next_unknown_delivery",
        "process_otp_privacy_cleanup", "process_admin_security_cleanup",
    ):
        def action(*_args, name=name):
            calls.append(name)
            return False
        monkeypatch.setattr(worker, name, action)
    monkeypatch.setattr(mercadopago_webhook, "process_next_mercadopago_event", lambda: has_payment)
    monkeypatch.setattr(mercadopago_webhook, "reconcile_next_mercadopago_payment", lambda: has_payment)
    monkeypatch.setattr(mercadopago_credit_purchases, "process_next_mercadopago_credit_purchase", lambda: False)
    monkeypatch.setattr(photographer_signup, "process_signup_expiry", lambda **_: False)
    assert worker.run_cycle() is has_payment
    assert "process_next_media_job" in calls
    assert "process_otp_privacy_cleanup" in calls
    assert "process_next_photo_credit_reconciliation" in calls


@pytest.mark.parametrize(("reconciled", "expected_action"), [(True, "commit"), (False, "rollback")])
def test_photo_credit_reconciliation_commits_only_when_operation_changed(monkeypatch, reconciled, expected_action):
    from app import photographer_credits

    actions = []

    class Session:
        def commit(self):
            actions.append("commit")

        def rollback(self):
            actions.append("rollback")

    @contextmanager
    def session():
        yield Session()

    monkeypatch.setattr(worker, "SessionLocal", session)
    monkeypatch.setattr(worker, "_last_photo_credit_reconciliation", -1.0)
    monkeypatch.setattr(
        photographer_credits,
        "reconcile_next_stale_photo_credit_operation",
        lambda _db: reconciled,
    )

    assert worker.process_next_photo_credit_reconciliation() is reconciled
    assert actions == [expected_action]
