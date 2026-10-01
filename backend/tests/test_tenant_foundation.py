"""Integridade real em banco isolado; nenhum serviço externo ou acervo real."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    Base,
    Client,
    DerivedGallery,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    Tenant,
    TenantAdmin,
)


@pytest.fixture
def tenant_db(tmp_path):
    url = (
        os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL")
        or os.getenv("TENANT_TEST_DATABASE_URL")
        or f"sqlite:///{tmp_path / 'tenant.sqlite'}"
    )
    engine = create_engine(url)
    schema = None
    if engine.dialect.name == "postgresql":
        parsed = engine.url
        assert parsed.host == "127.0.0.1"
        assert (parsed.port, parsed.database) in {
            (55469, "pyp_tenant_test"), (15470, "pyp_photographer_test"),
        }
        schema = f"tenant_test_{uuid4().hex}"
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = engine.execution_options(schema_translate_map={None: schema})
    else:
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def enable_fk(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    if schema:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


def acervo(db):
    first, second = Tenant(), Tenant()
    db.add_all([first, second])
    db.flush()
    client = Client(tenant_id=first.id, full_name="Sintético", phone_e164="+5511999999999")
    db.add(client)
    db.flush()
    parent = ParentGallery(name="Sintética", tenant_id=first.id)
    db.add(parent)
    db.flush()
    folder = PhotoFolder(tenant_id=first.id, parent_gallery_id=parent.id, name="Lote")
    db.add(folder)
    db.flush()
    return first, second, client, parent, folder


def test_proprietario_obrigatorio_sem_default(tenant_db):
    tenant_db.add(ParentGallery(name="Sem proprietário"))
    with pytest.raises(IntegrityError):
        tenant_db.flush()
    for entity in (ParentGallery, DerivedGallery, PhotoAsset):
        column = entity.__table__.c.tenant_id
        assert not column.nullable and column.default is None and column.server_default is None


def test_galeria_privada_nao_muda_proprietario(tenant_db):
    _, other, client, parent, _ = acervo(tenant_db)
    tenant_db.add(DerivedGallery(
        parent_gallery_id=parent.id, tenant_id=other.id, client_id=client.id, name="Inválida",
    ))
    with pytest.raises(IntegrityError):
        tenant_db.flush()


def test_foto_nao_muda_proprietario(tenant_db):
    _, other, _, parent, folder = acervo(tenant_db)
    tenant_db.add(PhotoAsset(
        tenant_id=other.id, parent_gallery_id=parent.id, folder_id=folder.id,
        filename="fake.jpg", storage_key="fake.jpg",
    ))
    with pytest.raises(IntegrityError):
        tenant_db.flush()


def test_foto_privada_nao_troca_origem(tenant_db):
    tenant, _, client, parent, folder = acervo(tenant_db)
    different = ParentGallery(name="Outra origem", tenant_id=tenant.id)
    tenant_db.add(different)
    tenant_db.flush()
    gallery = DerivedGallery(
        tenant_id=tenant.id, parent_gallery_id=different.id, client_id=client.id, name="Privada",
    )
    tenant_db.add(gallery)
    tenant_db.flush()
    tenant_db.add(PhotoAsset(
        tenant_id=tenant.id, parent_gallery_id=parent.id, derived_gallery_id=gallery.id,
        folder_id=folder.id, filename="fake.jpg", storage_key="fake.jpg",
    ))
    with pytest.raises(IntegrityError):
        tenant_db.flush()


def test_relacoes_validas_preservam_uuid(tenant_db):
    tenant, _, client, parent, _ = acervo(tenant_db)
    gallery = DerivedGallery(
        tenant_id=tenant.id, parent_gallery_id=parent.id, client_id=client.id, name="Privada",
    )
    tenant_db.add(gallery)
    tenant_db.flush()
    folder = PhotoFolder(tenant_id=tenant.id, name="Privada", parent_gallery_id=parent.id,
                         derived_gallery_id=gallery.id)
    tenant_db.add(folder)
    tenant_db.flush()
    photo = PhotoAsset(
        tenant_id=tenant.id, parent_gallery_id=parent.id, derived_gallery_id=gallery.id,
        folder_id=folder.id, filename="fake.jpg", storage_key="private/fake.jpg",
    )
    tenant_db.add(photo)
    tenant_db.commit()
    tenant_db.expire_all()
    assert tenant_db.get(PhotoAsset, photo.id).tenant_id == parent.tenant_id == gallery.tenant_id


def test_seed_vincula_admin_e_preserva_credenciais(tenant_db, monkeypatch):
    import pyotp
    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from app import seed_admin

    tenant = Tenant()
    tenant_db.add(tenant)
    tenant_db.commit()
    monkeypatch.setattr(seed_admin, "SessionLocal", sessionmaker(bind=tenant_db.bind))
    monkeypatch.setenv("ADMIN_SEED_EMAIL", "seed@example.test")
    monkeypatch.setenv("ADMIN_SEED_PASSWORD", "Synthetic-test-Password-2026!")
    monkeypatch.setenv("ADMIN_SEED_TOTP_SECRET", pyotp.random_base32())
    seed_admin.seed_admin()
    original = tenant_db.scalar(select(AdminUser))
    fingerprint = (original.id, original.password_hash, original.totp_secret)
    seed_admin.seed_admin()
    tenant_db.expire_all()
    current = tenant_db.scalar(select(AdminUser))
    assert (current.id, current.password_hash, current.totp_secret) == fingerprint
    link = tenant_db.scalar(select(TenantAdmin))
    assert link.active and link.tenant_id == tenant.id and link.admin_user_id == current.id
    link.active = False
    tenant_db.commit()
    from app.tenancy import TenantContextError
    with pytest.raises(TenantContextError):
        seed_admin.seed_admin()


def test_seed_nao_repara_admin_sem_vinculo(tenant_db, monkeypatch):
    import pyotp
    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from app import seed_admin
    from app.tenancy import TenantContextError

    tenant_db.add(Tenant())
    tenant_db.add(AdminUser(email="seed@example.test", password_hash="synthetic", totp_secret="fake"))
    tenant_db.commit()
    monkeypatch.setattr(seed_admin, "SessionLocal", sessionmaker(bind=tenant_db.bind))
    monkeypatch.setenv("ADMIN_SEED_EMAIL", "seed@example.test")
    monkeypatch.setenv("ADMIN_SEED_PASSWORD", "Synthetic-test-Password-2026!")
    monkeypatch.setenv("ADMIN_SEED_TOTP_SECRET", pyotp.random_base32())
    with pytest.raises(TenantContextError):
        seed_admin.seed_admin()
    assert tenant_db.scalar(select(TenantAdmin)) is None
