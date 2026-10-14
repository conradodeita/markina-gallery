"""Adiciona a fundação persistente do filtro facial, desativada por padrão.

Revision ID: 20260905_0043
Revises: 20260903_0042
"""

import sqlalchemy as sa
from alembic import op

revision = "20260905_0043"
down_revision = "20260903_0042"
branch_labels = None
depends_on = None


def _create_indexes(table: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("photo_asset", recreate="always") as batch:
            batch.create_unique_constraint(
                "uq_photo_asset_id_parent", ["id", "parent_gallery_id"]
            )
    else:
        op.create_unique_constraint(
            "uq_photo_asset_id_parent",
            "photo_asset",
            ["id", "parent_gallery_id"],
        )

    op.create_table(
        "gallery_facial_policy",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "parent_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("parent_gallery.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="disabled"),
        sa.Column("legal_notice_version", sa.String(length=80), nullable=True),
        sa.Column("legal_basis_reference", sa.String(length=200), nullable=True),
        sa.Column("retention_policy_version", sa.String(length=80), nullable=True),
        sa.Column("minor_policy_version", sa.String(length=80), nullable=True),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.Column("quality_version", sa.String(length=120), nullable=False),
        sa.Column("calibration_version", sa.String(length=120), nullable=True),
        sa.Column(
            "similarity_threshold_milli", sa.Integer(), nullable=False, server_default="750"
        ),
        sa.Column("index_generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actor_admin_id", sa.Uuid(), sa.ForeignKey("admin_user.id"), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("parent_gallery_id", name="uq_gallery_facial_policy_parent"),
        sa.CheckConstraint(
            "status IN ('disabled', 'pending', 'active', 'suspended')",
            name="ck_gallery_facial_policy_status",
        ),
        sa.CheckConstraint(
            "similarity_threshold_milli BETWEEN 0 AND 1000",
            name="ck_gallery_facial_policy_threshold",
        ),
        sa.CheckConstraint(
            "index_generation >= 0", name="ck_gallery_facial_policy_generation"
        ),
    )
    _create_indexes(
        "gallery_facial_policy", ("parent_gallery_id", "status", "actor_admin_id")
    )

    op.create_table(
        "photo_face_embedding",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "parent_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("parent_gallery.id"),
            nullable=False,
        ),
        sa.Column("photo_asset_id", sa.Uuid(), nullable=False),
        sa.Column("face_ordinal", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.Column("quality_version", sa.String(length=120), nullable=False),
        sa.Column("preview_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("quality_band", sa.String(length=16), nullable=False, server_default="other"),
        sa.Column("payload_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("payload_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("key_id", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["photo_asset_id", "parent_gallery_id"],
            ["photo_asset.id", "photo_asset.parent_gallery_id"],
            name="fk_face_embedding_photo_parent",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "photo_asset_id",
            "face_ordinal",
            "model_version",
            "quality_version",
            "preview_fingerprint",
            name="uq_face_embedding_versioned_photo_face",
        ),
        sa.CheckConstraint("face_ordinal >= 0", name="ck_face_embedding_ordinal"),
        sa.CheckConstraint(
            "quality_band IN ('best', 'other')", name="ck_face_embedding_quality_band"
        ),
    )
    _create_indexes("photo_face_embedding", ("parent_gallery_id", "photo_asset_id"))
    op.create_index(
        "ix_face_embedding_gallery_model",
        "photo_face_embedding",
        ["parent_gallery_id", "model_version", "quality_version"],
    )

    op.create_table(
        "facial_search_request",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "parent_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("parent_gallery.id"),
            nullable=False,
        ),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column(
            "policy_id", sa.Uuid(), sa.ForeignKey("gallery_facial_policy.id"), nullable=False
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("consent_version", sa.String(length=80), nullable=False),
        sa.Column("legal_notice_version", sa.String(length=80), nullable=False),
        sa.Column("subject_declaration", sa.String(length=16), nullable=False),
        sa.Column("representation_reference", sa.String(length=200), nullable=True),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.Column("quality_version", sa.String(length=120), nullable=False),
        sa.Column("index_generation", sa.Integer(), nullable=False),
        sa.Column("snapshot_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshot_ready", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("compare_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("compare_done", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reference_locator_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("reference_locator_nonce", sa.LargeBinary(), nullable=True),
        sa.Column("reference_key_id", sa.String(length=80), nullable=True),
        sa.Column("reference_deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "id", "parent_gallery_id", "client_id", name="uq_facial_search_scope"
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'waiting_index', 'validating_reference', 'searching', "
            "'ranking', 'ready', 'no_face', 'multiple_faces', 'low_quality', "
            "'index_incomplete', 'no_candidates', 'cancelled', 'expired', 'failed')",
            name="ck_facial_search_status",
        ),
        sa.CheckConstraint(
            "subject_declaration IN ('adult', 'minor')",
            name="ck_facial_search_subject_declaration",
        ),
        sa.CheckConstraint(
            "snapshot_total >= 0 AND snapshot_ready >= 0 AND snapshot_ready <= snapshot_total",
            name="ck_facial_search_snapshot_progress",
        ),
        sa.CheckConstraint(
            "compare_total >= 0 AND compare_done >= 0 AND compare_done <= compare_total",
            name="ck_facial_search_compare_progress",
        ),
    )
    _create_indexes(
        "facial_search_request",
        ("parent_gallery_id", "client_id", "policy_id", "status", "expires_at"),
    )
    op.create_index(
        "ix_facial_search_client_gallery_expiry",
        "facial_search_request",
        ["client_id", "parent_gallery_id", "expires_at"],
    )

    op.create_table(
        "facial_search_snapshot_item",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("search_request_id", sa.Uuid(), nullable=False),
        sa.Column("parent_gallery_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("photo_asset_id", sa.Uuid(), nullable=False),
        sa.Column("preview_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["search_request_id", "parent_gallery_id", "client_id"],
            [
                "facial_search_request.id",
                "facial_search_request.parent_gallery_id",
                "facial_search_request.client_id",
            ],
            name="fk_facial_snapshot_search_scope",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["photo_asset_id", "parent_gallery_id"],
            ["photo_asset.id", "photo_asset.parent_gallery_id"],
            name="fk_facial_snapshot_photo_parent",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "search_request_id", "photo_asset_id", name="uq_facial_snapshot_photo"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'ready', 'excluded')",
            name="ck_facial_snapshot_status",
        ),
    )
    _create_indexes(
        "facial_search_snapshot_item",
        ("search_request_id", "parent_gallery_id", "client_id", "photo_asset_id", "status"),
    )
    op.create_index(
        "ix_facial_snapshot_request_status",
        "facial_search_snapshot_item",
        ["search_request_id", "status"],
    )

    op.create_table(
        "facial_search_candidate",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("search_request_id", sa.Uuid(), nullable=False),
        sa.Column("parent_gallery_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("photo_asset_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("quality_band", sa.String(length=16), nullable=False),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["search_request_id", "parent_gallery_id", "client_id"],
            [
                "facial_search_request.id",
                "facial_search_request.parent_gallery_id",
                "facial_search_request.client_id",
            ],
            name="fk_facial_candidate_search_scope",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["photo_asset_id", "parent_gallery_id"],
            ["photo_asset.id", "photo_asset.parent_gallery_id"],
            name="fk_facial_candidate_photo_parent",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "search_request_id", "photo_asset_id", name="uq_facial_candidate_photo"
        ),
        sa.CheckConstraint("rank >= 1", name="ck_facial_candidate_rank"),
        sa.CheckConstraint(
            "quality_band IN ('best', 'other')", name="ck_facial_candidate_quality_band"
        ),
    )
    _create_indexes(
        "facial_search_candidate",
        ("search_request_id", "parent_gallery_id", "client_id", "photo_asset_id", "expires_at"),
    )
    op.create_index(
        "ix_facial_candidate_request_rank",
        "facial_search_candidate",
        ["search_request_id", "rank"],
    )

    op.create_table(
        "facial_job",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("idempotency_key", sa.String(length=240), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column(
            "parent_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("parent_gallery.id"),
            nullable=False,
        ),
        sa.Column("photo_asset_id", sa.Uuid(), sa.ForeignKey("photo_asset.id"), nullable=True),
        sa.Column(
            "search_request_id",
            sa.Uuid(),
            sa.ForeignKey("facial_search_request.id"),
            nullable=True,
        ),
        sa.Column("model_version", sa.String(length=120), nullable=True),
        sa.Column("quality_version", sa.String(length=120), nullable=True),
        sa.Column("preview_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_done", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.String(length=64), nullable=True),
        sa.Column("last_error_category", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_facial_job_idempotency"),
        sa.CheckConstraint(
            "kind IN ('index', 'purge', 'search', 'cleanup')", name="ck_facial_job_kind"
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_facial_job_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_facial_job_attempts"),
        sa.CheckConstraint("priority >= 0", name="ck_facial_job_priority"),
        sa.CheckConstraint(
            "progress_total >= 0 AND progress_done >= 0 AND progress_done <= progress_total",
            name="ck_facial_job_progress",
        ),
    )
    _create_indexes(
        "facial_job",
        (
            "kind",
            "status",
            "parent_gallery_id",
            "photo_asset_id",
            "search_request_id",
            "available_at",
            "lease_expires_at",
        ),
    )
    op.create_index(
        "ix_facial_job_pending", "facial_job", ["status", "priority", "available_at"]
    )

    op.create_table(
        "facial_search_notification_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("search_request_id", sa.Uuid(), nullable=False),
        sa.Column("parent_gallery_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("result_kind", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("idempotency_key", sa.String(length=240), nullable=False),
        sa.Column("payload_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("payload_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("key_id", sa.String(length=80), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_category", sa.String(length=80), nullable=True),
        sa.Column("external_message_id", sa.String(length=192), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["search_request_id", "parent_gallery_id", "client_id"],
            [
                "facial_search_request.id",
                "facial_search_request.parent_gallery_id",
                "facial_search_request.client_id",
            ],
            name="fk_facial_notification_search_scope",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_facial_notification_idempotency"
        ),
        sa.CheckConstraint(
            "result_kind IN ('ready', 'no_candidates', 'failed')",
            name="ck_facial_notification_result_kind",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'sent', 'failed', 'cancelled')",
            name="ck_facial_notification_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_facial_notification_attempts"),
    )
    _create_indexes(
        "facial_search_notification_outbox",
        ("search_request_id", "parent_gallery_id", "client_id", "status"),
    )
    op.create_index(
        "ix_facial_notification_pending",
        "facial_search_notification_outbox",
        ["status", "available_at"],
    )


def downgrade() -> None:
    for table in (
        "facial_search_notification_outbox",
        "facial_job",
        "facial_search_candidate",
        "facial_search_snapshot_item",
        "facial_search_request",
        "photo_face_embedding",
        "gallery_facial_policy",
    ):
        op.drop_table(table)

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("photo_asset", recreate="always") as batch:
            batch.drop_constraint("uq_photo_asset_id_parent", type_="unique")
    else:
        op.drop_constraint(
            "uq_photo_asset_id_parent", "photo_asset", type_="unique"
        )
