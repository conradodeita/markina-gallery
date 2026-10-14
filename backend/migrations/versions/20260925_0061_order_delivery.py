"""Link de entrega e geração de autorização por pedido."""

import sqlalchemy as sa
from alembic import op

revision = "20260925_0061"
down_revision = "20260921_0060"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sale_order") as batch:
        batch.add_column(sa.Column("delivery_album_url", sa.String(2048), nullable=True))
        batch.add_column(sa.Column("delivery_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("delivery_revision", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM sale_order WHERE delivery_revision <> 0 OR delivery_album_url IS NOT NULL")):
        raise RuntimeError("Há entregas registradas. Preserve o schema ao reverter a aplicação.")
    with op.batch_alter_table("sale_order") as batch:
        batch.drop_column("delivery_revision")
        batch.drop_column("delivery_updated_at")
        batch.drop_column("delivery_album_url")
