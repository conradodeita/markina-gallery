"""Performance e isolamento com banco/acervo exclusivamente sintéticos."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import event, update
from sqlalchemy.orm import Session

from app import storage_metrics as sm
from app.auth import MediaDerivative, ParentGallery, PhotoAsset, PhotoFolder, Tenant
from tests.test_tenant_foundation import tenant_db as foundation_tenant_db

tenant_db = foundation_tenant_db


@pytest.fixture(autouse=True)
def storage_roots(monkeypatch, tmp_path):
    roots = tuple(tmp_path / name for name in ('source', 'derivatives', 'history'))
    for root, env in zip(roots, ('MEDIA_SOURCE_ROOT', 'MEDIA_DERIVATIVES_ROOT', 'MEDIA_HISTORY_ROOT')):
        root.mkdir()
        monkeypatch.setenv(env, str(root))
    sm.clear_storage_usage_cache()
    yield roots
    sm.clear_storage_usage_cache()


def seed(db, root, *, count=1, tenant=None):
    tenant = tenant or Tenant()
    db.add(tenant)
    db.flush()
    parent = ParentGallery(tenant_id=tenant.id, name='Sintética')
    db.add(parent)
    db.flush()
    folder = PhotoFolder(tenant_id=tenant.id, parent_gallery_id=parent.id, name='Sintética')
    db.add(folder)
    db.flush()
    photos = []
    for i in range(count):
        key = f'tenants/{tenant.id}/photo-{i}.jpg'
        path = root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'photo')
        photo = PhotoAsset(tenant_id=tenant.id, parent_gallery_id=parent.id, folder_id=folder.id,
                           filename=f'photo-{i}.jpg', storage_key=key)
        db.add(photo)
        photos.append(photo)
    db.commit()
    return tenant, photos


def test_queries_are_constant_and_cache_hit_reauthorizes(tenant_db, storage_roots):
    owner, _ = seed(tenant_db, storage_roots[0], count=30)
    owner_id = owner.id
    statements = []

    def record(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append(statement)

    event.listen(tenant_db.bind, 'before_cursor_execute', record)
    try:
        assert sm.measure_owned_photo_storage(tenant_db, tenant_id=owner_id).bytes == 150
        assert len(statements) == 5  # duas autorizações + três projeções de mídia
        statements.clear()
        assert sm.measure_owned_photo_storage(tenant_db, tenant_id=owner_id).bytes == 150
        assert len(statements) == 2
    finally:
        event.remove(tenant_db.bind, 'before_cursor_execute', record)


def test_cache_expires_without_sliding_and_clear_invalidates(tenant_db, storage_roots, monkeypatch):
    owner, photos = seed(tenant_db, storage_roots[0])
    clock = [100.0]
    monkeypatch.setattr(sm, 'monotonic', lambda: clock[0])
    path = storage_roots[0] / photos[0].storage_key
    assert sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id).bytes == 5
    path.write_bytes(b'changed-size')
    clock[0] = 129.9
    assert sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id).bytes == 5
    clock[0] = 130.0
    assert sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id).bytes == 12
    path.write_bytes(b'x')
    sm.clear_storage_usage_cache()
    assert sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id).bytes == 1


def test_cache_separates_tenants_and_roots(tenant_db, storage_roots, monkeypatch, tmp_path):
    first, _ = seed(tenant_db, storage_roots[0])
    second, _ = seed(tenant_db, storage_roots[0], count=2)
    assert sm.measure_owned_photo_storage(tenant_db, tenant_id=first.id).bytes == 5
    assert sm.measure_owned_photo_storage(tenant_db, tenant_id=second.id).bytes == 10
    replacement = tmp_path / 'replacement'
    replacement.mkdir()
    monkeypatch.setenv('MEDIA_SOURCE_ROOT', str(replacement))
    assert sm.measure_owned_photo_storage(tenant_db, tenant_id=first.id).bytes == 0


def test_cache_separates_database_binds(tenant_db, storage_roots):
    owner, _ = seed(tenant_db, storage_roots[0])
    assert sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id).bytes == 5
    # Outro bind, mesmo banco/UUID: a falta de arquivo não pode usar a memória do anterior.
    (storage_roots[0] / f'tenants/{owner.id}/photo-0.jpg').unlink()
    with tenant_db.bind.connect() as connection, Session(connection) as other:
        assert sm.measure_owned_photo_storage(other, tenant_id=owner.id).bytes == 0


def test_suspended_tenant_cannot_read_cache(tenant_db, storage_roots):
    owner, _ = seed(tenant_db, storage_roots[0])
    assert sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id).available
    tenant_db.execute(update(Tenant).where(Tenant.id == owner.id).values(status='suspended'))
    tenant_db.commit()
    with pytest.raises(HTTPException) as denied:
        sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id)
    assert denied.value.status_code == 403


def test_suspension_during_collection_does_not_publish_cache(tenant_db, storage_roots, monkeypatch):
    owner, _ = seed(tenant_db, storage_roots[0])
    original = sm._measure_owned_photo_storage

    def suspend(db, tenant_id, roots):
        result = original(db, tenant_id, roots)
        db.execute(update(Tenant).where(Tenant.id == tenant_id).values(status='suspended'))
        db.flush()
        return result

    monkeypatch.setattr(sm, '_measure_owned_photo_storage', suspend)
    with pytest.raises(HTTPException):
        sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id)
    assert all(entry.measurement is None for entry in sm._owned_cache.values())


@pytest.mark.parametrize('kind', ['outside', 'other_tenant', 'directory', 'read_error'])
def test_invalid_files_never_publish_partial_total(tenant_db, storage_roots, monkeypatch, tmp_path, kind):
    owner, photos = seed(tenant_db, storage_roots[0], count=2)
    if kind == 'outside':
        target = tmp_path / 'external.jpg'
        target.write_bytes(b'not-authorized')
        photos[0].storage_key = str(target)
    elif kind == 'other_tenant':
        photos[0].storage_key = f'tenants/{uuid4()}/not-authorized.jpg'
    elif kind == 'directory':
        path = storage_roots[0] / photos[0].storage_key
        path.unlink()
        path.mkdir()
    else:
        original = Path.lstat

        def fail(path, *args, **kwargs):
            if path.name == 'photo-0.jpg':
                raise PermissionError('synthetic')
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, 'lstat', fail)
    tenant_db.commit()
    result = sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id)
    assert not result.available and result.bytes is None
    assert all(entry.measurement is None for entry in sm._owned_cache.values())


def test_symlink_cannot_cross_root_or_tenant(tenant_db, storage_roots, tmp_path):
    owner, photos = seed(tenant_db, storage_roots[0])
    path = storage_roots[0] / photos[0].storage_key
    target = tmp_path / 'external.jpg'
    target.write_bytes(b'external')
    path.unlink()
    try:
        path.symlink_to(target)
    except OSError:
        pytest.skip('Sistema sem suporte/permissão para symlink')
    assert not sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id).available


def test_originals_derivatives_adjustments_and_duplicates(tenant_db, storage_roots):
    from app.preview_adjustment.service import result_path

    owner, photos = seed(tenant_db, storage_roots[0])
    photo = photos[0]
    preview_key = f'tenants/{owner.id}/photos/{photo.id}/preview.jpg'
    preview_path = storage_roots[1] / preview_key
    preview_path.parent.mkdir(parents=True)
    preview_path.write_bytes(b'preview')
    for variant in ('thumbnail', 'client_preview'):
        key = preview_key if variant == 'thumbnail' else preview_key.replace('preview.jpg', './preview.jpg')
        tenant_db.add(MediaDerivative(tenant_id=owner.id, photo_asset_id=photo.id,
                                     variant=variant, relative_path=key, status='ready'))
    for legacy in (False, True):
        path = result_path(photo.id, str(uuid4()), tenant_id=owner.id, legacy=legacy)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'adjust')
    tenant_db.commit()
    assert sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id).bytes == 24


def test_history_item_is_checked_before_and_after_resolution(storage_roots):
    owner, item, other = uuid4(), uuid4(), uuid4()
    root = storage_roots[2]
    valid = f'tenants/{owner}/items/{item}/preview.jpg'
    assert sm._owned_path(root, valid, owner, item_id=item) == root / valid
    with pytest.raises(ValueError):
        sm._owned_path(root, f'tenants/{owner}/items/{other}/preview.jpg', owner, item_id=item)
    target = root / f'tenants/{owner}/items/{other}'
    target.mkdir(parents=True)
    link = root / f'tenants/{owner}/items/{item}'
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('Sistema sem suporte/permissão para symlink')
    with pytest.raises(ValueError):
        sm._owned_path(root, valid, owner, item_id=item)


def test_owned_cache_has_bounded_capacity(tenant_db, storage_roots, monkeypatch):
    monkeypatch.setattr(sm, 'OWNED_CACHE_MAX_ENTRIES', 2)
    for _ in range(3):
        owner, _ = seed(tenant_db, storage_roots[0])
        assert sm.measure_owned_photo_storage(tenant_db, tenant_id=owner.id).bytes == 5
    assert len(sm._owned_cache) == 2


def test_same_tenant_coalesces_without_blocking_other_tenants(tenant_db, storage_roots, monkeypatch):
    first, _ = seed(tenant_db, storage_roots[0])
    second, _ = seed(tenant_db, storage_roots[0], count=2)
    engine = tenant_db.bind
    entered, release = Event(), Event()
    original = sm._measure_owned_photo_storage
    collections = []

    def collect(db, owner, roots):
        collections.append(owner)
        if owner == first.id:
            entered.set()
            assert release.wait(5)
        return original(db, owner, roots)

    def read(owner):
        with Session(engine) as db:
            return sm.measure_owned_photo_storage(db, tenant_id=owner).bytes

    monkeypatch.setattr(sm, '_measure_owned_photo_storage', collect)
    with ThreadPoolExecutor(max_workers=3) as executor:
        one = executor.submit(read, first.id)
        try:
            assert entered.wait(5)
            two = executor.submit(read, first.id)
            other = executor.submit(read, second.id)
            assert other.result(timeout=5) == 10
        finally:
            release.set()
        assert one.result(timeout=5) == two.result(timeout=5) == 5
    assert collections.count(first.id) == 1
