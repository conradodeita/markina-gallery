from datetime import timedelta
from uuid import UUID

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from app.auth import (
    AdminUser,
    AuditEvent,
    AuthChallenge,
    Base,
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    DerivedGalleryPhotoOrigin,
    GalleryAccessCapability,
    GalleryMembershipNotificationOutbox,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    PhotoAsset,
    PhotoComment,
    PhotoFavorite,
    PhotoFolder,
    PhotoSelection,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    engine,
    now,
    password_hasher,
    token_hash,
)
from app.gallery_access import (
    GalleryCapabilityConfigurationError,
    capability_hash,
    issue_gallery_capability,
    reconstruct_gallery_capability_token,
    resolve_gallery_capability,
    rotate_gallery_capability,
    validate_gallery_capability_runtime_configuration,
    validate_gallery_capability_signing_configuration,
)
from app.main import app
from app.membership_notifications import (
    enqueue_membership_notification,
    process_next_membership_notification,
)
from app.private_derivation import ensure_private_photo_reference
from app.private_membership import (
    block_private_membership,
    ensure_private_membership,
)


@pytest.fixture(autouse=True)
def clean_database(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GALLERY_CAPABILITY_SIGNING_KEY", raising=False)
    monkeypatch.delenv("AUTH_PII_FINGERPRINT_SALT", raising=False)
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


def test_signing_configuration_requires_dedicated_strong_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    with pytest.raises(GalleryCapabilityConfigurationError, match="32 bytes"):
        validate_gallery_capability_signing_configuration()
    monkeypatch.setenv("GALLERY_CAPABILITY_SIGNING_KEY", "a" * 32)
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "a" * 32)
    with pytest.raises(GalleryCapabilityConfigurationError, match="dedicada"):
        validate_gallery_capability_signing_configuration()

    monkeypatch.delenv("GALLERY_CAPABILITY_SIGNING_KEY")
    with pytest.raises(GalleryCapabilityConfigurationError):
        validate_gallery_capability_runtime_configuration()


def test_signed_capability_is_reconstructible_tamper_evident_and_hash_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GALLERY_CAPABILITY_SIGNING_KEY", "signed-gallery-key-for-tests-0001")
    with SessionLocal() as db:
        parent = ParentGallery(name="Origem assinada")
        db.add(parent)
        db.flush()
        capability, token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            scope="public_gallery",
            reconstructible=True,
        )
        db.commit()

        assert token.startswith(f"gc1.{capability.id}.1.")
        assert reconstruct_gallery_capability_token(capability) == token
        assert capability.token_hash == capability_hash(token)
        assert token not in capability.token_hash
        assert resolve_gallery_capability(db, token).id == capability.id
        assert resolve_gallery_capability(db, f"{token[:-1]}x") is None


def test_signed_rotation_invalidates_old_token_and_increments_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GALLERY_CAPABILITY_SIGNING_KEY", "signed-gallery-key-for-tests-0002")
    with SessionLocal() as db:
        parent = ParentGallery(name="Origem rotacionada")
        db.add(parent)
        db.flush()
        original, original_token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            scope="public_gallery",
            reconstructible=True,
        )
        replacement, replacement_token = rotate_gallery_capability(db, original)
        db.commit()

        assert original.status == "rotated"
        assert replacement.token_version == 2
        assert replacement.rotated_from_id == original.id
        assert resolve_gallery_capability(db, original_token) is None
        assert resolve_gallery_capability(db, replacement_token).id == replacement.id


