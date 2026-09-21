"""Consulta sintética por região e consentimento infantil sem prova administrativa."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from test_facial_search_worker import (
    Provider,
    _add_photo,
    _base,
    _face,
    _index_photo,
    _jpeg,
    _settings,
    _vector,
)

from app.auth import FacialSearchNotificationOutbox, PhotoFaceEmbedding
from app.facial.crypto import FacialCipher
from app.facial.jobs import FacialJobRepository
from app.facial.search import FacialSearchError, cancel_search_request, create_search_request
from app.facial.search_worker import process_claimed_search_job
from app.public_gallery_access import PublicGalleryAccessDenied


def test_region_contract_accepts_only_an_opaque_id_and_rejects_file_fields():
    from pydantic import ValidationError

    from app.main import FaceRegionSearchInput

    region_id = uuid4()
    value = FaceRegionSearchInput.model_validate({"face_region_id": str(region_id)})
    assert value.face_region_id == region_id
    assert value.consent_version is None and value.subject_declaration is None
    with pytest.raises(ValidationError):
        FaceRegionSearchInput.model_validate({"face_region_id": str(region_id), "file": "image"})


@pytest.mark.parametrize("invalidated", [False, True])
def test_region_has_no_upload_or_consent_and_rechecks_region(tmp_path, monkeypatch, invalidated):
    monkeypatch.setenv("APP_ENV", "test")
    engine, db, gallery, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    photo = _add_photo(db, gallery, folder, tmp_path)
    _index_photo(db, photo, tmp_path, settings, cipher)
    region = db.scalar(select(PhotoFaceEmbedding))
    region.bbox_x, region.bbox_y, region.bbox_width, region.bbox_height = .1, .1, .2, .2
    db.commit()
    common = {"db": db, "parent_gallery_id": gallery.id, "client_id": client.id,
              "consent_version": None, "subject_declaration": None,
              "representation_reference": None, "settings": settings}
    with pytest.raises(FacialSearchError):
        create_search_request(**common, payload=b"", reference_region_id=uuid4())
    with pytest.raises(FacialSearchError):
        create_search_request(**common, payload=_jpeg(), reference_region_id=region.id)
    with pytest.raises(PublicGalleryAccessDenied):
        create_search_request(**{**common, "client_id": uuid4()}, payload=b"", reference_region_id=region.id)
    with pytest.raises(FacialSearchError):
        create_search_request(**{**common, "parent_gallery_id": uuid4()}, payload=b"", reference_region_id=region.id)
    region.model_version = "obsolete-model"
    db.commit()
    with pytest.raises(FacialSearchError):
        create_search_request(**common, payload=b"", reference_region_id=region.id)
    region.model_version = settings.model_version
    db.commit()
    request = create_search_request(**common, payload=b"", reference_region_id=region.id)
    db.commit()
    assert not list(settings.reference_root.glob("**/*"))
    if invalidated:
        db.delete(region)
        db.commit()
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=120, job_class="search")
    process_claimed_search_job(db, claim, repository=repository, provider=None,
                              cipher=cipher, settings=settings, max_attempts=1)
    db.refresh(request)
    assert request.status == ("failed" if invalidated else "ready")
    assert request.consent_version is None and request.subject_declaration is None
    assert request.reference_region_id is None
    assert request.reference_source == "indexed_region"
    assert db.scalar(select(FacialSearchNotificationOutbox)) is not None
    cancel_search_request(db, parent_gallery_id=gallery.id, client_id=client.id,
                          request_id=request.id, settings=settings)
    db.commit()
    assert request.status == "cancelled"
    db.close()
    engine.dispose()


@pytest.mark.parametrize("cancelled", [False, True])
def test_minor_consent_runs_without_representation_and_can_be_revoked(tmp_path, monkeypatch, cancelled):
    monkeypatch.setenv("APP_ENV", "test")
    engine, db, gallery, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    photo = _add_photo(db, gallery, folder, tmp_path)
    _index_photo(db, photo, tmp_path, settings, cipher)
    request = create_search_request(db, parent_gallery_id=gallery.id, client_id=client.id,
                                    consent_version=settings.consent_version, subject_declaration="minor",
                                    consent_accepted=True, representation_reference=None,
                                    payload=_jpeg(), settings=settings)
    db.commit()
    repository = FacialJobRepository()
    if cancelled:
        cancel_search_request(db, parent_gallery_id=gallery.id, client_id=client.id,
                              request_id=request.id, settings=settings)
        db.commit()
        assert repository.claim_next(db, lease_seconds=120, job_class="search") is None
    else:
        claim = repository.claim_next(db, lease_seconds=120, job_class="search")
        process_claimed_search_job(db, claim, repository=repository,
                                  provider=Provider([_face(_vector(1.0))]), cipher=cipher, settings=settings)
    db.refresh(request)
    assert request.status == ("cancelled" if cancelled else "ready")
    assert request.authorization_method == "explicit_consent"
    assert request.representation_reference is None
    assert request.reference_deleted_at is not None
    db.close()
    engine.dispose()
