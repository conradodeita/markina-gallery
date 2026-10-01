"""Acervo A/B com cookies reais e PostgreSQL descartável; sem transporte ou biometria."""

import asyncio
from functools import partial
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app import main
from app.auth import DerivedGalleryPhoto, MediaDerivative, MediaJob, PhotoAsset, PhotoFolder, Role
from tests.test_tenant_client_auth import client_db as _client_db
from tests.test_tenant_client_auth import graph as _graph
from tests.test_tenant_client_auth import links as _links
from tests.test_tenant_client_auth import request
from tests.test_tenant_client_navigation import cookie

client_db = _client_db
graph = _graph
links = _links


@pytest.fixture
def admin_request(client_db, graph, links):
    return request(cookie(client_db, graph[0], Role.ADMIN))


@pytest.mark.parametrize("kind", ["parent", "folder", "private", "photo"])
def test_UUID_estrangeiro_equivale_ausente_sem_metadados_efeitos_ou_arquivos(
    client_db, graph, admin_request, monkeypatch, kind,
):
    def forbidden(*args, **kwargs):
        pytest.fail("Recurso estrangeiro alcançou acesso a arquivo ou processamento")

    for name in ("safe_source_path", "safe_derivative_path", "presentation_path", "enqueue_derivatives"):
        monkeypatch.setattr(main, name, forbidden)
    payload = SimpleNamespace(name="Sintética", gallery_ids=[], photo_ids=[], storage_key="candidate")
    if kind == "parent":
        functions = [main.parent_gallery_editor, main.parent_gallery_settings, main.parent_gallery_summary,
                     main.parent_gallery_details, main.admin_parent_gallery_photos,
                     main.admin_parent_gallery_available_photos, main.admin_parent_gallery_folders,
                     main.create_photo_folder, main.update_parent_gallery_settings,
                     main.set_parent_gallery_cover, main.clear_parent_gallery_cover,
                     main.register_parent_gallery_cover_photo, main.parent_gallery_public_link_status,
                     main.issue_parent_gallery_public_link, main.rotate_parent_gallery_public_link,
                     main.revoke_parent_gallery_public_link, main.publish_parent_gallery_ready_photos]
        argument, resource = "parent_gallery_id", graph[1]["parent"]
    elif kind == "folder":
        functions = [main.rename_photo_folder, main.delete_photo_folder, main.admin_photo_folder_photos,
                     main.register_folder_photo_asset, main.publish_photo_folder, main.release_photo_folder,
                     main.delete_folder_photo_assets]
        argument, resource = "folder_id", graph[1]["folder"]
    elif kind == "private":
        functions = [main.derived_gallery_detail, main.admin_private_gallery_photos,
                     main.admin_private_gallery_folders, main.create_private_gallery_folder,
                     main.list_private_upload_batches, main.begin_private_upload_batch,
                     main.private_gallery_link_status, main.private_gallery_members,
                     main.update_derived_gallery, main.renew_gallery_selection]
        argument, resource = "gallery_id", graph[1]["gallery"]
    else:
        functions = [main.photo_media_status, main.admin_photo_preview, main.admin_watermarked_photo_preview,
                     main.import_photo_source]
        argument, resource = "photo_id", graph[1]["photo"]
    import inspect

    before = client_db.scalar(select(func.count()).select_from(PhotoAsset))
    for function in functions:
        results = []
        for resource_id in (resource.id, uuid4()):
            arguments = {argument: resource_id, "request": admin_request, "db": client_db}
            for name in ("payload", "_payload"):
                if name in inspect.signature(function).parameters:
                    arguments[name] = payload
            with pytest.raises(HTTPException) as exc:
                result = function(**arguments)
                if inspect.isawaitable(result):
                    asyncio.run(result)
            assert exc.value.status_code == 404, function.__name__
            results.append(exc.value.detail)
        assert results[0] == results[1], function.__name__
    assert client_db.scalar(select(func.count()).select_from(PhotoAsset)) == before


def test_catalogos_e_criacao_administrativa_preservam_proprietario(client_db, graph, admin_request):
    first, second = graph
    listed = main.admin_parent_galleries(admin_request, client_db)
    assert [item["id"] for item in listed["parent_galleries"]] == [str(first["parent"].id)]
    overview = main.parent_gallery_overview(admin_request, query=second["parent"].name,
                                          offset=0, limit=30, db=client_db)
    assert overview == {"total": 0, "parent_galleries": []}
    private = main.list_derived_galleries(admin_request, query=None, tab="active", state=None,
                                         offset=0, limit=30, db=client_db)
    assert [item["id"] for item in private["galleries"]] == [str(first["gallery"].id)]
    created = main.create_photo_folder(first["parent"].id, main.PhotoFolderInput(name="Pasta A"),
                                       admin_request, client_db)
    assert client_db.get(PhotoFolder, UUID(created["id"])).tenant_id == first["tenant"].id
    created = main.create_private_gallery_folder(first["gallery"].id, main.PhotoFolderInput(name="Privada A"),
                                                 admin_request, client_db)
    assert client_db.get(PhotoFolder, UUID(created["id"])).tenant_id == first["tenant"].id


