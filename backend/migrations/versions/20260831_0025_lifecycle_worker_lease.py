"""Adiciona lease retomável às operações de ciclo de vida.

Revision ID: 20260831_0025
Revises: 20260831_0024
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0025"
down_revision = "20260831_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "gallery_lifecycle_operation", recreate="always"
        ) as batch_op:
            batch_op.add_column(
                sa.Column("attempts", sa.Integer(), nullable=False, server_default="0")
            )
            batch_op.add_column(
                sa.Column("lease_token", sa.String(length=64), nullable=True)
            )
            batch_op.add_column(
                sa.Column(
                    "lease_expires_at", sa.DateTime(timezone=True), nullable=True
                )
            )
            batch_op.create_check_constraint(
                "ck_gallery_lifecycle_operation_attempts", "attempts >= 0"
            )
            batch_op.create_index(
                "ix_gallery_lifecycle_operation_lease_expires_at",
                ["lease_expires_at"],
            )
    else:
        op.add_column(
            "gallery_lifecycle_operation",
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        )
        op.add_column(
            "gallery_lifecycle_operation",
            sa.Column("lease_token", sa.String(length=64), nullable=True),
        )
        op.add_column(
            "gallery_lifecycle_operation",
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_check_constraint(
            "ck_gallery_lifecycle_operation_attempts",
            "gallery_lifecycle_operation",
            "attempts >= 0",
        )
        op.create_index(
            "ix_gallery_lifecycle_operation_lease_expires_at",
            "gallery_lifecycle_operation",
            ["lease_expires_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "gallery_lifecycle_operation", recreate="always"
        ) as batch_op:
            batch_op.drop_index(
                "ix_gallery_lifecycle_operation_lease_expires_at"
            )
            batch_op.drop_constraint(
                "ck_gallery_lifecycle_operation_attempts", type_="check"
            )
            batch_op.drop_column("lease_expires_at")
            batch_op.drop_column("lease_token")
            batch_op.drop_column("attempts")
    else:
        op.drop_index(
            "ix_gallery_lifecycle_operation_lease_expires_at",
            table_name="gallery_lifecycle_operation",
        )
        op.drop_constraint(
            "ck_gallery_lifecycle_operation_attempts",
            "gallery_lifecycle_operation",
            type_="check",
        )
        op.drop_column("gallery_lifecycle_operation", "lease_expires_at")
        op.drop_column("gallery_lifecycle_operation", "lease_token")
        op.drop_column("gallery_lifecycle_operation", "attempts")
