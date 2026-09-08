"""Adiciona configurações visuais da galeria e marca-d'água."""

import sqlalchemy as sa
from alembic import op

revision = "20260827_0008"
down_revision = "20260827_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("parent_gallery") as batch_op:
        batch_op.add_column(sa.Column("watermark_text", sa.String(length=120), nullable=False, server_default="MARKINA • PRÉVIA"))
        batch_op.add_column(sa.Column("watermark_font", sa.String(length=80), nullable=False, server_default="sans-serif"))
        batch_op.add_column(sa.Column("watermark_color", sa.String(length=7), nullable=False, server_default="#FFFFFF"))
        batch_op.add_column(sa.Column("watermark_size", sa.Integer(), nullable=False, server_default="24"))
        batch_op.add_column(sa.Column("watermark_direction", sa.String(length=16), nullable=False, server_default="diagonal"))
        batch_op.add_column(sa.Column("folder_display_mode", sa.String(length=16), nullable=False, server_default="individual"))


def downgrade() -> None:
    with op.batch_alter_table("parent_gallery") as batch_op:
        for name in ("folder_display_mode", "watermark_direction", "watermark_size", "watermark_color", "watermark_font", "watermark_text"):
            batch_op.drop_column(name)
