"""Tabelas técnicas próprias; identidades são usadas somente para autorização/atividade."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.auth import Base, now

PERMISSIONS = ("metrics", "tree", "incidents", "export")


class PlatformOwner(Base):
    """Único proprietário, identificado pela conta permanente e não pelo e-mail."""
    __tablename__ = "platform_owner"
    __table_args__ = (CheckConstraint("singleton = 1"),)
    singleton: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), unique=True)
    authorization_reference: Mapped[str] = mapped_column(String(120))
    established_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MonitorGrant(Base):
    __tablename__ = "system_monitor_grant"
    __table_args__ = (CheckConstraint("permission IN ('metrics','tree','incidents','export')"),)
    admin_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), primary_key=True)
    permission: Mapped[str] = mapped_column(String(16), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    authorization_reference: Mapped[str] = mapped_column(String(120))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MonitorBucket(Base):
    __tablename__ = "system_monitor_bucket"
    minute: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    operation: Mapped[str] = mapped_column(String(40), primary_key=True)
    latency_bin: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    timeouts: Mapped[int] = mapped_column(Integer, default=0)
    total_ms: Mapped[float] = mapped_column(Float, default=0)


class MonitorSample(Base):
    __tablename__ = "system_monitor_sample"
    minute: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class MonitorWorker(Base):
    __tablename__ = "system_monitor_worker"
    instance: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_progress: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MonitorActivity(Base):
    __tablename__ = "system_monitor_activity"
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_session.id", ondelete="CASCADE"), primary_key=True,
    )
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class MonitorIncident(Base):
    __tablename__ = "system_monitor_incident"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    state: Mapped[str] = mapped_column(String(16))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    evidence: Mapped[dict] = mapped_column(JSON)


class MonitorTransition(Base):
    __tablename__ = "system_monitor_transition"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    evidence: Mapped[dict] = mapped_column(JSON)
