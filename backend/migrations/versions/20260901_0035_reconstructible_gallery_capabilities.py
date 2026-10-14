"""Versiona capacidades e adiciona link privado reutilizável.

Revision ID: 20260901_0035
Revises: 20260901_0034
"""

import sqlalchemy as sa
from alembic import op

revision = "20260901_0035"
down_revision = "20260901_0034"
branch_labels = None
depends_on = None

SCOPES = (
    "scope IN ('public_gallery', 'parent_invite', 'private_invite', "
    "'private_gallery_link', 'private_client_invite')"
)
TARGETS = (
    "(scope = 'public_gallery' AND client_id IS NULL AND derived_gallery_id IS NULL) OR "
    "(scope = 'parent_invite' AND client_id IS NOT NULL AND derived_gallery_id IS NULL) OR "
    "(scope IN ('private_invite', 'private_client_invite') "
    "AND client_id IS NOT NULL AND derived_gallery_id IS NOT NULL) OR "
    "(scope = 'private_gallery_link' AND client_id IS NULL "
    "AND derived_gallery_id IS NOT NULL)"
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "gallery_access_capability", recreate="always"
        ) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "token_mode",
                    sa.String(length=24),
                    nullable=False,
                    server_default="legacy_random",
                )
            )
            batch_op.add_column(
                sa.Column(
                    "token_version",
                    sa.Integer(),
                    nullable=False,
                    server_default="1",
                )
            )
            batch_op.drop_constraint(
                "ck_gallery_access_capability_scope", type_="check"
            )
            batch_op.drop_constraint(
                "ck_gallery_access_capability_target", type_="check"
            )
            batch_op.create_check_constraint(
                "ck_gallery_access_capability_scope", SCOPES
            )
            batch_op.create_check_constraint(
                "ck_gallery_access_capability_target", TARGETS
            )
            batch_op.create_check_constraint(
                "ck_gallery_access_capability_token_mode",
                "token_mode IN ('legacy_random', 'signed_v1')",
            )
            batch_op.create_check_constraint(
                "ck_gallery_access_capability_token_version",
                "token_version >= 1",
            )
    else:
        op.add_column(
            "gallery_access_capability",
            sa.Column(
                "token_mode",
                sa.String(length=24),
                nullable=False,
                server_default="legacy_random",
            ),
        )
        op.add_column(
            "gallery_access_capability",
            sa.Column(
                "token_version", sa.Integer(), nullable=False, server_default="1"
            ),
        )
        op.drop_constraint(
            "ck_gallery_access_capability_scope",
            "gallery_access_capability",
            type_="check",
        )
        op.drop_constraint(
            "ck_gallery_access_capability_target",
            "gallery_access_capability",
            type_="check",
        )
        op.create_check_constraint(
            "ck_gallery_access_capability_scope",
            "gallery_access_capability",
            SCOPES,
        )
        op.create_check_constraint(
            "ck_gallery_access_capability_target",
            "gallery_access_capability",
            TARGETS,
        )
        op.create_check_constraint(
            "ck_gallery_access_capability_token_mode",
            "gallery_access_capability",
            "token_mode IN ('legacy_random', 'signed_v1')",
        )
        op.create_check_constraint(
            "ck_gallery_access_capability_token_version",
            "gallery_access_capability",
            "token_version >= 1",
        )
    op.create_index(
        "uq_gallery_access_capability_active_private_link",
        "gallery_access_capability",
        ["derived_gallery_id"],
        unique=True,
        sqlite_where=sa.text("scope = 'private_gallery_link' AND status = 'active'"),
        postgresql_where=sa.text("scope = 'private_gallery_link' AND status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_gallery_access_capability_active_private_link",
        table_name="gallery_access_capability",
    )
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "gallery_access_capability", recreate="always"
        ) as batch_op:
            batch_op.drop_constraint(
                "ck_gallery_access_capability_token_version", type_="check"
            )
            batch_op.drop_constraint(
                "ck_gallery_access_capability_token_mode", type_="check"
            )
            batch_op.drop_constraint(
                "ck_gallery_access_capability_target", type_="check"
            )
            batch_op.drop_constraint(
                "ck_gallery_access_capability_scope", type_="check"
            )
            batch_op.create_check_constraint(
                "ck_gallery_access_capability_scope",
                "scope IN ('public_gallery', 'parent_invite', 'private_invite')",
            )
            batch_op.create_check_constraint(
                "ck_gallery_access_capability_target",
                "(scope = 'public_gallery' AND client_id IS NULL "
                "AND derived_gallery_id IS NULL) OR "
                "(scope = 'parent_invite' AND client_id IS NOT NULL "
                "AND derived_gallery_id IS NULL) OR "
                "(scope = 'private_invite' AND client_id IS NOT NULL "
                "AND derived_gallery_id IS NOT NULL)",
            )
            batch_op.drop_column("token_version")
            batch_op.drop_column("token_mode")
    else:
        op.drop_constraint(
            "ck_gallery_access_capability_token_version",
            "gallery_access_capability",
            type_="check",
        )
        op.drop_constraint(
            "ck_gallery_access_capability_token_mode",
            "gallery_access_capability",
            type_="check",
        )
        op.drop_constraint(
            "ck_gallery_access_capability_target",
            "gallery_access_capability",
            type_="check",
        )
        op.drop_constraint(
            "ck_gallery_access_capability_scope",
            "gallery_access_capability",
            type_="check",
        )
        op.create_check_constraint(
            "ck_gallery_access_capability_scope",
            "gallery_access_capability",
            "scope IN ('public_gallery', 'parent_invite', 'private_invite')",
        )
        op.create_check_constraint(
            "ck_gallery_access_capability_target",
            "gallery_access_capability",
            "(scope = 'public_gallery' AND client_id IS NULL "
            "AND derived_gallery_id IS NULL) OR "
            "(scope = 'parent_invite' AND client_id IS NOT NULL "
            "AND derived_gallery_id IS NULL) OR "
            "(scope = 'private_invite' AND client_id IS NOT NULL "
            "AND derived_gallery_id IS NOT NULL)",
        )
        op.drop_column("gallery_access_capability", "token_version")
        op.drop_column("gallery_access_capability", "token_mode")
