"""Keep an append-only audit when a card confirmation is held.

DDL frozen for PostgreSQL and SQLite; no runtime model import.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261012_0077"
down_revision = "20261012_0076"
branch_labels = None
depends_on = None

DDL = {
    "postgresql": """CREATE TABLE provider_payment_correction (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    client_id UUID NOT NULL,
    payment_id UUID NOT NULL,
    actor_admin_id UUID NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    reason VARCHAR(500) NOT NULL,
    previous_revision INTEGER NOT NULL,
    previous_transaction_nsu VARCHAR(200) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_provider_correction_payment_owner FOREIGN KEY(payment_id, tenant_id, client_id)
        REFERENCES provider_payment (id, tenant_id, client_id),
    CONSTRAINT uq_provider_correction_idempotency UNIQUE (tenant_id, payment_id, idempotency_key),
    CONSTRAINT ck_provider_correction_revision CHECK (previous_revision >= 1),
    CONSTRAINT ck_provider_correction_transaction CHECK (previous_transaction_nsu <> ''),
    FOREIGN KEY(tenant_id) REFERENCES tenant (id),
    FOREIGN KEY(client_id) REFERENCES client (id),
    FOREIGN KEY(actor_admin_id) REFERENCES admin_user (id),
    CONSTRAINT uq_owner_provider_payment_correction_id_tenant_id UNIQUE (id, tenant_id),
    CONSTRAINT fk_owner_provider_payment_correction_client_id_tenant_id_client
        FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)
)""",
    "sqlite": """CREATE TABLE provider_payment_correction (
    id CHAR(32) NOT NULL,
    tenant_id CHAR(32) NOT NULL,
    client_id CHAR(32) NOT NULL,
    payment_id CHAR(32) NOT NULL,
    actor_admin_id CHAR(32) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    reason VARCHAR(500) NOT NULL,
    previous_revision INTEGER NOT NULL,
    previous_transaction_nsu VARCHAR(200) NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_provider_correction_payment_owner FOREIGN KEY(payment_id, tenant_id, client_id)
        REFERENCES provider_payment (id, tenant_id, client_id),
    CONSTRAINT uq_provider_correction_idempotency UNIQUE (tenant_id, payment_id, idempotency_key),
    CONSTRAINT ck_provider_correction_revision CHECK (previous_revision >= 1),
    CONSTRAINT ck_provider_correction_transaction CHECK (previous_transaction_nsu <> ''),
    FOREIGN KEY(tenant_id) REFERENCES tenant (id),
    FOREIGN KEY(client_id) REFERENCES client (id),
    FOREIGN KEY(actor_admin_id) REFERENCES admin_user (id),
    CONSTRAINT uq_owner_provider_payment_correction_id_tenant_id UNIQUE (id, tenant_id),
    CONSTRAINT fk_owner_provider_payment_correction_client_id_tenant_id_client
        FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)
)""",
}


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect not in DDL:
        raise RuntimeError("Dialeto não suportado nesta migração.")
    op.execute(sa.text(DDL[dialect]))
    op.create_index("ix_provider_payment_correction_client_id", "provider_payment_correction", ["client_id"])
    op.create_index("ix_provider_payment_correction_payment_id", "provider_payment_correction", ["payment_id"])
    op.create_index("ix_provider_payment_correction_tenant_id", "provider_payment_correction", ["tenant_id"])
    op.create_index("ix_provider_payment_correction_actor_admin_id", "provider_payment_correction", ["actor_admin_id"])


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM provider_payment_correction")):
        raise RuntimeError("Downgrade recusado: preserve histórico de correções financeiras.")
    op.drop_index("ix_provider_payment_correction_actor_admin_id", table_name="provider_payment_correction")
    op.drop_index("ix_provider_payment_correction_tenant_id", table_name="provider_payment_correction")
    op.drop_index("ix_provider_payment_correction_payment_id", table_name="provider_payment_correction")
    op.drop_index("ix_provider_payment_correction_client_id", table_name="provider_payment_correction")
    op.drop_table("provider_payment_correction")
