"""Indexação atômica e comparação vetorizada dentro de uma Galeria pública."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy import and_, bindparam, delete, or_, select
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFaceEmbedding,
    Tenant,
)
from app.facial.config import FacialSettings
from app.facial.crypto import FacialCipher, FacialEnvelope, FacialScope
from app.facial.indexing import (
    CLIENT_PRESENTATION_VARIANT,
    FACIAL_ANALYSIS_VARIANT,
    preview_fingerprint,
)
from app.facial.provider import (
    EXPECTED_EMBEDDING_DIMENSIONS,
    OpenCvSFaceProvider,
    normalize_embedding,
)
from app.facial.quality import FacialQualityError, assess_face_quality
from app.tenancy import bind_domain_owner


class FacialEngineError(RuntimeError):
    """Falha sanitizada de consistência do índice facial."""


@dataclass(frozen=True)
class SearchMatch:
    photo_id: UUID
    quality_band: str
    similarity: float = field(repr=False)
    match_class: str = "matched"


def replace_photo_index(
    db: Session,
    *,
    photo_id: UUID,
    tenant_id: UUID,
    derivatives_root: Path,
    provider: OpenCvSFaceProvider,
    cipher: FacialCipher,
    settings: FacialSettings,
    authorize: Callable[[], object] | None = None,
) -> int:
    """Substitui todas as faces da foto em uma única transação/savepoint."""

    photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
    from app.facial.detection import normalized_box
    from app.facial.lifecycle import analysis_for
    from app.media import safe_source_path

    analysis = analysis_for(db, photo_id, lock=True, tenant_id=tenant_id)
    if not photo or (not photo.available and not analysis):
        raise FacialEngineError("Foto não está elegível para indexação facial.")
    policy = db.scalar(
        select(GalleryFacialPolicy).where(
            GalleryFacialPolicy.tenant_id == tenant_id,
            GalleryFacialPolicy.parent_gallery_id == photo.parent_gallery_id,
            GalleryFacialPolicy.status == "active",
        )
    )
    if not policy or not _policy_matches(policy, settings):
        raise FacialEngineError("Política facial não está elegível para indexação.")
    derivative = db.scalar(
        select(MediaDerivative).where(
            MediaDerivative.tenant_id == tenant_id,
            MediaDerivative.photo_asset_id == photo.id,
            MediaDerivative.variant == FACIAL_ANALYSIS_VARIANT,
            MediaDerivative.status == "ready",
        )
    )
    if not analysis and (not derivative or not derivative.relative_path):
        raise FacialEngineError("Prévia facial não está pronta.")
    protected_preview_ready = db.scalar(
        select(MediaDerivative.id).where(
            MediaDerivative.tenant_id == tenant_id,
            MediaDerivative.photo_asset_id == photo.id,
            MediaDerivative.variant == CLIENT_PRESENTATION_VARIANT,
            MediaDerivative.status == "ready",
        )
    )
    if not analysis and protected_preview_ready is None:
        raise FacialEngineError("Prévia protegida não está pronta.")
    if analysis:
        if analysis.deleted_at:
            raise FacialEngineError("Reenvie o JPEG original para reindexar esta foto.")
        path = safe_source_path(photo)
    else:
        from app.media import media_namespace
        root = derivatives_root.resolve()
        media_namespace(derivative.relative_path, tenant_id)
        path = (root / derivative.relative_path).resolve()
        media_namespace(path.relative_to(root).as_posix(), tenant_id)
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise FacialEngineError("Caminho de prévia facial inválido.") from exc
    def revalidate():
        if authorize:
            authorize()
        current = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
        parent = owned_record(db, ParentGallery, photo.parent_gallery_id, tenant_id=tenant_id)
        current_policy = db.scalar(select(GalleryFacialPolicy).where(
            GalleryFacialPolicy.tenant_id == tenant_id,
            GalleryFacialPolicy.parent_gallery_id == photo.parent_gallery_id,
        ).execution_options(populate_existing=True))
        if not current or not parent or not parent.active or parent.lifecycle_status != "active" or not current_policy or current_policy.status != "active" or not _policy_matches(current_policy, settings):
            raise FacialEngineError("Origem facial indisponível.")
    revalidate()
    fingerprint = preview_fingerprint(path)
    if analysis and fingerprint != analysis.source_fingerprint:
        raise FacialEngineError("A fonte facial foi alterada.")
    observations = provider.observe_highres_path(path) if analysis else provider.observe_path(path)
    revalidate()
    largest_face_area = max(
        (face.box[2] * face.box[3] for face in observations), default=0
    )
    records: list[PhotoFaceEmbedding] = []
    engine_model_id = getattr(provider, "model_id", "opencv-yunet-sface")
    engine_model_version = getattr(provider, "model_version", policy.model_version)
    for ordinal, face in enumerate(observations):
        try:
            assessment = assess_face_quality(
                face,
                image_width=face.image_width or (analysis.width if analysis else derivative.width) or 1,
                image_height=face.image_height or (analysis.height if analysis else derivative.height) or 1,
                largest_face_area=largest_face_area,
            )
        except FacialQualityError:
            # Uma detecção sem geometria utilizável equivale a ausência daquela face;
            # ela não torna indisponíveis a foto nem as outras observações válidas.
            continue
        payload = json.dumps(
            {
                "embedding": face.embedding,
                "quality": assessment.encrypted_indicators(),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        envelope = cipher.encrypt(
            payload,
            scope=_embedding_scope(
                settings=settings,
                gallery_id=photo.parent_gallery_id,
                photo_id=photo.id,
                model_version=engine_model_version,
                quality_version=policy.quality_version,
            ),
        )
        geometry = {}
        if analysis:
            try:
                box = normalized_box(face.box, analysis.width, analysis.height)
            except ValueError:
                continue
            geometry = dict(zip(("bbox_x", "bbox_y", "bbox_width", "bbox_height"), box, strict=True))
        records.append(
            PhotoFaceEmbedding(
                tenant_id=tenant_id,
                parent_gallery_id=photo.parent_gallery_id,
                derived_gallery_id=photo.derived_gallery_id,
                photo_asset_id=photo.id,
                face_ordinal=ordinal,
                model_version=engine_model_version,
                quality_version=policy.quality_version,
                preview_fingerprint=fingerprint,
                quality_band=assessment.band,
                payload_ciphertext=envelope.ciphertext,
                payload_nonce=envelope.nonce,
                key_id=envelope.key_id,
                model_id=engine_model_id,
                embedding_dimension=getattr(provider, "embedding_dimension", 128),
                pipeline_version=analysis.pipeline_version if analysis else "legacy-preview-v1",
                detection_pass=face.detection_pass,
                detection_confidence=face.detection_confidence,
                **geometry,
            )
        )
    revalidate()
    with db.begin_nested():
        db.execute(
            delete(PhotoFaceEmbedding).where(
                PhotoFaceEmbedding.tenant_id == tenant_id,
                PhotoFaceEmbedding.photo_asset_id == photo.id,
                PhotoFaceEmbedding.parent_gallery_id == photo.parent_gallery_id,
                PhotoFaceEmbedding.model_id == engine_model_id,
            )
        )
        db.add_all(records)
        if analysis and engine_model_id == "opencv-yunet-sface":
            analysis.state = "ready"
            analysis.metrics = {**getattr(provider, "last_metrics", {}),
                                "faces_accepted": len(records), "faces_rejected": len(observations)-len(records),
                                "quality_version": policy.quality_version,
                                "rejection_reason": "invalid_geometry" if len(records)<len(observations) else None}
        db.flush()
    return len(records)


def search_gallery_index(
    db: Session,
    *,
    gallery_id: UUID,
    tenant_id: UUID,
    query_embedding: tuple[float, ...],
    cipher: FacialCipher,
    settings: FacialSettings,
    threshold_milli: int,
    allowed_fingerprints: dict[UUID, str] | None = None,
    ambiguous_threshold_milli: int | None = None,
    authorize: Callable[[UUID], bool] | None = None,
    on_progress: Callable[[int], None] | None = None,
    model_id: str = "opencv-yunet-sface",
    model_version: str | None = None,
    embedding_dimension: int = EXPECTED_EMBEDDING_DIMENSIONS,
) -> list[SearchMatch]:
    """Compara em memória somente embeddings autorizados da mesma galeria."""

    try:
        import numpy as np
    except ImportError as exc:
        raise FacialEngineError("Runtime vetorial facial indisponível.") from exc
    if not owned_record(db, ParentGallery, gallery_id, tenant_id=tenant_id):
        raise FacialEngineError("Origem facial indisponível.")
    normalized_query = normalize_embedding(query_embedding, embedding_dimension)
    selected_version = model_version or settings.model_version
    if allowed_fingerprints is not None and not allowed_fingerprints:
        return []
    query = (
        select(
            PhotoFaceEmbedding.photo_asset_id,
            PhotoFaceEmbedding.face_ordinal,
            PhotoFaceEmbedding.preview_fingerprint,
            PhotoFaceEmbedding.quality_band,
            PhotoFaceEmbedding.payload_ciphertext,
            PhotoFaceEmbedding.payload_nonce,
            PhotoFaceEmbedding.key_id,
            PhotoFaceEmbedding.model_version,
            PhotoFaceEmbedding.quality_version,
            PhotoFaceEmbedding.embedding_dimension,
        )
        .join(PhotoAsset, PhotoAsset.id == PhotoFaceEmbedding.photo_asset_id)
        .where(
            PhotoFaceEmbedding.tenant_id == tenant_id,
            PhotoAsset.tenant_id == tenant_id,
            PhotoFaceEmbedding.parent_gallery_id == gallery_id,
            PhotoFaceEmbedding.model_version == selected_version,
            PhotoFaceEmbedding.model_id == model_id,
            PhotoFaceEmbedding.embedding_dimension == embedding_dimension,
            PhotoFaceEmbedding.quality_version == settings.quality_version,
            PhotoAsset.parent_gallery_id == gallery_id,
            PhotoAsset.derived_gallery_id.is_(None),
            PhotoFaceEmbedding.derived_gallery_id.is_(None),
            PhotoAsset.available.is_(True),
            *(
                (PhotoFaceEmbedding.photo_asset_id.in_(allowed_fingerprints),)
                if allowed_fingerprints is not None
                else ()
            ),
        )
        .order_by(PhotoFaceEmbedding.photo_asset_id, PhotoFaceEmbedding.face_ordinal)
    )
    threshold = threshold_milli / 1000
    ambiguous = threshold if ambiguous_threshold_milli is None else ambiguous_threshold_milli / 1000
    if not 0 <= ambiguous <= threshold <= 1:
        raise FacialEngineError("Faixas de similaridade inválidas.")
    normalized_query_array = np.asarray(normalized_query, dtype=np.float32)
    current_scope = (
        select(PhotoAsset.id)
        .select_from(ParentGallery)
        .join(Tenant, Tenant.id == ParentGallery.tenant_id)
        .join(GalleryFacialPolicy, and_(
            GalleryFacialPolicy.parent_gallery_id == ParentGallery.id,
            GalleryFacialPolicy.tenant_id == tenant_id,
        ))
        .outerjoin(PhotoAsset, and_(
            PhotoAsset.id == bindparam("comparison_photo_id"),
            PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.parent_gallery_id == gallery_id,
            PhotoAsset.derived_gallery_id.is_(None),
            PhotoAsset.available.is_(True),
        ))
        .where(
            settings.enabled,
            Tenant.id == tenant_id, Tenant.status == "active",
            ParentGallery.id == gallery_id, ParentGallery.tenant_id == tenant_id,
            ParentGallery.active.is_(True), ParentGallery.lifecycle_status == "active",
            GalleryFacialPolicy.status == "active",
            *(getattr(GalleryFacialPolicy, field) == getattr(settings, field) for field in (
                "model_version", "quality_version", "calibration_version", "legal_notice_version",
                "legal_basis_reference", "retention_policy_version", "minor_policy_version",
            )),
        )
    )
    best_by_photo: dict[UUID, SearchMatch] = {}
    compared_photos = 0
    previous_photo_id = None
    cursor = None
    while True:
        page_query = query
        if cursor is not None:
            photo_id, ordinal = cursor
            page_query = page_query.where(or_(
                PhotoFaceEmbedding.photo_asset_id > photo_id,
                and_(
                    PhotoFaceEmbedding.photo_asset_id == photo_id,
                    PhotoFaceEmbedding.face_ordinal > ordinal,
                ),
            ))
        # Projeção imutável e paginação por chave: callbacks podem fazer commit
        # sem expirar milhares de entidades ORM nem fechar um cursor de servidor.
        rows = list(db.execute(page_query.limit(128)))
        if not rows:
            break
        cursor = (rows[-1].photo_asset_id, rows[-1].face_ordinal)
        for row in rows:
            if row.photo_asset_id != previous_photo_id:
                if previous_photo_id is not None:
                    compared_photos += 1
                    if on_progress is not None:
                        on_progress(compared_photos)
                previous_photo_id = row.photo_asset_id
            if authorize is not None and not authorize(row.photo_asset_id):
                continue
            current = db.execute(current_scope, {
                "comparison_photo_id": row.photo_asset_id,
            }).first()
            if current is None:
                require_active_owner(db, tenant_id)
                raise FacialEngineError("Origem facial indisponível.")
            bind_domain_owner(db, tenant_id)
            if current[0] is None:
                continue
            if (
                allowed_fingerprints is not None
                and allowed_fingerprints.get(row.photo_asset_id)
                != row.preview_fingerprint
            ):
                continue
            envelope = FacialEnvelope(
                ciphertext=row.payload_ciphertext,
                nonce=row.payload_nonce,
                key_id=row.key_id,
            )
            payload = cipher.decrypt(
                envelope,
                scope=_embedding_scope(
                    settings=settings,
                    gallery_id=gallery_id,
                    photo_id=row.photo_asset_id,
                    model_version=row.model_version,
                    quality_version=row.quality_version,
                ),
            )
            try:
                decoded = json.loads(payload)
                embedding = normalize_embedding(decoded["embedding"], row.embedding_dimension)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                raise FacialEngineError("Índice facial inválido.") from exc
            vector = np.asarray(embedding, dtype=np.float32)
            if vector.shape != (embedding_dimension,):
                raise FacialEngineError("Dimensão do índice facial inválida.")
            similarity = float(vector @ normalized_query_array)
            if similarity < ambiguous:
                continue
            current = best_by_photo.get(row.photo_asset_id)
            if current is None or similarity > current.similarity:
                best_by_photo[row.photo_asset_id] = SearchMatch(
                    photo_id=row.photo_asset_id,
                    quality_band=row.quality_band,
                    similarity=similarity,
                    match_class="matched" if similarity >= threshold else "ambiguous",
                )
    if previous_photo_id is not None and on_progress is not None:
        on_progress(compared_photos + 1)
    return sorted(
        best_by_photo.values(),
        key=lambda match: (
            0 if match.match_class == "matched" else 1,
            0 if match.quality_band == "best" else 1,
            -match.similarity,
            str(match.photo_id),
        ),
    )


def _embedding_scope(
    *,
    settings: FacialSettings,
    gallery_id: UUID,
    photo_id: UUID,
    model_version: str,
    quality_version: str,
) -> FacialScope:
    return FacialScope(
        environment=settings.environment,
        gallery_id=gallery_id,
        object_kind="photo",
        object_id=photo_id,
        purpose="embedding",
        model_version=model_version,
        data_version=quality_version,
    )


def _policy_matches(
    policy: GalleryFacialPolicy, settings: FacialSettings
) -> bool:
    return all(
        (
            settings.enabled,
            policy.model_version == settings.model_version,
            policy.quality_version == settings.quality_version,
            policy.calibration_version == settings.calibration_version,
            policy.legal_notice_version == settings.legal_notice_version,
            policy.legal_basis_reference == settings.legal_basis_reference,
            policy.retention_policy_version == settings.retention_policy_version,
            policy.minor_policy_version == settings.minor_policy_version,
        )
    )
