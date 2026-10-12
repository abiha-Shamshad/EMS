"""Webcam opt-in and camera state: db/006_ems_webcam.sql.

Revision ID: 0005
Revises: 0004
"""
from migrations.sqlfile import run_sql_file

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_sql_file("006_ems_webcam.sql")


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration; restore from backup instead.")
