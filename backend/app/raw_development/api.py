"""Configuração administrativa do módulo RAW com escopo de tenant."""

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import RawDevelopmentSettings, audit


class SettingsInput(BaseModel):
    enabled: bool
    selected_engine: str


def register_routes(app, *, db_session, require_admin, require_same_origin, tenant_context):
    dependency = Depends(db_session)

    @app.get("/admin/settings/raw-development")
    def get_settings(request: Request, db: Session = dependency):
        tenant_id = tenant_context(db, request)
        require_admin(request)
        from app.raw_development.settings import settings_payload
        payload = settings_payload(db, tenant_id=tenant_id)
        db.commit()
        return payload

    @app.get("/admin/settings/raw-development/capabilities")
    def capabilities(request: Request, db: Session = dependency):
        tenant_id = tenant_context(db, request)
        require_admin(request)
        from app.raw_development.settings import _engine_formats, _installed_versions
        settings = db.scalar(select(RawDevelopmentSettings).where(
            RawDevelopmentSettings.tenant_id == tenant_id, RawDevelopmentSettings.id == 1))
        engine = settings.selected_engine if settings else "lightcraft"
        formats = _engine_formats(engine)
        return {"enabled": bool(settings and settings.enabled and _installed_versions().get(engine) and formats),
                "formats": formats}

    @app.patch("/admin/settings/raw-development")
    def update_settings(payload: SettingsInput, request: Request, db: Session = dependency):
        tenant_id = tenant_context(db, request)
        require_admin(request)
        require_same_origin(request)
        from app.raw_development.settings import settings_payload
        from app.raw_development.settings import update_settings as update
        try:
            update(db, tenant_id=tenant_id, enabled=payload.enabled, selected_engine=payload.selected_engine)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        audit(db, "raw_development.settings_updated", payload.selected_engine, tenant_id=tenant_id)
        db.commit()
        return settings_payload(db, tenant_id=tenant_id)

    @app.post("/admin/settings/raw-development/release-check")
    def refresh_release(request: Request, db: Session = dependency):
        tenant_id = tenant_context(db, request)
        require_admin(request)
        require_same_origin(request)
        from app.raw_development.settings import settings_payload
        payload = settings_payload(db, tenant_id=tenant_id, refresh_release=True)
        db.commit()
        audit(db, "raw_development.lightcraft_release_checked", payload["release_check_status"], tenant_id=tenant_id)
        db.commit()
        return payload
