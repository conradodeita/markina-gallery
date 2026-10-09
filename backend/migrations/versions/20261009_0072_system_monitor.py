"""Monitor aditivo: sem grants, defaults de domínio ou ativação de coleta."""
import sqlalchemy as sa
from alembic import op

revision = "20261009_0072"
down_revision = "20261001_0071"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("platform_owner",
        sa.Column("singleton", sa.Integer(), primary_key=True),
        sa.Column("admin_user_id", sa.Uuid(), sa.ForeignKey("admin_user.id"), nullable=False, unique=True),
        sa.Column("authorization_reference", sa.String(120), nullable=False),
        sa.Column("established_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("singleton = 1"))
    op.create_table("system_monitor_grant",
        sa.Column("admin_user_id", sa.Uuid(), sa.ForeignKey("admin_user.id"), primary_key=True),
        sa.Column("permission", sa.String(16), primary_key=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("authorization_reference", sa.String(120), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("permission IN ('metrics','tree','incidents','export')"))
    op.create_table("system_monitor_bucket",
        sa.Column("minute", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("operation", sa.String(40), primary_key=True),
        sa.Column("latency_bin", sa.Integer(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("errors", sa.Integer(), nullable=False),
        sa.Column("rejected", sa.Integer(), nullable=False),
        sa.Column("timeouts", sa.Integer(), nullable=False),
        sa.Column("total_ms", sa.Float(), nullable=False))
    op.create_table("system_monitor_sample",
        sa.Column("minute", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False))
    op.create_table("system_monitor_worker",
        sa.Column("instance", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_progress", sa.DateTime(timezone=True)))
    op.create_index("ix_system_monitor_worker_kind", "system_monitor_worker", ["kind"])
    op.create_table("system_monitor_activity",
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("auth_session.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_system_monitor_activity_last_activity", "system_monitor_activity", ["last_activity"])
    op.create_table("system_monitor_incident",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False))
    op.create_index("ix_system_monitor_incident_updated_at", "system_monitor_incident", ["updated_at"])
    op.create_table("system_monitor_transition",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False))
    op.create_index("ix_system_monitor_transition_occurred_at", "system_monitor_transition", ["occurred_at"])


def downgrade():
    raise RuntimeError("Downgrade destrutivo recusado; desabilite a coleta preservando evidências.")
