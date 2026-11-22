"""Separar reserva de hostname e prontidão sem alterar hosts legados."""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0105"
down_revision = "20261105_0104"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Reserva de hostname requer PostgreSQL.")
    op.add_column("tenant", sa.Column("canonical_host_status", sa.String(12), nullable=True))
    op.create_check_constraint(
        "ck_tenant_canonical_host_status", "tenant",
        "canonical_host_status IS NULL OR (canonical_host IS NOT NULL "
        "AND canonical_host_status IN ('reserved', 'ready'))",
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Reserva de hostname requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE tenant IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM tenant WHERE canonical_host_status IS NOT NULL LIMIT 1)"
    )):
        raise RuntimeError("Preserve reservas de hostname: rollback recusado.")
    op.drop_constraint("ck_tenant_canonical_host_status", "tenant", type_="check")
    op.drop_column("tenant", "canonical_host_status")
