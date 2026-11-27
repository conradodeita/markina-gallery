"""Persiste recibos sanitizados do backup PostgreSQL global."""

import sqlalchemy as sa
from alembic import op

revision = "20261127_0127"
down_revision = "20261113_0126"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Estado do backup PostgreSQL global requer PostgreSQL.")

    op.create_table(
        "global_postgresql_backup_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_day", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_id", sa.String(length=64), nullable=True),
        sa.Column("dump_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'validated', 'failed', 'unknown')",
            name="ck_global_postgresql_backup_run_status",
        ),
        sa.CheckConstraint(
            "dump_size_bytes IS NULL OR dump_size_bytes >= 0",
            name="ck_global_postgresql_backup_run_dump_size",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_global_postgresql_backup_run_duration",
        ),
        sa.CheckConstraint(
            "status != 'validated' OR "
            "(verified = true AND snapshot_id IS NOT NULL AND finished_at IS NOT NULL)",
            name="ck_global_postgresql_backup_run_verified",
        ),
        sa.CheckConstraint(
            "verified = false OR status = 'validated'",
            name="ck_global_postgresql_backup_run_no_unverified_success",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scheduled_day", name="uq_global_postgresql_backup_run_day"),
    )
    op.create_index(
        "ix_global_postgresql_backup_run_status_day",
        "global_postgresql_backup_run",
        ["status", "scheduled_day"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Rollback do estado de backup global requer PostgreSQL.")
    has_history = connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM global_postgresql_backup_run)")
    )
    if has_history:
        raise RuntimeError("Preserve histórico do backup global: downgrade recusado.")
    op.drop_index(
        "ix_global_postgresql_backup_run_status_day",
        table_name="global_postgresql_backup_run",
    )
    op.drop_table("global_postgresql_backup_run")
