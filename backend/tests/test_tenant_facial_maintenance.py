"""Claims e purge com envelopes/arquivos sintéticos; nenhum motor ou face real."""

from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.auth import (
    FacialJob,
    FacialSearchRequest,
    GalleryFacialPolicy,
    ParentGalleryRegistration,
    now,
)
from app.facial.jobs import FacialJobError, FacialJobRepository
from app.facial.policy import ensure_automatic_policy
from app.facial.search import (
    FacialSearchError,
    cancel_search_request,
    create_search_request,
    read_search_result,
    search_availability,
)
from app.facial.worker import process_claimed_purge_job
from tests.test_facial_search_worker import _jpeg, _settings
from tests.test_tenant_client_auth import client_db as _client_db
from tests.test_tenant_client_auth import graph as _graph
from tests.test_tenant_client_auth import links as _links

client_db = _client_db
graph = _graph
links = _links


def test_contexto_de_retomada_HTTP_opaco_e_renovado_por_sessao(client_db, graph, links, tmp_path, monkeypatch):
    import re

    from fastapi import Response

    from app import auth, main
    from app.auth import Role
    from tests.test_tenant_client_auth import request

    settings = searches(client_db, graph, tmp_path)
    monkeypatch.setattr(main, "facial_settings_from_environment", lambda **_kwargs: settings)
    contexts = []
    for row in (graph[0], graph[1], graph[0]):
        token = auth.create_session(client_db, Response(), Role.CLIENT, row["client"].id, tenant_id=row["tenant"].id)
        value = main.public_gallery_facial_search_availability(row["parent"].id, request(token), client_db)
        assert re.fullmatch(r"[a-f0-9]{64}", value["storage_context"])
        assert all(str(row[key].id) not in str(value) for key in ("tenant", "client"))
        contexts.append(value["storage_context"])
    assert len(set(contexts)) == 3
    with pytest.raises(HTTPException) as exc:
        main.public_gallery_facial_search_availability(graph[1]["parent"].id, request(token), client_db)
    assert exc.value.status_code == 403


def enqueue(db, row, **extra):
    return FacialJobRepository().enqueue(db, kind="purge", idempotency_key="same-synthetic-purge",
        parent_gallery_id=row["parent"].id, tenant_id=row["tenant"].id, **extra)


def test_startup_reconciliation_continua_B_sem_reativar_A_suspensa(client_db, graph, links, tmp_path):
    from app.facial.indexing import reconcile_automatic_gallery_policies

    graph[0]["tenant"].status = "suspended"
    client_db.commit()
    result = reconcile_automatic_gallery_policies(client_db, derivatives_root=tmp_path, settings=_settings(tmp_path))
    client_db.commit()
    assert result.galleries_scanned == 1 and result.galleries_changed == 1
    assert client_db.query(GalleryFacialPolicy).filter_by(tenant_id=graph[0]["tenant"].id).count() == 0
    assert client_db.query(GalleryFacialPolicy).filter_by(tenant_id=graph[1]["tenant"].id).count() == 1


def test_embedding_alheio_e_politica_revogada_recusados_antes_do_decrypt(client_db, graph, links, tmp_path):
    from app.auth import PhotoFaceEmbedding
    from app.facial.engine import search_gallery_index
    from app.facial.regions import region_embedding

    settings = searches(client_db, graph, tmp_path)
    row = PhotoFaceEmbedding(tenant_id=graph[1]["tenant"].id, parent_gallery_id=graph[1]["parent"].id,
        photo_asset_id=graph[1]["photo"].id, face_ordinal=0, model_id="opencv-yunet-sface", embedding_dimension=128,
        model_version=settings.model_version, quality_version=settings.quality_version,
        preview_fingerprint="a"*64, quality_band="best", payload_ciphertext=b"synthetic-envelope",
        payload_nonce=b"n"*12, key_id="synthetic")
    client_db.add(row)
    graph[1]["photo"].available = True
    client_db.commit()

    class RejectDecrypt:
        def decrypt(self, *_args, **_kwargs):
            raise AssertionError("Envelope não autorizado chegou à criptografia")

    with pytest.raises(ValueError):
        region_embedding(client_db, row, RejectDecrypt(), settings, tenant_id=graph[0]["tenant"].id)
    assert search_gallery_index(client_db, gallery_id=graph[0]["parent"].id, tenant_id=graph[0]["tenant"].id,
        query_embedding=(1.0, *([0.0]*127)), cipher=RejectDecrypt(), settings=settings,
        threshold_milli=settings.similarity_threshold_milli) == []
    with pytest.raises(AssertionError, match="criptografia"):
        region_embedding(client_db, row, RejectDecrypt(), settings, tenant_id=graph[1]["tenant"].id)
    policy = client_db.query(GalleryFacialPolicy).filter_by(tenant_id=graph[1]["tenant"].id).one()
    policy.status = "disabled"
    client_db.commit()
    with pytest.raises(ValueError):
        region_embedding(client_db, row, RejectDecrypt(), settings, tenant_id=graph[1]["tenant"].id)


