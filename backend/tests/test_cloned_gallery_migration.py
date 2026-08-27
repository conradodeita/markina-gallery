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
