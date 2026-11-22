"""Preserve legacy credit-only links and verified payment method."""

import sqlalchemy as sa
from alembic import op

revision = "20261021_0086"
down_revision = "20261020_0085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("provider_payment", sa.Column("checkout_methods_snapshot", sa.JSON(),
        nullable=False, server_default=sa.text("'[\"credit_card\"]'")))
    op.add_column("provider_payment", sa.Column("capture_method", sa.String(24), nullable=True))
    op.add_column("provider_payment", sa.Column("cart_dismissed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("ck_provider_payment_capture_method", "provider_payment",
        "capture_method IS NULL OR capture_method IN ('credit_card', 'pix')")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM provider_payment WHERE "
        "CAST(checkout_methods_snapshot AS TEXT) <> '[\"credit_card\"]' "
        "OR capture_method IS NOT NULL OR cart_dismissed_at IS NOT NULL")):
        raise RuntimeError("Downgrade recusado: preserve meios de pagamento, confirmação e desistência.")
    op.drop_constraint("ck_provider_payment_capture_method", "provider_payment", type_="check")
    for name in ("cart_dismissed_at", "capture_method", "checkout_methods_snapshot"):
        op.drop_column("provider_payment", name)
