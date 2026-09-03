import os
import sys
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from subprocess import run
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, inspect, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    AuditEvent,
    AuthChallenge,
    Base,
    Client,
    ClientPhone,
    CommercialHistoryMedia,
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    DerivedGalleryPhotoOrigin,
    GalleryAccess,
    GalleryAccessCapability,
    GalleryLifecycleOperation,
    MediaDerivative,
    MediaJob,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    PhotoAsset,
    PhotoComment,
    PhotoFavorite,
    PhotoFolder,
    PhotoSelection,
    PhotoView,
    PixCheckoutSettings,
    PriceRule,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    engine,
    now,
    password_hasher,
    token_hash,
)
from app.commercial_history import (
    CommercialHistoryGap,
    backfill_commercial_snapshots,
    materialize_commercial_history,
)
from app.commercial_removal import (
    CommercialRemovalBlocked,
    apply_commercial_removal_policy,
    commercial_removal_orders_query,
)
from app.commercial_retention import (
    CommercialPiiMinimizationNotAuthorized,
    CommercialRetentionConfigurationError,
    apply_commercial_media_retention,
    commercial_retention_policy,
    minimize_client_commercial_pii,
)
from app.gallery_access import (
    issue_gallery_capability,
    resolve_gallery_capability,
    revoke_gallery_capability,
    rotate_gallery_capability,
)
from app.gallery_cleanup import (
    remove_operational_records,
    remove_operational_storage,
)
from app.gallery_lifecycle import (
    InvalidLifecycleTransition,
    gallery_operational_storage_manifest,
    retry_failed_operation,
    transition_operation,
)
from app.historical_media import (
    HistoricalMediaConflict,
    prepare_confirmed_historical_media,
)
from app.main import app, derived_gallery_for_client
from app.private_derivation import (
    FacialDerivationUnavailable,
    derive_approved_facial_result,
    ensure_private_photo_reference,
)
from app.worker import process_next_gallery_lifecycle_operation


@pytest.fixture(autouse=True)
def clean_database():
    # Migration tests run Alembic in subprocesses against SQLite. Discard pooled
    # connections before rebuilding the schema so inspectors never observe a
    # stale sqlite_schema snapshot from an earlier process.
    engine.dispose()
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(connection)
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
    Base.metadata.create_all(engine)
    yield


def create_private_gallery_fixture(
    db: Session,
    *,
    label: str,
    phones: tuple[str, ...],
    with_memberships: bool,
) -> tuple[ParentGallery, DerivedGallery, list[Client]]:
    """Constrói tanto o estado legado quanto uma privada compartilhada."""

    clients = [
        Client(full_name=f"{label} cliente {index}", phone_e164=phone)
        for index, phone in enumerate(phones, start=1)
    ]
    parent = ParentGallery(name=f"{label} pública")
    db.add_all([*clients, parent])
    db.flush()
    private = DerivedGallery(
        parent_gallery_id=parent.id,
        client_id=clients[0].id,
        name=f"{label} privada",
    )
    db.add(private)
    db.flush()
    if with_memberships:
        db.add_all(
            DerivedGalleryMembership(
                derived_gallery_id=private.id,
                parent_gallery_id=parent.id,
                client_id=client.id,
            )
            for client in clients
        )
        db.flush()
    return parent, private, clients


def test_lifecycle_operation_enforces_idempotency_and_valid_target() -> None:
    parent_id = uuid4()
    actor_id = uuid4()
    with SessionLocal() as db:
        db.add(
            GalleryLifecycleOperation(
                operation_type="delete_parent_gallery",
                target_parent_gallery_id=parent_id,
                actor_admin_id=actor_id,
                idempotency_key="delete-parent-0001",
                manifest={},
            )
        )
        db.commit()
        db.add(
            GalleryLifecycleOperation(
                operation_type="delete_parent_gallery",
                target_parent_gallery_id=parent_id,
                actor_admin_id=actor_id,
                idempotency_key="delete-parent-0001",
                manifest={},
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()

    with SessionLocal() as db:
        db.add(
            GalleryLifecycleOperation(
                operation_type="unlink_client",
                target_parent_gallery_id=parent_id,
                target_client_id=None,
                actor_admin_id=actor_id,
                idempotency_key="unlink-invalid-0001",
                manifest={},
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_lifecycle_operation_accepts_forward_transitions_and_rejects_jumps() -> None:
    operation = GalleryLifecycleOperation(
        operation_type="delete_parent_gallery",
        target_parent_gallery_id=uuid4(),
        actor_admin_id=uuid4(),
        idempotency_key="transition-0001",
        manifest={},
        status="queued",
    )
    transition_operation(operation, "preparing_history")
    assert operation.status == "preparing_history"
    with pytest.raises(InvalidLifecycleTransition):
        transition_operation(operation, "completed")
    transition_operation(operation, "removing_storage")
    assert operation.destructive_started_at is not None
    transition_operation(operation, "removing_records")
    transition_operation(operation, "completed")
    assert operation.completed_at is not None
    with pytest.raises(InvalidLifecycleTransition):
        transition_operation(operation, "queued")


@pytest.mark.parametrize(
    "failed_stage",
    ["preparing_history", "removing_storage", "removing_records"],
)
def test_lifecycle_worker_resumes_after_failure_in_each_stage(
    failed_stage: str,
) -> None:
    with SessionLocal() as db:
        operation = GalleryLifecycleOperation(
            operation_type="delete_parent_gallery",
            target_parent_gallery_id=uuid4(),
            actor_admin_id=uuid4(),
            idempotency_key=f"resume-{failed_stage}",
            manifest={},
        )
        db.add(operation)
        db.commit()
        operation_id = operation.id

    calls = {
        stage: 0
        for stage in (
            "preparing_history",
            "removing_storage",
            "removing_records",
        )
    }

    def handler(stage: str):
        def execute(_db, _operation) -> None:
            calls[stage] += 1
            if stage == failed_stage and calls[stage] == 1:
                raise RuntimeError("segredo-que-nao-pode-vazar")

        return execute

    handlers = {stage: handler(stage) for stage in calls}
    assert process_next_gallery_lifecycle_operation(handlers=handlers)
    with SessionLocal() as db:
        failed = db.get(GalleryLifecycleOperation, operation_id)
        assert failed.status == "failed"
        assert failed.manifest["failed_step"] == failed_stage
        assert failed.lease_token is None
        assert failed.lease_expires_at is None
        assert "segredo" not in failed.last_error
        retry_failed_operation(db, failed)
        db.commit()

    assert process_next_gallery_lifecycle_operation(handlers=handlers)
    with SessionLocal() as db:
        completed = db.get(GalleryLifecycleOperation, operation_id)
        assert completed.status == "completed"
        assert completed.attempts == 2
        assert completed.manifest["completed_steps"] == [
            "preparing_history",
            "removing_storage",
            "removing_records",
        ]
        assert "failed_step" not in completed.manifest
        assert completed.lease_token is None
        assert completed.completed_at is not None
        assert completed.destructive_started_at is not None
    expected_calls = {stage: 1 for stage in calls}
    expected_calls[failed_stage] = 2
    assert calls == expected_calls


def test_parent_gallery_deletion_endpoint_is_idempotent_and_returns_inventory() -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Cliente do inventário", phone_e164="+5511999999830")
        parent = ParentGallery(name="Galeria pública com conteúdo")
        db.add_all([owner, parent])
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote principal", status="released")
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Galeria privada da cliente",
        )
        registration = ParentGalleryRegistration(
            parent_gallery_id=parent.id, client_id=owner.id, status="active"
        )
        db.add_all([folder, private, registration])
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="inventario.jpg",
            storage_key="inventario/original.jpg",
        )
        db.add(photo)
        db.flush()
        db.add_all(
            [
                DerivedGalleryMembership(
                    derived_gallery_id=private.id,
                    parent_gallery_id=parent.id,
                    client_id=owner.id,
                ),
                DerivedGalleryPhoto(
                    derived_gallery_id=private.id,
                    photo_asset_id=photo.id,
                    origin="admin",
                ),
                PhotoSelection(
                    derived_gallery_id=private.id,
                    photo_asset_id=photo.id,
                    client_id=owner.id,
                ),
            ]
        )
        order = SaleOrder(
            derived_gallery_id=private.id,
            client_id=owner.id,
            payment_status="confirmed",
            total_cents=1500,
            confirmed_at=now(),
        )
        db.add(order)
        db.flush()
        item = SaleOrderItem(
            sale_order_id=order.id,
            photo_asset_id=photo.id,
            filename_snapshot=photo.filename,
            unit_price_cents=1500,
        )
        db.add(item)
        db.flush()
        db.add(
            CommercialHistoryMedia(
                sale_order_item_id=item.id,
                preview_storage_key=f"items/{item.id}/preview.jpg",
                delivery_reference="provider://delivery/reference",
                checksum_sha256="b" * 64,
                media_type="image/jpeg",
                size_bytes=128,
                status="ready",
            )
        )
        db.commit()
        parent_id = parent.id

    with TestClient(app) as anonymous:
        assert (
            anonymous.get(f"/admin/parent-galleries/{parent_id}/deletion-inventory").status_code
            == 403
        )
        assert (
            anonymous.delete(
                f"/admin/parent-galleries/{parent_id}",
                headers={"Idempotency-Key": "delete-inventory-0001"},
            ).status_code
            == 403
        )

    with TestClient(app) as client:
        authenticate_admin(client)
        preview = client.get(f"/admin/parent-galleries/{parent_id}/deletion-inventory")
        assert preview.status_code == 200
        assert preview.json()["operation_type"] == "delete_parent_gallery"
        assert preview.json()["target"] == {
            "id": str(parent_id),
            "name": "Galeria pública com conteúdo",
        }
        assert preview.json()["request"] == {
            "method": "DELETE",
            "url": f"/admin/parent-galleries/{parent_id}",
            "requires_idempotency_key": True,
            "asynchronous": True,
        }
        assert preview.json()["consequences"] == {
            "public_gallery_removed": True,
            "public_access_revoked": True,
            "private_galleries_preserved": True,
            "private_referenced_photos_preserved": True,
            "clients_preserved": True,
            "commercial_history_preserved": True,
            "restoration_available_after_start": False,
        }
        assert client.delete(f"/admin/parent-galleries/{parent_id}").status_code == 422
        first = client.delete(
            f"/admin/parent-galleries/{parent_id}",
            headers={"Idempotency-Key": "delete-inventory-0001"},
        )
        assert first.status_code == 202
        payload = first.json()
        assert payload["status"] == "queued"
        assert payload["progress"] == {
            "label": "Na fila",
            "percent": 0,
            "completed_steps": 0,
            "total_steps": 3,
            "failed_step": None,
        }
        assert payload["actions"] == {
            "can_cancel": True,
            "can_retry": False,
            "should_poll": True,
            "poll_after_ms": 1000,
        }
        assert payload["inventory"] == {
            "remove": {
                "folders": 0,
                "photos": 0,
                "media_derivatives": 0,
                "registrations": 1,
                "access_capabilities": 0,
            },
            "preserve": {
                "clients": 1,
                "memberships": 1,
                "private_galleries": 1,
                "photos_referenced_by_private": 1,
                "folders_with_private_photos": 1,
                "available_references": 1,
                "selections": 1,
                "favorites": 0,
                "comments": 0,
                "views": 0,
                "orders": 1,
                "orders_by_status": {
                    "pending": 0,
                    "confirmed": 1,
                    "cancelled": 0,
                },
                "order_items": 1,
                "historical_media": 1,
            },
        }
        assert preview.json()["inventory"] == payload["inventory"]
        repeated = client.delete(
            f"/admin/parent-galleries/{parent_id}",
            headers={"Idempotency-Key": "delete-inventory-0001"},
        )
        assert repeated.status_code == 202
        assert repeated.json()["operation_id"] == payload["operation_id"]
        assert (
            client.delete(
                f"/admin/parent-galleries/{parent_id}",
                headers={"Idempotency-Key": "delete-inventory-other"},
            ).status_code
            == 409
        )
        progress = client.get(payload["status_url"])
        assert progress.status_code == 200
        assert progress.json()["inventory"] == payload["inventory"]
        assert progress.json()["actions"]["should_poll"] is True

    with SessionLocal() as db:
        assert db.get(ParentGallery, parent_id).lifecycle_status == "deleting"
        operation = db.get(GalleryLifecycleOperation, UUID(payload["operation_id"]))
        assert operation.actor_admin_id is not None
        assert (
            db.scalar(
                select(func.count()).where(
                    AuditEvent.event == "parent_gallery.deletion_queued",
                    AuditEvent.subject == str(operation.id),
                )
            )
            == 1
        )


def test_lifecycle_cancellation_is_safe_only_before_physical_removal() -> None:
    with SessionLocal() as db:
        cancellable = ParentGallery(name="Galeria cancelável")
        irreversible = ParentGallery(name="Galeria irreversível", lifecycle_status="deleting")
        db.add_all([cancellable, irreversible])
        db.flush()
        started = GalleryLifecycleOperation(
            operation_type="delete_parent_gallery",
            target_parent_gallery_id=irreversible.id,
            actor_admin_id=uuid4(),
            idempotency_key="already-physical-removal",
            status="removing_storage",
            manifest={"operational_storage": {"sources": [], "derivatives": []}},
            destructive_started_at=now(),
        )
        db.add(started)
        db.commit()
        cancellable_id, irreversible_id, started_id = (
            cancellable.id,
            irreversible.id,
            started.id,
        )

    with TestClient(app) as client:
        authenticate_admin(client)
        queued = client.delete(
            f"/admin/parent-galleries/{cancellable_id}",
            headers={"Idempotency-Key": "cancel-before-removal"},
        )
        assert queued.status_code == 202
        operation_id = queued.json()["operation_id"]
        cancelled = client.post(f"/admin/gallery-lifecycle-operations/{operation_id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        repeated = client.post(f"/admin/gallery-lifecycle-operations/{operation_id}/cancel")
        assert repeated.status_code == 200
        assert repeated.json()["operation_id"] == operation_id

        refused = client.post(f"/admin/gallery-lifecycle-operations/{started_id}/cancel")
        assert refused.status_code == 409
        assert refused.json()["detail"] == (
            "A remoção física já começou e não pode ser cancelada nem restaurada."
        )
        assert "storage" not in refused.text.lower()

    with SessionLocal() as db:
        assert db.get(ParentGallery, cancellable_id).lifecycle_status == "active"
        assert db.get(ParentGallery, irreversible_id).lifecycle_status == "deleting"
        assert db.get(GalleryLifecycleOperation, started_id).status == ("removing_storage")
        assert (
            db.scalar(select(func.count()).where(AuditEvent.event == "gallery_lifecycle.cancelled"))
            == 1
        )


def test_lifecycle_contract_exposes_failure_progress_and_retry_action() -> None:
    with SessionLocal() as db:
        parent = ParentGallery(name="Galeria com retomada", lifecycle_status="deleting")
        db.add(parent)
        db.flush()
        operation = GalleryLifecycleOperation(
            operation_type="delete_parent_gallery",
            target_parent_gallery_id=parent.id,
            actor_admin_id=uuid4(),
            idempotency_key="retry-contract-0001",
            status="failed",
            manifest={
                "completed_steps": ["preparing_history"],
                "failed_step": "removing_storage",
                "inventory": {"remove": {}, "preserve": {}},
            },
            last_error="Falha interna na etapa removing_storage.",
            destructive_started_at=now(),
        )
        db.add(operation)
        db.commit()
        operation_id = operation.id

    with TestClient(app) as client:
        authenticate_admin(client)
        status_response = client.get(f"/admin/gallery-lifecycle-operations/{operation_id}")
        assert status_response.status_code == 200
        assert status_response.json()["progress"] == {
            "label": "Falhou",
            "percent": 25,
            "completed_steps": 1,
            "total_steps": 3,
            "failed_step": "removing_storage",
        }
        assert status_response.json()["actions"] == {
            "can_cancel": False,
            "can_retry": True,
            "should_poll": False,
            "poll_after_ms": None,
        }

        retried = client.post(f"/admin/gallery-lifecycle-operations/{operation_id}/retry")
        assert retried.status_code == 200
        assert retried.json()["status"] == "queued"
        assert retried.json()["completed_steps"] == ["preparing_history"]
        assert retried.json()["actions"]["can_retry"] is False
        assert retried.json()["actions"]["should_poll"] is True
        assert (
            client.post(f"/admin/gallery-lifecycle-operations/{operation_id}/retry").status_code
            == 409
        )


def test_record_cleanup_removes_public_origin_and_preserves_private_graph() -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Cliente preservada", phone_e164="+5511999999840")
        parent = ParentGallery(name="Galeria pública descartável")
        db.add_all([owner, parent])
        db.flush()
        folder = PhotoFolder(
            parent_gallery_id=parent.id, name="Lote descartável", status="released"
        )
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada descartável",
        )
        db.add_all([folder, private])
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="comprada.jpg",
            storage_key="cleanup/comprada.jpg",
        )
        db.add(photo)
        db.flush()
        unused_photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="sem-referencia.jpg",
            storage_key="cleanup/sem-referencia.jpg",
        )
        db.add(unused_photo)
        db.flush()
        parent.cover_photo_id = photo.id
        db.add_all(
            [
                ParentGalleryRegistration(
                    parent_gallery_id=parent.id,
                    client_id=owner.id,
                    status="active",
                ),
                DerivedGalleryPhoto(
                    derived_gallery_id=private.id,
                    photo_asset_id=photo.id,
                    origin="admin",
                ),
                PhotoSelection(
                    derived_gallery_id=private.id,
                    photo_asset_id=photo.id,
                    client_id=owner.id,
                ),
                PhotoFavorite(
                    derived_gallery_id=private.id,
                    photo_asset_id=photo.id,
                    client_id=owner.id,
                ),
                PhotoView(
                    derived_gallery_id=private.id,
                    photo_asset_id=photo.id,
                    client_id=owner.id,
                ),
                PhotoComment(
                    derived_gallery_id=private.id,
                    photo_asset_id=photo.id,
                    client_id=owner.id,
                    body="Comentário operacional",
                ),
                PriceRule(
                    parent_gallery_id=parent.id,
                    minimum_quantity=1,
                    maximum_quantity=None,
                    unit_price_cents=2100,
                ),
                PixCheckoutSettings(
                    parent_gallery_id=parent.id,
                    copy_paste="pix-operacional",
                ),
                GalleryAccess(client_id=owner.id, gallery_id=private.id),
                GalleryAccessCapability(
                    parent_gallery_id=parent.id,
                    derived_gallery_id=private.id,
                    client_id=owner.id,
                    scope="private_invite",
                    token_hash="c" * 64,
                ),
                MediaDerivative(
                    photo_asset_id=photo.id,
                    variant="client_preview",
                    relative_path=f"{photo.id}/client_preview.jpg",
                    status="ready",
                ),
                MediaJob(photo_asset_id=photo.id, kind="generate_derivatives"),
                MediaDerivative(
                    photo_asset_id=unused_photo.id,
                    variant="client_preview",
                    relative_path=f"{unused_photo.id}/client_preview.jpg",
                    status="ready",
                ),
                MediaJob(
                    photo_asset_id=unused_photo.id,
                    kind="generate_derivatives",
                ),
                AuthChallenge(
                    kind="client_otp",
                    subject=owner.phone_e164,
                    secret_hash="d" * 64,
                    expires_at=now() + timedelta(minutes=10),
                    parent_gallery_id=parent.id,
                ),
            ]
        )
        order = SaleOrder(
            derived_gallery_id=private.id,
            client_id=owner.id,
            payment_status="confirmed",
            total_cents=2100,
            confirmed_at=now(),
        )
        db.add(order)
        db.flush()
        item = SaleOrderItem(
            sale_order_id=order.id,
            photo_asset_id=photo.id,
            filename_snapshot=photo.filename,
            unit_price_cents=2100,
        )
        db.add(item)
        db.flush()
        db.add(
            CommercialHistoryMedia(
                sale_order_item_id=item.id,
                preview_storage_key=f"items/{item.id}/preview.jpg",
                delivery_reference="provider://entrega/preservada",
                checksum_sha256="e" * 64,
                media_type="image/jpeg",
                size_bytes=100,
                status="ready",
            )
        )
        operation = GalleryLifecycleOperation(
            operation_type="delete_parent_gallery",
            target_parent_gallery_id=parent.id,
            actor_admin_id=uuid4(),
            idempotency_key="complete-record-cleanup",
            status="removing_records",
            manifest={},
        )
        db.add(operation)
        db.commit()
        parent_id, private_id, folder_id, photo_id, unused_photo_id = (
            parent.id,
            private.id,
            folder.id,
            photo.id,
            unused_photo.id,
        )
        owner_id, order_id, item_id, operation_id = (
            owner.id,
            order.id,
            item.id,
            operation.id,
        )

    with SessionLocal() as db:
        operation = db.get(GalleryLifecycleOperation, operation_id)
        remove_operational_records(db, operation)
        db.commit()

    with SessionLocal() as db:
        retained_parent = db.get(ParentGallery, parent_id)
        assert retained_parent is not None
        assert retained_parent.lifecycle_status == "deleted"
        assert retained_parent.active is False
        assert retained_parent.cover_photo_id is None
        assert db.get(DerivedGallery, private_id) is not None
        assert db.get(PhotoFolder, folder_id) is not None
        assert db.get(PhotoAsset, photo_id) is not None
        assert db.get(PhotoAsset, unused_photo_id) is None
        for model in (
            DerivedGalleryPhoto,
            PhotoSelection,
            PhotoFavorite,
            PhotoView,
            PhotoComment,
            PriceRule,
            PixCheckoutSettings,
            GalleryAccess,
            MediaDerivative,
            MediaJob,
        ):
            assert db.scalar(select(func.count()).select_from(model)) == 1
        assert db.scalar(select(func.count()).select_from(GalleryAccessCapability)) == 0
        assert db.scalar(select(func.count()).select_from(ParentGalleryRegistration)) == 0
        assert db.scalar(select(func.count()).select_from(AuthChallenge)) == 0
        assert db.get(Client, owner_id) is not None
        preserved_order = db.get(SaleOrder, order_id)
        preserved_item = db.get(SaleOrderItem, item_id)
        assert preserved_order.derived_gallery_id == private_id
        assert preserved_order.total_cents == 2100
        assert preserved_order.parent_gallery_name_snapshot == ("Galeria pública descartável")
        assert preserved_item.photo_asset_id == photo_id
        assert preserved_item.filename_snapshot == "comprada.jpg"
        assert db.scalar(select(func.count()).select_from(CommercialHistoryMedia)) == 1
        operation = db.get(GalleryLifecycleOperation, operation_id)
        assert operation.manifest["removed_records"]["public_origins"] == 1
        assert operation.manifest["removed_records"]["photos"] == 1
        assert operation.manifest["removed_records"]["preserved_private_galleries"] == 1
        assert operation.manifest["removed_records"]["preserved_private_photos"] == 1
        assert (
            db.scalar(
                select(func.count()).where(
                    AuditEvent.event == "parent_gallery.operational_records_removed"
                )
            )
            == 1
        )


