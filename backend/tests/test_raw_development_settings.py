import json
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import RawDevelopmentSettings
from app.raw_development import settings as raw_settings
from app.raw_development.settings import settings_payload, update_settings

TENANT_ID = uuid4()


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    RawDevelopmentSettings.__table__.create(engine)
    yield engine
    RawDevelopmentSettings.__table__.drop(engine)
    engine.dispose()


def test_release_status_tracks_lightcraft_version_and_ignores_prereleases(database):
    seen = []

    def release_lookup(engine):
        seen.append(engine)
        return {
            "version": "0.6.0",
            "url": "https://github.com/storytold/lightcraft/releases/tag/v0.6.0",
            "published_at": "2026-10-11T00:54:00Z",
        }

    with Session(database) as db:
        payload = settings_payload(
            db,
            tenant_id=TENANT_ID,
            release_lookup=release_lookup,
            environ={"RAW_DEVELOPMENT_LIGHTCRAFT_VERSION": "0.5.0", "RAW_DEVELOPMENT_RAWTHERAPEE_VERSION": "5.13.0"},
        )
        db.commit()
        assert payload["lightcraft_installed_version"] == "0.5.0"
        assert payload["lightcraft_latest_stable_version"] == "0.6.0"
        assert payload["lightcraft_update_available"] is True
        assert payload["release_check_status"] == "ok"
        assert seen == ["lightcraft"]

        cached = settings_payload(db, tenant_id=TENANT_ID, release_lookup=lambda _engine: pytest.fail("cache was bypassed"))
        assert cached["lightcraft_latest_stable_version"] == "0.6.0"


@pytest.mark.parametrize("installed", ["0.6.0", "0.7.0", "0.7.0-rc.1"])
def test_update_available_only_when_stable_release_is_newer(database, installed):
    with Session(database) as db:
        payload = settings_payload(
            db,
            tenant_id=TENANT_ID,
            release_lookup=lambda _engine: {
                "version": "0.6.0",
                "url": "https://github.com/storytold/lightcraft/releases/tag/v0.6.0",
                "published_at": None,
            },
            environ={"RAW_DEVELOPMENT_LIGHTCRAFT_VERSION": installed},
        )
        assert payload["lightcraft_update_available"] is False


def test_release_lookup_failure_keeps_upload_settings_readable(database):
    with Session(database) as db:
        payload = settings_payload(
            db,
            tenant_id=TENANT_ID,
            release_lookup=lambda _engine: (_ for _ in ()).throw(TimeoutError()),
            environ={},
        )
        assert payload["release_check_status"] == "unavailable"
        assert payload["enabled"] is False


def test_rawtherapee_reports_its_actual_two_component_version():
    versions = raw_settings._installed_versions({
        "RAW_DEVELOPMENT_LIGHTCRAFT_VERSION": "0.6.0",
        "RAW_DEVELOPMENT_RAWTHERAPEE_VERSION": "5.9",
    })
    assert versions["rawtherapee"] == "5.9"
    assert not raw_settings._has_newer_stable("5.9", "5.9.0")
    assert raw_settings._has_newer_stable("5.9", "5.10.0")


def test_lightcraft_release_lookup_skips_prerelease_and_uses_official_release_url(monkeypatch):
    releases = [
        {"tag_name": "v0.7.0-rc.1", "draft": False, "prerelease": True},
        {
            "tag_name": "v0.6.0",
            "draft": False,
            "prerelease": False,
            "published_at": "2026-10-11T00:54:00Z",
        },
    ]

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit):
            return json.dumps(releases).encode()

    monkeypatch.setattr(raw_settings, "urlopen", lambda _request, timeout: Response())
    assert raw_settings._stable_release("lightcraft") == {
        "version": "0.6.0",
        "url": "https://github.com/storytold/lightcraft/releases/tag/v0.6.0",
        "published_at": "2026-10-11T00:54:00Z",
    }


def test_enabling_requires_installed_engine_and_declared_formats(database):
    with Session(database) as db:
        with pytest.raises(ValueError, match="motor selecionado não está instalado"):
            update_settings(db, tenant_id=TENANT_ID, enabled=True, selected_engine="lightcraft", environ={})

        with pytest.raises(ValueError, match="nenhum formato RAW"):
            update_settings(
                db,
                tenant_id=TENANT_ID,
                enabled=True,
                selected_engine="lightcraft",
                environ={
                    "RAW_DEVELOPMENT_LIGHTCRAFT_VERSION": "0.6.0",
                    "RAW_DEVELOPMENT_LIGHTCRAFT_FORMATS": "",
                },
            )

        update_settings(
            db,
            tenant_id=TENANT_ID,
            enabled=True,
            selected_engine="lightcraft",
            environ={
                "RAW_DEVELOPMENT_LIGHTCRAFT_VERSION": "0.6.0",
            },
        )
        db.commit()
        payload = settings_payload(
            db,
            tenant_id=TENANT_ID,
            environ={
                "RAW_DEVELOPMENT_LIGHTCRAFT_VERSION": "0.6.0",
            },
        )
        assert payload["enabled"] is True
        assert ".arw" in payload["supported_formats"]
        assert ".nef" in payload["supported_formats"]


def test_settings_are_independent_between_tenants(database):
    other_tenant = uuid4()
    with Session(database) as db:
        update_settings(db, tenant_id=TENANT_ID, enabled=False, selected_engine="rawtherapee")
        update_settings(db, tenant_id=other_tenant, enabled=False, selected_engine="lightcraft")
        db.commit()
        first = settings_payload(db, tenant_id=TENANT_ID, release_lookup=lambda _engine: {"version": None, "url": None, "published_at": None})
        second = settings_payload(db, tenant_id=other_tenant, release_lookup=lambda _engine: {"version": None, "url": None, "published_at": None})
        assert first["selected_engine"] == "rawtherapee"
        assert second["selected_engine"] == "lightcraft"
