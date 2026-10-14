"""Adiciona modos e capacidades opacas de acesso às galerias.

Revision ID: 20260831_0023
Revises: 20260831_0022
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0023"
down_revision = "20260831_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("parent_gallery", recreate="always") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "access_mode",
                    sa.String(length=24),
                    nullable=False,
                    server_default="invite_only",
                )
            )
            batch_op.create_check_constraint(
                "ck_parent_gallery_access_mode",
                "access_mode IN ('standard', 'invite_only', 'collective_protected')",
            )
    else:
        op.add_column(
            "parent_gallery",
            sa.Column(
                "access_mode",
                sa.String(length=24),
                nullable=False,
                server_default="invite_only",
            ),
        )
        op.create_check_constraint(
            "ck_parent_gallery_access_mode",
            "parent_gallery",
            "access_mode IN ('standard', 'invite_only', 'collective_protected')",
        )

    op.create_table(
        "gallery_access_capability",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "parent_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("parent_gallery.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "derived_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("derived_gallery.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=True),
        sa.Column("scope", sa.String(length=24), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "rotated_from_id",
            sa.Uuid(),
            sa.ForeignKey("gallery_access_capability.id"),
            nullable=True,
        ),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "token_hash", name="uq_gallery_access_capability_token_hash"
        ),
        sa.CheckConstraint(
            "scope IN ('public_gallery', 'parent_invite', 'private_invite')",
            name="ck_gallery_access_capability_scope",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'consumed', 'revoked', 'rotated', 'expired')",
            name="ck_gallery_access_capability_status",
        ),
        sa.CheckConstraint(
            "length(token_hash) = 64",
            name="ck_gallery_access_capability_token_hash",
        ),
        sa.CheckConstraint(
            "(scope = 'public_gallery' AND client_id IS NULL AND derived_gallery_id IS NULL) OR "
            "(scope = 'parent_invite' AND client_id IS NOT NULL AND derived_gallery_id IS NULL) OR "
            "(scope = 'private_invite' AND client_id IS NOT NULL AND derived_gallery_id IS NOT NULL)",
            name="ck_gallery_access_capability_target",
        ),
    )
    for column in (
        "parent_gallery_id",
        "derived_gallery_id",
        "client_id",
        "scope",
        "status",
        "rotated_from_id",
        "actor_admin_id",
    ):
        op.create_index(
            f"ix_gallery_access_capability_{column}",
            "gallery_access_capability",
            [column],
        )
    op.create_index(
        "ix_gallery_access_capability_parent_status",
        "gallery_access_capability",
        ["parent_gallery_id", "status"],
    )
    op.create_index(
        "uq_gallery_access_capability_active_public",
        "gallery_access_capability",
        ["parent_gallery_id"],
        unique=True,
        sqlite_where=sa.text("scope = 'public_gallery' AND status = 'active'"),
        postgresql_where=sa.text("scope = 'public_gallery' AND status = 'active'"),
    )
    op.create_index(
        "uq_gallery_access_capability_active_invite",
        "gallery_access_capability",
        ["parent_gallery_id", "client_id", "scope"],
        unique=True,
        sqlite_where=sa.text("scope <> 'public_gallery' AND status = 'active'"),
        postgresql_where=sa.text("scope <> 'public_gallery' AND status = 'active'"),
    )


def downgrade() -> None:
    op.drop_table("gallery_access_capability")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("parent_gallery", recreate="always") as batch_op:
            batch_op.drop_constraint("ck_parent_gallery_access_mode", type_="check")
            batch_op.drop_column("access_mode")
    else:
        op.drop_constraint(
            "ck_parent_gallery_access_mode", "parent_gallery", type_="check"
        )
        op.drop_column("parent_gallery", "access_mode")