def test_storage_cleanup_uses_manifest_and_retries_partial_failure_without_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    derivative_root = tmp_path / "derivatives"
    history_root = tmp_path / "history"
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivative_root))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))
    with SessionLocal() as db:
        parent = ParentGallery(name="Galeria para limpeza física")
        db.add(parent)
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote")
        db.add(folder)
        db.flush()
        first = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="primeira.jpg",
            storage_key="evento/primeira.jpg",
        )
        second = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="segunda.jpg",
            storage_key="evento/segunda.jpg",
        )
        db.add_all([first, second])
        db.flush()
        db.add_all(
            [
                MediaDerivative(
                    photo_asset_id=first.id,
                    variant="client_preview",
                    relative_path=f"{first.id}/client_preview.jpg",
                    status="ready",
                ),
                MediaDerivative(
                    photo_asset_id=second.id,
                    variant="client_preview",
                    relative_path=f"{second.id}/client_preview.jpg",
                    status="ready",
                ),
            ]
        )
        db.flush()
        storage_manifest = gallery_operational_storage_manifest(db, parent.id)
        operation = GalleryLifecycleOperation(
            operation_type="delete_parent_gallery",
            target_parent_gallery_id=parent.id,
            actor_admin_id=uuid4(),
            idempotency_key="partial-storage-cleanup",
            status="removing_storage",
            manifest={"operational_storage": storage_manifest},
        )
        db.add(operation)
        db.commit()
        operation_id = operation.id

    operational_paths = [
        source_root / "evento/primeira.jpg",
        source_root / "evento/segunda.jpg",
        derivative_root / f"{first.id}/client_preview.jpg",
    ]
    for index, path in enumerate(operational_paths):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"operacional-{index}".encode())
    # O segundo derivado existe no manifesto, mas já sumiu antes do worker.
    expected_missing = derivative_root / f"{second.id}/client_preview.jpg"
    assert not expected_missing.exists()
    historical = history_root / f"items/{uuid4()}/preview.jpg"
    historical.parent.mkdir(parents=True, exist_ok=True)
    historical.write_bytes(b"historico-preservado")

    original_unlink = Path.unlink
    calls = 0

    def fail_second_unlink(path: Path, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("falha física injetada")
        return original_unlink(path, *args, **kwargs)

    with SessionLocal() as db:
        operation = db.get(GalleryLifecycleOperation, operation_id)
        monkeypatch.setattr(Path, "unlink", fail_second_unlink)
        with pytest.raises(OSError, match="falha física injetada"):
            remove_operational_storage(db, operation)
        db.rollback()

    monkeypatch.setattr(Path, "unlink", original_unlink)
    with SessionLocal() as db:
        operation = db.get(GalleryLifecycleOperation, operation_id)
        remove_operational_storage(db, operation)
        db.commit()
        cleanup = operation.manifest["storage_cleanup"]
        assert cleanup["expected_files"] == 4
        assert cleanup["removed_files"] == 2
        assert cleanup["missing_files"] == 2
    assert not any(path.exists() for path in operational_paths)
    assert historical.read_bytes() == b"historico-preservado"


def test_public_deletion_keeps_one_private_photo_copy_and_private_viewing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "retained-source"
    derivative_root = tmp_path / "retained-derivatives"
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivative_root))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(tmp_path / "retained-history"))
    owner_phone = "+5511999999849"
    with SessionLocal() as db:
        owner = Client(full_name="Cliente com privada preservada", phone_e164=owner_phone)
        parent = ParentGallery(name="Origem removível", access_mode="standard")
        db.add_all([owner, parent])
        db.flush()
        folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Lote compartilhado",
            status="released",
            released_at=now(),
        )
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada que permanece",
        )
        registration = ParentGalleryRegistration(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            status="active",
        )
        db.add_all([folder, private, registration])
        db.flush()
        retained = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="privada.jpg",
            storage_key="evento/privada.jpg",
        )
        removable = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="somente-publica.jpg",
            storage_key="evento/somente-publica.jpg",
        )
        db.add_all([retained, removable])
        db.flush()
        retained_derivative = f"{retained.id}/client_preview.jpg"
        removable_derivative = f"{removable.id}/client_preview.jpg"
        db.add_all(
            [
                DerivedGalleryPhoto(
                    derived_gallery_id=private.id,
                    photo_asset_id=retained.id,
                    origin="client",
                ),
                MediaDerivative(
                    photo_asset_id=retained.id,
                    variant="client_preview",
                    relative_path=retained_derivative,
                    status="ready",
                ),
                MediaDerivative(
                    photo_asset_id=removable.id,
                    variant="client_preview",
                    relative_path=removable_derivative,
                    status="ready",
                ),
            ]
        )
        db.commit()
        parent_id = parent.id
        private_id = private.id
        retained_id = retained.id
        removable_id = removable.id

    retained_source = source_root / "evento/privada.jpg"
    removable_source = source_root / "evento/somente-publica.jpg"
    retained_preview = derivative_root / retained_derivative
    removable_preview = derivative_root / removable_derivative
    for path, content in (
        (retained_source, b"original-privada"),
        (removable_source, b"original-publica"),
        (retained_preview, b"preview-privada-protegida"),
        (removable_preview, b"preview-publica"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    with TestClient(app) as admin:
        authenticate_admin(admin)
        response = admin.delete(
            f"/admin/parent-galleries/{parent_id}",
            headers={"Idempotency-Key": "retain-private-photo-0001"},
        )
        assert response.status_code == 202
        inventory = response.json()["inventory"]
        assert inventory["remove"]["photos"] == 1
        assert inventory["preserve"]["photos_referenced_by_private"] == 1
        operation_id = UUID(response.json()["operation_id"])

    with SessionLocal() as db:
        storage = db.get(GalleryLifecycleOperation, operation_id).manifest["operational_storage"]
        assert [entry["photo_id"] for entry in storage["sources"]] == [str(removable_id)]

    assert process_next_gallery_lifecycle_operation() is True

    with SessionLocal() as db:
        parent = db.get(ParentGallery, parent_id)
        assert parent.lifecycle_status == "deleted"
        assert db.get(DerivedGallery, private_id) is not None
        assert db.get(PhotoAsset, retained_id) is not None
        assert db.get(PhotoAsset, removable_id) is None
        assert db.scalar(select(func.count()).select_from(DerivedGalleryPhoto)) == 1
    assert retained_source.read_bytes() == b"original-privada"
    assert retained_preview.read_bytes() == b"preview-privada-protegida"
    assert not removable_source.exists()
    assert not removable_preview.exists()

    with TestClient(app) as client:
        authenticate_client(client, owner_phone)
        library = client.get("/library")
        assert library.status_code == 200
        assert library.json()["public_galleries"] == []
        assert library.json()["galleries"] == [
            {
                "id": str(private_id),
                "name": "Privada que permanece",
                "message": "",
                "selection_expires_at": None,
                "gallery_status": "origin_removed",
                "membership_status": "active",
                "browse_url": f"/gallery/{private_id}",
                "origin_removed": True,
                "origin": {
                    "id": str(parent_id),
                    "name": "Origem removível",
                    "available": False,
                    "browse_url": None,
                },
                "folders": [{"id": str(folder.id), "name": "Lote compartilhado"}],
            }
        ]
        assert library.json()["private_galleries"] == library.json()["galleries"]
        photos = client.get(f"/gallery/{private_id}/photos")
        assert [item["id"] for item in photos.json()["photos"]] == [str(retained_id)]
        review = client.get(f"/gallery/{private_id}/review")
        assert review.status_code == 200
        assert [item["id"] for item in review.json()["photos"]] == [str(retained_id)]
        preview = client.get(f"/gallery/{private_id}/photos/{retained_id}/preview")
        assert preview.status_code == 200
        assert preview.content == b"preview-privada-protegida"
        assert (
            client.post(f"/gallery/{private_id}/photos/{retained_id}/selection").status_code == 409
        )
        assert client.get(f"/public-galleries/{parent_id}").status_code == 403

    with TestClient(app) as admin:
        authenticate_admin(admin)
        listed = admin.get("/admin/parent-galleries").json()["parent_galleries"]
        assert all(item["id"] != str(parent_id) for item in listed)


def test_client_library_separates_public_private_and_origin_states() -> None:
    owner_phone = "+5511999999817"
    with SessionLocal() as db:
        owner = Client(full_name="Cliente com múltiplas origens", phone_e164=owner_phone)
        active_parent = ParentGallery(name="Origem ativa", access_mode="standard")
        expired_parent = ParentGallery(name="Origem da seleção expirada")
        removed_parent = ParentGallery(
            name="Origem removida", lifecycle_status="deleted", active=False
        )
        pending_parent = ParentGallery(name="Origem coletiva", access_mode="collective_protected")
        unlinked_parent = ParentGallery(name="Origem sem vínculo")
        db.add_all(
            [
                owner,
                active_parent,
                expired_parent,
                removed_parent,
                pending_parent,
                unlinked_parent,
            ]
        )
        db.flush()
        db.add_all(
            [
                ParentGalleryRegistration(
                    parent_gallery_id=active_parent.id,
                    client_id=owner.id,
                    status="active",
                ),
                ParentGalleryRegistration(
                    parent_gallery_id=expired_parent.id,
                    client_id=owner.id,
                    status="active",
                ),
                ParentGalleryRegistration(
                    parent_gallery_id=removed_parent.id,
                    client_id=owner.id,
                    status="active",
                ),
                ParentGalleryRegistration(
                    parent_gallery_id=pending_parent.id,
                    client_id=owner.id,
                    status="pending",
                ),
                DerivedGallery(
                    parent_gallery_id=active_parent.id,
                    client_id=owner.id,
                    name="Privada ativa",
                ),
                DerivedGallery(
                    parent_gallery_id=expired_parent.id,
                    client_id=owner.id,
                    name="Privada expirada",
                    selection_expires_at=now() - timedelta(days=1),
                ),
                DerivedGallery(
                    parent_gallery_id=removed_parent.id,
                    client_id=owner.id,
                    name="Privada preservada",
                ),
            ]
        )
        db.commit()
        ids = {
            "active": active_parent.id,
            "expired": expired_parent.id,
            "removed": removed_parent.id,
            "pending": pending_parent.id,
            "unlinked": unlinked_parent.id,
        }

    with TestClient(app) as client:
        authenticate_client(client, owner_phone)
        response = client.get("/library")
    assert response.status_code == 200
    public_rows = {row["name"]: row for row in response.json()["public_galleries"]}
    assert set(public_rows) == {
        "Origem ativa",
        "Origem da seleção expirada",
        "Origem coletiva",
    }
    assert public_rows["Origem ativa"]["gallery_status"] == "active"
    assert public_rows["Origem ativa"]["browse_url"] == (f"/public-galleries/{ids['active']}")
    assert public_rows["Origem coletiva"]["gallery_status"] == "pending_review"
    assert public_rows["Origem coletiva"]["browse_url"] is None
    assert "Origem removida" not in public_rows
    assert "Origem sem vínculo" not in public_rows

    private_rows = {row["name"]: row for row in response.json()["private_galleries"]}
    assert private_rows["Privada ativa"]["gallery_status"] == "active"
    assert private_rows["Privada ativa"]["origin"]["browse_url"] == (
        f"/public-galleries/{ids['active']}"
    )
    assert private_rows["Privada expirada"]["gallery_status"] == "expired"
    assert private_rows["Privada expirada"]["origin"]["available"] is True
    assert private_rows["Privada preservada"]["gallery_status"] == ("origin_removed")
    assert private_rows["Privada preservada"]["origin"] == {
        "id": str(ids["removed"]),
        "name": "Origem removida",
        "available": False,
        "browse_url": None,
    }
    assert response.json()["galleries"] == response.json()["private_galleries"]


def test_commercial_removal_policy_blocks_review_cancels_pending_and_prepares_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "commercial-source"
    derivative_root = tmp_path / "commercial-derivatives"
    history_root = tmp_path / "commercial-history"
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivative_root))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))
    owner_phone = "+5511999999850"
    with SessionLocal() as db:
        owner = Client(full_name="Cliente comercial", phone_e164=owner_phone)
        parent = ParentGallery(name="Galeria da política comercial")
        db.add_all([owner, parent])
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote comercial", status="released")
        gallery = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada comercial",
        )
        db.add_all([folder, gallery])
        db.flush()
        photos = []
        for name in ("confirmada.jpg", "pendente.jpg", "revisao.jpg", "carrinho.jpg"):
            photo = PhotoAsset(
                parent_gallery_id=parent.id,
                folder_id=folder.id,
                filename=name,
                storage_key=f"commercial/{name}",
            )
            db.add(photo)
            db.flush()
            db.add(
                DerivedGalleryPhoto(
                    derived_gallery_id=gallery.id,
                    photo_asset_id=photo.id,
                    origin="client",
                )
            )
            photos.append(photo)
        confirmed, pending, review, cart = photos
        db.add(
            MediaDerivative(
                photo_asset_id=confirmed.id,
                variant="client_preview",
                relative_path=f"{confirmed.id}/client_preview.jpg",
                status="ready",
            )
        )
        orders = []
        for status_value, photo in (
            ("confirmed", confirmed),
            ("pending", pending),
            ("pending", review),
        ):
            order = SaleOrder(
                derived_gallery_id=gallery.id,
                client_id=owner.id,
                payment_status=status_value,
                total_cents=1000,
                confirmed_at=now() if status_value == "confirmed" else None,
            )
            db.add(order)
            db.flush()
            db.add(
                SaleOrderItem(
                    sale_order_id=order.id,
                    photo_asset_id=photo.id,
                    filename_snapshot=photo.filename,
                    unit_price_cents=1000,
                )
            )
            orders.append(order)
        communication = PaymentCommunication(
            sale_order_id=orders[2].id,
            client_id=owner.id,
            idempotency_key="review-before-removal",
        )
        db.add(communication)
        cart_selection = PhotoSelection(
            derived_gallery_id=gallery.id,
            photo_asset_id=cart.id,
            client_id=owner.id,
        )
        db.add(cart_selection)
        db.commit()
        parent_id, gallery_id, owner_id = parent.id, gallery.id, owner.id
        confirmed_id, cart_id = confirmed.id, cart.id
        order_ids = [order.id for order in orders]
        communication_id = communication.id

    source = source_root / "commercial/confirmada.jpg"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"entrega-confirmada")
    preview = derivative_root / f"{confirmed_id}/client_preview.jpg"
    preview.parent.mkdir(parents=True, exist_ok=True)
    preview.write_bytes(b"preview-confirmada")

    with SessionLocal() as db:
        with pytest.raises(CommercialRemovalBlocked):
            apply_commercial_removal_policy(db, parent_gallery_id=parent_id, client_id=owner_id)
        assert [db.get(SaleOrder, order_id).payment_status for order_id in order_ids] == [
            "confirmed",
            "pending",
            "pending",
        ]
        assert db.scalar(select(func.count()).select_from(CommercialHistoryMedia)) == 0
        db.rollback()

    with SessionLocal() as db:
        db.get(PaymentCommunication, communication_id).status = "refused"
        report = apply_commercial_removal_policy(
            db, parent_gallery_id=parent_id, client_id=owner_id
        )
        db.commit()
        assert report.cancelled_pending_orders == 2
        assert report.confirmed_orders == 1
        assert [db.get(SaleOrder, order_id).payment_status for order_id in order_ids] == [
            "confirmed",
            "cancelled",
            "cancelled",
        ]
        assert (
            db.scalar(
                select(func.count()).where(
                    AuditEvent.event == "sale_order.cancelled_for_operational_removal"
                )
            )
            == 2
        )
        assert db.scalar(select(func.count()).select_from(CommercialHistoryMedia)) == 1
        second = apply_commercial_removal_policy(
            db, parent_gallery_id=parent_id, client_id=owner_id
        )
        assert second.cancelled_pending_orders == 0
        assert second.confirmed_orders == 1

    with TestClient(app) as client:
        authenticate_client(client, owner_phone)
        response = client.delete(f"/gallery/{gallery_id}/photos/{cart_id}/selection")
        assert response.status_code == 204
    with SessionLocal() as db:
        assert (
            db.scalar(select(PhotoSelection.id).where(PhotoSelection.photo_asset_id == cart_id))
            is None
        )


