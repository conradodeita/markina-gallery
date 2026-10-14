"""Torna obrigatória a hierarquia galeria, pasta e foto.

Revision ID: 20260827_0006
Revises: 20260827_0005
"""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

import sqlalchemy as sa
from alembic import op


revision = "20260827_0006"
down_revision = "20260827_0005"
branch_labels = None
depends_on = None


def _compatibility_folder_id(parent_gallery_id: UUID) -> UUID:
    return uuid5(NAMESPACE_URL, f"markina-gallery:legacy-folder:{parent_gallery_id}")


def _database_uuid(connection: sa.Connection, value: UUID) -> UUID | str:
    return value.hex if connection.dialect.name == "sqlite" else value


def _backfill_legacy_photos(connection: sa.Connection) -> None:
    orphan = connection.execute(
        sa.text(
            """
            SELECT photo_asset.id
            FROM photo_asset
            LEFT JOIN parent_gallery ON parent_gallery.id = photo_asset.parent_gallery_id
            WHERE photo_asset.folder_id IS NULL AND parent_gallery.id IS NULL
            LIMIT 1
            """
        )
    ).first()
    if orphan:
        raise RuntimeError(f"Foto legada sem galeria-mãe válida: {orphan[0]}")

    parent_ids = connection.execute(
        sa.text(
            "SELECT DISTINCT parent_gallery_id FROM photo_asset WHERE folder_id IS NULL"
        )
    ).scalars()
    timestamp = datetime.now(UTC)
    for raw_parent_id in parent_ids:
        parent_id = UUID(str(raw_parent_id))
        folder_id = _compatibility_folder_id(parent_id)
        bound_parent_id = _database_uuid(connection, parent_id)
        bound_folder_id = _database_uuid(connection, folder_id)
        existing = connection.execute(
            sa.text("SELECT parent_gallery_id FROM photo_folder WHERE id = :folder_id"),
            {"folder_id": bound_folder_id},
        ).scalar_one_or_none()
        if existing is not None and UUID(str(existing)) != parent_id:
            raise RuntimeError("Identificador determinístico de pasta já pertence a outra galeria.")
        if existing is None:
            position = connection.execute(
                sa.text(
                    """
                    SELECT COALESCE(MAX(position), -1) + 1
                    FROM photo_folder
                    WHERE parent_gallery_id = :parent_id
                    """
                ),
                {"parent_id": bound_parent_id},
            ).scalar_one()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO photo_folder
                        (id, parent_gallery_id, name, status, position, released_at, created_at, updated_at)
                    VALUES
                        (:id, :parent_id, :name, 'released', :position, :timestamp, :timestamp, :timestamp)
                    """
                ),
                {
                    "id": bound_folder_id,
                    "parent_id": bound_parent_id,
                    "name": "Importação anterior",
                    "position": position,
                    "timestamp": timestamp,
                },
            )
        connection.execute(
            sa.text(
                """
                UPDATE photo_asset
                SET folder_id = :folder_id
                WHERE parent_gallery_id = :parent_id AND folder_id IS NULL
                """
            ),
            {"folder_id": bound_folder_id, "parent_id": bound_parent_id},
        )

    remaining = connection.execute(
        sa.text("SELECT COUNT(*) FROM photo_asset WHERE folder_id IS NULL")
    ).scalar_one()
    if remaining:
        raise RuntimeError("O saneamento terminou com fotos sem pasta.")


def upgrade() -> None:
    connection = op.get_bind()
    _backfill_legacy_photos(connection)
    with op.batch_alter_table("photo_folder") as batch_op:
        batch_op.create_unique_constraint(
            "uq_photo_folder_id_parent", ["id", "parent_gallery_id"]
        )
    with op.batch_alter_table("photo_asset") as batch_op:
        batch_op.drop_constraint("fk_photo_asset_folder", type_="foreignkey")
        batch_op.alter_column("folder_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.create_foreign_key(
            "fk_photo_asset_folder_gallery",
            "photo_folder",
            ["folder_id", "parent_gallery_id"],
            ["id", "parent_gallery_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("photo_asset") as batch_op:
        batch_op.drop_constraint("fk_photo_asset_folder_gallery", type_="foreignkey")
        batch_op.alter_column("folder_id", existing_type=sa.Uuid(), nullable=True)
        batch_op.create_foreign_key(
            "fk_photo_asset_folder", "photo_folder", ["folder_id"], ["id"]
        )
    with op.batch_alter_table("photo_folder") as batch_op:
        batch_op.drop_constraint("uq_photo_folder_id_parent", type_="unique")
