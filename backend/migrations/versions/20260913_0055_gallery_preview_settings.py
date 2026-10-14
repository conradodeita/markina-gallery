"""Ajuste por galeria; preserva geração/resultados e não enfileira fotos."""

import sqlalchemy as sa
from alembic import op

revision = "20260913_0055"
down_revision = "20260913_0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gallery_preview_settings",
        sa.Column(
            "parent_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("parent_gallery.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("exposure_tenths", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("generation >= 1"),
        sa.CheckConstraint("strength BETWEEN 10 AND 75"),
        sa.CheckConstraint("exposure_tenths BETWEEN -20 AND 20"),
    )
    op.execute(
        sa.text(
            "INSERT INTO gallery_preview_settings "
            "(parent_gallery_id, enabled, generation, strength, exposure_tenths, updated_at) "
            "SELECT p.id, COALESCE(s.enabled, false), COALESCE(s.generation, 1), "
            "COALESCE(s.strength, 50), 0, CURRENT_TIMESTAMP "
            "FROM parent_gallery p LEFT JOIN preview_adjustment_settings s ON s.id = 1"
        )
    )
    # Fail-closed se alguém reiniciar acidentalmente o worker da versão global.
    op.execute(sa.text("UPDATE preview_adjustment_settings SET enabled = false"))


def downgrade() -> None:
    # O singleton legado não representa mais as configurações individuais.
    # Desligar impede o código anterior de servir resultados de outra geração.
    op.execute(sa.text("UPDATE preview_adjustment_settings SET enabled = false"))
    op.drop_table("gallery_preview_settings")
