"""Add a per-photographer switch for offering new card checkouts."""

import sqlalchemy as sa
from alembic import op

revision = "20261013_0078"
down_revision = "20261012_0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "infinitepay_settings",
        sa.Column("card_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT COUNT(*) FROM infinitepay_settings WHERE card_enabled")):
        raise RuntimeError("Downgrade recusado: preserve as preferências de disponibilidade de cartão.")
    op.drop_column("infinitepay_settings", "card_enabled")
