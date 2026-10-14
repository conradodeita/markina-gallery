"""Diretório da conta e exclusão segura do estado operacional de clientes."""

from __future__ import annotations

import base64
import binascii
import json
import re
from datetime import UTC
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    AuditEvent,
    AuthChallenge,
    AuthSession,
    Client,
    ClientDeletionReceipt,
    ClientPhone,
    CommercialHistoryMedia,
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    DerivedGalleryPhotoOrigin,
    FacialJob,
    FacialSearchCandidate,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    FacialSearchSnapshotItem,
    FolderClientGrant,
    GalleryAccess,
    GalleryAccessCapability,
    GalleryClientState,
    GalleryMembershipNotificationOutbox,
    GalleryReopeningNotificationOutbox,
    GalleryReopeningRequest,
    ParentGalleryRegistration,
    PaymentCommunication,
    PaymentGroup,
    PaymentNotificationOutbox,
    PhotoComment,
    PhotoFavorite,
    PhotoSelection,
    PhotoView,
    Role,
    SaleOrder,
    SaleOrderItem,
    WhatsAppDelivery,
    WhatsAppDeliveryAttempt,
    now,
    pii_fingerprint,
)
from app.client_identity import ClientIdentityConflict, require_identity_tenant
from app.facial.reference_store import delete_reference_file
from app.tenancy import TenantContextError, require_admin_tenant


class ClientLifecycleError(RuntimeError):
    """Erro sanitizado do contrato administrativo de lifecycle."""


class ClientDeletionBlocked(ClientLifecycleError):
    def __init__(self, inventory: dict[str, object]) -> None:
        super().__init__("A cliente possui histórico comercial protegido.")
        self.inventory = inventory


def list_client_directory(
    db: Session,
    *,
    tenant_id: UUID,
    query: str | None,
    cursor: str | None,
    limit: int,
) -> dict[str, object]:
    """Lista clientes e agregados em uma consulta de tamanho constante."""

    try:
        require_identity_tenant(db, tenant_id)
    except ClientIdentityConflict as exc:
        raise ClientLifecycleError("Diretório indisponível.") from exc

    public_count = (
        select(func.count(func.distinct(ParentGalleryRegistration.parent_gallery_id)))
        .where(
            ParentGalleryRegistration.tenant_id == tenant_id,
            ParentGalleryRegistration.client_id == Client.id,
            ParentGalleryRegistration.status != "revoked",
        )
        .correlate(Client)
        .scalar_subquery()
    )
    membership_count = (
        select(func.count(func.distinct(DerivedGalleryMembership.derived_gallery_id)))
        .where(
            DerivedGalleryMembership.tenant_id == tenant_id,
            DerivedGalleryMembership.client_id == Client.id,
            DerivedGalleryMembership.status != "unlinked",
        )
        .correlate(Client)
        .scalar_subquery()
    )
    owned_without_membership = (
        select(func.count(DerivedGallery.id))
        .where(
            DerivedGallery.tenant_id == tenant_id,
            DerivedGallery.client_id == Client.id,
            ~select(DerivedGalleryMembership.id)
            .where(
                DerivedGalleryMembership.tenant_id == tenant_id,
                DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id,
                DerivedGalleryMembership.client_id == Client.id,
                DerivedGalleryMembership.status != "unlinked",
            )
            .exists(),
        )
        .correlate(Client)
        .scalar_subquery()
    )
    order_count = (
        select(func.count(SaleOrder.id))
        .where(SaleOrder.tenant_id == tenant_id, SaleOrder.client_id == Client.id)
        .correlate(Client)
        .scalar_subquery()
    )
    payment_count = (
        select(func.count(PaymentCommunication.id))
        .where(PaymentCommunication.tenant_id == tenant_id, PaymentCommunication.client_id == Client.id)
        .correlate(Client)
        .scalar_subquery()
    )
    payment_group_count = (
        select(func.count(PaymentGroup.id))
        .where(PaymentGroup.tenant_id == tenant_id, PaymentGroup.client_id == Client.id)
        .correlate(Client)
        .scalar_subquery()
    )
    normalized_name = func.lower(Client.full_name)
    statement = select(
        Client,
        public_count.label("public_count"),
        (membership_count + owned_without_membership).label("private_count"),
        order_count.label("order_count"),
        (payment_count + payment_group_count).label("payment_count"),
        normalized_name.label("sort_name"),
    ).where(Client.tenant_id == tenant_id)
    normalized_query = (query or "").strip().casefold()
    if normalized_query:
        phone_query = re.sub(r"\D", "", normalized_query)
        search_criteria = [
            normalized_name.contains(normalized_query),
            Client.phone_e164.contains(normalized_query),
        ]
        if phone_query:
            search_criteria.append(Client.phone_e164.contains(phone_query))
        statement = statement.where(
            or_(*search_criteria)
        )
    if cursor:
        cursor_name, cursor_id = _decode_cursor(cursor, tenant_id)
        statement = statement.where(
            or_(
                normalized_name > cursor_name,
                and_(normalized_name == cursor_name, Client.id > cursor_id),
            )
        )
    rows = list(db.execute(statement.order_by(normalized_name, Client.id).limit(limit + 1)))
    has_more = len(rows) > limit
    visible = rows[:limit]
    next_cursor = None
    if has_more and visible:
        last_client = visible[-1][0]
        next_cursor = _encode_cursor(str(visible[-1][5]), last_client.id, tenant_id)
    return {
        "clients": [
            {
                "id": str(item.id),
                "name": item.full_name,
                "phone": item.phone_e164,
                "aggregates": {
                    "public_galleries": int(public_galleries or 0),
                    "private_galleries": int(private_galleries or 0),
                    "orders": int(orders or 0),
                },
                "deletion_eligible": not int(orders or 0) and not int(payments or 0),
            }
            for item, public_galleries, private_galleries, orders, payments, _sort_name in visible
        ],
        "page": {"has_more": has_more, "next_cursor": next_cursor},
    }