def test_legacy_token_remains_resolvable_and_private_link_has_no_bound_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GALLERY_CAPABILITY_SIGNING_KEY", "signed-gallery-key-for-tests-0003")
    with SessionLocal() as db:
        owner = Client(full_name="Titular", phone_e164="+5511999999401")
        parent = ParentGallery(name="Origem compatível")
        db.add_all((owner, parent))
        db.flush()
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada compatível",
        )
        db.add(private)
        db.flush()
        legacy, legacy_token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            derived_gallery_id=private.id,
            client_id=owner.id,
            scope="private_invite",
            expires_at=now() + timedelta(hours=1),
        )
        shared, shared_token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            derived_gallery_id=private.id,
            scope="private_gallery_link",
            reconstructible=True,
        )
        db.commit()

        assert legacy.token_mode == "legacy_random"
        assert resolve_gallery_capability(db, legacy_token).id == legacy.id
        assert shared.client_id is None
        assert reconstruct_gallery_capability_token(shared) == shared_token
        assert resolve_gallery_capability(db, shared_token).id == shared.id

        duplicate = GalleryAccessCapability(
            parent_gallery_id=parent.id,
            derived_gallery_id=private.id,
            scope="private_gallery_link",
            token_hash="f" * 64,
            token_mode="signed_v1",
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.commit()


def _authenticate_admin(client: TestClient) -> None:
    with SessionLocal() as db:
        admin = AdminUser(
            email="links@markina.test",
            password_hash=password_hasher.hash("senha-segura"),
            email_verified=True,
            totp_secret=pyotp.random_base32(),
        )
        db.add(admin)
        db.commit()
        secret = admin.totp_secret
    challenge = client.post(
        "/auth/admin/password",
        json={"email": "links@markina.test", "password": "senha-segura"},
    ).json()["challenge_id"]
    assert client.post(
        "/auth/admin/totp",
        json={"challenge_id": challenge, "code": pyotp.TOTP(secret).now()},
    ).status_code == 200


def _verify_client_link(
    client: TestClient,
    *,
    full_name: str,
    phone: str,
    access_token: str,
) -> tuple[int, dict[str, str]]:
    challenge_response = client.post(
        "/auth/client/challenge",
        json={
            "full_name": full_name,
            "phone": phone,
            "access_token": access_token,
        },
    )
    assert challenge_response.status_code == 202
    challenge_id = challenge_response.json()["challenge_id"]
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, UUID(challenge_id))
        challenge.secret_hash = token_hash("123456")
        db.commit()
    verified = client.post(
        "/auth/client/verify",
        json={"challenge_id": challenge_id, "code": "123456"},
    )
    return verified.status_code, verified.json()


def _authenticate_existing_client(
    client: TestClient,
    *,
    full_name: str,
    phone: str,
) -> None:
    response = client.post(
        "/auth/client/challenge",
        json={"full_name": full_name, "phone": phone},
    )
    assert response.status_code == 202
    challenge_id = response.json()["challenge_id"]
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, UUID(challenge_id))
        challenge.secret_hash = token_hash("123456")
        db.commit()
    assert client.post(
        "/auth/client/verify",
        json={"challenge_id": challenge_id, "code": "123456"},
    ).status_code == 200


def test_admin_private_link_endpoints_migrate_rotate_reconstruct_and_revoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GALLERY_CAPABILITY_SIGNING_KEY", "signed-gallery-key-for-tests-0004")
    with SessionLocal() as db:
        owner = Client(full_name="Titular API", phone_e164="+5511999999402")
        parent = ParentGallery(name="Origem API")
        db.add_all((owner, parent))
        db.flush()
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada API",
        )
        db.add(private)
        db.flush()
        legacy, legacy_token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            derived_gallery_id=private.id,
            client_id=owner.id,
            scope="private_invite",
        )
        db.commit()
        private_id = private.id
        legacy_id = legacy.id

    with TestClient(app) as client:
        _authenticate_admin(client)
        status = client.get(f"/admin/derived-galleries/{private_id}/link")
        assert status.status_code == 200
        assert status.json()["status"] == "legacy_unrecoverable"
        assert status.json()["link"] is None

        migrated = client.post(
            f"/admin/derived-galleries/{private_id}/link/rotate",
            json={},
        )
        assert migrated.status_code == 200
        first_token = migrated.json()["access_token"]
        assert first_token.startswith("gc1.")

        reconstructed = client.get(f"/admin/derived-galleries/{private_id}/link")
        assert reconstructed.status_code == 200
        assert reconstructed.json()["access_token"] == first_token
        assert reconstructed.json()["secret_available"] is True

        rotated = client.post(
            f"/admin/derived-galleries/{private_id}/link/rotate",
            json={},
        )
        assert rotated.status_code == 200
        second_token = rotated.json()["access_token"]
        assert second_token != first_token

        with SessionLocal() as db:
            assert db.get(GalleryAccessCapability, legacy_id).status == "revoked"
            assert resolve_gallery_capability(db, legacy_token) is None
            assert resolve_gallery_capability(db, first_token) is None
            assert resolve_gallery_capability(db, second_token) is not None

        assert client.delete(f"/admin/derived-galleries/{private_id}/link").status_code == 204
        unavailable = client.get(f"/admin/derived-galleries/{private_id}/link")
        assert unavailable.json()["status"] == "unavailable"


