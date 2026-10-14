"""Permite cancelamento terminal antes da remoção física.

Revision ID: 20260831_0026
Revises: 20260831_0025
"""

from alembic import op

revision = "20260831_0026"
down_revision = "20260831_0025"
branch_labels = None
depends_on = None


NEW_STATUS = (
    "status IN ('queued', 'preparing_history', 'removing_storage', "
    "'removing_records', 'completed', 'failed', 'cancelled')"
)
OLD_STATUS = (
    "status IN ('queued', 'preparing_history', 'removing_storage', "
    "'removing_records', 'completed', 'failed')"
)


def _replace_constraint(expression: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "gallery_lifecycle_operation", recreate="always"
        ) as batch_op:
            batch_op.drop_constraint(
                "ck_gallery_lifecycle_operation_status", type_="check"
            )
            batch_op.create_check_constraint(
                "ck_gallery_lifecycle_operation_status", expression
            )
    else:
        op.drop_constraint(
            "ck_gallery_lifecycle_operation_status",
            "gallery_lifecycle_operation",
            type_="check",
        )
        op.create_check_constraint(
            "ck_gallery_lifecycle_operation_status",
            "gallery_lifecycle_operation",
            expression,
        )


def upgrade() -> None:
    _replace_constraint(NEW_STATUS)


def downgrade() -> None:
    bind = op.get_bind()
    cancelled = bind.exec_driver_sql(
        "SELECT COUNT(*) FROM gallery_lifecycle_operation WHERE status = 'cancelled'"
    ).scalar_one()
    if cancelled:
        raise RuntimeError(
            "Downgrade bloqueado: existem operações de ciclo de vida canceladas."
        )
    _replace_constraint(OLD_STATUS)