def test_admin_parent_link_is_idempotent_and_never_creates_empty_private_gallery() -> None:
    with SessionLocal() as db:
        client_record = Client(full_name="Cliente somente vinculada", phone_e164="+5511999999860")
        parent = ParentGallery(name="Galeria pública sem derivação")
        db.add_all([client_record, parent])
        db.commit()
        client_id, parent_id = client_record.id, parent.id

    with TestClient(app) as client:
        authenticate_admin(client)
        first = client.put(f"/admin/parent-galleries/{parent_id}/clients/{client_id}")
        second = client.put(f"/admin/parent-galleries/{parent_id}/clients/{client_id}")
        assert first.status_code == second.status_code == 200
        assert first.json()["registration_id"] == second.json()["registration_id"]
        assert first.json()["status"] == "active"
        assert first.json()["private_gallery_id"] is None

    with SessionLocal() as db:
        registrations = list(
            db.scalars(
                select(ParentGalleryRegistration).where(
                    ParentGalleryRegistration.parent_gallery_id == parent_id,
                    ParentGalleryRegistration.client_id == client_id,
                )
            )
        )
        assert len(registrations) == 1
        assert registrations[0].status == "active"
        assert (
            db.scalar(
                select(func.count())
                .select_from(DerivedGallery)
                .where(
                    DerivedGallery.parent_gallery_id == parent_id,
                    DerivedGallery.client_id == client_id,
                )
            )
            == 0
        )


def test_first_public_selection_derives_once_and_keeps_origins_separate() -> None:
    owner_phone = "+5511999999870"
    with SessionLocal() as db:
        owner = Client(full_name="Cliente da primeira seleção", phone_e164=owner_phone)
        parent = ParentGallery(
            name="Galeria pública selecionável",
            pricing_mode="fixed",
            fixed_unit_price_cents=700,
        )
        db.add_all([owner, parent])
        db.flush()
        db.add(
            PriceRule(
                parent_gallery_id=parent.id,
                minimum_quantity=1,
                maximum_quantity=None,
                unit_price_cents=700,
            )
        )
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote liberado", status="released")
        db.add(folder)
        db.flush()
        first = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="primeira-selecao.jpg",
            storage_key="selection/first.jpg",
        )
        second = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="segunda-selecao.jpg",
            storage_key="selection/second.jpg",
        )
        db.add_all([first, second])
        db.flush()
        db.add(
            ParentGalleryRegistration(
                parent_gallery_id=parent.id,
                client_id=owner.id,
                status="active",
            )
        )
        db.commit()
        parent_id, owner_id = parent.id, owner.id
        first_id, second_id = first.id, second.id

    with TestClient(app) as client:
        authenticate_client(client, owner_phone)
        first_response = client.post(f"/public-galleries/{parent_id}/photos/{first_id}/selection")
        assert first_response.status_code == 201
        assert first_response.json()["gallery_created"] is True
        assert first_response.json()["reference_created"] is True
        assert first_response.json()["selection_created"] is True
        private_id = UUID(first_response.json()["private_gallery_id"])
        repeated = client.post(f"/public-galleries/{parent_id}/photos/{first_id}/selection")
        assert repeated.status_code == 201
        assert {
            key: repeated.json()[key]
            for key in (
                "status",
                "private_gallery_id",
                "gallery_created",
                "reference_created",
                "selection_created",
            )
        } == {
            "status": "selected",
            "private_gallery_id": str(private_id),
            "gallery_created": False,
            "reference_created": False,
            "selection_created": False,
        }
        assert repeated.json()["cart"]["quantity"] == 1
        assert repeated.json()["cart"]["total_cents"] == 700

        with SessionLocal() as db:
            ensure_private_photo_reference(
                db, gallery_id=private_id, photo_id=second_id, origin="admin"
            )
            db.commit()
        additional = client.post(f"/public-galleries/{parent_id}/photos/{second_id}/selection")
        assert additional.status_code == 201
        assert additional.json()["private_gallery_id"] == str(private_id)
        assert additional.json()["gallery_created"] is False
        assert additional.json()["reference_created"] is False
        assert additional.json()["selection_created"] is True
        public_state = client.get(f"/public-galleries/{parent_id}/photos").json()
        assert public_state["private_gallery_id"] == str(private_id)
        assert {photo["id"]: photo["selected"] for photo in public_state["photos"]} == {
            str(first_id): True,
            str(second_id): True,
        }
        assert public_state["cart"]["quantity"] == 2
        assert public_state["cart"]["total_cents"] == 1400

        removed = client.delete(
            f"/public-galleries/{parent_id}/photos/{second_id}/selection"
        )
        assert removed.status_code == 200
        assert removed.json()["gallery_closed"] is False
        assert removed.json()["cart"]["quantity"] == 1
        restored = client.get(f"/public-galleries/{parent_id}/photos").json()
        assert {photo["id"]: photo["selected"] for photo in restored["photos"]} == {
            str(first_id): True,
            str(second_id): False,
        }

    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(DerivedGallery)
                .where(
                    DerivedGallery.parent_gallery_id == parent_id,
                    DerivedGallery.client_id == owner_id,
                )
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(PhotoSelection)
                .where(
                    PhotoSelection.derived_gallery_id == private_id,
                    PhotoSelection.client_id == owner_id,
                )
            )
            == 1
        )
        origins = set(
            db.scalars(
                select(DerivedGalleryPhotoOrigin.origin)
                .join(
                    DerivedGalleryPhoto,
                    DerivedGalleryPhoto.id
                    == DerivedGalleryPhotoOrigin.derived_gallery_photo_id,
                )
                .where(
                    DerivedGalleryPhoto.derived_gallery_id == private_id,
                    DerivedGalleryPhoto.photo_asset_id == second_id,
                )
            )
        )
        assert origins == {"admin"}


def test_public_selection_state_is_isolated_and_shared_reference_survives_unselect() -> None:
    first_phone = "+5511999999868"
    second_phone = "+5511999999869"
    with SessionLocal() as db:
        first = Client(full_name="Primeira cliente", phone_e164=first_phone)
        second = Client(full_name="Segunda cliente", phone_e164=second_phone)
        parent = ParentGallery(name="Galeria compartilhada", pricing_mode="fixed")
        db.add_all([first, second, parent])
        db.flush()
        db.add(
            PriceRule(
                parent_gallery_id=parent.id,
                minimum_quantity=1,
                maximum_quantity=None,
                unit_price_cents=900,
            )
        )
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote", status="released")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="compartilhada.jpg",
            storage_key="selection/shared.jpg",
        )
        gallery = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=first.id,
            name="Privada familiar",
        )
        db.add_all([photo, gallery])
        db.flush()
        db.add_all(
            [
                ParentGalleryRegistration(
                    parent_gallery_id=parent.id, client_id=person.id, status="active"
                )
                for person in (first, second)
            ]
            + [
                DerivedGalleryMembership(
                    derived_gallery_id=gallery.id,
                    parent_gallery_id=parent.id,
                    client_id=person.id,
                    status="active",
                )
                for person in (first, second)
            ]
        )
        ensure_private_photo_reference(
            db, gallery_id=gallery.id, photo_id=photo.id, origin="client"
        )
        db.add_all(
            [
                PhotoSelection(
                    derived_gallery_id=gallery.id,
                    photo_asset_id=photo.id,
                    client_id=person.id,
                )
                for person in (first, second)
            ]
        )
        db.commit()
        parent_id, gallery_id, photo_id, first_id = parent.id, gallery.id, photo.id, first.id

    with TestClient(app) as client:
        authenticate_client(client, first_phone)
        first_state = client.get(f"/public-galleries/{parent_id}/photos").json()
        assert first_state["photos"][0]["selected"] is True
        assert first_state["cart"]["quantity"] == 1
        assert client.delete(
            f"/public-galleries/{parent_id}/photos/{photo_id}/selection"
        ).status_code == 200

        client.cookies.clear()
        authenticate_client(client, second_phone)
        second_state = client.get(f"/public-galleries/{parent_id}/photos").json()
        assert second_state["private_gallery_id"] == str(gallery_id)
        assert second_state["photos"][0]["selected"] is True
        assert second_state["cart"]["quantity"] == 1
        assert client.get(f"/gallery/{gallery_id}/review").json()["photos"][0]["selected"] is True

    with SessionLocal() as db:
        assert db.scalar(
            select(DerivedGalleryPhoto).where(
                DerivedGalleryPhoto.derived_gallery_id == gallery_id,
                DerivedGalleryPhoto.photo_asset_id == photo_id,
            )
        ) is not None
        assert db.scalar(
            select(PhotoSelection).where(
                PhotoSelection.derived_gallery_id == gallery_id,
                PhotoSelection.photo_asset_id == photo_id,
            )
        ).client_id != first_id


def test_client_derivation_reuses_gallery_created_by_admin_race_winner() -> None:
    owner_phone = "+5511999999871"
    with SessionLocal() as db:
        owner = Client(full_name="Cliente da corrida", phone_e164=owner_phone)
        parent = ParentGallery(name="Galeria pública concorrente")
        db.add_all([owner, parent])
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote", status="released")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="corrida.jpg",
            storage_key="selection/race.jpg",
        )
        db.add(photo)
        db.flush()
        db.add(
            ParentGalleryRegistration(
                parent_gallery_id=parent.id,
                client_id=owner.id,
                status="active",
            )
        )
        admin_gallery = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Criada pelo admin",
        )
        db.add(admin_gallery)
        db.flush()
        ensure_private_photo_reference(
            db, gallery_id=admin_gallery.id, photo_id=photo.id, origin="admin"
        )
        db.commit()
        parent_id, photo_id, admin_gallery_id = parent.id, photo.id, admin_gallery.id

    with TestClient(app) as client:
        authenticate_client(client, owner_phone)
        response = client.post(f"/public-galleries/{parent_id}/photos/{photo_id}/selection")
        assert response.status_code == 201
        assert response.json()["private_gallery_id"] == str(admin_gallery_id)
        assert response.json()["gallery_created"] is False
        assert response.json()["reference_created"] is False
        assert response.json()["selection_created"] is True

    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(DerivedGallery)
                .where(DerivedGallery.parent_gallery_id == parent_id)
            )
            == 1
        )
        assert set(
            db.scalars(
                select(DerivedGalleryPhotoOrigin.origin)
                .join(
                    DerivedGalleryPhoto,
                    DerivedGalleryPhoto.id
                    == DerivedGalleryPhotoOrigin.derived_gallery_photo_id,
                )
                .where(
                    DerivedGalleryPhoto.derived_gallery_id == admin_gallery_id,
                    DerivedGalleryPhoto.photo_asset_id == photo_id,
                )
            )
        ) == {"admin", "client"}


def test_selection_isolated_by_parent_and_rederives_after_safe_closure() -> None:
    owner_phone = "+5511999999872"
    with SessionLocal() as db:
        owner = Client(full_name="Cliente de duas origens", phone_e164=owner_phone)
        first_parent = ParentGallery(name="Primeira origem")
        second_parent = ParentGallery(name="Segunda origem")
        db.add_all([owner, first_parent, second_parent])
        db.flush()
        photo_ids: dict[UUID, list[UUID]] = {}
        for parent, names in (
            (first_parent, ("primeira-a.jpg", "primeira-b.jpg")),
            (second_parent, ("segunda-a.jpg",)),
        ):
            folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote", status="released")
            db.add(folder)
            db.flush()
            photo_ids[parent.id] = []
            for name in names:
                photo = PhotoAsset(
                    parent_gallery_id=parent.id,
                    folder_id=folder.id,
                    filename=name,
                    storage_key=f"multi/{name}",
                )
                db.add(photo)
                db.flush()
                photo_ids[parent.id].append(photo.id)
            db.add(
                ParentGalleryRegistration(
                    parent_gallery_id=parent.id,
                    client_id=owner.id,
                    status="active",
                )
            )
        db.commit()
        first_parent_id, second_parent_id = first_parent.id, second_parent.id

    with TestClient(app) as client:
        authenticate_client(client, owner_phone)
        first = client.post(
            f"/public-galleries/{first_parent_id}/photos/{photo_ids[first_parent_id][0]}/selection"
        ).json()
        second = client.post(
            f"/public-galleries/{second_parent_id}/photos/"
            f"{photo_ids[second_parent_id][0]}/selection"
        ).json()
        assert first["private_gallery_id"] != second["private_gallery_id"]
        old_first_private = UUID(first["private_gallery_id"])

        with SessionLocal() as db:
            gallery = db.get(DerivedGallery, old_first_private)
            gallery.selection_expires_at = now() - timedelta(seconds=1)
            db.commit()
        expired_response = client.post(
            f"/public-galleries/{first_parent_id}/photos/{photo_ids[first_parent_id][1]}/selection"
        )
        assert expired_response.status_code == 409
        assert "expirou" in expired_response.json()["detail"]

        with SessionLocal() as db:
            gallery = db.get(DerivedGallery, old_first_private)
            gallery.selection_expires_at = None
            db.commit()
        client.cookies.clear()
        authenticate_admin(client)
        assert client.delete(f"/admin/derived-galleries/{old_first_private}").status_code == 204
        client.cookies.clear()
        authenticate_client(client, owner_phone)
        renewed = client.post(
            f"/public-galleries/{first_parent_id}/photos/{photo_ids[first_parent_id][1]}/selection"
        )
        assert renewed.status_code == 201
        assert renewed.json()["gallery_created"] is True
        assert renewed.json()["private_gallery_id"] != str(old_first_private)

    with SessionLocal() as db:
        active_galleries = list(
            db.scalars(select(DerivedGallery).order_by(DerivedGallery.parent_gallery_id))
        )
        assert len(active_galleries) == 2
        for gallery in active_galleries:
            assigned_parent_ids = set(
                db.scalars(
                    select(PhotoAsset.parent_gallery_id)
                    .join(
                        DerivedGalleryPhoto,
                        DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id,
                    )
                    .where(DerivedGalleryPhoto.derived_gallery_id == gallery.id)
                )
            )
            assert assigned_parent_ids == {gallery.parent_gallery_id}


