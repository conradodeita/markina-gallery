"""Registrar reabertura explícita de tenant no console do proprietário."""

import sqlalchemy as sa
from alembic import op

revision = "20261109_0119"
down_revision = "20261109_0118"
branch_labels = None
depends_on = None

_PREVIOUS_ACTIONS = (
    "action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied',"
    "'photographer.totp_revoked','photographer.totp_revoke_denied','tenant.host_ready',"
    "'tenant.host_activation_denied','media_archive.recovery_pricing_updated')"
)
_REOPEN_ACTIONS = _PREVIOUS_ACTIONS[:-1] + ", 'tenant.reopened')"
_REOPEN_CONTEXT = (
    "action != 'tenant.reopened' OR (result = 'success' AND tenant_id IS NOT NULL "
    "AND object_id IS NOT NULL AND previous_status = 'closed' AND next_status = 'open')"
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Auditoria de reabertura requer PostgreSQL.")
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint("ck_platform_admin_action", "platform_admin_event", _REOPEN_ACTIONS)
    op.create_check_constraint("ck_platform_admin_tenant_reopened_context", "platform_admin_event", _REOPEN_CONTEXT)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Auditoria de reabertura requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE platform_admin_event IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM platform_admin_event WHERE action = 'tenant.reopened')"
    )):
        raise RuntimeError("Preserve auditoria de reabertura de tenant: rollback recusado.")
    op.drop_constraint("ck_platform_admin_tenant_reopened_context", "platform_admin_event", type_="check")
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint("ck_platform_admin_action", "platform_admin_event", _PREVIOUS_ACTIONS)
