"""Endereço cifrado do pagador no perfil progressivo."""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0104"
down_revision = "20261104_0103"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Endereço de perfil requer PostgreSQL.")
    op.add_column(
        "photographer_business_profile",
        sa.Column("address_envelope", sa.String(2048), nullable=True),
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Endereço de perfil requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE photographer_business_profile IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM photographer_business_profile "
        "WHERE address_envelope IS NOT NULL LIMIT 1)"
    )):
        raise RuntimeError("Preserve endereços cadastrados: rollback recusado.")
    op.drop_column("photographer_business_profile", "address_envelope")
