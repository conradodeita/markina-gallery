"""Adiciona configuração única de marca e textos da entrada."""

import sqlalchemy as sa
from alembic import op

revision = "20260828_0010"
down_revision = "20260827_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "branding_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("login_title", sa.String(length=120), nullable=False, server_default="Sua galeria, do seu jeito."),
        sa.Column("login_intro", sa.String(length=300), nullable=False, server_default="Entre para acessar fotos, seleções e entregas — ou gerenciar sua operação."),
        sa.Column("login_helper", sa.String(length=240), nullable=False, server_default="Escolha seu tipo de acesso para continuar."),
        sa.Column("logo_key", sa.String(length=512), nullable=True),
        sa.Column("app_icon_key", sa.String(length=512), nullable=True),
        sa.Column("favicon_key", sa.String(length=512), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("branding_settings")
