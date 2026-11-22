"""Adicionar reaberturas com escopo de pasta e duração aprovada."""

import sqlalchemy as sa
from alembic import op

revision = "20261109_0113"
down_revision = "20261108_0112"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Reabertura por pasta requer PostgreSQL.")

    op.add_column(
        "gallery_reopening_request",
        sa.Column("photo_folder_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "gallery_reopening_request",
        sa.Column("approved_duration_days", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_gallery_reopening_photo_folder",
        "gallery_reopening_request",
        "photo_folder",
        ["photo_folder_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_gallery_reopening_folder_scope",
        "gallery_reopening_request",
        "photo_folder",
        ["photo_folder_id", "parent_gallery_id", "tenant_id"],
        ["id", "parent_gallery_id", "tenant_id"],
    )
    op.create_unique_constraint(
        "uq_owner_photo_folder_id_derived_gallery_id_tenant_id",
        "photo_folder",
        ["id", "derived_gallery_id", "tenant_id"],
    )
    op.create_foreign_key(
        "fk_gallery_reopening_derived_folder_scope",
        "gallery_reopening_request",
        "photo_folder",
        ["photo_folder_id", "derived_gallery_id", "tenant_id"],
        ["id", "derived_gallery_id", "tenant_id"],
    )
    op.create_check_constraint(
        "ck_gallery_reopening_approved_duration_days",
        "gallery_reopening_request",
        "approved_duration_days IS NULL OR approved_duration_days >= 1",
    )
    op.create_check_constraint(
        "ck_gallery_reopening_folder_approval_duration",
        "gallery_reopening_request",
        "photo_folder_id IS NULL OR status != 'approved' OR approved_duration_days IS NOT NULL",
    )

    op.drop_index(
        "uq_gallery_reopening_request_pending",
        table_name="gallery_reopening_request",
    )
    op.drop_index(
        "uq_gallery_reopening_canonical_pending",
        table_name="gallery_reopening_request",
    )
    op.create_index(
        "uq_gallery_reopening_request_pending",
        "gallery_reopening_request",
        ["tenant_id", "derived_gallery_id"],
        unique=True,
        postgresql_where=sa.text(
            "photo_folder_id IS NULL AND status = 'pending'"
        ),
    )
    op.create_index(
        "uq_gallery_reopening_canonical_pending",
        "gallery_reopening_request",
        ["tenant_id", "parent_gallery_id", "requested_by_client_id"],
        unique=True,
        postgresql_where=sa.text(
            "parent_gallery_id IS NOT NULL AND photo_folder_id IS NULL AND status = 'pending'"
        ),
    )
    op.create_index(
        "uq_gallery_reopening_folder_pending_client",
        "gallery_reopening_request",
        ["tenant_id", "photo_folder_id", "requested_by_client_id"],
        unique=True,
        postgresql_where=sa.text(
            "photo_folder_id IS NOT NULL AND status = 'pending'"
        ),
    )
    op.create_index(
        "ix_gallery_reopening_folder_approved_until",
        "gallery_reopening_request",
        ["tenant_id", "photo_folder_id", "status", "approved_until"],
    )
    op.create_index(
        "ix_gallery_reopening_request_photo_folder_id",
        "gallery_reopening_request",
        ["photo_folder_id"],
    )
    op.create_unique_constraint(
        "uq_gallery_reopening_folder_idempotency",
        "gallery_reopening_request",
        ["photo_folder_id", "requested_by_client_id", "idempotency_key"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Reabertura por pasta requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE gallery_reopening_request IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    has_folder_requests = bind.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM gallery_reopening_request "
            "WHERE photo_folder_id IS NOT NULL OR approved_duration_days IS NOT NULL LIMIT 1)"
        )
    )
    if has_folder_requests:
        raise RuntimeError("Preserve reaberturas por pasta: rollback recusado com valores configurados.")

    op.drop_constraint(
        "fk_gallery_reopening_derived_folder_scope",
        "gallery_reopening_request",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_owner_photo_folder_id_derived_gallery_id_tenant_id",
        "photo_folder",
        type_="unique",
    )
    op.drop_constraint(
        "fk_gallery_reopening_folder_scope",
        "gallery_reopening_request",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_gallery_reopening_folder_idempotency",
        "gallery_reopening_request",
        type_="unique",
    )
    op.drop_index(
        "ix_gallery_reopening_request_photo_folder_id",
        table_name="gallery_reopening_request",
    )
    op.drop_index(
        "ix_gallery_reopening_folder_approved_until",
        table_name="gallery_reopening_request",
    )
    op.drop_index(
        "uq_gallery_reopening_folder_pending_client",
        table_name="gallery_reopening_request",
    )
    op.drop_index(
        "uq_gallery_reopening_canonical_pending",
        table_name="gallery_reopening_request",
    )
    op.drop_index(
        "uq_gallery_reopening_request_pending",
        table_name="gallery_reopening_request",
    )
    op.create_index(
        "uq_gallery_reopening_canonical_pending",
        "gallery_reopening_request",
        ["tenant_id", "parent_gallery_id", "requested_by_client_id"],
        unique=True,
        postgresql_where=sa.text(
            "parent_gallery_id IS NOT NULL AND status = 'pending'"
        ),
    )
    op.create_index(
        "uq_gallery_reopening_request_pending",
        "gallery_reopening_request",
        ["tenant_id", "derived_gallery_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_constraint(
        "ck_gallery_reopening_folder_approval_duration",
        "gallery_reopening_request",
        type_="check",
    )
    op.drop_constraint(
        "ck_gallery_reopening_approved_duration_days",
        "gallery_reopening_request",
        type_="check",
    )
    op.drop_constraint(
        "fk_gallery_reopening_photo_folder",
        "gallery_reopening_request",
        type_="foreignkey",
    )
    op.drop_column("gallery_reopening_request", "approved_duration_days")
    op.drop_column("gallery_reopening_request", "photo_folder_id")