def test_unselect_closes_only_empty_client_private_and_preserves_admin_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_root = tmp_path / "private-close-history"
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))
    owner_phone = "+5511999999873"
    with SessionLocal() as db:
        owner = Client(full_name="Cliente que remove seleção", phone_e164=owner_phone)
        admin_parent = ParentGallery(name="Origem administrativa")
        client_parent = ParentGallery(name="Origem somente cliente")
        review_parent = ParentGallery(name="Origem em revisão")
        confirmed_parent = ParentGallery(name="Origem confirmada")
        db.add_all([owner, admin_parent, client_parent, review_parent, confirmed_parent])
        db.flush()

        def private_photo(parent: ParentGallery, suffix: str):
            folder = PhotoFolder(
                parent_gallery_id=parent.id,
                name=f"Lote {suffix}",
                status="released",
            )
            gallery = DerivedGallery(
                parent_gallery_id=parent.id,
                client_id=owner.id,
                name=f"Privada {suffix}",
            )
            db.add_all([folder, gallery])
            db.flush()
            photo = PhotoAsset(
                parent_gallery_id=parent.id,
                folder_id=folder.id,
                filename=f"{suffix}.jpg",
                storage_key=f"close/{suffix}.jpg",
            )
            db.add(photo)
            db.flush()
            ensure_private_photo_reference(
                db, gallery_id=gallery.id, photo_id=photo.id, origin="client"
            )
            db.add_all(
                [
                    ParentGalleryRegistration(
                        parent_gallery_id=parent.id,
                        client_id=owner.id,
                        status="active",
                    ),
                    PhotoSelection(
                        derived_gallery_id=gallery.id,
                        photo_asset_id=photo.id,
                        client_id=owner.id,
                    ),
                ]
            )
            return gallery, photo

        admin_gallery, admin_photo = private_photo(admin_parent, "admin")
        ensure_private_photo_reference(
            db, gallery_id=admin_gallery.id, photo_id=admin_photo.id, origin="admin"
        )
        client_gallery, client_photo = private_photo(client_parent, "client")
        review_gallery, review_photo = private_photo(review_parent, "review")
        review_order = SaleOrder(
            derived_gallery_id=review_gallery.id,
            client_id=owner.id,
            payment_status="pending",
            total_cents=1000,
        )
        db.add(review_order)
        db.flush()
        db.add_all(
            [
                SaleOrderItem(
                    sale_order_id=review_order.id,
                    photo_asset_id=review_photo.id,
                    filename_snapshot=review_photo.filename,
                    unit_price_cents=1000,
                ),
                PaymentCommunication(
                    sale_order_id=review_order.id,
                    client_id=owner.id,
                    idempotency_key="review-private-close",
                    status="pending_review",
                ),
            ]
        )
        confirmed_gallery, confirmed_photo = private_photo(confirmed_parent, "confirmed")
        confirmed_order = SaleOrder(
            derived_gallery_id=confirmed_gallery.id,
            client_id=owner.id,
            payment_status="confirmed",
            total_cents=1200,
            confirmed_at=now(),
        )
        db.add(confirmed_order)
        db.flush()
        confirmed_item = SaleOrderItem(
            sale_order_id=confirmed_order.id,
            photo_asset_id=confirmed_photo.id,
            filename_snapshot=confirmed_photo.filename,
            unit_price_cents=1200,
        )
        db.add(confirmed_item)
        db.flush()
        preview_key = f"items/{confirmed_item.id}/preview.jpg"
        preview_path = history_root / preview_key
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_bytes = b"preview-historica-confirmada"
        preview_path.write_bytes(preview_bytes)
        db.add(
            CommercialHistoryMedia(
                sale_order_item_id=confirmed_item.id,
                preview_storage_key=preview_key,
                delivery_reference="provider://entrega/confirmada",
                checksum_sha256=sha256(preview_bytes).hexdigest(),
                media_type="image/jpeg",
                size_bytes=len(preview_bytes),
                status="ready",
            )
        )
        db.commit()
        ids = {
            "admin_gallery": admin_gallery.id,
            "admin_photo": admin_photo.id,
            "client_gallery": client_gallery.id,
            "client_photo": client_photo.id,
            "client_parent": client_parent.id,
            "review_gallery": review_gallery.id,
            "review_photo": review_photo.id,
            "confirmed_gallery": confirmed_gallery.id,
            "confirmed_photo": confirmed_photo.id,
            "confirmed_order": confirmed_order.id,
        }

    with TestClient(app) as client:
        authenticate_client(client, owner_phone)
        admin_removal = client.delete(
            f"/gallery/{ids['admin_gallery']}/photos/{ids['admin_photo']}/selection"
        )
        assert admin_removal.status_code == 204
        assert "x-markina-gallery-closed" not in admin_removal.headers
        client_removal = client.delete(
            f"/gallery/{ids['client_gallery']}/photos/{ids['client_photo']}/selection"
        )
        assert client_removal.status_code == 204
        assert client_removal.headers["x-markina-gallery-closed"] == "true"
        assert client_removal.headers["x-markina-public-gallery-url"] == (
            f"/public-galleries/{ids['client_parent']}"
        )
        review = client.delete(
            f"/gallery/{ids['review_gallery']}/photos/{ids['review_photo']}/selection"
        )
        assert review.status_code == 409
        assert "aguardando decisão" in review.json()["detail"]
        confirmed_removal = client.delete(
            f"/gallery/{ids['confirmed_gallery']}/photos/{ids['confirmed_photo']}/selection"
        )
        assert confirmed_removal.status_code == 204
        assert confirmed_removal.headers["x-markina-gallery-closed"] == "true"

    with SessionLocal() as db:
        assert db.get(DerivedGallery, ids["admin_gallery"]) is not None
        assert set(
            db.scalars(
                select(DerivedGalleryPhotoOrigin.origin)
                .join(
                    DerivedGalleryPhoto,
                    DerivedGalleryPhoto.id
                    == DerivedGalleryPhotoOrigin.derived_gallery_photo_id,
                )
                .where(
                    DerivedGalleryPhoto.derived_gallery_id == ids["admin_gallery"]
                )
            )
        ) == {"admin"}
        assert db.get(DerivedGallery, ids["client_gallery"]) is None
        assert db.get(PhotoAsset, ids["client_photo"]) is not None
        assert (
            db.scalar(
                select(ParentGalleryRegistration.id).where(
                    ParentGalleryRegistration.parent_gallery_id == ids["client_parent"]
                )
            )
            is not None
        )
        assert db.get(DerivedGallery, ids["review_gallery"]) is not None
        assert (
            db.scalar(
                select(PhotoSelection.id).where(
                    PhotoSelection.derived_gallery_id == ids["review_gallery"]
                )
            )
            is not None
        )
        assert db.get(DerivedGallery, ids["confirmed_gallery"]) is None
        assert db.get(PhotoAsset, ids["confirmed_photo"]) is not None
        confirmed_order = db.get(SaleOrder, ids["confirmed_order"])
        assert confirmed_order.derived_gallery_id is None
        assert confirmed_order.payment_status == "confirmed"
        assert (
            db.scalar(
                select(CommercialHistoryMedia.id)
                .join(SaleOrderItem)
                .where(SaleOrderItem.sale_order_id == confirmed_order.id)
            )
            is not None
        )


def test_unlink_client_is_idempotent_scoped_and_preserves_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_root = tmp_path / "unlink-history"
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))
    with SessionLocal() as db:
        owner = Client(full_name="Cliente a desvincular", phone_e164="+5511999999874")
        link_only = Client(full_name="Cliente sem privada", phone_e164="+5511999999875")
        unrelated_client = Client(full_name="Cliente independente", phone_e164="+5511999999876")
        parent = ParentGallery(name="Origem da desvinculação")
        other_parent = ParentGallery(name="Origem independente")
        db.add_all([owner, link_only, unrelated_client, parent, other_parent])
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote alvo", status="released")
        other_folder = PhotoFolder(
            parent_gallery_id=other_parent.id,
            name="Lote independente",
            status="released",
        )
        target_gallery = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada alvo",
            favorites_enabled=True,
            comments_enabled=True,
        )
        other_gallery = DerivedGallery(
            parent_gallery_id=other_parent.id,
            client_id=owner.id,
            name="Privada independente",
        )
        db.add_all([folder, other_folder, target_gallery, other_gallery])
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="alvo.jpg",
            storage_key="unlink/alvo.jpg",
        )
        other_photo = PhotoAsset(
            parent_gallery_id=other_parent.id,
            folder_id=other_folder.id,
            filename="independente.jpg",
            storage_key="unlink/independente.jpg",
        )
        db.add_all([photo, other_photo])
        db.flush()
        target_registration = ParentGalleryRegistration(
            parent_gallery_id=parent.id, client_id=owner.id, status="active"
        )
        link_only_registration = ParentGalleryRegistration(
            parent_gallery_id=parent.id, client_id=link_only.id, status="active"
        )
        other_registration = ParentGalleryRegistration(
            parent_gallery_id=other_parent.id, client_id=owner.id, status="active"
        )
        db.add_all([target_registration, link_only_registration, other_registration])
        db.flush()
        db.add_all(
            [
                DerivedGalleryPhoto(
                    derived_gallery_id=target_gallery.id,
                    photo_asset_id=photo.id,
                    origin="admin",
                ),
                DerivedGalleryMembership(
                    derived_gallery_id=target_gallery.id,
                    parent_gallery_id=parent.id,
                    client_id=owner.id,
                ),
                PhotoSelection(
                    derived_gallery_id=target_gallery.id,
                    photo_asset_id=photo.id,
                    client_id=owner.id,
                ),
                PhotoFavorite(
                    derived_gallery_id=target_gallery.id,
                    photo_asset_id=photo.id,
                    client_id=owner.id,
                ),
                PhotoComment(
                    derived_gallery_id=target_gallery.id,
                    photo_asset_id=photo.id,
                    client_id=owner.id,
                    body="Interação removível",
                ),
                PhotoView(
                    derived_gallery_id=target_gallery.id,
                    photo_asset_id=photo.id,
                    client_id=owner.id,
                ),
                PriceRule(
                    parent_gallery_id=parent.id,
                    minimum_quantity=1,
                    maximum_quantity=None,
                    unit_price_cents=1800,
                ),
                PixCheckoutSettings(
                    parent_gallery_id=parent.id,
                    copy_paste="pix-desvinculacao",
                ),
                GalleryAccess(client_id=owner.id, gallery_id=target_gallery.id),
                GalleryAccessCapability(
                    parent_gallery_id=parent.id,
                    derived_gallery_id=target_gallery.id,
                    client_id=owner.id,
                    scope="private_invite",
                    token_hash="9" * 64,
                ),
                DerivedGalleryPhoto(
                    derived_gallery_id=other_gallery.id,
                    photo_asset_id=other_photo.id,
                    origin="admin",
                ),
            ]
        )
        order = SaleOrder(
            derived_gallery_id=target_gallery.id,
            client_id=owner.id,
            payment_status="confirmed",
            total_cents=1800,
            confirmed_at=now(),
        )
        db.add(order)
        db.flush()
        item = SaleOrderItem(
            sale_order_id=order.id,
            photo_asset_id=photo.id,
            filename_snapshot=photo.filename,
            unit_price_cents=1800,
        )
        db.add(item)
        db.flush()
        preview_key = f"items/{item.id}/preview.jpg"
        preview_path = history_root / preview_key
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_content = b"preview-desvinculacao"
        preview_path.write_bytes(preview_content)
        db.add(
            CommercialHistoryMedia(
                sale_order_item_id=item.id,
                preview_storage_key=preview_key,
                delivery_reference="provider://entrega/desvinculacao",
                checksum_sha256=sha256(preview_content).hexdigest(),
                media_type="image/jpeg",
                size_bytes=len(preview_content),
                status="ready",
            )
        )
        db.commit()
        ids = {
            "owner": owner.id,
            "link_only": link_only.id,
            "unrelated_client": unrelated_client.id,
            "parent": parent.id,
            "other_parent": other_parent.id,
            "target_gallery": target_gallery.id,
            "other_gallery": other_gallery.id,
            "photo": photo.id,
            "other_photo": other_photo.id,
            "order": order.id,
            "item": item.id,
        }

    target_url = f"/admin/parent-galleries/{ids['parent']}/clients/{ids['owner']}"
    inventory_url = f"{target_url}/unlink-inventory"
    with TestClient(app) as anonymous:
        assert anonymous.get(inventory_url).status_code == 403
        assert (
            anonymous.delete(
                target_url, headers={"Idempotency-Key": "unlink-target-0001"}
            ).status_code
            == 403
        )

    with TestClient(app) as client:
        authenticate_admin(client)
        preview = client.get(inventory_url)
        assert preview.status_code == 200
        assert preview.json()["operation_type"] == "unlink_client"
        assert preview.json()["target"] == {
            "parent_gallery_id": str(ids["parent"]),
            "parent_gallery_name": "Origem da desvinculação",
            "client_id": str(ids["owner"]),
            "client_name": "Cliente a desvincular",
        }
        assert preview.json()["request"] == {
            "method": "DELETE",
            "url": target_url,
            "requires_idempotency_key": True,
            "asynchronous": True,
        }
        assert preview.json()["consequences"] == {
            "gallery_relationship_removed": True,
            "private_gallery_removed": False,
            "private_gallery_preserved_for_other_members": True,
            "client_preserved": True,
            "commercial_history_preserved": True,
            "other_gallery_relationships_preserved": True,
            "restoration_available_after_start": False,
        }
        assert client.delete(target_url).status_code == 422
        assert (
            client.get(
                f"/admin/parent-galleries/{ids['parent']}/clients/{ids['unrelated_client']}/unlink-inventory"
            ).status_code
            == 404
        )
        assert (
            client.delete(
                f"/admin/parent-galleries/{ids['parent']}/clients/{uuid4()}",
                headers={"Idempotency-Key": "unlink-missing-client"},
            ).status_code
            == 404
        )
        assert (
            client.delete(
                f"/admin/parent-galleries/{ids['parent']}/clients/{ids['unrelated_client']}",
                headers={"Idempotency-Key": "unlink-missing-link"},
            ).status_code
            == 404
        )
        queued = client.delete(target_url, headers={"Idempotency-Key": "unlink-target-0001"})
        assert queued.status_code == 202
        payload = queued.json()
        assert payload["operation_type"] == "unlink_client"
        assert payload["inventory"] == {
            "remove": {
                "registrations": 1,
                "memberships": 1,
                "selections": 1,
                "favorites": 1,
                "comments": 1,
                "views": 1,
                "private_capabilities": 1,
            },
            "preserve": {
                "clients": 1,
                "private_galleries": 1,
                "available_references": 1,
                "shared_private_capabilities": 0,
                "photos": 1,
                "orders": 1,
                "orders_by_status": {
                    "pending": 0,
                    "confirmed": 1,
                    "cancelled": 0,
                },
                "order_items": 1,
            },
        }
        assert preview.json()["inventory"] == payload["inventory"]
        repeated = client.delete(target_url, headers={"Idempotency-Key": "unlink-target-0001"})
        assert repeated.json()["operation_id"] == payload["operation_id"]
        assert (
            client.delete(target_url, headers={"Idempotency-Key": "unlink-target-0002"}).status_code
            == 409
        )

    with SessionLocal() as db:
        registration = db.scalar(
            select(ParentGalleryRegistration).where(
                ParentGalleryRegistration.parent_gallery_id == ids["parent"],
                ParentGalleryRegistration.client_id == ids["owner"],
            )
        )
        assert registration.status == "unlinking"
        assert db.get(DerivedGallery, ids["target_gallery"]).access_enabled is True

    assert process_next_gallery_lifecycle_operation() is True

    with SessionLocal() as db:
        operation = db.get(GalleryLifecycleOperation, UUID(payload["operation_id"]))
        assert operation.status == "completed"
        assert operation.manifest["removed_records"]["private_galleries"] == 0
        assert operation.manifest["removed_records"]["memberships_unlinked"] == 1
        assert operation.manifest["removed_records"]["registrations"] == 1
        assert db.get(Client, ids["owner"]) is not None
        assert db.get(DerivedGallery, ids["target_gallery"]) is not None
        membership = db.scalar(
            select(DerivedGalleryMembership).where(
                DerivedGalleryMembership.parent_gallery_id == ids["parent"],
                DerivedGalleryMembership.client_id == ids["owner"],
            )
        )
        assert membership.status == "unlinked"
        assert db.get(PhotoAsset, ids["photo"]) is not None
        assert db.get(DerivedGallery, ids["other_gallery"]) is not None
        assert db.get(PhotoAsset, ids["other_photo"]) is not None
        assert (
            db.scalar(
                select(ParentGalleryRegistration.id).where(
                    ParentGalleryRegistration.parent_gallery_id == ids["other_parent"],
                    ParentGalleryRegistration.client_id == ids["owner"],
                )
            )
            is not None
        )
        order = db.get(SaleOrder, ids["order"])
        assert order.payment_status == "confirmed"
        assert order.derived_gallery_id == ids["target_gallery"]
        assert db.get(SaleOrderItem, ids["item"]).photo_asset_id == ids["photo"]
        assert (
            db.scalar(
                select(CommercialHistoryMedia.id).where(
                    CommercialHistoryMedia.sale_order_item_id == ids["item"]
                )
            )
            is not None
        )
        audit_rows = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.event.in_(
                        (
                            "parent_gallery.client_unlink_queued",
                            "parent_gallery.client_unlinked",
                        )
                    )
                )
            )
        )
        assert len(audit_rows) == 2
        serialized = str(operation.manifest) + " ".join(row.subject for row in audit_rows)
        assert "Cliente a desvincular" not in serialized
        assert "+5511999999874" not in serialized

    with TestClient(app) as client:
        authenticate_admin(client)
        link_only_url = f"/admin/parent-galleries/{ids['parent']}/clients/{ids['link_only']}"
        no_purchase = client.delete(
            link_only_url,
            headers={"Idempotency-Key": "unlink-without-private-0001"},
        )
        assert no_purchase.status_code == 202
    assert process_next_gallery_lifecycle_operation() is True
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(ParentGalleryRegistration.id).where(
                    ParentGalleryRegistration.parent_gallery_id == ids["parent"],
                    ParentGalleryRegistration.client_id == ids["link_only"],
                )
            )
            is None
        )
        assert db.get(Client, ids["link_only"]) is not None


