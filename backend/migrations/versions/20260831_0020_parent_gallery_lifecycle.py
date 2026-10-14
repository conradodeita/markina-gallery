"""Adiciona estado de exclusão e índices operacionais da galeria.

Revision ID: 20260831_0020
Revises: 20260831_0019
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0020"
down_revision = "20260831_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("parent_gallery", recreate="always") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "lifecycle_status",
                    sa.String(length=16),
                    nullable=False,
                    server_default="active",
                )
            )
            batch_op.create_check_constraint(
                "ck_parent_gallery_lifecycle_status",
                "lifecycle_status IN ('active', 'deleting')",
            )
    else:
        op.add_column(
            "parent_gallery",
            sa.Column(
                "lifecycle_status",
                sa.String(length=16),
                nullable=False,
                server_default="active",
            ),
        )
        op.create_check_constraint(
            "ck_parent_gallery_lifecycle_status",
            "parent_gallery",
            "lifecycle_status IN ('active', 'deleting')",
        )

    op.create_index(
        "ix_parent_gallery_lifecycle_created",
        "parent_gallery",
        ["lifecycle_status", "created_at"],
    )
    op.create_index(
        "ix_gallery_lifecycle_operation_target_status",
        "gallery_lifecycle_operation",
        ["target_parent_gallery_id", "status"],
    )
    op.create_index(
        "ix_sale_order_parent_payment_status",
        "sale_order",
        ["parent_gallery_id_snapshot", "payment_status"],
    )
    op.create_index(
        "ix_sale_order_gallery_client_payment",
        "sale_order",
        ["derived_gallery_id", "client_id", "payment_status"],
    )
    op.create_index(
        "ix_derived_gallery_parent_client",
        "derived_gallery",
        ["parent_gallery_id", "client_id"],
    )
    op.create_index(
        "ix_photo_selection_gallery_client",
        "photo_selection",
        ["derived_gallery_id", "client_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_photo_selection_gallery_client", table_name="photo_selection")
    op.drop_index("ix_derived_gallery_parent_client", table_name="derived_gallery")
    op.drop_index("ix_sale_order_gallery_client_payment", table_name="sale_order")
    op.drop_index("ix_sale_order_parent_payment_status", table_name="sale_order")
    op.drop_index(
        "ix_gallery_lifecycle_operation_target_status",
        table_name="gallery_lifecycle_operation",
    )
    op.drop_index(
        "ix_parent_gallery_lifecycle_created", table_name="parent_gallery"
    )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("parent_gallery", recreate="always") as batch_op:
            batch_op.drop_constraint(
                "ck_parent_gallery_lifecycle_status", type_="check"
            )
            batch_op.drop_column("lifecycle_status")
    else:
        op.drop_constraint(
            "ck_parent_gallery_lifecycle_status",
            "parent_gallery",
            type_="check",
        )
        op.drop_column("parent_gallery", "lifecycle_status")