def test_jobs_mesma_chave_A_B_e_origem_mista_recusada(client_db, graph, links):
    repository = FacialJobRepository()
    jobs = [enqueue(client_db, row)[0] for row in graph]
    assert jobs[0].id != jobs[1].id
    assert enqueue(client_db, graph[0]) == (jobs[0], False)
    with pytest.raises(FacialJobError):
        enqueue(client_db, graph[0], photo_asset_id=graph[1]["photo"].id)
    client_db.commit()
    claim = repository.claim_next(client_db, lease_seconds=120, job_class="maintenance")
    assert claim.id == jobs[0].id and claim.tenant_id == graph[0]["tenant"].id
    with pytest.raises(FacialJobError):
        repository.complete(client_db, replace(claim, tenant_id=graph[1]["tenant"].id))
    assert repository.complete(client_db, claim).status == "completed"
    assert client_db.get(FacialJob, jobs[1].id).status == "queued"


def test_conta_suspensa_nao_consumida_lease_expirado_nao_publica(client_db, graph, links):
    repository = FacialJobRepository()
    jobs = [enqueue(client_db, row)[0] for row in graph]
    graph[0]["tenant"].status = "suspended"
    client_db.commit()
    claim = repository.claim_next(client_db, lease_seconds=120, job_class="maintenance")
    assert claim.id == jobs[1].id
    assert jobs[0].status == "queued" and jobs[0].attempts == 0
    jobs[1].lease_expires_at = now() - timedelta(seconds=1)
    client_db.commit()
    with pytest.raises(FacialJobError):
        repository.complete(client_db, claim)
    assert jobs[1].status == "processing"


def test_suspensao_apos_claim_preserva_job_proprio_e_libera_B(client_db, graph, links):
    repository = FacialJobRepository()
    jobs = [enqueue(client_db, row)[0] for row in graph]
    client_db.commit()
    claim = repository.claim_next(client_db, lease_seconds=120, job_class="maintenance")
    graph[0]["tenant"].status = "suspended"
    client_db.commit()
    with pytest.raises(HTTPException):
        process_claimed_purge_job(client_db, claim, repository=repository)
    repository.release_denied(client_db, claim)
    client_db.refresh(jobs[0])
    assert jobs[0].status == "queued" and jobs[0].attempts == 0 and jobs[0].lease_token is None
    second = repository.claim_next(client_db, lease_seconds=120, job_class="maintenance")
    assert second.id == jobs[1].id
    assert process_claimed_purge_job(client_db, second, repository=repository).status == "completed"


