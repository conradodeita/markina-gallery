from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.auth import (
    FacialJob,
    FacialSearchCandidate,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    FacialSearchSnapshotItem,
    GalleryFacialPolicy,
    PhotoAsset,
    PhotoFaceEmbedding,
)


def _constraint_names(model, kind):
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, kind)
    }


def test_facial_models_are_scoped_versioned_and_disabled_by_default() -> None:
    assert GalleryFacialPolicy.__table__.c.status.default.arg == "disabled"
    assert GalleryFacialPolicy.__table__.c.similarity_threshold_milli.default.arg == 750
    assert "uq_gallery_facial_policy_parent" in _constraint_names(
        GalleryFacialPolicy, UniqueConstraint
    )
    assert "uq_photo_asset_id_parent" in _constraint_names(PhotoAsset, UniqueConstraint)
    assert "fk_face_embedding_photo_parent" in _constraint_names(
        PhotoFaceEmbedding, ForeignKeyConstraint
    )
    assert "uq_face_embedding_versioned_photo_face" in _constraint_names(
        PhotoFaceEmbedding, UniqueConstraint
    )


def test_search_candidate_and_notification_enforce_full_scope() -> None:
    assert "uq_facial_search_scope" in _constraint_names(
        FacialSearchRequest, UniqueConstraint
    )
    assert "fk_facial_candidate_search_scope" in _constraint_names(
        FacialSearchCandidate, ForeignKeyConstraint
    )
    assert "fk_facial_snapshot_search_scope" in _constraint_names(
        FacialSearchSnapshotItem, ForeignKeyConstraint
    )
    assert "fk_facial_snapshot_photo_parent" in _constraint_names(
        FacialSearchSnapshotItem, ForeignKeyConstraint
    )
    assert "fk_facial_candidate_photo_parent" in _constraint_names(
        FacialSearchCandidate, ForeignKeyConstraint
    )
    assert "fk_facial_notification_search_scope" in _constraint_names(
        FacialSearchNotificationOutbox, ForeignKeyConstraint
    )
    assert "uq_facial_job_idempotency" in _constraint_names(FacialJob, UniqueConstraint)


def test_facial_models_never_define_plain_biometric_or_pii_columns() -> None:
    forbidden = {
        "embedding",
        "image",
        "photo_bytes",
        "similarity",
        "score",
        "landmarks",
        "face_box",
        "phone",
        "client_name",
    }
    models = (
        GalleryFacialPolicy,
        PhotoFaceEmbedding,
        FacialSearchRequest,
        FacialSearchSnapshotItem,
        FacialSearchCandidate,
        FacialJob,
        FacialSearchNotificationOutbox,
    )
    for model in models:
        assert forbidden.isdisjoint(model.__table__.columns.keys())


def test_facial_state_and_progress_checks_exist() -> None:
    assert "ck_facial_search_status" in _constraint_names(
        FacialSearchRequest, CheckConstraint
    )
    assert "ck_facial_search_snapshot_progress" in _constraint_names(
        FacialSearchRequest, CheckConstraint
    )
    assert "ck_facial_job_progress" in _constraint_names(FacialJob, CheckConstraint)
