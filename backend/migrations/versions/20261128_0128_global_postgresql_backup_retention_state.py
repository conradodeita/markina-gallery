"""Persiste o estado verificado da retenção do backup global."""

import sqlalchemy as sa
from alembic import op

revision = "20261128_0128"
down_revision = "20261127_0127"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Estado de retenção do backup global requer PostgreSQL.")
    op.add_column(
        "global_postgresql_backup_run",
        sa.Column(
            "retention_status",
            sa.String(length=12),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.create_check_constraint(
        "ck_global_postgresql_backup_run_retention_status",
        "global_postgresql_backup_run",
        "retention_status IN ('unknown', 'pending', 'complete', 'failed')",
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Rollback do estado de retenção requer PostgreSQL.")
    connection.exec_driver_sql(
        "LOCK TABLE global_postgresql_backup_run IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    has_retention_history = connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM global_postgresql_backup_run "
            "WHERE retention_status != 'unknown')"
        )
    )
    if has_retention_history:
        raise RuntimeError("Preserve estados de retenção do backup global: downgrade recusado.")
    op.drop_constraint(
        "ck_global_postgresql_backup_run_retention_status",
        "global_postgresql_backup_run",
        type_="check",
    )
    op.drop_column("global_postgresql_backup_run", "retention_status")
