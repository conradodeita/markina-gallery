"""Preserva privadas e mídia referenciada após remover a origem pública.

Revision ID: 20260831_0029
Revises: 20260831_0028
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0029"
down_revision = "20260831_0028"
branch_labels = None
depends_on = None


def _replace_constraint(values: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("parent_gallery", recreate="always") as batch_op:
            batch_op.drop_constraint(
                "ck_parent_gallery_lifecycle_status", type_="check"
            )
            batch_op.create_check_constraint(
                "ck_parent_gallery_lifecycle_status",
                f"lifecycle_status IN ({values})",
            )
    else:
        op.drop_constraint(
            "ck_parent_gallery_lifecycle_status",
            "parent_gallery",
            type_="check",
        )
        op.create_check_constraint(
            "ck_parent_gallery_lifecycle_status",
            "parent_gallery",
            f"lifecycle_status IN ({values})",
        )


def upgrade() -> None:
    _replace_constraint("'active', 'deleting', 'deleted'")


def downgrade() -> None:
    bind = op.get_bind()
    deleted = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM parent_gallery "
            "WHERE lifecycle_status = 'deleted'"
        )
    ).scalar_one()
    if deleted:
        raise RuntimeError(
            "Downgrade recusado: existem Galerias públicas removidas com "
            "dependências privadas preservadas."
        )
    _replace_constraint("'active', 'deleting'")
