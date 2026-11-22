"""Diagnóstico agregado da procedência de índices, sem ler envelopes ou payloads."""

from sqlalchemy import and_, exists, func, select
from sqlalchemy.engine import Connection

from app.auth import (
    FacialRollout,
    GalleryFacialPolicy,
    ParentGallery,
    PhotoAsset,
    PhotoFaceEmbedding,
)


def inspect_embedding_origins(connection: Connection, *, source_environment: str) -> dict[str, int]:
    """Lê apenas vínculos/metadados; resultado não é autorização para migrar."""
    if source_environment not in {"development", "homolog", "homologation", "staging", "test"}:
        raise ValueError("Contexto de origem inválido.")
    embedding = PhotoFaceEmbedding.__table__
    photo = PhotoAsset.__table__
    gallery = ParentGallery.__table__
    policy = GalleryFacialPolicy.__table__
    rollout = FacialRollout.__table__
    valid_binding = exists(select(1).select_from(photo.join(
        gallery, gallery.c.id == photo.c.parent_gallery_id,
    )).where(
        photo.c.id == embedding.c.photo_asset_id,
        photo.c.parent_gallery_id == embedding.c.parent_gallery_id,
        photo.c.tenant_id == embedding.c.tenant_id,
        gallery.c.tenant_id == embedding.c.tenant_id,
    ))
    valid_policy = exists(select(1).select_from(policy).where(
        policy.c.parent_gallery_id == embedding.c.parent_gallery_id,
        policy.c.tenant_id == embedding.c.tenant_id,
        policy.c.status == "active",
        policy.c.suspended_at.is_(None),
        policy.c.model_version == embedding.c.model_version,
        policy.c.quality_version == embedding.c.quality_version,
        func.length(func.trim(policy.c.legal_notice_version)) > 0,
        func.length(func.trim(policy.c.legal_basis_reference)) > 0,
        func.length(func.trim(policy.c.retention_policy_version)) > 0,
    ))
    valid_rollout = exists(select(1).select_from(rollout.join(
        policy, and_(
            rollout.c.parent_gallery_id == policy.c.parent_gallery_id,
            rollout.c.tenant_id == policy.c.tenant_id,
        ),
    )).where(
        rollout.c.parent_gallery_id == embedding.c.parent_gallery_id,
        rollout.c.tenant_id == embedding.c.tenant_id,
        rollout.c.environment == source_environment,
        rollout.c.status == "active",
        rollout.c.revoked_at.is_(None),
        rollout.c.suspended_at.is_(None),
        rollout.c.approved_at.is_not(None),
        rollout.c.approved_by_admin_id.is_not(None),
        func.length(func.trim(rollout.c.approval_reference)) > 0,
        rollout.c.model_version == embedding.c.model_version,
        rollout.c.quality_version == embedding.c.quality_version,
        rollout.c.legal_notice_version == policy.c.legal_notice_version,
        rollout.c.legal_basis_reference == policy.c.legal_basis_reference,
        rollout.c.retention_policy_version == policy.c.retention_policy_version,
    ))
    row = connection.execute(select(
        func.count().label("total"),
        func.count().filter(valid_binding).label("binding_verified"),
        func.count().filter(valid_policy).label("policy_verified"),
        func.count().filter(valid_rollout).label("source_rollout_verified"),
        func.count().filter(and_(valid_binding, valid_policy, valid_rollout)).label(
            "all_metadata_verified"
        ),
    ).select_from(embedding)).mappings().one()
    return {key: int(value) for key, value in row.items()}