def test_commercial_removal_lock_is_valid_postgresql_without_distinct() -> None:
    statement = commercial_removal_orders_query(
        parent_gallery_id=uuid4(),
        client_id=uuid4(),
        photo_asset_id=uuid4(),
    )
    compiled = str(statement.compile(dialect=postgresql.dialect())).upper()

    assert "FOR UPDATE" in compiled
    assert "DISTINCT" not in compiled
    assert "SALE_ORDER_ITEM" in compiled


def test_public_access_modes_require_session_and_backend_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    derivative_root = tmp_path / "public-derivatives"
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivative_root))
    owner_phone = "+5511999999880"
    with SessionLocal() as db:
        owner = Client(full_name="Cliente dos modos", phone_e164=owner_phone)
        standard = ParentGallery(
            name="Padrão",
            access_mode="standard",
            folder_display_mode="sequential",
            cover_title_font="playfair-display",
        )
        invite = ParentGallery(name="Convite", access_mode="invite_only")
        collective = ParentGallery(name="Coletiva protegida", access_mode="collective_protected")
        db.add_all([owner, standard, invite, collective])
        db.flush()
        folder = PhotoFolder(parent_gallery_id=standard.id, name="Lote", status="released")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=standard.id,
            folder_id=folder.id,
            filename="publica.jpg",
            storage_key="public/publica.jpg",
        )
        db.add(photo)
        db.flush()
        standard.cover_photo_id = photo.id
        derivative_key = f"{photo.id}/client_preview.jpg"
        db.add(
            MediaDerivative(
                photo_asset_id=photo.id,
                variant="client_preview",
                relative_path=derivative_key,
                status="ready",
                width=1600,
                height=900,
            )
        )
        _, standard_token = issue_gallery_capability(
            db, parent_gallery_id=standard.id, scope="public_gallery"
        )
        _, invite_public_token = issue_gallery_capability(
            db, parent_gallery_id=invite.id, scope="public_gallery"
        )
        _, invite_token = issue_gallery_capability(
            db,
            parent_gallery_id=invite.id,
            client_id=owner.id,
            scope="parent_invite",
        )
        _, collective_token = issue_gallery_capability(
            db, parent_gallery_id=collective.id, scope="public_gallery"
        )
        db.commit()
        standard_id, invite_id, collective_id = standard.id, invite.id, collective.id
        photo_id = photo.id
    preview = derivative_root / derivative_key
    preview.parent.mkdir(parents=True, exist_ok=True)
    preview.write_bytes(b"preview-publica-protegida")

    with TestClient(app) as client:
        preview_url = f"/public-galleries/{standard_id}/photos/{photo_id}/preview"
        assert client.get(preview_url).status_code == 403
        authenticate_client(client, owner_phone)
        standard_access = client.post(
            "/public-gallery/access",
            json={
                "access_token": standard_token,
                "return_to": "https://malicioso.example/fuga",
            },
        )
        assert standard_access.status_code == 200
        assert standard_access.json() == {
            "parent_gallery_id": str(standard_id),
            "access_state": "authorized",
            "destination": f"/public-galleries/{standard_id}",
            "can_browse_photos": True,
        }
        public_gallery = client.get(f"/public-galleries/{standard_id}")
        assert public_gallery.status_code == 200
        assert public_gallery.json()["folder_display_mode"] == "sequential"
        assert public_gallery.json()["cover_title_font"] == "playfair-display"
        assert public_gallery.json()["cover_preview_url"] == f"/public-galleries/{standard_id}/cover-preview"
        public_photo = client.get(f"/public-galleries/{standard_id}/photos").json()["photos"][0]
        assert public_photo["id"] == str(photo_id)
        assert public_photo["folder_name"] == "Lote"
        assert (public_photo["width"], public_photo["height"]) == (1600, 900)
        assert client.get(f"/public-galleries/{standard_id}/cover-preview").content == b"preview-publica-protegida"
        protected = client.get(preview_url)
        assert protected.status_code == 200
        assert protected.content == b"preview-publica-protegida"
        assert protected.headers["cache-control"] == "private, no-store"

        denied_invite = client.post(
            "/public-gallery/access",
            json={"access_token": invite_public_token},
        )
        assert denied_invite.status_code == 403
        invited = client.post("/public-gallery/access", json={"access_token": invite_token})
        assert invited.status_code == 200
        assert invited.json()["parent_gallery_id"] == str(invite_id)
        assert invited.json()["can_browse_photos"] is True

        collective_access = client.post(
            "/public-gallery/access", json={"access_token": collective_token}
        )
        assert collective_access.status_code == 200
        assert collective_access.json()["access_state"] == "pending_review"
        assert collective_access.json()["can_browse_photos"] is False
        assert client.get(f"/public-galleries/{collective_id}/photos").status_code == 403

        client.cookies.clear()
        otp_return = f"/public-galleries/{standard_id}?from=otp"
        challenge_id = client.post(
            "/auth/client/challenge",
            json={
                "full_name": "Nova cliente padrão",
                "phone": "+5511999999881",
                "access_token": standard_token,
                "return_to": otp_return,
            },
        ).json()["challenge_id"]
        with SessionLocal() as db:
            challenge = db.get(AuthChallenge, UUID(challenge_id))
            challenge.secret_hash = token_hash("123456")
            db.commit()
        verified = client.post(
            "/auth/client/verify",
            json={"challenge_id": challenge_id, "code": "123456"},
        )
        assert verified.status_code == 200
        assert verified.json()["destination"] == otp_return
        assert client.get(preview_url).status_code == 200

    with SessionLocal() as db:
        statuses = {
            (registration.parent_gallery_id, registration.client_id): registration.status
            for registration in db.scalars(select(ParentGalleryRegistration))
        }
        owner = db.scalar(select(Client).where(Client.phone_e164 == owner_phone))
        new_client = db.scalar(select(Client).where(Client.phone_e164 == "+5511999999881"))
        assert statuses[(standard_id, owner.id)] == "active"
        assert statuses[(invite_id, owner.id)] == "active"
        assert statuses[(collective_id, owner.id)] == "pending"
        assert statuses[(standard_id, new_client.id)] == "active"
        assert db.scalar(select(func.count()).select_from(DerivedGallery)) == 0


def test_facial_derivation_port_stays_disabled_and_has_no_http_surface() -> None:
    with pytest.raises(FacialDerivationUnavailable, match="não está habilitada"):
        derive_approved_facial_result()
    documented_paths = app.openapi()["paths"]
    assert not any(
        "facial" in path.casefold() or "biometr" in path.casefold() for path in documented_paths
    )
    with TestClient(app) as client:
        assert client.post(f"/public-galleries/{uuid4()}/facial-results").status_code == 404


def test_admin_private_creation_requires_photo_and_private_invite_owner() -> None:
    owner_phone = "+5511999999821"
    other_phone = "+5511999999822"
    with SessionLocal() as db:
        owner = Client(full_name="Cliente convidada", phone_e164=owner_phone)
        other = Client(full_name="Terceira com o link", phone_e164=other_phone)
        parent = ParentGallery(name="Galeria pública administrativa")
        foreign_parent = ParentGallery(name="Outra Galeria pública")
        db.add_all([owner, other, parent, foreign_parent])
        db.flush()
        folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Lote liberado",
            status="released",
            released_at=now(),
        )
        foreign_folder = PhotoFolder(
            parent_gallery_id=foreign_parent.id,
            name="Lote estrangeiro",
            status="released",
            released_at=now(),
        )
        preparing_folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Lote em preparo",
            status="preparing",
            position=1,
        )
        db.add_all([folder, foreign_folder, preparing_folder])
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="autorizada.jpg",
            storage_key="admin/autorizada.jpg",
        )
        foreign_photo = PhotoAsset(
            parent_gallery_id=foreign_parent.id,
            folder_id=foreign_folder.id,
            filename="estrangeira.jpg",
            storage_key="admin/estrangeira.jpg",
        )
        unavailable_photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="indisponivel.jpg",
            storage_key="admin/indisponivel.jpg",
            available=False,
        )
        preparing_photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=preparing_folder.id,
            filename="em-preparo.jpg",
            storage_key="admin/em-preparo.jpg",
        )
        db.add_all([photo, foreign_photo, unavailable_photo, preparing_photo])
        db.flush()
        db.add(
            MediaDerivative(
                photo_asset_id=photo.id,
                variant="client_preview",
                relative_path=f"{photo.id}/client-preview.jpg",
                status="ready",
            )
        )
        db.commit()
        owner_id, other_id = owner.id, other.id
        parent_id, photo_id, foreign_photo_id = parent.id, photo.id, foreign_photo.id

    with TestClient(app) as client:
        authenticate_admin(client)
        available = client.get(f"/admin/parent-galleries/{parent_id}/available-photos")
        assert available.status_code == 200
        assert available.json() == {
            "photos": [
                {
                    "id": str(photo_id),
                    "name": "autorizada.jpg",
                    "folder_name": "Lote liberado",
                    "preview_url": (f"/admin/photo-assets/{photo_id}/watermarked-preview"),
                    "width": None,
                    "height": None,
                    "publication_state": "published",
                }
            ]
        }
        missing_client = client.post(
            "/admin/derived-galleries",
            json={
                "parent_gallery_id": str(parent_id),
                "client_id": str(uuid4()),
                "name": "Não deve existir",
                "photo_ids": [str(photo_id)],
            },
        )
        assert missing_client.status_code == 404

        empty = client.post(
            "/admin/derived-galleries",
            json={
                "parent_gallery_id": str(parent_id),
                "client_id": str(owner_id),
                "name": "Ainda sem fotos",
                "photo_ids": [],
            },
        )
        assert empty.status_code == 201
        assert empty.json()["private_gallery_id"] is None

        wrong_origin = client.post(
            "/admin/derived-galleries",
            json={
                "parent_gallery_id": str(parent_id),
                "client_id": str(owner_id),
                "name": "Mistura proibida",
                "photo_ids": [str(foreign_photo_id)],
            },
        )
        assert wrong_origin.status_code == 422

        created = client.post(
            "/admin/derived-galleries",
            json={
                "parent_gallery_id": str(parent_id),
                "client_id": str(owner_id),
                "name": "Seleção administrativa",
                "photo_ids": [str(photo_id)],
            },
        )
        assert created.status_code == 201
        created_payload = created.json()
        gallery_id = UUID(created_payload["private_gallery_id"])
        invite_token = created_payload["invite_token"]
        assert invite_token
        assert created_payload["references_created"] == 1
        assert created_payload["gallery_created"] is True

        repeated = client.post(
            "/admin/derived-galleries",
            json={
                "parent_gallery_id": str(parent_id),
                "client_id": str(owner_id),
                "name": "Nome repetido não sobrescreve",
                "photo_ids": [str(photo_id)],
            },
        )
        assert repeated.status_code == 201
        assert repeated.json()["private_gallery_id"] == str(gallery_id)
        assert repeated.json()["references_created"] == 0
        assert repeated.json()["invite_token"] is None
        assert repeated.json()["invite_already_active"] is True

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(DerivedGallery)) == 1
        assert db.scalar(select(func.count()).select_from(DerivedGalleryPhoto)) == 1
        assert db.scalar(select(func.count()).select_from(PhotoSelection)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(GalleryAccessCapability)
                .where(GalleryAccessCapability.scope == "private_gallery_link")
            )
            == 1
        )
        registration = db.scalar(
            select(ParentGalleryRegistration).where(
                ParentGalleryRegistration.parent_gallery_id == parent_id,
                ParentGalleryRegistration.client_id == owner_id,
            )
        )
        assert registration.status == "active"

    def verify_private_invite(test_client: TestClient, phone: str):
        challenge_response = test_client.post(
            "/auth/client/challenge",
            json={
                "full_name": "Nome não usado",
                "phone": phone,
                "access_token": invite_token,
            },
        )
        assert challenge_response.status_code == 202
        challenge_id = UUID(challenge_response.json()["challenge_id"])
        with SessionLocal() as db:
            db.get(AuthChallenge, challenge_id).secret_hash = token_hash("123456")
            db.commit()
        return test_client.post(
            "/auth/client/verify",
            json={"challenge_id": str(challenge_id), "code": "123456"},
        )

    with TestClient(app) as third_party:
        joined = verify_private_invite(third_party, other_phone)
        assert joined.status_code == 200
        assert joined.json()["destination"] == f"/gallery/{gallery_id}"
        assert third_party.get(f"/gallery/{gallery_id}").status_code == 200

    with TestClient(app) as owner_client:
        verified = verify_private_invite(owner_client, owner_phone)
        assert verified.status_code == 200
        assert verified.json()["destination"] == f"/gallery/{gallery_id}"
        assert owner_client.get(f"/gallery/{gallery_id}").status_code == 200
    with SessionLocal() as db:
        assert db.get(Client, other_id) is not None
        private_link = db.scalar(
            select(GalleryAccessCapability).where(
                GalleryAccessCapability.scope == "private_gallery_link"
            )
        )
        assert private_link.status == "active"
        assert private_link.consumed_at is None
        assert (
            db.scalar(
                select(func.count())
                .select_from(DerivedGalleryMembership)
                .where(DerivedGalleryMembership.derived_gallery_id == gallery_id)
            )
            == 2
        )


def authenticate_admin(client: TestClient) -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == "lifecycle@markina.test"))
        if not admin:
            admin = AdminUser(
                email="lifecycle@markina.test",
                password_hash=password_hasher.hash("senha-segura"),
                email_verified=True,
                totp_secret=pyotp.random_base32(),
            )
            db.add(admin)
            db.commit()
        secret = admin.totp_secret
    challenge_id = client.post(
        "/auth/admin/password",
        json={"email": admin.email, "password": "senha-segura"},
    ).json()["challenge_id"]
    response = client.post(
        "/auth/admin/totp",
        json={"challenge_id": challenge_id, "code": pyotp.TOTP(secret).now()},
    )
    assert response.status_code == 200


def authenticate_client(client: TestClient, phone: str) -> None:
    challenge_id = client.post(
        "/auth/client/challenge",
        json={"full_name": "Cliente do ciclo", "phone": phone},
    ).json()["challenge_id"]
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, UUID(challenge_id))
        challenge.secret_hash = token_hash("123456")
        db.commit()
    response = client.post(
        "/auth/client/verify",
        json={"challenge_id": challenge_id, "code": "123456"},
    )
    assert response.status_code == 200


def test_deleting_parent_gallery_rejects_admin_and_client_mutations() -> None:
    with SessionLocal() as db:
        parent = ParentGallery(name="Galeria em exclusão", lifecycle_status="deleting")
        owner = Client(full_name="Cliente do ciclo", phone_e164="+5511999999700")
        db.add_all([parent, owner])
        db.flush()
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada em exclusão",
        )
        db.add(private)
        db.commit()
        parent_id, owner_id, owner_phone, private_id = (
            parent.id,
            owner.id,
            owner.phone_e164,
            private.id,
        )

    with TestClient(app) as client:
        authenticate_admin(client)
        responses = [
            client.patch(
                f"/admin/parent-galleries/{parent_id}/settings",
                json={"name": "Alteração indevida"},
            ),
            client.post(
                f"/admin/parent-galleries/{parent_id}/folders",
                json={"name": "Pasta indevida"},
            ),
            client.post(
                "/admin/derived-galleries",
                json={
                    "parent_gallery_id": str(parent_id),
                    "client_id": str(owner_id),
                    "name": "Privada indevida",
                    "photo_ids": [],
                },
            ),
            client.patch(
                f"/admin/derived-galleries/{private_id}",
                json={"name": "Alteração indevida"},
            ),
        ]
        assert all(response.status_code == 409 for response in responses)

        client.post("/auth/logout")
        authenticate_client(client, owner_phone)
        selection = client.post(f"/gallery/{private_id}/photos/{uuid4()}/selection")
        assert selection.status_code == 409

    with SessionLocal() as db:
        assert (
            db.scalar(select(PhotoFolder).where(PhotoFolder.parent_gallery_id == parent_id)) is None
        )
        assert (
            db.scalar(select(PhotoSelection).where(PhotoSelection.derived_gallery_id == private_id))
            is None
        )
        assert (
            db.scalar(
                select(ParentGallery).where(
                    ParentGallery.id == parent_id,
                    ParentGallery.name == "Alteração indevida",
                )
            )
            is None
        )


