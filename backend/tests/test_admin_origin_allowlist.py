from fastapi import HTTPException
from starlette.requests import Request

from app.main import require_same_origin


def make_request(origin: str | None, *, host: str = "markina.pickyourpic.com.br") -> Request:
    headers = [(b"host", host.encode("ascii"))]
    if origin:
        headers.append((b"origin", origin.encode("ascii")))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "server": (host, 443),
            "client": ("127.0.0.1", 12345),
            "headers": headers,
        }
    )


def test_canonical_origin_is_allowed(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://markina.pickyourpic.com.br")
    monkeypatch.delenv("PUBLIC_APP_ORIGINS", raising=False)

    assert require_same_origin(make_request("https://markina.pickyourpic.com.br")) is None


def test_explicit_old_origin_is_allowed_during_migration(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://markina.pickyourpic.com.br")
    monkeypatch.setenv(
        "PUBLIC_APP_ORIGINS", "https://markina-homolog.duckdns.org"
    )

    assert require_same_origin(make_request("https://markina-homolog.duckdns.org")) is None


def test_unconfigured_origin_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://markina.pickyourpic.com.br")
    monkeypatch.delenv("PUBLIC_APP_ORIGINS", raising=False)

    try:
        require_same_origin(make_request("https://attacker.invalid"))
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("origem não configurada deveria ser recusada")


def test_invalid_additional_origin_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://markina.pickyourpic.com.br")
    monkeypatch.setenv("PUBLIC_APP_ORIGINS", "https://*.example.invalid")

    try:
        require_same_origin(make_request("https://markina.pickyourpic.com.br"))
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("allowlist inválida deveria falhar fechada")


def test_originless_legacy_request_keeps_existing_behavior(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://markina.pickyourpic.com.br")
    monkeypatch.delenv("PUBLIC_APP_ORIGINS", raising=False)

    assert require_same_origin(make_request(None)) is None
