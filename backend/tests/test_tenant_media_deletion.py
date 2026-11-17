"""Exclusão auditada de mídia fria com banco e storage sintéticos locais."""

from datetime import timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    MediaArchiveCycle,
    MediaArchiveObject,
    MediaArchiveOperation,
    PhotographerBusinessProfile,
    PlatformAdminEvent,
    Tenant,
    TenantAdmin,
    TenantClosureMediaDeletionBatch,
    TenantClosureMediaDeletionItem,
    TenantClosureRequest,
    now,
)
from app.media_archive_executor import execute_archive_operation, execute_delete_operation
from app.media_archive_worker import (
    MediaArchiveClaim,
    begin_delete_operation,
    checkpoint_operation,
    claim_next_operation,
    complete_delete_operation,
)
from app.tenant_closure_recovery import closure_console_payload, reopen_account, request_batch
from app.tenant_media_deletion import (
    DELETION_CONFIRMATION,
    evaluate_media_deletion_preflight,
    request_media_deletion,
    retry_media_deletion,
)
from tests.test_media_archive_executor import InMemoryArchiveStorage, _archive_fixture
from tests.test_photographer_credits import create_accounts, create_photo


class AmbiguousDeleteStorage(InMemoryArchiveStorage):
    """Apaga o primeiro objeto e falha no readback para simular resposta incerta."""

    def __init__(self):
        super().__init__()
        self.deleted = False
        self.fail_after_delete = True

    def delete_object(self, *, remote_id: str) -> None:
        super().delete_object(remote_id=remote_id)
        self.deleted = True

    def read_object(self, *, remote_id: str):
        if self.deleted and self.fail_after_delete:
            self.fail_after_delete = False
            raise RuntimeError("synthetic adapter detail must not be saved")
        return super().read_object(remote_id=remote_id)


class NoopDeleteStorage(InMemoryArchiveStorage):
    def delete_object(self, *, remote_id: str) -> None:
        del remote_id


class TrackingDeleteStorage(InMemoryArchiveStorage):
    def __init__(self):
        super().__init__()
        self.delete_order: list[str] = []

    def delete_object(self, *, remote_id: str) -> None:
        self.delete_order.append(remote_id)
        super().delete_object(remote_id=remote_id)


class CorruptingDeleteStorage(TrackingDeleteStorage):
    def __init__(self):
        super().__init__()
        self.corrupt = False

    def download_object(self, *, remote_id: str, destination):
        if not self.corrupt:
            return super().download_object(remote_id=remote_id, destination=destination)
        payload, _mime_type = self.objects[remote_id]
        corrupted = payload + b"synthetic-corruption"
        destination.write(corrupted)
        from app.media_archive_storage import ArchiveDownloadReceipt

        return ArchiveDownloadReceipt(len(corrupted), sha256(corrupted).hexdigest())


def _closed_archive_fixture(
    tmp_path, monkeypatch, *, storage_type=InMemoryArchiveStorage, photo_count=1,
):
    engine, tenant_id, _gallery_id, _folder_id, cycle_id, _archive_operation_id, _paths = (
        _archive_fixture(tmp_path, monkeypatch, photo_count=photo_count)
    )
    storage = storage_type()
    with Session(engine, expire_on_commit=False) as db:
        archive_claim = claim_next_operation(db)
        assert archive_claim is not None
        assert execute_archive_operation(db, archive_claim, storage=storage).status == "completed"

        _owner_tenant, _unused_tenant, owner, photographer = create_accounts(db)
        tenant = db.get(Tenant, tenant_id)
        assert tenant is not None
        assert db.scalar(select(AdminUser.id).where(AdminUser.id == photographer.id)) == photographer.id
        assert db.scalar(select(Tenant.id).where(Tenant.id == tenant_id)) == tenant_id
        db.add(TenantAdmin(tenant_id=tenant_id, admin_user_id=photographer.id))
        db.flush()
        tenant.lifecycle = "closed"
        closed_at = now() - timedelta(days=4000)
        closure = TenantClosureRequest(
            tenant_id=tenant_id,
            request_id=uuid4(),
            requested_by=photographer.id,
            state="closed",
            requested_at=closed_at - timedelta(days=1),
            closed_at=closed_at,
            terms_version="synthetic-terms-v1",
            terms_sha256="a" * 64,
            balance_snapshot=0,
            balance_acknowledged=True,
        )
        db.add_all([
            closure,
            PhotographerBusinessProfile(
                admin_user_id=photographer.id,
                tenant_id=tenant_id,
                full_name="Fotógrafa sintética",
                cpf_envelope="synthetic-encrypted-envelope",
                cpf_fingerprint="b" * 64,
                cpf_fingerprint_key_version="test-key-v1",
            ),
        ])
        db.commit()
        owner_id = owner.id
    return engine, tenant_id, cycle_id, owner_id, storage


