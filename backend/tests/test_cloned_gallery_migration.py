"""Verifica preservação de dados ao atualizar uma base anterior à mudança."""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from subprocess import run
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


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
    inspector = inspect(engine)
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
    assert {item["name"] for item in inspector.get_indexes("photo_asset")} >= {
        "ix_photo_asset_folder_id",
        "ix_photo_asset_parent_gallery_id",
    }
    assert any(
        constraint["name"] == "uq_photo_folder_id_parent"
        and constraint["column_names"] == ["id", "parent_gallery_id"]
        for constraint in inspector.get_unique_constraints("photo_folder")
    )
    assert any(
        foreign_key["name"] == "fk_photo_asset_folder_gallery"
        and foreign_key["constrained_columns"] == ["folder_id", "parent_gallery_id"]
        and foreign_key["referred_columns"] == ["id", "parent_gallery_id"]
        for foreign_key in inspector.get_foreign_keys("photo_asset")
    )

    alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM photo_folder")).scalar_one() == 1

    alembic(database_url, "downgrade", "20260827_0005")
    inspector = inspect(engine)
    with engine.connect() as connection:
        folder_column = next(
            row for row in connection.execute(text("PRAGMA table_info(photo_asset)")) if row[1] == "folder_id"
        )
        assert folder_column[3] == 0
        assert connection.execute(
            text("SELECT folder_id FROM photo_asset WHERE id = :id"), {"id": photo_id.hex}
        ).scalar_one() == folder_id
    assert any(
        foreign_key["name"] == "fk_photo_asset_folder"
        and foreign_key["constrained_columns"] == ["folder_id"]
        for foreign_key in inspector.get_foreign_keys("photo_asset")
    )
    assert not any(
        constraint["name"] == "uq_photo_folder_id_parent"
        for constraint in inspector.get_unique_constraints("photo_folder")
    )


