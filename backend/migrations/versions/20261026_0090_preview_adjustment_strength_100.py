"""Permite intensidade de ajuste de prévias até 100%."""

import sqlalchemy as sa
from alembic import op

revision = "20261026_0090"
down_revision = "20261025_0089"
branch_labels = None
depends_on = None


_CONSTRAINTS = (
    (
        "preview_adjustment_settings",
        "strength",
        "preview_adjustment_settings_strength_check",
        "ck_preview_adjustment_strength",
    ),
    (
        "gallery_preview_settings",
        "strength",
        "gallery_preview_settings_strength_check",
        "ck_gallery_preview_strength",
    ),
    (
        "folder_processing_settings",
        "preview_strength",
        "ck_folder_preview_strength",
        "ck_folder_preview_strength",
    ),
)


def _replace_constraint(
    table: str, column: str, old_db_name: str, new_name: str, from_upper: int, to_upper: int
) -> None:
    bind = op.get_bind()
    old_expression = f"{column} BETWEEN 10 AND {from_upper}"
    new_expression = f"{column} BETWEEN 10 AND {to_upper}"

    if bind.dialect.name == "sqlite":
        reflected = sa.Table(table, sa.MetaData(), autoload_with=bind)
        constraints = list(reflected.constraints) + [
            constraint for column_ref in reflected.c for constraint in column_ref.constraints
        ]
        matches = [
            constraint
            for constraint in constraints
            if isinstance(constraint, sa.CheckConstraint)
            and " ".join(str(constraint.sqltext).split()).replace("(", "").replace(")", "")
            == old_expression
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"Esperada uma CHECK constraint {old_expression!r} em {table}; encontradas {len(matches)}."
            )
        # SQLite não nomeia CHECKs criadas sem name. Damos um nome apenas à
        # constraint refletida para que o batch mode possa removê-la sem tocar
        # nas demais constraints da tabela.
        temporary_name = f"_replace_{table}_{column}_range"
        matches[0].name = temporary_name
        with op.batch_alter_table(table, copy_from=reflected, recreate="always") as batch:
            batch.drop_constraint(temporary_name, type_="check")
            batch.create_check_constraint(new_name, new_expression)
        return

    op.drop_constraint(old_db_name, table, type_="check")
    op.create_check_constraint(new_name, table, new_expression)


def upgrade() -> None:
    for table, column, old_name, new_name in _CONSTRAINTS:
        _replace_constraint(table, column, old_name, new_name, 75, 100)


def downgrade() -> None:
    bind = op.get_bind()
    for table, column, _, _ in _CONSTRAINTS:
        value = bind.execute(
            sa.text(f"SELECT 1 FROM {table} WHERE {column} > 75 LIMIT 1")
        ).first()
        if value:
            raise RuntimeError(
                "Downgrade recusado: há intensidade acima de 75%; reduza as configurações "
                "antes de voltar a migration 0090."
            )

    for table, column, old_name, new_name in _CONSTRAINTS:
        _replace_constraint(table, column, new_name, old_name, 100, 75)
