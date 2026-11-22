"""Versionar a chave dos fingerprints de CPF do fotógrafo."""

import sqlalchemy as sa
from alembic import op

revision = "20261110_0120"
down_revision = "20261109_0119"
branch_labels = None
depends_on = None

_TABLE = "photographer_business_profile"
_COLUMN = "cpf_fingerprint_key_version"
_LEGACY_VERSION = "legacy-v0"
_CONSTRAINT = "ck_photographer_profile_fingerprint_key_version"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            _COLUMN,
            sa.String(length=40),
            nullable=False,
            server_default=sa.text(f"'{_LEGACY_VERSION}'"),
        ),
    )
    op.create_check_constraint(
        _CONSTRAINT,
        _TABLE,
        f"length({_COLUMN}) BETWEEN 1 AND 40",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Versão de impressão de CPF requer PostgreSQL.")
    bind.exec_driver_sql(
        f"LOCK TABLE {_TABLE} IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(
        f"SELECT EXISTS(SELECT 1 FROM {_TABLE} WHERE {_COLUMN} <> :legacy)"
    ), {"legacy": _LEGACY_VERSION}):
        raise RuntimeError("Preserve versões de impressão de CPF: rollback recusado.")
    op.drop_constraint(_CONSTRAINT, _TABLE, type_="check")
    op.drop_column(_TABLE, _COLUMN)
