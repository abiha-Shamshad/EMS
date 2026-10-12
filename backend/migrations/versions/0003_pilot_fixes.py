"""Outbox retry state and leakage run marker: db/004_ems_pilot_fixes.sql.

Revision ID: 0003
Revises: 0002
"""
from migrations.sqlfile import run_sql_file

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_sql_file("004_ems_pilot_fixes.sql")


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration; restore from backup instead.")
