"""Centraliza a proteção visual configurável da Markina Gallery.

Revision ID: 20260829_0015
Revises: 20260829_0014
Create Date: 2026-08-29
"""

import sqlalchemy as sa
from alembic import op


revision = "20260829_0015"
down_revision = "20260829_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("branding_settings") as batch_op:
        batch_op.add_column(sa.Column("watermark_text", sa.String(length=120), nullable=False, server_default="MARKINA • PRÉVIA"))
        batch_op.add_column(sa.Column("watermark_font", sa.String(length=80), nullable=False, server_default="sans-serif"))
        batch_op.add_column(sa.Column("watermark_color", sa.String(length=7), nullable=False, server_default="#FFFFFF"))
        batch_op.add_column(sa.Column("watermark_size", sa.Integer(), nullable=False, server_default="24"))
        batch_op.add_column(sa.Column("watermark_direction", sa.String(length=16), nullable=False, server_default="diagonal"))


def downgrade() -> None:
    with op.batch_alter_table("branding_settings") as batch_op:
        for name in ("watermark_direction", "watermark_size", "watermark_color", "watermark_font", "watermark_text"):
            batch_op.drop_column(name)
