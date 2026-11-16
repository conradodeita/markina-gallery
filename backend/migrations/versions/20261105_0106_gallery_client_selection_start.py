"""Persistir o início do carrinho atual sem inventar histórico legado."""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0106"
down_revision = "20261105_0105"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "gallery_client_state",
        sa.Column("selection_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Início de seleção requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE gallery_client_state IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM gallery_client_state "
        "WHERE selection_started_at IS NOT NULL LIMIT 1)"
    )):
        raise RuntimeError("Preserve horários de início de seleção: rollback recusado.")
    op.drop_column("gallery_client_state", "selection_started_at")
