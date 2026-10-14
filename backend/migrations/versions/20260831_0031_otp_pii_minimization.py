"""Minimiza PII transitória dos desafios OTP.

Revision ID: 20260831_0031
Revises: 20260831_0030
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0031"
down_revision = "20260831_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("auth_challenge", recreate="always") as batch_op:
            batch_op.alter_column("subject", existing_type=sa.String(320), nullable=True)
            batch_op.add_column(sa.Column("subject_fingerprint", sa.String(64), nullable=True))
            batch_op.create_index("ix_auth_challenge_subject_fingerprint", ["subject_fingerprint"])
        with op.batch_alter_table("whatsapp_delivery", recreate="always") as batch_op:
            batch_op.alter_column("recipient_phone", existing_type=sa.String(16), nullable=True)
            batch_op.add_column(sa.Column("recipient_fingerprint", sa.String(64), nullable=True))
            batch_op.create_index(
                "ix_whatsapp_delivery_recipient_fingerprint", ["recipient_fingerprint"]
            )
    else:
        op.alter_column("auth_challenge", "subject", existing_type=sa.String(320), nullable=True)
        op.add_column(
            "auth_challenge", sa.Column("subject_fingerprint", sa.String(64), nullable=True)
        )
        op.create_index(
            "ix_auth_challenge_subject_fingerprint", "auth_challenge", ["subject_fingerprint"]
        )
        op.alter_column(
            "whatsapp_delivery", "recipient_phone", existing_type=sa.String(16), nullable=True
        )
        op.add_column(
            "whatsapp_delivery", sa.Column("recipient_fingerprint", sa.String(64), nullable=True)
        )
        op.create_index(
            "ix_whatsapp_delivery_recipient_fingerprint",
            "whatsapp_delivery",
            ["recipient_fingerprint"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    auth_challenge = sa.table(
        "auth_challenge",
        sa.column("id", sa.Uuid()),
        sa.column("subject", sa.String(320)),
    )
    whatsapp_delivery = sa.table(
        "whatsapp_delivery",
        sa.column("id", sa.Uuid()),
        sa.column("recipient_phone", sa.String(16)),
    )
    bind.execute(
        auth_challenge.update()
        .where(auth_challenge.c.subject.is_(None))
        .values(subject="minimized")
    )
    bind.execute(
        whatsapp_delivery.update()
        .where(whatsapp_delivery.c.recipient_phone.is_(None))
        .values(recipient_phone="minimized")
    )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("whatsapp_delivery", recreate="always") as batch_op:
            batch_op.drop_index("ix_whatsapp_delivery_recipient_fingerprint")
            batch_op.drop_column("recipient_fingerprint")
            batch_op.alter_column("recipient_phone", existing_type=sa.String(16), nullable=False)
        with op.batch_alter_table("auth_challenge", recreate="always") as batch_op:
            batch_op.drop_index("ix_auth_challenge_subject_fingerprint")
            batch_op.drop_column("subject_fingerprint")
            batch_op.alter_column("subject", existing_type=sa.String(320), nullable=False)
    else:
        op.drop_index("ix_whatsapp_delivery_recipient_fingerprint", table_name="whatsapp_delivery")
        op.drop_column("whatsapp_delivery", "recipient_fingerprint")
        op.alter_column(
            "whatsapp_delivery", "recipient_phone", existing_type=sa.String(16), nullable=False
        )
        op.drop_index("ix_auth_challenge_subject_fingerprint", table_name="auth_challenge")
        op.drop_column("auth_challenge", "subject_fingerprint")
        op.alter_column("auth_challenge", "subject", existing_type=sa.String(320), nullable=False)