def test_purge_A_apaga_apenas_referencia_cifrada_UUID_proprio(client_db, graph, links, tmp_path):
    requests = []
    for row in graph:
        policy = GalleryFacialPolicy(tenant_id=row["tenant"].id, parent_gallery_id=row["parent"].id,
            model_version="model-v1", quality_version="quality-v1")
        client_db.add(policy)
        client_db.flush()
        request = FacialSearchRequest(tenant_id=row["tenant"].id, parent_gallery_id=row["parent"].id,
            client_id=row["client"].id, policy_id=policy.id, status="ready", subject_declaration="adult",
            consent_version="consent-v1", legal_notice_version="notice-v1", model_version="model-v1", quality_version="quality-v1",
            reference_locator_ciphertext=b"synthetic-envelope", reference_locator_nonce=b"n"*12, reference_key_id="synthetic",
            index_generation=1, expires_at=now()+timedelta(hours=1))
        client_db.add(request)
        client_db.flush()
        (tmp_path / f"{request.id}.reference").write_bytes(b"synthetic-encrypted-artifact")
        requests.append(request)
    job, _ = enqueue(client_db, graph[0])
    client_db.commit()
    repository = FacialJobRepository()
    claim = repository.claim_next(client_db, lease_seconds=120, job_class="maintenance")
    assert claim.id == job.id
    assert process_claimed_purge_job(client_db, claim, repository=repository, reference_root=tmp_path).status == "completed"
    client_db.refresh(requests[0]); client_db.refresh(requests[1])
    assert requests[0].status == "cancelled" and requests[0].reference_locator_ciphertext is None
    assert not (tmp_path / f"{requests[0].id}.reference").exists()
    assert requests[1].status == "ready" and requests[1].reference_locator_ciphertext == b"synthetic-envelope"
    assert (tmp_path / f"{requests[1].id}.reference").read_bytes() == b"synthetic-encrypted-artifact"


def searches(db, graph, tmp_path):
    settings = _settings(tmp_path)
    for row in graph:
        ensure_automatic_policy(db, parent_gallery_id=row["parent"].id, tenant_id=row["tenant"].id, settings=settings)
        db.add(ParentGalleryRegistration(tenant_id=row["tenant"].id, parent_gallery_id=row["parent"].id,
            client_id=row["client"].id, status="active"))
    db.commit()
    return settings


def create(db, row, settings):
    return create_search_request(db, parent_gallery_id=row["parent"].id, client_id=row["client"].id,
        consent_version=settings.consent_version, subject_declaration="adult", representation_reference=None,
        payload=_jpeg(), settings=settings)


def test_busca_sintetica_A_B_mesmo_telefone_cancelamento_e_referencia_isolados(client_db, graph, links, tmp_path):
    settings = searches(client_db, graph, tmp_path)
    requests = [create(client_db, row, settings) for row in graph]
    client_db.commit()
    assert requests[0].tenant_id != requests[1].tenant_id
    assert all(request.reference_locator_ciphertext and b"reference" not in request.reference_locator_ciphertext for request in requests)
    assert search_availability(client_db, parent_gallery_id=graph[0]["parent"].id, client_id=graph[0]["client"].id,
        settings=settings)["state"] == "consent_required"
    before = (requests[1].status, requests[1].reference_locator_ciphertext)
    with pytest.raises(FacialSearchError):
        read_search_result(client_db, parent_gallery_id=graph[0]["parent"].id, client_id=graph[0]["client"].id, request_id=requests[1].id)
    cancel_search_request(client_db, parent_gallery_id=graph[0]["parent"].id, client_id=graph[0]["client"].id,
        request_id=requests[0].id, settings=settings)
    client_db.commit()
    client_db.refresh(requests[1])
    assert requests[0].status == "cancelled" and requests[0].reference_locator_ciphertext is None
    assert (requests[1].status, requests[1].reference_locator_ciphertext) == before
    assert (settings.reference_root / f"{requests[1].id}.reference").exists()


def test_criacao_alheia_recusada_antes_de_armazenar_envelope(client_db, graph, links, tmp_path):
    settings = searches(client_db, graph, tmp_path)
    with pytest.raises(FacialSearchError):
        create_search_request(client_db, parent_gallery_id=graph[1]["parent"].id, client_id=graph[0]["client"].id,
            consent_version=settings.consent_version, subject_declaration="adult", representation_reference=None,
            payload=_jpeg(), settings=settings)
    assert not settings.reference_root.exists()


