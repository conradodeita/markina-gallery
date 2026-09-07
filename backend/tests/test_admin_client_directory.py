from datetime import timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select

from app import client_lifecycle
from app.auth import (
    AdminUser,
    AuditEvent,
    AuthChallenge,
    AuthSession,
    Base,
    Client,
    ClientDeletionReceipt,
    ClientPhone,
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    FacialSearchRequest,
    GalleryAccess,
    GalleryAccessCapability,
    GalleryFacialPolicy,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    PaymentNotificationOutbox,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    SaleOrder,
    SessionLocal,
    WhatsAppDelivery,
    WhatsAppDeliveryAttempt,
    engine,
    now,
    password_hasher,
    token_hash,
)
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(connection)
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def authenticate_admin(client: TestClient) -> UUID:
    with SessionLocal() as db:
        admin = AdminUser(
            email="diretorio@markina.test",
            password_hash=password_hasher.hash("senha-segura"),
            email_verified=True,
            totp_secret=pyotp.random_base32(),
        )
        db.add(admin)
        db.commit()
        admin_id = admin.id
        secret = admin.totp_secret
    challenge_id = client.post(
        "/auth/admin/password",
        json={"email": "diretorio@markina.test", "password": "senha-segura"},
    ).json()["challenge_id"]
    assert client.post(
        "/auth/admin/totp",
        json={"challenge_id": challenge_id, "code": pyotp.TOTP(secret).now()},
    ).status_code == 200
    return admin_id


def add_client(db, name: str, phone: str) -> Client:
    item = Client(full_name=name, phone_e164=phone)
    db.add(item)
    db.flush()
    db.add(ClientPhone(client_id=item.id, phone_e164=phone, active=True))
    return item


def add_gallery_graph(db, owner: Client, *, name: str) -> tuple[ParentGallery, DerivedGallery, PhotoAsset]:
    parent = ParentGallery(name=f"Pública {name}")
    db.add(parent)
    db.flush()
    folder = PhotoFolder(parent_gallery_id=parent.id, name="Fotos", status="released")
    db.add(folder)
    db.flush()
    photo = PhotoAsset(
        parent_gallery_id=parent.id,
        folder_id=folder.id,
        filename=f"{name}.jpg",
        storage_key=f"synthetic/{uuid4()}/{name}.jpg",
    )
    db.add(photo)
    db.flush()
    gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=owner.id, name=name)
    db.add(gallery)
    db.flush()
    db.add_all(
        [
            ParentGalleryRegistration(
                parent_gallery_id=parent.id, client_id=owner.id, status="active"
            ),
            DerivedGalleryMembership(
                derived_gallery_id=gallery.id,
                parent_gallery_id=parent.id,
                client_id=owner.id,
                status="active",
            ),
            DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=photo.id),
        ]
    )
    return parent, gallery, photo


def test_directory_is_authorized_paginated_searchable_and_aggregated(client: TestClient) -> None:
    assert client.get("/admin/clients").status_code == 403
    authenticate_admin(client)
    with SessionLocal() as db:
        ana = add_client(db, "Ana Cliente", "+5511900000101")
        bia = add_client(db, "Bia Cliente", "+5511900000102")
        caio = add_client(db, "Caio Cliente", "+5511900000103")
        parent, private, _ = add_gallery_graph(db, ana, name="Privada Ana")
        order = SaleOrder(
            derived_gallery_id=private.id,
            client_id=ana.id,
            payment_status="pending",
            total_cents=700,
            checkout_key="directory-order-0001",
        )
        db.add(order)
        db.commit()
        ids = {"ana": str(ana.id), "bia": str(bia.id), "caio": str(caio.id)}

    first = client.get("/admin/clients?limit=2")
    assert first.status_code == 200
    assert [item["id"] for item in first.json()["clients"]] == [ids["ana"], ids["bia"]]
    assert first.json()["clients"][0]["aggregates"] == {
        "public_galleries": 1,
        "private_galleries": 1,
        "orders": 1,
    }
    assert first.json()["clients"][0]["deletion_eligible"] is False
    assert first.json()["page"]["has_more"] is True
    assert first.json()["page"]["next_cursor"]

    second = client.get(
        "/admin/clients",
        params={"limit": 2, "cursor": first.json()["page"]["next_cursor"]},
    )
    assert [item["id"] for item in second.json()["clients"]] == [ids["caio"]]
    assert second.json()["page"] == {"has_more": False, "next_cursor": None}

    searched = client.get("/admin/clients", params={"query": "11 90000-0102"}).json()
    assert [item["id"] for item in searched["clients"]] == [ids["bia"]]
    assert searched["clients"][0]["aggregates"] == {
        "public_galleries": 0,
        "private_galleries": 0,
        "orders": 0,
    }
    assert searched["clients"][0]["deletion_eligible"] is True

    with SessionLocal() as db:
        assert db.get(ParentGallery, parent.id) is not None


