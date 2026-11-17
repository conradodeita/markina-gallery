"""Adicionar avisos internos tenant-scoped do arquivo frio."""

import sqlalchemy as sa
from alembic import op

revision = "20261109_0116"
down_revision = "20261109_0115"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Avisos de arquivo frio requerem PostgreSQL.")

    op.add_column(
        "media_archive_cycle",
        sa.Column("last_window_notice_for_expiry", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "media_archive_notice",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("notice_type", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=192), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.String(length=400), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "notice_type IN ('window_7_days', 'blocked_open_order', 'archive_started', "
            "'archive_completed', 'archive_failed', 'archive_reconciliation_required', "
            "'recovery_started', 'recovery_completed', 'recovery_failed', "
            "'recovery_reconciliation_required')",
            name="ck_media_archive_notice_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.id"], name="fk_media_archive_notice_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["cycle_id", "tenant_id"],
            ["media_archive_cycle.id", "media_archive_cycle.tenant_id"],
            name="fk_media_archive_notice_cycle_tenant",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_archive_notice"),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_media_archive_notice_idempotency",
        ),
    )
    op.create_index(
        "ix_media_archive_notice_tenant_id", "media_archive_notice", ["tenant_id"],
    )
    op.create_index(
        "ix_media_archive_notice_cycle_id", "media_archive_notice", ["cycle_id"],
    )
    op.create_index(
        "ix_media_archive_notice_tenant_created",
        "media_archive_notice", ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_media_archive_notice_tenant_read_created",
        "media_archive_notice", ["tenant_id", "read_at", "created_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Avisos de arquivo frio requerem PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE media_archive_cycle, media_archive_notice "
        "IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    has_notices = bind.scalar(sa.text(
        "SELECT EXISTS (SELECT 1 FROM media_archive_notice LIMIT 1)"
    ))
    if has_notices:
        raise RuntimeError("Preserve os avisos do fotógrafo: rollback recusado com dados.")
    op.drop_table("media_archive_notice")
    op.drop_column("media_archive_cycle", "last_window_notice_for_expiry")