def test_private_link_otp_reuses_identity_membership_and_existing_origin_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GALLERY_CAPABILITY_SIGNING_KEY", "signed-gallery-key-for-tests-0005")
    with SessionLocal() as db:
        owner = Client(full_name="Titular", phone_e164="+5511999999403")
        other_owner = Client(full_name="Outra titular", phone_e164="+5511999999404")
        parent = ParentGallery(name="Origem OTP")
        db.add_all((owner, other_owner, parent))
        db.flush()
        first_private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Primeira privada",
        )
        second_private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=other_owner.id,
            name="Segunda privada",
        )
        db.add_all((first_private, second_private))
        db.flush()
        _first_capability, first_token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            derived_gallery_id=first_private.id,
            scope="private_gallery_link",
            reconstructible=True,
        )
        _second_capability, second_token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            derived_gallery_id=second_private.id,
            scope="private_gallery_link",
            reconstructible=True,
        )
        db.commit()
        first_id = first_private.id
        second_id = second_private.id
        parent_id = parent.id

    phone = "+5511999999405"
    with TestClient(app) as client:
        status_code, payload = _verify_client_link(
            client,
            full_name="Nova cliente",
            phone=phone,
            access_token=first_token,
        )
        assert status_code == 200
        assert payload["destination"] == f"/gallery/{first_id}"

        with SessionLocal() as db:
            canonical = db.scalar(select(Client).where(Client.phone_e164 == phone))
            membership = db.scalar(
                select(DerivedGalleryMembership).where(
                    DerivedGalleryMembership.parent_gallery_id == parent_id,
                    DerivedGalleryMembership.client_id == canonical.id,
                )
            )
            assert membership.derived_gallery_id == first_id
            assert db.scalar(
                select(ParentGalleryRegistration).where(
                    ParentGalleryRegistration.parent_gallery_id == parent_id,
                    ParentGalleryRegistration.client_id == canonical.id,
                )
            ).status == "active"
            canonical_id = canonical.id

        status_code, payload = _verify_client_link(
            client,
            full_name="Nome ignorado",
            phone=phone,
            access_token=second_token,
        )
        assert status_code == 200
        assert payload["destination"] == f"/gallery/{first_id}"
        with SessionLocal() as db:
            assert db.scalar(
                select(DerivedGalleryMembership).where(
                    DerivedGalleryMembership.parent_gallery_id == parent_id,
                    DerivedGalleryMembership.client_id == canonical_id,
                )
            ).derived_gallery_id == first_id
            assert db.scalar(select(Client).where(Client.phone_e164 == phone)).id == canonical_id
            assert db.scalar(
                select(DerivedGalleryMembership).where(
                    DerivedGalleryMembership.derived_gallery_id == second_id,
                    DerivedGalleryMembership.client_id == canonical_id,
                )
            ) is None


def test_blocked_member_cannot_reenter_through_private_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GALLERY_CAPABILITY_SIGNING_KEY", "signed-gallery-key-for-tests-0006")
    with SessionLocal() as db:
        client_record = Client(full_name="Cliente bloqueada", phone_e164="+5511999999406")
        parent = ParentGallery(name="Origem bloqueada")
        db.add_all((client_record, parent))
        db.flush()
        result = ensure_private_membership(db, parent=parent, client=client_record)
        block_private_membership(result.membership)
        _, token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            derived_gallery_id=result.gallery.id,
            scope="private_gallery_link",
            reconstructible=True,
        )
        db.commit()

    with TestClient(app) as client:
        status_code, payload = _verify_client_link(
            client,
            full_name="Cliente bloqueada",
            phone="+5511999999406",
            access_token=token,
        )
        assert status_code == 403
        assert payload["detail"] == "Acesso não autorizado."


