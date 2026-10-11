"""Rate limits, dashboard cache, Google linking and worker grants: db/003_ems_platform_gaps.sql.

Revision ID: 0002
Revises: 0001
"""
from migrations.sqlfile import run_sql_file

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_sql_file("003_ems_platform_gaps.sql")


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration; restore from backup instead.")
