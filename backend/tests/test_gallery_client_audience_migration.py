"""A migration de público preserva a base antiga e impede atribuição cruzada."""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from subprocess import run
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError


def _alembic(database_url: str, *arguments: str) -> None:
    backend = Path(__file__).resolve().parents[1]
    result = run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=backend,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


@pytest.mark.parametrize("database_kind", ["sqlite", "postgres"])
def test_gallery_client_audience_upgrade_preserves_legacy_and_rejects_cross_gallery(
    tmp_path, database_kind
):
    database_url = (
        f"sqlite:///{(tmp_path / 'legacy.sqlite').as_posix()}"
        if database_kind == "sqlite"
        else os.getenv("TEST_POSTGRES_DATABASE_URL")
    )
    if not database_url:
        pytest.skip("TEST_POSTGRES_DATABASE_URL não configurada")
    _alembic(database_url, "upgrade", "20260925_0061")
    engine = create_engine(database_url)

    def _foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    if database_kind == "sqlite":
        event.listen(engine, "connect", _foreign_keys)

    parent_a, parent_b, client_id, private_id, common_folder, private_folder, photo_id = (
        uuid4().hex for _ in range(7)
    )
    timestamp = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO client (id, full_name, phone_e164) "
            "VALUES (:id, 'Cliente legado', '+5511555501000')"
        ), {"id": client_id})
        for parent_id in (parent_a, parent_b):
            connection.execute(text(
                "INSERT INTO parent_gallery (id, name, active, created_at) "
                "VALUES (:id, 'Galeria legada', true, :created_at)"
            ), {"id": parent_id, "created_at": timestamp})
        connection.execute(text(
            "INSERT INTO derived_gallery "
            "(id, parent_gallery_id, client_id, name, access_enabled, favorites_enabled, "
            "comments_enabled, created_at) "
            "VALUES (:id, :parent, :client, 'Privada legada', true, false, false, :created_at)"
        ), {"id": private_id, "parent": parent_a, "client": client_id, "created_at": timestamp})
        for folder_id, scope in ((common_folder, None), (private_folder, private_id)):
            connection.execute(text(
                "INSERT INTO photo_folder "
                "(id, parent_gallery_id, derived_gallery_id, name, status, purpose, "
                "position, created_at, updated_at) "
                "VALUES (:id, :parent, :private, 'Pasta legada', 'released', 'content', "
                ":position, :created_at, :created_at)"
            ), {"id": folder_id, "parent": parent_a, "private": scope,
                "position": 0, "created_at": timestamp})
        connection.execute(text(
            "INSERT INTO photo_asset "
            "(id, parent_gallery_id, folder_id, filename, storage_key, available, created_at) "
            "VALUES (:id, :parent, :folder, 'legacy.jpg', 'migration/legacy.jpg', true, :time)"
        ), {"id": photo_id, "parent": parent_a, "folder": common_folder, "time": timestamp})
        connection.execute(text(
            "INSERT INTO photo_selection "
            "(id, derived_gallery_id, photo_asset_id, client_id, created_at) "
            "VALUES (:id, :private, :photo, :client, :time)"
        ), {"id": uuid4().hex, "private": private_id, "photo": photo_id,
            "client": client_id, "time": timestamp})
    engine.dispose()

    _alembic(database_url, "upgrade", "head")
    engine = create_engine(database_url)
    if database_kind == "sqlite":
        event.listen(engine, "connect", _foreign_keys)
    assert {"gallery_client_state", "folder_client_grant"} <= set(inspect(engine).get_table_names())
    with engine.begin() as connection:
        rows = connection.execute(text(
            "SELECT id, audience_scope FROM photo_folder ORDER BY id"
        )).all()
        assert {str(identifier).replace("-", ""): audience for identifier, audience in rows} == {
            common_folder: "all", private_folder: "selected"
        }
        assert connection.execute(text("SELECT count(*) FROM derived_gallery")).scalar_one() == 1
        assert connection.execute(text(
            "SELECT count(*) FROM photo_selection WHERE derived_gallery_id IS NOT NULL "
            "AND parent_gallery_id IS NULL"
        )).scalar_one() == 1
        state_id, grant_id = uuid4().hex, uuid4().hex
        connection.execute(text(
            "INSERT INTO gallery_client_state "
            "(id, parent_gallery_id, client_id, status, created_at, updated_at) "
            "VALUES (:id, :parent, :client, 'active', :time, :time)"
        ), {"id": state_id, "parent": parent_a, "client": client_id, "time": timestamp})
        try:
            with connection.begin_nested():
                connection.execute(text(
                    "INSERT INTO folder_client_grant "
                    "(id, folder_id, parent_gallery_id, client_id, created_at) "
                    "VALUES (:id, :folder, :parent, :client, :time)"
                ), {"id": grant_id, "folder": private_folder, "parent": parent_b,
                    "client": client_id, "time": timestamp})
        except IntegrityError:
            pass
        else:
            raise AssertionError("Atribuição entre galerias foi aceita")
        connection.execute(text(
            "INSERT INTO folder_client_grant "
            "(id, folder_id, parent_gallery_id, client_id, created_at) "
            "VALUES (:id, :folder, :parent, :client, :time)"
        ), {"id": grant_id, "folder": private_folder, "parent": parent_a,
            "client": client_id, "time": timestamp})
        try:
            with connection.begin_nested():
                connection.execute(text(
                    "INSERT INTO folder_client_grant "
                    "(id, folder_id, parent_gallery_id, client_id, created_at) "
                    "VALUES (:id, :folder, :parent, :client, :time)"
                ), {"id": uuid4().hex, "folder": private_folder, "parent": parent_a,
                    "client": client_id, "time": timestamp})
        except IntegrityError:
            pass
        else:
            raise AssertionError("Atribuição duplicada foi aceita")
        canonical = {
            "id": uuid4().hex, "parent": parent_a, "photo": photo_id,
            "client": client_id, "time": timestamp,
        }
        connection.execute(text(
            "INSERT INTO photo_selection "
            "(id, parent_gallery_id, photo_asset_id, client_id, created_at) "
            "VALUES (:id, :parent, :photo, :client, :time)"
        ), canonical)
        try:
            with connection.begin_nested():
                connection.execute(text(
                    "INSERT INTO photo_selection "
                    "(id, parent_gallery_id, photo_asset_id, client_id, created_at) "
                    "VALUES (:id, :parent, :photo, :client, :time)"
                ), {**canonical, "id": uuid4().hex})
        except IntegrityError:
            pass
        else:
            raise AssertionError("Seleção canônica duplicada foi aceita")
        order = {
            "id": uuid4().hex, "parent": parent_a, "client": client_id,
            "checkout": uuid4().hex, "time": timestamp,
        }
        order_insert = text(
            "INSERT INTO sale_order "
            "(id, parent_gallery_id, client_id, derived_gallery_name_snapshot, "
            "parent_gallery_id_snapshot, parent_gallery_name_snapshot, payment_status, "
            "total_cents, checkout_key, created_at) "
            "VALUES (:id, :parent, :client, 'Galeria legada', :parent, 'Galeria legada', "
            "'pending', 500, :checkout, :time)"
        )
        connection.execute(order_insert, order)
        assert connection.execute(text(
            "SELECT derived_gallery_id_snapshot FROM sale_order WHERE id = :id"
        ), {"id": order["id"]}).scalar_one_or_none() is None
        try:
            with connection.begin_nested():
                connection.execute(order_insert, {
                    **order, "id": uuid4().hex, "checkout": uuid4().hex,
                })
        except IntegrityError:
            pass
        else:
            raise AssertionError("Segundo rascunho canônico simultâneo foi aceito")