def test_lifecycle_queries_use_one_indexed_search_per_lookup() -> None:
    expected_indexes = {
        "gallery_lifecycle_operation": "ix_gallery_lifecycle_operation_target_status",
        "sale_order": "ix_sale_order_parent_payment_status",
        "derived_gallery": "ix_derived_gallery_parent_client",
        "photo_selection": "ix_photo_selection_gallery_client",
    }
    inspector = inspect(engine)
    for table_name, index_name in expected_indexes.items():
        assert index_name in {index["name"] for index in inspector.get_indexes(table_name)}

    plans = {
        "ix_gallery_lifecycle_operation_target_status": (
            (
                "SELECT id FROM gallery_lifecycle_operation "
                "WHERE target_parent_gallery_id = ? AND status = ?"
            ),
            (uuid4().hex, "queued"),
        ),
        "ix_sale_order_parent_payment_status": (
            (
                "SELECT id FROM sale_order "
                "WHERE parent_gallery_id_snapshot = ? AND payment_status = ?"
            ),
            (uuid4().hex, "confirmed"),
        ),
        "ix_derived_gallery_parent_client": (
            ("SELECT id FROM derived_gallery WHERE parent_gallery_id = ? AND client_id = ?"),
            (uuid4().hex, uuid4().hex),
        ),
        "ix_photo_selection_gallery_client": (
            ("SELECT count(*) FROM photo_selection WHERE derived_gallery_id = ? AND client_id = ?"),
            (uuid4().hex, uuid4().hex),
        ),
    }
    with engine.connect() as connection:
        for index_name, (statement, parameters) in plans.items():
            rows = connection.exec_driver_sql(f"EXPLAIN QUERY PLAN {statement}", parameters).all()
            indexed_searches = [
                row[3] for row in rows if "SEARCH" in row[3] and index_name in row[3]
            ]
            assert len(indexed_searches) == 1


def test_private_gallery_unique_pair_survives_a_preflight_race() -> None:
    with SessionLocal() as db:
        parent = ParentGallery(name="Galeria pública concorrente")
        owner = Client(full_name="Cliente concorrente", phone_e164="+5511999999600")
        db.add_all([parent, owner])
        db.commit()
        parent_id, owner_id = parent.id, owner.id

    first = SessionLocal()
    second = SessionLocal()
    try:
        lookup = select(DerivedGallery).where(
            DerivedGallery.parent_gallery_id == parent_id,
            DerivedGallery.client_id == owner_id,
        )
        assert first.scalar(lookup) is None
        assert second.scalar(lookup) is None
        first.add(
            DerivedGallery(
                parent_gallery_id=parent_id,
                client_id=owner_id,
                name="Primeira tentativa",
            )
        )
        second.add(
            DerivedGallery(
                parent_gallery_id=parent_id,
                client_id=owner_id,
                name="Segunda tentativa",
            )
        )
        first.commit()
        with pytest.raises(IntegrityError):
            second.commit()
    finally:
        first.close()
        second.close()

    with SessionLocal() as db:
        assert len(list(db.scalars(lookup))) == 1


def test_admin_availability_records_origin_without_creating_selection() -> None:
    with SessionLocal() as db:
        parent = ParentGallery(name="Galeria pública administrativa")
        owner = Client(full_name="Cliente administrativa", phone_e164="+5511999999500")
        db.add_all([parent, owner])
        db.flush()
        folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Disponíveis",
            status="released",
        )
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="admin.jpg",
            storage_key="admin/admin.jpg",
        )
        db.add(photo)
        db.flush()
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada iniciada pela cliente",
        )
        db.add(private)
        db.flush()
        ensure_private_photo_reference(
            db, gallery_id=private.id, photo_id=photo.id, origin="client"
        )
        db.commit()
        parent_id, owner_id, photo_id, expected_gallery_id = (
            parent.id,
            owner.id,
            photo.id,
            private.id,
        )

    with TestClient(app) as client:
        authenticate_admin(client)
        created = client.post(
            "/admin/derived-galleries",
            json={
                "parent_gallery_id": str(parent_id),
                "client_id": str(owner_id),
                "name": "Privada administrativa",
                "photo_ids": [str(photo_id)],
            },
        )
        assert created.status_code == 201
        gallery_id = UUID(created.json()["id"])
        assert gallery_id == expected_gallery_id

    with SessionLocal() as db:
        assert set(
            db.scalars(
                select(DerivedGalleryPhotoOrigin.origin)
                .join(
                    DerivedGalleryPhoto,
                    DerivedGalleryPhoto.id
                    == DerivedGalleryPhotoOrigin.derived_gallery_photo_id,
                )
                .where(
                    DerivedGalleryPhoto.derived_gallery_id == gallery_id,
                    DerivedGalleryPhoto.photo_asset_id == photo_id,
                )
            )
        ) == {"admin", "client"}
        assert (
            db.scalar(select(PhotoSelection).where(PhotoSelection.derived_gallery_id == gallery_id))
            is None
        )

        db.add(
            DerivedGalleryPhoto(
                derived_gallery_id=gallery_id,
                photo_asset_id=photo_id,
                origin="admin",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_phone_identity_constraints_contain_concurrent_client_creation() -> None:
    phone = "+5511999999400"
    first = SessionLocal()
    second = SessionLocal()
    try:
        assert first.scalar(select(Client).where(Client.phone_e164 == phone)) is None
        assert second.scalar(select(Client).where(Client.phone_e164 == phone)) is None
        first_client = Client(full_name="Primeira cliente", phone_e164=phone)
        second_client = Client(full_name="Segunda cliente", phone_e164=phone)
        first.add(first_client)
        second.add(second_client)
        first.flush()
        first.add(
            ClientPhone(
                client_id=first_client.id,
                phone_e164=phone,
                active=True,
                verified_at=now(),
            )
        )
        first.commit()
        with pytest.raises(IntegrityError):
            second.commit()
    finally:
        first.close()
        second.close()

    with SessionLocal() as db:
        clients = list(db.scalars(select(Client).where(Client.phone_e164 == phone)))
        phones = list(
            db.scalars(
                select(ClientPhone).where(
                    ClientPhone.phone_e164 == phone,
                    ClientPhone.active,
                    ClientPhone.verified_at.is_not(None),
                )
            )
        )
        assert len(clients) == 1
        assert len(phones) == 1
        assert phones[0].client_id == clients[0].id


def test_verified_phone_cannot_identify_two_distinct_clients() -> None:
    with SessionLocal() as db:
        first = Client(full_name="Primeira", phone_e164="+5511999999301")
        second = Client(full_name="Segunda", phone_e164="+5511999999302")
        db.add_all([first, second])
        db.flush()
        db.add(
            ClientPhone(
                client_id=first.id,
                phone_e164="+5511999999399",
                active=True,
                verified_at=now(),
            )
        )
        db.commit()
        db.add(
            ClientPhone(
                client_id=second.id,
                phone_e164="+5511999999399",
                active=True,
                verified_at=now(),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_gallery_access_mode_and_capability_targets_are_constrained() -> None:
    with SessionLocal() as db:
        db.add(ParentGallery(name="Modo inválido", access_mode="anonymous"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        parent = ParentGallery(name="Galeria protegida", access_mode="invite_only")
        db.add(parent)
        db.flush()
        db.add(
            GalleryAccessCapability(
                parent_gallery_id=parent.id,
                scope="parent_invite",
                token_hash="a" * 64,
                status="active",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_gallery_capability_never_persists_clear_token_and_supports_rotation() -> None:
    with SessionLocal() as db:
        parent = ParentGallery(name="Galeria com capacidade", access_mode="standard")
        db.add(parent)
        db.flush()
        capability, clear_token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            scope="public_gallery",
            expires_at=now() + timedelta(hours=1),
        )
        db.commit()
        capability_id, parent_id = capability.id, parent.id
        assert capability.token_hash != clear_token
        assert len(capability.token_hash) == 64
        assert (
            db.scalar(
                select(GalleryAccessCapability).where(
                    GalleryAccessCapability.token_hash == clear_token
                )
            )
            is None
        )
        assert resolve_gallery_capability(db, str(parent_id)) is None
        assert resolve_gallery_capability(db, clear_token).id == capability_id

        rotated, replacement_token = rotate_gallery_capability(db, capability)
        db.commit()
        assert capability.status == "rotated"
        assert rotated.rotated_from_id == capability_id
        assert replacement_token != clear_token
        assert resolve_gallery_capability(db, clear_token) is None
        assert resolve_gallery_capability(db, replacement_token).id == rotated.id

        revoke_gallery_capability(rotated)
        db.commit()
        assert resolve_gallery_capability(db, replacement_token) is None


def test_admin_manages_opaque_public_links_and_individual_invites() -> None:
    with TestClient(app) as client:
        authenticate_admin(client)
        created = client.post(
            "/admin/parent-galleries",
            json={"name": "Galeria pública com link", "access_mode": "standard"},
        )
        assert created.status_code == 201
        parent_id = UUID(created.json()["id"])
        first_token = created.json()["access_token"]
        assert len(first_token) >= 32
        assert first_token in created.json()["public_link"]

        status_response = client.get(f"/admin/parent-galleries/{parent_id}/public-link")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "active"
        assert status_response.json()["secret_available"] is True
        assert status_response.json()["access_token"] == first_token
        assert first_token in status_response.json()["link"]

        rotated = client.post(
            f"/admin/parent-galleries/{parent_id}/public-link/rotate",
            json={"expires_at": (now() + timedelta(hours=2)).isoformat()},
        )
        assert rotated.status_code == 200
        second_token = rotated.json()["access_token"]
        assert second_token != first_token

        client_id = UUID(
            client.post(
                "/admin/clients",
                json={
                    "full_name": "Cliente do convite",
                    "phone_e164": "+5511999999310",
                },
            ).json()["id"]
        )
        invite = client.post(
            f"/admin/parent-galleries/{parent_id}/clients/{client_id}/invite",
            json={"expires_at": (now() + timedelta(hours=1)).isoformat()},
        )
        assert invite.status_code == 201
        invite_token = invite.json()["access_token"]
        assert invite.json()["scope"] == "parent_invite"
        assert (
            client.post(
                f"/admin/parent-galleries/{parent_id}/clients/{client_id}/invite",
                json={},
            ).status_code
            == 409
        )
        rotated_invite = client.post(
            f"/admin/parent-galleries/{parent_id}/clients/{client_id}/invite/rotate",
            json={},
        )
        assert rotated_invite.status_code == 200
        replacement_invite_token = rotated_invite.json()["access_token"]
        assert replacement_invite_token != invite_token
        assert (
            client.delete(
                f"/admin/parent-galleries/{parent_id}/clients/{client_id}/invite"
            ).status_code
            == 204
        )
        assert (
            client.delete(
                f"/admin/parent-galleries/{parent_id}/clients/{client_id}/invite"
            ).status_code
            == 204
        )
        assert client.delete(f"/admin/parent-galleries/{parent_id}/public-link").status_code == 204

    with SessionLocal() as db:
        assert resolve_gallery_capability(db, first_token) is None
        assert resolve_gallery_capability(db, second_token) is None
        assert resolve_gallery_capability(db, invite_token) is None
        assert resolve_gallery_capability(db, replacement_invite_token) is None
        serialized = " ".join(
            event.subject
            for event in db.scalars(
                select(AuditEvent).where(AuditEvent.event.like("gallery_capability.%"))
            )
        )
        for token in (
            first_token,
            second_token,
            invite_token,
            replacement_invite_token,
        ):
            assert token not in serialized
            assert (
                db.scalar(
                    select(GalleryAccessCapability).where(
                        GalleryAccessCapability.token_hash == token
                    )
                )
                is None
            )


def test_expired_gallery_capability_is_neutral_and_persists_terminal_state() -> None:
    with SessionLocal() as db:
        parent = ParentGallery(name="Galeria com link expirado")
        db.add(parent)
        db.flush()
        capability, token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            scope="public_gallery",
            expires_at=now() - timedelta(seconds=1),
        )
        db.commit()
        capability_id = capability.id
        assert resolve_gallery_capability(db, token) is None
        db.commit()
    with SessionLocal() as db:
        assert db.get(GalleryAccessCapability, capability_id).status == "expired"
    with TestClient(app) as client:
        challenge = client.post(
            "/auth/client/challenge",
            json={
                "full_name": "Cliente expirada",
                "phone": "+5511999999311",
                "access_token": token,
            },
        )
        assert challenge.status_code == 401
        assert challenge.json() == {"detail": "Não foi possível concluir a autenticação."}


def test_parent_gallery_client_summary_is_batched_and_uses_status_precedence() -> None:
    with SessionLocal() as db:
        parent = ParentGallery(name="Galeria pública resumida")
        clients = [
            Client(
                full_name=f"Cliente {label}",
                phone_e164=f"+55119999994{index:02d}",
            )
            for index, label in enumerate(
                ("Pendente", "Sem seleção", "Bloqueada", "Expirada", "Ativa")
            )
        ]
        db.add_all([parent, *clients])
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote", status="released")
        db.add(folder)
        db.flush()
        photos = [
            PhotoAsset(
                parent_gallery_id=parent.id,
                folder_id=folder.id,
                filename=f"foto-{index}.jpg",
                storage_key=f"summary/foto-{index}.jpg",
            )
            for index in range(6)
        ]
        db.add_all(photos)
        db.flush()
        galleries = [
            DerivedGallery(
                parent_gallery_id=parent.id,
                client_id=client.id,
                name=f"Privada {index}",
                access_enabled=index != 2,
                selection_expires_at=(now() - timedelta(days=1) if index == 3 else None),
            )
            for index, client in enumerate(clients)
        ]
        db.add_all(galleries)
        db.flush()
        for index, (client, gallery) in enumerate(zip(clients, galleries)):
            db.add(
                ParentGalleryRegistration(
                    parent_gallery_id=parent.id,
                    client_id=client.id,
                    status="pending" if index == 0 else "active",
                )
            )
            db.add(
                DerivedGalleryPhoto(
                    derived_gallery_id=gallery.id,
                    photo_asset_id=photos[index].id,
                    origin="admin",
                )
            )
            if index != 1:
                db.add(
                    PhotoSelection(
                        derived_gallery_id=gallery.id,
                        photo_asset_id=photos[index].id,
                        client_id=client.id,
                    )
                )
        active_gallery = galleries[4]
        active_client = clients[4]
        db.add(
            DerivedGalleryPhoto(
                derived_gallery_id=active_gallery.id,
                photo_asset_id=photos[5].id,
                origin="admin",
            )
        )
        db.add(
            PhotoSelection(
                derived_gallery_id=active_gallery.id,
                photo_asset_id=photos[5].id,
                client_id=active_client.id,
            )
        )
        for checkout_key in ("summary-order-1", "summary-order-2"):
            order = SaleOrder(
                derived_gallery_id=active_gallery.id,
                client_id=active_client.id,
                payment_status="confirmed",
                total_cents=100,
                confirmed_at=now(),
                checkout_key=checkout_key,
            )
            db.add(order)
            db.flush()
            db.add(
                SaleOrderItem(
                    sale_order_id=order.id,
                    photo_asset_id=photos[4].id,
                    filename_snapshot=photos[4].filename,
                    unit_price_cents=100,
                )
            )
        db.commit()
        parent_id = parent.id

    statements: list[str] = []

    def record_select(_conn, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_select)
    try:
        with TestClient(app) as client:
            authenticate_admin(client)
            statements.clear()
            response = client.get(f"/admin/parent-galleries/{parent_id}/clients")
    finally:
        event.remove(engine, "before_cursor_execute", record_select)

    assert response.status_code == 200
    # A autenticação e todas as agregações permanecem constantes, sem crescer por cliente.
    assert len(statements) <= 12
    rows = {row["name"]: row for row in response.json()["clients"]}
    assert rows["Cliente Pendente"]["gallery_status"] == "pending_registration"
    assert rows["Cliente Sem seleção"]["gallery_status"] == "no_selection"
    assert rows["Cliente Sem seleção"]["available_count"] == 1
    assert rows["Cliente Bloqueada"]["gallery_status"] == "blocked"
    assert rows["Cliente Expirada"]["gallery_status"] == "expired"
    assert rows["Cliente Ativa"]["gallery_status"] == "active"
    assert rows["Cliente Ativa"]["available_count"] == 2
    assert rows["Cliente Ativa"]["selected_count"] == 2
    assert rows["Cliente Ativa"]["purchased_count"] == 1


def test_commercial_materialization_preserves_all_order_states_and_audit() -> None:
    with SessionLocal() as db:
        parent = ParentGallery(name="Galeria pública comercial")
        client = Client(full_name="Cliente comercial", phone_e164="+5511999999200")
        db.add_all([parent, client])
        db.flush()
        folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Comercial",
            status="released",
        )
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=client.id,
            name="Privada comercial",
        )
        db.add_all([folder, private])
        db.flush()
        order_ids = []
        for position, payment_status in enumerate(("confirmed", "pending", "cancelled"), start=1):
            photo = PhotoAsset(
                parent_gallery_id=parent.id,
                folder_id=folder.id,
                filename=f"IMG_{position:04d}.jpg",
                storage_key=f"commercial/IMG_{position:04d}.jpg",
            )
            db.add(photo)
            db.flush()
            order = SaleOrder(
                derived_gallery_id=private.id,
                client_id=client.id,
                payment_status=payment_status,
                total_cents=position * 700,
                confirmed_at=now() if payment_status == "confirmed" else None,
                checkout_key=f"commercial-state-{position}",
                price_rule_snapshot={"unit_price_cents": position * 700},
            )
            db.add(order)
            db.flush()
            db.add(
                SaleOrderItem(
                    sale_order_id=order.id,
                    photo_asset_id=photo.id,
                    filename_snapshot=photo.filename,
                    unit_price_cents=position * 700,
                )
            )
            order_ids.append(order.id)
        db.add(
            AuditEvent(
                event="commercial.fixture",
                subject=str(parent.id),
            )
        )
        db.commit()
        parent_id, client_id = parent.id, client.id

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE sale_order SET derived_gallery_name_snapshot = '', "
                "parent_gallery_name_snapshot = '', client_name_snapshot = NULL, "
                "client_phone_snapshot = NULL WHERE id IN (:one, :two, :three)"
            ),
            {
                "one": order_ids[0].hex,
                "two": order_ids[1].hex,
                "three": order_ids[2].hex,
            },
        )
        connection.execute(
            text(
                "UPDATE sale_order_item SET filename_snapshot = '' "
                "WHERE sale_order_id IN (:one, :two, :three)"
            ),
            {
                "one": order_ids[0].hex,
                "two": order_ids[1].hex,
                "three": order_ids[2].hex,
            },
        )

    with SessionLocal() as db:
        before = {
            order.id: (
                order.payment_status,
                order.total_cents,
                order.client_id,
                order.confirmed_at,
                order.price_rule_snapshot,
            )
            for order in db.scalars(select(SaleOrder).where(SaleOrder.id.in_(order_ids)))
        }
        audit_count = db.scalar(select(func.count()).select_from(AuditEvent))
        first = materialize_commercial_history(db, parent_gallery_id=parent_id, client_id=client_id)
        second = materialize_commercial_history(
            db, parent_gallery_id=parent_id, client_id=client_id
        )
        db.commit()
        after = {
            order.id: (
                order.payment_status,
                order.total_cents,
                order.client_id,
                order.confirmed_at,
                order.price_rule_snapshot,
            )
            for order in db.scalars(select(SaleOrder).where(SaleOrder.id.in_(order_ids)))
        }
        assert first.orders_updated == 3
        assert first.items_updated == 3
        assert second.orders_updated == 0
        assert second.items_updated == 0
        assert before == after
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == audit_count


def test_historical_media_is_minimal_deterministic_and_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    derivative_root = tmp_path / "derivatives"
    history_root = tmp_path / "history"
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivative_root))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))

    with SessionLocal() as db:
        parent = ParentGallery(name="Galeria histórica")
        client = Client(full_name="Cliente histórica mídia", phone_e164="+5511999999100")
        db.add_all([parent, client])
        db.flush()
        folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Histórico",
            status="released",
        )
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=client.id,
            name="Privada histórica mídia",
        )
        db.add_all([folder, private])
        db.flush()

        photos = []
        for position in range(4):
            photo = PhotoAsset(
                parent_gallery_id=parent.id,
                folder_id=folder.id,
                filename=f"pessoa-secreta-{position}.jpg",
                storage_key=f"operational/{position}.jpg",
            )
            db.add(photo)
            db.flush()
            derivative_key = f"{photo.id}/client_preview.jpg"
            db.add(
                MediaDerivative(
                    photo_asset_id=photo.id,
                    variant="client_preview",
                    relative_path=derivative_key,
                    status="ready",
                    width=800,
                    height=600,
                )
            )
            preview_path = derivative_root / derivative_key
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            preview_path.write_bytes(f"preview-protegida-{position}".encode())
            photos.append(photo)

        source_path = source_root / photos[0].storage_key
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(b"entrega-final-confirmada")

        confirmed_items = []
        for position, photo in enumerate(photos[:2]):
            order = SaleOrder(
                derived_gallery_id=private.id,
                client_id=client.id,
                payment_status="confirmed",
                total_cents=1000,
                confirmed_at=now(),
                checkout_key=f"history-confirmed-{position}",
            )
            db.add(order)
            db.flush()
            item = SaleOrderItem(
                sale_order_id=order.id,
                photo_asset_id=photo.id,
                filename_snapshot=photo.filename,
                unit_price_cents=1000,
            )
            db.add(item)
            db.flush()
            confirmed_items.append(item)

        pending = SaleOrder(
            derived_gallery_id=private.id,
            client_id=client.id,
            payment_status="pending",
            total_cents=500,
            checkout_key="history-pending",
        )
        db.add(pending)
        db.flush()
        db.add(
            SaleOrderItem(
                sale_order_id=pending.id,
                photo_asset_id=photos[2].id,
                filename_snapshot=photos[2].filename,
                unit_price_cents=500,
            )
        )
        db.add(
            CommercialHistoryMedia(
                sale_order_item_id=confirmed_items[1].id,
                delivery_reference="provider://delivery-safe-reference",
                status="pending",
            )
        )
        db.commit()
        parent_id = parent.id
        first_item_id, referenced_item_id = (
            confirmed_items[0].id,
            confirmed_items[1].id,
        )

    with SessionLocal() as db:
        first = prepare_confirmed_historical_media(db, parent_gallery_id=parent_id)
        db.commit()
        assert first.confirmed_items == 2
        assert first.prepared_items == 2
        assert first.delivery_bytes == len(b"entrega-final-confirmada")
        manifests = list(db.scalars(select(CommercialHistoryMedia)))
        assert len(manifests) == 2
        assert all(manifest.status == "ready" for manifest in manifests)
        assert all(
            "Cliente" not in manifest.preview_storage_key
            and "+55" not in manifest.preview_storage_key
            and "pessoa-secreta" not in manifest.preview_storage_key
            for manifest in manifests
        )
        copied = next(
            manifest for manifest in manifests if manifest.sale_order_item_id == first_item_id
        )
        referenced = next(
            manifest for manifest in manifests if manifest.sale_order_item_id == referenced_item_id
        )
        assert copied.delivery_storage_key == f"items/{first_item_id}/delivery.jpg"
        assert referenced.delivery_storage_key is None
        assert referenced.delivery_reference == "provider://delivery-safe-reference"
        assert not (history_root / f"items/{referenced_item_id}/delivery.jpg").exists()

        second = prepare_confirmed_historical_media(db, parent_gallery_id=parent_id)
        assert second.reused_items == 2
        assert second.prepared_items == 0
        assert len(list(db.scalars(select(CommercialHistoryMedia)))) == 2

        (history_root / copied.preview_storage_key).write_bytes(b"arquivo-divergente")
        with pytest.raises(HistoricalMediaConflict):
            prepare_confirmed_historical_media(db, parent_gallery_id=parent_id)


