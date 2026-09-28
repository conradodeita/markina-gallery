"""Configuração opcional por pasta, sem alterar pastas existentes."""

import sqlalchemy as sa
from alembic import op

revision = "20260928_0068"
down_revision = "20260927_0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "folder_processing_settings",
        sa.Column("folder_id", sa.Uuid(), sa.ForeignKey("photo_folder.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("preview_mode", sa.String(16), nullable=False, server_default="inherit"),
        sa.Column("facial_mode", sa.String(16), nullable=False, server_default="inherit"),
        sa.Column("preview_strength", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("preview_exposure_tenths", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("preview_mode IN ('inherit', 'custom', 'off')", name="ck_folder_preview_mode"),
        sa.CheckConstraint("facial_mode IN ('inherit', 'on', 'off')", name="ck_folder_facial_mode"),
        sa.CheckConstraint("preview_strength BETWEEN 10 AND 75", name="ck_folder_preview_strength"),
        sa.CheckConstraint("preview_exposure_tenths BETWEEN -20 AND 20", name="ck_folder_preview_exposure"),
        sa.CheckConstraint("revision >= 1", name="ck_folder_processing_revision"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    active = bind.execute(sa.text(
        "SELECT folder_id FROM folder_processing_settings "
        "WHERE preview_mode <> 'inherit' OR facial_mode <> 'inherit' LIMIT 1"
    )).first()
    if active:
        raise RuntimeError("Downgrade recusado: existem configurações próprias por pasta.")
    op.drop_table("folder_processing_settings")
