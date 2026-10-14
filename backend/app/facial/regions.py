"""Regiões acessíveis somente na galeria já autorizada; vetores nunca vão à API."""

import json

from sqlalchemy import select

from app.acervo_context import client_tenant_id, owned_record
from app.auth import (
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFaceEmbedding,
)
from app.facial.crypto import FacialEnvelope
from app.facial.engine import _embedding_scope
from app.facial.gemma_provider import GEMMA_EMBEDDING_DIMENSION, GEMMA_MODEL_ID, GEMMA_MODEL_VERSION
from app.facial.provider import normalize_embedding
from app.public_gallery_access import authorized_canonical_photos, require_public_gallery_browsing


def region_query(gallery_id, settings, *, tenant_id, model_id="opencv-yunet-sface"):
    is_gemma = model_id == GEMMA_MODEL_ID
    return (
        select(PhotoFaceEmbedding)
        .join(PhotoAsset, PhotoAsset.id == PhotoFaceEmbedding.photo_asset_id)
        .join(
            GalleryFacialPolicy,
            GalleryFacialPolicy.parent_gallery_id == PhotoAsset.parent_gallery_id,
        )
        .where(
            GalleryFacialPolicy.tenant_id == tenant_id,
            PhotoAsset.tenant_id == tenant_id,
            PhotoFaceEmbedding.tenant_id == tenant_id,
            GalleryFacialPolicy.status == "active",
            GalleryFacialPolicy.model_version == settings.model_version,
            GalleryFacialPolicy.quality_version == settings.quality_version,
            PhotoFaceEmbedding.parent_gallery_id == gallery_id,
            PhotoAsset.parent_gallery_id == gallery_id,
            PhotoAsset.available.is_(True),
            PhotoAsset.derived_gallery_id.is_(None),
            PhotoFaceEmbedding.derived_gallery_id.is_(None),
            PhotoFaceEmbedding.bbox_x.is_not(None),
            PhotoFaceEmbedding.model_id == model_id,
            PhotoFaceEmbedding.embedding_dimension == (
                GEMMA_EMBEDDING_DIMENSION if is_gemma else 128
            ),
            PhotoFaceEmbedding.model_version == (
                GEMMA_MODEL_VERSION if is_gemma else settings.model_version
            ),
            PhotoFaceEmbedding.quality_version == settings.quality_version,
            select(MediaDerivative.id)
            .where(
                MediaDerivative.tenant_id == tenant_id,
                MediaDerivative.photo_asset_id == PhotoAsset.id,
                MediaDerivative.variant == "client_preview",
                MediaDerivative.status == "ready",
            )
            .exists(),
        )
    )


def authorized_region(
    db, *, gallery_id, client_id, region_id, settings,
    model_id="opencv-yunet-sface",
):
    tenant_id = client_tenant_id(db, client_id)
    require_public_gallery_browsing(db, parent_gallery_id=gallery_id, client_id=client_id)
    row = db.scalar(region_query(
        gallery_id, settings, tenant_id=tenant_id, model_id=model_id
    ).where(
        PhotoFaceEmbedding.id == region_id,
        PhotoAsset.id.in_(authorized_canonical_photos(gallery_id, client_id).with_only_columns(PhotoAsset.id)),
    ))
    if not row:
        from app.facial.search import FacialSearchError

        raise FacialSearchError("Região facial indisponível.")
    return row


def region_embedding(db, row, cipher, settings, *, tenant_id):
    from app.facial.policy import read_policy
    from app.facial.rollout import rollout_is_active

    row = owned_record(db, PhotoFaceEmbedding, row.id, tenant_id=tenant_id)
    if row is None:
        raise ValueError("Região facial indisponível.")
    parent = owned_record(db, ParentGallery, row.parent_gallery_id, tenant_id=tenant_id)
    photo = owned_record(db, PhotoAsset, row.photo_asset_id, tenant_id=tenant_id)
    if not parent or not parent.active or parent.lifecycle_status != "active" or not photo or not photo.available or photo.derived_gallery_id is not None:
        raise ValueError("Região facial indisponível.")
    policy = read_policy(db, row.parent_gallery_id, tenant_id=tenant_id)
    expected_version = (
        GEMMA_MODEL_VERSION
        if row.model_id == GEMMA_MODEL_ID
        else settings.model_version
    )
    if not policy or policy.status != "active" or row.model_version != expected_version or policy.model_version != settings.model_version or policy.quality_version != row.quality_version or not rollout_is_active(db, settings=settings, parent_gallery_id=row.parent_gallery_id, tenant_id=tenant_id):
        raise ValueError("Região facial indisponível.")
    payload = cipher.decrypt(
        FacialEnvelope(
            ciphertext=row.payload_ciphertext, nonce=row.payload_nonce, key_id=row.key_id
        ),
        scope=_embedding_scope(
            settings=settings,
            gallery_id=row.parent_gallery_id,
            photo_id=row.photo_asset_id,
            model_version=row.model_version,
            quality_version=row.quality_version,
        ),
    )
    return normalize_embedding(json.loads(payload)["embedding"], row.embedding_dimension)


def photo_regions(db, *, gallery_id, client_id, photo_id, settings):
    tenant_id = client_tenant_id(db, client_id)
    require_public_gallery_browsing(db, parent_gallery_id=gallery_id, client_id=client_id)
    from app.facial.rollout import rollout_is_active

    if not rollout_is_active(db, settings=settings, parent_gallery_id=gallery_id, tenant_id=client_tenant_id(db, client_id)):
        return []
    from app.facial.serving import gallery_search_engine
    model_id = gallery_search_engine(
        db, parent_gallery_id=gallery_id, client_id=client_id, settings=settings
    )
    rows = db.scalars(
        region_query(gallery_id, settings, tenant_id=tenant_id, model_id=model_id)
        .where(PhotoFaceEmbedding.photo_asset_id == photo_id)
        .where(PhotoAsset.id.in_(authorized_canonical_photos(gallery_id, client_id).with_only_columns(PhotoAsset.id)))
        .order_by(PhotoFaceEmbedding.face_ordinal)
    )
    return [
        {
            "id": str(row.id),
            "x": row.bbox_x,
            "y": row.bbox_y,
            "width": row.bbox_width,
            "height": row.bbox_height,
        }
        for row in rows
    ]
