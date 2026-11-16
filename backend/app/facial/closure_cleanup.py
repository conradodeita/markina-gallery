"""Limpeza verificável e repetível da biometria no encerramento do tenant."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import (
    AuditEvent,
    FacialJob,
    FacialSearchCandidate,
    FacialSearchConsentProof,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    FacialSearchSnapshotItem,
    GalleryFacialPolicy,
    PhotoFaceEmbedding,
    TenantClosureRequest,
    now,
)
from app.facial.reference_store import FacialReferenceError, delete_reference_file

_CLEANUP_BATCH_SIZE = 200


class _CleanupVerificationError(RuntimeError):
    """O estado facial ainda contém uma linha operacional após a remoção."""


def cleanup_tenant_biometrics(
    db: Session,
    *,
    tenant_id: UUID,
    closure: TenantClosureRequest,
    instant=None,
    reference_root: Path | None = None,
) -> bool:
    """Retorna False enquanto um lease válido ou uma remoção não verificada existir.

    O chamador mantém locks de tenant e de solicitação de encerramento até o commit.
    Os arquivos são removidos antes das linhas que os identificam; uma falha em
    qualquer página deixa o tenant em `closing`, e a repetição é segura.
    """

    current = instant or now()
    if closure.tenant_id != tenant_id or closure.state != "closing":
        raise ValueError("Solicitação de encerramento fora do escopo.")

    if closure.biometric_cleanup_completed_at is not None:
        return _operational_rows_remaining(db, tenant_id) == 0

    if closure.biometric_cleanup_started_at is None:
        closure.biometric_cleanup_started_at = current
        policies = db.scalars(
            select(GalleryFacialPolicy)
            .where(GalleryFacialPolicy.tenant_id == tenant_id)
            .with_for_update()
        )
        for policy in policies:
            policy.status = "disabled"
            policy.index_generation += 1
            policy.updated_at = current
        db.add(
            AuditEvent(
                tenant_id=tenant_id,
                event="tenant.biometric_cleanup_started",
                subject=f"closure_request_id:{closure.request_id}",
            )
        )
        db.flush()
        # O marcador precisa estar commitado antes de qualquer remoção física.
        # O worker de encerramento confirma este estado e tenta a limpeza no
        # próximo ciclo; assim, um rollback de limpeza não libera novas buscas.
        return False

    _cancel_unclaimed_and_expired_work(db, tenant_id=tenant_id, instant=current)
    active_jobs = db.scalar(
        select(func.count()).select_from(FacialJob).where(
            FacialJob.tenant_id == tenant_id,
            FacialJob.status == "processing",
            FacialJob.lease_token.is_not(None),
            FacialJob.lease_expires_at > current,
        )
    ) or 0
    active_notifications = db.scalar(
        select(func.count()).select_from(FacialSearchNotificationOutbox).where(
            FacialSearchNotificationOutbox.tenant_id == tenant_id,
            FacialSearchNotificationOutbox.status == "processing",
            FacialSearchNotificationOutbox.lease_expires_at > current,
        )
    ) or 0
    if active_jobs or active_notifications:
        return False

    root = reference_root or Path(
        os.getenv("FACIAL_REFERENCE_ROOT", "./media/facial-references")
    )
    try:
        with db.begin_nested():
            while True:
                requests = list(
                    db.scalars(
                        select(FacialSearchRequest)
                        .where(FacialSearchRequest.tenant_id == tenant_id)
                        .order_by(FacialSearchRequest.id)
                        .limit(_CLEANUP_BATCH_SIZE)
                        .with_for_update()
                    )
                )
                if not requests:
                    break

                request_ids = [request.id for request in requests]
                existing_proofs = set(
                    db.scalars(
                        select(FacialSearchConsentProof.source_search_request_id).where(
                            FacialSearchConsentProof.tenant_id == tenant_id,
                            FacialSearchConsentProof.source_search_request_id.in_(request_ids),
                        )
                    )
                )
                db.add_all(
                    FacialSearchConsentProof(
                        tenant_id=request.tenant_id,
                        source_search_request_id=request.id,
                        parent_gallery_id=request.parent_gallery_id,
                        client_id=request.client_id,
                        authorization_method=request.authorization_method,
                        consent_version=request.consent_version,
                        legal_notice_version=request.legal_notice_version,
                        subject_declaration=request.subject_declaration,
                        recorded_at=request.created_at,
                    )
                    for request in requests
                    if request.id not in existing_proofs
                )
                db.flush()

                for request in requests:
                    delete_reference_file(root, request.id)

                for model in (
                    FacialSearchNotificationOutbox,
                    FacialSearchCandidate,
                    FacialSearchSnapshotItem,
                    FacialJob,
                ):
                    db.execute(
                        delete(model).where(
                            model.tenant_id == tenant_id,
                            model.search_request_id.in_(request_ids),
                        )
                    )
                db.execute(
                    delete(FacialSearchRequest).where(
                        FacialSearchRequest.tenant_id == tenant_id,
                        FacialSearchRequest.id.in_(request_ids),
                    )
                )
                db.flush()

            # Jobs de indexação não apontam a uma busca, mas também são dados
            # operacionais da política facial deste tenant.
            for model in (
                FacialSearchNotificationOutbox,
                FacialSearchCandidate,
                FacialSearchSnapshotItem,
                FacialJob,
                PhotoFaceEmbedding,
            ):
                db.execute(delete(model).where(model.tenant_id == tenant_id))
            db.flush()
            if _operational_rows_remaining(db, tenant_id):
                raise _CleanupVerificationError("A limpeza biométrica não foi confirmada.")
            closure.biometric_cleanup_completed_at = current
            db.add(
                AuditEvent(
                    tenant_id=tenant_id,
                    event="tenant.biometric_cleanup_completed",
                    subject=f"closure_request_id:{closure.request_id}",
                )
            )
            db.flush()
    except (FacialReferenceError, _CleanupVerificationError, SQLAlchemyError):
        return False
    return True


def _cancel_unclaimed_and_expired_work(
    db: Session, *, tenant_id: UUID, instant
) -> None:
    expired_or_unleased = or_(
        FacialJob.lease_expires_at.is_(None),
        FacialJob.lease_expires_at <= instant,
        FacialJob.lease_token.is_(None),
    )
    db.execute(
        update(FacialJob)
        .where(
            FacialJob.tenant_id == tenant_id,
            or_(
                FacialJob.status == "queued",
                (FacialJob.status == "processing") & expired_or_unleased,
            ),
        )
        .values(
            status="cancelled",
            lease_token=None,
            lease_expires_at=None,
            last_error_category="tenant_closure",
            updated_at=instant,
        )
        .execution_options(synchronize_session=False)
    )
    db.execute(
        update(FacialSearchNotificationOutbox)
        .where(
            FacialSearchNotificationOutbox.tenant_id == tenant_id,
            FacialSearchNotificationOutbox.status == "queued",
        )
        .values(
            status="cancelled",
            payload_ciphertext=b"",
            payload_nonce=b"",
            lease_expires_at=None,
            last_error_category="tenant_closure",
            updated_at=instant,
        )
        .execution_options(synchronize_session=False)
    )
    db.execute(
        update(FacialSearchNotificationOutbox)
        .where(
            FacialSearchNotificationOutbox.tenant_id == tenant_id,
            FacialSearchNotificationOutbox.status == "processing",
            or_(
                FacialSearchNotificationOutbox.lease_expires_at.is_(None),
                FacialSearchNotificationOutbox.lease_expires_at <= instant,
            ),
        )
        .values(
            status="failed",
            payload_ciphertext=b"",
            payload_nonce=b"",
            lease_expires_at=None,
            last_error_category="ambiguous_delivery",
            updated_at=instant,
        )
        .execution_options(synchronize_session=False)
    )


def _operational_rows_remaining(db: Session, tenant_id: UUID) -> int:
    return sum(
        db.scalar(
            select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
        )
        or 0
        for model in (
            FacialSearchNotificationOutbox,
            FacialSearchCandidate,
            FacialSearchSnapshotItem,
            FacialJob,
            PhotoFaceEmbedding,
            FacialSearchRequest,
        )
    )
