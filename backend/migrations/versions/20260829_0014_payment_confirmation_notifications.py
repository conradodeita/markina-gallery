"""Adiciona comunicação manual de pagamento e caixa de saída.

Revision ID: 20260829_0014
Revises: 20260828_0012
"""

import sqlalchemy as sa
from alembic import op

revision = "20260829_0014"
down_revision = "20260828_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table("payment_communication", sa.Column("id", uuid, primary_key=True), sa.Column("sale_order_id", uuid, sa.ForeignKey("sale_order.id"), nullable=False), sa.Column("client_id", uuid, sa.ForeignKey("client.id"), nullable=False), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("decided_by_admin_id", uuid, sa.ForeignKey("admin_user.id"), nullable=True), sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("sale_order_id", "idempotency_key"), sa.CheckConstraint("status IN ('pending_review', 'confirmed', 'refused')"))
    op.create_index("ix_payment_communication_sale_order_id", "payment_communication", ["sale_order_id"])
    op.create_table("payment_message_template", sa.Column("id", uuid, primary_key=True), sa.Column("kind", sa.String(16), nullable=False, unique=True), sa.Column("body", sa.String(500), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("payment_notification_outbox", sa.Column("id", uuid, primary_key=True), sa.Column("payment_communication_id", uuid, sa.ForeignKey("payment_communication.id"), nullable=False), sa.Column("recipient_phone", sa.String(32), nullable=False), sa.Column("template_kind", sa.String(32), nullable=False), sa.Column("idempotency_key", sa.String(160), nullable=False, unique=True), sa.Column("status", sa.String(16), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("last_error", sa.String(500), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("template_kind IN ('photographer_reported', 'confirmed', 'refused')"), sa.CheckConstraint("status IN ('queued', 'processing', 'sent', 'failed')"), sa.CheckConstraint("attempts >= 0"))
    op.create_index("ix_payment_notification_outbox_payment_communication_id", "payment_notification_outbox", ["payment_communication_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_notification_outbox_payment_communication_id", table_name="payment_notification_outbox")
    op.drop_table("payment_notification_outbox")
    op.drop_table("payment_message_template")
    op.drop_index("ix_payment_communication_sale_order_id", table_name="payment_communication")
    op.drop_table("payment_communication")