def _request_deletion(db: Session, *, tenant_id, owner_id):
    return request_media_deletion(
        db,
        owner_id=owner_id,
        tenant_id=tenant_id,
        request_id=uuid4(),
        confirmation=DELETION_CONFIRMATION,
    )


def _start_delete(db: Session, *, tenant_id) -> MediaArchiveClaim:
    result = claim_next_operation(db)
    assert result is not None and result.tenant_id == tenant_id
    assert db.get(MediaArchiveOperation, result.operation_id).operation_type == "delete_remote"
    return result


def test_preflight_blocks_before_anniversary_without_mutating_cpf_or_queue(
    tmp_path, monkeypatch,
):
    engine, tenant_id, _cycle_id, owner_id, _storage = _closed_archive_fixture(
        tmp_path, monkeypatch,
    )
    with Session(engine, expire_on_commit=False) as db:
        closure = db.scalar(select(TenantClosureRequest).where(
            TenantClosureRequest.tenant_id == tenant_id,
        ))
        assert closure is not None
        closure.closed_at = now() - timedelta(days=2000)
        db.commit()
        plan = evaluate_media_deletion_preflight(db, tenant_id=tenant_id)
        assert plan.blocker == "review_not_due"
        with pytest.raises(HTTPException) as error:
            _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
        assert error.value.status_code == 409
        profile = db.scalar(select(PhotographerBusinessProfile).where(
            PhotographerBusinessProfile.tenant_id == tenant_id,
        ))
        assert profile is not None
        assert profile.cpf_fingerprint == "b" * 64
        assert profile.cpf_fingerprint_key_version == "test-key-v1"
        assert db.scalar(select(TenantClosureMediaDeletionBatch.id).where(
            TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        )) is None


def test_preflight_requires_all_cycles_archived_and_preserves_existing_records(
    tmp_path, monkeypatch,
):
    engine, tenant_id, cycle_id, owner_id, _storage = _closed_archive_fixture(
        tmp_path, monkeypatch,
    )
    with Session(engine, expire_on_commit=False) as db:
        db.get(MediaArchiveCycle, cycle_id).state = "local"
        db.commit()
        plan = evaluate_media_deletion_preflight(db, tenant_id=tenant_id)
        assert plan.blocker == "cycle_not_archived"
        with pytest.raises(HTTPException) as error:
            _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
        assert error.value.status_code == 409
        assert db.scalar(select(TenantClosureMediaDeletionBatch.id)) is None
        assert db.scalar(select(PhotographerBusinessProfile.cpf_fingerprint).where(
            PhotographerBusinessProfile.tenant_id == tenant_id,
        )) == "b" * 64


