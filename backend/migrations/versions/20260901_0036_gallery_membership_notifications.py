"""Adiciona painel e outbox de notificações de membros.

Revision ID: 20260901_0036
Revises: 20260901_0035
"""

import sqlalchemy as sa
from alembic import op

revision = "20260901_0036"
down_revision = "20260901_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gallery_membership_notification_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_key", sa.String(length=200), nullable=False, unique=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column(
            "parent_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("parent_gallery.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "derived_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("derived_gallery.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "client_id",
            sa.Uuid(),
            sa.ForeignKey("client.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("parent_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("derived_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("client_name_snapshot", sa.String(length=200), nullable=True),
        sa.Column("admin_status", sa.String(length=16), nullable=False, server_default="unread"),
        sa.Column("external_status", sa.String(length=16), nullable=False, server_default="skipped"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=120), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('private_created', 'member_joined', 'member_blocked', "
            "'member_unblocked', 'member_unlinked')",
            name="ck_gallery_membership_notification_type",
        ),
        sa.CheckConstraint(
            "admin_status IN ('unread', 'read')",
            name="ck_gallery_membership_notification_admin_status",
        ),
        sa.CheckConstraint(
            "external_status IN ('skipped', 'queued', 'processing', 'sent', 'failed')",
            name="ck_gallery_membership_notification_external_status",
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_gallery_membership_notification_attempts",
        ),
    )
    for column in (
        "event_type",
        "parent_gallery_id",
        "derived_gallery_id",
        "client_id",
        "admin_status",
        "external_status",
        "next_attempt_at",
    ):
        op.create_index(
            f"ix_gallery_membership_notification_outbox_{column}",
            "gallery_membership_notification_outbox",
            [column],
        )
    op.create_index(
        "ix_gallery_membership_notification_admin_created",
        "gallery_membership_notification_outbox",
        ["admin_status", "created_at"],
    )
    op.create_index(
        "ix_gallery_membership_notification_external_next",
        "gallery_membership_notification_outbox",
        ["external_status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_table("gallery_membership_notification_outbox")
