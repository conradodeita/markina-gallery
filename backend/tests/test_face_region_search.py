"""Consulta por região usa o vetor existente, com gates e snapshot normais."""

import json
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_facial_engine import _vector
from test_facial_search import _fixture, _settings

from app.auth import ParentGallery, ParentGalleryRegistration, PhotoAsset, PhotoFaceEmbedding
from app.facial.crypto import FacialCipher
from app.facial.engine import _embedding_scope
from app.facial.jobs import FacialJobRepository
from app.facial.regions import photo_regions
from app.facial.search import FacialSearchError, create_search_request, read_search_result
from app.facial.search_worker import process_claimed_search_job


def setup_region(tmp_path):
    db, gallery, client = _fixture(tmp_path, index_ready=True)
    settings = _settings(tmp_path)
    photo = db.scalar(select(PhotoAsset))
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    envelope = cipher.encrypt(
        json.dumps({"embedding": _vector(1)}).encode(),
        scope=_embedding_scope(
            settings=settings,
            gallery_id=gallery.id,
            photo_id=photo.id,
            model_version=settings.model_version,
            quality_version=settings.quality_version,
        ),
    )
    region = PhotoFaceEmbedding(
        photo_asset_id=photo.id,
        parent_gallery_id=gallery.id,
        face_ordinal=0,
        model_version=settings.model_version,
        quality_version=settings.quality_version,
        preview_fingerprint="a" * 64,
        bbox_x=0.2,
        bbox_y=0.2,
        bbox_width=0.2,
        bbox_height=0.2,
        quality_band="best",
        payload_ciphertext=envelope.ciphertext,
        payload_nonce=envelope.nonce,
        key_id=envelope.key_id,
    )
    db.add(region)
    db.commit()
    return db, gallery, client, settings, cipher, region


def test_click_search_never_calls_provider_or_stores_reference(tmp_path):
    db, gallery, client, settings, cipher, region = setup_region(tmp_path)
    regions = photo_regions(
        db,
        gallery_id=gallery.id,
        client_id=client.id,
        photo_id=region.photo_asset_id,
        settings=settings,
    )
    assert set(regions[0]) == {"id", "x", "y", "width", "height"}
    request = create_search_request(
        db,
        parent_gallery_id=gallery.id,
        client_id=client.id,
        consent_version=settings.consent_version,
        subject_declaration="adult",
        representation_reference=None,
        payload=b"",
        reference_region_id=region.id,
        settings=settings,
    )
    db.commit()
    assert request.reference_locator_ciphertext is None
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=120, job_class="search")
    process_claimed_search_job(
        db, claim, repository=repository, provider=None, cipher=cipher, settings=settings
    )
    request, candidates = read_search_result(
        db, parent_gallery_id=gallery.id, client_id=client.id, request_id=request.id
    )
    assert request.status == "ready"
    assert candidates[0].photo_asset_id == region.photo_asset_id
    assert candidates[0].match_class == "matched"
    assert not settings.reference_root.exists()


@pytest.mark.parametrize("invalid", ["missing", "model", "minor", "consent"])
def test_click_rejects_stale_region_incompatible_model_and_missing_consent(tmp_path, invalid):
    db, gallery, client, settings, _, region = setup_region(tmp_path)
    if invalid == "model":
        region.model_id = "edgeface"
        db.commit()
    with pytest.raises(FacialSearchError):
        create_search_request(
            db,
            parent_gallery_id=gallery.id,
            client_id=client.id,
            consent_version="wrong" if invalid == "consent" else settings.consent_version,
            subject_declaration="minor" if invalid == "minor" else "adult",
            representation_reference=None,
            payload=b"",
            reference_region_id=uuid4() if invalid == "missing" else region.id,
            settings=settings,
        )


