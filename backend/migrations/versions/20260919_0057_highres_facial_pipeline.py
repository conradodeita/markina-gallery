"""Fonte temporária e regiões faciais; legado preservado sem geometria inventada."""

import sqlalchemy as sa
from alembic import op

revision = "20260919_0057"
down_revision = "20260914_0056"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "photo_analysis",
        sa.Column(
            "photo_asset_id",
            sa.Uuid(),
            sa.ForeignKey("photo_asset.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("source_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("pipeline_version", sa.String(80), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('receiving', 'pending', 'ready', 'failed', 'reupload_required')",
            name="ck_photo_analysis_state",
        ),
        sa.CheckConstraint(
            "width > 0 AND height > 0 AND source_bytes >= 0", name="ck_photo_analysis_dimensions"
        ),
    )
    op.create_index("ix_photo_analysis_state", "photo_analysis", ["state"])
    op.create_index("ix_photo_analysis_expires_at", "photo_analysis", ["expires_at"])
    with op.batch_alter_table("photo_face_embedding") as batch:
        batch.add_column(
            sa.Column(
                "model_id", sa.String(80), nullable=False, server_default="opencv-yunet-sface"
            )
        )
        batch.add_column(
            sa.Column("embedding_dimension", sa.Integer(), nullable=False, server_default="128")
        )
        batch.add_column(
            sa.Column(
                "pipeline_version",
                sa.String(80),
                nullable=False,
                server_default="legacy-preview-v1",
            )
        )
        batch.add_column(sa.Column("detection_pass", sa.String(80)))
        for name in ("detection_confidence", "bbox_x", "bbox_y", "bbox_width", "bbox_height"):
            batch.add_column(sa.Column(name, sa.Float()))
        batch.create_check_constraint(
            "ck_face_region_bounds",
            "(bbox_x IS NULL AND bbox_y IS NULL AND bbox_width IS NULL AND bbox_height IS NULL) OR "
            "(bbox_x IS NOT NULL AND bbox_y IS NOT NULL AND bbox_width IS NOT NULL AND bbox_height IS NOT NULL "
            "AND bbox_x >= 0 AND bbox_y >= 0 AND bbox_width > 0 AND bbox_height > 0 "
            "AND bbox_x + bbox_width <= 1 AND bbox_y + bbox_height <= 1)",
        )
    op.add_column("facial_search_request", sa.Column("reference_region_id", sa.Uuid()))
    op.add_column(
        "facial_search_candidate",
        sa.Column("match_class", sa.String(16), nullable=False, server_default="matched"),
    )


def downgrade():
    # Apenas banco descartável ou após inventário/backup autorizado; não recria pixels removidos.
    with op.batch_alter_table("facial_search_candidate") as batch:
        batch.drop_column("match_class")
    with op.batch_alter_table("facial_search_request") as batch:
        batch.drop_column("reference_region_id")
    with op.batch_alter_table("photo_face_embedding") as batch:
        batch.drop_constraint("ck_face_region_bounds", type_="check")
        for name in (
            "model_id",
            "embedding_dimension",
            "pipeline_version",
            "detection_pass",
            "detection_confidence",
            "bbox_x",
            "bbox_y",
            "bbox_width",
            "bbox_height",
        ):
            batch.drop_column(name)
    op.drop_table("photo_analysis")