def test_worker_busca_suspensa_no_provider_nao_publica_e_B_conclui(client_db, graph, links, tmp_path):
    from sqlalchemy.orm import sessionmaker

    from app.auth import Tenant
    from app.facial.crypto import FacialCipher
    from app.facial.search_worker import process_claimed_search_job

    settings = searches(client_db, graph, tmp_path)
    requests = [create(client_db, row, settings) for row in graph]
    client_db.commit()
    factory = sessionmaker(bind=client_db.bind, expire_on_commit=False)
    repository = FacialJobRepository()
    cipher = FacialCipher(active_key_id=settings.active_key_id, keys=settings.aead_keys)

    class EmptySyntheticProvider:
        def observe_bytes(self, _payload):
            return []

    class SuspendingProvider(EmptySyntheticProvider):
        def observe_bytes(self, _payload):
            with factory() as other:
                other.get(Tenant, graph[0]["tenant"].id).status = "suspended"
                other.commit()
            return []

    claim = repository.claim_next(client_db, lease_seconds=120, job_class="search")
    assert process_claimed_search_job(client_db, claim, repository=repository, provider=SuspendingProvider(),
        cipher=cipher, settings=settings).status == "queued"
    client_db.refresh(requests[0])
    assert requests[0].status != "no_face" and requests[0].reference_locator_ciphertext
    assert (settings.reference_root / f"{requests[0].id}.reference").exists()
    second = repository.claim_next(client_db, lease_seconds=120, job_class="search")
    assert second.tenant_id == graph[1]["tenant"].id
    assert process_claimed_search_job(client_db, second, repository=repository, provider=EmptySyntheticProvider(),
        cipher=cipher, settings=settings).status == "completed"
    client_db.refresh(requests[1])
    assert requests[1].status == "no_face" and requests[1].reference_locator_ciphertext is None


def test_indexacao_suspensa_no_provider_nao_publica_e_B_conclui(client_db, graph, links, tmp_path, monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from app.auth import MediaDerivative, PhotoFaceEmbedding, Tenant
    from app.facial.crypto import FacialCipher
    from app.facial.worker import process_claimed_index_job

    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    settings = _settings(tmp_path)
    repository = FacialJobRepository()
    factory = sessionmaker(bind=client_db.bind, expire_on_commit=False)
    for row in graph:
        ensure_automatic_policy(client_db, parent_gallery_id=row["parent"].id, tenant_id=row["tenant"].id, settings=settings)
        for variant in ("client_preview", "admin_preview"):
            key = f"tenants/{row['tenant'].id}/photos/{row['photo'].id}/{variant}.jpg"
            path = tmp_path / "derivatives" / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_jpeg())
            client_db.add(MediaDerivative(tenant_id=row["tenant"].id, photo_asset_id=row["photo"].id,
                variant=variant, status="ready", relative_path=key))
        repository.enqueue(client_db, tenant_id=row["tenant"].id, parent_gallery_id=row["parent"].id,
            photo_asset_id=row["photo"].id, kind="index", idempotency_key="same-index", model_version=settings.model_version,
            quality_version=settings.quality_version, preview_fingerprint="synthetic")
    client_db.commit()
    cipher = FacialCipher(active_key_id=settings.active_key_id, keys=settings.aead_keys)

    class EmptySyntheticProvider:
        def observe_path(self, _path):
            return []

    class SuspendingProvider(EmptySyntheticProvider):
        def observe_path(self, _path):
            with factory() as other:
                other.get(Tenant, graph[0]["tenant"].id).status = "suspended"
                other.commit()
            return []

    claim = repository.claim_next(client_db, lease_seconds=120, job_class="index")
    with pytest.raises(HTTPException):
        process_claimed_index_job(client_db, claim, repository=repository, provider=SuspendingProvider(), cipher=cipher,
            settings=settings, derivatives_root=tmp_path / "derivatives")
    repository.release_denied(client_db, claim)
    assert not list(client_db.scalars(select(PhotoFaceEmbedding)))
    second = repository.claim_next(client_db, lease_seconds=120, job_class="index")
    assert second.tenant_id == graph[1]["tenant"].id
    assert process_claimed_index_job(client_db, second, repository=repository, provider=EmptySyntheticProvider(), cipher=cipher,
        settings=settings, derivatives_root=tmp_path / "derivatives").status == "completed"


