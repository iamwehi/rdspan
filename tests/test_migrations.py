from rdspan.db import connect, migrate


def test_migrations_are_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "db.sqlite"))
    conn = connect()
    migrate(conn)
    migrate(conn)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    for required in (
        "users",
        "drills",
        "attempts",
        "scorecards",
        "scriptorium_pages",
        "paradigms",
        "paradigm_cells",
        "phrases",
        "schema_migrations",
    ):
        assert required in tables
    indexes = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name IS NOT NULL"
        ).fetchall()
    }
    assert "idx_scorecards_user_progress" in indexes
    conn.close()
