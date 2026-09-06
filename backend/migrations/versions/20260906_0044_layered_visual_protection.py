"""Amplia a proteção visual global com controles em camadas.

Revision ID: 20260906_0044
Revises: 20260905_0043
"""

import sqlalchemy as sa
from alembic import op

revision = "20260906_0044"
down_revision = "20260905_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("branding_settings", recreate="auto") as batch:
        batch.add_column(
            sa.Column("watermark_opacity", sa.Integer(), nullable=False, server_default="42")
        )
        batch.add_column(
            sa.Column(
                "watermark_position",
                sa.String(length=24),
                nullable=False,
                server_default="middle-center",
            )
        )
        batch.add_column(
            sa.Column("watermark_shadow", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.add_column(
            sa.Column(
                "watermark_security_lines",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.create_check_constraint(
            "ck_branding_watermark_opacity", "watermark_opacity BETWEEN 10 AND 100"
        )
        batch.create_check_constraint(
            "ck_branding_watermark_position",
            "watermark_position IN ('top-left', 'top-center', 'top-right', "
            "'middle-left', 'middle-center', 'middle-right', "
            "'bottom-left', 'bottom-center', 'bottom-right')",
        )


def downgrade() -> None:
    with op.batch_alter_table("branding_settings", recreate="auto") as batch:
        batch.drop_constraint("ck_branding_watermark_position", type_="check")
        batch.drop_constraint("ck_branding_watermark_opacity", type_="check")
        batch.drop_column("watermark_security_lines")
        batch.drop_column("watermark_shadow")
        batch.drop_column("watermark_position")
        batch.drop_column("watermark_opacity")
