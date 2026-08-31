import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text


def test_otp_privacy_migration_is_additive_and_keeps_active_challenges(
    tmp_path: Path,
) -> None:
    database = tmp_path / "otp-privacy.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    backend = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "DATABASE_URL": database_url}

    def alembic(*arguments: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=backend,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    alembic("upgrade", "20260831_0030")
    migrated_engine = create_engine(database_url)
    challenge_id = uuid4().hex
    delivery_id = uuid4().hex
    instant = datetime.now(UTC).replace(tzinfo=None)
    with migrated_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO auth_challenge "
                "(id, kind, subject, secret_hash, expires_at, attempts, resend_count, "
                "used_at, parent_gallery_id, gallery_capability_id, return_to, client_name) "
                "VALUES (:id, 'client_otp', :phone, 'hash', :expires, 0, 0, NULL, "
                "NULL, NULL, NULL, :name)"
            ),
            {
                "id": challenge_id,
                "phone": "+5511777777799",
                "expires": instant + timedelta(minutes=5),
                "name": "Cliente em desafio ativo",
            },
        )
        connection.execute(
            text(
                "INSERT INTO whatsapp_delivery "
                "(id, kind, source_type, source_id, recipient_phone, template_kind, "
                "idempotency_key, status, attempts, created_at, updated_at) "
                "VALUES (:id, 'otp', 'auth_challenge', :source_id, :phone, "
                "'client_otp', :key, 'queued', 0, :instant, :instant)"
            ),
            {
                "id": delivery_id,
                "source_id": challenge_id,
                "phone": "+5511777777799",
                "key": f"otp:{challenge_id}:0",
                "instant": instant,
            },
        )

    alembic("upgrade", "head")
    inspector = inspect(migrated_engine)
    challenge_columns = {
        column["name"]: column for column in inspector.get_columns("auth_challenge")
    }
    delivery_columns = {
        column["name"]: column
        for column in inspector.get_columns("whatsapp_delivery")
    }
    assert challenge_columns["subject"]["nullable"] is True
    assert "subject_fingerprint" in challenge_columns
    assert delivery_columns["recipient_phone"]["nullable"] is True
    assert "recipient_fingerprint" in delivery_columns
    with migrated_engine.begin() as connection:
        assert connection.scalar(
            text("SELECT subject FROM auth_challenge WHERE id = :id"),
            {"id": challenge_id},
        ) == "+5511777777799"
        assert connection.scalar(
            text("SELECT recipient_phone FROM whatsapp_delivery WHERE id = :id"),
            {"id": delivery_id},
        ) == "+5511777777799"
        connection.execute(
            text("UPDATE auth_challenge SET subject = NULL WHERE id = :id"),
            {"id": challenge_id},
        )
        connection.execute(
            text(
                "UPDATE whatsapp_delivery SET recipient_phone = NULL WHERE id = :id"
            ),
            {"id": delivery_id},
        )

    alembic("downgrade", "20260831_0030")
    inspector = inspect(migrated_engine)
    assert "subject_fingerprint" not in {
        column["name"] for column in inspector.get_columns("auth_challenge")
    }
    with migrated_engine.connect() as connection:
        assert connection.scalar(
            text("SELECT subject FROM auth_challenge WHERE id = :id"),
            {"id": challenge_id},
        ) == "minimized"
        assert connection.scalar(
            text("SELECT recipient_phone FROM whatsapp_delivery WHERE id = :id"),
            {"id": delivery_id},
        ) == "minimized"