def test_admin_manages_private_members_without_deleting_identity_or_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GALLERY_CAPABILITY_SIGNING_KEY", "signed-gallery-key-for-tests-0007")
    with SessionLocal() as db:
        owner = Client(full_name="Titular membros", phone_e164="+5511999999407")
        relative = Client(full_name="Familiar membros", phone_e164="+5511999999408")
        conflict_owner = Client(full_name="Titular conflito", phone_e164="+5511999999409")
        parent = ParentGallery(name="Origem membros")
        db.add_all((owner, relative, conflict_owner, parent))
        db.flush()
        shared = ensure_private_membership(db, parent=parent, client=owner)
        conflicting = ensure_private_membership(db, parent=parent, client=conflict_owner)
        db.commit()
        gallery_id = shared.gallery.id
        parent_id = parent.id
        owner_id = owner.id
        relative_id = relative.id
        conflict_id = conflict_owner.id
        conflict_gallery_id = conflicting.gallery.id

    with TestClient(app) as client:
        _authenticate_admin(client)
        added = client.post(
            f"/admin/derived-galleries/{gallery_id}/members",
            json={"client_id": str(relative_id)},
        )
        assert added.status_code == 201
        assert added.json()["status"] == "active"
        assert added.json()["created"] is True

        with SessionLocal() as db:
            folder = PhotoFolder(
                parent_gallery_id=parent_id,
                name="Lote membros",
                status="released",
                purpose="content",
            )
            db.add(folder)
            db.flush()
            photo = PhotoAsset(
                parent_gallery_id=parent_id,
                folder_id=folder.id,
                filename="membro.jpg",
                storage_key="membros/membro.jpg",
            )
            db.add(photo)
            db.flush()
            db.add(
                DerivedGalleryPhoto(
                    derived_gallery_id=gallery_id,
                    photo_asset_id=photo.id,
                )
            )
            db.add(
                PhotoSelection(
                    derived_gallery_id=gallery_id,
                    photo_asset_id=photo.id,
                    client_id=relative_id,
                )
            )
            db.add(
                SaleOrder(
                    derived_gallery_id=gallery_id,
                    client_id=relative_id,
                    payment_status="confirmed",
                    total_cents=700,
                )
            )
            db.commit()

        selects: list[str] = []

        def count_selects(_conn, _cursor, statement, _parameters, _context, _many):
            if statement.lstrip().upper().startswith("SELECT"):
                selects.append(statement)

        event.listen(engine, "before_cursor_execute", count_selects)
        try:
            listed = client.get(f"/admin/derived-galleries/{gallery_id}/members")
        finally:
            event.remove(engine, "before_cursor_execute", count_selects)
        assert listed.status_code == 200
        assert len(selects) <= 6
        assert {item["client_id"] for item in listed.json()["members"]} == {
            str(owner_id),
            str(relative_id),
        }
        assert len(listed.json()["members"]) == 2
        assert listed.json()["total"] == 2
        relative_row = next(
            item
            for item in listed.json()["members"]
            if item["client_id"] == str(relative_id)
        )
        assert relative_row["selected_count"] == 1
        assert relative_row["order_count"] == 1
        assert relative_row["confirmed_total_cents"] == 700
        assert relative_row["payment_status"] == "confirmed"

        parent_clients = client.get(f"/admin/parent-galleries/{parent_id}/clients")
        assert parent_clients.status_code == 200
        parent_relative = next(
            item
            for item in parent_clients.json()["clients"]
            if item["client_id"] == str(relative_id)
        )
        assert parent_relative["derived_gallery_id"] == str(gallery_id)
        assert parent_relative["membership_status"] == "active"
        assert parent_relative["available_count"] == 1
        assert parent_relative["selected_count"] == 1

        relative_selection = client.get(
            f"/admin/derived-galleries/{gallery_id}/selection",
            params={"client_id": str(relative_id)},
        )
        owner_selection = client.get(
            f"/admin/derived-galleries/{gallery_id}/selection",
            params={"client_id": str(owner_id)},
        )
        assert relative_selection.status_code == 200
        assert relative_selection.json()["client"]["id"] == str(relative_id)
        assert relative_selection.json()["selection_count"] == 1
        assert owner_selection.status_code == 200
        assert owner_selection.json()["selection_count"] == 0

        blocked = client.post(
            f"/admin/derived-galleries/{gallery_id}/members/{relative_id}/block"
        )
        assert blocked.status_code == 200
        assert blocked.json()["status"] == "blocked"
        unblocked = client.post(
            f"/admin/derived-galleries/{gallery_id}/members/{relative_id}/unblock"
        )
        assert unblocked.status_code == 200
        assert unblocked.json()["status"] == "active"
        unlinked = client.delete(
            f"/admin/derived-galleries/{gallery_id}/members/{relative_id}"
        )
        assert unlinked.status_code == 200
        assert unlinked.json()["status"] == "unlinked"

        reactivated = client.post(
            f"/admin/derived-galleries/{gallery_id}/members",
            json={"client_id": str(relative_id)},
        )
        assert reactivated.status_code == 201
        assert reactivated.json()["status"] == "active"
        assert reactivated.json()["created"] is False

        conflict = client.post(
            f"/admin/derived-galleries/{gallery_id}/members",
            json={"client_id": str(conflict_id)},
        )
        assert conflict.status_code == 409

        notifications = client.get("/admin/notifications")
        assert notifications.status_code == 200
        notification_rows = notifications.json()["notifications"]
        assert {item["event_type"] for item in notification_rows} >= {
            "member_joined",
            "member_blocked",
            "member_unblocked",
            "member_unlinked",
        }
        first_notification = notification_rows[0]
        marked = client.post(
            f"/admin/notifications/{first_notification['id']}/read"
        )
        assert marked.status_code == 200
        assert marked.json()["status"] == "read"

    with SessionLocal() as db:
        assert db.get(Client, relative_id) is not None
        assert db.get(DerivedGallery, conflict_gallery_id) is not None
        actions = set(
            db.scalars(
                select(AuditEvent.event).where(
                    AuditEvent.event.in_(
                        (
                            "private_gallery.member_joined",
                            "private_gallery.member_blocked",
                            "private_gallery.member_unblocked",
                            "private_gallery.member_unlinked",
                        )
                    )
                )
            )
        )
        assert actions == {
            "private_gallery.member_joined",
            "private_gallery.member_blocked",
            "private_gallery.member_unblocked",
            "private_gallery.member_unlinked",
        }


