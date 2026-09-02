import pytest
from sqlalchemy import select

from app.auth import (
    Base,
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    DerivedGalleryPhotoOrigin,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    SessionLocal,
    engine,
)
from app.private_derivation import derive_admin_gallery, derive_client_selection
from app.private_membership import (
    PrivateMembershipConflict,
    PrivateMembershipError,
    block_private_membership,
    client_has_operational_membership,
    ensure_private_membership,
    operational_galleries_for_client,
    reactivate_private_membership,
    unblock_private_membership,
    unlink_private_membership,
)


@pytest.fixture(autouse=True)
def clean_database():
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


def test_membership_service_is_idempotent_and_supports_shared_gallery() -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Cliente titular", phone_e164="+5511999999501")
        relative = Client(full_name="Cliente familiar", phone_e164="+5511999999502")
        parent = ParentGallery(name="Origem compartilhada")
        db.add_all((owner, relative, parent))
        db.flush()

        first = ensure_private_membership(db, parent=parent, client=owner)
        repeated = ensure_private_membership(db, parent=parent, client=owner)
        joined = ensure_private_membership(
            db,
            parent=parent,
            client=relative,
            gallery=first.gallery,
        )
        db.commit()

        assert first.gallery_created and first.membership_created
        assert repeated.gallery.id == first.gallery.id
        assert not repeated.gallery_created and not repeated.membership_created
        assert joined.membership_created
        assert joined.gallery.id == first.gallery.id
        assert len(
            list(
                db.scalars(
                    select(DerivedGalleryMembership).where(
                        DerivedGalleryMembership.derived_gallery_id == first.gallery.id
                    )
                )
            )
        ) == 2


def test_membership_service_rejects_second_private_in_same_origin() -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Titular", phone_e164="+5511999999503")
        other_owner = Client(full_name="Outra titular", phone_e164="+5511999999504")
        parent = ParentGallery(name="Origem única")
        db.add_all((owner, other_owner, parent))
        db.flush()
        own = ensure_private_membership(db, parent=parent, client=owner)
        other = ensure_private_membership(db, parent=parent, client=other_owner)
        db.flush()

        with pytest.raises(PrivateMembershipConflict):
            ensure_private_membership(
                db,
                parent=parent,
                client=owner,
                gallery=other.gallery,
            )
        assert own.gallery.id != other.gallery.id


def test_membership_state_transitions_are_idempotent_and_auditable() -> None:
    with SessionLocal() as db:
        client = Client(full_name="Cliente", phone_e164="+5511999999505")
        other_owner = Client(full_name="Outra titular", phone_e164="+5511999999506")
        parent = ParentGallery(name="Origem")
        db.add_all((client, other_owner, parent))
        db.flush()
        result = ensure_private_membership(db, parent=parent, client=client)
        membership = result.membership

        block_private_membership(membership)
        first_blocked_at = membership.blocked_at
        block_private_membership(membership)
        assert membership.status == "blocked"
        assert membership.blocked_at == first_blocked_at

        unblock_private_membership(membership)
        assert membership.status == "active"
        assert membership.blocked_at is None

        unlink_private_membership(membership)
        first_unlinked_at = membership.unlinked_at
        unlink_private_membership(membership)
        assert membership.status == "unlinked"
        assert membership.unlinked_at == first_unlinked_at
        with pytest.raises(PrivateMembershipError):
            unblock_private_membership(membership)

        replacement = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=other_owner.id,
            name="Privada reativada",
        )
        db.add(replacement)
        db.flush()

        reactivate_private_membership(
            membership,
            gallery=replacement,
        )
        assert membership.status == "active"
        assert membership.unlinked_at is None
        assert membership.derived_gallery_id == replacement.id


