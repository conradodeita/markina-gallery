"""Preserva justificativas independentes do acervo privado comum.

Revision ID: 20260901_0040
Revises: 20260901_0039
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "20260901_0040"
down_revision = "20260901_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "derived_gallery_photo_origin",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "derived_gallery_photo_id",
            sa.Uuid(),
            sa.ForeignKey("derived_gallery_photo.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "origin IN ('admin', 'client', 'facial')",
            name="ck_derived_gallery_photo_origin_reason",
        ),
        sa.UniqueConstraint(
            "derived_gallery_photo_id",
            "origin",
            name="uq_derived_gallery_photo_origin_reason",
        ),
    )
    op.create_index(
        "ix_derived_gallery_photo_origin_reference",
        "derived_gallery_photo_origin",
        ["derived_gallery_photo_id"],
    )
    bind = op.get_bind()
    created_at = datetime.now(UTC)
    rows = bind.execute(
        sa.text("SELECT id, origin, created_at FROM derived_gallery_photo")
    ).mappings()
    for row in rows:
        generated_id = uuid4()
        bind.execute(
            sa.text(
                "INSERT INTO derived_gallery_photo_origin "
                "(id, derived_gallery_photo_id, origin, created_at) "
                "VALUES (:id, :reference_id, :origin, :created_at)"
            ),
            {
                "id": generated_id.hex
                if bind.dialect.name == "sqlite"
                else generated_id,
                "reference_id": row["id"],
                "origin": row["origin"],
                "created_at": row["created_at"] or created_at,
            },
        )


def downgrade() -> None:
    op.drop_index(
        "ix_derived_gallery_photo_origin_reference",
        table_name="derived_gallery_photo_origin",
    )
    op.drop_table("derived_gallery_photo_origin")
