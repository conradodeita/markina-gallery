"""Materialize independent processing settings for public source folders."""

import sqlalchemy as sa
from alembic import op

revision = "20261014_0079"
down_revision = "20261014_0078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().execute(sa.text("""
        INSERT INTO folder_processing_settings (
            tenant_id, folder_id, preview_mode, facial_mode,
            preview_strength, preview_exposure_tenths, revision, updated_at
        )
        SELECT folder.tenant_id, folder.id, 'custom', 'on',
               COALESCE(gallery_settings.strength, 50),
               COALESCE(gallery_settings.exposure_tenths, 0),
               1, CURRENT_TIMESTAMP
        FROM photo_folder AS folder
        LEFT JOIN gallery_preview_settings AS gallery_settings
          ON gallery_settings.tenant_id = folder.tenant_id
         AND gallery_settings.parent_gallery_id = folder.parent_gallery_id
        WHERE folder.purpose = 'content'
          AND folder.derived_gallery_id IS NULL
          AND (folder.audience_scope = 'all' OR folder.audience_scope IS NULL)
          AND NOT EXISTS (
              SELECT 1 FROM folder_processing_settings AS folder_settings
              WHERE folder_settings.tenant_id = folder.tenant_id
                AND folder_settings.folder_id = folder.id
          )
    """))


def downgrade() -> None:
    # Linhas podem ter sido editadas após a migration; removê-las apagaria
    # configurações de fotógrafo que não podem ser distinguidas com segurança.
    pass