def test_operational_authorization_matrix_prefers_membership_over_legacy_owner() -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Titular", phone_e164="+5511999999507")
        member = Client(full_name="Membro", phone_e164="+5511999999508")
        outsider = Client(full_name="Terceira", phone_e164="+5511999999509")
        legacy_parent = ParentGallery(name="Origem legada")
        shared_parent = ParentGallery(name="Origem compartilhada")
        db.add_all((owner, member, outsider, legacy_parent, shared_parent))
        db.flush()
        legacy_gallery = DerivedGallery(
            parent_gallery_id=legacy_parent.id,
            client_id=owner.id,
            name="Privada sem backfill",
        )
        db.add(legacy_gallery)
        db.flush()
        assert client_has_operational_membership(
            db,
            gallery=legacy_gallery,
            client_id=owner.id,
        )
        assert not client_has_operational_membership(
            db,
            gallery=legacy_gallery,
            client_id=outsider.id,
        )

        shared = ensure_private_membership(db, parent=shared_parent, client=owner)
        joined = ensure_private_membership(
            db,
            parent=shared_parent,
            client=member,
            gallery=shared.gallery,
        )
        assert client_has_operational_membership(
            db,
            gallery=shared.gallery,
            client_id=owner.id,
        )
        assert client_has_operational_membership(
            db,
            gallery=shared.gallery,
            client_id=member.id,
        )
        assert not client_has_operational_membership(
            db,
            gallery=shared.gallery,
            client_id=outsider.id,
        )

        block_private_membership(joined.membership)
        assert not client_has_operational_membership(
            db,
            gallery=shared.gallery,
            client_id=member.id,
        )
        assert shared.gallery not in operational_galleries_for_client(
            db,
            client_id=member.id,
        )
        assert shared.gallery in operational_galleries_for_client(
            db,
            client_id=owner.id,
        )

        unlink_private_membership(joined.membership)
        assert not client_has_operational_membership(
            db,
            gallery=shared.gallery,
            client_id=member.id,
        )


def test_derivation_reuses_shared_collection_and_keeps_member_state_individual() -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Titular", phone_e164="+5511999999510")
        member = Client(full_name="Familiar", phone_e164="+5511999999511")
        parent = ParentGallery(name="Origem", active=True)
        db.add_all((owner, member, parent))
        db.flush()
        shared = ensure_private_membership(db, parent=parent, client=owner)
        ensure_private_membership(
            db,
            parent=parent,
            client=member,
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
        photos = [
            PhotoAsset(
                parent_gallery_id=parent.id,
                folder_id=folder.id,
                filename=f"filho-{position}.jpg",
                storage_key=f"origem/filho-{position}.jpg",
            )
            for position in (1, 2)
        ]
        db.add_all(photos)
        db.flush()

        administrative = derive_admin_gallery(
            db,
            parent_gallery_id=parent.id,
            client_id=member.id,
            photo_ids={photos[0].id},
        )
        selected = derive_client_selection(
            db,
            parent_gallery_id=parent.id,
            client_id=owner.id,
            photo_id=photos[1].id,
        )
        repeated_from_admin = derive_admin_gallery(
            db,
            parent_gallery_id=parent.id,
            client_id=member.id,
            photo_ids={photos[1].id},
        )
        db.flush()

        assert administrative.gallery.id == shared.gallery.id
        assert selected.gallery.id == shared.gallery.id
        assert selected.selection_created
        assert repeated_from_admin.references_created == 0
        assert set(
            db.scalars(
                select(DerivedGalleryPhoto.photo_asset_id).where(
                    DerivedGalleryPhoto.derived_gallery_id == shared.gallery.id
                )
            )
        ) == {photo.id for photo in photos}
        assert db.scalar(
            select(PhotoSelection.id).where(
                PhotoSelection.derived_gallery_id == shared.gallery.id,
                PhotoSelection.client_id == member.id,
            )
        ) is None
        assert set(db.scalars(select(PhotoAsset.storage_key))) == {
            "origem/filho-1.jpg",
            "origem/filho-2.jpg",
        }
        repeated_reference_id = db.scalar(
            select(DerivedGalleryPhoto.id).where(
                DerivedGalleryPhoto.derived_gallery_id == shared.gallery.id,
                DerivedGalleryPhoto.photo_asset_id == photos[1].id,
            )
        )
        assert set(
            db.scalars(
                select(DerivedGalleryPhotoOrigin.origin).where(
                    DerivedGalleryPhotoOrigin.derived_gallery_photo_id
                    == repeated_reference_id
                )
            )
        ) == {"admin", "client"}
