"""Distingue busca direta, consentimento explícito e autorização histórica."""

import sqlalchemy as sa
from alembic import op

revision = "20260921_0060"
down_revision = "20260921_0059"
branch_labels = None
depends_on = None

FIELDS = (
    "(authorization_method = 'legacy' AND consent_version IS NOT NULL AND subject_declaration IS NOT NULL) OR "
    "(authorization_method = 'explicit_consent' AND reference_source = 'upload' AND reference_region_id IS NULL "
    "AND consent_version IS NOT NULL AND subject_declaration IS NOT NULL AND representation_reference IS NULL) OR "
    "(authorization_method = 'direct_region' AND reference_source = 'indexed_region' "
    "AND (reference_region_id IS NOT NULL OR status IN ('ready', 'no_face', 'multiple_faces', 'low_quality', "
    "'index_incomplete', 'no_candidates', 'cancelled', 'expired', 'failed')) "
    "AND consent_version IS NULL AND subject_declaration IS NULL AND representation_reference IS NULL)"
)


def upgrade():
    with op.batch_alter_table("facial_search_request") as batch:
        batch.add_column(sa.Column("reference_source", sa.String(24), nullable=False, server_default="upload"))
        batch.add_column(sa.Column("authorization_method", sa.String(32), nullable=False, server_default="legacy"))
        batch.alter_column("consent_version", existing_type=sa.String(80), nullable=True)
        batch.alter_column("subject_declaration", existing_type=sa.String(16), nullable=True)
        batch.create_check_constraint("ck_facial_search_source", "reference_source IN ('upload', 'indexed_region', 'legacy_unknown')")
        batch.create_check_constraint("ck_facial_search_authorization", "authorization_method IN ('legacy', 'explicit_consent', 'direct_region')")
        batch.create_check_constraint("ck_facial_search_authorization_fields", FIELDS)
    # O lifecycle antigo apagava o UUID ao concluir; não inventar a origem perdida.
    op.execute("UPDATE facial_search_request SET reference_source = 'legacy_unknown' WHERE reference_region_id IS NULL AND reference_deleted_at IS NOT NULL AND reference_locator_ciphertext IS NULL")
    op.execute("UPDATE facial_search_request SET reference_source = 'indexed_region' WHERE reference_region_id IS NOT NULL")


def downgrade():
    # Nunca apagar ou fabricar consentimento para tornar o schema antigo compatível.
    count = op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM facial_search_request WHERE authorization_method <> 'legacy'"
    ))
    if count:
        raise RuntimeError("Downgrade indisponível: há consultas com nova autorização. Preserve o schema.")
    with op.batch_alter_table("facial_search_request") as batch:
        batch.drop_constraint("ck_facial_search_authorization_fields", type_="check")
        batch.drop_constraint("ck_facial_search_authorization", type_="check")
        batch.drop_constraint("ck_facial_search_source", type_="check")
        batch.drop_column("authorization_method")
        batch.drop_column("reference_source")
        batch.alter_column("consent_version", existing_type=sa.String(80), nullable=False)
        batch.alter_column("subject_declaration", existing_type=sa.String(16), nullable=False)
