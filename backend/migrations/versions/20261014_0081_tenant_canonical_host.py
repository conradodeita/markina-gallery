"""Add canonical public host per tenant for customer purchase links."""

import sqlalchemy as sa
from alembic import op

revision = "20261014_0081"
down_revision = "20261014_0080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tenant") as batch:
        batch.add_column(sa.Column("canonical_host", sa.String(length=253), nullable=True))
        batch.create_unique_constraint("uq_tenant_canonical_host", ["canonical_host"])
        batch.create_check_constraint(
            "ck_tenant_canonical_host",
            "canonical_host IS NULL OR (canonical_host = lower(canonical_host) "
            "AND length(canonical_host) BETWEEN 1 AND 253 "
            "AND canonical_host NOT LIKE '%/%' AND canonical_host NOT LIKE '%:%')",
        )
    op.execute(sa.text(
        "UPDATE notification_setting "
        "SET whatsapp_body = 'Suas fotos estão prontas! Acesse {{link_compras}} para abrir seu álbum.' "
        "WHERE event_type = 'order_delivery_ready' "
        "AND whatsapp_body = 'Suas fotos estão prontas! Acesse Compras para abrir seu álbum.'"
    ))


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM tenant WHERE canonical_host IS NOT NULL")):
        raise RuntimeError("Downgrade recusado: preserve os hostnames canônicos dos fotógrafos.")
    op.execute(sa.text(
        "UPDATE notification_setting "
        "SET whatsapp_body = 'Suas fotos estão prontas! Acesse Compras para abrir seu álbum.' "
        "WHERE event_type = 'order_delivery_ready' "
        "AND whatsapp_body = 'Suas fotos estão prontas! Acesse {{link_compras}} para abrir seu álbum.'"
    ))
    with op.batch_alter_table("tenant") as batch:
        batch.drop_constraint("ck_tenant_canonical_host", type_="check")
        batch.drop_constraint("uq_tenant_canonical_host", type_="unique")
        batch.drop_column("canonical_host")
