"""Cria metadados de derivados e jobs de mídia protegida.

Revision ID: 20260826_0003
Revises: 20260826_0002
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0003"
down_revision = "20260826_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "media_derivative",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("photo_asset_id", uuid, sa.ForeignKey("photo_asset.id"), nullable=False),
        sa.Column("variant", sa.String(32), nullable=False),
        sa.Column("relative_path", sa.String(1024), nullable=True, unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("photo_asset_id", "variant"),
        sa.CheckConstraint("variant IN ('thumbnail', 'client_preview', 'admin_preview')"),
        sa.CheckConstraint("status IN ('queued', 'ready', 'failed')"),
    )
    op.create_index("ix_media_derivative_photo_asset_id", "media_derivative", ["photo_asset_id"])
    op.create_index("ix_media_derivative_status", "media_derivative", ["status"])
    op.create_table(
        "media_job",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("photo_asset_id", uuid, sa.ForeignKey("photo_asset.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("photo_asset_id", "kind"),
        sa.CheckConstraint("kind IN ('generate_derivatives')"),
        sa.CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed')"),
        sa.CheckConstraint("attempts >= 0"),
    )
    op.create_index("ix_media_job_photo_asset_id", "media_job", ["photo_asset_id"])
    op.create_index("ix_media_job_status", "media_job", ["status"])


def downgrade() -> None:
    op.drop_table("media_job")
    op.drop_table("media_derivative")
