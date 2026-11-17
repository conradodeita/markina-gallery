"""DDL de testes sem alterar o metadata compartilhado pelos modelos ORM."""

from copy import deepcopy

from app.auth import Base


def create_test_schema(bind, *, exclude_tables=()):
    # PostgreSQL emits cyclic FKs via ALTER TABLE. SQLAlchemy attaches DDL
    # rules to those constraints, which would suppress later SQLite FKs.
    metadata = deepcopy(Base.metadata)
    metadata.create_all(bind, tables=[
        table for table in metadata.tables.values() if table.name not in exclude_tables
    ])