def test_admin_order_queries_use_snapshots_after_operational_removal() -> None:
    parent_id, gallery_id, photo_id, order_id, _item_id = create_commercial_fixture()
    with SessionLocal() as db:
        folder_id = db.get(PhotoAsset, photo_id).folder_id
        client_id = db.get(SaleOrder, order_id).client_id
        db.delete(db.get(PhotoAsset, photo_id))
        db.commit()
        db.delete(db.get(DerivedGallery, gallery_id))
        db.commit()
        db.delete(db.get(PhotoFolder, folder_id))
        db.delete(db.get(ParentGallery, parent_id))
        db.commit()
        assert db.get(SaleOrder, order_id).derived_gallery_id is None
        assert (
            db.scalar(
                select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order_id)
            ).photo_asset_id
            is None
        )

    with TestClient(app) as client:
        authenticate_admin(client)
        purchases = client.get(
            "/admin/purchases",
            params={
                "parent_gallery_id": str(parent_id),
                "client_id": str(client_id),
            },
        )
        assert purchases.status_code == 200
        payload = purchases.json()
        assert payload["totals"] == {"orders": 1, "amount_cents": 900}
        assert payload["orders"][0]["gallery_name"] == "Galeria privada original"
        assert payload["orders"][0]["parent_gallery_name"] == ("Galeria pública original")
        assert payload["orders"][0]["gallery_status_label"] == "Galeria removida"
        assert payload["orders"][0]["items"][0] == {
            "photo_id": str(photo_id),
            "name": "IMG_0100.jpg",
            "preview_url": None,
            "operational_media_available": False,
        }
        assert client.get("/admin/purchases", params={"client_id": str(uuid4())}).json()[
            "totals"
        ] == {"orders": 0, "amount_cents": 0}

        gallery_orders = client.get(f"/admin/derived-galleries/{gallery_id}/orders")
        assert gallery_orders.status_code == 200
        assert gallery_orders.json()["gallery"] == {
            "id": str(gallery_id),
            "name": "Galeria privada original",
            "status_label": "Galeria removida",
            "removed": True,
        }
        assert gallery_orders.json()["totals"] == {
            "orders": 1,
            "amount_cents": 900,
        }


def test_client_library_uses_isolated_historical_media_after_gallery_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_root = tmp_path / "commercial-history"
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))
    owner_phone = "+5511999999810"
    other_phone = "+5511999999811"
    private_id = uuid4()
    parent_id = uuid4()
    photo_id = uuid4()
    preview = b"preview-historica-protegida"
    delivery = b"arquivo-historico-entregue"

    with SessionLocal() as db:
        owner = Client(full_name="Cliente proprietária", phone_e164=owner_phone)
        other = Client(full_name="Outra cliente", phone_e164=other_phone)
        db.add_all([owner, other])
        db.flush()
        order = SaleOrder(
            derived_gallery_id=None,
            client_id=owner.id,
            derived_gallery_id_snapshot=private_id,
            derived_gallery_name_snapshot="Galeria privada preservada",
            parent_gallery_id_snapshot=parent_id,
            parent_gallery_name_snapshot="Galeria pública preservada",
            client_name_snapshot=owner.full_name,
            client_phone_snapshot=owner.phone_e164,
            payment_status="confirmed",
            total_cents=1700,
            confirmed_at=now(),
        )
        db.add(order)
        db.flush()
        item = SaleOrderItem(
            sale_order_id=order.id,
            photo_asset_id=None,
            photo_asset_id_snapshot=photo_id,
            filename_snapshot="IMG_0170.jpg",
            checksum_sha256_snapshot=sha256(delivery).hexdigest(),
            unit_price_cents=1700,
        )
        db.add(item)
        db.flush()
        preview_key = f"items/{item.id}/preview.jpg"
        delivery_key = f"items/{item.id}/delivery.jpg"
        db.add(
            CommercialHistoryMedia(
                sale_order_item_id=item.id,
                preview_storage_key=preview_key,
                delivery_storage_key=delivery_key,
                checksum_sha256=sha256(preview).hexdigest(),
                media_type="image/jpeg",
                size_bytes=len(preview),
                status="ready",
            )
        )
        db.commit()
        order_id, item_id = order.id, item.id

    for key, content in ((preview_key, preview), (delivery_key, delivery)):
        target = history_root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    with TestClient(app) as client:
        authenticate_client(client, owner_phone)
        response = client.get("/library/purchases")
        assert response.status_code == 200
        assert response.json()["orders"] == [
            {
                "id": str(order_id),
                "gallery_name": "Galeria privada preservada",
                "parent_gallery_name": "Galeria pública preservada",
                "gallery_status_label": "Galeria removida",
                "gallery_removed": True,
                "confirmed_at": response.json()["orders"][0]["confirmed_at"],
                "total_cents": 1700,
                "items": [
                    {
                        "item_id": str(item_id),
                        "photo_id": str(photo_id),
                        "name": "IMG_0170.jpg",
                        "preview_url": f"/library/history/items/{item_id}/preview",
                        "delivery_url": f"/library/history/items/{item_id}/delivery",
                        "delivery_reference_available": False,
                    }
                ],
            }
        ]
        preview_response = client.get(f"/library/history/items/{item_id}/preview")
        assert preview_response.status_code == 200
        assert preview_response.content == preview
        assert preview_response.headers["cache-control"] == "private, no-store"
        delivery_response = client.get(f"/library/history/items/{item_id}/delivery")
        assert delivery_response.status_code == 200
        assert delivery_response.content == delivery
        assert delivery_response.headers["cache-control"] == "private, no-store"

        client.cookies.clear()
        authenticate_client(client, other_phone)
        assert client.get("/library/purchases").json() == {"orders": []}
        assert client.get(f"/library/history/items/{item_id}/preview").status_code == 403
        assert client.get(f"/library/history/items/{item_id}/delivery").status_code == 403


def test_commercial_retention_requires_explicit_policy_and_preserves_accounting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_root = tmp_path / "commercial-retention"
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))
    monkeypatch.delenv("COMMERCIAL_HISTORY_MEDIA_RETENTION_DAYS", raising=False)
    instant = datetime(2026, 8, 31, 12, tzinfo=UTC)
    client_id = uuid4()
    parent_id = uuid4()
    private_id = uuid4()
    order_ids: list[UUID] = []
    item_ids: list[UUID] = []

    with SessionLocal() as db:
        db.add(
            Client(
                id=client_id,
                full_name="Cliente a minimizar",
                phone_e164="+5511999999820",
            )
        )
        for index, age_days in enumerate((60, 10)):
            order = SaleOrder(
                derived_gallery_id=None,
                client_id=client_id,
                derived_gallery_id_snapshot=private_id,
                derived_gallery_name_snapshot="Galeria comercial preservada",
                parent_gallery_id_snapshot=parent_id,
                parent_gallery_name_snapshot="Origem comercial preservada",
                client_name_snapshot="Cliente a minimizar",
                client_phone_snapshot="+5511999999820",
                payment_status="confirmed",
                total_cents=1200 + index,
                confirmed_at=instant - timedelta(days=age_days),
            )
            db.add(order)
            db.flush()
            item = SaleOrderItem(
                sale_order_id=order.id,
                photo_asset_id=None,
                photo_asset_id_snapshot=uuid4(),
                filename_snapshot=f"IMG_{index}.jpg",
                unit_price_cents=1200 + index,
            )
            db.add(item)
            db.flush()
            preview_key = f"items/{item.id}/preview.jpg"
            delivery_key = f"items/{item.id}/delivery.jpg"
            db.add(
                CommercialHistoryMedia(
                    sale_order_item_id=item.id,
                    preview_storage_key=preview_key,
                    delivery_storage_key=delivery_key,
                    checksum_sha256="a" * 64,
                    media_type="image/jpeg",
                    size_bytes=8,
                    status="ready",
                )
            )
            for key in (preview_key, delivery_key):
                target = history_root / key
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"historico")
            order_ids.append(order.id)
            item_ids.append(item.id)
        db.commit()

    assert commercial_retention_policy().media_retention_days is None
    with SessionLocal() as db:
        assert apply_commercial_media_retention(db, instant=instant).purged_items == 0
        db.commit()
    assert all((history_root / f"items/{item_id}/preview.jpg").is_file() for item_id in item_ids)

    monkeypatch.setenv("COMMERCIAL_HISTORY_MEDIA_RETENTION_DAYS", "trinta")
    with pytest.raises(CommercialRetentionConfigurationError):
        commercial_retention_policy()
    monkeypatch.setenv("COMMERCIAL_HISTORY_MEDIA_RETENTION_DAYS", "30")
    with SessionLocal() as db:
        report = apply_commercial_media_retention(db, instant=instant)
        db.commit()
        assert report.eligible_items == 1
        assert report.purged_items == 1
        assert report.removed_files == 2
        old_manifest = db.scalar(
            select(CommercialHistoryMedia).where(
                CommercialHistoryMedia.sale_order_item_id == item_ids[0]
            )
        )
        recent_manifest = db.scalar(
            select(CommercialHistoryMedia).where(
                CommercialHistoryMedia.sale_order_item_id == item_ids[1]
            )
        )
        assert old_manifest.status == "purged"
        assert old_manifest.preview_storage_key is None
        assert old_manifest.delivery_storage_key is None
        assert old_manifest.retention_expires_at.replace(tzinfo=UTC) == (
            instant - timedelta(days=30)
        )
        assert recent_manifest.status == "ready"
        assert db.get(SaleOrder, order_ids[0]).total_cents == 1200
        assert db.get(SaleOrder, order_ids[0]).parent_gallery_name_snapshot == (
            "Origem comercial preservada"
        )
        assert db.get(SaleOrderItem, item_ids[0]).filename_snapshot == "IMG_0.jpg"
        assert apply_commercial_media_retention(db, instant=instant).purged_items == 0
    assert not (history_root / f"items/{item_ids[0]}/preview.jpg").exists()
    assert (history_root / f"items/{item_ids[1]}/preview.jpg").is_file()