def test_preflight_blocks_missing_archive_cycle_and_preserves_cpf(
    tmp_path, monkeypatch,
):
    engine, *_ = _archive_fixture(tmp_path, monkeypatch)
    with Session(engine, expire_on_commit=False) as db:
        _owner_tenant, tenant, owner, photographer = create_accounts(db)
        create_photo(db, tenant.id)
        tenant.lifecycle = "closed"
        closed_at = now() - timedelta(days=4000)
        db.add_all([
            TenantClosureRequest(
                tenant_id=tenant.id,
                request_id=uuid4(),
                requested_by=photographer.id,
                state="closed",
                requested_at=closed_at - timedelta(days=1),
                closed_at=closed_at,
                terms_version="synthetic-terms-v1",
                terms_sha256="a" * 64,
                balance_snapshot=0,
                balance_acknowledged=True,
            ),
            PhotographerBusinessProfile(
                admin_user_id=photographer.id,
                tenant_id=tenant.id,
                full_name="Fotógrafa sintética sem ciclo",
                cpf_envelope="synthetic-encrypted-envelope",
                cpf_fingerprint="c" * 64,
                cpf_fingerprint_key_version="test-key-v1",
            ),
        ])
        db.commit()

        plan = evaluate_media_deletion_preflight(db, tenant_id=tenant.id)
        assert plan.cycles == ()
        assert plan.blocker == "archive_proof_unavailable"
        with pytest.raises(HTTPException) as error:
            _request_deletion(db, tenant_id=tenant.id, owner_id=owner.id)
        assert error.value.status_code == 409
        assert db.scalar(select(TenantClosureMediaDeletionBatch.id).where(
            TenantClosureMediaDeletionBatch.tenant_id == tenant.id,
        )) is None
        assert db.scalar(select(PhotographerBusinessProfile.cpf_fingerprint).where(
            PhotographerBusinessProfile.tenant_id == tenant.id,
        )) == "c" * 64


def test_deletion_verifies_every_object_then_clears_only_cpf_fingerprint(
    tmp_path, monkeypatch,
):
    engine, tenant_id, cycle_id, owner_id, storage = _closed_archive_fixture(
        tmp_path, monkeypatch, storage_type=TrackingDeleteStorage,
    )
    with Session(engine, expire_on_commit=False) as db:
        accepted = _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
        assert accepted["batch"]["state"] == "queued"
        manifest_remote_id = db.scalar(select(MediaArchiveObject.remote_object_id).where(
            MediaArchiveObject.tenant_id == tenant_id,
            MediaArchiveObject.cycle_id == cycle_id,
            MediaArchiveObject.object_type == "manifest",
        ))
        claim = _start_delete(db, tenant_id=tenant_id)
        result = execute_delete_operation(db, claim, storage=storage)
        assert result.status == "completed", result.error_code

        batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
            TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        ))
        assert batch is not None and batch.state == "completed"
        assert batch.object_count == batch.verified_deleted_object_count > 0
        assert storage.objects == {}
        assert storage.delete_order[-1] == manifest_remote_id
        assert db.get(MediaArchiveCycle, cycle_id).state == "deleted"
        objects = list(db.scalars(select(MediaArchiveObject).where(
            MediaArchiveObject.tenant_id == tenant_id,
        )))
        assert objects and all(item.remote_deleted_at is not None for item in objects)
        profile = db.scalar(select(PhotographerBusinessProfile).where(
            PhotographerBusinessProfile.tenant_id == tenant_id,
        ))
        assert profile is not None
        assert profile.cpf_fingerprint is None
        assert profile.cpf_fingerprint_key_version is None
        assert profile.cpf_envelope == "synthetic-encrypted-envelope"
        event_rows = list(db.scalars(select(PlatformAdminEvent).where(
            PlatformAdminEvent.tenant_id == tenant_id,
        )))
        assert event_rows == []


