"""A migration updates only the unchanged private-photo notification default."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

OLD_DEFAULT = "Novas fotos disponíveis na sua galeria."
NEW_DEFAULT = (
    "Essa mensagem é automática! Novas fotos disponíveis na sua galeria. "
    "Acesso no link: {{link_galeria}}."
)


def test_migration_0084_updates_only_exact_default_and_leaves_historical_events_untouched():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE notification_setting "
            "(tenant_id TEXT, event_type TEXT, whatsapp_body TEXT, version INTEGER, updated_at DATETIME, "
            "PRIMARY KEY (tenant_id, event_type))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE notification_event "
            "(id TEXT PRIMARY KEY, whatsapp_body TEXT, template_version INTEGER)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE notification_delivery "
            "(id TEXT PRIMARY KEY, status TEXT, attempts INTEGER)"
        )
        connection.execute(text(
            "INSERT INTO notification_setting VALUES "
            "('tenant-default', 'private_photos_ready', :old_body, 1, CURRENT_TIMESTAMP), "
            "('tenant-custom', 'private_photos_ready', 'Personalizada {{cliente}}', 5, CURRENT_TIMESTAMP), "
            "('other-event', 'payment_confirmed', :old_body, 2, CURRENT_TIMESTAMP)"
        ), {"old_body": OLD_DEFAULT})
        connection.execute(text(
            "INSERT INTO notification_event VALUES ('event-id', :old_body, 1)"
        ), {"old_body": OLD_DEFAULT})
        connection.exec_driver_sql("INSERT INTO notification_delivery VALUES ('delivery-id', 'queued', 0)")

        migration_path = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "20261017_0084_private_photo_gallery_link.py"
        spec = importlib.util.spec_from_file_location("private_photo_gallery_link_migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        settings = dict(connection.execute(text(
            "SELECT tenant_id, whatsapp_body FROM notification_setting"
        )).all())
        versions = dict(connection.execute(text(
            "SELECT tenant_id, version FROM notification_setting"
        )).all())
        assert settings["tenant-default"] == NEW_DEFAULT
        assert versions["tenant-default"] == 2
        assert settings["tenant-custom"] == "Personalizada {{cliente}}"
        assert versions["tenant-custom"] == 5
        assert settings["other-event"] == OLD_DEFAULT
        assert versions["other-event"] == 2
        assert connection.execute(text(
            "SELECT whatsapp_body, template_version FROM notification_event WHERE id = 'event-id'"
        )).one() == (OLD_DEFAULT, 1)
        assert connection.execute(text(
            "SELECT status, attempts FROM notification_delivery WHERE id = 'delivery-id'"
        )).one() == ("queued", 0)

        migration.downgrade()
        downgraded = dict(connection.execute(text(
            "SELECT tenant_id, whatsapp_body FROM notification_setting"
        )).all())
        assert downgraded["tenant-default"] == OLD_DEFAULT
        assert downgraded["tenant-custom"] == "Personalizada {{cliente}}"
        assert downgraded["other-event"] == OLD_DEFAULT
    engine.dispose()