def test_upload_namespace_idempotencia_legado_e_owner_job(client_db, graph, admin_request):
    first = graph[0]
    folder = first["folder"]
    logical_key = f"{first['parent'].id}/{folder.id}/{uuid4()}.jpg"
    payload = main.PhotoAssetInput(filename="synthetic.jpg", storage_key=logical_key)
    created = main.register_folder_photo_asset(folder.id, payload, admin_request, client_db)
    photo = client_db.get(PhotoAsset, UUID(created["id"]))
    assert photo.tenant_id == first["tenant"].id
    assert photo.storage_key == f"tenants/{photo.tenant_id}/{logical_key}"
    assert main.register_folder_photo_asset(folder.id, payload, admin_request, client_db)["id"] == created["id"]
    legacy_key = "legacy/frozen-storage-key.jpg"
    first["photo"].storage_key = legacy_key
    client_db.commit()
    result = main.register_folder_photo_asset(folder.id,
        main.PhotoAssetInput(filename="synthetic.jpg", storage_key=legacy_key), admin_request, client_db)
    assert result["id"] == str(first["photo"].id)
    assert first["photo"].storage_key == legacy_key
    main.enqueue_derivatives(client_db, photo)
    client_db.commit()
    assert client_db.scalar(select(MediaJob).where(MediaJob.photo_asset_id == photo.id)).tenant_id == photo.tenant_id


@pytest.mark.parametrize("key", ["../escape.jpg", "private/foreign/folder/image.jpg", "/absolute.jpg"])
def test_upload_recusa_chave_fora_da_pasta_antes_de_insert(client_db, graph, admin_request, key):
    with pytest.raises(HTTPException) as exc:
        main.register_folder_photo_asset(graph[0]["folder"].id,
            main.PhotoAssetInput(filename="synthetic.jpg", storage_key=key), admin_request, client_db)
    assert exc.value.status_code == 422


def test_rotas_auxiliares_recusam_B_antes_de_configuracao_jobs_comparacao(client_db, graph, admin_request):
    import inspect

    for route in main.app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/admin/photo-folders/{folder_id}/processing"):
            args = {"folder_id": graph[1]["folder"].id}
        elif path.startswith("/admin/preview-adjustment/galleries/{gallery_id}"):
            args = {"gallery_id": graph[1]["parent"].id}
        elif path.startswith("/admin/preview-adjustment/photos/{photo_id}"):
            args = {"photo_id": graph[1]["photo"].id, "version": "before"}
        else:
            continue
        args.update(request=admin_request, db=client_db)
        if "payload" in inspect.signature(route.endpoint).parameters:
            args["payload"] = SimpleNamespace()
        with pytest.raises(HTTPException) as exc:
            route.endpoint(**args)
        assert exc.value.status_code in {404, 409}, path


def test_previa_direta_publica_privada_e_admin_isolada_preserva_path_legado(
    client_db, graph, links, tmp_path, monkeypatch,
):
    from app.parent_registration import link_client_to_parent

    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path))
    for record in graph:
        photo = record["photo"]
        record["folder"].status = "released"
        photo.available = True
        for variant in ("client_preview", "admin_preview"):
            key = f"legacy/{record['tenant'].id}/{variant}.jpg"
            path = tmp_path / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(str(record["tenant"].id).encode())
            client_db.add(MediaDerivative(tenant_id=photo.tenant_id, photo_asset_id=photo.id,
                variant=variant, status="ready", relative_path=key))
        client_db.add(DerivedGalleryPhoto(tenant_id=photo.tenant_id,
            derived_gallery_id=record["gallery"].id, photo_asset_id=photo.id))
        link_client_to_parent(client_db, parent_gallery_id=record["parent"].id,
                              client_id=record["client"].id)
    client_db.commit()
    for record, other in (graph, graph[::-1]):
        admin = request(cookie(client_db, record, Role.ADMIN))
        customer = request(cookie(client_db, record))
        responses = [main.admin_photo_preview(record["photo"].id, admin, client_db),
            main.admin_watermarked_photo_preview(record["photo"].id, admin, client_db),
            main.client_photo_preview(record["gallery"].id, record["photo"].id, customer, client_db),
            main.public_gallery_photo_preview(record["parent"].id, record["photo"].id, customer, client_db)]
        for response in responses:
            assert str(record["tenant"].id) in str(response.path)
            assert response.headers["cache-control"] == "private, no-store"
        attempts = [partial(main.admin_photo_preview, other["photo"].id, admin, client_db),
            partial(main.client_photo_preview, other["gallery"].id, other["photo"].id, customer, client_db),
            partial(main.client_photo_preview, record["gallery"].id, other["photo"].id, customer, client_db),
            partial(main.public_gallery_photo_preview, other["parent"].id, other["photo"].id, customer, client_db),
            partial(main.public_gallery_photo_preview, record["parent"].id, other["photo"].id, customer, client_db)]
        for operation in attempts:
            with pytest.raises(HTTPException) as exc:
                operation()
            assert exc.value.status_code in {403, 404}


