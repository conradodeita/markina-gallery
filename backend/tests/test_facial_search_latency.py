"""Regressões sintéticas de custo, progresso e revalidação da consulta."""

from datetime import timedelta
from time import perf_counter
from uuid import uuid4

import pytest
from sqlalchemy import event, select

from app.auth import (
    FacialJob,
    FacialSearchCandidate,
    FacialSearchSnapshotItem,
    GalleryClientState,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFaceEmbedding,
    now,
)
from app.facial.crypto import FacialCipher
from app.facial.jobs import FacialJobRepository
from app.facial.search import cancel_search_request
from app.facial.search_worker import (
    _comparison_photo_is_current,
    _request_is_authorized,
    process_claimed_search_job,
)
from tests.test_facial_search_worker import (
    Provider,
    _add_photo,
    _base,
    _create_request,
    _face,
    _index_photo,
    _settings,
    _vector,
)


def test_search_does_not_reload_the_whole_snapshot_for_each_face(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    root = tmp_path / "derivatives"
    photos = [_add_photo(db, parent, folder, root) for _ in range(8)]
    for photo in photos:
        _index_photo(db, photo, root, settings, cipher)
    request = _create_request(db, parent, client, settings)
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=120, job_class="search")
    full_snapshot_reads = []

    def capture(_conn, _cursor, statement, _parameters, _context, _many):
        lowered = statement.lower()
        if ("from facial_search_snapshot_item" in lowered
                and "facial_search_snapshot_item.photo_asset_id =" not in lowered
                and "facial_search_snapshot_item.id =" not in lowered):
            full_snapshot_reads.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        outcome = process_claimed_search_job(
            db, claim, repository=repository, provider=Provider([_face(_vector(1))]),
            cipher=cipher, settings=settings,
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert outcome.status == "completed"
    assert request.status == "ready"
    assert set(db.scalars(select(FacialSearchCandidate.photo_asset_id))) == {
        photo.id for photo in photos
    }
    # Preparation, pinned index and publication may read the snapshot;
    # comparison must use point lookups regardless of the number of faces.
    assert len(full_snapshot_reads) <= 4
    db.close()
    engine.dispose()


def test_multiple_faces_cross_batches_without_duplicate_progress_or_results(tmp_path, monkeypatch):
    from app.facial.engine import search_gallery_index

    monkeypatch.setenv("APP_ENV", "test")
    engine, db, parent, _client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    root = tmp_path / "derivatives"
    photos = [_add_photo(db, parent, folder, root) for _ in range(3)]
    fingerprints = {}
    for photo in photos:
        _index_photo(db, photo, root, settings, cipher)
        face = db.scalar(select(PhotoFaceEmbedding).where(
            PhotoFaceEmbedding.photo_asset_id == photo.id,
        ))
        fingerprints[photo.id] = face.preview_fingerprint
        db.add_all(PhotoFaceEmbedding(
            tenant_id=photo.tenant_id, parent_gallery_id=parent.id,
            photo_asset_id=photo.id, face_ordinal=ordinal,
            model_id=face.model_id, embedding_dimension=face.embedding_dimension,
            model_version=face.model_version, quality_version=face.quality_version,
            preview_fingerprint=face.preview_fingerprint, quality_band=face.quality_band,
            payload_ciphertext=face.payload_ciphertext, payload_nonce=face.payload_nonce,
            key_id=face.key_id,
        ) for ordinal in range(1, 130))
        db.commit()
    progress = []
    batch_reads = []

    def capture(_conn, _cursor, statement, parameters, _context, _many):
        if "FROM photo_face_embedding JOIN photo_asset" in statement:
            batch_reads.append(parameters)
            assert "LIMIT" in statement
            assert parameters[-2] == 128

    event.listen(engine, "before_cursor_execute", capture)
    try:
        matches = search_gallery_index(
            db, gallery_id=parent.id, tenant_id=parent.tenant_id,
            query_embedding=_vector(1), cipher=cipher, settings=settings,
            threshold_milli=750, allowed_fingerprints=fingerprints,
            on_progress=lambda done: (progress.append(done), db.commit()),
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert [match.photo_id for match in matches] == sorted(
        (photo.id for photo in photos), key=str,
    )
    assert all(match.match_class == "matched" for match in matches)
    assert progress == [1, 2, 3]
    assert len(batch_reads) == 5  # 390 faces / 128 + final empty page
    db.close()
    engine.dispose()


def test_worker_renews_lease_during_comparison_with_real_photo_progress(tmp_path, monkeypatch):
    from app import auth
    from app.facial import jobs, search_worker

    monkeypatch.setenv("APP_ENV", "test")
    engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    root = tmp_path / "derivatives"
    photos = [_add_photo(db, parent, folder, root) for _ in range(8)]
    for photo in photos:
        _index_photo(db, photo, root, settings, cipher)
    request = _create_request(db, parent, client, settings)
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=120, job_class="search")
    started_at = now()
    elapsed = [0]
    monkeypatch.setattr(auth, "now", lambda: started_at + timedelta(seconds=elapsed[0]))
    monkeypatch.setattr(jobs, "now", auth.now)
    monkeypatch.setattr(search_worker, "now", auth.now)
    monkeypatch.setattr(search_worker, "monotonic", lambda: elapsed[0])
    progress = []

    class SlowCipher:
        def __getattr__(self, name):
            return getattr(cipher, name)

        def decrypt(self, envelope, *, scope):
            payload = cipher.decrypt(envelope, scope=scope)
            if scope.object_kind == "photo":
                elapsed[0] += 40
                current = db.get(FacialJob, claim.id)
                progress.append((request.compare_done, current.lease_expires_at))
            return payload

    outcome = process_claimed_search_job(
        db, claim, repository=repository, provider=Provider([_face(_vector(1))]),
        cipher=SlowCipher(), settings=settings,
    )
    assert elapsed[0] == 320  # Longer than the original 120-second lease.
    assert outcome.status == "completed" and outcome.attempts == 1
    assert request.status == "ready" and request.compare_done == 8
    assert [done for done, _expiry in progress] == list(range(8))
    assert len({expiry for _done, expiry in progress}) > 1
    db.close()
    engine.dispose()


def test_index_volume_matches_real_gallery_shape_without_unbounded_reads(tmp_path, monkeypatch):
    import json

    from app.facial.engine import _embedding_scope, search_gallery_index

    monkeypatch.setenv("APP_ENV", "test")
    engine, db, parent, _client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    fingerprints = {}
    photos = []
    faces = []
    for index in range(2691):
        photo_id = uuid4()
        photos.append(PhotoAsset(
            id=photo_id, tenant_id=parent.tenant_id, parent_gallery_id=parent.id,
            folder_id=folder.id, filename="synthetic.jpg",
            storage_key=f"{parent.id}/{photo_id}.jpg", available=True,
        ))
        fingerprints[photo_id] = "a" * 64
        payload = json.dumps({"embedding": _vector(1)}).encode()
        envelope = cipher.encrypt(payload, scope=_embedding_scope(
            settings=settings, gallery_id=parent.id, photo_id=photo_id,
            model_version=settings.model_version, quality_version=settings.quality_version,
        ))
        for ordinal in range(3 if index < 233 else 4):
            faces.append(PhotoFaceEmbedding(
                tenant_id=parent.tenant_id, parent_gallery_id=parent.id, photo_asset_id=photo_id,
                face_ordinal=ordinal, model_id="opencv-yunet-sface", embedding_dimension=128,
                model_version=settings.model_version, quality_version=settings.quality_version,
                preview_fingerprint="a" * 64, quality_band="best",
                payload_ciphertext=envelope.ciphertext, payload_nonce=envelope.nonce,
                key_id=envelope.key_id,
            ))
    assert len(faces) == 10531
    db.add_all(photos)
    db.flush()
    db.add_all(faces)
    db.commit()
    gallery_id, tenant_id = parent.id, parent.tenant_id
    db.expunge_all()
    progress = []
    batch_count = [0]

    def capture(_conn, _cursor, statement, parameters, _context, _many):
        if "FROM photo_face_embedding JOIN photo_asset" in statement:
            assert "LIMIT" in statement and parameters[-2] == 128
            batch_count[0] += 1

    event.listen(engine, "before_cursor_execute", capture)
    started_at = perf_counter()
    try:
        matches = search_gallery_index(
            db, gallery_id=gallery_id, tenant_id=tenant_id,
            query_embedding=_vector(1), cipher=cipher, settings=settings,
            threshold_milli=750, allowed_fingerprints=fingerprints, on_progress=progress.append,
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert len(matches) == 2691
    assert progress == list(range(1, 2692))
    assert batch_count[0] == 84  # 83 bounded pages plus EOF.
    assert len(db.identity_map) < 20  # Embedding rows are not materialized as ORM entities.
    print(f"synthetic 2691 photos / 10531 faces: {perf_counter() - started_at:.2f}s")
    db.close()
    engine.dispose()


@pytest.mark.parametrize("interruption", ["cancel", "expired_lease"])
def test_interruption_during_decrypt_does_not_publish_or_crash_worker(
    tmp_path, monkeypatch, interruption,
):
    monkeypatch.setenv("APP_ENV", "test")
    engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    root = tmp_path / "derivatives"
    photos = [_add_photo(db, parent, folder, root) for _ in range(2)]
    for photo in photos:
        _index_photo(db, photo, root, settings, cipher)
    request = _create_request(db, parent, client, settings)
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=120, job_class="search")
    decrypted_photos = []

    class InterruptedCipher:
        def __getattr__(self, name):
            return getattr(cipher, name)

        def decrypt(self, envelope, *, scope):
            payload = cipher.decrypt(envelope, scope=scope)
            if scope.object_kind == "photo":
                decrypted_photos.append(scope.object_id)
                assert len(decrypted_photos) == 1
                if interruption == "cancel":
                    cancel_search_request(
                        db, parent_gallery_id=parent.id, client_id=client.id,
                        request_id=request.id, settings=settings,
                    )
                else:
                    db.get(FacialJob, claim.id).lease_expires_at = now() - timedelta(seconds=1)
                db.commit()
            return payload

    outcome = process_claimed_search_job(
        db, claim, repository=repository, provider=Provider([_face(_vector(1))]),
        cipher=InterruptedCipher(), settings=settings,
    )
    assert len(decrypted_photos) == 1
    assert list(db.scalars(select(FacialSearchCandidate))) == []
    assert outcome.last_error_category is None
    if interruption == "cancel":
        assert outcome.status == "cancelled"
        assert request.status == "cancelled" and request.reference_deleted_at is not None
    else:
        assert outcome.status == "queued" and outcome.lease_token is None
        next_claim = repository.claim_next(db, lease_seconds=120, job_class="search")
        assert next_claim.id == claim.id
        resumed = process_claimed_search_job(
            db, next_claim, repository=repository, provider=Provider([_face(_vector(1))]),
            cipher=cipher, settings=settings,
        )
        assert resumed.status == "completed" and request.status == "ready"
    db.close()
    engine.dispose()


def test_photo_with_index_invalidated_after_decrypt_is_not_published(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    root = tmp_path / "derivatives"
    photo = _add_photo(db, parent, folder, root)
    _index_photo(db, photo, root, settings, cipher)
    request = _create_request(db, parent, client, settings)
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=120, job_class="search")

    class InvalidatedCipher:
        def __getattr__(self, name):
            return getattr(cipher, name)

        def decrypt(self, envelope, *, scope):
            payload = cipher.decrypt(envelope, scope=scope)
            if scope.object_kind == "photo":
                db.scalar(select(FacialJob).where(FacialJob.kind == "index")).status = "queued"
                db.commit()
            return payload

    outcome = process_claimed_search_job(
        db, claim, repository=repository, provider=Provider([_face(_vector(1))]),
        cipher=InvalidatedCipher(), settings=settings,
    )
    assert outcome.status == "completed" and request.status == "no_candidates"
    assert list(db.scalars(select(FacialSearchCandidate))) == []
    db.close()
    engine.dispose()


@pytest.mark.parametrize("revocation", [
    "client_blocked", "registration", "collective", "gallery", "policy",
    "model", "quality", "generation", "notice",
])
def test_condensed_request_guard_preserves_access_and_version_gates(
    tmp_path, monkeypatch, revocation,
):
    monkeypatch.setenv("APP_ENV", "test")
    engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    root = tmp_path / "derivatives"
    photo = _add_photo(db, parent, folder, root)
    _index_photo(db, photo, root, settings, cipher)
    request = _create_request(db, parent, client, settings)
    assert _request_is_authorized(db, request, settings)
    policy = db.scalar(select(GalleryFacialPolicy))
    if revocation == "client_blocked":
        db.add(GalleryClientState(
            tenant_id=parent.tenant_id, parent_gallery_id=parent.id,
            client_id=client.id, status="blocked",
        ))
    elif revocation == "registration":
        db.scalar(select(ParentGalleryRegistration)).status = "expired"
    elif revocation == "collective":
        parent.access_mode = "collective_protected"
    elif revocation == "gallery":
        parent.active = False
    elif revocation == "policy":
        policy.status = "suspended"
    elif revocation == "model":
        policy.model_version = "other-model"
    elif revocation == "quality":
        policy.quality_version = "other-quality"
    elif revocation == "generation":
        policy.index_generation += 1
    else:
        policy.legal_notice_version = "other-notice"
    db.commit()
    assert not _request_is_authorized(db, request, settings)
    db.close()
    engine.dispose()


@pytest.mark.parametrize("change", ["unavailable", "preview", "folder", "index", "fingerprint"])
def test_pinned_photo_is_revalidated_without_mutating_snapshot(tmp_path, monkeypatch, change):
    monkeypatch.setenv("APP_ENV", "test")
    engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    root = tmp_path / "derivatives"
    photo = _add_photo(db, parent, folder, root)
    _index_photo(db, photo, root, settings, cipher)
    request = _create_request(db, parent, client, settings)
    snapshot = db.scalar(select(FacialSearchSnapshotItem))
    fingerprint = snapshot.preview_fingerprint
    assert _comparison_photo_is_current(db, request, photo.id, fingerprint)
    if change == "unavailable":
        photo.available = False
    elif change == "preview":
        db.scalar(select(MediaDerivative).where(
            MediaDerivative.photo_asset_id == photo.id,
            MediaDerivative.variant == "client_preview",
        )).status = "failed"
    elif change == "folder":
        folder.status = "hidden"
    elif change == "index":
        db.scalar(select(FacialJob).where(FacialJob.kind == "index")).status = "failed"
    else:
        db.scalar(select(FacialJob).where(FacialJob.kind == "index")).preview_fingerprint = "b" * 64
    db.commit()
    assert not _comparison_photo_is_current(db, request, photo.id, fingerprint)
    assert snapshot.preview_fingerprint == fingerprint
    assert snapshot.status == "ready"
    db.close()
    engine.dispose()
