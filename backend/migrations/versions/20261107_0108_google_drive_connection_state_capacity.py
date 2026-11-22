"""Ampliar estado Drive sem reescrever conexões ou envelopes existentes."""

import sqlalchemy as sa
from alembic import op

revision = "20261107_0108"
down_revision = "20261107_0107"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Capacidade do estado Drive requer PostgreSQL.")
    op.alter_column("google_drive_connection", "state", existing_type=sa.String(16),
                    type_=sa.String(32), existing_nullable=False)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Capacidade do estado Drive requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE google_drive_connection IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM google_drive_connection WHERE length(state)>16 LIMIT 1)"
    )):
        raise RuntimeError("Preserve estados Drive: rollback recusado com estado maior que 16 caracteres.")
    op.alter_column("google_drive_connection", "state", existing_type=sa.String(32),
                    type_=sa.String(16), existing_nullable=False)
