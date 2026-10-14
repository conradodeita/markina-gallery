"""Agregado de todas as contas; candidatos refletem o gate ativo dos workers."""

from datetime import timedelta

from app.auth import FacialJob, MediaJob, now
from app.capacity_observability.queues import collect_all_queues
from tests.test_tenant_client_isolation import client_db as _client_db
from tests.test_tenant_ownership_schema import graph as _graph

client_db, graph = _client_db, _graph


def test_fila_bruta_A_B_e_candidatos_somente_de_conta_ativa(client_db, graph):
    instant = now()
    for row in graph:
        owner = row["tenant"].id
        client_db.add(MediaJob(tenant_id=owner, photo_asset_id=row["photo"].id,
            kind="generate_derivatives", status="queued"))
        for kind in ("search", "index", "cleanup"):
            for status in ("queued", "processing"):
                client_db.add(FacialJob(tenant_id=owner, parent_gallery_id=row["parent"].id,
                    kind=kind, status=status, idempotency_key=f"{kind}:{status}",
                    available_at=instant-timedelta(seconds=10),
                    lease_expires_at=instant-timedelta(seconds=1) if status=="processing" else None))
    graph[0]["tenant"].status = "suspended"
    client_db.commit()
    queues = {queue.queue_class: queue for queue in collect_all_queues(client_db, instant=instant)}
    assert queues["media"].queued_total.value == 2
    assert queues["media"].claim_candidates_total.value == 1
    for name in ("search", "index", "maintenance"):
        assert queues[name].queued_total.value == 2
        assert queues[name].claim_candidates_total.value == 1
        assert queues[name].processing_total.value == 2
        assert queues[name].reclaimable_total.value == 1
    # Reativação muda somente elegibilidade da leitura, nunca os registros da fila.
    graph[0]["tenant"].status = "active"
    client_db.commit()
    queues = {queue.queue_class: queue for queue in collect_all_queues(client_db, instant=instant)}
    assert queues["media"].queued_total.value == queues["media"].claim_candidates_total.value == 2
    for name in ("search", "index", "maintenance"):
        assert queues[name].queued_total.value == queues[name].claim_candidates_total.value == 2
        assert queues[name].processing_total.value == queues[name].reclaimable_total.value == 2
