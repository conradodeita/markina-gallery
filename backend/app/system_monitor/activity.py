"""Atividade registrada por interação; sessão válida continua sendo outro sinal."""
from datetime import timedelta
from uuid import UUID

from sqlalchemy import String, case, cast, func, or_, select

from app.auth import AdminUser, AuthSession, Client, FacialJob, MediaJob, Tenant, TenantAdmin
from app.system_monitor.config import Settings, enabled, utc
from app.system_monitor.models import MonitorActivity, MonitorSample
from app.system_monitor.store import insert


def signal(db, session_id, instant):
    statement = insert(db, MonitorActivity).values(session_id=session_id, last_activity=instant)
    db.execute(statement.on_conflict_do_update(index_elements=["session_id"],
        set_={"last_activity": instant},
        where=MonitorActivity.last_activity <= instant - timedelta(seconds=60)))


def classify(last_activity, sessions, fresh, instant, settings=None):
    settings = settings or Settings.read()
    if not fresh:
        return "unknown"
    if sessions and last_activity:
        age = (instant - utc(last_activity)).total_seconds()
        if 0 <= age <= settings.active_seconds:
            return "active"
        if 0 <= age <= settings.recent_seconds:
            return "recent"
    return "valid_session" if sessions else "inactive"


def session_aggregate(instant, role, tenant_id=None):
    membership = select(TenantAdmin.id).where(
        TenantAdmin.admin_user_id == AuthSession.subject_id,
        TenantAdmin.tenant_id == AuthSession.tenant_id, TenantAdmin.active.is_(True),
    ).exists()
    verified = select(AdminUser.id).where(
        AdminUser.id == AuthSession.subject_id, AdminUser.email_verified.is_(True),
    ).exists()
    unambiguous = select(func.count()).select_from(TenantAdmin).where(
        TenantAdmin.admin_user_id == AuthSession.subject_id, TenantAdmin.active.is_(True),
    ).scalar_subquery() == 1
    key = AuthSession.tenant_id if role == "admin" else AuthSession.subject_id
    query = select(key.label("subject"), func.count().label("sessions"),
                   func.max(MonitorActivity.last_activity).label("activity"))
    query = query.outerjoin(MonitorActivity, MonitorActivity.session_id == AuthSession.id)
    query = query.join(Tenant, Tenant.id == AuthSession.tenant_id).where(
        AuthSession.role == role, AuthSession.revoked_at.is_(None), AuthSession.expires_at > instant,
        Tenant.status == "active",
    )
    if role == "admin":
        query = query.where(membership, verified, unambiguous, AuthSession.admin_subject_id == AuthSession.subject_id)
    else:
        query = query.where(AuthSession.client_subject_id == AuthSession.subject_id,
            select(Client.id).where(Client.id == AuthSession.subject_id, Client.tenant_id == AuthSession.tenant_id).exists())
    if tenant_id is not None:
        query = query.where(AuthSession.tenant_id == tenant_id)
    return query.group_by(key).subquery()


def page(db, instant, *, tenant_id: UUID | None = None, cursor: UUID | None = None,
         limit=25, query="", state="all"):
    settings = Settings.read()
    last_sample = db.scalar(select(func.max(MonitorSample.minute)))
    fresh = bool(enabled() and last_sample and 0 <= (instant - utc(last_sample)).total_seconds() <= settings.stale_seconds)
    role = "client" if tenant_id else "admin"
    stats = session_aggregate(instant, role, tenant_id)
    model = Client if tenant_id else Tenant
    sessions = func.coalesce(stats.c.sessions, 0)
    activity = case((stats.c.activity <= instant, stats.c.activity), else_=None)
    status = case(
        (sessions > 0, case(
            (activity >= instant - timedelta(seconds=settings.active_seconds), "active"),
            (activity >= instant - timedelta(seconds=settings.recent_seconds), "recent"),
            else_="valid_session")), else_="inactive") if fresh else case((True, "unknown"))
    client_count = select(func.count()).select_from(Client).where(Client.tenant_id == Tenant.id).correlate(Tenant).scalar_subquery()
    columns = [model.id, sessions.label("sessions"), activity.label("activity"), status.label("state")]
    columns += [Client.full_name.label("label")] if tenant_id else [client_count.label("clients"), Tenant.status.label("account_state")]
    statement = select(*columns).outerjoin(stats, stats.c.subject == model.id)
    if tenant_id:
        statement = statement.where(Client.tenant_id == tenant_id)
    if cursor:
        statement = statement.where(model.id > cursor)
    if query:
        pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        criterion = cast(model.id, String).ilike(pattern, escape="\\")
        if tenant_id:
            criterion = or_(criterion, Client.full_name.ilike(pattern, escape="\\"))
        else:
            criterion = or_(criterion, select(Client.id).where(
                Client.tenant_id == Tenant.id, Client.full_name.ilike(pattern, escape="\\"),
            ).exists())
        statement = statement.where(criterion)
    if state != "all":
        statement = statement.where(status == state)
    rows = db.execute(statement.order_by(model.id).limit(min(100, max(1, limit)) + 1)).mappings().all()
    items = []
    issues = {}
    if not tenant_id and rows:
        ids = [row["id"] for row in rows[:limit]]
        for name, job in (("media_failed", MediaJob), ("facial_failed", FacialJob)):
            for owner, count in db.execute(select(job.tenant_id, func.count()).where(
                job.tenant_id.in_(ids), job.status == "failed",
            ).group_by(job.tenant_id)):
                issues.setdefault(owner, {})[name] = count
    for row in rows[:limit]:
        item = {"id": str(row["id"]), "label": row["label"] if tenant_id else f"Fotógrafo {str(row['id'])[:8]}",
                "sessions": row["sessions"], "state": row["state"],
                "last_activity": utc(row["activity"]).isoformat() if row["activity"] else None}
        if not tenant_id:
            item.update(clients=row["clients"], account_state=row["account_state"],
                        operational_issues=issues.get(row["id"], {}))
        items.append(item)
    return {"items": items, "next_cursor": str(rows[limit - 1]["id"]) if len(rows) > limit else None,
            "collected_at": instant.isoformat(), "activity_coverage": "observed" if fresh else "unknown",
            "rules": {"active_seconds": settings.active_seconds, "recent_seconds": settings.recent_seconds}}


def totals(db, instant):
    settings = Settings.read()
    last_sample = db.scalar(select(func.max(MonitorSample.minute)))
    fresh = enabled() and last_sample and 0 <= (instant - utc(last_sample)).total_seconds() <= settings.stale_seconds
    result = {"photographers": db.scalar(select(func.count()).select_from(Tenant)),
              "clients": db.scalar(select(func.count()).select_from(Client)),
              "active_photographers": None, "active_clients": None}
    if fresh:
        for role, key in (("admin", "active_photographers"), ("client", "active_clients")):
            stats = session_aggregate(instant, role)
            result[key] = db.scalar(select(func.count()).select_from(stats).where(
                stats.c.activity >= instant - timedelta(seconds=settings.active_seconds),
                stats.c.activity <= instant,
            ))
    return result
