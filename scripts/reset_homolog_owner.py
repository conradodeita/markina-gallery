"""Reset explícito de homologação; executado com os modelos da imagem publicada.

Não é endpoint nem substitui a limpeza antiga. Nenhuma configuração é impressa
ou copiada para disco; o wrapper deve pausar e conferir todos os writers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from app import auth
from app.homolog_cleanup import (
    admin_security_audit_criteria,
    has_mercadopago_financial_history,
)
from app.system_monitor import models as monitor
from sqlalchemy import delete, false, func, inspect, or_, select, text, true, update

CONFIRMATION = "RESET_HOMOLOG_TO_OWNER_WITHOUT_BACKUP"
MEDIA_ROOTS = {
    "source": Path("/var/lib/markina/source"),
    "derivatives": Path("/var/lib/markina/derivatives"),
    "history": Path("/var/lib/markina/history"),
    "facial_references": Path("/var/lib/markina/facial-references"),
    "raw_staging": Path("/var/lib/markina/raw-staging"),
}
BRANDING_ROOT = Path("/var/lib/markina/branding")
ROOT_ENV = {
    "source": "MEDIA_SOURCE_ROOT", "derivatives": "MEDIA_DERIVATIVES_ROOT",
    "history": "MEDIA_HISTORY_ROOT", "facial_references": "FACIAL_REFERENCE_ROOT",
    "raw_staging": "RAW_DEVELOPMENT_ROOT",
}
OPERATIONAL = frozenset({
    "asset_file_cleanup", "auth_challenge", "client", "client_deletion_receipt", "client_phone",
    "commercial_history_media", "derived_gallery", "derived_gallery_membership", "derived_gallery_photo",
    "derived_gallery_photo_origin", "facial_job", "facial_legal_representation", "facial_rollout",
    "facial_search_candidate", "facial_search_notification_outbox", "facial_search_request",
    "facial_search_snapshot_item", "folder_client_grant", "folder_processing_settings", "gallery_access",
    "gallery_access_capability", "gallery_client_state", "gallery_facial_policy", "gallery_lifecycle_operation",
    "gallery_membership_notification_outbox", "gallery_preview_settings", "gallery_reopening_notification_outbox",
    "gallery_reopening_request", "media_derivative", "media_job", "notification_delivery", "notification_event",
    "notification_milestone", "parent_gallery", "parent_gallery_registration", "payment_communication",
    "payment_confirmation_correction", "payment_group", "payment_notification_outbox", "photo_analysis",
    "photo_asset", "photo_comment", "photo_face_embedding", "photo_favorite", "photo_folder", "photo_selection",
    "photo_view", "pix_checkout_settings", "preview_adjustment", "price_rule", "private_upload_batch",
    "private_upload_batch_asset", "provider_payment", "provider_payment_attempt", "provider_payment_correction",
    "provider_payment_receipt", "raw_development_job", "removed_photo_movement", "sale_order", "sale_order_item",
    "whatsapp_delivery", "whatsapp_delivery_attempt", "whatsapp_webhook_receipt", "email_delivery",
    "email_delivery_attempt",
    "mercadopago_payment", "mercadopago_webhook",
})
TENANT_CONFIG = frozenset({
    "branding_settings", "facial_calibration_approval", "facial_rollout_operation", "global_pix_settings",
    "notification_setting", "payment_message_template", "preview_adjustment_settings",
    "progressive_pricing_preset", "progressive_pricing_tier", "raw_development_settings", "whatsapp_channel_settings",
    "mercadopago_account", "payment_preferences",
})
GLOBAL_PRESERVED = frozenset({
    "facial_embedding_experiment_setting", "platform_owner", "system_monitor_bucket", "system_monitor_sample",
    "system_monitor_worker", "system_monitor_incident", "system_monitor_transition",
})
OWNER_SCOPED = frozenset({
    "admin_action_token", "admin_security_challenge", "admin_user", "installation_operator", "system_monitor_grant",
    "tenant", "tenant_admin", "auth_session", "push_subscription", "audit_event", "system_monitor_activity",
})
CLASSIFIED = OPERATIONAL | TENANT_CONFIG | GLOBAL_PRESERVED | OWNER_SCOPED


class ResetPolicyError(RuntimeError):
    """Mensagens sanitizadas e próprias da política; não contém parâmetros SQL."""


def require_schema(db):
    if set(auth.Base.metadata.tables) != CLASSIFIED:
        raise ResetPolicyError("Schema do modelo sem classificação de reset.")
    connection = db.connection()
    schema = connection.get_execution_options().get("schema_translate_map", {}).get(None)
    inspector = inspect(connection)
    actual = set(inspector.get_table_names(schema=schema)) - {"alembic_version"}
    if actual != CLASSIFIED:
        raise ResetPolicyError("Schema real sem classificação de reset.")
    columns = inspector.get_multi_columns(schema=schema, filter_names=list(CLASSIFIED))
    for name in CLASSIFIED:
        if {c["name"] for c in columns[(schema, name)]} != set(auth.Base.metadata.tables[name].c.keys()):
            raise ResetPolicyError("Coluna real sem classificação de reset.")


def foreign_keys(db):
    connection = db.connection()
    schema = connection.get_execution_options().get("schema_translate_map", {}).get(None)
    expected_schema = schema or connection.dialect.default_schema_name
    constraints = inspect(connection).get_multi_foreign_keys(schema=schema, filter_names=list(CLASSIFIED))
    result = {name: constraints[(schema, name)] for name in CLASSIFIED}
    for items in result.values():
        for fk in items:
            if fk["referred_table"] not in CLASSIFIED or fk.get("referred_schema") not in (None, expected_schema):
                raise ResetPolicyError("FK real fora do schema exclusivo de reset.")
    return result


def owner_context(db, email):
    if os.getenv("APP_ENV", "").lower() not in {"homolog", "homologation"}:
        raise ResetPolicyError("Reset permitido somente em homologação.")
    require_schema(db)
    owners = list(db.scalars(select(auth.AdminUser).where(func.lower(auth.AdminUser.email) == email.lower())))
    if len(owners) != 1:
        raise ResetPolicyError("Identidade proprietária ausente ou ambígua.")
    owner = owners[0]
    platform = list(db.scalars(select(monitor.PlatformOwner)))
    memberships = list(db.scalars(select(auth.TenantAdmin).where(auth.TenantAdmin.admin_user_id == owner.id)))
    operator = db.get(auth.InstallationOperator, owner.id)
    if len(platform) != 1 or platform[0].admin_user_id != owner.id:
        raise ResetPolicyError("Conta não corresponde à proprietária da plataforma.")
    if not operator or not operator.active or operator.revoked_at is not None:
        raise ResetPolicyError("Privilégio proprietário de operação ausente.")
    if len(memberships) != 1 or not memberships[0].active:
        raise ResetPolicyError("Vínculo proprietário ausente ou ambíguo.")
    tenant = db.get(auth.Tenant, memberships[0].tenant_id)
    if tenant is None or tenant.status != "active":
        raise ResetPolicyError("Tenant proprietário não está ativo.")
    if has_mercadopago_financial_history(db):
        raise ResetPolicyError(
            "Reset bloqueado: preserve e reconcilie as evidências financeiras Mercado Pago.")
    return owner, memberships[0], tenant


def policy(db, owner, membership, tenant):
    tables = auth.Base.metadata.tables
    keep = {name: false() for name in OPERATIONAL}
    keep.update({name: tables[name].c.tenant_id == tenant.id for name in TENANT_CONFIG})
    keep.update({name: true() for name in GLOBAL_PRESERVED})
    def own_tenant_or_global(t):
        return or_(t.c.tenant_id == tenant.id, t.c.tenant_id.is_(None))
    sessions = tables["auth_session"]
    owner_sessions = (sessions.c.role == auth.Role.ADMIN.value) & (sessions.c.admin_subject_id == owner.id)
    owner_sessions &= (sessions.c.subject_id == owner.id) & own_tenant_or_global(sessions)
    push = tables["push_subscription"]
    challenges = tables["admin_security_challenge"]
    audit = tables["audit_event"]
    keep.update({
        "admin_user": tables["admin_user"].c.id == owner.id,
        "tenant": tables["tenant"].c.id == tenant.id,
        "tenant_admin": tables["tenant_admin"].c.id == membership.id,
        "admin_action_token": tables["admin_action_token"].c.admin_id == owner.id,
        "admin_security_challenge": (challenges.c.admin_id == owner.id) & own_tenant_or_global(challenges),
        "installation_operator": tables["installation_operator"].c.admin_user_id == owner.id,
        "system_monitor_grant": tables["system_monitor_grant"].c.admin_user_id == owner.id,
        "auth_session": owner_sessions,
        "push_subscription": (push.c.role == auth.Role.ADMIN.value) & (push.c.admin_subject_id == owner.id)
        & (push.c.subject_id == owner.id) & own_tenant_or_global(push),
        "audit_event": admin_security_audit_criteria() & own_tenant_or_global(audit),
        "system_monitor_activity": tables["system_monitor_activity"].c.session_id.in_(
            select(sessions.c.id).where(owner_sessions)),
    })
    if set(keep) != CLASSIFIED:
        raise ResetPolicyError("Política incompleta de tabelas.")
    return keep


def preserved_rows(db, keep):
    return {name: [dict(r) for r in db.execute(select(auth.Base.metadata.tables[name]).where(predicate)).mappings()]
            for name, predicate in keep.items()}


def validate_preserved_references(db, rows):
    constraints = foreign_keys(db)
    for name, records in rows.items():
        for constraint in constraints[name]:
            target_name = constraint["referred_table"]
            target_cols = constraint["referred_columns"]
            source_cols = constraint["constrained_columns"]
            targets = {tuple(r[c] for c in target_cols) for r in rows[target_name]}
            for record in records:
                value = tuple(record[c] for c in source_cols)
                if all(v is not None for v in value) and value not in targets:
                    raise ResetPolicyError("Linha preservada referencia dado elegível para remoção.")


def digests(rows):
    # Os valores não são publicados: o digest é usado somente para comparar em memória.
    return {name: hashlib.sha256("\n".join(sorted(json.dumps(r, sort_keys=True, default=str)
                                                    for r in records)).encode()).digest()
            for name, records in rows.items()}


def deletion_order(db):
    dependencies = {}
    constraints = foreign_keys(db)
    for name in CLASSIFIED - GLOBAL_PRESERVED:
        dependencies[name] = {
            fk["referred_table"] for fk in constraints[name]
            if fk["referred_table"] in CLASSIFIED - GLOBAL_PRESERVED and fk["referred_table"] != name
            and not (name == "parent_gallery" and fk["referred_table"] == "photo_asset"
                     and "cover_photo_id" in fk["constrained_columns"])
        }
    order = []
    while dependencies:
        referenced = set().union(*dependencies.values())
        children = sorted(set(dependencies) - referenced)
        if not children:
            raise ResetPolicyError("Ciclo de exclusão sem política.")
        order.extend(children)
        for name in children:
            del dependencies[name]
        for parents in dependencies.values():
            parents.difference_update(children)
    return order


def roots():
    result = {name: Path(os.getenv(ROOT_ENV[name], str(expected))) for name, expected in MEDIA_ROOTS.items()}
    result["branding"] = Path(os.getenv("BRANDING_ASSETS_ROOT", str(BRANDING_ROOT)))
    for name, root in result.items():
        expected = BRANDING_ROOT if name == "branding" else MEDIA_ROOTS[name]
        if root.is_symlink() or root.absolute() != expected.absolute() or root.resolve() != expected.absolute():
            raise ResetPolicyError("Raiz de mídia fora do volume aprovado.")
        if not root.is_dir() and not (name == "raw_staging" and not root.exists()):
            raise ResetPolicyError("Raiz obrigatória de mídia ausente.")
    return result


def entries(root):
    """Nunca segue symlinks, inclusive diretórios apontados por links."""
    found = []
    if not root.exists():
        return found
    def walk(directory):
        for item in os.scandir(directory):
            path = Path(item.path)
            found.append(path)
            if item.is_dir(follow_symlinks=False):
                walk(path)
    walk(root)
    return sorted(found, key=lambda p: len(p.parts), reverse=True)


def branding_manifest(rows, root, tenant_id):
    prefix = f"tenants/{tenant_id}/branding/"
    keys = {r[key] for r in rows["branding_settings"] for key in ("logo_key", "app_icon_key", "favicon_key") if r[key]}
    for key in keys:
        relative = Path(key)
        if "\\" in key or relative.is_absolute() or ".." in relative.parts:
            raise ResetPolicyError("Chave de marca proprietária inválida.")
        if key.startswith("tenants/") and not key.startswith(prefix):
            raise ResetPolicyError("Marca proprietária referencia outro tenant.")
        p = root / key
        if not p.is_file() or p.is_symlink() or p.resolve() != p.absolute():
            raise ResetPolicyError("Ativo proprietário ausente ou inseguro.")
    preserved = {}
    for p in entries(root):
        key = p.relative_to(root).as_posix()
        if key in keys or key.startswith(prefix):
            if p.is_symlink():
                raise ResetPolicyError("Link inseguro no namespace proprietário de marca.")
            if p.is_file():
                preserved[key] = hashlib.sha256(p.read_bytes()).digest()
    return preserved


def clear_root(root, preserved=None):
    preserved = preserved or {}
    for p in entries(root):
        key = p.relative_to(root).as_posix()
        if key in preserved or any(k.startswith(key + "/") for k in preserved):
            continue
        if p.is_symlink() or p.is_file():
            p.unlink()
        else:
            p.rmdir()


def inventory(db, email):
    owner, membership, tenant = owner_context(db, email)
    keep = policy(db, owner, membership, tenant)
    rows = preserved_rows(db, keep)
    validate_preserved_references(db, rows)
    deletion_order(db)
    media = roots()
    branding = branding_manifest(rows, media["branding"], tenant.id)
    return {
        "eligible": True,
        "preserved": {name: len(records) for name, records in sorted(rows.items()) if name not in OPERATIONAL},
        "delete": {name: int(db.scalar(select(func.count()).select_from(auth.Base.metadata.tables[name])
                                      .where(keep[name].is_not(True))) or 0) for name in sorted(CLASSIFIED)},
        "media": {name: {"files": sum(p.is_symlink() or p.is_file() for p in entries(root)),
                          "bytes": sum(p.stat().st_size for p in entries(root) if p.is_file() and not p.is_symlink())}
                  for name, root in media.items()},
        "owner_branding_files": len(branding),
    }


def execute(db, email, confirmation, *, progress=None):
    if confirmation != CONFIRMATION:
        raise ResetPolicyError("Confirmação de reset sem backup inválida.")
    if db.bind is None or db.bind.dialect.name != "postgresql":
        raise ResetPolicyError("Reset exige PostgreSQL exclusivo de homologação.")
    owner, membership, tenant = owner_context(db, email)
    connection = db.connection()
    schema_map = connection.get_execution_options().get("schema_translate_map", {})
    preparer = connection.dialect.identifier_preparer
    for name in sorted(CLASSIFIED):
        table = auth.Base.metadata.tables[name]
        schema = schema_map.get(table.schema, table.schema)
        qualified = preparer.quote(name)
        if schema:
            qualified = preparer.quote_schema(schema) + "." + qualified
        db.execute(text(f"LOCK TABLE {qualified} IN SHARE ROW EXCLUSIVE MODE"))
    db.expire_all()
    owner, membership, tenant = owner_context(db, email)
    keep = policy(db, owner, membership, tenant)
    before = preserved_rows(db, keep)
    validate_preserved_references(db, before)
    expected = digests(before)
    media = roots()
    branding = branding_manifest(before, media["branding"], tenant.id)
    order = deletion_order(db)
    db.execute(update(auth.ParentGallery).values(cover_photo_id=None))
    for name in order:
        db.execute(delete(auth.Base.metadata.tables[name]).where(keep[name].is_not(True)))
    after = preserved_rows(db, keep)
    if digests(after) != expected:
        db.rollback()
        raise ResetPolicyError("Estado proprietário divergente antes do commit.")
    remaining = inventory(db, email)
    if any(remaining["delete"].values()):
        db.rollback()
        raise ResetPolicyError("Linhas elegíveis não foram zeradas.")
    db.commit()
    if progress:
        progress("database_committed")
    for name, root in media.items():
        clear_root(root, branding if name == "branding" else None)
    current_branding = branding_manifest(after, media["branding"], tenant.id)
    if current_branding != branding:
        raise ResetPolicyError("Ativos proprietários divergentes após limpeza.")
    if digests(preserved_rows(db, keep)) != expected:
        raise ResetPolicyError("Estado proprietário divergente após commit.")
    result = inventory(db, email)
    if any(result["delete"].values()) or any(v["files"] for k, v in result["media"].items() if k != "branding"):
        raise ResetPolicyError("Reset parcial: dados ou mídia não zerados.")
    result.update(phase="complete", owner_state_preserved=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("inventory", "execute"), required=True)
    parser.add_argument("--owner-email", required=True)
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args()
    phase = "preflight"
    def progress(value):
        nonlocal phase
        phase = value
        print(json.dumps({"phase": value}), flush=True)
    try:
        with auth.SessionLocal() as db:
            result = inventory(db, args.owner_email) if args.mode == "inventory" else execute(
                db, args.owner_email, args.confirmation, progress=progress)
        print(json.dumps(result, sort_keys=True), flush=True)
    except Exception as exc:  # noqa: BLE001 - fronteira CLI não deve expor parâmetros SQL ou segredos
        # Exceções SQL podem conter parâmetros/segredos. Só políticas próprias
        # têm mensagem publicada; o restante expõe exclusivamente a classe.
        detail = str(exc) if isinstance(exc, ResetPolicyError) else type(exc).__name__
        print(json.dumps({"phase": phase, "error": detail}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
