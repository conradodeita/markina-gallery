"""Operational controls and stable-release discovery for RAW engines."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from urllib.request import Request, urlopen

from sqlalchemy import select

from app.auth import RawDevelopmentSettings, now
from app.raw_development.state import RAW_SUFFIXES

ENGINE_REPOSITORIES = {
    "lightcraft": "storytold/lightcraft",
    "rawtherapee": "RawTherapee/RawTherapee",
}
RELEASE_CACHE_TTL = timedelta(hours=24)
RELEASE_TIMEOUT_SECONDS = 3
_VERSION = re.compile(r"^v?(\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?)$")
ENGINE_FORMATS = {
    "lightcraft": (".arw", ".cr2", ".cr3", ".dng", ".nef", ".nrw", ".raf", ".rw2", ".rwl", ".pef", ".orf"),
    "rawtherapee": (".arw", ".cr2", ".cr3", ".dng", ".nef", ".nrw", ".raf", ".rw2", ".pef", ".orf"),
}


def _installed_versions(environ=None) -> dict[str, str | None]:
    environment = os.environ if environ is None else environ
    return {
        "lightcraft": _version(environment.get("RAW_DEVELOPMENT_LIGHTCRAFT_VERSION")),
        "rawtherapee": _version(environment.get("RAW_DEVELOPMENT_RAWTHERAPEE_VERSION")),
    }


def _engine_formats(engine: str, environ=None) -> list[str]:
    environment = os.environ if environ is None else environ
    configured = environment.get(f"RAW_DEVELOPMENT_{engine.upper()}_FORMATS")
    formats = (
        [value.strip().lower() for value in configured.split(",")]
        if configured is not None
        else list(ENGINE_FORMATS[engine])
    )
    return sorted(set(formats) & RAW_SUFFIXES)


def _version(value: str | None) -> str | None:
    if not value:
        return None
    match = _VERSION.fullmatch(value.strip())
    return match.group(1) if match else None


def _has_newer_stable(installed: str | None, latest: str | None) -> bool:
    if not installed or not latest:
        return False
    installed_core, _, installed_suffix = installed.partition("-")
    latest_core = latest.partition("-")[0]
    installed_parts = tuple(int(part) for part in installed_core.split("+")[0].split(".")[:3])
    latest_parts = tuple(int(part) for part in latest_core.split("+")[0].split(".")[:3])
    installed_parts = (*installed_parts, 0, 0)[:3]
    latest_parts = (*latest_parts, 0, 0)[:3]
    if latest_parts != installed_parts:
        return latest_parts > installed_parts
    return bool(installed_suffix) and not bool(latest.partition("-")[2])


def _stable_release(engine: str) -> dict[str, str | None]:
    repository = ENGINE_REPOSITORIES[engine]
    request = Request(
        f"https://api.github.com/repos/{repository}/releases?per_page=20",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Pick-your-Pic-RAW-status"},
    )
    with urlopen(request, timeout=RELEASE_TIMEOUT_SECONDS) as response:
        releases = json.loads(response.read(1_000_000))
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = release.get("tag_name")
        match = _VERSION.fullmatch(tag or "")
        if not match:
            continue
        return {
            "version": match.group(1),
            "url": f"https://github.com/{repository}/releases/tag/{tag}",
            "published_at": release.get("published_at"),
        }
    return {"version": None, "url": None, "published_at": None}


def _fresh(timestamp: datetime | None) -> bool:
    if timestamp is None:
        return False
    value = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp.astimezone(UTC)
    return value > now() - RELEASE_CACHE_TTL


def settings_payload(db, *, tenant_id, refresh_release=False, release_lookup=_stable_release, environ=None):
    settings = db.scalar(select(RawDevelopmentSettings).where(
        RawDevelopmentSettings.tenant_id == tenant_id, RawDevelopmentSettings.id == 1))
    if settings is None:
        settings = RawDevelopmentSettings(tenant_id=tenant_id, id=1, enabled=False, selected_engine="lightcraft")
        db.add(settings)
        db.flush()

    installed = _installed_versions(environ)
    engine_formats = {name: _engine_formats(name, environ) for name in ENGINE_REPOSITORIES}
    if refresh_release or not _fresh(settings.last_release_check_at):
        try:
            release = release_lookup("lightcraft")
            settings.lightcraft_latest_stable_version = release["version"]
            settings.lightcraft_latest_stable_url = release["url"]
            published_at = release.get("published_at")
            settings.lightcraft_latest_stable_published_at = (
                datetime.fromisoformat(published_at)
                if published_at
                else None
            )
            settings.release_check_status = "ok"
        except Exception:  # noqa: BLE001 -- Release status must never disable upload or controls.
            settings.release_check_status = "unavailable"
        settings.last_release_check_at = now()
        db.flush()

    engine = settings.selected_engine
    installed_version = installed.get(engine)
    lightcraft_installed = installed.get("lightcraft")
    latest = settings.lightcraft_latest_stable_version
    available = installed_version is not None
    return {
        "enabled": bool(settings.enabled and available and engine_formats[engine]),
        "selected_engine": engine,
        "engines": [
            {
                "id": name,
                "installed_version": version,
                "available": version is not None,
                "supported_formats": engine_formats[name],
            }
            for name, version in installed.items()
        ],
        "installed_version": installed_version,
        "lightcraft_installed_version": lightcraft_installed,
        "lightcraft_latest_stable_version": latest,
        "lightcraft_update_available": _has_newer_stable(lightcraft_installed, latest),
        "lightcraft_latest_stable_url": settings.lightcraft_latest_stable_url,
        "lightcraft_latest_stable_published_at": (
            settings.lightcraft_latest_stable_published_at.isoformat()
            if settings.lightcraft_latest_stable_published_at
            else None
        ),
        "last_release_check_at": (
            settings.last_release_check_at.isoformat() if settings.last_release_check_at else None
        ),
        "release_check_status": settings.release_check_status,
        "supported_formats": engine_formats[engine],
        "compatibility_policy": "Formatos são habilitados por motor; a decodificação valida cada arquivo sem lista global de fabricantes ou corpos.",
    }


def update_settings(db, *, tenant_id, enabled: bool, selected_engine: str, environ=None):
    if selected_engine not in ENGINE_REPOSITORIES:
        raise ValueError("Motor de desenvolvimento inválido.")
    if enabled:
        if _installed_versions(environ).get(selected_engine) is None:
            raise ValueError("O motor selecionado não está instalado e validado neste worker.")
        if not _engine_formats(selected_engine, environ):
            raise ValueError("O motor não declara nenhum formato RAW compatível neste worker.")
    settings = db.scalar(
        select(RawDevelopmentSettings)
        .where(RawDevelopmentSettings.tenant_id == tenant_id, RawDevelopmentSettings.id == 1)
        .with_for_update()
    )
    if settings is None:
        settings = RawDevelopmentSettings(tenant_id=tenant_id, id=1, enabled=False, selected_engine=selected_engine)
        db.add(settings)
    settings.enabled = enabled
    settings.selected_engine = selected_engine
    settings.updated_at = now()
    db.flush()
    return settings
