"""EMS canonical schema: db/001_ems_schema.sql + db/002_ems_settings_tokens.sql.

Revision ID: 0001
Revises:
"""
from migrations.sqlfile import run_sql_file

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_sql_file("001_ems_schema.sql")
    run_sql_file("002_ems_settings_tokens.sql")


def downgrade() -> None:
    raise NotImplementedError("The canonical schema is not reversible; restore from backup instead.")
