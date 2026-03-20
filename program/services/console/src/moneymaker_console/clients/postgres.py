# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Lazy PostgreSQL client for direct TimescaleDB queries.

Uses the ADMIN_DB_PASSWORD for full read access across all tables.
"""

from __future__ import annotations

import os
import re
from typing import Any

from moneymaker_console.console_logging import log_event


def _sanitize_sql_for_log(sql: str, max_len: int = 60) -> str:
    """Return a truncated, scrubbed summary of *sql* safe for logging.

    Strips quoted string literals and trims to *max_len* characters so
    that sensitive data embedded in queries never reaches the log files.
    """
    # Replace single-quoted string literals with placeholder
    scrubbed = re.sub(r"'[^']*'", "'?'", sql)
    if len(scrubbed) > max_len:
        scrubbed = scrubbed[:max_len] + "..."
    return scrubbed


class PostgresClient:
    """Lazy PostgreSQL connection with retry logic."""

    def __init__(self) -> None:
        self._conn = None
        self._available = True

    def _connect(self):
        if not self._available:
            return None
        if self._conn is not None:
            return self._conn
        try:
            import psycopg2

            db_host = os.environ.get("MONEYMAKER_DB_HOST", "localhost")
            db_port = os.environ.get("MONEYMAKER_DB_PORT", "5432")
            db_name = os.environ.get("MONEYMAKER_DB_NAME", "moneymaker_brain")
            db_user = os.environ.get("MONEYMAKER_DB_USER", "moneymaker")
            db_pass = os.environ.get(
                "ADMIN_DB_PASSWORD",
                os.environ.get("MONEYMAKER_DB_PASSWORD", "moneymaker"),
            )

            # Build DSN — also check BRAIN_DATABASE_URL as fallback
            db_url = os.environ.get("BRAIN_DATABASE_URL", "")
            if db_url:
                # Strip SQLAlchemy driver prefixes
                db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
                db_url = db_url.replace("postgresql+aiopg://", "postgresql://")
                self._conn = psycopg2.connect(db_url)
            else:
                self._conn = psycopg2.connect(
                    host=db_host,
                    port=int(db_port),
                    dbname=db_name,
                    user=db_user,
                    password=db_pass,
                    connect_timeout=5,
                )

            self._conn.autocommit = True
            log_event("postgres_connected", host=db_host, port=db_port)
            return self._conn
        except ImportError:
            self._available = False
            log_event("postgres_unavailable", reason="psycopg2 not installed")
            return None
        except Exception as exc:
            log_event("postgres_connect_error", error=str(exc))
            self._conn = None
            return None

    def ping(self) -> bool:
        """Check if the database is reachable."""
        conn = self._connect()
        if conn is None:
            return False
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return True
        except Exception as exc:
            log_event("postgres_ping_error", error=str(exc))
            self._conn = None
            return False

    def query(self, sql: str, params: tuple = ()) -> list[tuple[Any, ...]]:
        """Execute a SELECT query and return rows."""
        conn = self._connect()
        if conn is None:
            return []
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            return rows
        except Exception as exc:
            log_event("postgres_query_error", error=str(exc), sql=_sanitize_sql_for_log(sql))
            # Connection may be broken — reset
            self._conn = None
            return []

    def query_one(self, sql: str, params: tuple = ()) -> tuple[Any, ...] | None:
        """Execute a SELECT query and return the first row."""
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def query_dict(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute a SELECT and return rows as dicts (requires column names)."""
        conn = self._connect()
        if conn is None:
            return []
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
            cur.close()
            return rows
        except Exception as exc:
            log_event("postgres_query_error", error=str(exc), sql=_sanitize_sql_for_log(sql))
            self._conn = None
            return []

    def execute(self, sql: str, params: tuple = ()) -> bool:
        """Execute a non-SELECT statement (INSERT, UPDATE, etc.)."""
        conn = self._connect()
        if conn is None:
            return False
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            cur.close()
            return True
        except Exception as exc:
            log_event("postgres_execute_error", error=str(exc), sql=_sanitize_sql_for_log(sql))
            self._conn = None
            return False

    @property
    def is_available(self) -> bool:
        return self._available
