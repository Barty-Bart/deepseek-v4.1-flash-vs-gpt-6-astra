"""SQLite connection handling, schema bootstrap and transactional helpers."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(
        path,
        timeout=15.0,
        isolation_level=None,          # explicit transaction control
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())
    conn.execute("INSERT INTO schema_version (version) SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_version)")


def get_db() -> sqlite3.Connection:
    """Request-scoped connection (autocommit; use `write_txn` for mutations)."""
    if "db" not in g:
        path = current_app.config["DATABASE_PATH"]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        g.db = _connect(Path(path))
    return g.db


def close_db(_exc=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@contextmanager
def write_txn(conn: sqlite3.Connection):
    """Serialise writers with BEGIN IMMEDIATE so overlap checks cannot race."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    else:
        # `executescript` (schema rebuilds) commits on its own; tolerate that.
        if conn.in_transaction:
            conn.execute("COMMIT")


def open_standalone(path: Path) -> sqlite3.Connection:
    """A connection outside a request context (CLI commands, tests)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return _connect(Path(path))


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
