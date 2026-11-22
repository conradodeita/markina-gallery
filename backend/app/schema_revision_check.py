"""Read-only Alembic revision gate for explicit Compose maintenance runs."""

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.auth import database_url


def revisions_match(connection: Connection, script: ScriptDirectory) -> tuple[bool, str]:
    heads = tuple(script.get_heads())
    if len(heads) != 1:
        return False, "head Alembic ausente ou ambígua"

    current = tuple(MigrationContext.configure(connection).get_current_heads())
    if len(current) != 1:
        return False, "revisão do banco ausente ou ambígua"
    if current[0] != heads[0]:
        return False, "revisão do banco difere da head do código"
    return True, f"schema compatível: {current[0]}"


def main() -> int:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    try:
        script = ScriptDirectory.from_config(config)
        engine = create_engine(database_url(), poolclass=NullPool)
        try:
            with engine.connect() as connection:
                matches, message = revisions_match(connection, script)
        finally:
            engine.dispose()
    except (CommandError, OSError, RuntimeError, SQLAlchemyError, ValueError):
        # Database and configuration errors may contain credentials.
        print("falha ao consultar revisões Alembic; verifique banco e configuração")
        return 1
    print(message)
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
