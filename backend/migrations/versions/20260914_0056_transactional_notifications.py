"""Matriz e outbox de notificações; baseline silencioso, sem enfileirar histórico."""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "20260914_0056"
down_revision = "20260913_0055"
branch_labels = None
depends_on = None


def timestamp(name, nullable=False):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def reference(name, table, *, nullable=False, primary_key=False, ondelete="CASCADE"):
    return sa.Column(name, sa.Uuid(), sa.ForeignKey(f"{table}.id", ondelete=ondelete),
                     nullable=nullable, primary_key=primary_key)


def upgrade():
    settings = op.create_table(
        "notification_setting",
        sa.Column("event_type", sa.String(32), primary_key=True),
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False),
        sa.Column("push_enabled", sa.Boolean(), nullable=False),
        timestamp("whatsapp_disabled_at", nullable=True),
        timestamp("push_disabled_at", nullable=True),
        sa.Column("whatsapp_body", sa.String(500), nullable=False),
        sa.Column("push_title", sa.String(60), nullable=False),
        sa.Column("push_body", sa.String(140), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False), timestamp("updated_at"),
        sa.CheckConstraint("version >= 1"),
    )
    milestones = op.create_table(
        "notification_milestone",
        reference("parent_gallery_id", "parent_gallery", primary_key=True),
        reference("client_id", "client", primary_key=True),
        sa.Column("kind", sa.String(24), primary_key=True),
        sa.Column("baseline", sa.Boolean(), nullable=False), timestamp("created_at"),
        sa.CheckConstraint("kind IN ('first_access', 'first_selection')"),
    )
    op.create_table(
        "push_subscription",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("endpoint_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("installation_fingerprint", sa.String(64), nullable=True, unique=True),
        sa.Column("encrypted_subscription", sa.Text(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False, index=True),
        reference("session_id", "auth_session", nullable=True, ondelete="SET NULL"),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        timestamp("created_at"), timestamp("updated_at"),
        sa.CheckConstraint("role IN ('admin', 'client')"),
        sa.CheckConstraint("generation >= 1"),
    )
    op.create_index("ix_push_subscription_owner_active", "push_subscription",
                    ["role", "subject_id", "active"])
    op.create_table(
        "notification_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_key", sa.String(192), nullable=False, unique=True),
        sa.Column("event_type", sa.String(32),
                  sa.ForeignKey("notification_setting.event_type"), nullable=False),
        reference("parent_gallery_id", "parent_gallery", nullable=True),
        reference("derived_gallery_id", "derived_gallery", nullable=True),
        reference("client_id", "client", nullable=True),
        reference("sale_order_id", "sale_order", nullable=True),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("push_title", sa.String(60), nullable=False),
        sa.Column("push_body", sa.String(140), nullable=False),
        sa.Column("whatsapp_body", sa.String(500), nullable=False),
        sa.Column("target_path", sa.String(200), nullable=False),
        timestamp("created_at"), timestamp("expires_at"),
    )
    op.create_table(
        "notification_delivery",
        sa.Column("id", sa.Uuid(), primary_key=True),
        reference("event_id", "notification_event"),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("recipient_role", sa.String(16), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("device_key", sa.String(64), nullable=False),
        reference("subscription_id", "push_subscription", nullable=True),
        sa.Column("subscription_generation", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        timestamp("next_attempt_at"), timestamp("lease_until", nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("last_error", sa.String(80), nullable=True),
        timestamp("created_at"), timestamp("updated_at"),
        sa.UniqueConstraint("event_id", "channel", "recipient_role", "recipient_id", "device_key"),
        sa.CheckConstraint("channel IN ('push', 'whatsapp')"),
        sa.CheckConstraint("recipient_role IN ('admin', 'client')"),
        sa.CheckConstraint("attempts >= 0"),
        sa.CheckConstraint("status IN ('queued', 'processing', 'accepted', 'failed', "
                           "'unknown', 'expired', 'cancelled')"),
    )
    op.create_index("ix_notification_delivery_event_id", "notification_delivery", ["event_id"])
    op.create_index("ix_notification_delivery_ready", "notification_delivery",
                    ["channel", "status", "next_attempt_at"])
    op.create_table(
        "private_upload_batch",
        sa.Column("id", sa.Uuid(), primary_key=True),
        reference("derived_gallery_id", "derived_gallery"),
        reference("actor_admin_id", "admin_user", ondelete=None),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("recipient_ids", sa.JSON(), nullable=False),
        timestamp("created_at"), timestamp("closed_at", nullable=True),
        timestamp("announced_at", nullable=True),
        sa.CheckConstraint("status IN ('open', 'closed', 'completed')"),
    )
    op.create_index("ix_private_upload_batch_derived_gallery_id", "private_upload_batch",
                    ["derived_gallery_id"])
    op.create_table(
        "private_upload_batch_asset",
        reference("batch_id", "private_upload_batch", primary_key=True),
        reference("photo_asset_id", "photo_asset", primary_key=True),
        sa.UniqueConstraint("photo_asset_id"),
    )
    # Defaults congelados nesta revisão; não importar código de aplicação futuro.
    defaults = [
        ("first_access", "Primeiro acesso", "{{cliente}} acessou {{galeria}}."),
        ("first_selection", "Seleção iniciada",
         "{{cliente}} começou a escolher em {{galeria}}."),
        ("private_photos_ready", "Novas fotos", "Novas fotos disponíveis na sua galeria."),
        ("payment_reported", "Pagamento informado",
         "{{cliente}} informou pagamento do pedido {{pedido}}."),
        ("payment_confirmed", "Pagamento confirmado", "Confirmamos o pagamento do seu pedido."),
        ("payment_refused", "Pagamento não localizado",
         "Não localizamos seu pagamento. Confira seu pedido."),
    ]
    legacy = {kind: body for kind, body in op.get_bind().execute(
        sa.text("SELECT kind, body FROM payment_message_template")
    )}
    legacy_defaults = {
        "confirmed": "Olá {{cliente}}, confirmamos o pagamento do pedido {{pedido}} "
                     "da galeria {{galeria}}. Suas fotos seguirão para edição.",
        "refused": "Olá {{cliente}}, não localizamos o pagamento do pedido {{pedido}} "
                   "da galeria {{galeria}}. Revise os dados antes de comunicar novamente.",
    }
    instant = datetime.now(UTC)
    for event_type, title, body in defaults:
        kind = event_type.removeprefix("payment_")
        whatsapp = legacy.get(kind, legacy_defaults.get(kind, body))
        op.get_bind().execute(settings.insert().values(
            event_type=event_type, whatsapp_enabled=True, push_enabled=True,
            whatsapp_body=whatsapp, push_title=title, push_body=body,
            version=1, updated_at=instant,
        ))
    # Vinculações antigas não são primeiro acesso/seleção novos, mesmo sem histórico.
    pairs = sa.text(
        "SELECT parent_gallery_id, client_id FROM parent_gallery_registration UNION "
        "SELECT parent_gallery_id, client_id FROM derived_gallery_membership UNION "
        "SELECT parent_gallery_id, client_id FROM derived_gallery"
    )
    for parent_id, client_id in op.get_bind().execute(pairs):
        from uuid import UUID
        for kind in ("first_access", "first_selection"):
            op.get_bind().execute(milestones.insert().values(
                parent_gallery_id=UUID(str(parent_id)), client_id=UUID(str(client_id)),
                kind=kind, baseline=True, created_at=instant,
            ))


def downgrade():
    # Apenas schemas vazios de teste podem voltar. Operação usa transporte desligado.
    tables = ("private_upload_batch_asset", "private_upload_batch", "notification_delivery",
              "notification_event", "push_subscription", "notification_milestone")
    if any(op.get_bind().scalar(sa.text(f"SELECT count(*) FROM {table}")) for table in tables):
        raise RuntimeError("Rollback deve preservar dados; use transporte desligado.")
    for table in (*tables, "notification_setting"):
        op.drop_table(table)
