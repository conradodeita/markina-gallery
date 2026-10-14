"""Módulo opcional de ajuste de prévias; nenhuma alteração dos derivados existentes."""

import sqlalchemy as sa
from alembic import op

revision = "20260913_0054"
down_revision = "20260910_0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preview_adjustment_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1"),
        sa.CheckConstraint("generation >= 1"),
        sa.CheckConstraint("strength BETWEEN 10 AND 75"),
    )
    op.execute(
        sa.text(
            "INSERT INTO preview_adjustment_settings "
            "(id, enabled, generation, strength, updated_at) VALUES (1, false, 1, 50, CURRENT_TIMESTAMP)"
        )
    )
    op.create_table(
        "preview_adjustment",
        sa.Column(
            "photo_asset_id",
            sa.Uuid(),
            sa.ForeignKey("photo_asset.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("claim_token", sa.String(36)),
        sa.Column("relative_path", sa.String(1024)),
        sa.Column("elapsed_ms", sa.Integer()),
        sa.Column("last_error", sa.String(240)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('queued', 'processing', 'ready', 'failed', 'cancelled')"),
        sa.CheckConstraint("attempts >= 0"),
    )
    op.create_index("ix_preview_adjustment_queue", "preview_adjustment", ["status", "updated_at"])


def downgrade() -> None:
    op.drop_table("preview_adjustment")
    op.drop_table("preview_adjustment_settings")
