"""Rotas administrativas com autorização própria e dados privados não cacheáveis."""
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import BoundedSemaphore
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy.exc import SQLAlchemyError

from app.auth import Role, SessionLocal, audit, current_session
from app.system_monitor.access import permissions, require_permission
from app.system_monitor.activity import page, signal, totals
from app.system_monitor.config import Settings, enabled
from app.system_monitor.incidents import incident_rows
from app.system_monitor.models import PERMISSIONS
from app.system_monitor.report import build_report, export_report
from app.system_monitor.store import bounded

router = APIRouter()
HEADERS = {"Cache-Control": "private, no-store"}
_read_slots = BoundedSemaphore(2)


@contextmanager
def authorized(request, permission=None):
    if not _read_slots.acquire(blocking=False):
        raise HTTPException(429, "Monitor ocupado; tente novamente.", headers={**HEADERS, "Retry-After": "60"})
    try:
        session = current_session(request, Role.ADMIN)
        with SessionLocal() as db:
            bounded(db)
            if permission:
                require_permission(db, session.subject_id, permission)
            yield db, session
            renewed = current_session(request, Role.ADMIN)
            if renewed.id != session.id:
                raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
            if permission:
                require_permission(db, renewed.subject_id, permission)
    except SQLAlchemyError:
        raise HTTPException(503, "Monitor temporariamente indisponível.", headers=HEADERS) from None
    finally:
        _read_slots.release()


@router.get("/admin/system-monitor/capabilities")
def capabilities(request: Request, response: Response):
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        allowed = permissions(db, session.subject_id)
        return {key: key in allowed for key in PERMISSIONS}


@router.get("/admin/system-monitor")
def summary(request: Request, response: Response, minutes: int = Query(60, ge=5, le=1440)):
    response.headers.update(HEADERS)
    with authorized(request, "metrics") as (db, _session):
        return build_report(db, datetime.now(UTC), minutes)


@router.get("/admin/system-monitor/tree")
def tree(request: Request, response: Response, tenant_id: UUID | None = None,
         cursor: UUID | None = None, limit: int = Query(25, ge=1, le=100),
         q: str = Query("", max_length=80),
         state: Literal["all", "active", "recent", "valid_session", "inactive", "unknown"] = "all"):
    response.headers.update(HEADERS)
    with authorized(request, "tree") as (db, session):
        instant = datetime.now(UTC)
        result = page(db, instant, tenant_id=tenant_id, cursor=cursor, limit=limit, query=q, state=state)
        if tenant_id is None:
            result["totals"] = totals(db, instant)
        audit(db, "system_monitor.tree_consulted", str(session.subject_id), tenant_id=session.tenant_id)
        db.commit()
        return result


@router.get("/admin/system-monitor/incidents")
def incidents(request: Request, response: Response, minutes: int = Query(60, ge=5, le=1440)):
    response.headers.update(HEADERS)
    with authorized(request, "incidents") as (db, _session):
        instant = datetime.now(UTC)
        return incident_rows(db, instant - timedelta(minutes=minutes), instant)


@router.get("/admin/system-monitor/report")
def report(request: Request, minutes: int = Query(60, ge=5, le=1440),
           format: Literal["json", "text"] = "json"):
    with authorized(request, "export") as (db, session):
        require_permission(db, session.subject_id, "metrics")
        include_incidents = "incidents" in permissions(db, session.subject_id)
        data = build_report(db, datetime.now(UTC), minutes,
                            include_incidents=include_incidents)
        try:
            body = export_report(data, format)
        except ValueError:
            raise HTTPException(413, "Reduza o período do relatório.", headers=HEADERS) from None
        audit(db, "system_monitor.report_exported", str(session.subject_id), tenant_id=session.tenant_id)
        db.commit()
        require_permission(db, session.subject_id, "metrics")
        if include_incidents:
            require_permission(db, session.subject_id, "incidents")
    return Response(body, media_type="application/json" if format == "json" else "text/plain",
                    headers={**HEADERS, "Content-Disposition": f'attachment; filename="pick-your-pic-diagnostic.{"json" if format == "json" else "txt"}"'})


@router.get("/auth/activity-policy")
def activity_policy(request: Request, response: Response):
    response.headers.update(HEADERS)
    current_session(request)
    settings = Settings.read()
    return {"enabled": enabled(), "interval_seconds": 60,
            "active_seconds": settings.active_seconds, "recent_seconds": settings.recent_seconds}


@router.post("/auth/activity", status_code=204)
def activity(request: Request):
    if request.headers.get("X-Monitor-Activity") != "1":
        raise HTTPException(403, "Sinal não autorizado.", headers=HEADERS)
    session = current_session(request)
    if not enabled():
        return Response(status_code=204, headers=HEADERS)
    try:
        with SessionLocal() as db:
            bounded(db)
            signal(db, session.id, datetime.now(UTC))
            # Validate again before committing an identity-associated signal.
            if current_session(request).id != session.id:
                raise HTTPException(403, "Sinal não autorizado.", headers=HEADERS)
            db.commit()
    except SQLAlchemyError:
        raise HTTPException(503, "Sinal temporariamente indisponível.", headers=HEADERS) from None
    return Response(status_code=204, headers=HEADERS)
