"""Consolida PIX copia-e-cola como fonte do QR.

Revision ID: 20260901_0038
Revises: 20260901_0037
"""

import sqlalchemy as sa
from alembic import op

revision = "20260901_0038"
down_revision = "20260901_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column(
        "pix_checkout_settings",
        sa.Column(
            "review_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    rows = bind.execute(
        sa.text(
            "SELECT id, copy_paste, qr_code_payload FROM pix_checkout_settings"
        )
    ).mappings()
    for row in rows:
        copy_paste = row["copy_paste"].strip() if row["copy_paste"] else None
        qr_payload = row["qr_code_payload"].strip() if row["qr_code_payload"] else None
        if not copy_paste and qr_payload:
            bind.execute(
                sa.text(
                    "UPDATE pix_checkout_settings "
                    "SET copy_paste = :copy_paste, qr_code_payload = NULL "
                    "WHERE id = :id"
                ),
                {"copy_paste": qr_payload, "id": row["id"]},
            )
        elif copy_paste and qr_payload and copy_paste != qr_payload:
            bind.execute(
                sa.text(
                    "UPDATE pix_checkout_settings SET review_required = :required "
                    "WHERE id = :id"
                ),
                {"required": True, "id": row["id"]},
            )
        else:
            bind.execute(
                sa.text(
                    "UPDATE pix_checkout_settings SET qr_code_payload = NULL "
                    "WHERE id = :id"
                ),
                {"id": row["id"]},
            )


def downgrade() -> None:
    op.drop_column("pix_checkout_settings", "review_required")
