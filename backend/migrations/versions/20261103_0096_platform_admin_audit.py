"""Auditoria global aditiva; identidade/capabilities existentes preservadas."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261103_0096"
down_revision = "20261101_0095"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Auditoria global requer PostgreSQL.")
    op.create_table(
        "platform_admin_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True, unique=True),
        sa.Column("actor_admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_user.id"), nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=True),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("previous_status", sa.String(16), nullable=True),
        sa.Column("next_status", sa.String(16), nullable=True),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("origin", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("result IN ('success','denied')", name="ck_platform_admin_result"),
        sa.CheckConstraint("origin = 'web_console'", name="ck_platform_admin_origin"),
        sa.CheckConstraint("action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied')", name="ck_platform_admin_action"),
    )
    op.create_index("ix_platform_admin_event_tenant_id", "platform_admin_event", ["tenant_id"])
    op.create_index("ix_platform_admin_event_created_at", "platform_admin_event", ["created_at"])
    op.execute(sa.text("""
        CREATE FUNCTION reject_platform_admin_history_change() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'platform audit is append-only'; END;
        $$ LANGUAGE plpgsql
    """))
    op.execute(sa.text("""
        CREATE TRIGGER platform_admin_event_immutable BEFORE UPDATE OR DELETE ON platform_admin_event
        FOR EACH ROW EXECUTE FUNCTION reject_platform_admin_history_change()
    """))
    op.execute(sa.text("""
        CREATE TRIGGER platform_admin_event_no_truncate BEFORE TRUNCATE ON platform_admin_event
        FOR EACH STATEMENT EXECUTE FUNCTION reject_platform_admin_history_change()
    """))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Auditoria global requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE platform_admin_event IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM platform_admin_event LIMIT 1)")):
        raise RuntimeError("Preserve auditoria global: rollback recusado com histórico.")
    op.drop_table("platform_admin_event")
    op.execute(sa.text("DROP FUNCTION reject_platform_admin_history_change()"))
