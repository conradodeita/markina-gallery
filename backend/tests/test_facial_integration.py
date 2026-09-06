"""Ciclo facial sintético integrado sem criar capacidade fora da Galeria pública."""

from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    Base,
    Client,
    DerivedGallery,
    FacialJob,
    FacialSearchCandidate,
    GalleryFacialPolicy,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFaceEmbedding,
    PhotoFolder,
    PhotoSelection,
    PriceRule,
)
from app.facial.config import facial_settings_from_environment
from app.facial.crypto import FacialCipher
from app.facial.jobs import FacialJobRepository
from app.facial.policy import revoke_policy
from app.facial.provider import FaceObservation, normalize_embedding
from app.facial.search import authorize_search_candidate_selection, create_search_request
from app.facial.search_worker import process_claimed_search_job
from app.facial.worker import process_claimed_index_job, process_claimed_purge_job
from app.gallery_pricing import quote_parent_gallery
from app.media import generate_derivatives
from app.private_derivation import derive_client_selection


def _jpeg(color: tuple[int, int, int]) -> bytes:
    stream = BytesIO()
    Image.new("RGB", (800, 600), color).save(stream, format="JPEG")
    return stream.getvalue()


def _face() -> FaceObservation:
    return FaceObservation(
        embedding=normalize_embedding([1.0, *([0.0] * 127)]),
        detection_confidence=0.99,
        box=(180, 120, 240, 240),
        landmarks=((230, 190), (360, 190), (295, 245), (245, 310), (345, 310)),
        blur_variance=120.0,
    )


class SyntheticAdultProvider:
    def __init__(self) -> None:
        self.query_faces = [_face()]

    def observe_path(self, _path: Path):
        return [_face()]

    def observe_bytes(self, _payload: bytes):
        return self.query_faces


