from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth import (
    AuthSession,
    Client,
    DerivedGallery,
    FolderClientGrant,
    GalleryClientState,
    NotificationDelivery,
    NotificationEvent,
    NotificationMilestone,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFolder,
    PushSubscription,
    SessionLocal,
    now,
    token_hash,
)
from app.notification_delivery import recipient_allowed
from app.notification_events import record_gallery_milestone, record_restricted_folder_ready
from app.notification_settings import setting_for
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_notification_settings import isolated_schema  # noqa: F401


def scenario():
    with SessionLocal() as db:
        person = Client(full_name="Cliente sintético", phone_e164="+5511999999999")
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Evento")
        db.add_all([person, parent])
        db.flush()
        db.add(ParentGalleryRegistration(parent_gallery_id=parent.id, client_id=person.id, status="active"))
        db.add(AuthSession(role="client", subject_id=person.id, token_hash=token_hash("synthetic"),
                           expires_at=now() + timedelta(hours=1)))
        db.commit()
    return person.id, parent.id


def test_first_access_is_once_per_canonical_gallery_with_valid_session():
    from app.main import app
    person, parent = scenario()
    browser = TestClient(app)
    browser.cookies.set("markina_session", "synthetic")
    for _ in range(2):
        assert browser.get(f"/public-galleries/{parent}").status_code == 200
    with SessionLocal() as db:
        private = DerivedGallery(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent, client_id=person, name="Privada")
        another = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Outro evento")
        db.add_all([private, another])
        db.flush()
        db.add(ParentGalleryRegistration(parent_gallery_id=another.id, client_id=person, status="active"))
        db.commit()
        assert db.scalar(select(func.count(NotificationEvent.id))) == 1
    assert browser.get(f"/gallery/{private.id}").status_code == 200
    assert browser.get(f"/public-galleries/{another.id}").status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count(NotificationEvent.id))) == 2


def test_denied_and_legacy_baseline_do_not_generate_access_events():
    from app.main import app
    person, parent = scenario()
    browser = TestClient(app)
    browser.cookies.set("markina_session", "synthetic")
    with SessionLocal() as db:
        db.add(NotificationMilestone(parent_gallery_id=parent, client_id=person,
                                      kind="first_access", baseline=True))
        unauthorized = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Não autorizada")
        db.add(unauthorized)
        db.commit()
    assert browser.get(f"/public-galleries/{parent}").status_code == 200
    assert browser.get(f"/public-galleries/{unauthorized.id}").status_code == 403
    assert TestClient(app).get(f"/public-galleries/{parent}").status_code == 403
    with SessionLocal() as db:
        assert db.scalar(select(func.count(NotificationEvent.id))) == 0


def test_concurrent_access_is_deduplicated_and_rollback_is_atomic():
    person, parent = scenario()
    with SessionLocal() as db:
        setting_for(db, "first_access")
        db.commit()
    def record(_):
        with SessionLocal() as db:
            result = record_gallery_milestone(db, kind="first_access", parent_gallery_id=parent,
                                               client_id=person)
            db.commit()
            return result
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(record, range(2))) == [False, True]
    with SessionLocal() as db:
        assert db.scalar(select(func.count(NotificationEvent.id))) == 1


def test_first_private_selection_independent_of_creation_favorite_and_reselection():
    from app.main import app
    person, parent = scenario()
    with SessionLocal() as db:
        db.get(ParentGallery, parent).favorites_enabled = True
        gallery = DerivedGallery(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent, client_id=person, name="Privada existente")
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent, derived_gallery_id=gallery.id,
                              name="Privadas", status="released")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent, derived_gallery_id=gallery.id,
                            folder_id=folder.id, filename="teste.jpg", storage_key="synthetic/test.jpg")
        db.add(photo)
        db.commit()
        gallery_id, photo_id = gallery.id, photo.id
    browser = TestClient(app)
    browser.cookies.set("markina_session", "synthetic")
    path = f"/gallery/{gallery_id}/photos/{photo_id}"
    assert browser.post(f"{path}/favorite").status_code == 201
    with SessionLocal() as db:
        assert db.scalar(select(func.count(NotificationEvent.id))) == 0
    def choose(_):
        other = TestClient(app)
        other.cookies.set("markina_session", "synthetic")
        return other.post(f"{path}/selection").status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(choose, range(2))) == [201, 201]
    assert browser.delete(f"{path}/selection").status_code == 204
    assert browser.post(f"{path}/selection").status_code == 201
    with SessionLocal() as db:
        events = list(db.scalars(select(NotificationEvent)))
        assert len(events) == 1
        assert events[0].event_type == "first_selection"
        new_parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, id=uuid4(), name="Rollback")
        db.add(new_parent)
        db.flush()
        db.add(ParentGalleryRegistration(parent_gallery_id=new_parent.id, client_id=person, status="active"))
        db.flush()
        assert record_gallery_milestone(db, kind="first_access", parent_gallery_id=new_parent.id,
                                        client_id=person)
        db.rollback()
    with SessionLocal() as db:
        assert db.scalar(select(func.count(NotificationEvent.id))) == 1