def test_click_revalidates_revoked_membership_before_execution(tmp_path):
    db, gallery, client, settings, cipher, region = setup_region(tmp_path)
    request = create_search_request(
        db,
        parent_gallery_id=gallery.id,
        client_id=client.id,
        consent_version=settings.consent_version,
        subject_declaration="adult",
        representation_reference=None,
        payload=b"",
        reference_region_id=region.id,
        settings=settings,
    )
    db.scalar(select(ParentGalleryRegistration)).status = "expired"
    db.commit()
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=120, job_class="search")
    process_claimed_search_job(
        db, claim, repository=repository, provider=None, cipher=cipher, settings=settings
    )
    assert request.status == "cancelled"


def test_regions_disappear_immediately_when_policy_is_revoked(tmp_path):
    from app.auth import GalleryFacialPolicy

    db, gallery, client, settings, _, region = setup_region(tmp_path)
    db.scalar(select(GalleryFacialPolicy)).status = "disabled"
    db.commit()
    assert db.get(PhotoFaceEmbedding, region.id) is not None  # purge ainda não executado
    assert (
        photo_regions(
            db,
            gallery_id=gallery.id,
            client_id=client.id,
            photo_id=region.photo_asset_id,
            settings=settings,
        )
        == []
    )


def test_region_from_another_authorized_gallery_cannot_cross_scope(tmp_path):
    db, gallery, client, settings, _, region = setup_region(tmp_path)
    other = ParentGallery(name="Outro evento")
    db.add(other)
    db.flush()
    # Mesmo uma região existente é invisível ao escopo consultado.
    region.parent_gallery_id = other.id
    db.flush()
    assert (
        photo_regions(
            db,
            gallery_id=gallery.id,
            client_id=client.id,
            photo_id=region.photo_asset_id,
            settings=settings,
        )
        == []
    )
    with pytest.raises(FacialSearchError):
        create_search_request(
            db,
            parent_gallery_id=gallery.id,
            client_id=client.id,
            consent_version=settings.consent_version,
            subject_declaration="adult",
            representation_reference=None,
            payload=b"",
            reference_region_id=region.id,
            settings=settings,
        )


def test_http_regions_and_telemetry_require_sessions(tmp_path):
    from fastapi import HTTPException
    from starlette.requests import Request

    from app.main import admin_photo_facial_analysis, public_photo_face_regions

    db, gallery, _, _, _, region = setup_region(tmp_path)
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    for endpoint, args in (
        (public_photo_face_regions, (gallery.id, region.photo_asset_id)),
        (admin_photo_facial_analysis, (region.photo_asset_id,)),
    ):
        with pytest.raises(HTTPException) as error:
            endpoint(*args, request=request, db=db)
        assert error.value.status_code in {401, 403}


def test_gallery_purge_clears_region_reference_and_proof(tmp_path):
    from app.facial.purge import facial_cleanup_proof, purge_gallery_records

    db, gallery, client, settings, _, region = setup_region(tmp_path)
    item = create_search_request(
        db,
        parent_gallery_id=gallery.id,
        client_id=client.id,
        consent_version=settings.consent_version,
        subject_declaration="adult",
        representation_reference=None,
        payload=b"",
        reference_region_id=region.id,
        settings=settings,
    )
    db.commit()
    assert facial_cleanup_proof(db, parent_gallery_id=gallery.id)["references"] == 1
    purge_gallery_records(db, parent_gallery_id=gallery.id)
    db.commit()
    db.refresh(item)
    assert item.reference_region_id is None
    assert item.status == "cancelled"
    assert facial_cleanup_proof(db, parent_gallery_id=gallery.id)["clean"]


def test_cancel_clears_region_even_when_cleanup_jobs_are_cancelled(tmp_path):
    from app.facial.search import cancel_search_request

    db, gallery, client, settings, _, region = setup_region(tmp_path)
    item = create_search_request(
        db,
        parent_gallery_id=gallery.id,
        client_id=client.id,
        consent_version=settings.consent_version,
        subject_declaration="adult",
        representation_reference=None,
        payload=b"",
        reference_region_id=region.id,
        settings=settings,
    )
    db.commit()
    cancel_search_request(
        db, parent_gallery_id=gallery.id, client_id=client.id, request_id=item.id, settings=settings
    )
    assert item.reference_region_id is None
