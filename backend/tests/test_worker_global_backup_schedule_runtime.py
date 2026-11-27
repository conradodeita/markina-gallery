from __future__ import annotations

from contextlib import contextmanager

import pytest

pytest.importorskip(
    "mercadopago", reason="worker integration requires project payment dependencies"
)

from app import (
    global_postgresql_backup_scheduler,
    mercadopago_credit_purchases,
    mercadopago_webhook,
    photographer_signup,
    worker,
)


def _prepare_worker(monkeypatch, *, active_media_job=False):
    calls = []

    @contextmanager
    def domain_session(_session_factory):
        yield object()

    def false_work(name):
        def process(*_args, **_kwargs):
            calls.append(name)
            return False

        return process

    monkeypatch.setattr(worker, "domain_session", domain_session)
    monkeypatch.setattr(worker, "process_ready_batches", false_work("ready_batches"))
    for name in (
        "process_highres_cleanup",
        "process_asset_file_cleanup",
        "process_next_tenant_closure",
        "process_next_photo_credit_reconciliation",
        "process_next_gallery_lifecycle_operation",
        "process_next_media_archive_operation",
        "process_next_media_job",
        "process_next_whatsapp_delivery",
        "process_next_email_delivery",
        "materialize_next_payment_notification",
        "process_next_gallery_membership_notification",
        "process_next_gallery_reopening_notification",
        "reconcile_next_unknown_delivery",
        "process_otp_privacy_cleanup",
        "process_admin_security_cleanup",
    ):
        monkeypatch.setattr(worker, name, false_work(name))

    def notification(channel):
        calls.append(f"notification:{channel}")
        return False

    monkeypatch.setattr(worker, "process_next_notification", notification)
    monkeypatch.setattr(photographer_signup, "process_signup_expiry", false_work("signup_expiry"))
    monkeypatch.setattr(
        mercadopago_webhook, "process_next_mercadopago_event", false_work("mercadopago_event")
    )
    monkeypatch.setattr(
        mercadopago_webhook, "reconcile_next_mercadopago_payment", false_work("mercadopago_payment")
    )
    monkeypatch.setattr(
        mercadopago_credit_purchases,
        "process_next_mercadopago_credit_purchase",
        false_work("mercadopago_credit_purchase"),
    )

    def scheduled_backup():
        calls.append("global_backup")
        return False

    monkeypatch.setattr(
        global_postgresql_backup_scheduler,
        "process_scheduled_global_postgresql_backup",
        scheduled_backup,
    )
    if active_media_job:
        monkeypatch.setattr(
            worker, "process_next_media_job", lambda: calls.append("active_media_job") or True
        )
    return calls


def test_worker_runs_backup_after_other_work_is_idle(monkeypatch):
    calls = _prepare_worker(monkeypatch)

    assert worker.run_cycle() is False
    assert calls[-1] == "global_backup"


def test_worker_skips_backup_when_existing_media_job_is_claimed(monkeypatch):
    calls = _prepare_worker(monkeypatch, active_media_job=True)

    assert worker.run_cycle() is True
    assert calls[-1] == "active_media_job"
    assert "global_backup" not in calls
