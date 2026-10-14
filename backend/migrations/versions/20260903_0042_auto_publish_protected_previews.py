"""Disponibiliza fotos de conteúdo após a prévia protegida ficar pronta.

Revision ID: 20260903_0042
Revises: 20260902_0041
"""

import sqlalchemy as sa
from alembic import op

revision = "20260903_0042"
down_revision = "20260902_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE photo_asset SET available = true "
            "WHERE available = false AND EXISTS ("
            "SELECT 1 FROM photo_folder "
            "WHERE photo_folder.id = photo_asset.folder_id "
            "AND photo_folder.parent_gallery_id = photo_asset.parent_gallery_id "
            "AND photo_folder.purpose = 'content'"
            ") AND EXISTS ("
            "SELECT 1 FROM media_derivative "
            "WHERE media_derivative.photo_asset_id = photo_asset.id "
            "AND media_derivative.variant = 'client_preview' "
            "AND media_derivative.status = 'ready'"
            ")"
        )
    )
    op.execute(
        sa.text(
            "UPDATE photo_folder SET status = 'released', "
            "released_at = COALESCE(released_at, CURRENT_TIMESTAMP) "
            "WHERE purpose = 'content' AND status = 'preparing' AND EXISTS ("
            "SELECT 1 FROM photo_asset "
            "WHERE photo_asset.folder_id = photo_folder.id "
            "AND photo_asset.parent_gallery_id = photo_folder.parent_gallery_id "
            "AND photo_asset.available = true"
            ")"
        )
    )


def downgrade() -> None:
    # A disponibilidade anterior não pode ser distinguida com segurança após o upgrade.
    pass