def test_representacao_e_rollout_alheios_recusados_sem_mutacao(client_db, graph, links, tmp_path):
    from app.facial.representation import (
        FacialLegalRepresentationError,
        create_legal_representation,
        revoke_legal_representation,
    )
    from app.facial.rollout import (
        FacialRolloutError,
        draft_from_settings,
        prepare_rollout,
        suspend_rollout,
    )
    settings = searches(client_db, graph, tmp_path)
    b = graph[1]
    representation = create_legal_representation(client_db, client_id=b["client"].id, parent_gallery_id=b["parent"].id,
        subject_scope_reference="synthetic-scope", authority_kind="parent", verification_method="admin_attestation",
        terms_version="synthetic-terms", evidence_reference="synthetic-evidence", verified_by_admin_id=b["admin"].id,
        expires_at=now()+timedelta(days=1))
    rollout = prepare_rollout(client_db, tenant_id=b["tenant"].id, parent_gallery_id=b["parent"].id,
        environment="test", draft=draft_from_settings(settings))
    client_db.commit()
    with pytest.raises(FacialLegalRepresentationError):
        revoke_legal_representation(client_db, representation_id=representation.id, actor_admin_id=graph[0]["admin"].id)
    with pytest.raises(FacialRolloutError):
        suspend_rollout(client_db, parent_gallery_id=b["parent"].id, environment="test", actor_admin_id=graph[0]["admin"].id)
    client_db.refresh(representation); client_db.refresh(rollout)
    assert representation.status == "active" and rollout.status == "prepared"


def test_retencao_facial_expirada_B_preserva_referencia_A_suspensa(client_db, graph, links, tmp_path):
    from sqlalchemy import select

    from app.facial.retention import process_claimed_cleanup_job
    settings = searches(client_db, graph, tmp_path)
    requests = [create(client_db, row, settings) for row in graph]
    for request in requests:
        request.expires_at = now() - timedelta(minutes=1)
        job = client_db.scalar(select(FacialJob).where(FacialJob.search_request_id == request.id, FacialJob.kind == "cleanup"))
        job.available_at = now() - timedelta(minutes=1)
    graph[0]["tenant"].status = "suspended"
    client_db.commit()
    repository = FacialJobRepository()
    claim = repository.claim_next(client_db, lease_seconds=120, job_class="maintenance")
    assert claim.tenant_id == graph[1]["tenant"].id
    assert process_claimed_cleanup_job(client_db, claim, repository=repository, settings=settings).status == "completed"
    client_db.refresh(requests[0]); client_db.refresh(requests[1])
    assert requests[0].reference_locator_ciphertext and (settings.reference_root / f"{requests[0].id}.reference").exists()
    assert requests[1].reference_locator_ciphertext is None and not (settings.reference_root / f"{requests[1].id}.reference").exists()


def test_falha_provider_apos_suspensao_libera_apenas_lease_A_e_B_continua(client_db, graph, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    from app.auth import Tenant
    from app.facial import face_worker

    repository = FacialJobRepository()
    jobs = []
    for row in graph:
        job, _ = repository.enqueue(client_db, tenant_id=row["tenant"].id, kind="index",
            idempotency_key="provider-failure", parent_gallery_id=row["parent"].id,
            photo_asset_id=row["photo"].id, model_version="synthetic", quality_version="synthetic",
            preview_fingerprint="synthetic")
        jobs.append(job)
    client_db.commit()
    claims = [repository.claim_next(client_db, lease_seconds=120) for _ in graph]
    by_owner = {claim.tenant_id: claim for claim in claims}
    factory = sessionmaker(bind=client_db.bind)
    monkeypatch.setattr(face_worker, "SessionLocal", factory)
    with factory() as peer:
        peer.get(Tenant, graph[0]["tenant"].id).status = "suspended"
        peer.commit()
    face_worker.record_provider_failure(repository, by_owner[graph[0]["tenant"].id], ValueError("synthetic"))
    client_db.expire_all()
    assert jobs[0].status == "queued" and jobs[0].lease_token is None and jobs[0].attempts == 0
    assert jobs[0].last_error_category is None
    assert jobs[1].status == "processing" and jobs[1].lease_token == by_owner[graph[1]["tenant"].id].lease_token
    face_worker.record_provider_failure(repository, by_owner[graph[1]["tenant"].id], ValueError("synthetic"))
    client_db.expire_all()
    assert jobs[1].status == "queued" and jobs[1].attempts == 1 and jobs[1].last_error_category is not None
