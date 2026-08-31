"""Adiciona estado de retenção e minimização ao histórico comercial.

Revision ID: 20260831_0024
Revises: 20260831_0023
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0024"
down_revision = "20260831_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("sale_order", recreate="always") as batch_op:
            batch_op.add_column(
                sa.Column("pii_minimized_at", sa.DateTime(timezone=True), nullable=True)
            )
        with op.batch_alter_table(
            "commercial_history_media", recreate="always"
        ) as batch_op:
            batch_op.drop_constraint(
                "ck_commercial_history_media_status", type_="check"
            )
            batch_op.add_column(
                sa.Column(
                    "retention_expires_at", sa.DateTime(timezone=True), nullable=True
                )
            )
            batch_op.add_column(
                sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True)
            )
            batch_op.create_check_constraint(
                "ck_commercial_history_media_status",
                "status IN ('pending', 'preparing', 'ready', 'failed', 'purged')",
            )
            batch_op.create_index(
                "ix_commercial_history_media_retention_expires_at",
                ["retention_expires_at"],
            )
    else:
        op.add_column(
            "sale_order",
            sa.Column("pii_minimized_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.drop_constraint(
            "ck_commercial_history_media_status",
            "commercial_history_media",
            type_="check",
        )
        op.add_column(
            "commercial_history_media",
            sa.Column(
                "retention_expires_at", sa.DateTime(timezone=True), nullable=True
            ),
        )
        op.add_column(
            "commercial_history_media",
            sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_check_constraint(
            "ck_commercial_history_media_status",
            "commercial_history_media",
            "status IN ('pending', 'preparing', 'ready', 'failed', 'purged')",
        )
        op.create_index(
            "ix_commercial_history_media_retention_expires_at",
            "commercial_history_media",
            ["retention_expires_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    purged = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM commercial_history_media WHERE status = 'purged'"
        )
    ).scalar_one()
    if purged:
        raise RuntimeError(
            "Downgrade bloqueado: existe mídia histórica já expurgada pela política."
        )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "commercial_history_media", recreate="always"
        ) as batch_op:
            batch_op.drop_index(
                "ix_commercial_history_media_retention_expires_at"
            )
            batch_op.drop_constraint(
                "ck_commercial_history_media_status", type_="check"
            )
            batch_op.create_check_constraint(
                "ck_commercial_history_media_status",
                "status IN ('pending', 'preparing', 'ready', 'failed')",
            )
            batch_op.drop_column("purged_at")
            batch_op.drop_column("retention_expires_at")
        with op.batch_alter_table("sale_order", recreate="always") as batch_op:
            batch_op.drop_column("pii_minimized_at")
    else:
        op.drop_index(
            "ix_commercial_history_media_retention_expires_at",
            table_name="commercial_history_media",
        )
        op.drop_constraint(
            "ck_commercial_history_media_status",
            "commercial_history_media",
            type_="check",
        )
        op.create_check_constraint(
            "ck_commercial_history_media_status",
            "commercial_history_media",
            "status IN ('pending', 'preparing', 'ready', 'failed')",
        )
        op.drop_column("commercial_history_media", "purged_at")
        op.drop_column("commercial_history_media", "retention_expires_at")
        op.drop_column("sale_order", "pii_minimized_at")
