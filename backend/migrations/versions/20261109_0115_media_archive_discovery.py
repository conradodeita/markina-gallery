"""Persistir a próxima rechecagem de pastas elegíveis ao arquivo frio."""

import sqlalchemy as sa
from alembic import op

revision = "20261109_0115"
down_revision = "20261109_0114"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Descoberta de arquivo frio requer PostgreSQL.")
    op.add_column(
        "media_archive_cycle",
        sa.Column("next_archive_check_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_media_archive_cycle_state_next_check",
        "media_archive_cycle",
        ["state", "next_archive_check_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Descoberta de arquivo frio requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE media_archive_cycle IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    has_pending_checks = bind.scalar(sa.text(
        "SELECT EXISTS (SELECT 1 FROM media_archive_cycle "
        "WHERE next_archive_check_at IS NOT NULL LIMIT 1)"
    ))
    if has_pending_checks:
        raise RuntimeError("Preserve os horários de rechecagem: rollback recusado com dados.")
    op.drop_index("ix_media_archive_cycle_state_next_check", table_name="media_archive_cycle")
    op.drop_column("media_archive_cycle", "next_archive_check_at")
