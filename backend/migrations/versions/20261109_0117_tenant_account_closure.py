"""Lifecycle aditivo e histórico de encerramento voluntário do tenant."""

import sqlalchemy as sa
from alembic import op

revision = "20261109_0117"
down_revision = "20261109_0116"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Lifecycle requer PostgreSQL.")
    op.add_column("tenant", sa.Column("lifecycle", sa.String(16), server_default="open", nullable=False))
    op.create_check_constraint("ck_tenant_lifecycle", "tenant", "lifecycle IN ('open', 'closing', 'closed')")
    op.create_table(
        "tenant_closure_request",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("admin_user.id"), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("reopened_at", sa.DateTime(timezone=True)),
        sa.Column("terms_version", sa.String(80), nullable=False),
        sa.Column("terms_sha256", sa.String(64), nullable=False),
        sa.Column("balance_snapshot", sa.BigInteger(), nullable=False),
        sa.Column("balance_acknowledged", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("tenant_id", "request_id", name="uq_tenant_closure_request_key"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_tenant_closure_request_owner"),
        sa.CheckConstraint("state IN ('closing', 'closed', 'reopened')", name="ck_tenant_closure_state"),
        sa.CheckConstraint("balance_snapshot >= 0", name="ck_tenant_closure_balance"),
        sa.CheckConstraint("state = 'closing' OR closed_at IS NOT NULL", name="ck_tenant_closure_closed_at"),
        sa.CheckConstraint("state != 'reopened' OR reopened_at IS NOT NULL", name="ck_tenant_closure_reopened_at"),
    )
    op.create_index("ix_tenant_closure_request_tenant_id", "tenant_closure_request", ["tenant_id"])
    op.create_index("uq_tenant_closure_pending", "tenant_closure_request", ["tenant_id"],
                    unique=True, postgresql_where=sa.text("state = 'closing'"))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Lifecycle requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE tenant, tenant_closure_request IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM tenant_closure_request)")):
        raise RuntimeError("Preserve histórico de encerramento: rollback recusado com dados.")
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM tenant WHERE lifecycle != 'open')")):
        raise RuntimeError("Preserve lifecycle: rollback recusado com conta em encerramento.")
    op.drop_table("tenant_closure_request")
    op.drop_constraint("ck_tenant_lifecycle", "tenant", type_="check")
    op.drop_column("tenant", "lifecycle")
