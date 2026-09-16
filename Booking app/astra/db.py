"""SQLite connections and the initial, additive schema migration."""
import sqlite3
from pathlib import Path

from flask import current_app, g


def connect(path):
    db = sqlite3.connect(path, timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    db.execute('PRAGMA busy_timeout = 15000')
    return db


def init_database(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = connect(path)
    try:
        db.execute('PRAGMA journal_mode = WAL')
        db.executescript(Path(__file__).with_name('schema.sql').read_text())
    finally:
        db.close()


def get_db():
    if 'db' not in g:
        g.db = connect(current_app.config['DATABASE'])
    return g.db


def close_db(_error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