def test_commercial_pii_minimization_is_authorized_auditable_and_idempotent() -> None:
    _parent_id, _gallery_id, _photo_id, order_id, item_id = create_commercial_fixture()
    with SessionLocal() as db:
        order = db.get(SaleOrder, order_id)
        client_id = order.client_id
        original_total = order.total_cents
        original_gallery = order.parent_gallery_name_snapshot
        original_filename = db.get(SaleOrderItem, item_id).filename_snapshot
        with pytest.raises(CommercialPiiMinimizationNotAuthorized):
            minimize_client_commercial_pii(db, client_id=client_id, permitted=False)
        assert order.client_name_snapshot == "Cliente histórica"
        assert order.client_phone_snapshot == "+5511999999800"

        assert minimize_client_commercial_pii(db, client_id=client_id, permitted=True) == 1
        db.commit()
        db.refresh(order)
        assert order.client_name_snapshot is None
        assert order.client_phone_snapshot is None
        assert order.pii_minimized_at is not None
        assert order.total_cents == original_total
        assert order.parent_gallery_name_snapshot == original_gallery
        assert db.get(SaleOrderItem, item_id).filename_snapshot == original_filename
        assert db.get(Client, client_id) is not None
        event = db.scalar(
            select(AuditEvent).where(AuditEvent.event == "commercial_history.pii_minimized")
        )
        assert str(client_id) in event.subject
        assert "Cliente histórica" not in event.subject
        assert "+55" not in event.subject
        assert minimize_client_commercial_pii(db, client_id=client_id, permitted=True) == 0


def create_commercial_fixture(*, payment_status: str = "confirmed") -> tuple:
    with SessionLocal() as db:
        client = Client(full_name="Cliente histórica", phone_e164="+5511999999800")
        parent = ParentGallery(name="Galeria pública original")
        db.add_all([client, parent])
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote", status="released")
        gallery = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=client.id,
            name="Galeria privada original",
        )
        db.add_all([folder, gallery])
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="IMG_0100.jpg",
            storage_key="fixture/IMG_0100.jpg",
        )
        db.add(photo)
        db.flush()
        order = SaleOrder(
            derived_gallery_id=gallery.id,
            client_id=client.id,
            payment_status=payment_status,
            total_cents=900,
            confirmed_at=now() if payment_status == "confirmed" else None,
        )
        db.add(order)
        db.flush()
        item = SaleOrderItem(
            sale_order_id=order.id,
            photo_asset_id=photo.id,
            filename_snapshot=photo.filename,
            unit_price_cents=900,
        )
        db.add(item)
        db.commit()
        return parent.id, gallery.id, photo.id, order.id, item.id


def test_snapshot_backfill_is_idempotent_and_preserves_existing_values() -> None:
    parent_id, gallery_id, _photo_id, order_id, item_id = create_commercial_fixture()
    with SessionLocal() as db:
        order = db.get(SaleOrder, order_id)
        item = db.get(SaleOrderItem, item_id)
        db.get(ParentGallery, parent_id).name = "Galeria pública atualizada"
        db.get(DerivedGallery, gallery_id).name = "Galeria privada atualizada"
        order.derived_gallery_name_snapshot = "Nome privado congelado"
        order.parent_gallery_name_snapshot = ""
        item.filename_snapshot = ""
        db.commit()

    with SessionLocal() as db:
        first = backfill_commercial_snapshots(db)
        order = db.get(SaleOrder, order_id)
        item = db.get(SaleOrderItem, item_id)
        assert first.orders_updated == 1
        assert first.items_updated == 1
        assert first.gaps == []
        assert order.derived_gallery_name_snapshot == "Nome privado congelado"
        assert order.parent_gallery_name_snapshot == "Galeria pública atualizada"
        assert item.filename_snapshot == "IMG_0100.jpg"
        second = backfill_commercial_snapshots(db)
        assert second.orders_updated == 0
        assert second.items_updated == 0
        assert second.gaps == []


def test_snapshot_backfill_blocks_confirmed_item_without_any_media() -> None:
    _parent_id, _gallery_id, photo_id, _order_id, item_id = create_commercial_fixture()
    with SessionLocal() as db:
        db.delete(db.get(PhotoAsset, photo_id))
        db.commit()

    with SessionLocal() as db:
        with pytest.raises(CommercialHistoryGap) as captured:
            backfill_commercial_snapshots(db, block_on_confirmed_media_gap=True)
        assert any(gap["kind"] == "confirmed_media" for gap in captured.value.report.gaps)
        db.add(
            CommercialHistoryMedia(
                sale_order_item_id=item_id,
                preview_storage_key=f"history/{item_id}/preview.jpg",
                checksum_sha256="a" * 64,
                media_type="image/jpeg",
                size_bytes=1024,
                status="ready",
            )
        )
        db.commit()
        report = backfill_commercial_snapshots(db, block_on_confirmed_media_gap=True)
        assert not any(gap["kind"] == "confirmed_media" for gap in report.gaps)


def test_lifecycle_migration_is_additive_and_reversible(tmp_path: Path) -> None:
    database = tmp_path / "gallery-lifecycle.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    backend = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "DATABASE_URL": database_url}

    def alembic(*arguments: str) -> None:
        result = run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=backend,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    alembic("upgrade", "head")
    migrated_engine = create_engine(database_url)
    inspector = inspect(migrated_engine)
    assert "gallery_lifecycle_operation" in inspector.get_table_names()
    assert "commercial_history_media" in inspector.get_table_names()
    alembic("downgrade", "20260830_0017")
    inspector = inspect(migrated_engine)
    assert "gallery_lifecycle_operation" not in inspector.get_table_names()
    assert "commercial_history_media" not in inspector.get_table_names()


def test_retained_private_origin_migration_refuses_lossy_downgrade(
    tmp_path: Path,
) -> None:
    database = tmp_path / "retained-private-origin.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    backend = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "DATABASE_URL": database_url}

    def alembic(*arguments: str):
        return run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=backend,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    upgraded = alembic("upgrade", "head")
    assert upgraded.returncode == 0, f"{upgraded.stdout}\n{upgraded.stderr}"
    migrated_engine = create_engine(database_url)
    with Session(migrated_engine) as db:
        db.add(
            ParentGallery(
                name="Origem interna preservada",
                active=False,
                lifecycle_status="deleted",
            )
        )
        db.commit()

    refused = alembic("downgrade", "20260831_0028")
    assert refused.returncode != 0
    assert "Downgrade recusado" in refused.stderr

    with migrated_engine.begin() as connection:
        connection.execute(text("DELETE FROM parent_gallery WHERE lifecycle_status = 'deleted'"))
    downgraded = alembic("downgrade", "20260831_0028")
    assert downgraded.returncode == 0, f"{downgraded.stdout}\n{downgraded.stderr}"


def test_commercial_snapshot_migration_preserves_history_after_operational_delete(
    tmp_path: Path,
) -> None:
    database = tmp_path / "commercial-snapshots.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    backend = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "DATABASE_URL": database_url}

    def alembic(*arguments: str) -> None:
        result = run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=backend,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    alembic("upgrade", "20260831_0018")
    migrated_engine = create_engine(database_url)
    client_id, parent_id, folder_id, photo_id, gallery_id, reference_id, order_id, item_id = (
        uuid4() for _ in range(8)
    )
    timestamp = datetime.now(UTC)
    with migrated_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO client (id, full_name, phone_e164) "
                "VALUES (:id, 'Cliente histórica', '+5511999999900')"
            ),
            {"id": client_id.hex},
        )
        connection.execute(
            text(
                "INSERT INTO parent_gallery (id, name, active, created_at) "
                "VALUES (:id, 'Galeria pública histórica', 1, :created_at)"
            ),
            {"id": parent_id.hex, "created_at": timestamp},
        )
        connection.execute(
            text(
                """
                INSERT INTO photo_folder
                    (id, parent_gallery_id, name, status, position, created_at, updated_at)
                VALUES (:id, :parent, 'Lote', 'released', 0, :created_at, :updated_at)
                """
            ),
            {
                "id": folder_id.hex,
                "parent": parent_id.hex,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO photo_asset
                    (id, parent_gallery_id, folder_id, filename, storage_key,
                     available, created_at)
                VALUES (:id, :parent, :folder, 'IMG_0001.jpg', 'legacy/IMG_0001.jpg',
                        1, :created_at)
                """
            ),
            {
                "id": photo_id.hex,
                "parent": parent_id.hex,
                "folder": folder_id.hex,
                "created_at": timestamp,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO derived_gallery
                    (id, parent_gallery_id, client_id, name, access_enabled,
                     favorites_enabled, comments_enabled, created_at)
                VALUES (:id, :parent, :client, 'Privada histórica', 1, 0, 0, :created_at)
                """
            ),
            {
                "id": gallery_id.hex,
                "parent": parent_id.hex,
                "client": client_id.hex,
                "created_at": timestamp,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO derived_gallery_photo
                    (id, derived_gallery_id, photo_asset_id, created_at)
                VALUES (:id, :gallery, :photo, :created_at)
                """
            ),
            {
                "id": reference_id.hex,
                "gallery": gallery_id.hex,
                "photo": photo_id.hex,
                "created_at": timestamp,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO sale_order
                    (id, derived_gallery_id, client_id, payment_status, total_cents,
                     confirmed_at, created_at)
                VALUES (:id, :gallery, :client, 'confirmed', 1500, :confirmed_at, :created_at)
                """
            ),
            {
                "id": order_id.hex,
                "gallery": gallery_id.hex,
                "client": client_id.hex,
                "confirmed_at": timestamp,
                "created_at": timestamp,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO sale_order_item
                    (id, sale_order_id, photo_asset_id, filename_snapshot, unit_price_cents)
                VALUES (:id, :order_id, :photo_id, 'IMG_0001.jpg', 1500)
                """
            ),
            {"id": item_id.hex, "order_id": order_id.hex, "photo_id": photo_id.hex},
        )

    alembic("upgrade", "head")
    with migrated_engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        order_snapshot = connection.execute(
            text(
                """
                SELECT derived_gallery_id_snapshot, derived_gallery_name_snapshot,
                       parent_gallery_id_snapshot, parent_gallery_name_snapshot
                FROM sale_order WHERE id = :id
                """
            ),
            {"id": order_id.hex},
        ).one()
        item_snapshot = connection.execute(
            text(
                "SELECT photo_asset_id_snapshot, filename_snapshot "
                "FROM sale_order_item WHERE id = :id"
            ),
            {"id": item_id.hex},
        ).one()
        reference_origin = connection.execute(
            text("SELECT origin FROM derived_gallery_photo WHERE id = :reference_id"),
            {"reference_id": reference_id.hex},
        ).scalar_one()
        verified_phone = connection.execute(
            text(
                "SELECT phone_e164, active, verified_at "
                "FROM client_phone WHERE client_id = :client_id"
            ),
            {"client_id": client_id.hex},
        ).one()
        access_mode = connection.execute(
            text("SELECT access_mode FROM parent_gallery WHERE id = :parent_id"),
            {"parent_id": parent_id.hex},
        ).scalar_one()
        connection.execute(
            text("DELETE FROM derived_gallery_photo WHERE id = :id"),
            {"id": reference_id.hex},
        )
        connection.execute(text("DELETE FROM photo_asset WHERE id = :id"), {"id": photo_id.hex})
        connection.execute(
            text("DELETE FROM derived_gallery WHERE id = :id"), {"id": gallery_id.hex}
        )
        operational_links = connection.execute(
            text("SELECT derived_gallery_id FROM sale_order WHERE id = :order_id"),
            {"order_id": order_id.hex},
        ).scalar_one()
        operational_photo = connection.execute(
            text("SELECT photo_asset_id FROM sale_order_item WHERE id = :item_id"),
            {"item_id": item_id.hex},
        ).scalar_one()

    assert order_snapshot == (
        gallery_id.hex,
        "Privada histórica",
        parent_id.hex,
        "Galeria pública histórica",
    )
    assert item_snapshot == (photo_id.hex, "IMG_0001.jpg")
    assert reference_origin == "admin"
    assert verified_phone[0] == "+5511999999900"
    assert bool(verified_phone[1]) is True
    assert verified_phone[2] is not None
    assert access_mode == "invite_only"
    assert operational_links is None
    assert operational_photo is None


def test_transition_characterization_preserves_commercial_snapshots_after_private_removal() -> None:
    with SessionLocal() as db:
        client = Client(full_name="Cliente original", phone_e164="+5511999999701")
        parent = ParentGallery(name="Origem original")
        db.add_all((client, parent))
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Lote", status="released")
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=client.id,
            name="Privada original",
        )
        db.add_all((folder, private))
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="IMG_0007.jpg",
            storage_key="origem/IMG_0007.jpg",
        )
        db.add(photo)
        db.flush()
        order = SaleOrder(
            derived_gallery_id=private.id,
            client_id=client.id,
            payment_status="confirmed",
            total_cents=700,
            confirmed_at=now(),
            price_rule_snapshot={"unit_price_cents": 700},
            pix_copy_paste_snapshot="pix-original",
        )
        db.add(order)
        db.flush()
        item = SaleOrderItem(
            sale_order_id=order.id,
            photo_asset_id=photo.id,
            unit_price_cents=700,
        )
        db.add(item)
        db.commit()
        order_id = order.id

        parent.name = "Origem alterada"
        private.name = "Privada alterada"
        client.full_name = "Cliente alterada"
        db.commit()
        order = db.get(SaleOrder, order_id)
        order.derived_gallery_id = None
        db.flush()
        db.delete(private)
        db.commit()

        preserved = db.get(SaleOrder, order_id)
        assert preserved is not None
        assert preserved.derived_gallery_id is None
        assert preserved.derived_gallery_name_snapshot == "Privada original"
        assert preserved.parent_gallery_name_snapshot == "Origem original"
        assert preserved.client_name_snapshot == "Cliente original"
        assert preserved.price_rule_snapshot == {"unit_price_cents": 700}
        assert preserved.pix_copy_paste_snapshot == "pix-original"


def test_transition_characterization_legacy_private_invite_stores_only_hash() -> None:
    with SessionLocal() as db:
        client = Client(full_name="Cliente convite", phone_e164="+5511999999702")
        parent = ParentGallery(name="Origem convite")
        db.add_all((client, parent))
        db.flush()
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=client.id,
            name="Privada convite",
        )
        db.add(private)
        db.flush()
        capability, token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            derived_gallery_id=private.id,
            client_id=client.id,
            scope="private_invite",
        )
        db.commit()

        stored = db.get(GalleryAccessCapability, capability.id)
        assert stored is not None
        assert stored.token_hash == token_hash(token)
        assert token not in stored.token_hash
        assert resolve_gallery_capability(db, token).id == capability.id
        assert resolve_gallery_capability(db, f"{token}-adulterado") is None


def test_transition_characterization_owner_authorization_is_isolated_by_client() -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Cliente titular", phone_e164="+5511999999703")
        other = Client(full_name="Outra cliente", phone_e164="+5511999999704")
        parent = ParentGallery(name="Origem isolada")
        db.add_all((owner, other, parent))
        db.flush()
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada isolada",
        )
        db.add(private)
        db.commit()

        assert derived_gallery_for_client(db, private.id, owner.id).id == private.id
        with pytest.raises(HTTPException) as exc_info:
            derived_gallery_for_client(db, private.id, other.id)
        assert getattr(exc_info.value, "status_code", None) == 403


def test_membership_model_enforces_origin_client_uniqueness_and_gallery_origin() -> None:
    with SessionLocal() as db:
        client = Client(full_name="Cliente membro", phone_e164="+5511999999705")
        second_owner = Client(full_name="Segunda titular", phone_e164="+5511999999706")
        other_owner = Client(full_name="Outra titular", phone_e164="+5511999999707")
        first_parent = ParentGallery(name="Primeira origem")
        other_parent = ParentGallery(name="Outra origem")
        db.add_all((client, second_owner, other_owner, first_parent, other_parent))
        db.flush()
        first_private = DerivedGallery(
            parent_gallery_id=first_parent.id,
            client_id=client.id,
            name="Primeira privada",
        )
        second_private = DerivedGallery(
            parent_gallery_id=first_parent.id,
            client_id=second_owner.id,
            name="Segunda privada",
        )
        other_private = DerivedGallery(
            parent_gallery_id=other_parent.id,
            client_id=other_owner.id,
            name="Privada de outra origem",
        )
        db.add_all((first_private, second_private, other_private))
        db.flush()
        db.add(
            DerivedGalleryMembership(
                derived_gallery_id=first_private.id,
                parent_gallery_id=first_parent.id,
                client_id=client.id,
            )
        )
        db.commit()

        db.add(
            DerivedGalleryMembership(
                derived_gallery_id=second_private.id,
                parent_gallery_id=first_parent.id,
                client_id=client.id,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.add(
            DerivedGalleryMembership(
                derived_gallery_id=other_private.id,
                parent_gallery_id=first_parent.id,
                client_id=uuid4(),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_private_gallery_factory_supports_legacy_and_shared_states() -> None:
    with SessionLocal() as db:
        _, legacy, legacy_clients = create_private_gallery_fixture(
            db,
            label="Legado",
            phones=("+5511999999710",),
            with_memberships=False,
        )
        _, shared, shared_clients = create_private_gallery_fixture(
            db,
            label="Compartilhado",
            phones=("+5511999999711", "+5511999999712"),
            with_memberships=True,
        )
        db.commit()

        assert legacy.client_id == legacy_clients[0].id
        assert db.scalar(
            select(func.count(DerivedGalleryMembership.id)).where(
                DerivedGalleryMembership.derived_gallery_id == legacy.id
            )
        ) == 0
        assert db.scalar(
            select(func.count(DerivedGalleryMembership.id)).where(
                DerivedGalleryMembership.derived_gallery_id == shared.id
            )
        ) == len(shared_clients) == 2
