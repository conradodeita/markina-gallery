"""Adiciona rollout facial persistente por ambiente e galeria.

Revision ID: 20260908_0048
Revises: 20260907_0047
"""

import sqlalchemy as sa
from alembic import op

revision = "20260908_0048"
down_revision = "20260907_0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "facial_rollout",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("environment", sa.String(length=24), nullable=False),
        sa.Column(
            "parent_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("parent_gallery.id"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="prepared"
        ),
        sa.Column("stage", sa.String(length=16), nullable=False, server_default="dark"),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.Column("quality_version", sa.String(length=120), nullable=False),
        sa.Column("calibration_version", sa.String(length=120), nullable=False),
        sa.Column("legal_notice_version", sa.String(length=80), nullable=False),
        sa.Column("consent_version", sa.String(length=80), nullable=False),
        sa.Column("legal_basis_reference", sa.String(length=200), nullable=False),
        sa.Column("retention_policy_version", sa.String(length=80), nullable=False),
        sa.Column("approval_reference", sa.String(length=200), nullable=True),
        sa.Column(
            "approved_by_admin_id",
            sa.Uuid(),
            sa.ForeignKey("admin_user.id"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "environment",
            "parent_gallery_id",
            name="uq_facial_rollout_environment_gallery",
        ),
        sa.CheckConstraint(
            "environment IN ('local', 'development', 'test', 'homolog', "
            "'staging', 'prod', 'production')",
            name="ck_facial_rollout_environment",
        ),
        sa.CheckConstraint(
            "status IN ('prepared', 'active', 'suspended', 'revoked')",
            name="ck_facial_rollout_status",
        ),
        sa.CheckConstraint(
            "stage IN ('dark', 'canary', 'limited', 'general')",
            name="ck_facial_rollout_stage",
        ),
    )
    op.create_index(
        "ix_facial_rollout_environment",
        "facial_rollout",
        ["environment"],
    )
    op.create_index(
        "ix_facial_rollout_parent_gallery_id",
        "facial_rollout",
        ["parent_gallery_id"],
    )
    op.create_index("ix_facial_rollout_status", "facial_rollout", ["status"])
    op.create_index("ix_facial_rollout_stage", "facial_rollout", ["stage"])
    op.create_index(
        "ix_facial_rollout_approved_by_admin_id",
        "facial_rollout",
        ["approved_by_admin_id"],
    )
    op.create_index(
        "ix_facial_rollout_environment_status",
        "facial_rollout",
        ["environment", "status"],
    )


def downgrade() -> None:
    op.drop_table("facial_rollout")