def test_admin_private_acervo_adds_and_removes_only_its_justification() -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Titular acervo", phone_e164="+5511999999410")
        parent = ParentGallery(name="Origem acervo", active=True)
        db.add_all((owner, parent))
        db.flush()
        shared = ensure_private_membership(db, parent=parent, client=owner)
        folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Lote publicado",
            status="released",
            purpose="content",
        )
        db.add(folder)
        db.flush()
        selected_photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="selecionada.jpg",
            storage_key="acervo/selecionada.jpg",
        )
        admin_photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="administrativa.jpg",
            storage_key="acervo/administrativa.jpg",
        )
        db.add_all((selected_photo, admin_photo))
        db.flush()
        ensure_private_photo_reference(
            db,
            gallery_id=shared.gallery.id,
            photo_id=selected_photo.id,
            origin="client",
        )
        db.commit()
        gallery_id = shared.gallery.id
        selected_photo_id = selected_photo.id
        admin_photo_id = admin_photo.id

    with TestClient(app) as client:
        _authenticate_admin(client)
        added = client.post(
            f"/admin/derived-galleries/{gallery_id}/photos",
            json={"photo_ids": [str(selected_photo_id), str(admin_photo_id)]},
        )
        assert added.status_code == 200
        assert added.json()["references_created"] == 1

        listed = client.get(f"/admin/derived-galleries/{gallery_id}/photos")
        assert listed.status_code == 200
        by_id = {item["id"]: item for item in listed.json()["photos"]}
        assert by_id[str(selected_photo_id)]["origins"] == ["admin", "client"]

        retained = client.delete(
            f"/admin/derived-galleries/{gallery_id}/photos/{selected_photo_id}"
        )
        assert retained.status_code == 200
        assert retained.json()["reference_removed"] is False
        assert retained.json()["retained_origins"] == ["client"]

        removed = client.delete(
            f"/admin/derived-galleries/{gallery_id}/photos/{admin_photo_id}"
        )
        assert removed.status_code == 200
        assert removed.json()["reference_removed"] is True

    with SessionLocal() as db:
        assert db.get(PhotoAsset, selected_photo_id) is not None
        assert db.get(PhotoAsset, admin_photo_id) is not None
        selected_reference = db.scalar(
            select(DerivedGalleryPhoto).where(
                DerivedGalleryPhoto.derived_gallery_id == gallery_id,
                DerivedGalleryPhoto.photo_asset_id == selected_photo_id,
            )
        )
        assert selected_reference is not None
        assert set(
            db.scalars(
                select(DerivedGalleryPhotoOrigin.origin).where(
                    DerivedGalleryPhotoOrigin.derived_gallery_photo_id
                    == selected_reference.id
                )
            )
        ) == {"client"}
        assert db.scalar(
            select(DerivedGalleryPhoto.id).where(
                DerivedGalleryPhoto.derived_gallery_id == gallery_id,
                DerivedGalleryPhoto.photo_asset_id == admin_photo_id,
            )
        ) is None


