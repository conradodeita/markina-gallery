"""Add tenant-scoped opt-in RAW development state and provenance."""

import sqlalchemy as sa
from alembic import op

revision = "20261012_0075"
down_revision = "20261011_0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_development_settings",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("selected_engine", sa.String(16), nullable=False),
        sa.Column("lightcraft_latest_stable_version", sa.String(64)),
        sa.Column("lightcraft_latest_stable_url", sa.String(512)),
        sa.Column("lightcraft_latest_stable_published_at", sa.DateTime(timezone=True)),
        sa.Column("last_release_check_at", sa.DateTime(timezone=True)),
        sa.Column("release_check_status", sa.String(16), server_default="unknown", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1"),
        sa.CheckConstraint("selected_engine IN ('rawtherapee', 'lightcraft')"),
        sa.CheckConstraint("release_check_status IN ('unknown', 'ok', 'unavailable')"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_table(
        "raw_development_job",
        sa.Column("photo_asset_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("input_bytes", sa.Integer(), nullable=False),
        sa.Column("source_format", sa.String(8), nullable=False),
        sa.Column("camera_make", sa.String(64)),
        sa.Column("camera_model", sa.String(96)),
        sa.Column("staging_key", sa.String(96), nullable=False),
        sa.Column("engine", sa.String(16), nullable=False),
        sa.Column("engine_version", sa.String(64), nullable=False),
        sa.Column("profile_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("last_error", sa.String(64)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('receiving', 'queued', 'processing', 'ready', 'failed', 'reupload_required')"),
        sa.CheckConstraint("engine IN ('rawtherapee', 'lightcraft')"),
        sa.CheckConstraint("attempts >= 0"),
        sa.CheckConstraint("input_bytes > 0"),
        sa.CheckConstraint("width IS NULL OR width > 0"),
        sa.CheckConstraint("height IS NULL OR height > 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["photo_asset_id", "tenant_id"], ["photo_asset.id", "photo_asset.tenant_id"],
            ondelete="CASCADE", name="fk_raw_development_photo_tenant",
        ),
        sa.PrimaryKeyConstraint("photo_asset_id", "tenant_id"),
        sa.UniqueConstraint("staging_key"),
    )
    op.create_index("ix_raw_development_job_status", "raw_development_job", ["status"])
    op.create_index("ix_raw_development_job_expires_at", "raw_development_job", ["expires_at"])
    op.create_index("ix_raw_development_queue", "raw_development_job", ["tenant_id", "status", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_raw_development_queue", table_name="raw_development_job")
    op.drop_index("ix_raw_development_job_expires_at", table_name="raw_development_job")
    op.drop_index("ix_raw_development_job_status", table_name="raw_development_job")
    op.drop_table("raw_development_job")
    op.drop_table("raw_development_settings")
