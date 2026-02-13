"""Idempotent database migrations for park-intel.

SQLite doesn't support full ALTER TABLE, but does support ADD COLUMN
for nullable columns. Each migration checks if the column exists first.
"""

import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _column_exists(engine: Engine, table: str, column: str) -> bool:
    """Check if a column exists in the given table."""
    with engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA table_info({table})"))
        columns = [row[1] for row in result]
        return column in columns


def run_migrations(engine: Engine) -> None:
    """Run all pending migrations idempotently."""
    migrations = [
        ("articles", "relevance_score", "INTEGER"),
        ("articles", "narrative_tags", "TEXT"),
    ]

    with engine.connect() as conn:
        for table, column, col_type in migrations:
            if not _column_exists(engine, table, column):
                logger.info("Adding column %s.%s (%s)", table, column, col_type)
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
            else:
                logger.debug("Column %s.%s already exists, skipping", table, column)
