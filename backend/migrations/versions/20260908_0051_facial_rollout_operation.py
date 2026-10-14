"""Adiciona recibo da operação protegida de rollout facial.

Revision ID: 20260908_0051
Revises: 20260908_0050
"""

import sqlalchemy as sa
from alembic import op

revision = "20260908_0051"
down_revision = "20260908_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "facial_rollout_operation",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("environment", sa.String(length=24), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("deployment_sha", sa.String(length=40), nullable=False),
        sa.Column("inventory_reference", sa.String(length=200), nullable=False),
        sa.Column("backup_reference", sa.String(length=200), nullable=False),
        sa.Column("gate_set_version", sa.String(length=80), nullable=False),
        sa.Column("allowlist_digest", sa.String(length=64), nullable=False),
        sa.Column("allowlist_count", sa.Integer(), nullable=False),
        sa.Column(
            "approved_by_admin_id",
            sa.Uuid(),
            sa.ForeignKey("admin_user.id"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "environment IN ('local', 'development', 'test', 'homolog', "
            "'staging', 'prod', 'production')",
            name="ck_facial_rollout_operation_environment",
        ),
        sa.CheckConstraint(
            "action IN ('activate', 'suspend')",
            name="ck_facial_rollout_operation_action",
        ),
        sa.CheckConstraint(
            "stage IN ('dark', 'canary', 'limited', 'general')",
            name="ck_facial_rollout_operation_stage",
        ),
        sa.CheckConstraint(
            "allowlist_count > 0",
            name="ck_facial_rollout_operation_allowlist",
        ),
    )
    for column in ("environment", "action", "stage", "approved_by_admin_id"):
        op.create_index(
            f"ix_facial_rollout_operation_{column}",
            "facial_rollout_operation",
            [column],
        )


def downgrade() -> None:
    op.drop_table("facial_rollout_operation")
