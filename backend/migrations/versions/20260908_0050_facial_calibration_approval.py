"""Adiciona aprovação humana de calibração facial para produção.

Revision ID: 20260908_0050
Revises: 20260908_0049
"""

import sqlalchemy as sa
from alembic import op

revision = "20260908_0050"
down_revision = "20260908_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "facial_calibration_approval",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("environment", sa.String(length=24), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.Column("quality_version", sa.String(length=120), nullable=False),
        sa.Column("calibration_version", sa.String(length=120), nullable=False),
        sa.Column("similarity_threshold_milli", sa.Integer(), nullable=False),
        sa.Column("criteria_version", sa.String(length=80), nullable=False),
        sa.Column("corpus_reference", sa.String(length=200), nullable=False),
        sa.Column("approval_reference", sa.String(length=200), nullable=False),
        sa.Column("relevant_group_count", sa.Integer(), nullable=False),
        sa.Column("approved_group_count", sa.Integer(), nullable=False),
        sa.Column(
            "approved_by_admin_id",
            sa.Uuid(),
            sa.ForeignKey("admin_user.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "environment IN ('prod', 'production')",
            name="ck_facial_calibration_environment",
        ),
        sa.CheckConstraint(
            "status IN ('approved', 'revoked')",
            name="ck_facial_calibration_status",
        ),
        sa.CheckConstraint(
            "similarity_threshold_milli BETWEEN 0 AND 1000",
            name="ck_facial_calibration_threshold",
        ),
        sa.CheckConstraint(
            "relevant_group_count > 0 AND approved_group_count = relevant_group_count",
            name="ck_facial_calibration_groups",
        ),
    )
    op.create_index(
        "ix_facial_calibration_approval_environment",
        "facial_calibration_approval",
        ["environment"],
    )
    op.create_index(
        "ix_facial_calibration_approval_approved_by_admin_id",
        "facial_calibration_approval",
        ["approved_by_admin_id"],
    )
    op.create_index(
        "ix_facial_calibration_approval_status",
        "facial_calibration_approval",
        ["status"],
    )
    op.create_index(
        "ix_facial_calibration_effective",
        "facial_calibration_approval",
        [
            "environment",
            "model_version",
            "quality_version",
            "calibration_version",
            "status",
        ],
    )


def downgrade() -> None:
    op.drop_table("facial_calibration_approval")
