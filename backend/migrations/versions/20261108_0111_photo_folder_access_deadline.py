"""Adicionar prazo independente às pastas de conteúdo."""

import sqlalchemy as sa
from alembic import op

revision = "20261108_0111"
down_revision = "20261107_0110"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Prazo por pasta requer PostgreSQL.")
    op.add_column(
        "photo_folder",
        sa.Column("access_duration_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "photo_folder",
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_photo_folder_access_duration_days",
        "photo_folder",
        "access_duration_days IS NULL OR access_duration_days >= 1",
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Prazo por pasta requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE photo_folder IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    populated = bind.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM photo_folder "
            "WHERE access_duration_days IS NOT NULL OR access_expires_at IS NOT NULL LIMIT 1)"
        )
    )
    if populated:
        raise RuntimeError("Preserve prazos de pastas: rollback recusado com valores configurados.")
    op.drop_constraint(
        "ck_photo_folder_access_duration_days", "photo_folder", type_="check"
    )
    op.drop_column("photo_folder", "access_expires_at")
    op.drop_column("photo_folder", "access_duration_days")
