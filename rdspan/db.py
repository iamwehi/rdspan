from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from rdspan import config

SLOTS = ("1s", "2s", "3s", "1p", "2p", "3p")


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or config.database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied = {
        row["id"]
        for row in conn.execute("SELECT id FROM schema_migrations").fetchall()
    }
    for sql_path in sorted(config.migrations_dir().glob("*.sql")):
        mid = sql_path.name
        if mid in applied:
            continue
        conn.executescript(sql_path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations (id, applied_at) VALUES (?, ?)",
            (mid, utcnow()),
        )
        conn.commit()


def get_or_create_user(conn: sqlite3.Connection, username: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row:
        return row
    conn.execute(
        "INSERT INTO users (username, created_at) VALUES (?, ?)",
        (username, utcnow()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    assert row is not None
    return row


def iter_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        migrate(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()
