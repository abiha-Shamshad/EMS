"""Prospect promotion link and indexes for the Lead Hunter, rule runs and leakage findings: db/005_ems_automation.sql.

Revision ID: 0004
Revises: 0003
"""
from migrations.sqlfile import run_sql_file

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_sql_file("005_ems_automation.sql")


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration; restore from backup instead.")
