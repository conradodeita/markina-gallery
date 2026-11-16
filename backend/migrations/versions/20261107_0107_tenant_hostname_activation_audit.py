"""Auditoria aditiva para prontidão de hostname por tenant."""

import sqlalchemy as sa
from alembic import op

revision = "20261107_0107"
down_revision = "20261105_0106"
branch_labels = None
depends_on = None

PREVIOUS_ACTIONS = (
    "action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied',"
    "'photographer.totp_revoked','photographer.totp_revoke_denied')"
)
NEW_ACTIONS = (
    "action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied',"
    "'photographer.totp_revoked','photographer.totp_revoke_denied','tenant.host_ready',"
    "'tenant.host_activation_denied')"
)
HOST_ACTIONS = "'tenant.host_ready','tenant.host_activation_denied'"


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Ativação auditada de hostname requer PostgreSQL.")
    op.add_column("platform_admin_event", sa.Column("evidence_sha256", sa.String(64), nullable=True))
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint("ck_platform_admin_action", "platform_admin_event", NEW_ACTIONS)
    op.create_check_constraint(
        "ck_platform_admin_evidence_sha256", "platform_admin_event",
        "evidence_sha256 IS NULL OR evidence_sha256 ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_platform_admin_host_ready_context", "platform_admin_event",
        "action != 'tenant.host_ready' OR (result = 'success' AND tenant_id IS NOT NULL "
        "AND object_id IS NOT NULL AND previous_status IS NOT NULL AND previous_status = 'reserved' "
        "AND next_status IS NOT NULL AND next_status = 'ready' "
        "AND evidence_sha256 IS NOT NULL)",
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Ativação auditada de hostname requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE platform_admin_event IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM platform_admin_event "
        f"WHERE action IN ({HOST_ACTIONS}) OR evidence_sha256 IS NOT NULL LIMIT 1)"
    )):
        raise RuntimeError("Preserve auditoria de ativação de hostname: rollback recusado.")
    op.drop_constraint("ck_platform_admin_host_ready_context", "platform_admin_event", type_="check")
    op.drop_constraint("ck_platform_admin_evidence_sha256", "platform_admin_event", type_="check")
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint("ck_platform_admin_action", "platform_admin_event", PREVIOUS_ACTIONS)
    op.drop_column("platform_admin_event", "evidence_sha256")