def test_lote_e_capa_novos_tem_owner_namespace_e_replay(client_db, graph, admin_request, monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://example.test")
    first, second = graph
    created = main.begin_private_upload_batch(first["gallery"].id, admin_request, client_db)
    batch_id = UUID(created["id"])
    folder = main.create_private_gallery_folder(first["gallery"].id,
        main.PhotoFolderInput(name="JPEGs sintéticos"), admin_request, client_db)
    folder_id = UUID(folder["id"])
    key = f"private/{first['gallery'].id}/{folder_id}/{uuid4()}.jpg"
    photo = main.register_folder_photo_asset(folder_id,
        main.PhotoAssetInput(filename="synthetic.jpg", storage_key=key, upload_batch_id=batch_id),
        admin_request, client_db)
    listed = main.list_private_upload_batches(first["gallery"].id, admin_request, client_db)
    asset = listed["batches"][0]["assets"][0]
    assert asset["id"] == photo["id"] and asset["upload_key"] == key
    assert asset["storage_key"] == f"tenants/{first['tenant'].id}/{key}"
    with pytest.raises(HTTPException) as exc:
        main.finish_private_upload_batch(second["gallery"].id, batch_id, admin_request, client_db)
    assert exc.value.status_code == 404
    main.finish_private_upload_batch(first["gallery"].id, batch_id, admin_request, client_db)
    payload = main.ParentGalleryCoverUploadInput(filename="synthetic.jpg", idempotency_key="synthetic-cover-key")
    result = main.register_parent_gallery_cover_photo(first["parent"].id, payload, admin_request, client_db)
    assert main.register_parent_gallery_cover_photo(first["parent"].id, payload, admin_request, client_db)["id"] == result["id"]
    cover = client_db.get(PhotoAsset, UUID(result["id"]))
    assert cover.storage_key.startswith(f"tenants/{first['tenant'].id}/covers/{first['parent'].id}/")


def test_importacao_de_capa_escreve_apenas_A_e_persiste_job_contextual(
    client_db, graph, admin_request, tmp_path, monkeypatch,
):
    from io import BytesIO

    from PIL import Image
    from starlette.requests import Request

    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path))
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://example.test")
    result = main.register_parent_gallery_cover_photo(graph[0]["parent"].id,
        main.ParentGalleryCoverUploadInput(filename="synthetic.jpg", idempotency_key="synthetic-import-key"),
        admin_request, client_db)
    photo = client_db.get(PhotoAsset, UUID(result["id"]))
    output = BytesIO()
    Image.new("RGB", (24, 12), color="blue").save(output, format="JPEG")

    async def receive():
        return {"type": "http.request", "body": output.getvalue(), "more_body": False}

    scope = dict(admin_request.scope)
    scope["headers"] = list(scope["headers"]) + [(b"content-type", b"image/jpeg")]
    assert asyncio.run(main.import_photo_source(photo.id, Request(scope, receive), client_db)) == {"status": "queued"}
    assert (tmp_path / photo.storage_key).read_bytes() == output.getvalue()
    assert not (tmp_path / graph[1]["photo"].storage_key).exists()
    assert client_db.scalar(select(MediaJob).where(MediaJob.photo_asset_id == photo.id)).tenant_id == photo.tenant_id


