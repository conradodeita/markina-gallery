"""Estado canônico da cliente e público explícito da pasta.

Revision ID: 20260926_0062
Revises: 20260925_0061
"""

import sqlalchemy as sa
from alembic import op

revision = "20260926_0062"
down_revision = "20260925_0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("photo_folder", recreate=recreate) as batch:
        batch.add_column(sa.Column("audience_scope", sa.String(16), nullable=True))
        batch.create_check_constraint(
            "ck_photo_folder_audience_scope",
            "audience_scope IS NULL OR audience_scope IN ('all', 'selected')",
        )
    op.execute(sa.text(
        "UPDATE photo_folder SET audience_scope = "
        "CASE WHEN derived_gallery_id IS NULL THEN 'all' ELSE 'selected' END"
    ))

    op.create_table(
        "gallery_client_state",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("parent_gallery_id", sa.Uuid(), sa.ForeignKey("parent_gallery.id"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("selection_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("parent_gallery_id", "client_id", name="uq_gallery_client_state_pair"),
        sa.CheckConstraint(
            "status IN ('active', 'blocked', 'unlinked')",
            name="ck_gallery_client_state_status",
        ),
    )
    op.create_index("ix_gallery_client_state_parent_gallery_id", "gallery_client_state", ["parent_gallery_id"])
    op.create_index("ix_gallery_client_state_client_id", "gallery_client_state", ["client_id"])

    op.create_table(
        "folder_client_grant",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("parent_gallery_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["folder_id", "parent_gallery_id"],
            ["photo_folder.id", "photo_folder.parent_gallery_id"],
            name="fk_folder_client_grant_folder_parent",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_gallery_id", "client_id"],
            ["gallery_client_state.parent_gallery_id", "gallery_client_state.client_id"],
            name="fk_folder_client_grant_client_state",
        ),
        sa.UniqueConstraint("folder_id", "client_id", name="uq_folder_client_grant_pair"),
    )
    for column in ("folder_id", "parent_gallery_id", "client_id"):
        op.create_index(f"ix_folder_client_grant_{column}", "folder_client_grant", [column])
    op.create_index(
        "ix_folder_client_grant_audience", "folder_client_grant", ["parent_gallery_id", "client_id"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM gallery_client_state")) or bind.scalar(
        sa.text("SELECT count(*) FROM folder_client_grant")
    ):
        raise RuntimeError("Há público ou estado canônico em uso; preserve o schema ao reverter.")
    op.drop_table("folder_client_grant")
    op.drop_table("gallery_client_state")
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("photo_folder", recreate=recreate) as batch:
        batch.drop_constraint("ck_photo_folder_audience_scope", type_="check")
        batch.drop_column("audience_scope")
