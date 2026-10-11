"""Alembic environment. Runs as an admin role (ADMIN_DATABASE_URL); revisions execute the canonical SQL files."""
import os

from alembic import context
from sqlalchemy import create_engine, pool

url = os.environ.get("ADMIN_DATABASE_URL")
if not url:
    raise SystemExit("ADMIN_DATABASE_URL is required to run migrations (an admin role, never ems_app).")


def run_migrations_online() -> None:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        # The SQL files change search_path; keep Alembic's own table in public explicitly.
        context.configure(connection=connection, version_table_schema="public", transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("Offline mode is not supported: the canonical SQL files are applied as-is.")
run_migrations_online()
