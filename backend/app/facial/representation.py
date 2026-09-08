"""Representação legal não biométrica para a fronteira infantil da cliente."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    AuditEvent,
    FacialJob,
    FacialLegalRepresentation,
    FacialSearchCandidate,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    ParentGallery,
    ParentGalleryRegistration,
    now,
)
from app.facial.reference_store import delete_reference_file

AUTHORITY_KINDS = {"parent", "legal_guardian", "court_order"}
VERIFICATION_METHODS = {"admin_attestation", "trusted_provider"}


class FacialLegalRepresentationError(ValueError):
    """Falha genérica sem revelar a existência ou o escopo da prova."""


@dataclass(frozen=True)
class FacialRepresentationRightsReport:
    representations_revoked: int
    requests_cancelled: int
    references_deleted: int
    candidates_deleted: int
    notifications_cancelled: int
    jobs_cancelled: int


def _required_opaque(value: str, *, field: str, max_length: int = 200) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        raise FacialLegalRepresentationError(f"{field} inválido.")
    return normalized


def create_legal_representation(
    db: Session,
    *,
    client_id: UUID,
    parent_gallery_id: UUID,
    subject_scope_reference: str,
    authority_kind: str,
    verification_method: str,
    terms_version: str,
    evidence_reference: str,
    verified_by_admin_id: UUID,
    expires_at: datetime,
    valid_from: datetime | None = None,
) -> FacialLegalRepresentation:
    issued_at = valid_from or now()
    if authority_kind not in AUTHORITY_KINDS:
        raise FacialLegalRepresentationError("Autoridade de representação inválida.")
    if verification_method not in VERIFICATION_METHODS:
        raise FacialLegalRepresentationError("Método de verificação inválido.")
    if expires_at <= issued_at:
        raise FacialLegalRepresentationError("Validade da representação inválida.")
    if db.get(AdminUser, verified_by_admin_id) is None:
        raise FacialLegalRepresentationError("Representação legal indisponível.")
    registration = db.scalar(
        select(ParentGalleryRegistration).where(
            ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
            ParentGalleryRegistration.client_id == client_id,
            ParentGalleryRegistration.status == "active",
        )
    )
    gallery = db.get(ParentGallery, parent_gallery_id)
    if registration is None or gallery is None or not gallery.active:
        raise FacialLegalRepresentationError("Representação legal indisponível.")
    item = FacialLegalRepresentation(
        client_id=client_id,
        parent_gallery_id=parent_gallery_id,
        subject_scope_reference=_required_opaque(
            subject_scope_reference, field="Escopo da representação"
        ),
        authority_kind=authority_kind,
        verification_method=verification_method,
        terms_version=_required_opaque(
            terms_version, field="Versão dos termos", max_length=80
        ),
        evidence_reference=_required_opaque(
            evidence_reference, field="Referência da prova"
        ),
        verified_by_admin_id=verified_by_admin_id,
        valid_from=issued_at,
        expires_at=expires_at,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditEvent(
            event="facial.legal_representation_created",
            subject=(
                f"representation_id:{item.id};gallery_id:{parent_gallery_id};"
                f"client_id:{client_id}"
            ),
        )
    )
    return item


def require_valid_legal_representation(
    db: Session,
    *,
    representation_reference: str | None,
    client_id: UUID,
    parent_gallery_id: UUID,
    terms_version: str,
    at: datetime | None = None,
) -> FacialLegalRepresentation:
    try:
        representation_id = UUID((representation_reference or "").strip())
    except (ValueError, AttributeError) as exc:
        raise FacialLegalRepresentationError("Representação legal indisponível.") from exc
    instant = at or now()
    item = db.scalar(
        select(FacialLegalRepresentation)
        .join(
            ParentGalleryRegistration,
            (ParentGalleryRegistration.parent_gallery_id == parent_gallery_id)
            & (ParentGalleryRegistration.client_id == client_id),
        )
        .join(ParentGallery, ParentGallery.id == parent_gallery_id)
        .where(
            FacialLegalRepresentation.id == representation_id,
            FacialLegalRepresentation.client_id == client_id,
            FacialLegalRepresentation.parent_gallery_id == parent_gallery_id,
            FacialLegalRepresentation.terms_version == terms_version,
            FacialLegalRepresentation.status == "active",
            FacialLegalRepresentation.revoked_at.is_(None),
            FacialLegalRepresentation.valid_from <= instant,
            FacialLegalRepresentation.expires_at > instant,
            ParentGalleryRegistration.status == "active",
            ParentGallery.active.is_(True),
            ParentGallery.lifecycle_status == "active",
        )
    )
    if item is None:
        raise FacialLegalRepresentationError("Representação legal indisponível.")
    return item


def find_valid_legal_representation(
    db: Session,
    *,
    client_id: UUID,
    parent_gallery_id: UUID,
    terms_version: str,
    at: datetime | None = None,
) -> FacialLegalRepresentation | None:
    instant = at or now()
    return db.scalar(
        select(FacialLegalRepresentation)
        .join(
            ParentGalleryRegistration,
            (ParentGalleryRegistration.parent_gallery_id == parent_gallery_id)
            & (ParentGalleryRegistration.client_id == client_id),
        )
        .join(ParentGallery, ParentGallery.id == parent_gallery_id)
        .where(
            FacialLegalRepresentation.client_id == client_id,
            FacialLegalRepresentation.parent_gallery_id == parent_gallery_id,
            FacialLegalRepresentation.terms_version == terms_version,
            FacialLegalRepresentation.status == "active",
            FacialLegalRepresentation.revoked_at.is_(None),
            FacialLegalRepresentation.valid_from <= instant,
            FacialLegalRepresentation.expires_at > instant,
            ParentGalleryRegistration.status == "active",
            ParentGallery.active.is_(True),
            ParentGallery.lifecycle_status == "active",
        )
        .order_by(
            FacialLegalRepresentation.expires_at.desc(),
            FacialLegalRepresentation.created_at.desc(),
        )
        .limit(1)
    )


def revoke_legal_representation(
    db: Session,
    *,
    representation_id: UUID,
    actor_admin_id: UUID,
) -> FacialLegalRepresentation:
    item = db.get(FacialLegalRepresentation, representation_id)
    if item is None or db.get(AdminUser, actor_admin_id) is None:
        raise FacialLegalRepresentationError("Representação legal indisponível.")
    if item.status != "revoked":
        item.status = "revoked"
        item.revoked_at = now()
        item.updated_at = now()
        db.add(
            AuditEvent(
                event="facial.legal_representation_revoked",
                subject=(
                    f"representation_id:{item.id};gallery_id:{item.parent_gallery_id};"
                    f"client_id:{item.client_id}"
                ),
            )
        )
    db.flush()
    return item


def legal_representation_rights_inventory(
    db: Session, *, representation_id: UUID
) -> dict[str, int | bool]:
    item = db.get(FacialLegalRepresentation, representation_id)
    if item is None:
        raise FacialLegalRepresentationError("Representação legal indisponível.")
    reference = str(item.id)
    requests = select(FacialSearchRequest.id).where(
        FacialSearchRequest.representation_reference == reference,
        FacialSearchRequest.subject_declaration == "minor",
    )

    def count(model, *criteria) -> int:
        return int(db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)

    references = count(
        FacialSearchRequest,
        FacialSearchRequest.representation_reference == reference,
        FacialSearchRequest.reference_locator_ciphertext.is_not(None),
    )
    candidates = count(
        FacialSearchCandidate,
        FacialSearchCandidate.search_request_id.in_(requests),
    )
    pending_notifications = count(
        FacialSearchNotificationOutbox,
        FacialSearchNotificationOutbox.search_request_id.in_(requests),
        FacialSearchNotificationOutbox.status.in_(("queued", "processing")),
    )
    active_requests = count(
        FacialSearchRequest,
        FacialSearchRequest.representation_reference == reference,
        FacialSearchRequest.status.not_in(("cancelled", "expired")),
    )
    return {
        "clean": references == candidates == pending_notifications == active_requests == 0,
        "active_requests": active_requests,
        "references": references,
        "candidates": candidates,
        "pending_notifications": pending_notifications,
    }


def fulfill_legal_representation_deletion(
    db: Session,
    *,
    representation_id: UUID,
    actor_admin_id: UUID,
    reference_root: Path,
) -> FacialRepresentationRightsReport:
    item = db.get(FacialLegalRepresentation, representation_id)
    if item is None or db.get(AdminUser, actor_admin_id) is None:
        raise FacialLegalRepresentationError("Representação legal indisponível.")
    reference = str(item.id)
    requests = list(
        db.scalars(
            select(FacialSearchRequest).where(
                FacialSearchRequest.representation_reference == reference,
                FacialSearchRequest.subject_declaration == "minor",
            )
        )
    )
    request_ids = [request.id for request in requests]
    references_deleted = 0
    for request in requests:
        if request.reference_locator_ciphertext is not None:
            references_deleted += int(delete_reference_file(reference_root, request.id))
    candidates_deleted = 0
    notifications_cancelled = 0
    jobs_cancelled = 0
    requests_cancelled = 0
    instant = now()
    if request_ids:
        candidate_result = db.execute(
            delete(FacialSearchCandidate).where(
                FacialSearchCandidate.search_request_id.in_(request_ids)
            )
        )
        candidates_deleted = candidate_result.rowcount or 0
        notification_result = db.execute(
            update(FacialSearchNotificationOutbox)
            .where(
                FacialSearchNotificationOutbox.search_request_id.in_(request_ids),
                FacialSearchNotificationOutbox.status.in_(("queued", "processing")),
            )
            .values(
                status="cancelled",
                payload_ciphertext=b"",
                payload_nonce=b"",
                last_error_category="representation_revoked",
                updated_at=instant,
            )
        )
        notifications_cancelled = notification_result.rowcount or 0
        job_result = db.execute(
            update(FacialJob)
            .where(
                FacialJob.search_request_id.in_(request_ids),
                FacialJob.status.in_(("queued", "processing")),
            )
            .values(
                status="cancelled",
                lease_token=None,
                lease_expires_at=None,
                last_error_category="representation_revoked",
                updated_at=instant,
            )
        )
        jobs_cancelled = job_result.rowcount or 0
        request_result = db.execute(
            update(FacialSearchRequest)
            .where(
                FacialSearchRequest.id.in_(request_ids),
                FacialSearchRequest.status.not_in(("cancelled", "expired")),
            )
            .values(status="cancelled", completed_at=instant, updated_at=instant)
        )
        requests_cancelled = request_result.rowcount or 0
        db.execute(
            update(FacialSearchRequest)
            .where(FacialSearchRequest.id.in_(request_ids))
            .values(
                reference_locator_ciphertext=None,
                reference_locator_nonce=None,
                reference_key_id=None,
                reference_deleted_at=instant,
                updated_at=instant,
            )
        )
    was_active = item.status != "revoked"
    revoke_legal_representation(
        db, representation_id=item.id, actor_admin_id=actor_admin_id
    )
    report = FacialRepresentationRightsReport(
        representations_revoked=int(was_active),
        requests_cancelled=requests_cancelled,
        references_deleted=references_deleted,
        candidates_deleted=candidates_deleted,
        notifications_cancelled=notifications_cancelled,
        jobs_cancelled=jobs_cancelled,
    )
    db.add(
        AuditEvent(
            event="facial.legal_representation_rights_fulfilled",
            subject=(
                f"representation_id:{item.id};requests:{report.requests_cancelled};"
                f"references:{report.references_deleted};"
                f"candidates:{report.candidates_deleted}"
            ),
        )
    )
    db.flush()
    return report
