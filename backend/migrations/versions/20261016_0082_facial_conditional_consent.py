"""Aceite condicional único para novas buscas por foto de referência."""

import sqlalchemy as sa
from alembic import op

revision = "20261016_0082"
down_revision = "20261014_0081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("facial_search_request") as batch:
        batch.drop_constraint("ck_facial_search_subject_declaration", type_="check")
        batch.create_check_constraint(
            "ck_facial_search_subject_declaration",
            "subject_declaration IN ('adult', 'minor', 'conditional')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text(
        "SELECT COUNT(*) FROM facial_search_request "
        "WHERE subject_declaration = 'conditional'"
    )):
        raise RuntimeError("Downgrade recusado: preserve recibos de consentimento condicional.")
    with op.batch_alter_table("facial_search_request") as batch:
        batch.drop_constraint("ck_facial_search_subject_declaration", type_="check")
        batch.create_check_constraint(
            "ck_facial_search_subject_declaration",
            "subject_declaration IN ('adult', 'minor')",
        )