def deletion_inventory(db: Session, client: Client, *, tenant_id: UUID) -> dict[str, object]:
    require_active_owner(db, tenant_id)
    if client.tenant_id != tenant_id:
        raise ClientLifecycleError("Cliente não encontrada.")
    phones = _client_auth_phones(db, client, tenant_id=tenant_id)
    fingerprints = [pii_fingerprint(phone) for phone in phones]
    gallery_ids = _client_gallery_ids(db, client.id, tenant_id=tenant_id)
    exclusive, shared = _classify_private_galleries(db, client.id, gallery_ids, tenant_id=tenant_id)
    reopening_ids = select(GalleryReopeningRequest.id).where(GalleryReopeningRequest.tenant_id == tenant_id).where(
        GalleryReopeningRequest.requested_by_client_id == client.id
    )

    operational = {
        "client": 1,
        "phone_records": _count(db, ClientPhone, ClientPhone.client_id == client.id, tenant_id=tenant_id),
        "gallery_accesses": _count(db, GalleryAccess, GalleryAccess.client_id == client.id, tenant_id=tenant_id),
        "public_gallery_registrations": _count(
            db, ParentGalleryRegistration, ParentGalleryRegistration.client_id == client.id,
            tenant_id=tenant_id,
        ),
        "gallery_client_states": _count(
            db, GalleryClientState, GalleryClientState.client_id == client.id,
            tenant_id=tenant_id,
        ),
        "folder_client_grants": _count(
            db, FolderClientGrant, FolderClientGrant.client_id == client.id,
            tenant_id=tenant_id,
        ),
        "reopening_requests": _count(
            db, GalleryReopeningRequest,
            GalleryReopeningRequest.requested_by_client_id == client.id,
            tenant_id=tenant_id,
       ),
        "reopening_notifications": _count(
            db, GalleryReopeningNotificationOutbox,
            GalleryReopeningNotificationOutbox.gallery_reopening_request_id.in_(reopening_ids),
            tenant_id=tenant_id,
       ),
        "private_galleries_exclusive": len(exclusive),
        "private_galleries_shared": len(shared),
        "private_gallery_memberships": _count(
            db, DerivedGalleryMembership, DerivedGalleryMembership.client_id == client.id,
            tenant_id=tenant_id,
        ),
        "gallery_capabilities": _count(
            db,
            GalleryAccessCapability,
            _capability_deletion_predicate(client.id, exclusive),
            tenant_id=tenant_id,
       ),
        "selections": _count(db, PhotoSelection, PhotoSelection.client_id == client.id, tenant_id=tenant_id),
        "favorites": _count(db, PhotoFavorite, PhotoFavorite.client_id == client.id, tenant_id=tenant_id),
        "views": _count(db, PhotoView, PhotoView.client_id == client.id, tenant_id=tenant_id),
        "comments": _count(db, PhotoComment, PhotoComment.client_id == client.id, tenant_id=tenant_id),
        "membership_notifications": _count(
            db,
            GalleryMembershipNotificationOutbox,
            GalleryMembershipNotificationOutbox.client_id == client.id,
            tenant_id=tenant_id,
       ),
        "sessions": _count(
            db,
            AuthSession,
            AuthSession.role == Role.CLIENT.value,
            AuthSession.subject_id == client.id,
            tenant_id=tenant_id,
       ),
        "otp_challenges": _count(
            db,
            AuthChallenge,
            AuthChallenge.kind == "client_otp",
            _phone_predicate(
                phones,
                fingerprints,
                AuthChallenge.subject,
                AuthChallenge.subject_fingerprint,
            ),
            tenant_id=tenant_id,
       ),
        "otp_deliveries": _delivery_count(db, phones, fingerprints, kind="otp", tenant_id=tenant_id),
        "facial_searches": _count(
            db, FacialSearchRequest, FacialSearchRequest.client_id == client.id,
            tenant_id=tenant_id,
        ),
    }
    order_ids = select(SaleOrder.id).where(SaleOrder.tenant_id == tenant_id).where(SaleOrder.client_id == client.id)
    communication_ids = list(
        db.scalars(
            select(PaymentCommunication.id).where(PaymentCommunication.tenant_id == tenant_id).where(
                PaymentCommunication.client_id == client.id
            )
        )
    )
    notification_ids = list(
        db.scalars(
            select(PaymentNotificationOutbox.id).where(PaymentNotificationOutbox.tenant_id == tenant_id).where(
                PaymentNotificationOutbox.payment_communication_id.in_(communication_ids)
            )
        )
    )
    protected = {
        "orders": _count(db, SaleOrder, SaleOrder.client_id == client.id, tenant_id=tenant_id),
        "payment_groups": _count(db, PaymentGroup, PaymentGroup.client_id == client.id, tenant_id=tenant_id),
        "order_items": int(
            db.scalar(
                select(func.count())
                .select_from(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id)
                .where(SaleOrderItem.sale_order_id.in_(order_ids))
            )
            or 0
        ),
        "payment_communications": _count(
            db, PaymentCommunication, PaymentCommunication.client_id == client.id,
            tenant_id=tenant_id,
        ),
        "payment_notifications": len(notification_ids),
        "commercial_media": int(
            db.scalar(
                select(func.count())
                .select_from(CommercialHistoryMedia).where(CommercialHistoryMedia.tenant_id == tenant_id)
                .join(
                    SaleOrderItem,
                    SaleOrderItem.id == CommercialHistoryMedia.sale_order_item_id,
                )
                .where(SaleOrderItem.sale_order_id.in_(order_ids))
            )
            or 0
        ),
        "payment_deliveries": _payment_delivery_count(
            db,
            communication_ids=communication_ids,
            notification_ids=notification_ids,
            tenant_id=tenant_id,
       ),
    }
    from app.auth import RemovedPhotoMovement
    retained_movements = _count(db, RemovedPhotoMovement, RemovedPhotoMovement.client_id == client.id, tenant_id=tenant_id)
    if retained_movements:
        protected["removed_movements"] = retained_movements
    return {
        "client_id": str(client.id),
        "operational_removable": operational,
        "commercial_protected": protected,
        "can_delete": not any(protected.values()),
    }