def test_deletion_removes_verified_manifest_for_empty_media_cycle(tmp_path, monkeypatch):
    engine, tenant_id, cycle_id, owner_id, storage = _closed_archive_fixture(
        tmp_path, monkeypatch, photo_count=0,
    )
    with Session(engine, expire_on_commit=False) as db:
        cycle = db.get(MediaArchiveCycle, cycle_id)
        assert cycle is not None and cycle.object_count == 0
        plan = evaluate_media_deletion_preflight(db, tenant_id=tenant_id)
        assert plan.blocker is None
        assert plan.object_count == 1  # O manifesto remoto continua no inventário.

        accepted = _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
        assert accepted["batch"]["state"] == "queued"
        assert accepted["batch"]["object_count"] == 1
        claim = _start_delete(db, tenant_id=tenant_id)
        result = execute_delete_operation(db, claim, storage=storage)
        assert result.status == "completed", result.error_code
        assert db.get(MediaArchiveCycle, cycle_id).state == "deleted"
        assert storage.objects == {}
        assert db.scalar(select(TenantClosureMediaDeletionBatch.state).where(
            TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        )) == "completed"
        assert db.scalar(select(PhotographerBusinessProfile.cpf_fingerprint).where(
            PhotographerBusinessProfile.tenant_id == tenant_id,
        )) is None
        items = list(db.scalars(select(TenantClosureMediaDeletionItem).where(
            TenantClosureMediaDeletionItem.tenant_id == tenant_id,
        )))
        assert len(items) == 1


def test_failed_remote_delete_keeps_tenant_media_and_cpf_recoverable(
    tmp_path, monkeypatch,
):
    engine, tenant_id, cycle_id, owner_id, storage = _closed_archive_fixture(
        tmp_path, monkeypatch, storage_type=NoopDeleteStorage,
    )
    with Session(engine, expire_on_commit=False) as db:
        _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
        claim = _start_delete(db, tenant_id=tenant_id)
        result = execute_delete_operation(db, claim, storage=storage)
        assert result.status == "failed"
        batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
            TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        ))
        assert batch is not None and batch.state == "attention_required"
        assert db.get(MediaArchiveCycle, cycle_id).state == "deleting"
        assert db.scalar(select(PhotographerBusinessProfile.cpf_fingerprint).where(
            PhotographerBusinessProfile.tenant_id == tenant_id,
        )) == "b" * 64


def test_ambiguous_delete_requires_owner_retry_then_resumes_idempotently(
    tmp_path, monkeypatch,
):
    engine, tenant_id, cycle_id, owner_id, storage = _closed_archive_fixture(
        tmp_path, monkeypatch, storage_type=AmbiguousDeleteStorage,
    )
    with Session(engine, expire_on_commit=False) as db:
        _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
        claim = _start_delete(db, tenant_id=tenant_id)
        result = execute_delete_operation(db, claim, storage=storage)
        assert result.status == "reconciliation_required", result.error_code
        batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
            TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        ))
        assert batch is not None and batch.state == "reconciliation_required"
        deletion_operation = db.get(MediaArchiveOperation, claim.operation_id)
        assert deletion_operation is not None
        assert deletion_operation.last_error_code == "deletion_runtimeerror"
        assert "synthetic adapter detail" not in (deletion_operation.last_error or "")
        assert "synthetic adapter detail" not in str(closure_console_payload(db, tenant_id))
        assert db.get(MediaArchiveCycle, cycle_id).state == "deleting"
        assert db.scalar(select(PhotographerBusinessProfile.cpf_fingerprint).where(
            PhotographerBusinessProfile.tenant_id == tenant_id,
        )) == "b" * 64

        retry = retry_media_deletion(
            db,
            owner_id=owner_id,
            tenant_id=tenant_id,
            confirmation=DELETION_CONFIRMATION,
        )
        assert retry["batch"]["state"] == "queued"
        retry_claim = _start_delete(db, tenant_id=tenant_id)
        resumed = execute_delete_operation(db, retry_claim, storage=storage)
        assert resumed.status == "completed"
        assert storage.objects == {}
        assert db.get(MediaArchiveCycle, cycle_id).state == "deleted"
        assert db.scalar(select(PhotographerBusinessProfile.cpf_fingerprint).where(
            PhotographerBusinessProfile.tenant_id == tenant_id,
        )) is None


