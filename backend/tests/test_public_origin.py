"""Origem pública compartilhada pelos links sensíveis."""

import pytest

from app.public_origin import PublicOriginError, public_app_origin


@pytest.fixture(autouse=True)
def isolated_origins(monkeypatch):
    monkeypatch.delenv("PUBLIC_APP_ORIGIN", raising=False)
    monkeypatch.delenv("MARKINA_PUBLIC_URL", raising=False)


def test_canonical_origin_precedes_legacy_and_tracks_domain_change(monkeypatch):
    monkeypatch.setenv("MARKINA_PUBLIC_URL", "http://localhost:3000")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://first.example/")
    assert public_app_origin("staging") == "https://first.example"
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://new-gallery.example/")
    assert public_app_origin("staging") == "https://new-gallery.example"


def test_local_http_fallback_only_without_configured_origin(monkeypatch):
    assert public_app_origin("test", local_fallback="http://testserver") == "http://testserver"
    with pytest.raises(PublicOriginError):
        public_app_origin("staging", local_fallback="http://testserver")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://localhost")
    with pytest.raises(PublicOriginError):
        public_app_origin("staging", local_fallback="http://testserver")
