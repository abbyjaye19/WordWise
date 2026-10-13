"""SQLite storage for accounts, folders, and saved readings.

The database file lives at data/wordwise.db (not committed to git). It is
created automatically the first time the app runs.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager

from config import DATA_DIR

DB_PATH = os.getenv("WORDWISE_DB", str(DATA_DIR / "wordwise.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS folders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id  INTEGER,
    name       TEXT NOT NULL,
    color      TEXT NOT NULL DEFAULT 'navy',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
-- Folder names are unique among siblings only (two classes can each have a "Notes" subfolder).
CREATE UNIQUE INDEX IF NOT EXISTS idx_folders_sibling_name ON folders(user_id, COALESCE(parent_id, 0), name COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS readings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    folder_id       INTEGER REFERENCES folders(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    kind            TEXT NOT NULL,
    doc_json        TEXT NOT NULL,
    highlights_json TEXT NOT NULL DEFAULT '{}',
    word_count      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_readings_user ON readings(user_id, folder_id);

-- Saved words (from the Word Coach) for review on My Dashboard.
CREATE TABLE IF NOT EXISTS saved_words (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word           TEXT NOT NULL,
    syllables      TEXT NOT NULL DEFAULT '',
    say_it         TEXT NOT NULL DEFAULT '',
    part_of_speech TEXT NOT NULL DEFAULT '',
    meaning        TEXT NOT NULL DEFAULT '',
    synonyms_json  TEXT NOT NULL DEFAULT '[]',
    example        TEXT NOT NULL DEFAULT '',
    sentence       TEXT NOT NULL DEFAULT '',
    source_title   TEXT NOT NULL DEFAULT '',
    known          INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_words_user_word ON saved_words(user_id, word COLLATE NOCASE);

-- Minutes spent actively reading in the Reading Studio, per local day.
CREATE TABLE IF NOT EXISTS reading_log (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day     TEXT NOT NULL,          -- YYYY-MM-DD in the student's own time zone
    seconds INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day)
);

-- Daily reading goal, plus the student's own goals checklist.
CREATE TABLE IF NOT EXISTS reading_goal (
    user_id       INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    daily_minutes INTEGER NOT NULL DEFAULT 15
);
CREATE TABLE IF NOT EXISTS personal_goals (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text       TEXT NOT NULL,
    due        TEXT,
    done       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate_folders(conn) -> None:
    """Older databases had flat folders with globally unique names; add parent_id and color."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(folders)")}
    if not cols or "parent_id" in cols:
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        """
        CREATE TABLE folders_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            parent_id INTEGER,
            name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT 'navy',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO folders_new (id, user_id, parent_id, name, color, created_at)
            SELECT id, user_id, NULL, name, 'navy', created_at FROM folders;
        DROP TABLE folders;
        ALTER TABLE folders_new RENAME TO folders;
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")


def init() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with connect() as conn:
        _migrate_folders(conn)
        conn.executescript(SCHEMA)


init()
