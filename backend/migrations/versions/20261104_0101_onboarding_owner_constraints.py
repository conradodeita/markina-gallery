"""Vínculo administrativo composto para perfil e aceite do onboarding."""

import sqlalchemy as sa
from alembic import op

revision = "20261104_0101"
down_revision = "20261104_0100"
branch_labels = None
depends_on = None

TABLES = (
    ("photographer_business_profile", "fk_profile_admin_tenant"),
    ("photographer_terms_acceptance", "fk_terms_admin_tenant"),
)


def upgrade():
    for table, _constraint in TABLES:
        invalid = op.get_bind().scalar(sa.text(
            f"SELECT EXISTS(SELECT 1 FROM {table} p WHERE NOT EXISTS "
            "(SELECT 1 FROM tenant_admin a WHERE a.admin_user_id=p.admin_user_id AND a.tenant_id=p.tenant_id))"
        ))
        if invalid:
            raise RuntimeError("Onboarding contém vínculo incompatível; migração recusada sem alterar dados.")
    for table, constraint in TABLES:
        op.create_foreign_key(constraint, table, "tenant_admin", ["admin_user_id", "tenant_id"], ["admin_user_id", "tenant_id"])


def downgrade():
    for table, constraint in reversed(TABLES):
        op.drop_constraint(constraint, table, type_="foreignkey")
