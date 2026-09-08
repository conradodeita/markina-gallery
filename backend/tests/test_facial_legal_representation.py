"""Escopo, validade, autoridade e minimização da representação legal facial."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    AuditEvent,
    Base,
    Client,
    FacialLegalRepresentation,
    ParentGallery,
    ParentGalleryRegistration,
    now,
)
from app.facial.representation import (
    FacialLegalRepresentationError,
    create_legal_representation,
    require_valid_legal_representation,
    revoke_legal_representation,
)


def _fixture() -> tuple[
    Session, AdminUser, Client, Client, ParentGallery, ParentGallery
]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    admin = AdminUser(
        id=uuid4(),
        email="admin-representation@example.test",
        password_hash="unused",
        totp_secret="unused",
    )
    client = Client(
        id=uuid4(), full_name="Cliente A", phone_e164="+5511999999801"
    )
    other_client = Client(
        id=uuid4(), full_name="Cliente B", phone_e164="+5511999999802"
    )
    gallery = ParentGallery(id=uuid4(), name="Evento A")
    other_gallery = ParentGallery(id=uuid4(), name="Evento B")
    db.add_all((admin, client, other_client, gallery, other_gallery))
    db.flush()
    db.add_all(
        (
            ParentGalleryRegistration(
                parent_gallery_id=gallery.id,
                client_id=client.id,
                status="active",
            ),
            ParentGalleryRegistration(
                parent_gallery_id=other_gallery.id,
                client_id=client.id,
                status="active",
            ),
            ParentGalleryRegistration(
                parent_gallery_id=gallery.id,
                client_id=other_client.id,
                status="active",
            ),
        )
    )
    db.commit()
    return db, admin, client, other_client, gallery, other_gallery


def _create(
    db: Session, admin: AdminUser, client: Client, gallery: ParentGallery
) -> FacialLegalRepresentation:
    return create_legal_representation(
        db,
        client_id=client.id,
        parent_gallery_id=gallery.id,
        subject_scope_reference="subject-scope-opaque-01",
        authority_kind="parent",
        verification_method="admin_attestation",
        terms_version="minor-consent-v1",
        evidence_reference="evidence-opaque-01",
        verified_by_admin_id=admin.id,
        expires_at=now() + timedelta(days=30),
    )


def test_valid_representation_is_strictly_bound_to_client_gallery_and_terms() -> None:
    db, admin, client, other_client, gallery, other_gallery = _fixture()
    item = _create(db, admin, client, gallery)
    db.commit()

    assert require_valid_legal_representation(
        db,
        representation_reference=str(item.id),
        client_id=client.id,
        parent_gallery_id=gallery.id,
        terms_version="minor-consent-v1",
    ).id == item.id
    for changed_scope in (
        {"client_id": other_client.id, "parent_gallery_id": gallery.id},
        {"client_id": client.id, "parent_gallery_id": other_gallery.id},
    ):
        with pytest.raises(FacialLegalRepresentationError, match="indisponível"):
            require_valid_legal_representation(
                db,
                representation_reference=str(item.id),
                terms_version="minor-consent-v1",
                **changed_scope,
            )
    with pytest.raises(FacialLegalRepresentationError, match="indisponível"):
        require_valid_legal_representation(
            db,
            representation_reference=str(item.id),
            client_id=client.id,
            parent_gallery_id=gallery.id,
            terms_version="minor-consent-v2",
        )


def test_expiration_revocation_and_invalid_authority_fail_closed() -> None:
    db, admin, client, _other_client, gallery, _other_gallery = _fixture()
    item = _create(db, admin, client, gallery)
    db.commit()

    with pytest.raises(FacialLegalRepresentationError, match="indisponível"):
        require_valid_legal_representation(
            db,
            representation_reference=str(item.id),
            client_id=client.id,
            parent_gallery_id=gallery.id,
            terms_version="minor-consent-v1",
            at=now() + timedelta(days=31),
        )
    revoke_legal_representation(
        db, representation_id=item.id, actor_admin_id=admin.id
    )
    revoke_legal_representation(
        db, representation_id=item.id, actor_admin_id=admin.id
    )
    db.commit()
    with pytest.raises(FacialLegalRepresentationError, match="indisponível"):
        require_valid_legal_representation(
            db,
            representation_reference=str(item.id),
            client_id=client.id,
            parent_gallery_id=gallery.id,
            terms_version="minor-consent-v1",
        )
    assert len(
        list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.event == "facial.legal_representation_revoked"
                )
            )
        )
    ) == 1
    with pytest.raises(FacialLegalRepresentationError, match="Autoridade"):
        create_legal_representation(
            db,
            client_id=client.id,
            parent_gallery_id=gallery.id,
            subject_scope_reference="scope-2",
            authority_kind="self_declaration",
            verification_method="admin_attestation",
            terms_version="minor-consent-v1",
            evidence_reference="evidence-2",
            verified_by_admin_id=admin.id,
            expires_at=now() + timedelta(days=1),
        )


def test_representation_schema_and_audit_are_minimized() -> None:
    db, admin, client, _other_client, gallery, _other_gallery = _fixture()
    item = _create(db, admin, client, gallery)
    db.commit()
    columns = {column["name"] for column in inspect(db.bind).get_columns(item.__tablename__)}
    forbidden_columns = {
        "name",
        "phone",
        "birth_date",
        "document_number",
        "document_image",
        "photo",
        "embedding",
        "biometric_payload",
    }
    assert columns.isdisjoint(forbidden_columns)
    audit = " ".join(db.scalars(select(AuditEvent.subject)))
    assert item.subject_scope_reference not in audit
    assert item.evidence_reference not in audit
    assert client.full_name not in audit
    assert client.phone_e164 not in audit