def test_restricted_folder_ready_notifies_only_current_recipients_without_replay():
    owner_id, parent_id = scenario()
    with SessionLocal() as db:
        other = Client(full_name="Segunda cliente", phone_e164="+5511999999997")
        db.add(other)
        db.flush()
        db.add(ParentGalleryRegistration(
            parent_gallery_id=parent_id, client_id=other.id, status="active"
        ))
        folder = PhotoFolder(
            parent_gallery_id=parent_id, name="Acervo", status="released",
            purpose="content", audience_scope="selected",
        )
        db.add(folder)
        db.flush()
        db.add_all([
            GalleryClientState(parent_gallery_id=parent_id, client_id=owner_id),
            GalleryClientState(parent_gallery_id=parent_id, client_id=other.id),
        ])
        db.flush()
        db.add_all([
            FolderClientGrant(folder_id=folder.id, parent_gallery_id=parent_id, client_id=owner_id),
            FolderClientGrant(folder_id=folder.id, parent_gallery_id=parent_id, client_id=other.id),
            PushSubscription(endpoint_fingerprint="1" * 64, encrypted_subscription="ciphertext",
                             role="client", subject_id=owner_id),
            PushSubscription(endpoint_fingerprint="2" * 64, encrypted_subscription="ciphertext",
                             role="client", subject_id=other.id),
        ])
        db.flush()
        first_photo = uuid4()
        assert record_restricted_folder_ready(
            db, folder=folder, photo_ids={first_photo}, batch_key="publish"
        ) == 2
        db.commit()
        events = list(db.scalars(select(NotificationEvent)))
        assert len(events) == 2
        assert {event.client_id for event in events} == {owner_id, other.id}
        assert {event.target_path for event in events} == {f"/public-galleries/{parent_id}"}
        deliveries = list(db.scalars(select(NotificationDelivery)))
        assert {(item.recipient_id, item.channel) for item in deliveries} == {
            (owner_id, "whatsapp"), (owner_id, "push"),
            (other.id, "whatsapp"), (other.id, "push"),
        }
        assert record_restricted_folder_ready(
            db, folder=folder, photo_ids={first_photo}, batch_key="publish"
        ) == 2
        db.commit()
        assert db.scalar(select(func.count(NotificationEvent.id))) == 2
        grant = db.scalar(select(FolderClientGrant).where(
            FolderClientGrant.folder_id == folder.id,
            FolderClientGrant.client_id == other.id,
        ))
        db.delete(grant)
        db.flush()
        queued_event = db.scalar(select(NotificationEvent).where(
            NotificationEvent.client_id == other.id,
            NotificationEvent.event_type == "private_photos_ready",
        ))
        queued_delivery = db.scalar(select(NotificationDelivery).where(
            NotificationDelivery.event_id == queued_event.id,
        ))
        assert not recipient_allowed(db, queued_event, queued_delivery)
        assert record_restricted_folder_ready(
            db, folder=folder, photo_ids={uuid4()}, batch_key="publish"
        ) == 1
        db.commit()
        assert db.scalar(select(func.count(NotificationEvent.id))) == 3
        assert db.scalar(select(func.count(NotificationDelivery.id)).where(
            NotificationDelivery.recipient_id == other.id
        )) == 2
        db.add(FolderClientGrant(
            folder_id=folder.id, parent_gallery_id=parent_id, client_id=other.id
        ))
        db.flush()
        assert record_restricted_folder_ready(
            db, folder=folder, photo_ids={first_photo}, batch_key="publish",
            client_ids={other.id},
        ) == 1
        db.commit()
        assert db.scalar(select(func.count(NotificationEvent.id))) == 4
        assert not recipient_allowed(db, queued_event, queued_delivery)
