"""Vincula desafio OTP a capacidade e retorno interno seguro.

Revision ID: 20260831_0028
Revises: 20260831_0027
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0028"
down_revision = "20260831_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("auth_challenge", recreate="always") as batch_op:
            batch_op.add_column(
                sa.Column("gallery_capability_id", sa.Uuid(), nullable=True)
            )
            batch_op.add_column(
                sa.Column("return_to", sa.String(length=512), nullable=True)
            )
            batch_op.create_index(
                "ix_auth_challenge_gallery_capability_id",
                ["gallery_capability_id"],
            )
    else:
        op.add_column(
            "auth_challenge",
            sa.Column("gallery_capability_id", sa.Uuid(), nullable=True),
        )
        op.add_column(
            "auth_challenge",
            sa.Column("return_to", sa.String(length=512), nullable=True),
        )
        op.create_index(
            "ix_auth_challenge_gallery_capability_id",
            "auth_challenge",
            ["gallery_capability_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("auth_challenge", recreate="always") as batch_op:
            batch_op.drop_index("ix_auth_challenge_gallery_capability_id")
            batch_op.drop_column("return_to")
            batch_op.drop_column("gallery_capability_id")
    else:
        op.drop_index(
            "ix_auth_challenge_gallery_capability_id",
            table_name="auth_challenge",
        )
        op.drop_column("auth_challenge", "return_to")
        op.drop_column("auth_challenge", "gallery_capability_id")
