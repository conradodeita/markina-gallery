from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, text

from tests.test_cloned_gallery_migration import alembic


def test_upgrade_preserves_existing_order(tmp_path):
    url = f"sqlite:///{(tmp_path / 'delivery.sqlite').as_posix()}"
    alembic(url, "upgrade", "20260921_0060")
    engine = create_engine(url)
    owner, order = uuid4().hex, uuid4().hex
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO client (id, full_name, phone_e164) VALUES (:id, 'Teste', '+5511999999999')"), {"id": owner})
        connection.execute(text("""INSERT INTO sale_order
            (id, client_id, derived_gallery_id_snapshot, derived_gallery_name_snapshot,
             parent_gallery_id_snapshot, parent_gallery_name_snapshot, payment_status, total_cents, created_at)
            VALUES (:id, :owner, :gallery, 'Privada', :parent, 'Evento', 'confirmed', 1200, :created)"""),
                           {"id": order, "owner": owner, "gallery": uuid4().hex,
                            "parent": uuid4().hex, "created": datetime.now(UTC)})
    alembic(url, "upgrade", "head")
    with engine.connect() as connection:
        row = connection.execute(text("SELECT payment_status, total_cents, delivery_album_url, delivery_updated_at, delivery_revision FROM sale_order WHERE id=:id"), {"id": order}).one()
        assert row == ("confirmed", 1200, None, None, 0)
    engine.dispose()
