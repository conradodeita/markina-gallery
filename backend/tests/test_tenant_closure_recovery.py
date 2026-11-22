"""Recuperação de conta fechada usa storage sintético e cobrança existente."""

import os
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    MediaArchiveCycle,
    MediaArchiveOperation,
    MediaArchiveRecoveryCreditReservation,
    MediaArchiveRecoveryPricing,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PhotographerCreditEntry,
    PhotographerTermsAcceptance,
    PlatformAdminEvent,
    Tenant,
    TenantAdmin,
    TenantClosureRecoveryBatch,
    TenantClosureRequest,
    TenantCreditWallet,
    now,
)
from app.media_archive_executor import execute_archive_operation, execute_restore_operation
from app.media_archive_staging import VolumeCapacity
from app.media_archive_worker import claim_next_operation
from app.photographer_credits import grant_credits
from app.system_monitor.models import PlatformOwner
from app.tenant_closure import ClosureInput, finalize_closure, request_closure
from app.tenant_closure_recovery import batch_payload, reopen_account, request_batch
from tests.test_media_archive_executor import InMemoryArchiveStorage, _archive_fixture
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
from tests.test_photographer_credits import create_accounts


@pytest.mark.parametrize("cover_only", [False, True])
@pytest.mark.parametrize("failure_mode", [None, "readback", "capacity"])
@pytest.mark.parametrize("reopen_after_restore", [False, True])
@pytest.mark.parametrize("credit_balance", [5, 3])
def test_closed_account_batch_restores_once_without_implicit_reopening(
    tmp_path, monkeypatch, cover_only, failure_mode, reopen_after_restore, credit_balance,
):
    engine, tenant_id, gallery_id, folder_id, original_cycle_id, _, paths = _archive_fixture(tmp_path, monkeypatch)
    staging = (tmp_path / "private-staging").resolve()
    monkeypatch.setenv("MEDIA_ARCHIVE_STAGING_ROOT", str(staging))
    storage = InMemoryArchiveStorage()
    try:
        with Session(engine, expire_on_commit=False) as db:
            owner_tenant = Tenant()
            db.add(owner_tenant)
            db.flush()
            owner = AdminUser(email="owner@synthetic.test", password_hash="synthetic", email_verified=True,
                              totp_enabled=False)
            photographer = AdminUser(email="photo@synthetic.test", password_hash="synthetic", email_verified=True,
                                     totp_enabled=False)
            owner.tenant_memberships.append(TenantAdmin(tenant_id=owner_tenant.id))
            photographer.tenant_memberships.append(TenantAdmin(tenant_id=tenant_id))
            db.add_all([owner, photographer])
            db.flush()
            db.add(PlatformOwner(singleton=1, admin_user_id=owner.id, authorization_reference="synthetic"))
            db.add_all([TenantCreditWallet(tenant_id=owner_tenant.id, mode="unmetered"),
                        TenantCreditWallet(tenant_id=tenant_id, mode="finite")])
            db.flush()
            db.add(MediaArchiveRecoveryPricing(id=1, recovery_fee_credits=2, updated_by_admin_id=owner.id))
            grant_credits(db, owner.id, tenant_id, credit_balance, "synthetic-close-grant", "synthetic")
            db.add(PhotographerTermsAcceptance(
                tenant_id=tenant_id, admin_user_id=photographer.id, terms_version="synthetic-closure",
                terms_sha256="a" * 64, terms_text="synthetic", provider_identity="synthetic",
                photographer_identity="synthetic", environment="development"))
            if cover_only:
                folder = db.get(PhotoFolder, folder_id)
                folder.purpose, folder.status = "cover_assets", "preparing"
                folder.released_at = folder.access_expires_at = None
            second_cycle_id = None
            second_source_path = None
            if not cover_only:
                instant = now()
                second_folder_id, second_cycle_id, second_operation_id, second_photo_id = (
                    uuid4(), uuid4(), uuid4(), uuid4(),
                )
                db.add(PhotoFolder(
                    id=second_folder_id, tenant_id=tenant_id, parent_gallery_id=gallery_id,
                    name="Segunda pasta sintética", purpose="content", status="released", position=2,
                    released_at=instant - timedelta(days=90), access_duration_days=30,
                    access_expires_at=instant - timedelta(days=61),
                ))
                db.flush()
                second_storage_key = (
                    f"tenants/{tenant_id}/{gallery_id}/{second_folder_id}/{second_photo_id}.jpg"
                )
                db.add(PhotoAsset(
                    id=second_photo_id, tenant_id=tenant_id, parent_gallery_id=gallery_id,
                    folder_id=second_folder_id, filename="segunda-sintetica.jpg",
                    storage_key=second_storage_key,
                ))
                second_source_path = Path(os.environ["MEDIA_SOURCE_ROOT"]).joinpath(
                    *second_storage_key.split("/"),
                )
                second_source_path.parent.mkdir(parents=True, exist_ok=True)
                second_source_path.write_bytes(b"second-synthetic-jpeg")
                db.add(MediaArchiveCycle(
                    id=second_cycle_id, tenant_id=tenant_id, parent_gallery_id=gallery_id,
                    folder_id=second_folder_id, cycle_number=1, state="local",
                ))
                db.add(MediaArchiveOperation(
                    id=second_operation_id, tenant_id=tenant_id, cycle_id=second_cycle_id,
                    operation_type="archive", status="queued",
                    idempotency_key=f"closure-second-archive-{second_operation_id}",
                    actor_type="system", created_at=instant,
                ))
            db.commit()
            request_closure(db, SimpleNamespace(role="admin", subject_id=photographer.id, tenant_id=tenant_id),
                            ClosureInput(request_id=uuid4(), confirm_closure=True,
                                         acknowledge_remaining_balance=True, expected_balance=credit_balance,
                                         terms_version="synthetic-closure", terms_sha256="a" * 64))
            db.commit()
            archive = claim_next_operation(db)
            assert execute_archive_operation(db, archive, storage=storage).status == "completed"
            if not cover_only:
                second_archive = claim_next_operation(db)
                assert second_archive.operation_id == second_operation_id
                assert execute_archive_operation(db, second_archive, storage=storage).status == "completed"
            first_finalization = finalize_closure(db, tenant_id)
            db.commit()
            assert first_finalization["ready"] is False
            assert db.get(Tenant, tenant_id, populate_existing=True).lifecycle == "closing"
            assert finalize_closure(db, tenant_id)["ready"]
            db.commit()
            with pytest.raises(HTTPException):
                request_batch(db, owner_id=photographer.id, tenant_id=tenant_id, request_id=uuid4(), duration_days=7)
            key = uuid4()
            if not cover_only and credit_balance < 4:
                with pytest.raises(HTTPException, match="crédito"):
                    request_batch(db, owner_id=owner.id, tenant_id=tenant_id,
                                  request_id=key, duration_days=7)
                db.rollback()
                assert db.scalar(select(func.count()).select_from(TenantClosureRecoveryBatch).where(
                    TenantClosureRecoveryBatch.tenant_id == tenant_id,
                )) == 0
                assert db.scalar(select(func.count()).select_from(MediaArchiveRecoveryCreditReservation).where(
                    MediaArchiveRecoveryCreditReservation.tenant_id == tenant_id,
                )) == 0
                assert db.scalar(select(func.count()).select_from(MediaArchiveOperation).where(
                    MediaArchiveOperation.tenant_id == tenant_id,
                    MediaArchiveOperation.operation_type == "restore",
                )) == 0
                grant_credits(db, owner.id, tenant_id, 1, "synthetic-after-insufficient-balance", "synthetic")
                db.commit()
            batch = request_batch(db, owner_id=owner.id, tenant_id=tenant_id, request_id=key, duration_days=7)
            db.commit()
            assert len(batch["operations"]) == (1 if cover_only else 2)
            assert request_batch(db, owner_id=owner.id, tenant_id=tenant_id,
                                 request_id=key, duration_days=7)["replayed"]
            db.commit()
            other_tenant = Tenant()
            db.add(other_tenant)
            db.flush()
            other_gallery = ParentGallery(tenant_id=other_tenant.id, name="Outra conta sintética")
            db.add(other_gallery)
            db.flush()
            other_folder = PhotoFolder(
                tenant_id=other_tenant.id, parent_gallery_id=other_gallery.id,
                name="Fila de arquivo sintética", purpose="content", status="preparing",
            )
            db.add(other_folder)
            db.flush()
            other_cycle = MediaArchiveCycle(
                tenant_id=other_tenant.id, parent_gallery_id=other_gallery.id,
                folder_id=other_folder.id, cycle_number=1, state="local",
            )
            db.add(other_cycle)
            db.flush()
            db.add(MediaArchiveOperation(
                tenant_id=other_tenant.id, cycle_id=other_cycle.id,
                operation_type="archive", status="queued",
                idempotency_key=f"unrelated-archive-{uuid4()}", actor_type="system",
            ))
            db.commit()
            with pytest.raises(HTTPException):
                reopen_account(db, owner_id=photographer.id, tenant_id=tenant_id, request_id=uuid4())
            with pytest.raises(HTTPException, match="recuperação completa"):
                reopen_account(db, owner_id=owner.id, tenant_id=tenant_id, request_id=uuid4())
            db.rollback()
            from app.acervo_context import require_active_owner
            for index in range(len(batch["operations"])):
                claim = claim_next_operation(db)
                assert claim is not None
                assert db.get(MediaArchiveOperation, claim.operation_id).operation_type == "restore"
                if index == 0:
                    db.info["closure_archive_execution"] = (tenant_id, claim.operation_id, "invalid-lease")
                    with pytest.raises(HTTPException):
                        require_active_owner(db, tenant_id)
                last_operation_fails = failure_mode is not None and index == len(batch["operations"]) - 1
                storage.corrupt_readback = failure_mode == "readback" and last_operation_fails
                capacity_provider = lambda _, failed=last_operation_fails: VolumeCapacity(
                    "a" * 64, 100 * 1024**3,
                    0 if failure_mode == "capacity" and failed else 90 * 1024**3,
                )
                result = execute_restore_operation(
                    db, claim, storage=storage, staging_root=staging,
                    capacity_provider=capacity_provider,
                )
                if last_operation_fails:
                    from app.media_archive_billing import request_recovery
                    assert result.status == "failed", result
                    if failure_mode == "capacity":
                        assert db.get(MediaArchiveOperation, claim.operation_id).last_error_code == "insufficient_space"
                    recovery_batch = db.get(TenantClosureRecoveryBatch, UUID(batch["batch_id"]))
                    assert batch_payload(db, recovery_batch)["state"] == "attention_required"
                    assert db.get(Tenant, tenant_id, populate_existing=True).lifecycle == "closed"
                    failed_operation = db.get(MediaArchiveOperation, claim.operation_id)
                    if failed_operation.cycle_id == original_cycle_id:
                        failed_paths = paths
                        already_restored = [second_source_path] if second_source_path else []
                    else:
                        failed_paths = [second_source_path]
                        already_restored = paths
                    assert all(not path.exists() for path in failed_paths)
                    assert all(path.is_file() for path in already_restored)
                    assert db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
                        PhotographerCreditEntry.tenant_id == tenant_id,
                        PhotographerCreditEntry.entry_type == "archive_recovery")) == (0 if cover_only else 1)
                    retry = request_recovery(
                        db, tenant_id=tenant_id, actor_admin_id=owner.id,
                        cycle_id=failed_operation.cycle_id, duration_days=7,
                        idempotency_key="synthetic-closure-retry",
                        retry_of_operation_id=claim.operation_id,
                    )
                    db.commit()
                    storage.corrupt_readback = False
                    retry_claim = claim_next_operation(db)
                    assert retry_claim.operation_id == UUID(retry["operation_id"])
                    result = execute_restore_operation(
                        db, retry_claim, storage=storage, staging_root=staging,
                        capacity_provider=lambda _: VolumeCapacity("a" * 64, 100 * 1024**3, 90 * 1024**3),
                    )
                assert result.status == "completed", result
            assert db.get(Tenant, tenant_id, populate_existing=True).lifecycle == "closed"
            assert all(path.is_file() for path in paths)
            if second_source_path is not None:
                assert second_source_path.is_file()
            assert all(path.is_file() for path in paths)
            with pytest.raises(HTTPException):
                require_active_owner(db, tenant_id)
            charges = db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
                PhotographerCreditEntry.tenant_id == tenant_id,
                PhotographerCreditEntry.entry_type == "archive_recovery"))
            assert charges == (0 if cover_only else 2)
            if reopen_after_restore:
                tenant = db.get(Tenant, tenant_id, populate_existing=True)
                tenant.status = "suspended"
                db.commit()
                request_id = uuid4()
                reopened = reopen_account(db, owner_id=owner.id, tenant_id=tenant_id,
                                          request_id=request_id)
                db.commit()
                assert reopened["lifecycle"] == "open"
                assert reopened["availability"] == "suspended"
                assert tenant.lifecycle == "open" and tenant.status == "suspended"
                closure = db.scalar(select(TenantClosureRequest).where(
                    TenantClosureRequest.tenant_id == tenant_id,
                ).order_by(TenantClosureRequest.closed_at.desc()).limit(1))
                event = db.scalar(select(PlatformAdminEvent).where(
                    PlatformAdminEvent.request_id == request_id,
                ))
                assert closure.state == "reopened" and closure.reopened_at is not None
                assert event.action == "tenant.reopened" and event.result == "success"
    finally:
        engine.dispose()


def test_reopening_after_ten_years_requires_recovery_identity(client_db):
    _owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    closed_at = now().replace(year=now().year - 10)
    tenant.lifecycle = "closed"
    client_db.add(TenantClosureRequest(
        tenant_id=tenant.id,
        request_id=uuid4(),
        requested_by=photographer.id,
        state="closed",
        requested_at=closed_at,
        closed_at=closed_at,
        terms_version="synthetic-closure",
        terms_sha256="a" * 64,
        balance_snapshot=0,
        balance_acknowledged=True,
    ))
    client_db.commit()

    with pytest.raises(HTTPException, match="confirmação de identidade"):
        reopen_account(client_db, owner_id=owner.id, tenant_id=tenant.id, request_id=uuid4())

    assert client_db.get(Tenant, tenant.id, populate_existing=True).lifecycle == "closed"
    assert client_db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.tenant_id == tenant.id,
        PlatformAdminEvent.action == "tenant.reopened",
    )) is None