def test_gallery_folder_ownership_on_postgresql_preserves_constraints_and_rollback():
    database_url = os.getenv("TEST_POSTGRES_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_POSTGRES_DATABASE_URL não configurada")

    alembic(database_url, "upgrade", "20260827_0005")
    engine = create_engine(database_url)
    first_parent_id, second_parent_id, first_photo_id, second_photo_id = (
        uuid4() for _ in range(4)
    )
    existing_folder_id, invalid_photo_id = uuid4(), uuid4()
    timestamp = datetime.now(UTC)
    with engine.begin() as connection:
        for parent_id, name in (
            (first_parent_id, "Evento com pasta"),
            (second_parent_id, "Evento sem pasta"),
        ):
            connection.execute(
                text(
                    """
                    INSERT INTO parent_gallery (id, name, active, created_at)
                    VALUES (:id, :name, true, :created_at)
                    """
                ),
                {"id": parent_id, "name": name, "created_at": timestamp},
            )
        connection.execute(
            text(
                """
                INSERT INTO photo_folder
                    (id, parent_gallery_id, name, status, position, created_at, updated_at)
                VALUES (:id, :parent_id, 'Pasta existente', 'preparing', 0, :created_at, :updated_at)
                """
            ),
            {
                "id": existing_folder_id,
                "parent_id": first_parent_id,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )
        for photo_id, parent_id, filename in (
            (first_photo_id, first_parent_id, "primeira.jpg"),
            (second_photo_id, second_parent_id, "segunda.jpg"),
        ):
            connection.execute(
                text(
                    """
                    INSERT INTO photo_asset
                        (id, parent_gallery_id, folder_id, filename, storage_key, available, created_at)
                    VALUES (:id, :parent_id, NULL, :filename, :storage_key, true, :created_at)
                    """
                ),
                {
                    "id": photo_id,
                    "parent_id": parent_id,
                    "filename": filename,
                    "storage_key": f"legacy/{filename}",
                    "created_at": timestamp,
                },
            )

    alembic(database_url, "upgrade", "20260827_0006")
    inspector = inspect(engine)
    folder_column = next(
        column for column in inspector.get_columns("photo_asset") if column["name"] == "folder_id"
    )
    assert folder_column["nullable"] is False
    assert {item["name"] for item in inspector.get_indexes("photo_asset")} >= {
        "ix_photo_asset_folder_id",
        "ix_photo_asset_parent_gallery_id",
    }
    assert any(
        constraint["name"] == "uq_photo_folder_id_parent"
        and constraint["column_names"] == ["id", "parent_gallery_id"]
        for constraint in inspector.get_unique_constraints("photo_folder")
    )
    assert any(
        foreign_key["name"] == "fk_photo_asset_folder_gallery"
        and foreign_key["constrained_columns"] == ["folder_id", "parent_gallery_id"]
        and foreign_key["referred_columns"] == ["id", "parent_gallery_id"]
        for foreign_key in inspector.get_foreign_keys("photo_asset")
    )
    with engine.connect() as connection:
        compatibility_rows = connection.execute(
            text(
                """
                SELECT parent_gallery_id, position, status
                FROM photo_folder
                WHERE name = 'Importação anterior'
                ORDER BY parent_gallery_id
                """
            )
        ).all()
    assert sorted(row.position for row in compatibility_rows) == [0, 1]
    assert {row.status for row in compatibility_rows} == {"released"}

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO photo_asset
                    (id, parent_gallery_id, folder_id, filename, storage_key, available, created_at)
                VALUES (:id, :parent_id, :folder_id, 'invalida.jpg', 'invalid/invalida.jpg',
                        true, :created_at)
                """
            ),
            {
                "id": invalid_photo_id,
                "parent_id": second_parent_id,
                "folder_id": existing_folder_id,
                "created_at": timestamp,
            },
        )

    alembic(database_url, "downgrade", "20260827_0005")
    inspector = inspect(engine)
    folder_column = next(
        column for column in inspector.get_columns("photo_asset") if column["name"] == "folder_id"
    )
    assert folder_column["nullable"] is True
    assert any(
        foreign_key["name"] == "fk_photo_asset_folder"
        and foreign_key["constrained_columns"] == ["folder_id"]
        for foreign_key in inspector.get_foreign_keys("photo_asset")
    )
    assert not any(
        constraint["name"] == "uq_photo_folder_id_parent"
        for constraint in inspector.get_unique_constraints("photo_folder")
    )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM photo_folder WHERE name = 'Importação anterior'")
        ).scalar_one() == 2
        assert connection.execute(
            text("SELECT COUNT(*) FROM photo_asset WHERE folder_id IS NOT NULL")
        ).scalar_one() == 2


def test_shared_private_membership_migration_backfills_legacy_owners(tmp_path: Path):
    database = tmp_path / "shared-private-memberships.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260831_0033")
    engine = create_engine(database_url)
    timestamp = datetime.now(UTC)
    first_client, second_client, parent_id, first_private, second_private = (
        uuid4() for _ in range(5)
    )
    with engine.begin() as connection:
        for client_id, name, phone in (
            (first_client, "Primeira cliente", "+5511999999601"),
            (second_client, "Segunda cliente", "+5511999999602"),
        ):
            connection.execute(
                text(
                    "INSERT INTO client (id, full_name, phone_e164) "
                    "VALUES (:id, :name, :phone)"
                ),
                {"id": client_id.hex, "name": name, "phone": phone},
            )
        connection.execute(
            text(
                "INSERT INTO parent_gallery (id, name, active, created_at) "
                "VALUES (:id, 'Origem legada', 1, :created_at)"
            ),
            {"id": parent_id.hex, "created_at": timestamp},
        )
        for gallery_id, client_id, name in (
            (first_private, first_client, "Primeira privada"),
            (second_private, second_client, "Segunda privada"),
        ):
            connection.execute(
                text(
                    """
                    INSERT INTO derived_gallery
                        (id, parent_gallery_id, client_id, name, access_enabled,
                         favorites_enabled, comments_enabled, created_at)
                    VALUES
                        (:id, :parent, :client, :name, 1, 0, 0, :created_at)
                    """
                ),
                {
                    "id": gallery_id.hex,
                    "parent": parent_id.hex,
                    "client": client_id.hex,
                    "name": name,
                    "created_at": timestamp,
                },
            )

    alembic(database_url, "upgrade", "head")
    inspector = inspect(engine)
    with engine.connect() as connection:
        memberships = connection.execute(
            text(
                """
                SELECT derived_gallery_id, parent_gallery_id, client_id, status
                FROM derived_gallery_membership
                ORDER BY client_id
                """
            )
        ).all()
    assert set(memberships) == {
        (first_private.hex, parent_id.hex, first_client.hex, "active"),
        (second_private.hex, parent_id.hex, second_client.hex, "active"),
    }
    assert any(
        constraint["name"] == "uq_membership_parent_client"
        for constraint in inspector.get_unique_constraints("derived_gallery_membership")
    )
    assert any(
        constraint["name"] == "uq_derived_gallery_id_parent"
        for constraint in inspector.get_unique_constraints("derived_gallery")
    )

    alembic(database_url, "downgrade", "20260831_0033")
    inspector = inspect(engine)
    assert "derived_gallery_membership" not in inspector.get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM derived_gallery")).scalar_one() == 2


def test_shared_private_membership_migration_aborts_on_owner_conflict(tmp_path: Path):
    database = tmp_path / "shared-private-conflict.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260831_0033")
    engine = create_engine(database_url)
    timestamp = datetime.now(UTC)
    client_id, parent_id, first_private, second_private = (uuid4() for _ in range(4))
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX ix_derived_gallery_parent_client"))
        connection.execute(
            text(
                "INSERT INTO client (id, full_name, phone_e164) "
                "VALUES (:id, 'Cliente conflitante', '+5511999999603')"
            ),
            {"id": client_id.hex},
        )
        connection.execute(
            text(
                "INSERT INTO parent_gallery (id, name, active, created_at) "
                "VALUES (:id, 'Origem conflitante', 1, :created_at)"
            ),
            {"id": parent_id.hex, "created_at": timestamp},
        )
        for gallery_id in (first_private, second_private):
            connection.execute(
                text(
                    """
                    INSERT INTO derived_gallery
                        (id, parent_gallery_id, client_id, name, access_enabled,
                         favorites_enabled, comments_enabled, created_at)
                    VALUES
                        (:id, :parent, :client, 'Privada conflitante', 1, 0, 0, :created_at)
                    """
                ),
                {
                    "id": gallery_id.hex,
                    "parent": parent_id.hex,
                    "client": client_id.hex,
                    "created_at": timestamp,
                },
            )

    backend = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "DATABASE_URL": database_url}
    result = run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "upgrade foi interrompido sem mesclar dados" in f"{result.stdout}\n{result.stderr}"
    inspector = inspect(engine)
    assert "derived_gallery_membership" not in inspector.get_table_names()


def test_progressive_pricing_migration_preserves_legacy_semantics_and_orders(
    tmp_path: Path,
):
    database = tmp_path / "progressive-pricing.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260901_0036")
    engine = create_engine(database_url)
    timestamp = datetime.now(UTC)
    client_id, single_parent, multi_parent, empty_parent, private_id, order_id = (
        uuid4() for _ in range(6)
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO client (id, full_name, phone_e164) "
                "VALUES (:id, 'Cliente preço', '+5511999999604')"
            ),
            {"id": client_id.hex},
        )
        for parent_id, name in (
            (single_parent, "Preço único"),
            (multi_parent, "Preço volume"),
            (empty_parent, "Sem preço"),
        ):
            connection.execute(
                text(
                    "INSERT INTO parent_gallery (id, name, active, created_at) "
                    "VALUES (:id, :name, 1, :created_at)"
                ),
                {"id": parent_id.hex, "name": name, "created_at": timestamp},
            )
        connection.execute(
            text(
                """
                INSERT INTO derived_gallery
                    (id, parent_gallery_id, client_id, name, access_enabled,
                     favorites_enabled, comments_enabled, created_at)
                VALUES (:id, :parent, :client, 'Privada preço', 1, 0, 0, :created_at)
                """
            ),
            {
                "id": private_id.hex,
                "parent": single_parent.hex,
                "client": client_id.hex,
                "created_at": timestamp,
            },
        )
        rules = (
            (single_parent, 1, None, 700),
            (multi_parent, 1, 30, 700),
            (multi_parent, 31, None, 600),
        )
        for parent_id, minimum, maximum, unit_price in rules:
            connection.execute(
                text(
                    """
                    INSERT INTO price_rule
                        (id, parent_gallery_id, minimum_quantity, maximum_quantity,
                         unit_price_cents, created_at, updated_at)
                    VALUES
                        (:id, :parent, :minimum, :maximum, :unit_price,
                         :created_at, :updated_at)
                    """
                ),
                {
                    "id": uuid4().hex,
                    "parent": parent_id.hex,
                    "minimum": minimum,
                    "maximum": maximum,
                    "unit_price": unit_price,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
            )
        original_snapshot = {"mode": "legacy_volume", "unit_price_cents": 700}
        connection.execute(
            text(
                """
                INSERT INTO sale_order
                    (id, derived_gallery_id, client_id, derived_gallery_id_snapshot,
                     derived_gallery_name_snapshot, parent_gallery_id_snapshot,
                     parent_gallery_name_snapshot, payment_status, total_cents,
                     price_rule_snapshot, created_at)
                VALUES
                    (:id, :private_id, :client_id, :private_id, 'Privada preço',
                     :parent_id, 'Preço único', 'confirmed', 700, :snapshot, :created_at)
                """
            ),
            {
                "id": order_id.hex,
                "private_id": private_id.hex,
                "client_id": client_id.hex,
                "parent_id": single_parent.hex,
                "snapshot": json.dumps(original_snapshot),
                "created_at": timestamp,
            },
        )

    alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        single = connection.execute(
            text(
                "SELECT pricing_mode, fixed_unit_price_cents, pricing_review_required "
                "FROM parent_gallery WHERE id = :id"
            ),
            {"id": single_parent.hex},
        ).one()
        multi = connection.execute(
            text(
                "SELECT pricing_mode, fixed_unit_price_cents, pricing_review_required, "
                "pricing_snapshot FROM parent_gallery WHERE id = :id"
            ),
            {"id": multi_parent.hex},
        ).one()
        empty = connection.execute(
            text(
                "SELECT pricing_mode, fixed_unit_price_cents, pricing_review_required "
                "FROM parent_gallery WHERE id = :id"
            ),
            {"id": empty_parent.hex},
        ).one()
        preserved_snapshot = connection.execute(
            text("SELECT price_rule_snapshot FROM sale_order WHERE id = :id"),
            {"id": order_id.hex},
        ).scalar_one()
    assert single == ("fixed", 700, 0)
    assert multi[:3] == ("legacy_volume", None, 1)
    assert json.loads(multi.pricing_snapshot)["tiers"][1]["unit_price_cents"] == 600
    assert empty == ("fixed", None, 1)
    assert json.loads(preserved_snapshot) == original_snapshot


def test_pix_source_migration_converges_safe_values_and_flags_divergence(tmp_path) -> None:
    database = tmp_path / "pix-source.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260901_0037")
    engine = create_engine(database_url)
    rows = [
        (str(uuid4()), str(uuid4()), None, "qr-only"),
        (str(uuid4()), str(uuid4()), "same", "same"),
        (str(uuid4()), str(uuid4()), "copy", "different"),
    ]
    with engine.begin() as connection:
        for row_id, parent_id, copy_paste, qr_payload in rows:
            connection.execute(
                text(
                    "INSERT INTO pix_checkout_settings "
                    "(id, parent_gallery_id, copy_paste, qr_code_payload, instructions, updated_at) "
                    "VALUES (:id, :parent_id, :copy_paste, :qr_payload, NULL, :updated_at)"
                ),
                {
                    "id": row_id,
                    "parent_id": parent_id,
                    "copy_paste": copy_paste,
                    "qr_payload": qr_payload,
                    "updated_at": datetime.now(UTC),
                },
            )

    alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        migrated = connection.execute(
            text(
                "SELECT copy_paste, qr_code_payload, review_required, input_type "
                "FROM pix_checkout_settings ORDER BY copy_paste"
            )
        ).mappings().all()

    by_copy = {row["copy_paste"]: row for row in migrated}
    assert by_copy["qr-only"]["qr_code_payload"] is None
    assert by_copy["qr-only"]["input_type"] == "br_code"
    assert by_copy["same"]["qr_code_payload"] is None
    assert by_copy["same"]["input_type"] == "br_code"
    assert by_copy["copy"]["qr_code_payload"] == "different"
    assert by_copy["copy"]["input_type"] == "br_code"
    assert bool(by_copy["copy"]["review_required"]) is True


def test_pix_simple_key_columns_migration_is_reversible(tmp_path: Path) -> None:
    database = tmp_path / "pix-simple-key-columns.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260901_0040")
    engine = create_engine(database_url)

    alembic(database_url, "upgrade", "20260902_0041")
    with engine.connect() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(pix_checkout_settings)"))
        }
    assert {"input_type", "pix_key", "receiver_name", "receiver_city"} <= columns

    alembic(database_url, "downgrade", "20260901_0040")
    with engine.connect() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(pix_checkout_settings)"))
        }
    assert {"input_type", "pix_key", "receiver_name", "receiver_city"}.isdisjoint(columns)


def test_auto_publish_migration_reconciles_only_ready_protected_content(tmp_path: Path) -> None:
    database = tmp_path / "auto-publish-protected-content.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260902_0041")
    engine = create_engine(database_url)
    parent_id, content_folder_id, cover_folder_id = (uuid4() for _ in range(3))
    ready_id, pending_id, cover_id = (uuid4() for _ in range(3))
    ready_derivative_id, cover_derivative_id = (uuid4() for _ in range(2))
    timestamp = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO parent_gallery (id, name, active, created_at) VALUES (:id, 'Evento', 1, :created_at)"),
            {"id": parent_id.hex, "created_at": timestamp},
        )
        for folder_id, purpose in (
            (content_folder_id, "content"),
            (cover_folder_id, "cover_assets"),
        ):
            connection.execute(
                text("INSERT INTO photo_folder (id, parent_gallery_id, name, status, purpose, position, created_at, updated_at) VALUES (:id, :parent_id, :name, 'preparing', :purpose, :position, :created_at, :created_at)"),
                {
                    "id": folder_id.hex,
                    "parent_id": parent_id.hex,
                    "name": purpose,
                    "purpose": purpose,
                    "position": 0 if purpose == "content" else -1,
                    "created_at": timestamp,
                },
            )
        for photo_id, folder_id, filename in (
            (ready_id, content_folder_id, "ready.jpg"),
            (pending_id, content_folder_id, "pending.jpg"),
            (cover_id, cover_folder_id, "cover.jpg"),
        ):
            connection.execute(
                text("INSERT INTO photo_asset (id, parent_gallery_id, folder_id, filename, storage_key, available, created_at) VALUES (:id, :parent_id, :folder_id, :filename, :storage_key, 0, :created_at)"),
                {
                    "id": photo_id.hex,
                    "parent_id": parent_id.hex,
                    "folder_id": folder_id.hex,
                    "filename": filename,
                    "storage_key": f"migration/{filename}",
                    "created_at": timestamp,
                },
            )
        for derivative_id, photo_id, path in (
            (ready_derivative_id, ready_id, "ready/client_preview.jpg"),
            (cover_derivative_id, cover_id, "cover/client_preview.jpg"),
        ):
            connection.execute(
                text("INSERT INTO media_derivative (id, photo_asset_id, variant, relative_path, status, created_at, updated_at) VALUES (:id, :photo_id, 'client_preview', :path, 'ready', :created_at, :created_at)"),
                {
                    "id": derivative_id.hex,
                    "photo_id": photo_id.hex,
                    "path": path,
                    "created_at": timestamp,
                },
            )

    alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        availability = dict(
            connection.execute(
                text("SELECT filename, available FROM photo_asset ORDER BY filename")
            ).all()
        )
        folder_states = dict(
            connection.execute(
                text("SELECT purpose, status FROM photo_folder ORDER BY purpose")
            ).all()
        )
    assert availability == {"cover.jpg": 0, "pending.jpg": 0, "ready.jpg": 1}
    assert folder_states == {"content": "released", "cover_assets": "preparing"}


def test_private_photo_origins_backfill_existing_justification(tmp_path: Path) -> None:
    database = tmp_path / "private-photo-origins.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260901_0039")
    engine = create_engine(database_url)
    client_id, parent_id, gallery_id, folder_id, photo_id, reference_id = (
        uuid4() for _ in range(6)
    )
    timestamp = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO client (id, full_name, phone_e164) VALUES (:id, :name, :phone)"),
            {"id": client_id.hex, "name": "Cliente origem", "phone": "+5511999999499"},
        )
        connection.execute(
            text("INSERT INTO parent_gallery (id, name, active, created_at) VALUES (:id, :name, 1, :created_at)"),
            {"id": parent_id.hex, "name": "Origem", "created_at": timestamp},
        )
        connection.execute(
            text("INSERT INTO photo_folder (id, parent_gallery_id, name, status, position, purpose, created_at, updated_at) VALUES (:id, :parent_id, :name, 'released', 0, 'content', :created_at, :created_at)"),
            {"id": folder_id.hex, "parent_id": parent_id.hex, "name": "Lote", "created_at": timestamp},
        )
        connection.execute(
            text("INSERT INTO photo_asset (id, parent_gallery_id, folder_id, filename, storage_key, available, created_at) VALUES (:id, :parent_id, :folder_id, :filename, :storage_key, 1, :created_at)"),
            {"id": photo_id.hex, "parent_id": parent_id.hex, "folder_id": folder_id.hex, "filename": "foto.jpg", "storage_key": "origem/foto.jpg", "created_at": timestamp},
        )
        connection.execute(
            text("INSERT INTO derived_gallery (id, parent_gallery_id, client_id, name, access_enabled, favorites_enabled, comments_enabled, created_at) VALUES (:id, :parent_id, :client_id, :name, 1, 0, 0, :created_at)"),
            {"id": gallery_id.hex, "parent_id": parent_id.hex, "client_id": client_id.hex, "name": "Privada", "created_at": timestamp},
        )
        connection.execute(
            text("INSERT INTO derived_gallery_photo (id, derived_gallery_id, photo_asset_id, origin, created_at) VALUES (:id, :gallery_id, :photo_id, 'client', :created_at)"),
            {"id": reference_id.hex, "gallery_id": gallery_id.hex, "photo_id": photo_id.hex, "created_at": timestamp},
        )

    alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        origin = connection.execute(
            text("SELECT origin FROM derived_gallery_photo_origin WHERE derived_gallery_photo_id = :reference_id"),
            {"reference_id": reference_id.hex},
        ).scalar_one()
    assert origin == "client"


def test_parent_gallery_cover_migration_is_reversible(tmp_path: Path):
    database = tmp_path / "parent-gallery-cover.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260827_0006")
    engine = create_engine(database_url)
    parent_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO parent_gallery (id, name, active, created_at) VALUES (:id, :name, :active, :created_at)"),
            {"id": parent_id.hex, "name": "Evento legado", "active": True, "created_at": datetime.now(UTC)},
        )
    alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(parent_gallery)"))}
        assert connection.execute(
            text("SELECT cover_photo_id FROM parent_gallery WHERE id = :id"), {"id": parent_id.hex}
        ).scalar_one() is None
    assert "cover_photo_id" in columns

    alembic(database_url, "downgrade", "20260827_0006")
    with engine.connect() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(parent_gallery)"))}
    assert "cover_photo_id" not in columns
