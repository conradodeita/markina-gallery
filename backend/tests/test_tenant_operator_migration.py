"""0071 expansiva e vazia; preservação integral após a transição 0070."""

import pytest
import sqlalchemy as sa

from app.auth import InstallationOperator
from tests.test_tenant_photographer_migration import (
    assert_preserved,
    legacy,
    migrate,
    snapshot,
)
from tests.test_tenant_photographer_migration import baseline_template as _baseline_template
from tests.test_tenant_photographer_migration import migration_db as _migration_db

baseline_template = _baseline_template
migration_db = _migration_db


@pytest.mark.parametrize("with_legacy", [False, True])
def test_permission_migration_vazia_preserva_legado_e_recusa_downgrade(migration_db, with_legacy):
    url, engine = migration_db
    if with_legacy:
        with engine.begin() as connection:
            legacy(connection)
    migrate(url, "20260930_0070")
    with engine.connect() as connection:
        before = snapshot(connection)
    migrate(url, "20261001_0071")
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert connection.scalar(sa.text("SELECT count(*) FROM installation_operator")) == 0
        inspector = sa.inspect(connection)
        target = InstallationOperator.__table__
        columns = {column["name"]: column for column in inspector.get_columns(target.name)}
        assert set(columns) == set(target.c.keys())
        assert all(columns[column.name]["nullable"] == column.nullable for column in target.c)
        assert all(column["default"] is None for column in columns.values())
        assert inspector.get_pk_constraint(target.name)["constrained_columns"] == ["admin_user_id"]
        foreign = inspector.get_foreign_keys(target.name)
        assert len(foreign) == 1 and foreign[0]["referred_table"] == "admin_user"
        assert {item["name"] for item in inspector.get_check_constraints(target.name)} == {
            "ck_operator_reference", "ck_operator_active_revocation",
        }
        after = snapshot(connection)
    result = migrate(url, "20260930_0070", downgrade=True, succeeds=False)
    assert "Downgrade recusado" in result.stderr
    with engine.connect() as connection:
        assert_preserved(connection, after)
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "20261001_0071"
