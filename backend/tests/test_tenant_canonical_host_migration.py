import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.test_cloned_gallery_migration import alembic


def test_adds_unique_nullable_host_and_updates_only_unchanged_delivery_default(tmp_path):
    url = f"sqlite:///{(tmp_path / 'tenant-host.sqlite').as_posix()}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE tenant (id CHAR(36) PRIMARY KEY, status VARCHAR(16) NOT NULL, created_at DATETIME NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE notification_setting (tenant_id CHAR(36), event_type VARCHAR(32), whatsapp_body VARCHAR(500))"
        )
        connection.execute(text("INSERT INTO tenant VALUES ('a', 'active', CURRENT_TIMESTAMP), ('b', 'active', CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO notification_setting VALUES ('a', 'order_delivery_ready', 'Suas fotos estão prontas! Acesse Compras para abrir seu álbum.'), ('b', 'order_delivery_ready', 'Mensagem personalizada')"))

    alembic(url, "stamp", "20261014_0080")
    alembic(url, "upgrade", "20261014_0081")
    with engine.begin() as connection:
        assert "canonical_host" in {row["name"] for row in inspect(connection).get_columns("tenant")}
        assert any(item["name"] == "uq_tenant_canonical_host"
                   for item in inspect(connection).get_unique_constraints("tenant"))
        connection.execute(text("UPDATE tenant SET canonical_host='a.fotografo.example.com' WHERE id='a'"))
        connection.execute(text("UPDATE tenant SET canonical_host='b.fotografo.example.com' WHERE id='b'"))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("UPDATE tenant SET canonical_host='a.fotografo.example.com' WHERE id='b'"))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("UPDATE tenant SET canonical_host='Invalid/host' WHERE id='b'"))
        bodies = dict(connection.execute(text("SELECT tenant_id, whatsapp_body FROM notification_setting")).all())
        assert bodies["a"].endswith("{{link_compras}} para abrir seu álbum.")
        assert bodies["b"] == "Mensagem personalizada"
    engine.dispose()
