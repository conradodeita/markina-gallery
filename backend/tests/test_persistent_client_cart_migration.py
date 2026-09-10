"""Valida a migration aditiva do carrinho persistente da cliente."""

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
    result = run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=backend,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def _insert_order(
    connection,
    *,
    order_id,
    gallery_id,
    client_id,
    parent_id,
    created_at,
    checkout_key,
    native_uuid: bool,
) -> None:
    identifier = (lambda value: value) if native_uuid else (lambda value: value.hex)
    connection.execute(
        text(
            "INSERT INTO sale_order "
            "(id, derived_gallery_id, client_id, payment_status, total_cents, created_at, "
            "checkout_key, derived_gallery_id_snapshot, derived_gallery_name_snapshot, "
            "parent_gallery_id_snapshot, parent_gallery_name_snapshot) "
            "VALUES (:id, :gallery_id, :client_id, 'pending', 700, :created_at, "
            ":checkout_key, :gallery_id, 'Privada', :parent_id, 'Evento')"
        ),
        {
            "id": identifier(order_id),
            "gallery_id": identifier(gallery_id),
            "client_id": identifier(client_id),
            "parent_id": identifier(parent_id),
            "created_at": created_at,
            "checkout_key": checkout_key,
        },
    )


def exercise_cart_migration(database_url: str) -> None:
    alembic(database_url, "upgrade", "20260909_0052")
    engine = create_engine(database_url)
    native_uuid = engine.dialect.name == "postgresql"
    identifier = (lambda value: value) if native_uuid else (lambda value: value.hex)
    client_id, parent_id, gallery_id, legacy_order_id = (uuid4() for _ in range(4))
    created_at = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO client (id, full_name, phone_e164) VALUES (:id, 'Cliente', '+5511999990000')"),
            {"id": identifier(client_id)},
        )
        connection.execute(
            text(
                "INSERT INTO parent_gallery (id, name, active, created_at) "
                "VALUES (:id, 'Evento', :active, :created_at)"
            ),
            {"id": identifier(parent_id), "active": True, "created_at": created_at},
        )
        connection.execute(
            text(
                "INSERT INTO derived_gallery "
                "(id, parent_gallery_id, client_id, name, access_enabled, favorites_enabled, "
                "comments_enabled, created_at) VALUES "
                "(:id, :parent_id, :client_id, 'Privada', :enabled, :enabled, "
                ":enabled, :created_at)"
            ),
            {
                "id": identifier(gallery_id),
                "parent_id": identifier(parent_id),
                "client_id": identifier(client_id),
                "enabled": True,
                "created_at": created_at,
            },
        )
        _insert_order(
            connection,
            order_id=legacy_order_id,
            gallery_id=gallery_id,
            client_id=client_id,
            parent_id=parent_id,
            created_at=created_at,
            checkout_key="legacy-order",
            native_uuid=native_uuid,
        )

    alembic(database_url, "upgrade", "head")
    assert "frozen_at" in {
        column["name"] for column in inspect(engine).get_columns("sale_order")
    }
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT frozen_at FROM sale_order WHERE id = :id"),
            {"id": identifier(legacy_order_id)},
        ).scalar_one() is not None

    first_draft_id, duplicate_draft_id = uuid4(), uuid4()
    with engine.begin() as connection:
        _insert_order(
            connection,
            order_id=first_draft_id,
            gallery_id=gallery_id,
            client_id=client_id,
            parent_id=parent_id,
            created_at=created_at,
            checkout_key="draft-one",
            native_uuid=native_uuid,
        )
    with pytest.raises(IntegrityError), engine.begin() as connection:
        _insert_order(
            connection,
            order_id=duplicate_draft_id,
            gallery_id=gallery_id,
            client_id=client_id,
            parent_id=parent_id,
            created_at=created_at,
            checkout_key="draft-two",
            native_uuid=native_uuid,
        )

    alembic(database_url, "downgrade", "20260909_0052")
    assert "frozen_at" not in {
        column["name"] for column in inspect(engine).get_columns("sale_order")
    }
    alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM sale_order WHERE frozen_at IS NULL")
        ).scalar_one() == 0


def test_cart_migration_freezes_legacy_and_limits_editable_draft(tmp_path: Path) -> None:
    exercise_cart_migration(
        f"sqlite:///{(tmp_path / 'persistent-cart.sqlite').as_posix()}"
    )


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_DATABASE_URL"),
    reason="TEST_POSTGRES_DATABASE_URL não configurada",
)
def test_cart_migration_cycle_on_postgresql() -> None:
    exercise_cart_migration(os.environ["TEST_POSTGRES_DATABASE_URL"])