def test_membership_notification_outbox_is_idempotent_and_sanitizes_external_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GALLERY_NOTIFICATION_EXTERNAL_ENABLED", "true")
    with SessionLocal() as db:
        client = Client(full_name="Cliente notificada", phone_e164="+5511999999410")
        parent = ParentGallery(name="Origem notificada")
        db.add_all((client, parent))
        db.flush()
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=client.id,
            name="Privada notificada",
        )
        db.add(private)
        db.flush()
        first, first_created = enqueue_membership_notification(
            db,
            event_key=f"private_created:{private.id}",
            event_type="private_created",
            parent=parent,
            gallery=private,
            client=client,
        )
        repeated, repeated_created = enqueue_membership_notification(
            db,
            event_key=f"private_created:{private.id}",
            event_type="private_created",
            parent=parent,
            gallery=private,
            client=client,
        )
        db.commit()
        assert first_created is True
        assert repeated_created is False
        assert repeated.id == first.id

        def failing_sender(_notification) -> None:
            raise RuntimeError("segredo-que-nao-pode-ser-persistido")

        assert process_next_membership_notification(db, failing_sender) is True
        stored = db.get(GalleryMembershipNotificationOutbox, first.id)
        assert stored.external_status == "queued"
        assert stored.attempts == 1
        assert stored.last_error == "RuntimeError"
        assert "segredo" not in stored.last_error


