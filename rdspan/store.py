"""Persistence helpers around the drill state machines."""

from __future__ import annotations

import sqlite3

from rdspan import config
from rdspan.db import utcnow
from rdspan.drills import ParadigmMachine


def ensure_scorecard(conn: sqlite3.Connection, user_id: int, paradigm_id: str) -> sqlite3.Row:
    conn.execute(
        """
        INSERT INTO scorecards (user_id, paradigm_id, reps, target)
        VALUES (?, ?, 0, ?)
        ON CONFLICT(user_id, paradigm_id) DO NOTHING
        """,
        (user_id, paradigm_id, config.scorecard_target()),
    )
    row = conn.execute(
        "SELECT * FROM scorecards WHERE user_id = ? AND paradigm_id = ?",
        (user_id, paradigm_id),
    ).fetchone()
    assert row is not None
    return row


def ensure_scriptorium_page(conn: sqlite3.Connection, user_id: int, page_id: str) -> sqlite3.Row:
    conn.execute(
        """
        INSERT INTO scriptorium_pages (user_id, page_id)
        VALUES (?, ?)
        ON CONFLICT(user_id, page_id) DO NOTHING
        """,
        (user_id, page_id),
    )
    row = conn.execute(
        "SELECT * FROM scriptorium_pages WHERE user_id = ? AND page_id = ?",
        (user_id, page_id),
    ).fetchone()
    assert row is not None
    return row


def get_or_create_paradigm_drill(
    conn: sqlite3.Connection, user_id: int, paradigm_id: str
) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT * FROM drills
        WHERE user_id = ? AND paradigm_id = ? AND drill_type = 'verb_table'
        """,
        (user_id, paradigm_id),
    ).fetchone()
    if row:
        return row
    now = utcnow()
    conn.execute(
        """
        INSERT INTO drills (
            user_id, drill_type, state, paradigm_id, created_at, updated_at
        ) VALUES (?, 'verb_table', 'idle', ?, ?, ?)
        """,
        (user_id, paradigm_id, now, now),
    )
    return get_or_create_paradigm_drill(conn, user_id, paradigm_id)


def get_or_create_scriptorium_drill(
    conn: sqlite3.Connection, user_id: int, page_id: str
) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT * FROM drills
        WHERE user_id = ? AND page_id = ? AND drill_type = 'phrase_transcription'
        """,
        (user_id, page_id),
    ).fetchone()
    if row:
        return row
    now = utcnow()
    conn.execute(
        """
        INSERT INTO drills (
            user_id, drill_type, state, page_id, created_at, updated_at
        ) VALUES (?, 'phrase_transcription', 'idle', ?, ?, ?)
        """,
        (user_id, page_id, now, now),
    )
    return get_or_create_scriptorium_drill(conn, user_id, page_id)


def _set_drill_state(conn: sqlite3.Connection, drill_id: int, state: str) -> None:
    conn.execute(
        "UPDATE drills SET state = ?, updated_at = ? WHERE id = ?",
        (state, utcnow(), drill_id),
    )


def record_attempt(
    conn: sqlite3.Connection,
    user_id: int,
    drill_id: int,
    mode: str,
    passed: bool | None,
    response: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO attempts (user_id, drill_id, mode, passed, response, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            drill_id,
            mode,
            None if passed is None else int(passed),
            response,
            utcnow(),
        ),
    )


def paradigm_machine(scorecard: sqlite3.Row, drill: sqlite3.Row) -> ParadigmMachine:
    return ParadigmMachine(drill["state"], scorecard["reps"], scorecard["target"])


def apply_paradigm_machine(
    conn: sqlite3.Connection,
    user_id: int,
    paradigm_id: str,
    drill: sqlite3.Row,
    machine: ParadigmMachine,
    *,
    mastered_now: bool = False,
) -> None:
    _set_drill_state(conn, drill["id"], machine.state)
    if machine.state == "mastered" or mastered_now:
        conn.execute(
            """
            UPDATE scorecards
            SET reps = ?, mastered_at = COALESCE(mastered_at, ?)
            WHERE user_id = ? AND paradigm_id = ?
            """,
            (machine.reps, utcnow(), user_id, paradigm_id),
        )
    else:
        conn.execute(
            """
            UPDATE scorecards SET reps = ? WHERE user_id = ? AND paradigm_id = ?
            """,
            (machine.reps, user_id, paradigm_id),
        )


def load_cells(conn: sqlite3.Connection, paradigm_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT slot, pronoun, form, tts_text
        FROM paradigm_cells
        WHERE paradigm_id = ?
        ORDER BY id
        """,
        (paradigm_id,),
    ).fetchall()


def ack_paradigm_repeat(
    conn: sqlite3.Connection, user_id: int, paradigm_id: str
) -> ParadigmMachine:
    drill = get_or_create_paradigm_drill(conn, user_id, paradigm_id)
    scorecard = ensure_scorecard(conn, user_id, paradigm_id)
    nxt = paradigm_machine(scorecard, drill).ack_repeat()
    record_attempt(conn, user_id, drill["id"], "say", True, None)
    apply_paradigm_machine(
        conn,
        user_id,
        paradigm_id,
        drill,
        nxt,
        mastered_now=nxt.state == "mastered" and scorecard["mastered_at"] is None,
    )
    return nxt


def next_paradigm(conn: sqlite3.Connection, paradigm_id: str) -> sqlite3.Row:
    rows = conn.execute(
        "SELECT * FROM paradigms ORDER BY sort_order, lemma, id"
    ).fetchall()
    if not rows:
        raise ValueError("no paradigms seeded")
    ids = [row["id"] for row in rows]
    try:
        idx = ids.index(paradigm_id)
    except ValueError:
        return rows[0]
    return rows[(idx + 1) % len(rows)]


def home_paradigms(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            p.id, p.lemma, p.ending, p.regularity, p.tense, p.mood,
            COALESCE(sc.reps, 0) AS reps,
            COALESCE(sc.target, ?) AS target,
            sc.mastered_at,
            d.state AS drill_state
        FROM paradigms p
        LEFT JOIN scorecards sc
            ON sc.paradigm_id = p.id AND sc.user_id = ?
        LEFT JOIN drills d
            ON d.paradigm_id = p.id AND d.user_id = ? AND d.drill_type = 'verb_table'
        ORDER BY p.sort_order, p.lemma
        """,
        (config.scorecard_target(), user_id, user_id),
    ).fetchall()


def home_phrases(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            ph.id, ph.title, ph.text,
            COALESCE(sp.listen_ok, 0) AS listen_ok,
            COALESCE(sp.say_ok, 0) AS say_ok,
            COALESCE(sp.write_ok, 0) AS write_ok,
            d.state AS drill_state
        FROM phrases ph
        LEFT JOIN scriptorium_pages sp
            ON sp.page_id = ph.id AND sp.user_id = ?
        LEFT JOIN drills d
            ON d.page_id = ph.id AND d.user_id = ? AND d.drill_type = 'phrase_transcription'
        ORDER BY ph.sort_order
        """,
        (user_id, user_id),
    ).fetchall()


def progress_summary(conn: sqlite3.Connection, user_id: int) -> dict:
    para = home_paradigms(conn, user_id)
    phrases = home_phrases(conn, user_id)
    mastered = sum(1 for p in para if p["mastered_at"])
    page_done = sum(
        1 for p in phrases if p["listen_ok"] and p["say_ok"] and p["write_ok"]
    )
    reps = sum(p["reps"] for p in para)
    return {
        "paradigms": len(para),
        "mastered": mastered,
        "reps": reps,
        "pages": len(phrases),
        "pages_done": page_done,
    }