def test_deletion_retry_locks_global_coordinator_before_tenant_or_batch(
    tmp_path, monkeypatch,
):
    engine, tenant_id, _cycle_id, owner_id, _storage = _closed_archive_fixture(
        tmp_path, monkeypatch,
    )
    with Session(engine, expire_on_commit=False) as db:
        _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
        batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
            TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        ))
        operation = db.scalar(select(MediaArchiveOperation).where(
            MediaArchiveOperation.tenant_id == tenant_id,
            MediaArchiveOperation.operation_type == "delete_remote",
        ))
        assert batch is not None and operation is not None
        batch.state = "attention_required"
        operation.status = "failed"
        operation.last_error_code = "synthetic_failure"
        db.commit()

        row_locks = []

        def record_row_lock(execute_state):
            statement = execute_state.statement
            if not execute_state.is_select or getattr(statement, "_for_update_arg", None) is None:
                return
            sql = str(statement).lower()
            if "media_archive_coordinator" in sql:
                row_locks.append("coordinator")
            elif "tenant_closure_media_deletion_batch" in sql:
                row_locks.append("batch")
            elif "media_archive_operation" in sql:
                row_locks.append("operation")
            elif "media_archive_cycle" in sql:
                row_locks.append("cycle")
            elif " from tenants " in sql:
                row_locks.append("tenant")

        event.listen(db, "do_orm_execute", record_row_lock)
        try:
            result = retry_media_deletion(
                db,
                owner_id=owner_id,
                tenant_id=tenant_id,
                confirmation=DELETION_CONFIRMATION,
            )
        finally:
            event.remove(db, "do_orm_execute", record_row_lock)
            db.rollback()

    assert result["batch"]["state"] == "queued"
    assert row_locks[0] == "coordinator"
    assert {"batch", "operation", "cycle"}.issubset(row_locks)


def test_content_mismatch_stops_before_remote_delete_and_keeps_cpf(
    tmp_path, monkeypatch,
):
    engine, tenant_id, _cycle_id, owner_id, storage = _closed_archive_fixture(
        tmp_path, monkeypatch, storage_type=CorruptingDeleteStorage,
    )
    with Session(engine, expire_on_commit=False) as db:
        storage.corrupt = True
        _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
        claim = _start_delete(db, tenant_id=tenant_id)
        result = execute_delete_operation(db, claim, storage=storage)
        assert result.status == "failed"
        assert result.error_code == "remote_content_unverified"
        assert storage.delete_order == []
        assert db.scalar(select(PhotographerBusinessProfile.cpf_fingerprint).where(
            PhotographerBusinessProfile.tenant_id == tenant_id,
        )) == "b" * 64