def _configure(monkeypatch, tmp_path: Path) -> None:
    key = base64.urlsafe_b64encode(b"k" * 32).decode("ascii")
    manifest = Path(__file__).parents[1] / "facial-assets" / "model-manifest.json"
    values = {
        "APP_ENV": "test",
        "FACIAL_PROCESSING_ENABLED": "true",
        "FACIAL_CREDENTIAL_ENV": "test",
        "FACIAL_MODEL_MANIFEST_PATH": str(manifest),
        "FACIAL_MODEL_ROOT": str(tmp_path / "models"),
        "FACIAL_REFERENCE_ROOT": str(tmp_path / "references"),
        "FACIAL_MODEL_VERSION": "yunet-2023mar+sface-2021dec",
        "FACIAL_QUALITY_VERSION": "opencv-technical-v1",
        "FACIAL_CALIBRATION_VERSION": "synthetic-calibration-v1",
        "FACIAL_LEGAL_NOTICE_VERSION": "synthetic-notice-v1",
        "FACIAL_CONSENT_VERSION": "synthetic-consent-v1",
        "FACIAL_LEGAL_BASIS_REFERENCE": "synthetic-adults-only",
        "FACIAL_RETENTION_POLICY_VERSION": "synthetic-retention-v1",
        "FACIAL_MINOR_POLICY_VERSION": "minor-disabled-v1",
        "FACIAL_MINOR_SEARCH_ENABLED": "false",
        "FACIAL_AEAD_ACTIVE_KEY_ID": "test-key",
        "FACIAL_AEAD_KEYS_JSON": json.dumps({"test-key": key}),
        "MEDIA_SOURCE_ROOT": str(tmp_path / "source"),
        "MEDIA_DERIVATIVES_ROOT": str(tmp_path / "derivatives"),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_synthetic_upload_filter_selection_quote_and_revocation(
    tmp_path: Path, monkeypatch
) -> None:
    _configure(monkeypatch, tmp_path)
    settings = facial_settings_from_environment(verify_runtime_assets=False)
    cipher = FacialCipher(
        active_key_id=settings.active_key_id,
        keys=settings.aead_keys,
    )
    repository = FacialJobRepository()
    provider = SyntheticAdultProvider()
    db = Session(create_engine(f"sqlite:///{tmp_path / 'integration.db'}"))
    Base.metadata.create_all(db.bind)

    admin = AdminUser(
        id=uuid4(),
        email="admin.synthetic@example.invalid",
        password_hash="synthetic",
        email_verified=True,
        totp_secret="synthetic",
    )
    gallery = ParentGallery(
        id=uuid4(),
        name="Evento sintético adulto",
        pricing_mode="fixed",
        fixed_unit_price_cents=700,
    )
    folder = PhotoFolder(
        id=uuid4(),
        parent_gallery_id=gallery.id,
        name="Fotos sintéticas",
        status="preparing",
        purpose="content",
    )
    client = Client(
        id=uuid4(),
        full_name="Cliente sintética adulta",
        phone_e164="+5511999999998",
    )
    registration = ParentGalleryRegistration(
        parent_gallery_id=gallery.id,
        client_id=client.id,
        status="active",
    )
    db.add_all(
        (
            admin,
            gallery,
            folder,
            client,
            registration,
            PriceRule(
                parent_gallery_id=gallery.id,
                minimum_quantity=1,
                maximum_quantity=None,
                unit_price_cents=700,
            ),
        )
    )
    photos = []
    for index, color in enumerate(((210, 180, 160), (160, 190, 215)), start=1):
        photo = PhotoAsset(
            id=uuid4(),
            parent_gallery_id=gallery.id,
            folder_id=folder.id,
            filename=f"adulto-sintetico-{index}.jpg",
            storage_key=f"{gallery.id}/adulto-sintetico-{index}.jpg",
            available=False,
        )
        source = tmp_path / "source" / photo.storage_key
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(_jpeg(color))
        db.add(photo)
        photos.append(photo)
    db.commit()
    assert db.scalar(select(func.count()).select_from(GalleryFacialPolicy)) == 0

    # O upload gera a prévia e agenda o índice, mas continua válido mesmo se a
    # camada facial falhar separadamente.
    for photo in photos:
        derivatives = generate_derivatives(db, photo)
        assert any(item.variant == "client_preview" and item.status == "ready" for item in derivatives)
    assert all(photo.available for photo in photos)
    policy = db.scalar(
        select(GalleryFacialPolicy).where(
            GalleryFacialPolicy.parent_gallery_id == gallery.id
        )
    )
    assert policy is not None
    assert policy.status == "active"
    assert policy.actor_admin_id is None

    for _photo in photos:
        claim = repository.claim_next(db, lease_seconds=60)
        assert claim is not None
        process_claimed_index_job(
            db,
            claim,
            repository=repository,
            provider=provider,
            cipher=cipher,
            settings=settings,
            derivatives_root=tmp_path / "derivatives",
        )
    assert db.scalar(select(func.count()).select_from(PhotoFaceEmbedding)) == 2

    request = create_search_request(
        db,
        parent_gallery_id=gallery.id,
        client_id=client.id,
        consent_version=settings.consent_version,
        subject_declaration="adult",
        representation_reference=None,
        payload=_jpeg((200, 180, 170)),
        settings=settings,
    )
    db.commit()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None
    process_claimed_search_job(
        db,
        claim,
        repository=repository,
        provider=provider,
        cipher=cipher,
        settings=settings,
    )
    db.refresh(request)
    assert request.status == "ready" and request.reference_deleted_at is not None
    assert db.scalar(select(func.count()).select_from(DerivedGallery)) == 0

    authorize_search_candidate_selection(
        db,
        parent_gallery_id=gallery.id,
        client_id=client.id,
        request_id=request.id,
        photo_id=photos[0].id,
    )
    selected = derive_client_selection(
        db,
        parent_gallery_id=gallery.id,
        client_id=client.id,
        photo_id=photos[0].id,
    )
    db.commit()
    quote = quote_parent_gallery(db, gallery=gallery, quantity=1)
    assert selected.gallery_created is True
    assert quote.quote.total_cents == 700

    # Uma nova tentativa tecnicamente inválida não desfaz seleção, privada ou a
    # alternativa manual para uma segunda foto.
    provider.query_faces = []
    failed_filter = create_search_request(
        db,
        parent_gallery_id=gallery.id,
        client_id=client.id,
        consent_version=settings.consent_version,
        subject_declaration="adult",
        representation_reference=None,
        payload=_jpeg((190, 190, 190)),
        settings=settings,
    )
    db.commit()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None
    process_claimed_search_job(
        db,
        claim,
        repository=repository,
        provider=provider,
        cipher=cipher,
        settings=settings,
    )
    db.refresh(failed_filter)
    assert failed_filter.status == "no_face"
    manual = derive_client_selection(
        db,
        parent_gallery_id=gallery.id,
        client_id=client.id,
        photo_id=photos[1].id,
    )
    db.commit()
    assert manual.gallery.id == selected.gallery.id
    assert quote_parent_gallery(db, gallery=gallery, quantity=2).quote.total_cents == 1400

    revoke_policy(db, parent_gallery_id=gallery.id, actor_admin_id=admin.id)
    db.commit()
    purge_claim = repository.claim_next(db, lease_seconds=60)
    assert purge_claim is not None
    assert db.get(FacialJob, purge_claim.id).kind == "purge"
    process_claimed_purge_job(
        db,
        purge_claim,
        repository=repository,
        reference_root=settings.reference_root,
    )

    assert db.scalar(select(func.count()).select_from(PhotoFaceEmbedding)) == 0
    assert db.scalar(select(func.count()).select_from(FacialSearchCandidate)) == 0
    assert db.scalar(select(func.count()).select_from(PhotoSelection)) == 2
    assert db.get(DerivedGallery, selected.gallery.id) is not None
    assert all(db.get(PhotoAsset, photo.id) is not None for photo in photos)
