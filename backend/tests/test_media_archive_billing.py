"""Cobrança local de recuperações com carteira e worker sintéticos."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app import media_archive_billing as billing
from app import photographer_credits as credits
from app.auth import (
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveOperation,
    MediaArchiveRecoveryCreditAllocationEvent,
    MediaArchiveRecoveryCreditReservation,
    MediaArchiveRecoveryPricing,
    MediaArchiveRecoveryRequest,
    PhotoFolder,
    PhotographerCreditEntry,
    TenantCreditWallet,
    now,
)
from app.credit_history import history_page
from app.media_archive_worker import complete_restore_operation, fail_operation
from tests.schema_fixtures import create_test_schema
from tests.test_photographer_credits import create_accounts, create_photo
from tests.test_tenant_client_isolation import client_db as _client_db
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

client_db = _client_db
postgres_schema = _postgres_schema


def _archived_cycle(db, tenant_id):
    photo = create_photo(db, tenant_id)
    folder = db.get(PhotoFolder, photo.folder_id)
    folder.status = "released"
    folder.released_at = now() - timedelta(days=60)
    folder.access_duration_days = 30
    folder.access_expires_at = now() - timedelta(days=30)
    cycle = MediaArchiveCycle(
        tenant_id=tenant_id,
        parent_gallery_id=photo.parent_gallery_id,
        folder_id=photo.folder_id,
        cycle_number=1,
        state="archived",
        object_count=1,
        total_bytes=20,
    )
    db.add(cycle)
    db.flush()
    return cycle, folder


def _queue_restore(db, operation_id, *, at):
    operation = db.get(MediaArchiveOperation, operation_id)
    cycle = db.get(MediaArchiveCycle, operation.cycle_id)
    token = "synthetic-restore-lease"
    expiry = at + timedelta(minutes=2)
    operation.status = "processing"
    operation.stage = "verified_promoted"
    operation.lease_token = token
    operation.lease_expires_at = expiry
    operation.details = {
        **(operation.details or {}),
        "restore_readback_verified": True,
        "restore_manifest_verified": True,
        "restored_object_count": cycle.object_count,
        "promoted_object_count": cycle.object_count,
    }
    cycle.state = "restoring"
    coordinator = db.get(MediaArchiveCoordinator, 1)
    if coordinator is None:
        coordinator = MediaArchiveCoordinator(id=1)
        db.add(coordinator)
    coordinator.active_operation_id = operation.id
    coordinator.lease_token = token
    coordinator.lease_expires_at = expiry
    db.flush()
    return token


def _pricing(db, owner_id, fee):
    db.add(MediaArchiveRecoveryPricing(
        id=1, recovery_fee_credits=fee, updated_by_admin_id=owner_id,
    ))


def _request(db, tenant, admin, cycle, *, key="tenant-request-001", days=14):
    return billing.request_recovery(
        db, tenant_id=tenant.id, actor_admin_id=admin.id,
        cycle_id=cycle.id, duration_days=days, idempotency_key=key,
    )


def test_unconfigured_or_insufficient_price_fails_before_operation_or_reservation(client_db):
    _owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    cycle, _folder = _archived_cycle(client_db, tenant.id)
    client_db.commit()

    with pytest.raises(HTTPException) as unconfigured:
        _request(client_db, tenant, photographer, cycle)
    assert unconfigured.value.status_code == 409
    assert client_db.scalar(select(MediaArchiveOperation.id)) is None

    _pricing(client_db, owner.id, 2)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "one-credit", "synthetic")
    client_db.commit()
    with pytest.raises(HTTPException) as insufficient:
        _request(client_db, tenant, photographer, cycle, key="tenant-request-002")
    assert insufficient.value.status_code == 409
    assert client_db.scalar(select(MediaArchiveOperation.id)) is None
    assert client_db.scalar(select(MediaArchiveRecoveryCreditReservation.id)) is None


def test_active_recovery_check_does_not_lock_operation_while_cycle_is_locked(client_db):
    _owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    cycle, _folder = _archived_cycle(client_db, tenant.id)
    _pricing(client_db, owner.id, 1)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "active-recovery", "synthetic")
    _request(client_db, tenant, photographer, cycle, key="active-recovery-first")
    client_db.commit()

    row_locks = []

    def record_row_lock(execute_state):
        statement = execute_state.statement
        if not execute_state.is_select or getattr(statement, "_for_update_arg", None) is None:
            return
        sql = str(statement).lower()
        if "media_archive_cycle" in sql:
            row_locks.append("cycle")
        elif "media_archive_operation" in sql:
            row_locks.append("operation")

    event.listen(client_db, "do_orm_execute", record_row_lock)
    try:
        with pytest.raises(HTTPException) as active:
            _request(client_db, tenant, photographer, cycle, key="active-recovery-second")
    finally:
        event.remove(client_db, "do_orm_execute", record_row_lock)
        client_db.rollback()

    assert active.value.status_code == 409
    assert row_locks == ["cycle"]
    assert client_db.scalar(select(func.count()).select_from(MediaArchiveOperation).where(
        MediaArchiveOperation.tenant_id == tenant.id,
        MediaArchiveOperation.operation_type == "restore",
    )) == 1
    assert client_db.scalar(select(func.count()).select_from(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.tenant_id == tenant.id,
    )) == 1


def test_concurrent_recovery_requests_cannot_overreserve_the_same_wallet(postgres_schema):
    create_test_schema(postgres_schema)
    with Session(postgres_schema, expire_on_commit=False) as db:
        _owner_tenant, tenant, owner, photographer = create_accounts(db)
        first_cycle, _first_folder = _archived_cycle(db, tenant.id)
        second_cycle, _second_folder = _archived_cycle(db, tenant.id)
        _pricing(db, owner.id, 2)
        credits.grant_credits(db, owner.id, tenant.id, 2, "concurrent-grant", "synthetic")
        db.commit()
        tenant_id = tenant.id
        photographer_id = photographer.id
        cycle_ids = [first_cycle.id, second_cycle.id]

    barrier = Barrier(2)

    def request(cycle_id: UUID):
        with Session(postgres_schema) as db:
            barrier.wait(timeout=10)
            try:
                result = billing.request_recovery(
                    db,
                    tenant_id=tenant_id,
                    actor_admin_id=photographer_id,
                    cycle_id=cycle_id,
                    duration_days=14,
                    idempotency_key=f"concurrent-recovery-{cycle_id}",
                )
                db.commit()
                return ("created", result)
            except HTTPException as exc:
                db.rollback()
                return ("rejected", exc.status_code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(request, cycle_ids))

    assert sorted(outcome[0] for outcome in outcomes) == ["created", "rejected"]
    rejection = next(outcome for outcome in outcomes if outcome[0] == "rejected")
    assert rejection == ("rejected", 409)
    with Session(postgres_schema) as db:
        assert db.scalar(select(func.count()).select_from(MediaArchiveRecoveryRequest)) == 1
        assert db.scalar(select(func.count()).select_from(MediaArchiveRecoveryCreditReservation).where(
            MediaArchiveRecoveryCreditReservation.status == "reserved",
        )) == 1
        wallet = credits.wallet_snapshot(db, tenant_id)
        assert wallet["available_credits"] == 0
        assert wallet["reserved_credits"] == 2


def test_recovery_reserves_fifo_and_debits_once_after_verified_restore(client_db):
    _owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    cycle, folder = _archived_cycle(client_db, tenant.id)
    _pricing(client_db, owner.id, 2)
    first = credits.grant_credits(client_db, owner.id, tenant.id, 1, "grant-first", "synthetic-a")
    second = credits.grant_credits(client_db, owner.id, tenant.id, 2, "grant-second", "synthetic-b")
    first.created_at = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)
    second.created_at = datetime(2026, 11, 2, 0, 0, tzinfo=UTC)
    client_db.commit()

    result = _request(client_db, tenant, photographer, cycle)
    client_db.commit()
    operation_id = UUID(result["operation_id"])
    snapshot = credits.wallet_snapshot(client_db, tenant.id)
    assert snapshot["available_credits"] == 1
    assert snapshot["reserved_credits"] == 2
    assert snapshot["pending_operations"] == 1
    assert snapshot["pending_upload_operations"] == 0
    assert snapshot["pending_recovery_operations"] == 1
    allocations = list(client_db.scalars(select(MediaArchiveRecoveryCreditAllocationEvent).where(
        MediaArchiveRecoveryCreditAllocationEvent.operation_id == operation_id,
        MediaArchiveRecoveryCreditAllocationEvent.event_type == "reserved",
    ).order_by(MediaArchiveRecoveryCreditAllocationEvent.occurred_at)))
    assert [(item.source_entry_id, item.quantity) for item in allocations] == [
        (first.id, 1), (second.id, 1),
    ]

    at = datetime(2026, 11, 9, 18, 0, tzinfo=UTC)
    lease = _queue_restore(client_db, operation_id, at=at)
    client_db.commit()
    complete_restore_operation(
        client_db, operation_id=operation_id, lease_token=lease, at=at,
    )

    operation = client_db.get(MediaArchiveOperation, operation_id)
    reservation = client_db.scalar(select(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.operation_id == operation_id,
    ))
    ledger = client_db.scalar(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.archive_operation_id == operation_id,
        PhotographerCreditEntry.entry_type == "archive_recovery",
    ))
    assert operation.status == "completed"
    assert reservation.status == "consumed"
    assert ledger.delta == -2
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 1
    assert folder.access_duration_days == 14
    assert folder.released_at.replace(tzinfo=UTC) == at
    assert folder.access_expires_at.replace(tzinfo=UTC) == at + timedelta(days=14)
    assert billing.list_tenant_recoveries(client_db, tenant.id)[0]["fee_credits"] == 2
    assert billing.list_tenant_recoveries(client_db, tenant.id)[0]["status"] == "completed"
    recovery_entry = next(
        item for item in history_page(
            client_db, tenant.id, as_of=at + timedelta(seconds=1),
        )["items"]
        if item["type"] == "archive_recovery"
    )
    assert recovery_entry["related_folder_name"] == folder.name
    assert recovery_entry["folder_id"] == str(folder.id)
    assert billing.consume_verified_recovery(
        client_db, operation=operation, at=at,
    ) == ledger


def test_existing_debit_with_held_reservation_fails_closed(client_db):
    _owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    cycle, _folder = _archived_cycle(client_db, tenant.id)
    _pricing(client_db, owner.id, 2)
    credits.grant_credits(client_db, owner.id, tenant.id, 2, "grant-inconsistent", "synthetic")
    result = _request(client_db, tenant, photographer, cycle)
    client_db.commit()
    operation = client_db.get(MediaArchiveOperation, UUID(result["operation_id"]))
    client_db.add(PhotographerCreditEntry(
        tenant_id=tenant.id,
        entry_type="archive_recovery",
        delta=-2,
        idempotency_key=f"archive-recovery:{operation.id}",
        archive_operation_id=operation.id,
        source_reference=str(cycle.id),
        description="Recuperação de arquivo frio",
    ))
    client_db.commit()

    with pytest.raises(HTTPException) as inconsistent:
        billing.consume_verified_recovery(
            client_db, operation=operation, at=datetime(2026, 11, 9, 18, 0, tzinfo=UTC),
        )
    assert inconsistent.value.status_code == 503
    reservation = client_db.scalar(select(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.operation_id == operation.id,
    ))
    assert reservation.status == "reserved"


def test_owner_recovery_is_exempt_from_price_and_credit_ledger(client_db):
    owner_tenant, _tenant, owner, _photographer = create_accounts(client_db)
    cycle, _folder = _archived_cycle(client_db, owner_tenant.id)
    client_db.commit()

    result = billing.request_recovery(
        client_db,
        tenant_id=owner_tenant.id,
        actor_admin_id=owner.id,
        cycle_id=cycle.id,
        duration_days=7,
        idempotency_key="owner-unmetered-recovery",
    )
    client_db.commit()
    operation_id = UUID(result["operation_id"])
    assert result["owner_exempt"] is True
    assert result["fee_credits"] is None
    assert credits.wallet_snapshot(client_db, owner_tenant.id)["mode"] == "unmetered"

    at = datetime(2026, 11, 9, 18, 0, tzinfo=UTC)
    lease = _queue_restore(client_db, operation_id, at=at)
    client_db.commit()
    complete_restore_operation(client_db, operation_id=operation_id, lease_token=lease, at=at)
    assert client_db.scalar(select(PhotographerCreditEntry.id).where(
        PhotographerCreditEntry.archive_operation_id == operation_id,
    )) is None


def test_unmetered_wallet_on_non_owner_tenant_fails_closed(client_db):
    owner_tenant, tenant, _owner, photographer = create_accounts(client_db)
    cycle, _folder = _archived_cycle(client_db, tenant.id)
    owner_wallet = client_db.get(TenantCreditWallet, owner_tenant.id)
    target_wallet = client_db.get(TenantCreditWallet, tenant.id)
    owner_wallet.mode = "finite"
    client_db.commit()
    target_wallet.mode = "unmetered"
    client_db.commit()

    with pytest.raises(HTTPException) as failure:
        billing.request_recovery(
            client_db,
            tenant_id=tenant.id,
            actor_admin_id=photographer.id,
            cycle_id=cycle.id,
            duration_days=7,
            idempotency_key="misassigned-unmetered-wallet",
        )
    assert failure.value.status_code == 503
    assert client_db.scalar(select(func.count()).select_from(MediaArchiveOperation).where(
        MediaArchiveOperation.tenant_id == tenant.id,
        MediaArchiveOperation.operation_type == "restore",
    )) == 0


def test_proven_failure_releases_reservation_and_unknown_result_keeps_it(client_db):
    _owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    cycle, _folder = _archived_cycle(client_db, tenant.id)
    _pricing(client_db, owner.id, 2)
    credits.grant_credits(client_db, owner.id, tenant.id, 2, "grant-failure", "synthetic")
    result = _request(client_db, tenant, photographer, cycle)
    client_db.commit()
    operation_id = UUID(result["operation_id"])
    at = datetime(2026, 11, 9, 18, 0, tzinfo=UTC)
    lease = _queue_restore(client_db, operation_id, at=at)
    operation = client_db.get(MediaArchiveOperation, operation_id)
    operation.stage = "downloading"
    client_db.commit()
    fail_operation(
        client_db, operation_id=operation_id, lease_token=lease,
        outcome="proven_failure", error_code="drive_timeout", at=at,
    )
    reservation = client_db.scalar(select(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.operation_id == operation_id,
    ))
    assert reservation.status == "released"
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 2
    assert client_db.scalar(select(PhotographerCreditEntry.id).where(
        PhotographerCreditEntry.archive_operation_id == operation_id,
    )) is None

    second_cycle, _folder2 = _archived_cycle(client_db, tenant.id)
    result = _request(
        client_db, tenant, photographer, second_cycle, key="tenant-request-uncertain",
    )
    client_db.commit()
    second_id = UUID(result["operation_id"])
    lease = _queue_restore(client_db, second_id, at=at)
    client_db.get(MediaArchiveOperation, second_id).stage = "downloading"
    client_db.commit()
    fail_operation(
        client_db, operation_id=second_id, lease_token=lease,
        outcome="unknown", error_code="provider_uncertain", at=at,
    )
    held = client_db.scalar(select(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.operation_id == second_id,
    ))
    assert held.status == "reconciliation_required"
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 0
    tenant_view = billing.list_tenant_recoveries(client_db, tenant.id)[0]
    assert "last_error" not in tenant_view
    assert "last_error_code" not in tenant_view
    owner_view = billing.list_owner_recoveries(client_db, owner.id, tenant.id)[0]
    assert owner_view["last_error_code"] == "provider_uncertain"
    assert owner_view["last_error"] == "Resultado externo incerto; reconciliação necessária."


def test_recovery_candidates_are_archived_and_tenant_scoped(client_db):
    owner_tenant, tenant, _owner, _photographer = create_accounts(client_db)
    cycle, folder = _archived_cycle(client_db, tenant.id)
    _other_cycle, other_folder = _archived_cycle(client_db, owner_tenant.id)
    local_cycle, local_folder = _archived_cycle(client_db, tenant.id)
    local_cycle.state = "local"
    client_db.commit()

    candidates = billing.list_recovery_candidates(client_db, tenant.id)
    assert candidates == [{
        "cycle_id": str(cycle.id),
        "folder_id": str(folder.id),
        "folder_name": folder.name,
        "cycle_number": 1,
        "archived_at": None,
    }]
    assert str(other_folder.id) not in {item["folder_id"] for item in candidates}
    assert str(local_folder.id) not in {item["folder_id"] for item in candidates}


def test_owner_retry_is_attributed_to_owner_and_links_the_failed_attempt(client_db):
    _owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    cycle, _folder = _archived_cycle(client_db, tenant.id)
    _pricing(client_db, owner.id, 2)
    credits.grant_credits(client_db, owner.id, tenant.id, 4, "grant-retry", "synthetic")
    first = _request(client_db, tenant, photographer, cycle)
    client_db.commit()
    failed_id = UUID(first["operation_id"])
    at = datetime(2026, 11, 9, 18, 0, tzinfo=UTC)
    lease = _queue_restore(client_db, failed_id, at=at)
    client_db.get(MediaArchiveOperation, failed_id).stage = "downloading"
    client_db.commit()
    fail_operation(
        client_db, operation_id=failed_id, lease_token=lease,
        outcome="proven_failure", error_code="drive_timeout", at=at,
    )
    pricing = client_db.get(MediaArchiveRecoveryPricing, 1)
    pricing.recovery_fee_credits = 3
    client_db.commit()

    retried = billing.request_recovery(
        client_db,
        tenant_id=tenant.id,
        actor_admin_id=owner.id,
        cycle_id=cycle.id,
        duration_days=7,
        idempotency_key="owner-retry-001",
        retry_of_operation_id=failed_id,
    )
    client_db.commit()
    retry_id = UUID(retried["operation_id"])
    retry_operation = client_db.get(MediaArchiveOperation, retry_id)
    retry_request = client_db.scalar(select(MediaArchiveRecoveryRequest).where(
        MediaArchiveRecoveryRequest.operation_id == retry_id,
    ))
    assert retry_operation.actor_type == "owner"
    assert retry_request.requester_type == "owner"
    assert retry_request.requested_by_admin_id == owner.id
    assert retry_request.requested_by_owner_admin_id == owner.id
    assert retry_request.requested_by_tenant_admin_id is None
    assert retry_request.retry_of_operation_id == failed_id
    assert retry_request.fee_credits_snapshot == 2
    retry_reservation = client_db.scalar(select(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.operation_id == retry_id,
    ))
    assert retry_reservation.reserved_credits == 2
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 2
