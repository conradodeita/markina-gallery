"""Add the canonical source-gallery link to the private-photo WhatsApp default."""

import sqlalchemy as sa
from alembic import op

revision = "20261017_0084"
down_revision = "20261017_0083"
branch_labels = None
depends_on = None

OLD_DEFAULT = "Novas fotos disponíveis na sua galeria."
NEW_DEFAULT = (
    "Essa mensagem é automática! Novas fotos disponíveis na sua galeria. "
    "Acesso no link: {{link_galeria}}."
)


def upgrade() -> None:
    op.execute(sa.text(
        "UPDATE notification_setting "
        "SET whatsapp_body = :new_body, version = version + 1, updated_at = CURRENT_TIMESTAMP "
        "WHERE event_type = 'private_photos_ready' AND whatsapp_body = :old_body"
    ).bindparams(old_body=OLD_DEFAULT, new_body=NEW_DEFAULT))


def downgrade() -> None:
    op.execute(sa.text(
        "UPDATE notification_setting "
        "SET whatsapp_body = :old_body, version = version + 1, updated_at = CURRENT_TIMESTAMP "
        "WHERE event_type = 'private_photos_ready' AND whatsapp_body = :new_body"
    ).bindparams(old_body=OLD_DEFAULT, new_body=NEW_DEFAULT))