def test_client_contracts_do_not_serialize_other_member_or_commercial_activity() -> None:
    with SessionLocal() as db:
        first = Client(full_name="Primeira cliente privada", phone_e164="+5511999999411")
        second = Client(full_name="Segunda cliente secreta", phone_e164="+5511999999412")
        parent = ParentGallery(name="Origem privada", comments_enabled=True)
        db.add_all((first, second, parent))
        db.flush()
        shared = ensure_private_membership(db, parent=parent, client=first)
        ensure_private_membership(
            db,
            parent=parent,
            client=second,
            gallery=shared.gallery,
        )
        folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Lote",
            status="released",
            purpose="content",
        )
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="IMG_PRIVADA.jpg",
            storage_key="privada/IMG_PRIVADA.jpg",
        )
        db.add(photo)
        db.flush()
        db.add(DerivedGalleryPhoto(derived_gallery_id=shared.gallery.id, photo_asset_id=photo.id))
        db.add_all(
            (
                PhotoComment(
                    derived_gallery_id=shared.gallery.id,
                    photo_asset_id=photo.id,
                    client_id=first.id,
                    body="Comentário visível da primeira",
                ),
                PhotoComment(
                    derived_gallery_id=shared.gallery.id,
                    photo_asset_id=photo.id,
                    client_id=second.id,
                    body="SEGREDO-COMENTARIO-SEGUNDA",
                ),
                PhotoSelection(
                    derived_gallery_id=shared.gallery.id,
                    photo_asset_id=photo.id,
                    client_id=second.id,
                ),
                PhotoFavorite(
                    derived_gallery_id=shared.gallery.id,
                    photo_asset_id=photo.id,
                    client_id=second.id,
                ),
            )
        )
        other_order = SaleOrder(
            derived_gallery_id=shared.gallery.id,
            client_id=second.id,
            payment_status="confirmed",
            total_cents=987654,
        )
        db.add(other_order)
        db.flush()
        db.add(
            SaleOrderItem(
                sale_order_id=other_order.id,
                photo_asset_id=photo.id,
                filename_snapshot=photo.filename,
                unit_price_cents=987654,
            )
        )
        db.add(
            PaymentCommunication(
                sale_order_id=other_order.id,
                client_id=second.id,
                status="pending_review",
                idempotency_key="privacy-other-payment-001",
            )
        )
        db.commit()
        gallery_id = shared.gallery.id
        second_id = second.id

    with TestClient(app) as client:
        _authenticate_existing_client(
            client,
            full_name="Primeira cliente privada",
            phone="+5511999999411",
        )
        responses = (
            client.get("/library"),
            client.get(f"/gallery/{gallery_id}/review"),
            client.get(f"/gallery/{gallery_id}/comments"),
            client.get(f"/gallery/{gallery_id}/payment-communications"),
        )
        assert all(response.status_code == 200 for response in responses)
        serialized = "\n".join(response.text for response in responses)
        assert "Segunda cliente secreta" not in serialized
        assert "+5511999999412" not in serialized
        assert str(second_id) not in serialized
        assert "SEGREDO-COMENTARIO-SEGUNDA" not in serialized
        assert "987654" not in serialized
        first_photo = responses[1].json()["photos"][0]
        assert first_photo["selected"] is False
        assert first_photo["favorited"] is False
        assert first_photo["purchase_state"] != "já comprada"

        _authenticate_existing_client(
            client,
            full_name="Segunda cliente secreta",
            phone="+5511999999412",
        )
        second_photo = client.get(f"/gallery/{gallery_id}/review").json()["photos"][0]
        assert second_photo["selected"] is True
        assert second_photo["favorited"] is True
        assert second_photo["purchase_state"] == "já comprada"


def test_library_routes_one_private_per_origin_and_preserves_blocked_history() -> None:
    with SessionLocal() as db:
        client_record = Client(full_name="Cliente biblioteca", phone_e164="+5511999999413")
        first_parent = ParentGallery(name="Primeira origem")
        second_parent = ParentGallery(name="Segunda origem")
        db.add_all((client_record, first_parent, second_parent))
        db.flush()
        blocked = ensure_private_membership(
            db, parent=first_parent, client=client_record
        )
        active = ensure_private_membership(
            db, parent=second_parent, client=client_record
        )
        block_private_membership(blocked.membership)
        order = SaleOrder(
            derived_gallery_id=blocked.gallery.id,
            client_id=client_record.id,
            payment_status="confirmed",
            total_cents=1500,
            confirmed_at=now(),
        )
        db.add(order)
        db.commit()
        blocked_id = blocked.gallery.id
        active_id = active.gallery.id

    with TestClient(app) as client:
        _authenticate_existing_client(
            client,
            full_name="Cliente biblioteca",
            phone="+5511999999413",
        )
        library = client.get("/library")
        assert library.status_code == 200
        rows = {row["id"]: row for row in library.json()["private_galleries"]}
        assert set(rows) == {str(blocked_id), str(active_id)}
        assert rows[str(blocked_id)]["gallery_status"] == "blocked"
        assert rows[str(blocked_id)]["browse_url"] is None
        assert rows[str(active_id)]["browse_url"] == f"/gallery/{active_id}"
        history = client.get("/library/purchases")
        assert history.status_code == 200
        assert history.json()["orders"][0]["total_cents"] == 1500