def test_pasta_restrita_preserva_publico_e_cliente_B_nao_recebe_atribuicao(
    client_db, graph, admin_request,
):
    from app.auth import Client
    from app.parent_registration import link_client_to_parent
    from app.public_gallery_access import authorized_canonical_photos

    first, second = graph
    link_client_to_parent(client_db, parent_gallery_id=first["parent"].id, client_id=first["client"].id)
    other = Client(tenant_id=first["tenant"].id, full_name="Outra sintética A", phone_e164="+5511999990080")
    client_db.add(other)
    client_db.flush()
    link_client_to_parent(client_db, parent_gallery_id=first["parent"].id, client_id=other.id)
    client_db.commit()
    folder = main.create_admin_client_restricted_folder(first["parent"].id, first["client"].id,
        main.PhotoFolderInput(name="Pasta restrita A"), admin_request, client_db)
    folder_id = UUID(folder["id"])
    photo = PhotoAsset(tenant_id=first["tenant"].id, parent_gallery_id=first["parent"].id,
        folder_id=folder_id, filename="synthetic.jpg", storage_key=f"synthetic/{uuid4()}.jpg", available=False)
    client_db.add(photo)
    client_db.flush()
    client_db.add(MediaDerivative(tenant_id=photo.tenant_id, photo_asset_id=photo.id,
        variant="client_preview", status="ready"))
    client_db.commit()
    published = main.publish_photo_folder(folder_id, main.PhotoFolderPublishInput(), admin_request, client_db)
    assert published["published_count"] == 1
    assert photo.id in {p.id for p in client_db.scalars(authorized_canonical_photos(first["parent"].id, first["client"].id))}
    assert photo.id not in {p.id for p in client_db.scalars(authorized_canonical_photos(first["parent"].id, other.id))}
    assert list(client_db.scalars(authorized_canonical_photos(first["parent"].id, second["client"].id))) == []
    with pytest.raises(HTTPException) as exc:
        main.grant_restricted_folder_client(first["parent"].id, folder_id, second["client"].id, admin_request, client_db)
    assert exc.value.status_code == 404


def test_excluir_foto_A_preserva_registros_e_arquivos_B(client_db, graph, admin_request, tmp_path, monkeypatch):
    from app.auth import AssetFileCleanup

    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "sources"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(tmp_path / "history"))
    files = []
    for record in graph:
        path = tmp_path / "sources" / record["photo"].storage_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic")
        files.append(path)
    first, second = graph
    result = main.delete_folder_photo_asset(first["folder"].id, first["photo"].id, admin_request, client_db)
    assert result.status_code == 204 and result.headers["x-asset-cleanup"] == "completed"
    assert not files[0].exists() and files[1].read_bytes() == b"synthetic"
    assert client_db.get(PhotoAsset, second["photo"].id) is not None
    cleanup = client_db.scalar(select(AssetFileCleanup))
    assert cleanup.tenant_id == first["tenant"].id


def test_criacao_link_e_rotacao_nao_alteram_capacidade_B(client_db, graph, links, admin_request, monkeypatch):
    from app.auth import GalleryAccessCapability, ParentGallery
    from app.gallery_access import rotate_gallery_capability

    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://example.test")
    created = main.create_parent_gallery(main.ParentGalleryInput(name="Nova sintética A"), admin_request, client_db)
    parent = client_db.get(ParentGallery, UUID(created["id"]))
    cap = client_db.get(GalleryAccessCapability, UUID(created["capability_id"]))
    assert parent.tenant_id == cap.tenant_id == graph[0]["tenant"].id
    foreign = links[1][1]
    with pytest.raises(ValueError):
        rotate_gallery_capability(client_db, foreign, tenant_id=graph[0]["tenant"].id)
    assert foreign.status == "active" and foreign.revoked_at is None
    replacement, _token = rotate_gallery_capability(client_db, cap, tenant_id=graph[0]["tenant"].id,
                                                     actor_admin_id=graph[0]["admin"].id)
    client_db.commit()
    assert replacement.tenant_id == cap.tenant_id and cap.status == "rotated"


def test_banco_recusa_asset_variante_e_job_com_owner_cruzado(client_db, graph):
    from sqlalchemy.exc import IntegrityError

    first, second = graph
    records = [
        PhotoAsset(tenant_id=first["tenant"].id, parent_gallery_id=second["parent"].id,
                   folder_id=second["folder"].id, filename="synthetic.jpg", storage_key=f"synthetic/{uuid4()}.jpg"),
        MediaDerivative(tenant_id=first["tenant"].id, photo_asset_id=second["photo"].id,
                        variant="client_preview", status="ready"),
        MediaJob(tenant_id=first["tenant"].id, photo_asset_id=second["photo"].id),
    ]
    for record in records:
        with pytest.raises(IntegrityError), client_db.begin_nested():
            client_db.add(record)
            client_db.flush()
