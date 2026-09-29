# Garante que o diretório backend/ entre no sys.path quando o pytest roda
# de fora do pacote (ex.: na CI: `pytest backend/tests -q` a partir da raiz).

import pytest
from sqlalchemy import event, inspect, select

from app.auth import Base, Tenant, now
from tests.tenant_fixtures import FIXTURE_TENANT_ID


@pytest.fixture(autouse=True)
def legacy_tenant_fixture(request):
    """Seed explícito só para fixtures legadas; testes da fundação não usam este hook."""
    if request.module.__name__.split(".")[-1].startswith("test_tenant_"):
        yield
        return

    def seed_tenant(_metadata, connection, **_kwargs):
        if inspect(connection).has_table("tenant") and not connection.scalar(select(Tenant.id)):
            connection.execute(Tenant.__table__.insert().values(
                id=FIXTURE_TENANT_ID, status="active", created_at=now(),
            ))

    event.listen(Base.metadata, "after_create", seed_tenant)
    yield
    event.remove(Base.metadata, "after_create", seed_tenant)
