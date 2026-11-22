"""Lote de recuperação de conta e isenção específica para capa técnica."""

import sqlalchemy as sa
from alembic import op

revision = "20261109_0118"
down_revision = "20261109_0117"
branch_labels = None
depends_on = None

_OLD_ACTOR = (
    "(requester_type = 'tenant' AND requested_by_tenant_admin_id = requested_by_admin_id "
    "AND requested_by_owner_admin_id IS NULL AND retry_of_operation_id IS NULL) OR "
    "(requester_type = 'owner' AND requested_by_tenant_admin_id IS NULL "
    "AND requested_by_owner_admin_id = requested_by_admin_id AND retry_of_operation_id IS NOT NULL)"
)
_NEW_ACTOR = (
    "(requester_type = 'tenant' AND requested_by_tenant_admin_id = requested_by_admin_id "
    "AND requested_by_owner_admin_id IS NULL AND retry_of_operation_id IS NULL AND closure_batch_id IS NULL) OR "
    "(requester_type = 'owner' AND requested_by_tenant_admin_id IS NULL "
    "AND requested_by_owner_admin_id = requested_by_admin_id "
    "AND (retry_of_operation_id IS NOT NULL OR closure_batch_id IS NOT NULL))"
)
_OLD_FEE = "(owner_exempt AND fee_credits_snapshot IS NULL) OR (NOT owner_exempt AND fee_credits_snapshot IS NOT NULL)"
_NEW_FEE = (
    "((owner_exempt OR technical_cover_exempt) AND fee_credits_snapshot IS NULL) OR "
    "(NOT owner_exempt AND NOT technical_cover_exempt AND fee_credits_snapshot IS NOT NULL)"
)


def _constraints(actor, fee):
    table = "media_archive_recovery_request"
    op.drop_constraint("ck_media_archive_recovery_request_actor_shape", table, type_="check")
    op.drop_constraint("ck_media_archive_recovery_fee_shape", table, type_="check")
    op.create_check_constraint("ck_media_archive_recovery_request_actor_shape", table, actor)
    op.create_check_constraint("ck_media_archive_recovery_fee_shape", table, fee)


def upgrade() -> None:
    op.create_table(
        "tenant_closure_recovery_batch",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("closure_request_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_owner_admin_id", sa.Uuid(), sa.ForeignKey("platform_owner.admin_user_id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id", "tenant_id", name="uq_closure_recovery_batch_owner"),
        sa.UniqueConstraint("tenant_id", "request_id", name="uq_closure_recovery_batch_key"),
        sa.ForeignKeyConstraint(["closure_request_id", "tenant_id"],
                                ["tenant_closure_request.id", "tenant_closure_request.tenant_id"],
                                name="fk_closure_recovery_batch_closure"),
        sa.CheckConstraint("duration_days IN (7, 14, 30)", name="ck_closure_recovery_batch_duration"),
    )
    op.create_index("ix_tenant_closure_recovery_batch_tenant_id", "tenant_closure_recovery_batch", ["tenant_id"])
    op.create_table(
        "tenant_closure_recovery_item",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.UniqueConstraint("batch_id", "cycle_id", name="uq_closure_recovery_item_cycle"),
        sa.ForeignKeyConstraint(["batch_id", "tenant_id"],
                                ["tenant_closure_recovery_batch.id", "tenant_closure_recovery_batch.tenant_id"],
                                name="fk_closure_recovery_item_batch"),
        sa.ForeignKeyConstraint(["operation_id", "cycle_id", "tenant_id"],
                                ["media_archive_operation.id", "media_archive_operation.cycle_id", "media_archive_operation.tenant_id"],
                                name="fk_closure_recovery_item_operation"),
    )
    op.create_index("ix_tenant_closure_recovery_item_tenant_id", "tenant_closure_recovery_item", ["tenant_id"])
    op.create_index("ix_tenant_closure_recovery_item_batch_id", "tenant_closure_recovery_item", ["batch_id"])
    table = "media_archive_recovery_request"
    op.add_column(table, sa.Column("closure_batch_id", sa.Uuid(), nullable=True))
    op.add_column(table, sa.Column("technical_cover_exempt", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_foreign_key("fk_archive_recovery_closure_batch", table, "tenant_closure_recovery_batch",
                          ["closure_batch_id", "tenant_id"], ["id", "tenant_id"])
    _constraints(_NEW_ACTOR, _NEW_FEE)
    op.create_check_constraint("ck_archive_recovery_cover_exemption", table,
                                "NOT technical_cover_exempt OR (closure_batch_id IS NOT NULL AND NOT owner_exempt)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Recuperação em lote requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE media_archive_recovery_request, tenant_closure_recovery_batch, "
        "tenant_closure_recovery_item IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM tenant_closure_recovery_batch)")):
        raise RuntimeError("Preserve histórico de recuperação da conta: rollback recusado.")
    table = "media_archive_recovery_request"
    op.drop_constraint("ck_archive_recovery_cover_exemption", table, type_="check")
    _constraints(_OLD_ACTOR, _OLD_FEE)
    op.drop_constraint("fk_archive_recovery_closure_batch", table, type_="foreignkey")
    op.drop_column(table, "technical_cover_exempt")
    op.drop_column(table, "closure_batch_id")
    op.drop_table("tenant_closure_recovery_item")
    op.drop_table("tenant_closure_recovery_batch")
