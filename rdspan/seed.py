from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from rdspan import config
from rdspan.db import utcnow

REQUIRED_PARADIGM = ("id", "lemma", "tense", "mood", "source", "license", "verified_at", "cells")
REQUIRED_CELL = ("slot", "pronoun", "form")
REQUIRED_PHRASE = ("id", "title", "text", "source", "license", "verified_at")
SLOTS = ("1s", "2s", "3s", "1p", "2p", "3p")


class SeedError(ValueError):
    pass


def _require(obj: dict, keys: tuple[str, ...], label: str) -> None:
    missing = [k for k in keys if k not in obj or obj[k] in (None, "")]
    if missing:
        raise SeedError(f"{label} missing {', '.join(missing)}")


def load_paradigms(path: Path | None = None) -> list[dict]:
    data_path = path or (config.data_dir() / "paradigms.json")
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SeedError("paradigms.json must be a list")
    for item in raw:
        _require(item, REQUIRED_PARADIGM, f"paradigm {item.get('id', '?')}")
        cells = item["cells"]
        if not isinstance(cells, list) or len(cells) != 6:
            raise SeedError(f"{item['id']} must have exactly 6 curated cells")
        slots = [c.get("slot") for c in cells]
        if tuple(slots) != SLOTS:
            raise SeedError(f"{item['id']} cells must be ordered {SLOTS}")
        for cell in cells:
            _require(cell, REQUIRED_CELL, f"{item['id']} cell")
        if item.get("regularity") not in ("regular", "irregular"):
            raise SeedError(f"{item['id']} regularity must be regular|irregular")
    return raw


def load_phrases(path: Path | None = None) -> list[dict]:
    data_path = path or (config.data_dir() / "phrases.json")
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SeedError("phrases.json must be a list")
    for item in raw:
        _require(item, REQUIRED_PHRASE, f"phrase {item.get('id', '?')}")
    return raw


def seed(conn: sqlite3.Connection) -> dict[str, int]:
    """Load curated JSON into SQLite. Never synthesizes verb forms."""
    paradigms = load_paradigms()
    phrases = load_phrases()
    for p in paradigms:
        conn.execute(
            """
            INSERT INTO paradigms (
                id, lemma, ending, regularity, tense, mood,
                source, license, verified_at, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                lemma=excluded.lemma,
                ending=excluded.ending,
                regularity=excluded.regularity,
                tense=excluded.tense,
                mood=excluded.mood,
                source=excluded.source,
                license=excluded.license,
                verified_at=excluded.verified_at,
                sort_order=excluded.sort_order
            """,
            (
                p["id"],
                p["lemma"],
                p.get("ending"),
                p["regularity"],
                p["tense"],
                p["mood"],
                p["source"],
                p["license"],
                p["verified_at"],
                int(p.get("sort_order", 0)),
            ),
        )
        conn.execute("DELETE FROM paradigm_cells WHERE paradigm_id = ?", (p["id"],))
        for cell in p["cells"]:
            tts_text = cell.get("tts_text") or f"{cell['pronoun']} {cell['form']}"
            conn.execute(
                """
                INSERT INTO paradigm_cells (
                    paradigm_id, slot, pronoun, form, tts_text
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (p["id"], cell["slot"], cell["pronoun"], cell["form"], tts_text),
            )
    for ph in phrases:
        tts_text = ph.get("tts_text") or ph["text"]
        conn.execute(
            """
            INSERT INTO phrases (
                id, title, text, tts_text, source, license, verified_at, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                text=excluded.text,
                tts_text=excluded.tts_text,
                source=excluded.source,
                license=excluded.license,
                verified_at=excluded.verified_at,
                sort_order=excluded.sort_order
            """,
            (
                ph["id"],
                ph["title"],
                ph["text"],
                tts_text,
                ph["source"],
                ph["license"],
                ph["verified_at"],
                int(ph.get("sort_order", 0)),
            ),
        )
    conn.commit()
    return {"paradigms": len(paradigms), "phrases": len(phrases), "seeded_at": utcnow()}