def test_directory_query_count_does_not_grow_per_client(client: TestClient) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        add_client(db, "Cliente 00", "+5511900000200")
        db.commit()

    def count_selects() -> int:
        queries = 0

        def observe(_conn, _cursor, statement, _parameters, _context, _executemany):
            nonlocal queries
            if statement.lstrip().upper().startswith("SELECT"):
                queries += 1

        event.listen(engine, "before_cursor_execute", observe)
        try:
            assert client.get("/admin/clients?limit=100").status_code == 200
        finally:
            event.remove(engine, "before_cursor_execute", observe)
        return queries

    baseline = count_selects()
    with SessionLocal() as db:
        for index in range(1, 16):
            add_client(db, f"Cliente {index:02d}", f"+55119000002{index:02d}")
        db.commit()
    assert count_selects() == baseline


def test_deletion_removes_exclusive_operational_graph_and_replays_receipt(
    client: TestClient,
) -> None:
    admin_id = authenticate_admin(client)
    with SessionLocal() as db:
        target = add_client(db, "Excluir Operacional", "+5511900000301")
        other = add_client(db, "Preservar Terceira", "+5511900000302")
        parent, private, photo = add_gallery_graph(db, target, name="Privada exclusiva")
        db.add_all(
            [
                GalleryAccess(client_id=target.id, gallery_id=parent.id),
                GalleryAccessCapability(
                    parent_gallery_id=parent.id,
                    derived_gallery_id=private.id,
                    client_id=None,
                    scope="private_gallery_link",
                    token_hash="a" * 64,
                    status="active",
                ),
                PhotoSelection(
                    derived_gallery_id=private.id,
                    photo_asset_id=photo.id,
                    client_id=target.id,
                ),
                AuthSession(
                    token_hash="operational-session",
                    role="client",
                    subject_id=target.id,
                    expires_at=now() + timedelta(days=1),
                ),
            ]
        )
        db.commit()
        target_id, other_id = target.id, other.id
        parent_id, private_id, photo_id = parent.id, private.id, photo.id

    inventory = client.get(f"/admin/clients/{target_id}/deletion-inventory")
    assert inventory.status_code == 200
    assert inventory.json()["can_delete"] is True
    assert inventory.json()["operational_removable"]["public_gallery_registrations"] == 1
    assert inventory.json()["operational_removable"]["private_galleries_exclusive"] == 1
    assert inventory.json()["operational_removable"]["gallery_capabilities"] == 1
    assert inventory.json()["commercial_protected"]["orders"] == 0

    headers = {"Idempotency-Key": "delete-client-operational-0001"}
    deleted = client.delete(f"/admin/clients/{target_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "completed"
    assert deleted.json()["client_id"] == str(target_id)
    assert deleted.json()["counts"]["clients"] == 1

    repeated = client.delete(f"/admin/clients/{target_id}", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json() == deleted.json()
    reused_for_other = client.delete(f"/admin/clients/{other_id}", headers=headers)
    assert reused_for_other.status_code == 409

    with SessionLocal() as db:
        assert db.get(Client, target_id) is None
        assert db.get(Client, other_id) is not None
        assert db.get(ParentGallery, parent_id) is not None
        assert db.get(PhotoAsset, photo_id) is not None
        assert db.get(DerivedGallery, private_id) is None
        receipt = db.scalar(
            select(ClientDeletionReceipt).where(
                ClientDeletionReceipt.target_client_id == target_id
            )
        )
        assert receipt is not None
        assert receipt.actor_admin_id == admin_id
        assert receipt.idempotency_key == sha256(
            headers["Idempotency-Key"].encode("utf-8")
        ).hexdigest()
        assert headers["Idempotency-Key"] not in repr(receipt)
        events = list(
            db.scalars(select(AuditEvent).where(AuditEvent.event == "client.deleted_without_history"))
        )
        assert len(events) == 1
        assert "+5511" not in events[0].subject
        assert "Excluir Operacional" not in events[0].subject


def test_deletion_preserves_shared_private_gallery_and_other_member(client: TestClient) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        target = add_client(db, "Excluir Compartilhada", "+5511900000401")
        survivor = add_client(db, "Membro preservado", "+5511900000402")
        parent, private, photo = add_gallery_graph(db, target, name="Privada compartilhada")
        db.add(
            DerivedGalleryMembership(
                derived_gallery_id=private.id,
                parent_gallery_id=parent.id,
                client_id=survivor.id,
                status="active",
            )
        )
        db.add_all(
            [
                PhotoSelection(
                    derived_gallery_id=private.id,
                    photo_asset_id=photo.id,
                    client_id=target.id,
                ),
                PhotoSelection(
                    derived_gallery_id=private.id,
                    photo_asset_id=photo.id,
                    client_id=survivor.id,
                ),
            ]
        )
        db.commit()
        target_id, survivor_id = target.id, survivor.id
        gallery_id = private.id

    response = client.delete(
        f"/admin/clients/{target_id}",
        headers={"Idempotency-Key": "delete-client-shared-0001"},
    )
    assert response.status_code == 200
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        assert gallery is not None
        assert gallery.client_id == survivor_id
        assert db.scalar(
            select(func.count()).select_from(PhotoSelection).where(
                PhotoSelection.client_id == target_id
            )
        ) == 0
        assert db.scalar(
            select(func.count()).select_from(PhotoSelection).where(
                PhotoSelection.client_id == survivor_id
            )
        ) == 1
        assert db.scalar(
            select(func.count()).select_from(DerivedGalleryMembership).where(
                DerivedGalleryMembership.client_id == survivor_id
            )
        ) == 1


def test_deletion_preserves_private_gallery_with_third_party_interaction(
    client: TestClient,
) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        target = add_client(db, "Excluir proprietária", "+5511900000451")
        survivor = add_client(db, "Preservar seleção", "+5511900000452")
        _, private, photo = add_gallery_graph(db, target, name="Privada com interação")
        db.add(
            PhotoSelection(
                derived_gallery_id=private.id,
                photo_asset_id=photo.id,
                client_id=survivor.id,
            )
        )
        db.commit()
        target_id = target.id
        survivor_id = survivor.id
        gallery_id = private.id

    response = client.delete(
        f"/admin/clients/{target_id}",
        headers={"Idempotency-Key": "delete-client-third-party-0001"},
    )
    assert response.status_code == 200
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        assert gallery is not None
        assert gallery.client_id == survivor_id
        assert db.scalar(
            select(func.count()).select_from(PhotoSelection).where(
                PhotoSelection.client_id == survivor_id
            )
        ) == 1


@pytest.mark.parametrize("payment_status", ["pending", "confirmed"])
def test_deletion_blocks_commercial_history_without_pii(
    client: TestClient, payment_status: str
) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        target = add_client(db, "Histórico Protegido", "+5511900000501")
        _, private, _ = add_gallery_graph(db, target, name="Privada com pedido")
        db.add(
            SaleOrder(
                derived_gallery_id=private.id,
                client_id=target.id,
                payment_status=payment_status,
                total_cents=700,
                checkout_key=f"protected-{payment_status}-0001",
            )
        )
        db.commit()
        target_id = target.id

    inventory = client.get(f"/admin/clients/{target_id}/deletion-inventory").json()
    assert inventory["can_delete"] is False
    assert inventory["commercial_protected"]["orders"] == 1
    denied = client.delete(
        f"/admin/clients/{target_id}",
        headers={"Idempotency-Key": f"delete-protected-{payment_status}-0001"},
    )
    assert denied.status_code == 409
    serialized = denied.text
    assert "Histórico Protegido" not in serialized
    assert "+5511900000501" not in serialized
    assert client.get(f"/admin/clients/{target_id}/deletion-inventory").status_code == 200


def test_deletion_requires_valid_idempotency_key(client: TestClient) -> None:
    authenticate_admin(client)
    created = client.post(
        "/admin/clients",
        json={"full_name": "Chave obrigatória", "phone_e164": "+5511900000601"},
    )
    client_id = created.json()["id"]
    assert client.delete(f"/admin/clients/{client_id}").status_code == 422
    assert client.delete(
        f"/admin/clients/{client_id}", headers={"Idempotency-Key": "curta"}
    ).status_code == 422


def test_verified_phone_change_preserves_uuid_revokes_session_and_refuses_duplicate(
    client: TestClient,
) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        target = add_client(db, "Identidade estável", "+5511900000681")
        other = add_client(db, "Número ocupado", "+5511900000682")
        registration_parent = ParentGallery(name="Pública identidade")
        db.add(registration_parent)
        db.flush()
        registration = ParentGalleryRegistration(
            parent_gallery_id=registration_parent.id,
            client_id=target.id,
            status="active",
        )
        db.add(registration)
        session = AuthSession(
            token_hash="old-phone-session-directory",
            role="client",
            subject_id=target.id,
            expires_at=now() + timedelta(days=1),
        )
        db.add(session)
        successful = AuthChallenge(
            kind="client_otp",
            subject="+5511900000683",
            secret_hash=token_hash("123456"),
            expires_at=now() + timedelta(minutes=10),
        )
        duplicate = AuthChallenge(
            kind="client_otp",
            subject=other.phone_e164,
            secret_hash=token_hash("654321"),
            expires_at=now() + timedelta(minutes=10),
        )
        db.add_all([successful, duplicate])
        db.commit()
        target_id = target.id
        registration_id = registration.id
        session_id = session.id
        successful_id = successful.id
        duplicate_id = duplicate.id

    changed = client.post(
        f"/admin/clients/{target_id}/phone",
        json={
            "phone_e164": "+55 11 90000-0683",
            "challenge_id": str(successful_id),
            "code": "123456",
        },
    )
    assert changed.status_code == 200
    assert changed.json()["id"] == str(target_id)
    with SessionLocal() as db:
        assert db.get(Client, target_id).phone_e164 == "+5511900000683"
        assert db.get(ParentGalleryRegistration, registration_id).client_id == target_id
        assert db.get(AuthSession, session_id).revoked_at is not None

    refused = client.post(
        f"/admin/clients/{target_id}/phone",
        json={
            "phone_e164": "+5511900000682",
            "challenge_id": str(duplicate_id),
            "code": "654321",
        },
    )
    assert refused.status_code == 409
    assert refused.json()["detail"] == "Este WhatsApp já pertence a outra cliente."
    with SessionLocal() as db:
        assert db.get(Client, target_id).phone_e164 == "+5511900000683"


def test_deletion_reclassifies_a_commercial_race_and_rolls_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        target = add_client(db, "Corrida comercial", "+5511900000611")
        _, private, photo = add_gallery_graph(db, target, name="Privada corrida")
        selection = PhotoSelection(
            derived_gallery_id=private.id,
            photo_asset_id=photo.id,
            client_id=target.id,
        )
        db.add(selection)
        db.commit()
        target_id, gallery_id, selection_id = target.id, private.id, selection.id

    original = client_lifecycle.deletion_inventory
    calls = 0

    def raced_inventory(db, target):
        nonlocal calls
        calls += 1
        inventory = original(db, target)
        if calls == 2:
            inventory["commercial_protected"]["orders"] = 1
            inventory["can_delete"] = False
        return inventory

    monkeypatch.setattr(client_lifecycle, "deletion_inventory", raced_inventory)
    response = client.delete(
        f"/admin/clients/{target_id}",
        headers={"Idempotency-Key": "delete-client-race-0001"},
    )
    assert response.status_code == 409
    with SessionLocal() as db:
        assert db.get(Client, target_id) is not None
        assert db.get(DerivedGallery, gallery_id) is not None
        assert db.get(PhotoSelection, selection_id) is not None
        assert db.scalar(
            select(ClientDeletionReceipt).where(
                ClientDeletionReceipt.target_client_id == target_id
            )
        ) is None


def test_payment_delivery_is_protected_by_its_commercial_source(client: TestClient) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        target = add_client(db, "Entrega protegida", "+5511900000651")
        _, private, _ = add_gallery_graph(db, target, name="Privada com entrega")
        order = SaleOrder(
            derived_gallery_id=private.id,
            client_id=target.id,
            payment_status="confirmed",
            total_cents=700,
            checkout_key="test-order-1",
        )
        db.add(order)
        db.flush()
        communication = PaymentCommunication(
            sale_order_id=order.id,
            client_id=target.id,
            idempotency_key="protected-payment-communication-0001",
            status="confirmed",
        )
        db.add(communication)
        db.flush()
        notification = PaymentNotificationOutbox(
            payment_communication_id=communication.id,
            recipient_phone=target.phone_e164,
            template_kind="confirmed",
            idempotency_key="protected-payment-notification-0001",
        )
        db.add(notification)
        db.flush()
        db.add(
            WhatsAppDelivery(
                kind="payment",
                source_type="payment_notification_outbox",
                source_id=str(notification.id),
                recipient_phone=target.phone_e164,
                template_kind="confirmed",
                idempotency_key="protected-payment-delivery-0001",
                status="delivered",
            )
        )
        db.commit()
        target_id = target.id
    inventory = client.get(f"/admin/clients/{target_id}/deletion-inventory").json()
    assert inventory["commercial_protected"]["payment_deliveries"] == 1
    assert inventory["can_delete"] is False
    response = client.delete(
        f"/admin/clients/{target_id}",
        headers={"Idempotency-Key": "delete-payment-delivery-0001"},
    )
    assert response.status_code == 409


def test_deletion_never_claims_state_from_a_retired_phone_reused_by_another_client(
    client: TestClient,
) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        former_owner = add_client(db, "Telefone anterior", "+5511900000671")
        previous_record = db.scalar(
            select(ClientPhone).where(ClientPhone.client_id == former_owner.id)
        )
        assert previous_record is not None
        previous_record.active = False
        previous_record.retired_at = now()
        former_owner.phone_e164 = "+5511900000672"
        db.add(
            ClientPhone(
                client_id=former_owner.id,
                phone_e164=former_owner.phone_e164,
                active=True,
                verified_at=now(),
            )
        )
        current_owner = add_client(db, "Dona atual", "+5511900000671")
        challenge = AuthChallenge(
            kind="client_otp",
            subject=current_owner.phone_e164,
            secret_hash="synthetic",
            expires_at=now() + timedelta(minutes=10),
        )
        db.add(challenge)
        db.flush()
        delivery = WhatsAppDelivery(
            kind="otp",
            source_type="auth_challenge",
            source_id=str(challenge.id),
            recipient_phone=current_owner.phone_e164,
            template_kind="client_otp",
            idempotency_key="reused-phone-otp-delivery-0001",
            status="accepted",
        )
        db.add(delivery)
        db.flush()
        db.add(
            WhatsAppDelivery(
                kind="payment",
                source_type="payment_notification_outbox",
                source_id=str(uuid4()),
                recipient_phone=current_owner.phone_e164,
                template_kind="confirmed",
                idempotency_key="orphan-old-phone-payment-0001",
                status="delivered",
            )
        )
        db.commit()
        former_owner_id = former_owner.id
        current_owner_id = current_owner.id
        challenge_id = challenge.id
        delivery_id = delivery.id

    inventory = client.get(
        f"/admin/clients/{former_owner_id}/deletion-inventory"
    ).json()
    assert inventory["commercial_protected"]["payment_deliveries"] == 0
    assert inventory["operational_removable"]["otp_challenges"] == 0
    assert inventory["operational_removable"]["otp_deliveries"] == 0

    deleted = client.delete(
        f"/admin/clients/{former_owner_id}",
        headers={"Idempotency-Key": "delete-former-phone-owner-0001"},
    )
    assert deleted.status_code == 200
    with SessionLocal() as db:
        assert db.get(Client, former_owner_id) is None
        assert db.get(Client, current_owner_id) is not None
        assert db.get(AuthChallenge, challenge_id) is not None
        assert db.get(WhatsAppDelivery, delivery_id) is not None


def test_deletion_removes_otp_challenge_delivery_and_attempt(client: TestClient) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        target = add_client(db, "OTP transitório", "+5511900000661")
        challenge = AuthChallenge(
            kind="client_otp",
            subject=target.phone_e164,
            subject_fingerprint=None,
            secret_hash="synthetic",
            expires_at=now() + timedelta(minutes=10),
        )
        db.add(challenge)
        db.flush()
        delivery = WhatsAppDelivery(
            kind="otp",
            source_type="auth_challenge",
            source_id=str(challenge.id),
            recipient_phone=target.phone_e164,
            template_kind="client_otp",
            idempotency_key="test-otp-1",
            status="accepted",
        )
        db.add(delivery)
        db.flush()
        db.add(
            WhatsAppDeliveryAttempt(
                delivery_id=delivery.id,
                attempt_number=1,
                result="accepted",
            )
        )
        db.commit()
        target_id, challenge_id, delivery_id = target.id, challenge.id, delivery.id
    response = client.delete(
        f"/admin/clients/{target_id}",
        headers={"Idempotency-Key": "delete-client-otp-state-0001"},
    )
    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.get(AuthChallenge, challenge_id) is None
        assert db.get(WhatsAppDelivery, delivery_id) is None


def test_deletion_removes_transient_facial_request_and_reference_file(
    client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authenticate_admin(client)
    reference_root = tmp_path / "facial-references"
    monkeypatch.setenv("FACIAL_REFERENCE_ROOT", str(reference_root))
    with SessionLocal() as db:
        target = add_client(db, "Busca transitória", "+5511900000701")
        parent = ParentGallery(name="Pública facial")
        db.add(parent)
        db.flush()
        policy = GalleryFacialPolicy(
            parent_gallery_id=parent.id,
            status="active",
            legal_notice_version="notice-v1",
            legal_basis_reference="synthetic-only",
            retention_policy_version="retention-v1",
            minor_policy_version="minor-disabled-v1",
            model_version="model-v1",
            quality_version="quality-v1",
            calibration_version="calibration-v1",
            index_generation=1,
        )
        db.add(policy)
        db.flush()
        search = FacialSearchRequest(
            parent_gallery_id=parent.id,
            client_id=target.id,
            policy_id=policy.id,
            status="queued",
            consent_version="consent-v1",
            legal_notice_version="notice-v1",
            subject_declaration="adult",
            model_version="model-v1",
            quality_version="quality-v1",
            index_generation=1,
            expires_at=now() + timedelta(minutes=15),
        )
        db.add(search)
        db.commit()
        target_id, search_id = target.id, search.id
    reference_root.mkdir(parents=True)
    reference_path = reference_root / f"{search_id}.reference"
    reference_path.write_bytes(b"synthetic-encrypted-reference")

    inventory = client.get(f"/admin/clients/{target_id}/deletion-inventory").json()
    assert inventory["can_delete"] is True
    assert inventory["operational_removable"]["facial_searches"] == 1
    response = client.delete(
        f"/admin/clients/{target_id}",
        headers={"Idempotency-Key": "delete-client-facial-0001"},
    )
    assert response.status_code == 200
    assert not reference_path.exists()
    with SessionLocal() as db:
        assert db.get(FacialSearchRequest, search_id) is None
