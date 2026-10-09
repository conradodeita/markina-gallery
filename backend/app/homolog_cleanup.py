"""Inventário e limpeza explícita dos dados sintéticos de homologação.

Não é uma API. O módulo só executa dentro do container Markina com APP_ENV de
homologação e exige uma confirmação literal para a fase destrutiva.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

from sqlalchemy import delete, func, inspect, or_, select, text, update
from sqlalchemy.orm import Session

from app.auth import (
    AuditEvent,
    AuthSession,
    Base,
    ParentGallery,
    PushSubscription,
    Role,
    SessionLocal,
    Tenant,
)
from app.media import derivatives_root, source_root
from app.system_monitor import models as monitor_models
from app.tenancy import require_single_tenant

CONFIRMATION = "DELETE_HOMOLOG_GALLERIES_AND_CLIENTS"
WITHOUT_BACKUP_CONFIRMATION = "DELETE_HOMOLOG_GALLERIES_AND_CLIENTS_WITHOUT_BACKUP"
ALLOWED_ENVIRONMENTS = {"homolog", "homologation"}
EXPECTED_MEDIA_ROOTS = {
    "source": Path("/var/lib/markina/source"),
    "derivatives": Path("/var/lib/markina/derivatives"),
    "history": Path("/var/lib/markina/history"),
    "facial_references": Path("/var/lib/markina/facial-references"),
}

# Lista fechada: uma migration que adicione tabela sem classificação bloqueia a limpeza.
# As linhas mistas são tratadas separadamente para preservar sessões e push do admin.
MONITOR_PRESERVED_TABLES = frozenset({
    monitor_models.PlatformOwner.__tablename__, monitor_models.MonitorGrant.__tablename__,
    monitor_models.MonitorActivity.__tablename__, monitor_models.MonitorBucket.__tablename__,
    monitor_models.MonitorSample.__tablename__, monitor_models.MonitorWorker.__tablename__,
    monitor_models.MonitorIncident.__tablename__, monitor_models.MonitorTransition.__tablename__,
})
PRESERVED_TABLES = MONITOR_PRESERVED_TABLES | frozenset({
    "admin_action_token", "admin_security_challenge", "admin_user", "installation_operator",
    "branding_settings", "email_delivery", "email_delivery_attempt",
    "facial_calibration_approval", "facial_rollout_operation",
    "global_pix_settings", "notification_setting", "payment_message_template",
    "preview_adjustment_settings", "progressive_pricing_preset",
    "progressive_pricing_tier", "whatsapp_channel_settings", "tenant", "tenant_admin",
})
MIXED_TABLES = frozenset({"audit_event", "auth_session", "push_subscription"})
OPERATIONAL_TABLES = frozenset({
    "asset_file_cleanup", "auth_challenge", "client",
    "client_deletion_receipt", "client_phone", "commercial_history_media",
    "derived_gallery", "derived_gallery_membership", "derived_gallery_photo",
    "derived_gallery_photo_origin", "facial_job", "facial_legal_representation",
    "facial_rollout", "facial_search_candidate", "facial_search_notification_outbox",
    "facial_search_request", "facial_search_snapshot_item", "folder_client_grant",
    "folder_processing_settings",
    "gallery_access", "gallery_access_capability", "gallery_client_state",
    "gallery_facial_policy", "gallery_lifecycle_operation",
    "gallery_membership_notification_outbox", "gallery_preview_settings",
    "gallery_reopening_notification_outbox", "gallery_reopening_request",
    "media_derivative", "media_job", "notification_delivery", "notification_event",
    "notification_milestone", "parent_gallery", "parent_gallery_registration",
    "payment_communication", "payment_confirmation_correction", "payment_group",
    "payment_notification_outbox", "photo_analysis", "photo_asset", "photo_comment",
    "photo_face_embedding", "photo_favorite", "photo_folder", "photo_selection",
    "photo_view", "pix_checkout_settings", "preview_adjustment", "price_rule",
    "private_upload_batch", "private_upload_batch_asset", "removed_photo_movement",
    "sale_order", "sale_order_item", "whatsapp_delivery",
    "whatsapp_delivery_attempt", "whatsapp_webhook_receipt",
})


def require_known_schema(db: Session) -> None:
    classified = PRESERVED_TABLES | MIXED_TABLES | OPERATIONAL_TABLES
    modeled = set(Base.metadata.tables)
    if modeled != classified:
        raise RuntimeError(f"Tabela do modelo sem política de limpeza: {sorted(modeled ^ classified)}")
    if db.bind is None:
        raise RuntimeError("Conexão de banco indisponível.")
    actual = set(inspect(db.bind).get_table_names())
    unknown = actual - classified - {"alembic_version"}
    missing = classified - actual
    if unknown or missing:
        raise RuntimeError(
            f"Schema inesperado; tabelas desconhecidas={sorted(unknown)}, ausentes={sorted(missing)}"
        )


def require_homolog_environment() -> str:
    environment = os.getenv("APP_ENV", "").strip().lower()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise RuntimeError("A limpeza só pode executar com APP_ENV de homologação.")
    return environment


def _count(db: Session, model, *criteria) -> int:
    statement = select(func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    return int(db.scalar(statement) or 0)


def admin_security_audit_criteria():
    return or_(
        AuditEvent.event.like("installation_operator.%"),
        AuditEvent.event.like("system_monitor.%"),
        AuditEvent.event.like("admin_security.%"),
        AuditEvent.event.like("admin_password.%"),
        AuditEvent.event.like("admin_totp.%"),
        AuditEvent.event == "admin.redirected",
    )


def _media_inventory(root: Path) -> dict[str, int]:
    resolved = root.resolve()
    files = [] if not resolved.exists() else [path for path in resolved.rglob("*")]
    regular_files = [
        path for path in files if stat.S_ISREG(path.lstat().st_mode)
    ]
    return {
        "files": len(regular_files),
        "bytes": sum(path.lstat().st_size for path in regular_files),
    }


def media_roots() -> dict[str, Path]:
    return {
        "source": source_root(),
        "derivatives": derivatives_root(),
        "history": Path(os.getenv("MEDIA_HISTORY_ROOT", "/var/lib/markina/history")),
        "facial_references": Path(os.getenv(
            "FACIAL_REFERENCE_ROOT", "/var/lib/markina/facial-references"
        )),
    }


def require_exclusive_media_roots(roots: dict[str, Path]) -> None:
    for name, expected in EXPECTED_MEDIA_ROOTS.items():
        root = roots[name]
        if root.resolve() != expected.resolve() or not root.is_dir():
            raise RuntimeError(f"Volume de mídia exclusivo da Markina inválido: {name}.")


def inventory(db: Session) -> dict[str, object]:
    environment = require_homolog_environment()
    require_known_schema(db)
    photographer_count = _count(db, Tenant)
    operational_counts = {
        name: _count(db, Base.metadata.tables[name]) for name in sorted(OPERATIONAL_TABLES)
    }
    operational_counts["client_sessions"] = _count(
        db, AuthSession, AuthSession.role == Role.CLIENT.value
    )
    operational_counts["client_push_subscriptions"] = _count(
        db, PushSubscription, PushSubscription.role == Role.CLIENT.value
    )
    operational_counts["client_gallery_audit_events"] = _count(
        db, AuditEvent, ~admin_security_audit_criteria()
    )
    if photographer_count == 0:
        cleanup_status = "unavailable_no_photographers"
    elif photographer_count > 1:
        cleanup_status = "unavailable_multiple_photographers"
    else:
        cleanup_status = "single_photographer_only"
    preserved_counts = {
        name: _count(db, Base.metadata.tables[name]) for name in sorted(PRESERVED_TABLES)
    }
    preserved_counts["admin_sessions"] = _count(
        db, AuthSession, AuthSession.role == Role.ADMIN.value
    )
    preserved_counts["admin_push_subscriptions"] = _count(
        db, PushSubscription, PushSubscription.role == Role.ADMIN.value
    )
    preserved_counts["admin_security_audit_events"] = _count(
        db, AuditEvent, admin_security_audit_criteria()
    )
    return {
        "environment": environment,
        "photographer_count": photographer_count,
        "destructive_cleanup": {"status": cleanup_status},
        "database": operational_counts,
        "preserved": preserved_counts,
        "media": {name: _media_inventory(root) for name, root in media_roots().items()},
    }


def _clear_media_root(root: Path) -> None:
    resolved = root.resolve()
    if resolved not in {path.resolve() for path in EXPECTED_MEDIA_ROOTS.values()}:
        raise RuntimeError("Raiz de mídia fora do volume exclusivo da Markina.")
    if not resolved.is_dir():
        return
    entries = sorted(resolved.rglob("*"), key=lambda item: len(item.parts), reverse=True)
    for entry in entries:
        if entry.is_file() or entry.is_symlink():
            entry.unlink()
        elif entry.is_dir():
            entry.rmdir()


def execute(db: Session, confirmation: str) -> dict[str, object]:
    require_homolog_environment()
    if confirmation not in {CONFIRMATION, WITHOUT_BACKUP_CONFIRMATION}:
        raise RuntimeError("Confirmação literal inválida; nenhuma alteração foi aplicada.")
    if db.bind is None or db.bind.dialect.name != "postgresql":
        raise RuntimeError("A limpeza homologada exige o PostgreSQL exclusivo da Markina.")
    # Serializar provisionamento/suspensão enquanto a operação integral decide
    # seu único proprietário. Escritores próprios ainda exigem barreira offline.
    connection = db.connection()
    schema_map = connection.get_execution_options().get("schema_translate_map", {})
    schema = schema_map.get(Tenant.__table__.schema, Tenant.__table__.schema)
    preparer = connection.dialect.identifier_preparer
    table_name = preparer.quote(Tenant.__tablename__)
    qualified = f"{preparer.quote_schema(schema)}.{table_name}" if schema else table_name
    db.execute(text(f"LOCK TABLE {qualified} IN SHARE ROW EXCLUSIVE MODE"))
    require_single_tenant(db)
    require_known_schema(db)
    order = operational_delete_order()
    if db.scalar(select(AuthSession.id).where(
        AuthSession.role == Role.ADMIN.value, AuthSession.client_subject_id.is_not(None)
    ).limit(1)) or db.scalar(select(PushSubscription.id).where(
        PushSubscription.role == Role.ADMIN.value, PushSubscription.client_subject_id.is_not(None)
    ).limit(1)):
        raise RuntimeError("Vínculo administrativo inesperado; limpeza interrompida.")
    roots = media_roots()
    require_exclusive_media_roots(roots)
    # As tabelas mistas conservam linhas administrativas. TRUNCATE não permite
    # isso quando qualquer FK aponta ao cliente, mesmo com as linhas vazias.
    db.execute(delete(PushSubscription).where(PushSubscription.role == Role.CLIENT.value))
    db.execute(delete(AuthSession).where(AuthSession.role == Role.CLIENT.value))
    db.execute(update(ParentGallery).values(cover_photo_id=None))
    for name in order:
        db.execute(delete(Base.metadata.tables[name]))
    db.execute(delete(AuditEvent).where(~admin_security_audit_criteria()))
    db.commit()

    # Nova transação: se houve provisionamento entre o commit e os arquivos,
    # recusar antes de tocar a mídia. O lock fica até terminar essa fase.
    db.execute(text(f"LOCK TABLE {qualified} IN SHARE ROW EXCLUSIVE MODE"))
    require_single_tenant(db)
    for root in roots.values():
        _clear_media_root(root)
    db.commit()
    return inventory(db)


def operational_delete_order() -> list[str]:
    """Filhos antes dos pais; único ciclo permitido é a capa operacional nullable."""
    dependencies = {}
    for name in OPERATIONAL_TABLES:
        targets = set()
        for foreign_key in Base.metadata.tables[name].foreign_key_constraints:
            target = foreign_key.referred_table.name
            if target not in OPERATIONAL_TABLES or target == name:
                continue
            if name == "parent_gallery" and target == "photo_asset" and any(
                item.parent.name == "cover_photo_id" for item in foreign_key.elements
            ):
                continue
            targets.add(target)
        dependencies[name] = targets
    order = []
    while dependencies:
        referenced = set().union(*dependencies.values())
        children = sorted(set(dependencies) - referenced)
        if not children:
            raise RuntimeError("Ciclo operacional sem política de limpeza; nenhuma alteração aplicada.")
        order.extend(children)
        for name in children:
            dependencies.pop(name)
        for targets in dependencies.values():
            targets.difference_update(children)
    return order


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("inventory", "execute"), required=True)
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args()
    with SessionLocal() as db:
        result = (
            inventory(db)
            if args.mode == "inventory"
            else execute(db, args.confirmation)
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
