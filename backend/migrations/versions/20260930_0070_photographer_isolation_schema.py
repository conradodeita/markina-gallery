"""Propriedade comercial completa a partir do legado de conta única comprovada.

DDL congelado da revisão 0069, sem importar metadata mutável da aplicação.
Somente PostgreSQL operacional; nenhuma exclusão de registro/campo histórico.
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "20260930_0070"
down_revision = "20260929_0069"
branch_labels = None
depends_on = None

SHARED = {"tenant", "admin_user", "admin_action_token", "email_delivery", "email_delivery_attempt"}


def _refuse(table, reason):
    # Não incluir identificadores, valores pessoais, caminhos ou credenciais.
    raise RuntimeError(f"Legado incompatível em {table}: {reason}; migration interrompida.")


def _preflight(bind):
    if bind.dialect.name != "postgresql":
        raise RuntimeError("A transição multitenant requer PostgreSQL; nenhum dado foi alterado.")
    tables = sa.MetaData()
    tables.reflect(bind)
    expected = SHARED | {name for name, _, _ in PLAN["add_columns"]} | {
        "tenant_admin", "parent_gallery", "derived_gallery", "photo_asset",
    }
    if set(tables.tables) - {"alembic_version"} != expected:
        raise RuntimeError("Inventário de tabelas diverge da revision 0069; migration interrompida.")
    bind.execute(sa.text("LOCK TABLE " + ", ".join(f'"{name}"' for name in sorted(expected))
                         + " IN SHARE ROW EXCLUSIVE MODE"))
    owners = list(bind.scalars(sa.select(tables.tables["tenant"].c.id)))
    if len(owners) != 1:
        _refuse("tenant", "proprietário único não demonstrável")
    owner = owners[0]
    membership = tables.tables["tenant_admin"]
    for table in tables.tables.values():
        if "tenant_id" in table.c and bind.scalar(sa.select(sa.func.count()).select_from(table).where(
            sa.or_(table.c.tenant_id.is_(None), table.c.tenant_id != owner)
        )):
            _refuse(table.name, "propriedade contraditória")
        for foreign_key in table.foreign_key_constraints:
            target = foreign_key.referred_table.alias()
            elements = list(foreign_key.elements)
            all_set = sa.and_(*(item.parent.is_not(None) for item in elements))
            related = sa.and_(*(target.c[item.column.name] == item.parent for item in elements))
            missing = ~sa.exists(sa.select(1).select_from(target).where(related).correlate(table))
            if bind.scalar(sa.select(sa.func.count()).select_from(table).where(all_set, missing)):
                _refuse(table.name, "vínculo órfão")
            if foreign_key.referred_table.name == "admin_user" and len(elements) == 1 and table.name not in SHARED:
                associated = sa.exists(sa.select(1).where(
                    membership.c.admin_user_id == elements[0].parent, membership.c.tenant_id == owner
                ))
                if bind.scalar(sa.select(sa.func.count()).select_from(table).where(all_set, ~associated)):
                    _refuse(table.name, "administrador sem propriedade demonstrável")
    for name in ("gallery_lifecycle_operation", "gallery_access_capability"):
        table = tables.tables[name]
        associated = sa.exists(sa.select(1).where(
            membership.c.admin_user_id == table.c.actor_admin_id, membership.c.tenant_id == owner
        ))
        if bind.scalar(sa.select(sa.func.count()).select_from(table).where(table.c.actor_admin_id.is_not(None), ~associated)):
            _refuse(name, "ator sem propriedade demonstrável")
    challenge = tables.tables["admin_security_challenge"]
    session = tables.tables["auth_session"]
    session_exists = sa.exists(sa.select(1).where(session.c.id == challenge.c.session_id))
    if bind.scalar(sa.select(sa.func.count()).select_from(challenge).where(challenge.c.session_id.is_not(None), ~session_exists)):
        _refuse("admin_security_challenge", "sessão sensível não demonstrável")
    access = tables.tables["gallery_access"]
    parent = tables.tables["parent_gallery"]
    private = tables.tables["derived_gallery"]
    parent_exists = sa.exists(sa.select(1).where(parent.c.id == access.c.gallery_id))
    private_exists = sa.exists(sa.select(1).where(private.c.id == access.c.gallery_id))
    if bind.scalar(sa.select(sa.func.count()).select_from(access).where(
        sa.or_(sa.and_(parent_exists, private_exists), sa.and_(~parent_exists, ~private_exists))
    )):
        _refuse("gallery_access", "alvo polimórfico ausente ou ambíguo")
    for name, role_column, subject_column in (
        ("push_subscription", "role", "subject_id"),
        ("notification_delivery", "recipient_role", "recipient_id"),
    ):
        table = tables.tables[name]
        for role, target_name in (("client", "client"), ("admin", "admin_user")):
            target = tables.tables[target_name]
            missing = ~sa.exists(sa.select(1).where(target.c.id == table.c[subject_column]))
            if bind.scalar(sa.select(sa.func.count()).select_from(table).where(
                table.c[role_column] == role, missing
            )):
                _refuse(name, "sujeito tipado não demonstrável")
            if role == "admin":
                associated = sa.exists(sa.select(1).where(
                    membership.c.admin_user_id == table.c[subject_column], membership.c.tenant_id == owner
                ))
                if bind.scalar(sa.select(sa.func.count()).select_from(table).where(table.c[role_column] == role, ~associated)):
                    _refuse(name, "destinatário administrativo sem proprietário")
    phone = tables.tables["client_phone"]
    duplicates = sa.select(phone.c.phone_e164).where(phone.c.active.is_(True)).group_by(
        phone.c.phone_e164
    ).having(sa.func.count() > 1)
    if bind.execute(duplicates.limit(1)).first():
        _refuse("client_phone", "reserva ativa de telefone duplicada")
    return owner


def _backfill(bind, owner):
    for name, column, definition in PLAN["add_columns"]:
        bind.execute(sa.text(f'ALTER TABLE "{name}" ADD COLUMN {definition}'))
        if column == "tenant_id":
            bind.execute(sa.text(f'UPDATE "{name}" SET tenant_id=:owner'), {"owner": owner})
    bind.execute(sa.text(
        "UPDATE gallery_access a SET parent_gallery_id = a.gallery_id "
        "WHERE EXISTS (SELECT 1 FROM parent_gallery p WHERE p.id=a.gallery_id)"
    ))
    bind.execute(sa.text(
        "UPDATE gallery_access a SET derived_gallery_id = a.gallery_id "
        "WHERE EXISTS (SELECT 1 FROM derived_gallery g WHERE g.id=a.gallery_id)"
    ))
    for name, role_column, subject_column, client_column, admin_column in (
        ("push_subscription", "role", "subject_id", "client_subject_id", "admin_subject_id"),
        ("notification_delivery", "recipient_role", "recipient_id", "client_recipient_id", "admin_recipient_id"),
        ("auth_session", "role", "subject_id", "client_subject_id", "admin_subject_id"),
    ):
        for role, column, target in (("client", client_column, "client"), ("admin", admin_column, "admin_user")):
            membership_filter = (
                f' AND EXISTS (SELECT 1 FROM tenant_admin m WHERE m.admin_user_id=s."{subject_column}" '
                'AND m.tenant_id=s.tenant_id)' if role == "admin" else ""
            )
            bind.execute(sa.text(
                f'UPDATE "{name}" s SET "{column}"=s."{subject_column}" '
                f'WHERE s."{role_column}"=:role AND EXISTS '
                f'(SELECT 1 FROM "{target}" t WHERE t.id=s."{subject_column}")'
                + membership_filter
            ), {"role": role})
    # Sessões sem prova não são reaproveitadas; hash/UUID e revogações antigas ficam.
    bind.execute(sa.text(
        "UPDATE auth_session SET revoked_at=COALESCE(revoked_at,:instant), tenant_id=NULL "
        "WHERE client_subject_id IS NULL AND admin_subject_id IS NULL"
    ), {"instant": datetime.now(UTC)})


def _apply_schema(bind):
    for name, constraint in PLAN["drop_constraints"]:
        bind.execute(sa.text(f'ALTER TABLE "{name}" DROP CONSTRAINT "{constraint}"'))
    for index in PLAN["drop_indexes"]:
        bind.execute(sa.text(f'DROP INDEX "{index}"'))
    for name, old_name, columns in PLAN["primary_keys"]:
        bind.execute(sa.text(f'ALTER TABLE "{name}" DROP CONSTRAINT "{old_name}"'))
        keys = ", ".join(f'"{column}"' for column in columns)
        bind.execute(sa.text(f'ALTER TABLE "{name}" ADD PRIMARY KEY ({keys})'))
    for section in ("unique_constraints", "checks", "foreign_keys", "indexes"):
        for statement in PLAN[section]:
            bind.execute(sa.text(statement))
    for name, column in PLAN["required"]:
        bind.execute(sa.text(f'ALTER TABLE "{name}" ALTER COLUMN "{column}" SET NOT NULL'))


def upgrade():
    bind = op.get_bind()
    owner = _preflight(bind)
    _backfill(bind, owner)
    _apply_schema(bind)


def downgrade():
    raise RuntimeError("Preserve o schema e a propriedade; reversão requer aplicação compatível.")


# SQL PostgreSQL congelado, gerado comparando catálogo 0069 e metadata da task 2.2.
# A revision não executa import/geração de modelos durante o upgrade.
PLAN = {
    "add_columns": [
        [
            "admin_security_challenge",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "asset_file_cleanup",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "audit_event",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "auth_challenge",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "auth_session",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "auth_session",
            "client_subject_id",
            "client_subject_id UUID"
        ],
        [
            "auth_session",
            "admin_subject_id",
            "admin_subject_id UUID"
        ],
        [
            "branding_settings",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "client",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "client_deletion_receipt",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "client_phone",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "commercial_history_media",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "derived_gallery_membership",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "derived_gallery_photo",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "derived_gallery_photo_origin",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "facial_calibration_approval",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "facial_job",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "facial_legal_representation",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "facial_rollout",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "facial_rollout_operation",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "facial_search_candidate",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "facial_search_notification_outbox",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "facial_search_request",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "facial_search_snapshot_item",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "folder_client_grant",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "folder_processing_settings",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "gallery_access",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "gallery_access",
            "parent_gallery_id",
            "parent_gallery_id UUID"
        ],
        [
            "gallery_access",
            "derived_gallery_id",
            "derived_gallery_id UUID"
        ],
        [
            "gallery_access_capability",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "gallery_client_state",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "gallery_facial_policy",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "gallery_lifecycle_operation",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "gallery_membership_notification_outbox",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "gallery_preview_settings",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "gallery_reopening_notification_outbox",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "gallery_reopening_request",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "global_pix_settings",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "media_derivative",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "media_job",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "notification_delivery",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "notification_delivery",
            "client_recipient_id",
            "client_recipient_id UUID"
        ],
        [
            "notification_delivery",
            "admin_recipient_id",
            "admin_recipient_id UUID"
        ],
        [
            "notification_event",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "notification_milestone",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "notification_setting",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "parent_gallery_registration",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "payment_communication",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "payment_confirmation_correction",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "payment_group",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "payment_message_template",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "payment_notification_outbox",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "photo_analysis",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "photo_comment",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "photo_face_embedding",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "photo_favorite",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "photo_folder",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "photo_selection",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "photo_view",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "pix_checkout_settings",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "preview_adjustment",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "preview_adjustment_settings",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "price_rule",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "private_upload_batch",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "private_upload_batch_asset",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "progressive_pricing_preset",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "progressive_pricing_tier",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "push_subscription",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "push_subscription",
            "client_subject_id",
            "client_subject_id UUID"
        ],
        [
            "push_subscription",
            "admin_subject_id",
            "admin_subject_id UUID"
        ],
        [
            "removed_photo_movement",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "sale_order",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "sale_order_item",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "whatsapp_channel_settings",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "whatsapp_delivery",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "whatsapp_delivery_attempt",
            "tenant_id",
            "tenant_id UUID"
        ],
        [
            "whatsapp_webhook_receipt",
            "tenant_id",
            "tenant_id UUID"
        ]
    ],
    "drop_constraints": [
        [
            "notification_event",
            "notification_event_event_type_fkey"
        ],
        [
            "admin_action_token",
            "admin_action_token_token_hash_key"
        ],
        [
            "admin_user",
            "admin_user_email_key"
        ],
        [
            "auth_session",
            "auth_session_token_hash_key"
        ],
        [
            "client",
            "client_phone_e164_key"
        ],
        [
            "client_deletion_receipt",
            "uq_client_deletion_receipt_idempotency"
        ],
        [
            "commercial_history_media",
            "uq_commercial_history_media_item"
        ],
        [
            "derived_gallery_membership",
            "uq_membership_parent_client"
        ],
        [
            "derived_gallery_photo",
            "uq_derived_gallery_photo_asset"
        ],
        [
            "derived_gallery_photo_origin",
            "uq_derived_gallery_photo_origin_reason"
        ],
        [
            "facial_job",
            "uq_facial_job_idempotency"
        ],
        [
            "facial_rollout",
            "uq_facial_rollout_environment_gallery"
        ],
        [
            "facial_search_candidate",
            "uq_facial_candidate_photo"
        ],
        [
            "facial_search_notification_outbox",
            "uq_facial_notification_idempotency"
        ],
        [
            "facial_search_snapshot_item",
            "uq_facial_snapshot_photo"
        ],
        [
            "folder_client_grant",
            "uq_folder_client_grant_pair"
        ],
        [
            "gallery_facial_policy",
            "uq_gallery_facial_policy_parent"
        ],
        [
            "gallery_lifecycle_operation",
            "uq_gallery_lifecycle_operation_idempotency"
        ],
        [
            "gallery_membership_notification_outbox",
            "gallery_membership_notification_outbox_event_key_key"
        ],
        [
            "gallery_reopening_notification_outbox",
            "gallery_reopening_notification_gallery_reopening_request_id_key"
        ],
        [
            "gallery_reopening_request",
            "uq_gallery_reopening_canonical_idempotency"
        ],
        [
            "gallery_reopening_request",
            "uq_gallery_reopening_request_idempotency"
        ],
        [
            "global_pix_settings",
            "global_pix_settings_admin_user_id_key"
        ],
        [
            "global_pix_settings",
            "global_pix_settings_singleton_key"
        ],
        [
            "media_derivative",
            "media_derivative_photo_asset_id_variant_key"
        ],
        [
            "media_job",
            "media_job_photo_asset_id_kind_key"
        ],
        [
            "notification_delivery",
            "notification_delivery_event_id_channel_recipient_role_recip_key"
        ],
        [
            "notification_event",
            "notification_event_event_key_key"
        ],
        [
            "parent_gallery_registration",
            "uq_parent_gallery_registration"
        ],
        [
            "payment_communication",
            "payment_communication_sale_order_id_idempotency_key_key"
        ],
        [
            "payment_communication",
            "uq_payment_communication_group"
        ],
        [
            "payment_confirmation_correction",
            "uq_payment_confirmation_correction_idempotency"
        ],
        [
            "payment_message_template",
            "payment_message_template_kind_key"
        ],
        [
            "payment_notification_outbox",
            "payment_notification_outbox_idempotency_key_key"
        ],
        [
            "photo_face_embedding",
            "uq_face_embedding_versioned_photo_face"
        ],
        [
            "photo_favorite",
            "photo_favorite_derived_gallery_id_photo_asset_id_client_id_key"
        ],
        [
            "photo_selection",
            "photo_selection_derived_gallery_id_photo_asset_id_client_id_key"
        ],
        [
            "photo_view",
            "uq_photo_view_private"
        ],
        [
            "pix_checkout_settings",
            "pix_checkout_settings_parent_new_parent_gallery_id_key"
        ],
        [
            "price_rule",
            "price_rule_parent_new_parent_gallery_id_minimum_quantity_key"
        ],
        [
            "private_upload_batch_asset",
            "private_upload_batch_asset_photo_asset_id_key"
        ],
        [
            "progressive_pricing_preset",
            "uq_progressive_pricing_preset_code"
        ],
        [
            "progressive_pricing_tier",
            "uq_progressive_pricing_tier_minimum"
        ],
        [
            "push_subscription",
            "push_subscription_endpoint_fingerprint_key"
        ],
        [
            "push_subscription",
            "push_subscription_installation_fingerprint_key"
        ],
        [
            "removed_photo_movement",
            "uq_removed_photo_movement_source"
        ],
        [
            "sale_order",
            "uq_sale_order_canonical_checkout_key"
        ],
        [
            "sale_order",
            "uq_sale_order_gallery_client_checkout_key"
        ],
        [
            "sale_order_item",
            "sale_order_item_sale_order_id_photo_asset_id_key"
        ],
        [
            "whatsapp_channel_settings",
            "whatsapp_channel_settings_environment_key"
        ],
        [
            "whatsapp_delivery",
            "whatsapp_delivery_external_message_id_key"
        ],
        [
            "whatsapp_delivery",
            "whatsapp_delivery_idempotency_key_key"
        ],
        [
            "whatsapp_webhook_receipt",
            "whatsapp_webhook_receipt_fingerprint_key"
        ]
    ],
    "drop_indexes": [
        "ix_admin_action_token_token_hash",
        "ix_admin_user_email",
        "ix_auth_session_token_hash",
        "uq_client_phone_active_verified",
        "uq_client_phone_one_active_per_client",
        "ix_derived_gallery_parent_client",
        "uq_gallery_access_capability_active_invite",
        "uq_gallery_access_capability_active_private_link",
        "uq_gallery_access_capability_active_public",
        "uq_gallery_reopening_canonical_pending",
        "uq_gallery_reopening_request_pending",
        "uq_payment_group_draft",
        "uq_photo_favorite_canonical",
        "uq_photo_folder_cover_assets_parent",
        "uq_photo_folder_private_position",
        "uq_photo_folder_public_position",
        "uq_photo_selection_canonical",
        "uq_photo_view_canonical",
        "ix_pix_checkout_settings_parent_gallery_id",
        "uq_sale_order_canonical_editable_draft",
        "uq_sale_order_editable_draft"
    ],
    "primary_keys": [
        [
            "notification_setting",
            "notification_setting_pkey",
            [
                "tenant_id",
                "event_type"
            ]
        ],
        [
            "preview_adjustment_settings",
            "preview_adjustment_settings_pkey",
            [
                "tenant_id",
                "id"
            ]
        ]
    ],
    "unique_constraints": [
        "ALTER TABLE admin_security_challenge ADD CONSTRAINT uq_owner_admin_security_challenge_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE asset_file_cleanup ADD CONSTRAINT uq_owner_asset_file_cleanup_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE audit_event ADD CONSTRAINT uq_owner_audit_event_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE auth_challenge ADD CONSTRAINT uq_owner_auth_challenge_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE auth_session ADD CONSTRAINT uq_owner_auth_session_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE branding_settings ADD CONSTRAINT uq_owner_branding_settings_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE branding_settings ADD CONSTRAINT uq_owner_branding_settings_tenant_id UNIQUE (tenant_id)",
        "ALTER TABLE client ADD CONSTRAINT uq_client_id_tenant UNIQUE (id, tenant_id)",
        "ALTER TABLE client ADD CONSTRAINT uq_client_tenant_phone UNIQUE (tenant_id, phone_e164)",
        "ALTER TABLE client_deletion_receipt ADD CONSTRAINT uq_client_deletion_receipt_idempotency UNIQUE (tenant_id, idempotency_key)",
        "ALTER TABLE client_deletion_receipt ADD CONSTRAINT uq_owner_client_deletion_receipt_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE client_phone ADD CONSTRAINT uq_owner_client_phone_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE commercial_history_media ADD CONSTRAINT uq_commercial_history_media_item UNIQUE (tenant_id, sale_order_item_id)",
        "ALTER TABLE commercial_history_media ADD CONSTRAINT uq_owner_commercial_history_media_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE derived_gallery ADD CONSTRAINT uq_owner_derived_gallery_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE derived_gallery_membership ADD CONSTRAINT uq_membership_parent_client UNIQUE (tenant_id, parent_gallery_id, client_id)",
        "ALTER TABLE derived_gallery_membership ADD CONSTRAINT uq_owner_derived_gallery_membership_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE derived_gallery_photo ADD CONSTRAINT uq_derived_gallery_photo_asset UNIQUE (tenant_id, derived_gallery_id, photo_asset_id)",
        "ALTER TABLE derived_gallery_photo ADD CONSTRAINT uq_owner_derived_gallery_photo_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE derived_gallery_photo_origin ADD CONSTRAINT uq_derived_gallery_photo_origin_reason UNIQUE (tenant_id, derived_gallery_photo_id, origin)",
        "ALTER TABLE derived_gallery_photo_origin ADD CONSTRAINT uq_owner_derived_gallery_photo_origin_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE facial_calibration_approval ADD CONSTRAINT uq_owner_facial_calibration_approval_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE facial_job ADD CONSTRAINT uq_facial_job_idempotency UNIQUE (tenant_id, idempotency_key)",
        "ALTER TABLE facial_job ADD CONSTRAINT uq_owner_facial_job_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE facial_job ADD CONSTRAINT uq_scope_facial_job_idempotency_key UNIQUE (tenant_id, idempotency_key)",
        "ALTER TABLE facial_legal_representation ADD CONSTRAINT uq_owner_facial_legal_representation_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE facial_rollout ADD CONSTRAINT uq_facial_rollout_environment_gallery UNIQUE (tenant_id, environment, parent_gallery_id)",
        "ALTER TABLE facial_rollout ADD CONSTRAINT uq_owner_facial_rollout_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE facial_rollout_operation ADD CONSTRAINT uq_owner_facial_rollout_operation_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE facial_search_candidate ADD CONSTRAINT uq_facial_candidate_photo UNIQUE (tenant_id, search_request_id, photo_asset_id)",
        "ALTER TABLE facial_search_candidate ADD CONSTRAINT uq_owner_facial_search_candidate_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE facial_search_notification_outbox ADD CONSTRAINT uq_facial_notification_idempotency UNIQUE (tenant_id, idempotency_key)",
        "ALTER TABLE facial_search_notification_outbox ADD CONSTRAINT uq_owner_facial_search_notification_outbox_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE facial_search_notification_outbox ADD CONSTRAINT uq_scope_facial_search_notification_outbox_idempotency_key UNIQUE (tenant_id, idempotency_key)",
        "ALTER TABLE facial_search_request ADD CONSTRAINT uq_owner_facial_search_request_id_parent_gallery_id_cl_24d385e8 UNIQUE (id, parent_gallery_id, client_id, tenant_id)",
        "ALTER TABLE facial_search_request ADD CONSTRAINT uq_owner_facial_search_request_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE facial_search_snapshot_item ADD CONSTRAINT uq_facial_snapshot_photo UNIQUE (tenant_id, search_request_id, photo_asset_id)",
        "ALTER TABLE facial_search_snapshot_item ADD CONSTRAINT uq_owner_facial_search_snapshot_item_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE folder_client_grant ADD CONSTRAINT uq_folder_client_grant_pair UNIQUE (tenant_id, folder_id, client_id)",
        "ALTER TABLE folder_client_grant ADD CONSTRAINT uq_owner_folder_client_grant_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE gallery_access ADD CONSTRAINT uq_owner_gallery_access_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE gallery_access ADD CONSTRAINT uq_scope_gallery_access_client_id_gallery_id UNIQUE (tenant_id, client_id, gallery_id)",
        "ALTER TABLE gallery_access_capability ADD CONSTRAINT uq_owner_gallery_access_capability_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE gallery_client_state ADD CONSTRAINT uq_owner_gallery_client_state_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE gallery_client_state ADD CONSTRAINT uq_owner_gallery_client_state_parent_gallery_id_client_f9288bb2 UNIQUE (parent_gallery_id, client_id, tenant_id)",
        "ALTER TABLE gallery_facial_policy ADD CONSTRAINT uq_gallery_facial_policy_parent UNIQUE (tenant_id, parent_gallery_id)",
        "ALTER TABLE gallery_facial_policy ADD CONSTRAINT uq_owner_gallery_facial_policy_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE gallery_lifecycle_operation ADD CONSTRAINT uq_gallery_lifecycle_operation_idempotency UNIQUE (tenant_id, idempotency_key)",
        "ALTER TABLE gallery_lifecycle_operation ADD CONSTRAINT uq_owner_gallery_lifecycle_operation_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE gallery_membership_notification_outbox ADD CONSTRAINT uq_owner_gallery_membership_notification_outbox_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE gallery_membership_notification_outbox ADD CONSTRAINT uq_scope_gallery_membership_notification_outbox_event_key UNIQUE (tenant_id, event_key)",
        "ALTER TABLE gallery_reopening_notification_outbox ADD CONSTRAINT uq_owner_gallery_reopening_notification_outbox_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE gallery_reopening_notification_outbox ADD CONSTRAINT uq_scope_gallery_reopening_notification_outbox_gallery_462c157e UNIQUE (tenant_id, gallery_reopening_request_id)",
        "ALTER TABLE gallery_reopening_request ADD CONSTRAINT uq_gallery_reopening_canonical_idempotency UNIQUE (tenant_id, parent_gallery_id, requested_by_client_id, idempotency_key)",
        "ALTER TABLE gallery_reopening_request ADD CONSTRAINT uq_gallery_reopening_request_idempotency UNIQUE (tenant_id, derived_gallery_id, idempotency_key)",
        "ALTER TABLE gallery_reopening_request ADD CONSTRAINT uq_owner_gallery_reopening_request_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE global_pix_settings ADD CONSTRAINT uq_owner_global_pix_settings_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE global_pix_settings ADD CONSTRAINT uq_owner_global_pix_settings_tenant_id UNIQUE (tenant_id)",
        "ALTER TABLE global_pix_settings ADD CONSTRAINT uq_scope_global_pix_settings_admin_user_id UNIQUE (tenant_id, admin_user_id)",
        "ALTER TABLE global_pix_settings ADD CONSTRAINT uq_scope_global_pix_settings_singleton UNIQUE (tenant_id, singleton)",
        "ALTER TABLE media_derivative ADD CONSTRAINT uq_owner_media_derivative_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE media_derivative ADD CONSTRAINT uq_scope_media_derivative_photo_asset_id_variant UNIQUE (tenant_id, photo_asset_id, variant)",
        "ALTER TABLE media_job ADD CONSTRAINT uq_owner_media_job_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE media_job ADD CONSTRAINT uq_scope_media_job_photo_asset_id_kind UNIQUE (tenant_id, photo_asset_id, kind)",
        "ALTER TABLE notification_delivery ADD CONSTRAINT uq_owner_notification_delivery_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE notification_delivery ADD CONSTRAINT uq_scope_notification_delivery_event_id_channel_recipi_5760950e UNIQUE (tenant_id, event_id, channel, recipient_role, recipient_id, device_key)",
        "ALTER TABLE notification_event ADD CONSTRAINT uq_owner_notification_event_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE notification_event ADD CONSTRAINT uq_scope_notification_event_event_key UNIQUE (tenant_id, event_key)",
        "ALTER TABLE notification_setting ADD CONSTRAINT uq_owner_notification_setting_event_type_tenant_id UNIQUE (event_type, tenant_id)",
        "ALTER TABLE parent_gallery_registration ADD CONSTRAINT uq_owner_parent_gallery_registration_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE parent_gallery_registration ADD CONSTRAINT uq_scope_parent_gallery_registration_parent_gallery_id_9a39aef8 UNIQUE (tenant_id, parent_gallery_id, client_id)",
        "ALTER TABLE payment_communication ADD CONSTRAINT uq_owner_payment_communication_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE payment_communication ADD CONSTRAINT uq_scope_payment_communication_payment_group_id UNIQUE (tenant_id, payment_group_id)",
        "ALTER TABLE payment_communication ADD CONSTRAINT uq_scope_payment_communication_sale_order_id_idempotency_key UNIQUE (tenant_id, sale_order_id, idempotency_key)",
        "ALTER TABLE payment_confirmation_correction ADD CONSTRAINT uq_owner_payment_confirmation_correction_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE payment_confirmation_correction ADD CONSTRAINT uq_payment_confirmation_correction_idempotency UNIQUE (tenant_id, payment_communication_id, idempotency_key)",
        "ALTER TABLE payment_group ADD CONSTRAINT uq_owner_payment_group_id_client_id_tenant_id UNIQUE (id, client_id, tenant_id)",
        "ALTER TABLE payment_group ADD CONSTRAINT uq_owner_payment_group_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE payment_message_template ADD CONSTRAINT uq_owner_payment_message_template_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE payment_message_template ADD CONSTRAINT uq_scope_payment_message_template_kind UNIQUE (tenant_id, kind)",
        "ALTER TABLE payment_notification_outbox ADD CONSTRAINT uq_owner_payment_notification_outbox_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE payment_notification_outbox ADD CONSTRAINT uq_scope_payment_notification_outbox_idempotency_key UNIQUE (tenant_id, idempotency_key)",
        "ALTER TABLE photo_asset ADD CONSTRAINT uq_owner_photo_asset_id_parent_gallery_id_tenant_id UNIQUE (id, parent_gallery_id, tenant_id)",
        "ALTER TABLE photo_asset ADD CONSTRAINT uq_owner_photo_asset_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE photo_comment ADD CONSTRAINT uq_owner_photo_comment_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE photo_face_embedding ADD CONSTRAINT uq_face_embedding_versioned_photo_face UNIQUE (tenant_id, photo_asset_id, face_ordinal, model_version, quality_version, preview_fingerprint)",
        "ALTER TABLE photo_face_embedding ADD CONSTRAINT uq_owner_photo_face_embedding_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE photo_favorite ADD CONSTRAINT uq_owner_photo_favorite_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE photo_favorite ADD CONSTRAINT uq_scope_photo_favorite_derived_gallery_id_photo_asset_b93c68dc UNIQUE (tenant_id, derived_gallery_id, photo_asset_id, client_id)",
        "ALTER TABLE photo_folder ADD CONSTRAINT uq_owner_photo_folder_id_parent_gallery_id_derived_gal_4577d1c4 UNIQUE (id, parent_gallery_id, derived_gallery_id, tenant_id)",
        "ALTER TABLE photo_folder ADD CONSTRAINT uq_owner_photo_folder_id_parent_gallery_id_tenant_id UNIQUE (id, parent_gallery_id, tenant_id)",
        "ALTER TABLE photo_folder ADD CONSTRAINT uq_owner_photo_folder_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE photo_selection ADD CONSTRAINT uq_owner_photo_selection_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE photo_selection ADD CONSTRAINT uq_scope_photo_selection_derived_gallery_id_photo_asse_6d9ff670 UNIQUE (tenant_id, derived_gallery_id, photo_asset_id, client_id)",
        "ALTER TABLE photo_view ADD CONSTRAINT uq_owner_photo_view_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE photo_view ADD CONSTRAINT uq_scope_photo_view_derived_gallery_id_client_id_photo_asset_id UNIQUE (tenant_id, derived_gallery_id, client_id, photo_asset_id)",
        "ALTER TABLE pix_checkout_settings ADD CONSTRAINT uq_owner_pix_checkout_settings_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE preview_adjustment_settings ADD CONSTRAINT uq_owner_preview_adjustment_settings_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE price_rule ADD CONSTRAINT uq_owner_price_rule_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE price_rule ADD CONSTRAINT uq_scope_price_rule_parent_gallery_id_minimum_quantity UNIQUE (tenant_id, parent_gallery_id, minimum_quantity)",
        "ALTER TABLE private_upload_batch ADD CONSTRAINT uq_owner_private_upload_batch_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE private_upload_batch_asset ADD CONSTRAINT uq_scope_private_upload_batch_asset_photo_asset_id UNIQUE (tenant_id, photo_asset_id)",
        "ALTER TABLE progressive_pricing_preset ADD CONSTRAINT uq_owner_progressive_pricing_preset_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE progressive_pricing_preset ADD CONSTRAINT uq_progressive_pricing_preset_code UNIQUE (tenant_id, code)",
        "ALTER TABLE progressive_pricing_tier ADD CONSTRAINT uq_owner_progressive_pricing_tier_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE progressive_pricing_tier ADD CONSTRAINT uq_progressive_pricing_tier_minimum UNIQUE (tenant_id, preset_id, minimum_quantity)",
        "ALTER TABLE push_subscription ADD CONSTRAINT uq_owner_push_subscription_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE push_subscription ADD CONSTRAINT uq_scope_push_subscription_endpoint_fingerprint UNIQUE (tenant_id, endpoint_fingerprint)",
        "ALTER TABLE push_subscription ADD CONSTRAINT uq_scope_push_subscription_installation_fingerprint UNIQUE (tenant_id, installation_fingerprint)",
        "ALTER TABLE removed_photo_movement ADD CONSTRAINT uq_owner_removed_photo_movement_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE removed_photo_movement ADD CONSTRAINT uq_removed_photo_movement_source UNIQUE (tenant_id, kind, source_id)",
        "ALTER TABLE sale_order ADD CONSTRAINT uq_owner_sale_order_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE sale_order ADD CONSTRAINT uq_sale_order_canonical_checkout_key UNIQUE (tenant_id, parent_gallery_id, client_id, checkout_key)",
        "ALTER TABLE sale_order ADD CONSTRAINT uq_scope_sale_order_derived_gallery_id_client_id_checkout_key UNIQUE (tenant_id, derived_gallery_id, client_id, checkout_key)",
        "ALTER TABLE sale_order_item ADD CONSTRAINT uq_owner_sale_order_item_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE sale_order_item ADD CONSTRAINT uq_scope_sale_order_item_sale_order_id_photo_asset_id UNIQUE (tenant_id, sale_order_id, photo_asset_id)",
        "ALTER TABLE tenant_admin ADD CONSTRAINT uq_owner_tenant_admin_admin_user_id_tenant_id UNIQUE (admin_user_id, tenant_id)",
        "ALTER TABLE tenant_admin ADD CONSTRAINT uq_owner_tenant_admin_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE whatsapp_channel_settings ADD CONSTRAINT uq_owner_whatsapp_channel_settings_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE whatsapp_channel_settings ADD CONSTRAINT uq_scope_whatsapp_channel_settings_environment UNIQUE (tenant_id, environment)",
        "ALTER TABLE whatsapp_delivery ADD CONSTRAINT uq_owner_whatsapp_delivery_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE whatsapp_delivery ADD CONSTRAINT uq_scope_whatsapp_delivery_external_message_id UNIQUE (tenant_id, external_message_id)",
        "ALTER TABLE whatsapp_delivery ADD CONSTRAINT uq_scope_whatsapp_delivery_idempotency_key UNIQUE (tenant_id, idempotency_key)",
        "ALTER TABLE whatsapp_delivery_attempt ADD CONSTRAINT uq_owner_whatsapp_delivery_attempt_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE whatsapp_webhook_receipt ADD CONSTRAINT uq_owner_whatsapp_webhook_receipt_id_tenant_id UNIQUE (id, tenant_id)",
        "ALTER TABLE whatsapp_webhook_receipt ADD CONSTRAINT uq_scope_whatsapp_webhook_receipt_fingerprint UNIQUE (tenant_id, fingerprint)"
    ],
    "checks": [
        "ALTER TABLE admin_security_challenge ADD CONSTRAINT ck_admin_challenge_pix_context CHECK (purpose != 'change_pix_otp' OR tenant_id IS NOT NULL)",
        "ALTER TABLE auth_challenge ADD CONSTRAINT ck_auth_challenge_client_context CHECK (kind != 'client_otp' OR tenant_id IS NOT NULL)",
        "ALTER TABLE auth_session ADD CONSTRAINT ck_auth_session_role CHECK (role IN ('admin', 'client'))",
        "ALTER TABLE auth_session ADD CONSTRAINT ck_auth_session_typed_context CHECK (revoked_at IS NOT NULL OR (tenant_id IS NOT NULL AND ((role = 'client' AND client_subject_id IS NOT NULL AND client_subject_id = subject_id AND admin_subject_id IS NULL) OR (role = 'admin' AND admin_subject_id IS NOT NULL AND admin_subject_id = subject_id AND client_subject_id IS NULL))))",
        "ALTER TABLE gallery_access ADD CONSTRAINT ck_gallery_access_typed_target CHECK ((parent_gallery_id IS NOT NULL AND derived_gallery_id IS NULL AND gallery_id = parent_gallery_id) OR (derived_gallery_id IS NOT NULL AND parent_gallery_id IS NULL AND gallery_id = derived_gallery_id))",
        "ALTER TABLE notification_delivery ADD CONSTRAINT ck_notification_delivery_typed_recipient CHECK ((recipient_role = 'client' AND client_recipient_id IS NOT NULL AND client_recipient_id = recipient_id AND admin_recipient_id IS NULL) OR (recipient_role = 'admin' AND admin_recipient_id IS NOT NULL AND admin_recipient_id = recipient_id AND client_recipient_id IS NULL))",
        "ALTER TABLE push_subscription ADD CONSTRAINT ck_push_subscription_typed_subject CHECK ((role = 'client' AND client_subject_id IS NOT NULL AND client_subject_id = subject_id AND admin_subject_id IS NULL) OR (role = 'admin' AND admin_subject_id IS NOT NULL AND admin_subject_id = subject_id AND client_subject_id IS NULL))"
    ],
    "foreign_keys": [
        "ALTER TABLE admin_security_challenge ADD CONSTRAINT fk_scope_admin_security_challenge_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE admin_security_challenge ADD CONSTRAINT fk_owner_admin_security_challenge_admin_id_tenant_id_t_a047f739 FOREIGN KEY(admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE admin_security_challenge ADD CONSTRAINT fk_owner_admin_security_challenge_session_id_tenant_id_91cdcc20 FOREIGN KEY(session_id, tenant_id) REFERENCES auth_session (id, tenant_id)",
        "ALTER TABLE asset_file_cleanup ADD CONSTRAINT fk_scope_asset_file_cleanup_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE audit_event ADD CONSTRAINT fk_scope_audit_event_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE auth_challenge ADD CONSTRAINT fk_scope_auth_challenge_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE auth_session ADD CONSTRAINT fk_scope_auth_session_admin_subject_id_admin_user FOREIGN KEY(admin_subject_id) REFERENCES admin_user (id)",
        "ALTER TABLE auth_session ADD CONSTRAINT fk_scope_auth_session_client_subject_id_client FOREIGN KEY(client_subject_id) REFERENCES client (id)",
        "ALTER TABLE auth_session ADD CONSTRAINT fk_scope_auth_session_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE auth_session ADD CONSTRAINT fk_owner_auth_session_admin_subject_id_tenant_id_tenant_admin FOREIGN KEY(admin_subject_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE auth_session ADD CONSTRAINT fk_owner_auth_session_client_subject_id_tenant_id_client FOREIGN KEY(client_subject_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE branding_settings ADD CONSTRAINT fk_scope_branding_settings_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE client ADD CONSTRAINT fk_scope_client_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE client_deletion_receipt ADD CONSTRAINT fk_scope_client_deletion_receipt_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE client_deletion_receipt ADD CONSTRAINT fk_owner_client_deletion_receipt_actor_admin_id_tenant_4602bb8e FOREIGN KEY(actor_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE client_phone ADD CONSTRAINT fk_scope_client_phone_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE client_phone ADD CONSTRAINT fk_client_phone_client_tenant FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE commercial_history_media ADD CONSTRAINT fk_scope_commercial_history_media_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE commercial_history_media ADD CONSTRAINT fk_owner_commercial_history_media_sale_order_item_id_t_8be9208c FOREIGN KEY(sale_order_item_id, tenant_id) REFERENCES sale_order_item (id, tenant_id)",
        "ALTER TABLE derived_gallery ADD CONSTRAINT fk_owner_derived_gallery_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE derived_gallery_membership ADD CONSTRAINT fk_scope_derived_gallery_membership_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE derived_gallery_membership ADD CONSTRAINT fk_owner_derived_gallery_membership_actor_admin_id_ten_56c09a8c FOREIGN KEY(actor_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE derived_gallery_membership ADD CONSTRAINT fk_owner_derived_gallery_membership_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE derived_gallery_membership ADD CONSTRAINT fk_owner_derived_gallery_membership_derived_gallery_id_b150659b FOREIGN KEY(derived_gallery_id, parent_gallery_id, tenant_id) REFERENCES derived_gallery (id, parent_gallery_id, tenant_id)",
        "ALTER TABLE derived_gallery_membership ADD CONSTRAINT fk_owner_derived_gallery_membership_parent_gallery_id__0e7535f6 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE derived_gallery_photo ADD CONSTRAINT fk_scope_derived_gallery_photo_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE derived_gallery_photo ADD CONSTRAINT fk_owner_derived_gallery_photo_derived_gallery_id_tena_88f98a1e FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE derived_gallery_photo ADD CONSTRAINT fk_owner_derived_gallery_photo_photo_asset_id_tenant_i_ac93cc0d FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE derived_gallery_photo_origin ADD CONSTRAINT fk_scope_derived_gallery_photo_origin_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE derived_gallery_photo_origin ADD CONSTRAINT fk_owner_derived_gallery_photo_origin_derived_gallery__0903e784 FOREIGN KEY(derived_gallery_photo_id, tenant_id) REFERENCES derived_gallery_photo (id, tenant_id)",
        "ALTER TABLE facial_calibration_approval ADD CONSTRAINT fk_scope_facial_calibration_approval_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE facial_calibration_approval ADD CONSTRAINT fk_owner_facial_calibration_approval_approved_by_admin_90219343 FOREIGN KEY(approved_by_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE facial_job ADD CONSTRAINT fk_scope_facial_job_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE facial_job ADD CONSTRAINT fk_owner_facial_job_derived_gallery_id_tenant_id_deriv_997f3b4c FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE facial_job ADD CONSTRAINT fk_owner_facial_job_parent_gallery_id_tenant_id_parent_gallery FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE facial_job ADD CONSTRAINT fk_owner_facial_job_photo_asset_id_tenant_id_photo_asset FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE facial_job ADD CONSTRAINT fk_owner_facial_job_search_request_id_tenant_id_facial_e75be47f FOREIGN KEY(search_request_id, tenant_id) REFERENCES facial_search_request (id, tenant_id)",
        "ALTER TABLE facial_legal_representation ADD CONSTRAINT fk_scope_facial_legal_representation_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE facial_legal_representation ADD CONSTRAINT fk_owner_facial_legal_representation_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE facial_legal_representation ADD CONSTRAINT fk_owner_facial_legal_representation_parent_gallery_id_2ef3a48d FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE facial_legal_representation ADD CONSTRAINT fk_owner_facial_legal_representation_verified_by_admin_a8e9298f FOREIGN KEY(verified_by_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE facial_rollout ADD CONSTRAINT fk_scope_facial_rollout_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE facial_rollout ADD CONSTRAINT fk_owner_facial_rollout_approved_by_admin_id_tenant_id_ca1c725e FOREIGN KEY(approved_by_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE facial_rollout ADD CONSTRAINT fk_owner_facial_rollout_parent_gallery_id_tenant_id_pa_47264477 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE facial_rollout_operation ADD CONSTRAINT fk_scope_facial_rollout_operation_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE facial_rollout_operation ADD CONSTRAINT fk_owner_facial_rollout_operation_approved_by_admin_id_4d8726fc FOREIGN KEY(approved_by_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE facial_search_candidate ADD CONSTRAINT fk_scope_facial_search_candidate_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE facial_search_candidate ADD CONSTRAINT fk_owner_facial_search_candidate_photo_asset_id_parent_ac30636d FOREIGN KEY(photo_asset_id, parent_gallery_id, tenant_id) REFERENCES photo_asset (id, parent_gallery_id, tenant_id)",
        "ALTER TABLE facial_search_candidate ADD CONSTRAINT fk_owner_facial_search_candidate_search_request_id_par_f0bc6646 FOREIGN KEY(search_request_id, parent_gallery_id, client_id, tenant_id) REFERENCES facial_search_request (id, parent_gallery_id, client_id, tenant_id)",
        "ALTER TABLE facial_search_notification_outbox ADD CONSTRAINT fk_scope_facial_search_notification_outbox_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE facial_search_notification_outbox ADD CONSTRAINT fk_owner_facial_search_notification_outbox_search_requ_6198207f FOREIGN KEY(search_request_id, parent_gallery_id, client_id, tenant_id) REFERENCES facial_search_request (id, parent_gallery_id, client_id, tenant_id)",
        "ALTER TABLE facial_search_request ADD CONSTRAINT fk_scope_facial_search_request_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE facial_search_request ADD CONSTRAINT fk_owner_facial_search_request_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE facial_search_request ADD CONSTRAINT fk_owner_facial_search_request_parent_gallery_id_tenan_9edc5186 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE facial_search_request ADD CONSTRAINT fk_owner_facial_search_request_policy_id_tenant_id_gal_285a5851 FOREIGN KEY(policy_id, tenant_id) REFERENCES gallery_facial_policy (id, tenant_id)",
        "ALTER TABLE facial_search_snapshot_item ADD CONSTRAINT fk_scope_facial_search_snapshot_item_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE facial_search_snapshot_item ADD CONSTRAINT fk_owner_facial_search_snapshot_item_photo_asset_id_pa_8ab50caa FOREIGN KEY(photo_asset_id, parent_gallery_id, tenant_id) REFERENCES photo_asset (id, parent_gallery_id, tenant_id)",
        "ALTER TABLE facial_search_snapshot_item ADD CONSTRAINT fk_owner_facial_search_snapshot_item_search_request_id_dff498a8 FOREIGN KEY(search_request_id, parent_gallery_id, client_id, tenant_id) REFERENCES facial_search_request (id, parent_gallery_id, client_id, tenant_id)",
        "ALTER TABLE folder_client_grant ADD CONSTRAINT fk_scope_folder_client_grant_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE folder_client_grant ADD CONSTRAINT fk_owner_folder_client_grant_folder_id_parent_gallery__e9d4d32d FOREIGN KEY(folder_id, parent_gallery_id, tenant_id) REFERENCES photo_folder (id, parent_gallery_id, tenant_id)",
        "ALTER TABLE folder_client_grant ADD CONSTRAINT fk_owner_folder_client_grant_parent_gallery_id_client__ac764b49 FOREIGN KEY(parent_gallery_id, client_id, tenant_id) REFERENCES gallery_client_state (parent_gallery_id, client_id, tenant_id)",
        "ALTER TABLE folder_processing_settings ADD CONSTRAINT fk_scope_folder_processing_settings_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE folder_processing_settings ADD CONSTRAINT fk_owner_folder_processing_settings_folder_id_tenant_i_37414bd0 FOREIGN KEY(folder_id, tenant_id) REFERENCES photo_folder (id, tenant_id)",
        "ALTER TABLE gallery_access ADD CONSTRAINT fk_scope_gallery_access_parent_gallery_id_parent_gallery FOREIGN KEY(parent_gallery_id) REFERENCES parent_gallery (id)",
        "ALTER TABLE gallery_access ADD CONSTRAINT fk_scope_gallery_access_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE gallery_access ADD CONSTRAINT fk_scope_gallery_access_derived_gallery_id_derived_gallery FOREIGN KEY(derived_gallery_id) REFERENCES derived_gallery (id)",
        "ALTER TABLE gallery_access ADD CONSTRAINT fk_owner_gallery_access_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE gallery_access ADD CONSTRAINT fk_owner_gallery_access_derived_gallery_id_tenant_id_d_58ea1050 FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE gallery_access ADD CONSTRAINT fk_owner_gallery_access_parent_gallery_id_tenant_id_pa_11f7504d FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE gallery_access_capability ADD CONSTRAINT fk_scope_gallery_access_capability_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE gallery_access_capability ADD CONSTRAINT fk_owner_gallery_access_capability_actor_admin_id_tena_c0840687 FOREIGN KEY(actor_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE gallery_access_capability ADD CONSTRAINT fk_owner_gallery_access_capability_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE gallery_access_capability ADD CONSTRAINT fk_owner_gallery_access_capability_derived_gallery_id__55fab5b0 FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE gallery_access_capability ADD CONSTRAINT fk_owner_gallery_access_capability_parent_gallery_id_t_611b7fef FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE gallery_access_capability ADD CONSTRAINT fk_owner_gallery_access_capability_rotated_from_id_ten_ac56b74e FOREIGN KEY(rotated_from_id, tenant_id) REFERENCES gallery_access_capability (id, tenant_id)",
        "ALTER TABLE gallery_client_state ADD CONSTRAINT fk_scope_gallery_client_state_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE gallery_client_state ADD CONSTRAINT fk_owner_gallery_client_state_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE gallery_client_state ADD CONSTRAINT fk_owner_gallery_client_state_parent_gallery_id_tenant_aa0ee3f7 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE gallery_facial_policy ADD CONSTRAINT fk_scope_gallery_facial_policy_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE gallery_facial_policy ADD CONSTRAINT fk_owner_gallery_facial_policy_actor_admin_id_tenant_i_9a64ce19 FOREIGN KEY(actor_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE gallery_facial_policy ADD CONSTRAINT fk_owner_gallery_facial_policy_parent_gallery_id_tenan_08e4abfb FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE gallery_lifecycle_operation ADD CONSTRAINT fk_scope_gallery_lifecycle_operation_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE gallery_lifecycle_operation ADD CONSTRAINT fk_owner_gallery_lifecycle_operation_actor_admin_id_te_5255137d FOREIGN KEY(actor_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE gallery_membership_notification_outbox ADD CONSTRAINT fk_scope_gallery_membership_notification_outbox_tenant_ac63c215 FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE gallery_membership_notification_outbox ADD CONSTRAINT fk_owner_gallery_membership_notification_outbox_client_ea362e47 FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE gallery_membership_notification_outbox ADD CONSTRAINT fk_owner_gallery_membership_notification_outbox_derive_4f2410ed FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE gallery_membership_notification_outbox ADD CONSTRAINT fk_owner_gallery_membership_notification_outbox_parent_374e0ee5 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE gallery_preview_settings ADD CONSTRAINT fk_scope_gallery_preview_settings_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE gallery_preview_settings ADD CONSTRAINT fk_owner_gallery_preview_settings_parent_gallery_id_te_2ca059ac FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE gallery_reopening_notification_outbox ADD CONSTRAINT fk_scope_gallery_reopening_notification_outbox_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE gallery_reopening_notification_outbox ADD CONSTRAINT fk_owner_gallery_reopening_notification_outbox_gallery_52290f01 FOREIGN KEY(gallery_reopening_request_id, tenant_id) REFERENCES gallery_reopening_request (id, tenant_id)",
        "ALTER TABLE gallery_reopening_request ADD CONSTRAINT fk_scope_gallery_reopening_request_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE gallery_reopening_request ADD CONSTRAINT fk_owner_gallery_reopening_request_decided_by_admin_id_5a567fae FOREIGN KEY(decided_by_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE gallery_reopening_request ADD CONSTRAINT fk_owner_gallery_reopening_request_derived_gallery_id__208c2603 FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE gallery_reopening_request ADD CONSTRAINT fk_owner_gallery_reopening_request_parent_gallery_id_r_119c7f0f FOREIGN KEY(parent_gallery_id, requested_by_client_id, tenant_id) REFERENCES gallery_client_state (parent_gallery_id, client_id, tenant_id)",
        "ALTER TABLE gallery_reopening_request ADD CONSTRAINT fk_owner_gallery_reopening_request_parent_gallery_id_t_079b08c9 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE gallery_reopening_request ADD CONSTRAINT fk_owner_gallery_reopening_request_requested_by_client_5e13410b FOREIGN KEY(requested_by_client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE global_pix_settings ADD CONSTRAINT fk_scope_global_pix_settings_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE global_pix_settings ADD CONSTRAINT fk_owner_global_pix_settings_admin_user_id_tenant_id_t_444ab32e FOREIGN KEY(admin_user_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE media_derivative ADD CONSTRAINT fk_scope_media_derivative_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE media_derivative ADD CONSTRAINT fk_owner_media_derivative_photo_asset_id_tenant_id_photo_asset FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE media_job ADD CONSTRAINT fk_scope_media_job_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE media_job ADD CONSTRAINT fk_owner_media_job_photo_asset_id_tenant_id_photo_asset FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE notification_delivery ADD CONSTRAINT fk_scope_notification_delivery_client_recipient_id_client FOREIGN KEY(client_recipient_id) REFERENCES client (id)",
        "ALTER TABLE notification_delivery ADD CONSTRAINT fk_scope_notification_delivery_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE notification_delivery ADD CONSTRAINT fk_scope_notification_delivery_admin_recipient_id_admin_user FOREIGN KEY(admin_recipient_id) REFERENCES admin_user (id)",
        "ALTER TABLE notification_delivery ADD CONSTRAINT fk_owner_notification_delivery_admin_recipient_id_tena_a5883675 FOREIGN KEY(admin_recipient_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE notification_delivery ADD CONSTRAINT fk_owner_notification_delivery_client_recipient_id_ten_88c4032b FOREIGN KEY(client_recipient_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE notification_delivery ADD CONSTRAINT fk_owner_notification_delivery_event_id_tenant_id_noti_e5603b15 FOREIGN KEY(event_id, tenant_id) REFERENCES notification_event (id, tenant_id)",
        "ALTER TABLE notification_delivery ADD CONSTRAINT fk_owner_notification_delivery_subscription_id_tenant__85d326eb FOREIGN KEY(subscription_id, tenant_id) REFERENCES push_subscription (id, tenant_id)",
        "ALTER TABLE notification_event ADD CONSTRAINT fk_scope_notification_event_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE notification_event ADD CONSTRAINT fk_owner_notification_event_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE notification_event ADD CONSTRAINT fk_owner_notification_event_derived_gallery_id_tenant__fb7a04c0 FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE notification_event ADD CONSTRAINT fk_owner_notification_event_event_type_tenant_id_notif_2bea8e95 FOREIGN KEY(event_type, tenant_id) REFERENCES notification_setting (event_type, tenant_id)",
        "ALTER TABLE notification_event ADD CONSTRAINT fk_owner_notification_event_parent_gallery_id_tenant_i_74d134b3 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE notification_event ADD CONSTRAINT fk_owner_notification_event_sale_order_id_tenant_id_sale_order FOREIGN KEY(sale_order_id, tenant_id) REFERENCES sale_order (id, tenant_id)",
        "ALTER TABLE notification_milestone ADD CONSTRAINT fk_scope_notification_milestone_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE notification_milestone ADD CONSTRAINT fk_owner_notification_milestone_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE notification_milestone ADD CONSTRAINT fk_owner_notification_milestone_parent_gallery_id_tena_8f79004d FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE notification_setting ADD CONSTRAINT fk_scope_notification_setting_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE parent_gallery ADD CONSTRAINT fk_owner_parent_gallery_cover_photo_id_tenant_id_photo_asset FOREIGN KEY(cover_photo_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE parent_gallery ADD CONSTRAINT fk_owner_parent_gallery_progressive_pricing_preset_id__e4bb0efa FOREIGN KEY(progressive_pricing_preset_id, tenant_id) REFERENCES progressive_pricing_preset (id, tenant_id)",
        "ALTER TABLE parent_gallery_registration ADD CONSTRAINT fk_scope_parent_gallery_registration_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE parent_gallery_registration ADD CONSTRAINT fk_owner_parent_gallery_registration_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE parent_gallery_registration ADD CONSTRAINT fk_owner_parent_gallery_registration_parent_gallery_id_19b29084 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE payment_communication ADD CONSTRAINT fk_scope_payment_communication_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE payment_communication ADD CONSTRAINT fk_owner_payment_communication_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE payment_communication ADD CONSTRAINT fk_owner_payment_communication_decided_by_admin_id_ten_cb6eaa36 FOREIGN KEY(decided_by_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE payment_communication ADD CONSTRAINT fk_owner_payment_communication_payment_group_id_client_f3ab6b16 FOREIGN KEY(payment_group_id, client_id, tenant_id) REFERENCES payment_group (id, client_id, tenant_id)",
        "ALTER TABLE payment_communication ADD CONSTRAINT fk_owner_payment_communication_sale_order_id_tenant_id_94dc6f48 FOREIGN KEY(sale_order_id, tenant_id) REFERENCES sale_order (id, tenant_id)",
        "ALTER TABLE payment_confirmation_correction ADD CONSTRAINT fk_scope_payment_confirmation_correction_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE payment_confirmation_correction ADD CONSTRAINT fk_owner_payment_confirmation_correction_actor_admin_i_1eaaf39c FOREIGN KEY(actor_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE payment_confirmation_correction ADD CONSTRAINT fk_owner_payment_confirmation_correction_payment_commu_2919ab5c FOREIGN KEY(payment_communication_id, tenant_id) REFERENCES payment_communication (id, tenant_id)",
        "ALTER TABLE payment_confirmation_correction ADD CONSTRAINT fk_owner_payment_confirmation_correction_sale_order_id_f9f01556 FOREIGN KEY(sale_order_id, tenant_id) REFERENCES sale_order (id, tenant_id)",
        "ALTER TABLE payment_group ADD CONSTRAINT fk_scope_payment_group_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE payment_group ADD CONSTRAINT fk_owner_payment_group_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE payment_message_template ADD CONSTRAINT fk_scope_payment_message_template_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE payment_notification_outbox ADD CONSTRAINT fk_scope_payment_notification_outbox_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE payment_notification_outbox ADD CONSTRAINT fk_owner_payment_notification_outbox_payment_communica_474daa65 FOREIGN KEY(payment_communication_id, tenant_id) REFERENCES payment_communication (id, tenant_id)",
        "ALTER TABLE photo_analysis ADD CONSTRAINT fk_scope_photo_analysis_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE photo_analysis ADD CONSTRAINT fk_owner_photo_analysis_photo_asset_id_tenant_id_photo_asset FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE photo_asset ADD CONSTRAINT fk_owner_photo_asset_derived_gallery_id_tenant_id_deri_5d59db0a FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE photo_asset ADD CONSTRAINT fk_owner_photo_asset_folder_id_parent_gallery_id_deriv_a72a0cb7 FOREIGN KEY(folder_id, parent_gallery_id, derived_gallery_id, tenant_id) REFERENCES photo_folder (id, parent_gallery_id, derived_gallery_id, tenant_id)",
        "ALTER TABLE photo_asset ADD CONSTRAINT fk_owner_photo_asset_folder_id_parent_gallery_id_tenan_1c94c15f FOREIGN KEY(folder_id, parent_gallery_id, tenant_id) REFERENCES photo_folder (id, parent_gallery_id, tenant_id)",
        "ALTER TABLE photo_comment ADD CONSTRAINT fk_scope_photo_comment_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE photo_comment ADD CONSTRAINT fk_owner_photo_comment_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE photo_comment ADD CONSTRAINT fk_owner_photo_comment_derived_gallery_id_tenant_id_de_1a2c8d10 FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE photo_comment ADD CONSTRAINT fk_owner_photo_comment_parent_gallery_id_tenant_id_par_3c7c1d41 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE photo_comment ADD CONSTRAINT fk_owner_photo_comment_photo_asset_id_tenant_id_photo_asset FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE photo_face_embedding ADD CONSTRAINT fk_scope_photo_face_embedding_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE photo_face_embedding ADD CONSTRAINT fk_owner_photo_face_embedding_derived_gallery_id_tenan_88519f7f FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE photo_face_embedding ADD CONSTRAINT fk_owner_photo_face_embedding_parent_gallery_id_tenant_6869763e FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE photo_face_embedding ADD CONSTRAINT fk_owner_photo_face_embedding_photo_asset_id_parent_ga_d0102b27 FOREIGN KEY(photo_asset_id, parent_gallery_id, tenant_id) REFERENCES photo_asset (id, parent_gallery_id, tenant_id)",
        "ALTER TABLE photo_favorite ADD CONSTRAINT fk_scope_photo_favorite_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE photo_favorite ADD CONSTRAINT fk_owner_photo_favorite_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE photo_favorite ADD CONSTRAINT fk_owner_photo_favorite_derived_gallery_id_tenant_id_d_e52e8940 FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE photo_favorite ADD CONSTRAINT fk_owner_photo_favorite_parent_gallery_id_tenant_id_pa_496e0174 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE photo_favorite ADD CONSTRAINT fk_owner_photo_favorite_photo_asset_id_tenant_id_photo_asset FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE photo_folder ADD CONSTRAINT fk_scope_photo_folder_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE photo_folder ADD CONSTRAINT fk_owner_photo_folder_derived_gallery_id_tenant_id_der_b8a2b9ec FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE photo_folder ADD CONSTRAINT fk_owner_photo_folder_parent_gallery_id_tenant_id_pare_d40fdce7 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE photo_selection ADD CONSTRAINT fk_scope_photo_selection_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE photo_selection ADD CONSTRAINT fk_owner_photo_selection_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE photo_selection ADD CONSTRAINT fk_owner_photo_selection_derived_gallery_id_tenant_id__9189d785 FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE photo_selection ADD CONSTRAINT fk_owner_photo_selection_parent_gallery_id_tenant_id_p_420d6307 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE photo_selection ADD CONSTRAINT fk_owner_photo_selection_photo_asset_id_tenant_id_photo_asset FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE photo_view ADD CONSTRAINT fk_scope_photo_view_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE photo_view ADD CONSTRAINT fk_owner_photo_view_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE photo_view ADD CONSTRAINT fk_owner_photo_view_derived_gallery_id_tenant_id_deriv_31414b78 FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE photo_view ADD CONSTRAINT fk_owner_photo_view_parent_gallery_id_tenant_id_parent_gallery FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE photo_view ADD CONSTRAINT fk_owner_photo_view_photo_asset_id_tenant_id_photo_asset FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE pix_checkout_settings ADD CONSTRAINT fk_scope_pix_checkout_settings_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE pix_checkout_settings ADD CONSTRAINT fk_owner_pix_checkout_settings_parent_gallery_id_tenan_688bde29 FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE preview_adjustment ADD CONSTRAINT fk_scope_preview_adjustment_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE preview_adjustment ADD CONSTRAINT fk_owner_preview_adjustment_photo_asset_id_tenant_id_p_3dc9f73d FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE preview_adjustment_settings ADD CONSTRAINT fk_scope_preview_adjustment_settings_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE price_rule ADD CONSTRAINT fk_scope_price_rule_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE price_rule ADD CONSTRAINT fk_owner_price_rule_parent_gallery_id_tenant_id_parent_gallery FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE private_upload_batch ADD CONSTRAINT fk_scope_private_upload_batch_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE private_upload_batch ADD CONSTRAINT fk_owner_private_upload_batch_actor_admin_id_tenant_id_2a37b5e8 FOREIGN KEY(actor_admin_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE private_upload_batch ADD CONSTRAINT fk_owner_private_upload_batch_derived_gallery_id_tenan_19292fe9 FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE private_upload_batch_asset ADD CONSTRAINT fk_scope_private_upload_batch_asset_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE private_upload_batch_asset ADD CONSTRAINT fk_owner_private_upload_batch_asset_batch_id_tenant_id_63e6dfcb FOREIGN KEY(batch_id, tenant_id) REFERENCES private_upload_batch (id, tenant_id)",
        "ALTER TABLE private_upload_batch_asset ADD CONSTRAINT fk_owner_private_upload_batch_asset_photo_asset_id_ten_3b77ca74 FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE progressive_pricing_preset ADD CONSTRAINT fk_scope_progressive_pricing_preset_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE progressive_pricing_tier ADD CONSTRAINT fk_scope_progressive_pricing_tier_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE progressive_pricing_tier ADD CONSTRAINT fk_owner_progressive_pricing_tier_preset_id_tenant_id__b42188b8 FOREIGN KEY(preset_id, tenant_id) REFERENCES progressive_pricing_preset (id, tenant_id)",
        "ALTER TABLE push_subscription ADD CONSTRAINT fk_scope_push_subscription_client_subject_id_client FOREIGN KEY(client_subject_id) REFERENCES client (id)",
        "ALTER TABLE push_subscription ADD CONSTRAINT fk_scope_push_subscription_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE push_subscription ADD CONSTRAINT fk_scope_push_subscription_admin_subject_id_admin_user FOREIGN KEY(admin_subject_id) REFERENCES admin_user (id)",
        "ALTER TABLE push_subscription ADD CONSTRAINT fk_owner_push_subscription_admin_subject_id_tenant_id__b83d9bc1 FOREIGN KEY(admin_subject_id, tenant_id) REFERENCES tenant_admin (admin_user_id, tenant_id)",
        "ALTER TABLE push_subscription ADD CONSTRAINT fk_owner_push_subscription_client_subject_id_tenant_id_client FOREIGN KEY(client_subject_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE push_subscription ADD CONSTRAINT fk_owner_push_subscription_session_id_tenant_id_auth_session FOREIGN KEY(session_id, tenant_id) REFERENCES auth_session (id, tenant_id)",
        "ALTER TABLE removed_photo_movement ADD CONSTRAINT fk_scope_removed_photo_movement_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE removed_photo_movement ADD CONSTRAINT fk_owner_removed_photo_movement_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE sale_order ADD CONSTRAINT fk_scope_sale_order_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE sale_order ADD CONSTRAINT fk_owner_sale_order_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)",
        "ALTER TABLE sale_order ADD CONSTRAINT fk_owner_sale_order_derived_gallery_id_tenant_id_deriv_c2511965 FOREIGN KEY(derived_gallery_id, tenant_id) REFERENCES derived_gallery (id, tenant_id)",
        "ALTER TABLE sale_order ADD CONSTRAINT fk_owner_sale_order_parent_gallery_id_client_id_tenant_ea42f8b9 FOREIGN KEY(parent_gallery_id, client_id, tenant_id) REFERENCES gallery_client_state (parent_gallery_id, client_id, tenant_id)",
        "ALTER TABLE sale_order ADD CONSTRAINT fk_owner_sale_order_parent_gallery_id_tenant_id_parent_gallery FOREIGN KEY(parent_gallery_id, tenant_id) REFERENCES parent_gallery (id, tenant_id)",
        "ALTER TABLE sale_order ADD CONSTRAINT fk_owner_sale_order_payment_group_id_client_id_tenant__bee1507d FOREIGN KEY(payment_group_id, client_id, tenant_id) REFERENCES payment_group (id, client_id, tenant_id)",
        "ALTER TABLE sale_order_item ADD CONSTRAINT fk_scope_sale_order_item_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE sale_order_item ADD CONSTRAINT fk_owner_sale_order_item_photo_asset_id_tenant_id_photo_asset FOREIGN KEY(photo_asset_id, tenant_id) REFERENCES photo_asset (id, tenant_id)",
        "ALTER TABLE sale_order_item ADD CONSTRAINT fk_owner_sale_order_item_sale_order_id_tenant_id_sale_order FOREIGN KEY(sale_order_id, tenant_id) REFERENCES sale_order (id, tenant_id)",
        "ALTER TABLE whatsapp_channel_settings ADD CONSTRAINT fk_scope_whatsapp_channel_settings_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE whatsapp_delivery ADD CONSTRAINT fk_scope_whatsapp_delivery_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE whatsapp_delivery_attempt ADD CONSTRAINT fk_scope_whatsapp_delivery_attempt_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)",
        "ALTER TABLE whatsapp_delivery_attempt ADD CONSTRAINT fk_owner_whatsapp_delivery_attempt_delivery_id_tenant__135da421 FOREIGN KEY(delivery_id, tenant_id) REFERENCES whatsapp_delivery (id, tenant_id)",
        "ALTER TABLE whatsapp_webhook_receipt ADD CONSTRAINT fk_scope_whatsapp_webhook_receipt_tenant_id_tenant FOREIGN KEY(tenant_id) REFERENCES tenant (id)"
    ],
    "indexes": [
        "CREATE UNIQUE INDEX ix_admin_action_token_token_hash ON admin_action_token (token_hash)",
        "CREATE INDEX ix_admin_security_challenge_tenant_id ON admin_security_challenge (tenant_id)",
        "CREATE UNIQUE INDEX ix_admin_user_email ON admin_user (email)",
        "CREATE INDEX ix_asset_file_cleanup_tenant_id ON asset_file_cleanup (tenant_id)",
        "CREATE INDEX ix_audit_event_tenant_id ON audit_event (tenant_id)",
        "CREATE INDEX ix_auth_challenge_parent_gallery_id ON auth_challenge (parent_gallery_id)",
        "CREATE INDEX ix_auth_challenge_tenant_id ON auth_challenge (tenant_id)",
        "CREATE INDEX ix_auth_session_tenant_id ON auth_session (tenant_id)",
        "CREATE UNIQUE INDEX ix_auth_session_token_hash ON auth_session (token_hash)",
        "CREATE INDEX ix_branding_settings_tenant_id ON branding_settings (tenant_id)",
        "CREATE INDEX ix_client_tenant_id ON client (tenant_id)",
        "CREATE INDEX ix_client_deletion_receipt_tenant_id ON client_deletion_receipt (tenant_id)",
        "CREATE INDEX ix_client_phone_tenant_id ON client_phone (tenant_id)",
        "CREATE UNIQUE INDEX uq_client_phone_active_reserved ON client_phone (tenant_id, phone_e164) WHERE active",
        "CREATE UNIQUE INDEX uq_client_phone_active_verified ON client_phone (tenant_id, phone_e164) WHERE active AND verified_at IS NOT NULL",
        "CREATE UNIQUE INDEX uq_client_phone_one_active_per_client ON client_phone (tenant_id, client_id) WHERE active",
        "CREATE INDEX ix_commercial_history_media_tenant_id ON commercial_history_media (tenant_id)",
        "CREATE UNIQUE INDEX ix_derived_gallery_parent_client ON derived_gallery (tenant_id, parent_gallery_id, client_id)",
        "CREATE INDEX ix_derived_gallery_membership_tenant_id ON derived_gallery_membership (tenant_id)",
        "CREATE INDEX ix_derived_gallery_photo_tenant_id ON derived_gallery_photo (tenant_id)",
        "CREATE INDEX ix_derived_gallery_photo_origin_derived_gallery_photo_id ON derived_gallery_photo_origin (derived_gallery_photo_id)",
        "CREATE INDEX ix_derived_gallery_photo_origin_tenant_id ON derived_gallery_photo_origin (tenant_id)",
        "CREATE INDEX ix_facial_calibration_approval_tenant_id ON facial_calibration_approval (tenant_id)",
        "CREATE INDEX ix_facial_job_tenant_id ON facial_job (tenant_id)",
        "CREATE INDEX ix_facial_legal_representation_tenant_id ON facial_legal_representation (tenant_id)",
        "CREATE INDEX ix_facial_rollout_tenant_id ON facial_rollout (tenant_id)",
        "CREATE INDEX ix_facial_rollout_operation_tenant_id ON facial_rollout_operation (tenant_id)",
        "CREATE INDEX ix_facial_search_candidate_tenant_id ON facial_search_candidate (tenant_id)",
        "CREATE INDEX ix_facial_search_notification_outbox_tenant_id ON facial_search_notification_outbox (tenant_id)",
        "CREATE INDEX ix_facial_search_request_tenant_id ON facial_search_request (tenant_id)",
        "CREATE INDEX ix_facial_search_snapshot_item_tenant_id ON facial_search_snapshot_item (tenant_id)",
        "CREATE INDEX ix_folder_client_grant_tenant_id ON folder_client_grant (tenant_id)",
        "CREATE INDEX ix_folder_processing_settings_tenant_id ON folder_processing_settings (tenant_id)",
        "CREATE INDEX ix_gallery_access_tenant_id ON gallery_access (tenant_id)",
        "CREATE INDEX ix_gallery_access_capability_tenant_id ON gallery_access_capability (tenant_id)",
        "CREATE UNIQUE INDEX uq_gallery_access_capability_active_invite ON gallery_access_capability (tenant_id, parent_gallery_id, client_id, scope) WHERE scope <> 'public_gallery' AND status = 'active'",
        "CREATE UNIQUE INDEX uq_gallery_access_capability_active_private_link ON gallery_access_capability (tenant_id, derived_gallery_id) WHERE scope = 'private_gallery_link' AND status = 'active'",
        "CREATE UNIQUE INDEX uq_gallery_access_capability_active_public ON gallery_access_capability (tenant_id, parent_gallery_id) WHERE scope = 'public_gallery' AND status = 'active'",
        "CREATE INDEX ix_gallery_client_state_tenant_id ON gallery_client_state (tenant_id)",
        "CREATE INDEX ix_gallery_facial_policy_tenant_id ON gallery_facial_policy (tenant_id)",
        "CREATE INDEX ix_gallery_lifecycle_operation_tenant_id ON gallery_lifecycle_operation (tenant_id)",
        "CREATE INDEX ix_gallery_membership_notification_outbox_tenant_id ON gallery_membership_notification_outbox (tenant_id)",
        "CREATE INDEX ix_gallery_preview_settings_tenant_id ON gallery_preview_settings (tenant_id)",
        "CREATE INDEX ix_gallery_reopening_notification_outbox_tenant_id ON gallery_reopening_notification_outbox (tenant_id)",
        "CREATE INDEX ix_gallery_reopening_request_tenant_id ON gallery_reopening_request (tenant_id)",
        "CREATE UNIQUE INDEX uq_gallery_reopening_canonical_pending ON gallery_reopening_request (tenant_id, parent_gallery_id, requested_by_client_id) WHERE parent_gallery_id IS NOT NULL AND status = 'pending'",
        "CREATE UNIQUE INDEX uq_gallery_reopening_request_pending ON gallery_reopening_request (tenant_id, derived_gallery_id) WHERE status = 'pending'",
        "CREATE INDEX ix_global_pix_settings_tenant_id ON global_pix_settings (tenant_id)",
        "CREATE INDEX ix_media_derivative_tenant_id ON media_derivative (tenant_id)",
        "CREATE INDEX ix_media_job_tenant_id ON media_job (tenant_id)",
        "CREATE INDEX ix_notification_delivery_tenant_id ON notification_delivery (tenant_id)",
        "CREATE INDEX ix_notification_event_tenant_id ON notification_event (tenant_id)",
        "CREATE INDEX ix_notification_milestone_tenant_id ON notification_milestone (tenant_id)",
        "CREATE INDEX ix_notification_setting_tenant_id ON notification_setting (tenant_id)",
        "CREATE INDEX ix_parent_gallery_registration_client_id ON parent_gallery_registration (client_id)",
        "CREATE INDEX ix_parent_gallery_registration_parent_gallery_id ON parent_gallery_registration (parent_gallery_id)",
        "CREATE INDEX ix_parent_gallery_registration_status ON parent_gallery_registration (status)",
        "CREATE INDEX ix_parent_gallery_registration_tenant_id ON parent_gallery_registration (tenant_id)",
        "CREATE INDEX ix_payment_communication_client_id ON payment_communication (client_id)",
        "CREATE INDEX ix_payment_communication_status ON payment_communication (status)",
        "CREATE INDEX ix_payment_communication_tenant_id ON payment_communication (tenant_id)",
        "CREATE INDEX ix_payment_confirmation_correction_tenant_id ON payment_confirmation_correction (tenant_id)",
        "CREATE INDEX ix_payment_group_tenant_id ON payment_group (tenant_id)",
        "CREATE UNIQUE INDEX uq_payment_group_draft ON payment_group (tenant_id, client_id) WHERE state = 'draft'",
        "CREATE INDEX ix_payment_message_template_tenant_id ON payment_message_template (tenant_id)",
        "CREATE INDEX ix_payment_notification_outbox_status ON payment_notification_outbox (status)",
        "CREATE INDEX ix_payment_notification_outbox_tenant_id ON payment_notification_outbox (tenant_id)",
        "CREATE INDEX ix_photo_analysis_tenant_id ON photo_analysis (tenant_id)",
        "CREATE INDEX ix_photo_comment_tenant_id ON photo_comment (tenant_id)",
        "CREATE INDEX ix_photo_face_embedding_tenant_id ON photo_face_embedding (tenant_id)",
        "CREATE INDEX ix_photo_favorite_tenant_id ON photo_favorite (tenant_id)",
        "CREATE UNIQUE INDEX uq_photo_favorite_canonical ON photo_favorite (tenant_id, parent_gallery_id, photo_asset_id, client_id) WHERE derived_gallery_id IS NULL",
        "CREATE INDEX ix_photo_folder_tenant_id ON photo_folder (tenant_id)",
        "CREATE UNIQUE INDEX uq_photo_folder_cover_assets_parent ON photo_folder (tenant_id, parent_gallery_id) WHERE purpose = 'cover_assets'",
        "CREATE UNIQUE INDEX uq_photo_folder_private_position ON photo_folder (tenant_id, derived_gallery_id, position) WHERE derived_gallery_id IS NOT NULL",
        "CREATE UNIQUE INDEX uq_photo_folder_public_position ON photo_folder (tenant_id, parent_gallery_id, position) WHERE derived_gallery_id IS NULL",
        "CREATE INDEX ix_photo_selection_tenant_id ON photo_selection (tenant_id)",
        "CREATE UNIQUE INDEX uq_photo_selection_canonical ON photo_selection (tenant_id, parent_gallery_id, photo_asset_id, client_id) WHERE derived_gallery_id IS NULL",
        "CREATE INDEX ix_photo_view_client_id ON photo_view (client_id)",
        "CREATE INDEX ix_photo_view_derived_gallery_id ON photo_view (derived_gallery_id)",
        "CREATE INDEX ix_photo_view_photo_asset_id ON photo_view (photo_asset_id)",
        "CREATE INDEX ix_photo_view_tenant_id ON photo_view (tenant_id)",
        "CREATE UNIQUE INDEX uq_photo_view_canonical ON photo_view (tenant_id, parent_gallery_id, client_id, photo_asset_id) WHERE derived_gallery_id IS NULL",
        "CREATE UNIQUE INDEX ix_pix_checkout_settings_parent_gallery_id ON pix_checkout_settings (tenant_id, parent_gallery_id)",
        "CREATE INDEX ix_pix_checkout_settings_tenant_id ON pix_checkout_settings (tenant_id)",
        "CREATE INDEX ix_preview_adjustment_tenant_id ON preview_adjustment (tenant_id)",
        "CREATE INDEX ix_preview_adjustment_settings_tenant_id ON preview_adjustment_settings (tenant_id)",
        "CREATE INDEX ix_price_rule_tenant_id ON price_rule (tenant_id)",
        "CREATE INDEX ix_private_upload_batch_tenant_id ON private_upload_batch (tenant_id)",
        "CREATE INDEX ix_private_upload_batch_asset_tenant_id ON private_upload_batch_asset (tenant_id)",
        "CREATE INDEX ix_progressive_pricing_preset_tenant_id ON progressive_pricing_preset (tenant_id)",
        "CREATE INDEX ix_progressive_pricing_tier_tenant_id ON progressive_pricing_tier (tenant_id)",
        "CREATE INDEX ix_push_subscription_tenant_id ON push_subscription (tenant_id)",
        "CREATE INDEX ix_removed_photo_movement_tenant_id ON removed_photo_movement (tenant_id)",
        "CREATE INDEX ix_sale_order_tenant_id ON sale_order (tenant_id)",
        "CREATE UNIQUE INDEX uq_sale_order_canonical_editable_draft ON sale_order (tenant_id, parent_gallery_id, client_id) WHERE parent_gallery_id IS NOT NULL AND frozen_at IS NULL AND payment_status = 'pending' AND checkout_key IS NOT NULL AND assets_removed_at IS NULL",
        "CREATE UNIQUE INDEX uq_sale_order_editable_draft ON sale_order (tenant_id, derived_gallery_id, client_id) WHERE frozen_at IS NULL AND payment_status = 'pending' AND checkout_key IS NOT NULL AND assets_removed_at IS NULL",
        "CREATE INDEX ix_sale_order_item_tenant_id ON sale_order_item (tenant_id)",
        "CREATE INDEX ix_whatsapp_channel_settings_tenant_id ON whatsapp_channel_settings (tenant_id)",
        "CREATE INDEX ix_whatsapp_delivery_tenant_id ON whatsapp_delivery (tenant_id)",
        "CREATE INDEX ix_whatsapp_delivery_attempt_tenant_id ON whatsapp_delivery_attempt (tenant_id)",
        "CREATE INDEX ix_whatsapp_webhook_receipt_tenant_id ON whatsapp_webhook_receipt (tenant_id)"
    ],
    "required": [
        [
            "asset_file_cleanup",
            "tenant_id"
        ],
        [
            "branding_settings",
            "tenant_id"
        ],
        [
            "client",
            "tenant_id"
        ],
        [
            "client_deletion_receipt",
            "tenant_id"
        ],
        [
            "client_phone",
            "tenant_id"
        ],
        [
            "commercial_history_media",
            "tenant_id"
        ],
        [
            "derived_gallery_membership",
            "tenant_id"
        ],
        [
            "derived_gallery_photo",
            "tenant_id"
        ],
        [
            "derived_gallery_photo_origin",
            "tenant_id"
        ],
        [
            "facial_calibration_approval",
            "tenant_id"
        ],
        [
            "facial_job",
            "tenant_id"
        ],
        [
            "facial_legal_representation",
            "tenant_id"
        ],
        [
            "facial_rollout",
            "tenant_id"
        ],
        [
            "facial_rollout_operation",
            "tenant_id"
        ],
        [
            "facial_search_candidate",
            "tenant_id"
        ],
        [
            "facial_search_notification_outbox",
            "tenant_id"
        ],
        [
            "facial_search_request",
            "tenant_id"
        ],
        [
            "facial_search_snapshot_item",
            "tenant_id"
        ],
        [
            "folder_client_grant",
            "tenant_id"
        ],
        [
            "folder_processing_settings",
            "tenant_id"
        ],
        [
            "gallery_access",
            "tenant_id"
        ],
        [
            "gallery_access_capability",
            "tenant_id"
        ],
        [
            "gallery_client_state",
            "tenant_id"
        ],
        [
            "gallery_facial_policy",
            "tenant_id"
        ],
        [
            "gallery_lifecycle_operation",
            "tenant_id"
        ],
        [
            "gallery_membership_notification_outbox",
            "tenant_id"
        ],
        [
            "gallery_preview_settings",
            "tenant_id"
        ],
        [
            "gallery_reopening_notification_outbox",
            "tenant_id"
        ],
        [
            "gallery_reopening_request",
            "tenant_id"
        ],
        [
            "global_pix_settings",
            "tenant_id"
        ],
        [
            "media_derivative",
            "tenant_id"
        ],
        [
            "media_job",
            "tenant_id"
        ],
        [
            "notification_delivery",
            "tenant_id"
        ],
        [
            "notification_event",
            "tenant_id"
        ],
        [
            "notification_milestone",
            "tenant_id"
        ],
        [
            "notification_setting",
            "tenant_id"
        ],
        [
            "parent_gallery_registration",
            "tenant_id"
        ],
        [
            "payment_communication",
            "tenant_id"
        ],
        [
            "payment_confirmation_correction",
            "tenant_id"
        ],
        [
            "payment_group",
            "tenant_id"
        ],
        [
            "payment_message_template",
            "tenant_id"
        ],
        [
            "payment_notification_outbox",
            "tenant_id"
        ],
        [
            "photo_analysis",
            "tenant_id"
        ],
        [
            "photo_comment",
            "tenant_id"
        ],
        [
            "photo_face_embedding",
            "tenant_id"
        ],
        [
            "photo_favorite",
            "tenant_id"
        ],
        [
            "photo_folder",
            "tenant_id"
        ],
        [
            "photo_selection",
            "tenant_id"
        ],
        [
            "photo_view",
            "tenant_id"
        ],
        [
            "pix_checkout_settings",
            "tenant_id"
        ],
        [
            "preview_adjustment",
            "tenant_id"
        ],
        [
            "preview_adjustment_settings",
            "tenant_id"
        ],
        [
            "price_rule",
            "tenant_id"
        ],
        [
            "private_upload_batch",
            "tenant_id"
        ],
        [
            "private_upload_batch_asset",
            "tenant_id"
        ],
        [
            "progressive_pricing_preset",
            "tenant_id"
        ],
        [
            "progressive_pricing_tier",
            "tenant_id"
        ],
        [
            "push_subscription",
            "tenant_id"
        ],
        [
            "removed_photo_movement",
            "tenant_id"
        ],
        [
            "sale_order",
            "tenant_id"
        ],
        [
            "sale_order_item",
            "tenant_id"
        ],
        [
            "whatsapp_channel_settings",
            "tenant_id"
        ],
        [
            "whatsapp_delivery",
            "tenant_id"
        ],
        [
            "whatsapp_delivery_attempt",
            "tenant_id"
        ],
        [
            "whatsapp_webhook_receipt",
            "tenant_id"
        ]
    ]
}
