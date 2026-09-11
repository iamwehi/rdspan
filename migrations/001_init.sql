CREATE TABLE IF NOT EXISTS schema_migrations (
    id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paradigms (
    id TEXT PRIMARY KEY,
    lemma TEXT NOT NULL,
    ending TEXT,
    regularity TEXT NOT NULL,
    tense TEXT NOT NULL,
    mood TEXT NOT NULL,
    source TEXT NOT NULL,
    license TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS paradigm_cells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paradigm_id TEXT NOT NULL REFERENCES paradigms(id),
    slot TEXT NOT NULL,
    pronoun TEXT NOT NULL,
    form TEXT NOT NULL,
    tts_text TEXT NOT NULL,
    UNIQUE (paradigm_id, slot)
);

CREATE TABLE IF NOT EXISTS phrases (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    tts_text TEXT NOT NULL,
    source TEXT NOT NULL,
    license TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS drills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    drill_type TEXT NOT NULL CHECK (drill_type IN ('verb_table', 'phrase_transcription')),
    state TEXT NOT NULL,
    paradigm_id TEXT REFERENCES paradigms(id),
    page_id TEXT REFERENCES phrases(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    drill_id INTEGER NOT NULL REFERENCES drills(id),
    mode TEXT NOT NULL CHECK (mode IN ('listen', 'say', 'write')),
    passed INTEGER,
    response TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scorecards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    paradigm_id TEXT NOT NULL REFERENCES paradigms(id),
    reps INTEGER NOT NULL DEFAULT 0,
    target INTEGER NOT NULL DEFAULT 100,
    mastered_at TEXT,
    UNIQUE (user_id, paradigm_id)
);

CREATE TABLE IF NOT EXISTS scriptorium_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    page_id TEXT NOT NULL REFERENCES phrases(id),
    listen_ok INTEGER NOT NULL DEFAULT 0,
    say_ok INTEGER NOT NULL DEFAULT 0,
    write_ok INTEGER NOT NULL DEFAULT 0,
    UNIQUE (user_id, page_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_drills_user_paradigm
    ON drills(user_id, paradigm_id)
    WHERE paradigm_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_drills_user_page
    ON drills(user_id, page_id)
    WHERE page_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_attempts_user_ts
    ON attempts(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_attempts_drill
    ON attempts(drill_id, created_at);

CREATE INDEX IF NOT EXISTS idx_scorecards_user_progress
    ON scorecards(user_id, paradigm_id, reps);

CREATE INDEX IF NOT EXISTS idx_scorecards_mastered
    ON scorecards(user_id, mastered_at);

CREATE INDEX IF NOT EXISTS idx_scriptorium_user_page
    ON scriptorium_pages(user_id, page_id);

CREATE INDEX IF NOT EXISTS idx_scriptorium_complete
    ON scriptorium_pages(user_id, listen_ok, say_ok, write_ok);

CREATE INDEX IF NOT EXISTS idx_drills_user_type_state
    ON drills(user_id, drill_type, state);

CREATE INDEX IF NOT EXISTS idx_paradigm_cells_paradigm
    ON paradigm_cells(paradigm_id);

CREATE INDEX IF NOT EXISTS idx_paradigms_sort
    ON paradigms(sort_order, lemma);

CREATE INDEX IF NOT EXISTS idx_phrases_sort
    ON phrases(sort_order);
