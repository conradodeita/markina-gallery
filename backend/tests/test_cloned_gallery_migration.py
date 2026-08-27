"""Verifica preservação de dados ao atualizar uma base anterior à mudança."""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from subprocess import run
from uuid import uuid4

from sqlalchemy import create_engine, text


def alembic(database_url: str, *arguments: str) -> None:
    backend = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "DATABASE_URL": database_url}
    result = run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=backend,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_upgrade_preserves_existing_client_and_confirmed_order(tmp_path: Path):
    database = tmp_path / "legacy.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260826_0003")
    engine = create_engine(database_url)
    client_id, parent_id, gallery_id, order_id = (uuid4() for _ in range(4))
    timestamp = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO client (id, full_name, phone_e164) VALUES (:id, :name, :phone)"), {"id": client_id.hex, "name": "Cliente legado", "phone": "+5511999999999"})
        connection.execute(text("INSERT INTO parent_gallery (id, name, active, created_at) VALUES (:id, :name, :active, :created_at)"), {"id": parent_id.hex, "name": "Evento legado", "active": True, "created_at": timestamp})
        connection.execute(text("INSERT INTO derived_gallery (id, parent_gallery_id, client_id, name, access_enabled, favorites_enabled, comments_enabled, created_at) VALUES (:id, :parent, :client, :name, :access, :favorites, :comments, :created_at)"), {"id": gallery_id.hex, "parent": parent_id.hex, "client": client_id.hex, "name": "Galeria legado", "access": True, "favorites": False, "comments": False, "created_at": timestamp})
        connection.execute(text("INSERT INTO sale_order (id, derived_gallery_id, client_id, payment_status, total_cents, confirmed_at, created_at) VALUES (:id, :gallery, :client, 'confirmed', 2500, :confirmed_at, :created_at)"), {"id": order_id.hex, "gallery": gallery_id.hex, "client": client_id.hex, "confirmed_at": timestamp, "created_at": timestamp})
    alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        phone = connection.execute(text("SELECT phone_e164, active FROM client_phone WHERE client_id = :client"), {"client": client_id.hex}).one()
        snapshot = connection.execute(text("SELECT client_name_snapshot, client_phone_snapshot FROM sale_order WHERE id = :id"), {"id": order_id.hex}).one()
        folder_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(photo_folder)"))}
        asset_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(photo_asset)"))}
    assert phone == ("+5511999999999", 1)
    assert snapshot == ("Cliente legado", "+5511999999999")
    assert {"id", "name", "status", "position", "released_at"} <= folder_columns
    assert "folder_id" in asset_columns
    alembic(database_url, "downgrade", "20260826_0004")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT full_name FROM client WHERE id = :id"), {"id": client_id.hex}).scalar_one() == "Cliente legado"


def test_gallery_folder_ownership_backfills_without_losing_history(tmp_path: Path):
    database = tmp_path / "folder-ownership.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260827_0005")
    engine = create_engine(database_url)
    client_id, parent_id, gallery_id, photo_id, link_id, selection_id, order_id, item_id = (
        uuid4() for _ in range(8)
    )
    timestamp = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO client (id, full_name, phone_e164) VALUES (:id, :name, :phone)"),
            {"id": client_id.hex, "name": "Cliente legado", "phone": "+5511999999999"},
        )
        connection.execute(
            text(
                """
                INSERT INTO parent_gallery (id, name, active, created_at)
                VALUES (:id, :name, :active, :created_at)
                """
            ),
            {"id": parent_id.hex, "name": "Evento legado", "active": True, "created_at": timestamp},
        )
        connection.execute(
            text(
                """
                INSERT INTO photo_asset
                    (id, parent_gallery_id, folder_id, filename, storage_key, available, created_at)
                VALUES (:id, :parent, NULL, :filename, :storage_key, :available, :created_at)
                """
            ),
            {
                "id": photo_id.hex,
                "parent": parent_id.hex,
                "filename": "legada.jpg",
                "storage_key": "legacy/legada.jpg",
                "available": True,
                "created_at": timestamp,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO derived_gallery
                    (id, parent_gallery_id, client_id, name, access_enabled,
                     favorites_enabled, comments_enabled, created_at)
                VALUES
                    (:id, :parent, :client, :name, :access, :favorites, :comments, :created_at)
                """
            ),
            {
                "id": gallery_id.hex,
                "parent": parent_id.hex,
                "client": client_id.hex,
                "name": "Galeria legada",
                "access": True,
                "favorites": False,
                "comments": False,
                "created_at": timestamp,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO derived_gallery_photo
                    (id, derived_gallery_id, photo_asset_id, created_at)
                VALUES (:id, :gallery, :photo, :created_at)
                """
            ),
            {"id": link_id.hex, "gallery": gallery_id.hex, "photo": photo_id.hex, "created_at": timestamp},
        )
        connection.execute(
            text(
                """
                INSERT INTO photo_selection
                    (id, derived_gallery_id, photo_asset_id, client_id, created_at)
                VALUES (:id, :gallery, :photo, :client, :created_at)
                """
            ),
            {
                "id": selection_id.hex,
                "gallery": gallery_id.hex,
                "photo": photo_id.hex,
                "client": client_id.hex,
                "created_at": timestamp,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO sale_order
                    (id, derived_gallery_id, client_id, payment_status, total_cents,
                     confirmed_at, created_at, client_name_snapshot, client_phone_snapshot)
                VALUES
                    (:id, :gallery, :client, 'confirmed', 1500, :confirmed_at, :created_at,
                     :client_name, :client_phone)
                """
            ),
            {
                "id": order_id.hex,
                "gallery": gallery_id.hex,
                "client": client_id.hex,
                "confirmed_at": timestamp,
                "created_at": timestamp,
                "client_name": "Cliente legado",
                "client_phone": "+5511999999999",
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO sale_order_item
                    (id, sale_order_id, photo_asset_id, filename_snapshot, unit_price_cents)
                VALUES (:id, :order_id, :photo_id, :filename, 1500)
                """
            ),
            {
                "id": item_id.hex,
                "order_id": order_id.hex,
                "photo_id": photo_id.hex,
                "filename": "legada.jpg",
            },
        )

    alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        folder_id = connection.execute(
            text("SELECT folder_id FROM photo_asset WHERE id = :id"), {"id": photo_id.hex}
        ).scalar_one()
        folder = connection.execute(
            text(
                "SELECT parent_gallery_id, name, status FROM photo_folder WHERE id = :id"
            ),
            {"id": folder_id},
        ).one()
        counts = tuple(
            connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in ("photo_asset", "derived_gallery_photo", "photo_selection", "sale_order_item")
        )
        folder_column = next(
            row for row in connection.execute(text("PRAGMA table_info(photo_asset)")) if row[1] == "folder_id"
        )
    assert folder == (parent_id.hex, "Importação anterior", "released")
    assert counts == (1, 1, 1, 1)
    assert folder_column[3] == 1

    alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM photo_folder")).scalar_one() == 1

    alembic(database_url, "downgrade", "20260827_0005")
    with engine.connect() as connection:
        folder_column = next(
            row for row in connection.execute(text("PRAGMA table_info(photo_asset)")) if row[1] == "folder_id"
        )
        assert folder_column[3] == 0
        assert connection.execute(
            text("SELECT folder_id FROM photo_asset WHERE id = :id"), {"id": photo_id.hex}
        ).scalar_one() == folder_id
