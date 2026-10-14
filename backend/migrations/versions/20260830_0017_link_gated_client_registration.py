"""Persiste nome temporário para cadastro de cliente condicionado ao link.

Revision ID: 20260830_0017
Revises: 20260830_0016
"""

import sqlalchemy as sa
from alembic import op

revision = "20260830_0017"
down_revision = "20260830_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_challenge",
        sa.Column("client_name", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("auth_challenge", "client_name")
