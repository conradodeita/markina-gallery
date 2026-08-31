"""Garante privada única e registra a origem de cada foto disponível.

Revision ID: 20260831_0021
Revises: 20260831_0020
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0021"
down_revision = "20260831_0020"
branch_labels = None
depends_on = None

SQLITE_NAMING_CONVENTION = {
    "uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s"
}


def _existing_photo_reference_unique_name(bind) -> str:
    expected = {"derived_gallery_id", "photo_asset_id"}
    for constraint in sa.inspect(bind).get_unique_constraints("derived_gallery_photo"):
        if set(constraint["column_names"]) == expected and constraint.get("name"):
            return constraint["name"]
    raise RuntimeError(
        "Constraint legada de disponibilidade não encontrada; migration interrompida."
    )


def _reject_duplicate_private_galleries(bind) -> None:
    duplicate = bind.execute(
        sa.text(
            """
            SELECT parent_gallery_id, client_id, COUNT(*) AS quantity
            FROM derived_gallery
            GROUP BY parent_gallery_id, client_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate:
        raise RuntimeError(
            "Existem galerias privadas operacionais duplicadas para o mesmo cliente e "
            "Galeria pública; reconcilie-as antes de aplicar a migration."
        )


def upgrade() -> None:
    bind = op.get_bind()
    _reject_duplicate_private_galleries(bind)

    op.drop_index("ix_derived_gallery_parent_client", table_name="derived_gallery")
    op.create_index(
        "ix_derived_gallery_parent_client",
        "derived_gallery",
        ["parent_gallery_id", "client_id"],
        unique=True,
    )

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "derived_gallery_photo",
            recreate="always",
            naming_convention=SQLITE_NAMING_CONVENTION,
        ) as batch_op:
            batch_op.drop_constraint(
                "uq_derived_gallery_photo_derived_gallery_id_photo_asset_id",
                type_="unique",
            )
            batch_op.add_column(
                sa.Column(
                    "origin",
                    sa.String(length=16),
                    nullable=False,
                    server_default="admin",
                )
            )
            batch_op.create_check_constraint(
                "ck_derived_gallery_photo_origin",
                "origin IN ('admin', 'client', 'facial')",
            )
            batch_op.create_unique_constraint(
                "uq_derived_gallery_photo_origin",
                ["derived_gallery_id", "photo_asset_id", "origin"],
            )
        return

    old_constraint = _existing_photo_reference_unique_name(bind)
    op.drop_constraint(old_constraint, "derived_gallery_photo", type_="unique")
    op.add_column(
        "derived_gallery_photo",
        sa.Column(
            "origin",
            sa.String(length=16),
            nullable=False,
            server_default="admin",
        ),
    )
    op.create_check_constraint(
        "ck_derived_gallery_photo_origin",
        "derived_gallery_photo",
        "origin IN ('admin', 'client', 'facial')",
    )
    op.create_unique_constraint(
        "uq_derived_gallery_photo_origin",
        "derived_gallery_photo",
        ["derived_gallery_id", "photo_asset_id", "origin"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    duplicate_origin = bind.execute(
        sa.text(
            """
            SELECT derived_gallery_id, photo_asset_id, COUNT(*) AS quantity
            FROM derived_gallery_photo
            GROUP BY derived_gallery_id, photo_asset_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate_origin:
        raise RuntimeError(
            "O downgrade descartaria procedências coexistentes; remova a divergência "
            "explicitamente antes de prosseguir."
        )

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "derived_gallery_photo",
            recreate="always",
            naming_convention=SQLITE_NAMING_CONVENTION,
        ) as batch_op:
            batch_op.drop_constraint(
                "uq_derived_gallery_photo_origin", type_="unique"
            )
            batch_op.drop_constraint(
                "ck_derived_gallery_photo_origin", type_="check"
            )
            batch_op.drop_column("origin")
            batch_op.create_unique_constraint(
                "uq_derived_gallery_photo_derived_gallery_id_photo_asset_id",
                ["derived_gallery_id", "photo_asset_id"],
            )
    else:
        op.drop_constraint(
            "uq_derived_gallery_photo_origin",
            "derived_gallery_photo",
            type_="unique",
        )
        op.drop_constraint(
            "ck_derived_gallery_photo_origin",
            "derived_gallery_photo",
            type_="check",
        )
        op.drop_column("derived_gallery_photo", "origin")
        op.create_unique_constraint(
            "derived_gallery_photo_derived_gallery_id_photo_asset_id_key",
            "derived_gallery_photo",
            ["derived_gallery_id", "photo_asset_id"],
        )

    op.drop_index("ix_derived_gallery_parent_client", table_name="derived_gallery")
    op.create_index(
        "ix_derived_gallery_parent_client",
        "derived_gallery",
        ["parent_gallery_id", "client_id"],
        unique=False,
    )
