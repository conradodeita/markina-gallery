"""Permite mais de uma compra Orders ativa quando as revisões diferem."""
import sqlalchemy as sa
from alembic import op

revision = "20261025_0089"
down_revision = "20261024_0088"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("uq_mp_active_client", table_name="mercadopago_payment")
    op.create_index(
        "uq_mp_active_client_revision", "mercadopago_payment",
        ["tenant_id", "client_id", "cart_revision"], unique=True,
        sqlite_where=sa.text("active = true"),
        postgresql_where=sa.text("active = true"),
    )


def downgrade():
    bind = op.get_bind()
    duplicates = bind.execute(sa.text(
        "SELECT 1 FROM mercadopago_payment WHERE active = true "
        "GROUP BY tenant_id, client_id HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicates:
        raise RuntimeError(
            "Downgrade recusado: há compras Orders ativas simultâneas que a unicidade antiga não preserva."
        )
    op.drop_index("uq_mp_active_client_revision", table_name="mercadopago_payment")
    op.create_index(
        "uq_mp_active_client", "mercadopago_payment", ["tenant_id", "client_id"], unique=True,
        sqlite_where=sa.text("active = true"),
        postgresql_where=sa.text("active = true"),
    )
