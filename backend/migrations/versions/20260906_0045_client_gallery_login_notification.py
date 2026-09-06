"""Inclui notificação administrativa de login da cliente na galeria.

Revision ID: 20260906_0045
Revises: 20260906_0044
"""

from alembic import op

revision = "20260906_0045"
down_revision = "20260906_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table(
        "gallery_membership_notification_outbox", recreate="auto"
    ) as batch:
        batch.drop_constraint(
            "ck_gallery_membership_notification_type", type_="check"
        )
        batch.create_check_constraint(
            "ck_gallery_membership_notification_type",
            "event_type IN ('private_created', 'member_joined', 'member_blocked', "
            "'member_unblocked', 'member_unlinked', 'client_logged_in')",
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "gallery_membership_notification_outbox", recreate="auto"
    ) as batch:
        batch.drop_constraint(
            "ck_gallery_membership_notification_type", type_="check"
        )
        batch.create_check_constraint(
            "ck_gallery_membership_notification_type",
            "event_type IN ('private_created', 'member_joined', 'member_blocked', "
            "'member_unblocked', 'member_unlinked')",
        )
