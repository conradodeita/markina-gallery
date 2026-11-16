"""Registrar a declaração de maioridade no cadastro de fotógrafos."""

import sqlalchemy as sa
from alembic import op

revision = "20261107_0109"
down_revision = "20261107_0108"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Declaração de maioridade requer PostgreSQL.")
    op.add_column(
        "photographer_signup",
        sa.Column("adult_attested_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Declaração de maioridade requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE photographer_signup IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM photographer_signup WHERE adult_attested_at IS NOT NULL LIMIT 1)"
    )):
        raise RuntimeError("Preserve declarações de maioridade registradas: rollback recusado.")
    op.drop_column("photographer_signup", "adult_attested_at")
