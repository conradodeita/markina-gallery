"""Adiciona configurações do título sobre a capa."""

import sqlalchemy as sa
from alembic import op

revision = "20260827_0009"
down_revision = "20260827_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("parent_gallery") as batch_op:
        batch_op.add_column(sa.Column("cover_title_font", sa.String(length=80), nullable=False, server_default="sans-serif"))
        batch_op.add_column(sa.Column("cover_title_color", sa.String(length=7), nullable=False, server_default="#FFFFFF"))
        batch_op.add_column(sa.Column("cover_title_size", sa.Integer(), nullable=False, server_default="32"))
        batch_op.add_column(sa.Column("cover_title_position", sa.String(length=16), nullable=False, server_default="bottom-left"))


def downgrade() -> None:
    with op.batch_alter_table("parent_gallery") as batch_op:
        for name in ("cover_title_position", "cover_title_size", "cover_title_color", "cover_title_font"):
            batch_op.drop_column(name)
