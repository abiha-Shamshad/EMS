"""Execute a canonical SQL file verbatim (TASK-002: no table definitions are retyped in Python)."""
from pathlib import Path

from alembic import op

DB_DIR = Path(__file__).resolve().parents[2] / "db"


def run_sql_file(name: str) -> None:
    sql = (DB_DIR / name).read_text(encoding="utf-8")
    # Use the driver connection directly: no parameters are passed, so psycopg does not interpret '%' or ':'
    # placeholders, and multi-statement scripts (DO blocks, SET ROLE) run unchanged inside Alembic's transaction.
    driver_conn = op.get_bind().connection.driver_connection
    with driver_conn.cursor() as cur:
        cur.execute(sql)