def test_batch_attention_does_not_strand_other_already_authorized_cycles(
    tmp_path, monkeypatch,
):
    engine, tenant_id, first_cycle_id, owner_id, _storage = _closed_archive_fixture(
        tmp_path, monkeypatch,
    )
    with Session(engine, expire_on_commit=False) as db:
        _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
        batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
            TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        ))
        first_item = db.scalar(select(TenantClosureMediaDeletionItem).where(
            TenantClosureMediaDeletionItem.tenant_id == tenant_id,
            TenantClosureMediaDeletionItem.batch_id == batch.id,
        ))
        first_operation = db.get(MediaArchiveOperation, first_item.operation_id)
        first_operation.status = "failed"
        first_operation.last_error_code = "synthetic_failure"
        batch.state = "attention_required"

        first_cycle = db.get(MediaArchiveCycle, first_cycle_id)
        second_cycle = MediaArchiveCycle(
            tenant_id=tenant_id,
            parent_gallery_id=first_cycle.parent_gallery_id,
            folder_id=first_cycle.folder_id,
            cycle_number=2,
            state="deleting",
            object_count=0,
            archived_at=now() - timedelta(days=4000),
        )
        db.add(second_cycle)
        db.flush()
        second_operation = MediaArchiveOperation(
            tenant_id=tenant_id,
            cycle_id=second_cycle.id,
            operation_type="delete_remote",
            status="queued",
            idempotency_key=f"tenant-media-deletion-test:{second_cycle.id}",
            actor_type="owner",
            actor_admin_id=owner_id,
            details={"deletion_batch_id": str(batch.id)},
        )
        db.add(second_operation)
        db.flush()
        db.add(TenantClosureMediaDeletionItem(
            tenant_id=tenant_id,
            batch_id=batch.id,
            cycle_id=second_cycle.id,
            operation_id=second_operation.id,
        ))
        db.add(MediaArchiveObject(
            tenant_id=tenant_id,
            cycle_id=second_cycle.id,
            source_ref="synthetic-manifest-v2",
            object_type="manifest",
            mime_type="application/json",
            size_bytes=2,
            sha256="c" * 64,
            remote_object_id="synthetic-manifest-v2",
            remote_deleted_at=now(),
        ))
        db.commit()

        claim = claim_next_operation(db)
        assert claim is not None and claim.operation_id == second_operation.id
        begin_delete_operation(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        for stage in ("manifest_verified", "objects_deleting", "manifest_deleting"):
            checkpoint_operation(
                db,
                operation_id=claim.operation_id,
                lease_token=claim.lease_token,
                stage=stage,
            )
        checkpoint_operation(
            db,
            operation_id=claim.operation_id,
            lease_token=claim.lease_token,
            stage="objects_verified",
            details_patch={
                "final_readback_verified": True,
                "verified_deleted_object_count": 1,
            },
        )
        assert complete_delete_operation(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        ) is True
        assert db.get(MediaArchiveOperation, second_operation.id).status == "completed"
        assert db.get(MediaArchiveCycle, second_cycle.id).state == "deleted"
        assert db.get(TenantClosureMediaDeletionBatch, batch.id).state == "attention_required"
        assert db.get(MediaArchiveOperation, first_operation.id).status == "failed"


def test_recovery_and_reopening_are_blocked_by_pending_or_completed_deletion(
    tmp_path, monkeypatch,
):
    engine, tenant_id, cycle_id, owner_id, storage = _closed_archive_fixture(
        tmp_path, monkeypatch,
    )
    with Session(engine, expire_on_commit=False) as db:
        _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
        status = closure_console_payload(db, tenant_id)
        assert status["reopen_blocker"] == "media_deletion_pending"
        with pytest.raises(HTTPException) as error:
            request_batch(
                db,
                owner_id=owner_id,
                tenant_id=tenant_id,
                request_id=uuid4(),
                duration_days=14,
            )
        assert error.value.status_code == 409

        claim = _start_delete(db, tenant_id=tenant_id)
        assert execute_delete_operation(db, claim, storage=storage).status == "completed"
        status = closure_console_payload(db, tenant_id)
        assert status["reopen_blocker"] == "media_permanently_deleted"
        # Mesmo uma identidade aprovada não pode recuperar mídia eliminada.
        monkeypatch.setattr("app.photographer_access_recovery.completed_closure_proof", lambda *_args: object())
        with pytest.raises(HTTPException, match="recuperação completa da mídia"):
            reopen_account(db, owner_id=owner_id, tenant_id=tenant_id, request_id=uuid4())
        with pytest.raises(HTTPException) as error:
            request_batch(
                db,
                owner_id=owner_id,
                tenant_id=tenant_id,
                request_id=uuid4(),
                duration_days=14,
            )
        assert error.value.status_code == 409
        assert db.get(MediaArchiveCycle, cycle_id).state == "deleted"
