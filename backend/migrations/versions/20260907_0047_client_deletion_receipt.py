"""Adiciona recibo idempotente de exclusão global de cliente.

Revision ID: 20260907_0047
Revises: 20260906_0046
"""

import sqlalchemy as sa
from alembic import op

revision = "20260907_0047"
down_revision = "20260906_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_deletion_receipt",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("target_client_id", sa.Uuid(), nullable=False),
        sa.Column(
            "actor_admin_id",
            sa.Uuid(),
            sa.ForeignKey("admin_user.id"),
            nullable=False,
        ),
        sa.Column("inventory_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("removed_counts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('completed')", name="ck_client_deletion_receipt_status"
        ),
        sa.CheckConstraint(
            "length(inventory_fingerprint) = 64",
            name="ck_client_deletion_receipt_fingerprint",
        ),
        sa.CheckConstraint(
            "length(idempotency_key) = 64",
            name="ck_client_deletion_receipt_idempotency_fingerprint",
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_client_deletion_receipt_idempotency"
        ),
    )
    op.create_index(
        "ix_client_deletion_receipt_target_client_id",
        "client_deletion_receipt",
        ["target_client_id"],
    )
    op.create_index(
        "ix_client_deletion_receipt_actor_admin_id",
        "client_deletion_receipt",
        ["actor_admin_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_client_deletion_receipt_actor_admin_id",
        table_name="client_deletion_receipt",
    )
    op.drop_index(
        "ix_client_deletion_receipt_target_client_id",
        table_name="client_deletion_receipt",
    )
    op.drop_table("client_deletion_receipt")