def delete_client_operational_graph(
    db: Session,
    *,
    client_id: UUID,
    actor_admin_id: UUID,
    tenant_id: UUID,
    idempotency_key: str,
) -> tuple[dict[str, object], list[UUID]]:
    """Executa o grafo em uma transação; o chamador confirma antes do arquivo físico."""

    require_active_owner(db, tenant_id)
    try:
        if require_admin_tenant(db, actor_admin_id).id != tenant_id:
            raise TenantContextError("Acesso negado.")
    except TenantContextError as exc:
        raise ClientLifecycleError("Acesso negado.") from exc
    idempotency_fingerprint = sha256(idempotency_key.encode("utf-8")).hexdigest()
    existing = db.scalar(
        select(ClientDeletionReceipt).where(ClientDeletionReceipt.tenant_id == tenant_id).where(
            ClientDeletionReceipt.idempotency_key == idempotency_fingerprint
        )
    )
    if existing:
        if existing.target_client_id != client_id:
            raise ClientLifecycleError("A chave idempotente já foi usada em outra operação.")
        return receipt_payload(existing), []

    client = db.scalar(select(Client).where(Client.tenant_id == tenant_id).where(Client.id == client_id).with_for_update())
    if not client:
        raise ClientLifecycleError("Cliente não encontrada.")
    inventory = deletion_inventory(db, client, tenant_id=tenant_id)
    if not inventory["can_delete"]:
        raise ClientDeletionBlocked(inventory)

    fingerprint = _inventory_fingerprint(inventory)
    search_ids = list(
        db.scalars(select(FacialSearchRequest.id).where(FacialSearchRequest.tenant_id == tenant_id).where(FacialSearchRequest.client_id == client.id))
    )
    gallery_ids = _client_gallery_ids(db, client.id, tenant_id=tenant_id)
    exclusive_ids, shared_ids = _classify_private_galleries(db, client.id, gallery_ids, tenant_id=tenant_id)
    counts: dict[str, int] = {}

    reopening_ids = select(GalleryReopeningRequest.id).where(GalleryReopeningRequest.tenant_id == tenant_id).where(
        GalleryReopeningRequest.requested_by_client_id == client.id
    )
    counts["reopening_notifications"] = _delete_where(
        db,
        GalleryReopeningNotificationOutbox,
        GalleryReopeningNotificationOutbox.gallery_reopening_request_id.in_(reopening_ids),
        tenant_id=tenant_id,
    )
    counts["reopening_requests"] = _delete_where(
        db, GalleryReopeningRequest,
        GalleryReopeningRequest.requested_by_client_id == client.id,
        tenant_id=tenant_id,
    )
    counts["folder_client_grants"] = _delete_where(
        db, FolderClientGrant, FolderClientGrant.client_id == client.id,
        tenant_id=tenant_id,
    )

    if search_ids:
        counts["facial_notifications"] = _delete_where(
            db,
            FacialSearchNotificationOutbox,
            FacialSearchNotificationOutbox.search_request_id.in_(search_ids),
            tenant_id=tenant_id,
        )
        counts["facial_candidates"] = _delete_where(
            db, FacialSearchCandidate, FacialSearchCandidate.search_request_id.in_(search_ids),
            tenant_id=tenant_id,
        )
        counts["facial_snapshots"] = _delete_where(
            db,
            FacialSearchSnapshotItem,
            FacialSearchSnapshotItem.search_request_id.in_(search_ids),
            tenant_id=tenant_id,
        )
        counts["facial_jobs"] = _delete_where(
            db, FacialJob, FacialJob.search_request_id.in_(search_ids),
            tenant_id=tenant_id,
        )
        counts["facial_searches"] = _delete_where(
            db, FacialSearchRequest, FacialSearchRequest.id.in_(search_ids),
            tenant_id=tenant_id,
        )

    for model, name in (
        (PhotoSelection, "selections"),
        (PhotoFavorite, "favorites"),
        (PhotoView, "views"),
        (PhotoComment, "comments"),
    ):
        counts[name] = _delete_where(db, model, model.client_id == client.id, tenant_id=tenant_id)

    capability_ids = list(
        db.scalars(
            select(GalleryAccessCapability.id).where(GalleryAccessCapability.tenant_id == tenant_id).where(
                _capability_deletion_predicate(client.id, exclusive_ids)
            )
        )
    )
    if capability_ids:
        db.execute(
            update(GalleryAccessCapability).where(GalleryAccessCapability.tenant_id == tenant_id)
            .where(GalleryAccessCapability.rotated_from_id.in_(capability_ids))
            .values(rotated_from_id=None)
        )
    counts["gallery_capabilities"] = (
        _delete_where(
            db,
            GalleryAccessCapability,
            GalleryAccessCapability.id.in_(capability_ids),
            tenant_id=tenant_id,
        )
        if capability_ids
        else 0
    )

    if exclusive_ids:
        private_photo_ids = select(DerivedGalleryPhoto.id).where(DerivedGalleryPhoto.tenant_id == tenant_id).where(
            DerivedGalleryPhoto.derived_gallery_id.in_(exclusive_ids)
        )
        counts["private_photo_origins"] = _delete_where(
            db,
            DerivedGalleryPhotoOrigin,
            DerivedGalleryPhotoOrigin.derived_gallery_photo_id.in_(private_photo_ids),
            tenant_id=tenant_id,
        )
        counts["private_photos"] = _delete_where(
            db, DerivedGalleryPhoto, DerivedGalleryPhoto.derived_gallery_id.in_(exclusive_ids),
            tenant_id=tenant_id,
        )
        counts["exclusive_memberships"] = _delete_where(
            db,
            DerivedGalleryMembership,
            DerivedGalleryMembership.derived_gallery_id.in_(exclusive_ids),
            tenant_id=tenant_id,
        )
        counts["exclusive_private_galleries"] = _delete_where(
            db, DerivedGallery, DerivedGallery.id.in_(exclusive_ids),
            tenant_id=tenant_id,
        )

    for gallery_id in shared_ids:
        gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
        if gallery and gallery.client_id == client.id:
            successor = _shared_gallery_successor(db, gallery_id, client.id, tenant_id=tenant_id)
            if successor is None:
                raise ClientLifecycleError("A privada compartilhada não possui sucessora válida.")
            gallery.client_id = successor

    counts["memberships"] = _delete_where(
        db, DerivedGalleryMembership, DerivedGalleryMembership.client_id == client.id,
        tenant_id=tenant_id,
    )
    counts["membership_notifications"] = _delete_where(
        db,
        GalleryMembershipNotificationOutbox,
        GalleryMembershipNotificationOutbox.client_id == client.id,
        tenant_id=tenant_id,
    )
    counts["public_gallery_registrations"] = _delete_where(
        db, ParentGalleryRegistration, ParentGalleryRegistration.client_id == client.id,
        tenant_id=tenant_id,
    )
    counts["gallery_client_states"] = _delete_where(
        db, GalleryClientState, GalleryClientState.client_id == client.id,
        tenant_id=tenant_id,
    )
    counts["gallery_accesses"] = _delete_where(
        db, GalleryAccess, GalleryAccess.client_id == client.id,
        tenant_id=tenant_id,
    )
    counts["sessions"] = _delete_where(
        db,
        AuthSession,
        AuthSession.role == Role.CLIENT.value,
        AuthSession.subject_id == client.id,
        tenant_id=tenant_id,
    )

    phones = _client_auth_phones(db, client, tenant_id=tenant_id)
    fingerprints = [pii_fingerprint(phone) for phone in phones]
    otp_delivery_ids = list(
        db.scalars(
            select(WhatsAppDelivery.id).where(WhatsAppDelivery.tenant_id == tenant_id).where(
                WhatsAppDelivery.kind == "otp",
                WhatsAppDelivery.source_type == "auth_challenge",
                _phone_predicate(
                    phones,
                    fingerprints,
                    WhatsAppDelivery.recipient_phone,
                    WhatsAppDelivery.recipient_fingerprint,
                ),
            )
        )
    )
    if otp_delivery_ids:
        counts["otp_delivery_attempts"] = _delete_where(
            db, WhatsAppDeliveryAttempt, WhatsAppDeliveryAttempt.delivery_id.in_(otp_delivery_ids),
            tenant_id=tenant_id,
        )
        counts["otp_deliveries"] = _delete_where(
            db, WhatsAppDelivery, WhatsAppDelivery.id.in_(otp_delivery_ids),
            tenant_id=tenant_id,
        )
    counts["otp_challenges"] = _delete_where(
        db,
        AuthChallenge,
        AuthChallenge.kind == "client_otp",
        _phone_predicate(
            phones,
            fingerprints,
            AuthChallenge.subject,
            AuthChallenge.subject_fingerprint,
        ),
        tenant_id=tenant_id,
    )
    counts["phone_records"] = _delete_where(
        db, ClientPhone, ClientPhone.client_id == client.id,
        tenant_id=tenant_id,
    )

    # A rechecagem ocorre já sob lock e imediatamente antes da remoção da identidade.
    refreshed = deletion_inventory(db, client, tenant_id=tenant_id)
    if not refreshed["can_delete"]:
        raise ClientDeletionBlocked(refreshed)
    db.delete(client)
    counts["clients"] = 1
    completed_at = now()
    receipt = ClientDeletionReceipt(
        idempotency_key=idempotency_fingerprint,
        target_client_id=client_id,
        actor_admin_id=actor_admin_id,
        inventory_fingerprint=fingerprint,
        status="completed",
        removed_counts=counts,
        created_at=completed_at,
        completed_at=completed_at,
        tenant_id=tenant_id,
    )
    db.add(receipt)
    db.flush()
    db.add(
        AuditEvent(
            event="client.deleted_without_history",
            # Os detalhes completos ficam no recibo durável; a referência curta
            # evita exceder o limite de AuditEvent.subject no PostgreSQL.
            subject=f"client_deletion_receipt:{receipt.id}",
            tenant_id=tenant_id,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        replay = db.scalar(
            select(ClientDeletionReceipt).where(ClientDeletionReceipt.tenant_id == tenant_id).where(
                ClientDeletionReceipt.idempotency_key == idempotency_fingerprint
            )
        )
        if replay and replay.target_client_id == client_id:
            return receipt_payload(replay), []
        raise
    return receipt_payload(receipt), search_ids


def remove_facial_reference_files(reference_root: Path, request_ids: list[UUID], *, db: Session, tenant_id: UUID) -> int:
    removed = 0
    for request_id in request_ids:
        require_active_owner(db, tenant_id)
        removed += int(delete_reference_file(reference_root, request_id))
    return removed


def receipt_payload(receipt: ClientDeletionReceipt) -> dict[str, object]:
    completed_at = receipt.completed_at
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=UTC)
    return {
        "receipt_id": str(receipt.id),
        "client_id": str(receipt.target_client_id),
        "status": receipt.status,
        "counts": receipt.removed_counts,
        "completed_at": completed_at.isoformat(),
    }


def _client_gallery_ids(db: Session, client_id: UUID, *, tenant_id: UUID) -> list[UUID]:
    membership_ids = select(DerivedGalleryMembership.derived_gallery_id).where(DerivedGalleryMembership.tenant_id == tenant_id).where(
        DerivedGalleryMembership.client_id == client_id,
        DerivedGalleryMembership.status != "unlinked",
    )
    return list(
        db.scalars(
            select(DerivedGallery.id).where(DerivedGallery.tenant_id == tenant_id)
            .where(
                or_(
                    DerivedGallery.client_id == client_id,
                    DerivedGallery.id.in_(membership_ids),
                )
            )
            .order_by(DerivedGallery.id)
        )
    )


def _client_auth_phones(db: Session, client: Client, *, tenant_id: UUID) -> list[str]:
    """Retorna somente números atualmente atribuíveis à identidade alvo.

    Telefones aposentados podem ter sido reutilizados por outra pessoa. Associar OTPs e
    entregas pelo histórico inteiro apagaria estado operacional de terceiros.
    """

    phones = set(
        db.scalars(
            select(ClientPhone.phone_e164).where(ClientPhone.tenant_id == tenant_id).where(
                ClientPhone.client_id == client.id,
                ClientPhone.active,
            )
        )
    )
    phones.add(client.phone_e164)
    return sorted(phones)


def _classify_private_galleries(
    db: Session, client_id: UUID, gallery_ids: list[UUID], *, tenant_id: UUID
) -> tuple[list[UUID], list[UUID]]:
    exclusive: list[UUID] = []
    shared: list[UUID] = []
    for gallery_id in gallery_ids:
        target = shared if _shared_gallery_successor(db, gallery_id, client_id, tenant_id=tenant_id) else exclusive
        target.append(gallery_id)
    return exclusive, shared


def _shared_gallery_successor(
    db: Session, gallery_id: UUID, excluded_client_id: UUID, *, tenant_id: UUID
) -> UUID | None:
    """Encontra outra identidade com estado real na privada, sem descartar terceiros."""

    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    if gallery and gallery.client_id != excluded_client_id:
        return gallery.client_id
    candidate_queries = (
        select(DerivedGalleryMembership.client_id).where(DerivedGalleryMembership.tenant_id == tenant_id)
        .where(
            DerivedGalleryMembership.derived_gallery_id == gallery_id,
            DerivedGalleryMembership.client_id != excluded_client_id,
            DerivedGalleryMembership.status != "unlinked",
        )
        .order_by(DerivedGalleryMembership.created_at, DerivedGalleryMembership.id),
        select(SaleOrder.client_id).where(SaleOrder.tenant_id == tenant_id)
        .where(
            SaleOrder.derived_gallery_id == gallery_id,
            SaleOrder.client_id != excluded_client_id,
        )
        .order_by(SaleOrder.created_at, SaleOrder.id),
        select(PhotoSelection.client_id).where(PhotoSelection.tenant_id == tenant_id).where(
            PhotoSelection.derived_gallery_id == gallery_id,
            PhotoSelection.client_id != excluded_client_id,
        ),
        select(PhotoFavorite.client_id).where(PhotoFavorite.tenant_id == tenant_id).where(
            PhotoFavorite.derived_gallery_id == gallery_id,
            PhotoFavorite.client_id != excluded_client_id,
        ),
        select(PhotoView.client_id).where(PhotoView.tenant_id == tenant_id).where(
            PhotoView.derived_gallery_id == gallery_id,
            PhotoView.client_id != excluded_client_id,
        ),
        select(PhotoComment.client_id).where(PhotoComment.tenant_id == tenant_id).where(
            PhotoComment.derived_gallery_id == gallery_id,
            PhotoComment.client_id != excluded_client_id,
        ),
        select(GalleryAccess.client_id).where(GalleryAccess.tenant_id == tenant_id).where(
            GalleryAccess.gallery_id == gallery_id,
            GalleryAccess.client_id != excluded_client_id,
        ),
        select(GalleryAccessCapability.client_id).where(GalleryAccessCapability.tenant_id == tenant_id).where(
            GalleryAccessCapability.derived_gallery_id == gallery_id,
            GalleryAccessCapability.client_id.is_not(None),
            GalleryAccessCapability.client_id != excluded_client_id,
            GalleryAccessCapability.status == "active",
        ),
    )
    for statement in candidate_queries:
        candidate = db.scalar(statement.limit(1))
        if candidate is not None:
            return candidate
    return None


def _count(db: Session, model, *criteria, tenant_id: UUID) -> int:
    return int(
        db.scalar(select(func.count()).select_from(model).where(model.tenant_id == tenant_id).where(*criteria)) or 0
    )


def _capability_deletion_predicate(client_id: UUID, exclusive_ids: list[UUID]):
    criteria = [GalleryAccessCapability.client_id == client_id]
    if exclusive_ids:
        criteria.append(GalleryAccessCapability.derived_gallery_id.in_(exclusive_ids))
    return or_(*criteria)


def _delete_where(db: Session, model, *criteria, tenant_id: UUID) -> int:
    result = db.execute(delete(model).where(model.tenant_id == tenant_id, *criteria))
    return max(int(result.rowcount or 0), 0)


def _phone_predicate(phones, fingerprints, phone_column, fingerprint_column):
    clauses = []
    if phones:
        clauses.append(phone_column.in_(phones))
    if fingerprints:
        clauses.append(fingerprint_column.in_(fingerprints))
    return or_(*clauses) if clauses else phone_column.is_(None) & phone_column.is_not(None)


def _delivery_count(db: Session, phones: list[str], fingerprints: list[str], *, kind: str, tenant_id: UUID) -> int:
    return _count(
        db,
        WhatsAppDelivery,
        WhatsAppDelivery.kind == kind,
        WhatsAppDelivery.source_type == "auth_challenge",
        _phone_predicate(
            phones,
            fingerprints,
            WhatsAppDelivery.recipient_phone,
            WhatsAppDelivery.recipient_fingerprint,
        ),
        tenant_id=tenant_id,
    )


def _payment_delivery_count(
    db: Session,
    *,
    tenant_id: UUID,
    communication_ids: list[UUID],
    notification_ids: list[UUID],
) -> int:
    """Atribui entrega comercial pelo source persistido, nunca pelo telefone mutável."""

    sources = []
    if communication_ids:
        sources.append(
            and_(
                WhatsAppDelivery.source_type == "payment_communication",
                WhatsAppDelivery.source_id.in_([str(value) for value in communication_ids]),
            )
        )
    if notification_ids:
        sources.append(
            and_(
                WhatsAppDelivery.source_type == "payment_notification_outbox",
                WhatsAppDelivery.source_id.in_([str(value) for value in notification_ids]),
            )
        )
    if not sources:
        return 0
    return _count(
        db,
        WhatsAppDelivery,
        WhatsAppDelivery.kind == "payment",
        or_(*sources),
        tenant_id=tenant_id,
    )


def _inventory_fingerprint(inventory: dict[str, object]) -> str:
    stable = {
        "client_id": inventory["client_id"],
        "operational_removable": inventory["operational_removable"],
        "commercial_protected": inventory["commercial_protected"],
    }
    return sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _encode_cursor(name: str, client_id: UUID, tenant_id: UUID) -> str:
    scope = sha256(str(tenant_id).encode()).hexdigest()
    payload = json.dumps([name, str(client_id), scope], separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str, tenant_id: UUID) -> tuple[str, UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        name, raw_id, scope = json.loads(base64.urlsafe_b64decode(cursor + padding))
        if not isinstance(name, str) or scope != sha256(str(tenant_id).encode()).hexdigest():
            raise TypeError
        return name, UUID(raw_id)
    except (ValueError, TypeError, json.JSONDecodeError, binascii.Error) as exc:
        raise ClientLifecycleError("Cursor de paginação inválido.") from exc
