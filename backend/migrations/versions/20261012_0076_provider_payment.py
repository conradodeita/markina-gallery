"""Persist isolated card payments without issuing external charges.

DDL frozen from reviewed models; no runtime model import.
"""
import sqlalchemy as sa
from alembic import op

revision = "20261012_0076"
down_revision = "20261012_0075"
branch_labels = None
depends_on = None

TABLE_DDL = {
    "postgresql": [
        """CREATE TABLE provider_payment (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    client_id UUID NOT NULL,
    provider VARCHAR(24) NOT NULL,
    checkout_key VARCHAR(128) NOT NULL,
    cart_revision VARCHAR(64) NOT NULL,
    total_cents INTEGER NOT NULL,
    handle_snapshot VARCHAR(100) NOT NULL,
    configuration_version INTEGER NOT NULL,
    verification_profile VARCHAR(100) NOT NULL,
    state VARCHAR(32) NOT NULL,
    revision_number INTEGER NOT NULL,
    checkout_url TEXT,
    provider_transaction_nsu VARCHAR(200),
    confirmed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_provider_payment_owner UNIQUE (id, tenant_id, client_id),
    CONSTRAINT uq_provider_payment_checkout UNIQUE (tenant_id, client_id, checkout_key),
    CONSTRAINT uq_provider_payment_transaction UNIQUE (provider, provider_transaction_nsu),
    CONSTRAINT ck_provider_payment_provider CHECK (provider = 'infinitepay'),
    CONSTRAINT ck_provider_payment_amount_version CHECK (total_cents > 0 AND configuration_version > 0 AND revision_number >= 0),
    CONSTRAINT ck_provider_payment_state CHECK (state IN ('creating', 'awaiting_payment', 'verification_required', 'confirmed', 'failed_before_issue', 'exception', 'hold')),
    CONSTRAINT ck_provider_payment_confirmed CHECK (state != 'confirmed' OR (provider_transaction_nsu IS NOT NULL AND confirmed_at IS NOT NULL)),
    FOREIGN KEY(tenant_id) REFERENCES tenant (id),
    FOREIGN KEY(client_id) REFERENCES client (id),
    CONSTRAINT uq_owner_provider_payment_id_tenant_id UNIQUE (id, tenant_id),
    CONSTRAINT fk_owner_provider_payment_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)
)""",
        """CREATE TABLE provider_payment_attempt (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    client_id UUID NOT NULL,
    payment_id UUID NOT NULL,
    state VARCHAR(16) NOT NULL,
    error_category VARCHAR(48),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT fk_provider_attempt_payment_owner FOREIGN KEY(payment_id, tenant_id, client_id) REFERENCES provider_payment (id, tenant_id, client_id),
    CONSTRAINT uq_provider_attempt_payment UNIQUE (tenant_id, payment_id),
    CONSTRAINT ck_provider_attempt_state CHECK (state IN ('started', 'accepted', 'refused', 'unknown')),
    FOREIGN KEY(tenant_id) REFERENCES tenant (id),
    FOREIGN KEY(client_id) REFERENCES client (id),
    CONSTRAINT uq_owner_provider_payment_attempt_id_tenant_id UNIQUE (id, tenant_id),
    CONSTRAINT fk_owner_provider_payment_attempt_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)
)""",
        """CREATE TABLE provider_payment_receipt (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    client_id UUID NOT NULL,
    payment_id UUID NOT NULL,
    digest VARCHAR(64) NOT NULL,
    transaction_nsu VARCHAR(200) NOT NULL,
    slug VARCHAR(512) NOT NULL,
    verification_profile VARCHAR(100) NOT NULL,
    state VARCHAR(16) NOT NULL,
    attempts INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT fk_provider_receipt_payment_owner FOREIGN KEY(payment_id, tenant_id, client_id) REFERENCES provider_payment (id, tenant_id, client_id),
    CONSTRAINT uq_provider_receipt_digest UNIQUE (tenant_id, payment_id, digest),
    CONSTRAINT ck_provider_receipt_state CHECK (state IN ('queued', 'processing', 'verified', 'ignored', 'failed')),
    CONSTRAINT ck_provider_receipt_attempts CHECK (attempts >= 0),
    FOREIGN KEY(tenant_id) REFERENCES tenant (id),
    FOREIGN KEY(client_id) REFERENCES client (id),
    CONSTRAINT uq_owner_provider_payment_receipt_id_tenant_id UNIQUE (id, tenant_id),
    CONSTRAINT fk_owner_provider_payment_receipt_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)
)""",
        """CREATE INDEX ix_provider_payment_client_id ON provider_payment (client_id)""",
        """CREATE INDEX ix_provider_payment_state ON provider_payment (state)""",
        """CREATE INDEX ix_provider_payment_tenant_id ON provider_payment (tenant_id)""",
        """CREATE INDEX ix_provider_payment_attempt_client_id ON provider_payment_attempt (client_id)""",
        """CREATE INDEX ix_provider_payment_attempt_payment_id ON provider_payment_attempt (payment_id)""",
        """CREATE INDEX ix_provider_payment_attempt_tenant_id ON provider_payment_attempt (tenant_id)""",
        """CREATE INDEX ix_provider_payment_receipt_client_id ON provider_payment_receipt (client_id)""",
        """CREATE INDEX ix_provider_payment_receipt_payment_id ON provider_payment_receipt (payment_id)""",
        """CREATE INDEX ix_provider_payment_receipt_state ON provider_payment_receipt (state)""",
        """CREATE INDEX ix_provider_payment_receipt_tenant_id ON provider_payment_receipt (tenant_id)""",
    ],
    "sqlite": [
        """CREATE TABLE provider_payment (
    id CHAR(32) NOT NULL,
    tenant_id CHAR(32) NOT NULL,
    client_id CHAR(32) NOT NULL,
    provider VARCHAR(24) NOT NULL,
    checkout_key VARCHAR(128) NOT NULL,
    cart_revision VARCHAR(64) NOT NULL,
    total_cents INTEGER NOT NULL,
    handle_snapshot VARCHAR(100) NOT NULL,
    configuration_version INTEGER NOT NULL,
    verification_profile VARCHAR(100) NOT NULL,
    state VARCHAR(32) NOT NULL,
    revision_number INTEGER NOT NULL,
    checkout_url TEXT,
    provider_transaction_nsu VARCHAR(200),
    confirmed_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_provider_payment_owner UNIQUE (id, tenant_id, client_id),
    CONSTRAINT uq_provider_payment_checkout UNIQUE (tenant_id, client_id, checkout_key),
    CONSTRAINT uq_provider_payment_transaction UNIQUE (provider, provider_transaction_nsu),
    CONSTRAINT ck_provider_payment_provider CHECK (provider = 'infinitepay'),
    CONSTRAINT ck_provider_payment_amount_version CHECK (total_cents > 0 AND configuration_version > 0 AND revision_number >= 0),
    CONSTRAINT ck_provider_payment_state CHECK (state IN ('creating', 'awaiting_payment', 'verification_required', 'confirmed', 'failed_before_issue', 'exception', 'hold')),
    CONSTRAINT ck_provider_payment_confirmed CHECK (state != 'confirmed' OR (provider_transaction_nsu IS NOT NULL AND confirmed_at IS NOT NULL)),
    FOREIGN KEY(tenant_id) REFERENCES tenant (id),
    FOREIGN KEY(client_id) REFERENCES client (id),
    CONSTRAINT uq_owner_provider_payment_id_tenant_id UNIQUE (id, tenant_id),
    CONSTRAINT fk_owner_provider_payment_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)
)""",
        """CREATE TABLE provider_payment_attempt (
    id CHAR(32) NOT NULL,
    tenant_id CHAR(32) NOT NULL,
    client_id CHAR(32) NOT NULL,
    payment_id CHAR(32) NOT NULL,
    state VARCHAR(16) NOT NULL,
    error_category VARCHAR(48),
    created_at DATETIME NOT NULL,
    completed_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT fk_provider_attempt_payment_owner FOREIGN KEY(payment_id, tenant_id, client_id) REFERENCES provider_payment (id, tenant_id, client_id),
    CONSTRAINT uq_provider_attempt_payment UNIQUE (tenant_id, payment_id),
    CONSTRAINT ck_provider_attempt_state CHECK (state IN ('started', 'accepted', 'refused', 'unknown')),
    FOREIGN KEY(tenant_id) REFERENCES tenant (id),
    FOREIGN KEY(client_id) REFERENCES client (id),
    CONSTRAINT uq_owner_provider_payment_attempt_id_tenant_id UNIQUE (id, tenant_id),
    CONSTRAINT fk_owner_provider_payment_attempt_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)
)""",
        """CREATE TABLE provider_payment_receipt (
    id CHAR(32) NOT NULL,
    tenant_id CHAR(32) NOT NULL,
    client_id CHAR(32) NOT NULL,
    payment_id CHAR(32) NOT NULL,
    digest VARCHAR(64) NOT NULL,
    transaction_nsu VARCHAR(200) NOT NULL,
    slug VARCHAR(512) NOT NULL,
    verification_profile VARCHAR(100) NOT NULL,
    state VARCHAR(16) NOT NULL,
    attempts INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    processed_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT fk_provider_receipt_payment_owner FOREIGN KEY(payment_id, tenant_id, client_id) REFERENCES provider_payment (id, tenant_id, client_id),
    CONSTRAINT uq_provider_receipt_digest UNIQUE (tenant_id, payment_id, digest),
    CONSTRAINT ck_provider_receipt_state CHECK (state IN ('queued', 'processing', 'verified', 'ignored', 'failed')),
    CONSTRAINT ck_provider_receipt_attempts CHECK (attempts >= 0),
    FOREIGN KEY(tenant_id) REFERENCES tenant (id),
    FOREIGN KEY(client_id) REFERENCES client (id),
    CONSTRAINT uq_owner_provider_payment_receipt_id_tenant_id UNIQUE (id, tenant_id),
    CONSTRAINT fk_owner_provider_payment_receipt_client_id_tenant_id_client FOREIGN KEY(client_id, tenant_id) REFERENCES client (id, tenant_id)
)""",
        """CREATE INDEX ix_provider_payment_client_id ON provider_payment (client_id)""",
        """CREATE INDEX ix_provider_payment_state ON provider_payment (state)""",
        """CREATE INDEX ix_provider_payment_tenant_id ON provider_payment (tenant_id)""",
        """CREATE INDEX ix_provider_payment_attempt_client_id ON provider_payment_attempt (client_id)""",
        """CREATE INDEX ix_provider_payment_attempt_payment_id ON provider_payment_attempt (payment_id)""",
        """CREATE INDEX ix_provider_payment_attempt_tenant_id ON provider_payment_attempt (tenant_id)""",
        """CREATE INDEX ix_provider_payment_receipt_client_id ON provider_payment_receipt (client_id)""",
        """CREATE INDEX ix_provider_payment_receipt_payment_id ON provider_payment_receipt (payment_id)""",
        """CREATE INDEX ix_provider_payment_receipt_state ON provider_payment_receipt (state)""",
        """CREATE INDEX ix_provider_payment_receipt_tenant_id ON provider_payment_receipt (tenant_id)""",
    ],
}


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect not in TABLE_DDL:
        raise RuntimeError("Dialeto não suportado nesta migração.")
    for statement in TABLE_DDL[dialect]:
        op.execute(sa.text(statement))
    with op.batch_alter_table("sale_order") as batch:
        batch.add_column(sa.Column("provider_payment_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_sale_order_provider_payment_owner", "provider_payment",
                                 ["provider_payment_id", "tenant_id", "client_id"],
                                 ["id", "tenant_id", "client_id"])
        batch.create_check_constraint("ck_sale_order_single_payment_method",
                                      "payment_group_id IS NULL OR provider_payment_id IS NULL")
        batch.create_index("ix_sale_order_provider_payment_id", ["provider_payment_id"])


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("provider_payment", "provider_payment_attempt", "provider_payment_receipt"):
        if bind.scalar(sa.text(f"SELECT COUNT(*) FROM {table}")):
            raise RuntimeError("Downgrade recusado: preserve compras e evidências de cartão.")
    with op.batch_alter_table("sale_order") as batch:
        batch.drop_index("ix_sale_order_provider_payment_id")
        batch.drop_constraint("ck_sale_order_single_payment_method", type_="check")
        batch.drop_constraint("fk_sale_order_provider_payment_owner", type_="foreignkey")
        batch.drop_column("provider_payment_id")
    for table in ("provider_payment_receipt", "provider_payment_attempt", "provider_payment"):
        op.drop_table(table)
