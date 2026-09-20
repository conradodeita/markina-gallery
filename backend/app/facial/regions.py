"""Regiões acessíveis somente na galeria já autorizada; vetores nunca vão à API."""

import json

from sqlalchemy import select

from app.auth import GalleryFacialPolicy, MediaDerivative, PhotoAsset, PhotoFaceEmbedding
from app.facial.crypto import FacialEnvelope
from app.facial.engine import _embedding_scope
from app.facial.provider import normalize_embedding
from app.public_gallery_access import require_public_gallery_browsing


def region_query(gallery_id, settings):
    return (
        select(PhotoFaceEmbedding)
        .join(PhotoAsset, PhotoAsset.id == PhotoFaceEmbedding.photo_asset_id)
        .join(
            GalleryFacialPolicy,
            GalleryFacialPolicy.parent_gallery_id == PhotoAsset.parent_gallery_id,
        )
        .where(
            GalleryFacialPolicy.status == "active",
            GalleryFacialPolicy.model_version == settings.model_version,
            GalleryFacialPolicy.quality_version == settings.quality_version,
            PhotoFaceEmbedding.parent_gallery_id == gallery_id,
            PhotoAsset.parent_gallery_id == gallery_id,
            PhotoAsset.available.is_(True),
            PhotoAsset.derived_gallery_id.is_(None),
            PhotoFaceEmbedding.derived_gallery_id.is_(None),
            PhotoFaceEmbedding.bbox_x.is_not(None),
            PhotoFaceEmbedding.model_id == "opencv-yunet-sface",
            PhotoFaceEmbedding.embedding_dimension == 128,
            PhotoFaceEmbedding.model_version == settings.model_version,
            PhotoFaceEmbedding.quality_version == settings.quality_version,
            select(MediaDerivative.id)
            .where(
                MediaDerivative.photo_asset_id == PhotoAsset.id,
                MediaDerivative.variant == "client_preview",
                MediaDerivative.status == "ready",
            )
            .exists(),
        )
    )


def authorized_region(db, *, gallery_id, client_id, region_id, settings):
    require_public_gallery_browsing(db, parent_gallery_id=gallery_id, client_id=client_id)
    row = db.scalar(region_query(gallery_id, settings).where(PhotoFaceEmbedding.id == region_id))
    if not row:
        from app.facial.search import FacialSearchError

        raise FacialSearchError("Região facial indisponível.")
    return row


def region_embedding(row, cipher, settings):
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
    require_public_gallery_browsing(db, parent_gallery_id=gallery_id, client_id=client_id)
    from app.facial.rollout import rollout_is_active

    if not rollout_is_active(db, settings=settings, parent_gallery_id=gallery_id):
        return []
    rows = db.scalars(
        region_query(gallery_id, settings)
        .where(PhotoFaceEmbedding.photo_asset_id == photo_id)
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
