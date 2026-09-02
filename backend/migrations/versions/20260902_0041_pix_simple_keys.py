"""Permite editar PIX por BR Code ou chave simples estruturada.

Revision ID: 20260902_0041
Revises: 20260901_0040
"""

import sqlalchemy as sa
from alembic import op

revision = "20260902_0041"
down_revision = "20260901_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pix_checkout_settings") as batch:
        batch.add_column(sa.Column("input_type", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("pix_key", sa.String(length=160), nullable=True))
        batch.add_column(sa.Column("receiver_name", sa.String(length=25), nullable=True))
        batch.add_column(sa.Column("receiver_city", sa.String(length=15), nullable=True))
        batch.create_check_constraint(
            "ck_pix_checkout_settings_input_type",
            "input_type IS NULL OR input_type IN ('br_code', 'cpf', 'phone', 'email')",
        )
    op.execute(
        sa.text(
            "UPDATE pix_checkout_settings SET input_type = 'br_code' "
            "WHERE copy_paste IS NOT NULL"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("pix_checkout_settings") as batch:
        batch.drop_constraint(
            "ck_pix_checkout_settings_input_type",
            type_="check",
        )
        batch.drop_column("receiver_city")
        batch.drop_column("receiver_name")
        batch.drop_column("pix_key")
        batch.drop_column("input_type")
