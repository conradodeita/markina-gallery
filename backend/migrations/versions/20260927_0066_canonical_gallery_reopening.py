"""Permite pedir reabertura pelo par galeria canônica e cliente.

Revision ID: 20260927_0066
Revises: 20260926_0065
"""

import sqlalchemy as sa
from alembic import op

revision = "20260927_0066"
down_revision = "20260926_0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("gallery_reopening_request", recreate=recreate) as batch:
        batch.add_column(sa.Column("parent_gallery_id", sa.Uuid(), nullable=True))
        batch.alter_column("derived_gallery_id", existing_type=sa.Uuid(), nullable=True)
        batch.create_foreign_key(
            "fk_gallery_reopening_parent", "parent_gallery",
            ["parent_gallery_id"], ["id"], ondelete="CASCADE",
        )
        batch.create_foreign_key(
            "fk_gallery_reopening_canonical_state", "gallery_client_state",
            ["parent_gallery_id", "requested_by_client_id"],
            ["parent_gallery_id", "client_id"],
        )
        batch.create_unique_constraint(
            "uq_gallery_reopening_canonical_idempotency",
            ["parent_gallery_id", "requested_by_client_id", "idempotency_key"],
        )
        batch.create_check_constraint(
            "ck_gallery_reopening_single_scope",
            "(derived_gallery_id IS NOT NULL) <> (parent_gallery_id IS NOT NULL)",
        )
    op.create_index(
        "ix_gallery_reopening_request_parent_gallery_id",
        "gallery_reopening_request", ["parent_gallery_id"],
    )
    op.create_index(
        "uq_gallery_reopening_canonical_pending", "gallery_reopening_request",
        ["parent_gallery_id", "requested_by_client_id"], unique=True,
        sqlite_where=sa.text("parent_gallery_id IS NOT NULL AND status = 'pending'"),
        postgresql_where=sa.text("parent_gallery_id IS NOT NULL AND status = 'pending'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text(
        "SELECT count(*) FROM gallery_reopening_request WHERE parent_gallery_id IS NOT NULL "
        "OR derived_gallery_id IS NULL"
    )):
        raise RuntimeError("Há solicitações canônicas. Preserve o schema ao reverter.")
    op.drop_index("uq_gallery_reopening_canonical_pending", table_name="gallery_reopening_request")
    op.drop_index("ix_gallery_reopening_request_parent_gallery_id", table_name="gallery_reopening_request")
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("gallery_reopening_request", recreate=recreate) as batch:
        batch.drop_constraint("ck_gallery_reopening_single_scope", type_="check")
        batch.drop_constraint("uq_gallery_reopening_canonical_idempotency", type_="unique")
        batch.drop_constraint("fk_gallery_reopening_canonical_state", type_="foreignkey")
        batch.drop_constraint("fk_gallery_reopening_parent", type_="foreignkey")
        batch.alter_column("derived_gallery_id", existing_type=sa.Uuid(), nullable=False)
        batch.drop_column("parent_gallery_id")
