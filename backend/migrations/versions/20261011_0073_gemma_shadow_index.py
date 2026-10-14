"""Global Gemma shadow setting and isolated facial job namespace."""

import sqlalchemy as sa
from alembic import op

revision = "20261011_0073"
down_revision = "20261009_0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "facial_embedding_experiment_setting",
        sa.Column("singleton", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="shadow"),
        sa.Column(
            "model_revision", sa.String(length=64), nullable=False,
            server_default="914f7f89142e33e77833254d9c9b90c3cef7303b",
        ),
        sa.Column("updated_by_admin_id", sa.Uuid(), sa.ForeignKey("admin_user.id"), nullable=True),
        sa.Column("worker_last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("singleton = 1", name="ck_facial_embedding_experiment_singleton"),
        sa.CheckConstraint("mode = 'shadow'", name="ck_facial_embedding_experiment_mode"),
    )
    with op.batch_alter_table("facial_job") as batch:
        batch.drop_constraint("ck_facial_job_kind", type_="check")
        batch.create_check_constraint(
            "ck_facial_job_kind",
            "kind IN ('index', 'index_gemma', 'purge', 'search', 'cleanup')",
        )
    op.create_index(
        "ix_face_embedding_gallery_engine",
        "photo_face_embedding",
        ["tenant_id", "parent_gallery_id", "model_id", "model_version", "quality_version"],
    )


def downgrade() -> None:
    raise RuntimeError("Downgrade recusado: preserve a configuração e os embeddings biométricos.")
