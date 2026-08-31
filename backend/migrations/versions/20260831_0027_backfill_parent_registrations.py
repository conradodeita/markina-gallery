"""Materializa vínculos públicos para galerias privadas legadas.

Revision ID: 20260831_0027
Revises: 20260831_0026
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision = "20260831_0027"
down_revision = "20260831_0026"
branch_labels = None
depends_on = None


def _uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT d.parent_gallery_id, d.client_id
            FROM derived_gallery AS d
            LEFT JOIN parent_gallery_registration AS r
              ON r.parent_gallery_id = d.parent_gallery_id
             AND r.client_id = d.client_id
            WHERE r.id IS NULL
            """
        )
    ).all()
    timestamp = datetime.now(UTC)
    registration = sa.table(
        "parent_gallery_registration",
        sa.column("id", sa.Uuid()),
        sa.column("parent_gallery_id", sa.Uuid()),
        sa.column("client_id", sa.Uuid()),
        sa.column("status", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    if rows:
        op.bulk_insert(
            registration,
            [
                {
                    "id": uuid4(),
                    "parent_gallery_id": _uuid(parent_gallery_id),
                    "client_id": _uuid(client_id),
                    "status": "active",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
                for parent_gallery_id, client_id in rows
            ],
        )


def downgrade() -> None:
    # Vínculos podem ter sido usados após o upgrade; removê-los seria perda de acesso.
    pass
