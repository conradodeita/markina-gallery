import os
from uuid import uuid4

import sqlalchemy as sa

from tests.test_global_pix_migration import alembic


def test_asset_history_upgrade_and_guarded_downgrade(tmp_path):
    url = f"sqlite:///{(tmp_path / 'history.sqlite').as_posix()}"
    if os.getenv("ASSET_HISTORY_MIGRATION_TEST_URL"):
        parsed = sa.engine.make_url(os.environ["ASSET_HISTORY_MIGRATION_TEST_URL"])
        assert parsed.host == "127.0.0.1" and parsed.port == 55458
        assert parsed.database == "markina_unified_test"
        maintenance = sa.create_engine(parsed, isolation_level="AUTOCOMMIT")
        database = f"markina_asset_history_{uuid4().hex}"
        with maintenance.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database}"')
        maintenance.dispose()
        url = parsed.set(database=database).render_as_string(hide_password=False)
    alembic(url, "upgrade", "20260920_0058")
    alembic(url, "upgrade", "head")
    engine = sa.create_engine(url)
    assert "removed_photo_movement" in sa.inspect(engine).get_table_names()
    assert "assets_removed_at" in {c['name'] for c in sa.inspect(engine).get_columns('sale_order')}
    alembic(url, "downgrade", "20260920_0058")
    alembic(url, "upgrade", "head")
    with engine.begin() as db:
        db.execute(sa.text("INSERT INTO asset_file_cleanup "
            "(id, paths, status, attempts, created_at) VALUES "
            "('00000000000000000000000000000001', '[]', 'pending', 0, CURRENT_TIMESTAMP)"))
    alembic(url, "downgrade", "20260920_0058", succeeds=False)
    with engine.connect() as db:
        assert db.execute(sa.text('SELECT count(*) FROM asset_file_cleanup')).scalar() == 1
    engine.dispose()
