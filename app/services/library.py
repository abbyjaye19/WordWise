"""A user's library: folders and saved readings (with their highlights).

Every function takes the user id and every query is scoped to it, so one
user can never see or change another user's readings.
"""

from __future__ import annotations

import json
import sqlite3

from services.db import connect

MAX_READINGS = 300
MAX_FOLDERS = 60
MAX_DEPTH = 3  # e.g. School › Science › Lab notes

# Folder colors: palette-friendly, each readable as a dot or a left border.
COLORS = {
    "navy": ("Navy", "#1B3366"),
    "sky": ("Sky", "#5B7FBF"),
    "green": ("Green", "#4F7A5A"),
    "gold": ("Gold", "#B08D57"),
    "red": ("Red", "#A2463A"),
    "purple": ("Purple", "#6B4E8A"),
    "gray": ("Gray", "#6F7787"),
}


class LibraryError(ValueError):
    """A friendly, user-facing library problem."""


# ---------- folders ----------

def folders(user_id: int) -> list[dict]:
    """All folders as a tree in display order. Each has depth, path ("School › Science"), and n (readings directly inside)."""
    with connect() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT f.id, f.parent_id, f.name, f.color, COUNT(r.id) AS n FROM folders f "
                "LEFT JOIN readings r ON r.folder_id = f.id "
                "WHERE f.user_id = ? GROUP BY f.id ORDER BY f.name COLLATE NOCASE",
                (user_id,),
            ).fetchall()
        ]
    ids = {r["id"] for r in rows}
    children: dict = {}
    for r in rows:
        parent = r["parent_id"] if r["parent_id"] in ids else None  # orphans show at top level
        children.setdefault(parent, []).append(r)
    out: list[dict] = []

    def walk(parent, depth, path):
        for r in children.get(parent, []):
            item = {**r, "parent_id": parent, "depth": depth, "path": " › ".join(path + [r["name"]])}
            item["has_children"] = bool(children.get(r["id"]))
            out.append(item)
            walk(r["id"], depth + 1, path + [r["name"]])

    walk(None, 0, [])
    return out


def create_folder(user_id: int, name: str, color: str = "navy", parent_id: int | None = None) -> int:
    name = " ".join((name or "").split())[:60]
    if not name:
        raise LibraryError("Give your folder a name first.")
    color = color if color in COLORS else "navy"
    tree = folders(user_id)
    if len(tree) >= MAX_FOLDERS:
        raise LibraryError(f"You can have up to {MAX_FOLDERS} folders.")
    if parent_id is not None:
        parent = next((f for f in tree if f["id"] == parent_id), None)
        if not parent:
            raise LibraryError("We couldn't find that folder. Please pick another one.")
        if parent["depth"] + 1 >= MAX_DEPTH:
            raise LibraryError(f"Folders can go {MAX_DEPTH} levels deep. Pick a higher folder to put this in.")
    with connect() as conn:
        try:
            return conn.execute(
                "INSERT INTO folders (user_id, parent_id, name, color) VALUES (?, ?, ?, ?)",
                (user_id, parent_id, name, color),
            ).lastrowid
        except sqlite3.IntegrityError as exc:
            raise LibraryError(f"There's already a folder called “{name}” there.") from exc


def set_folder_color(user_id: int, folder_id: int, color: str) -> None:
    if color not in COLORS:
        raise LibraryError("Please pick one of the colors shown.")
    with connect() as conn:
        conn.execute("UPDATE folders SET color = ? WHERE id = ? AND user_id = ?", (color, folder_id, user_id))


def delete_folder(user_id: int, folder_id: int) -> None:
    """Nothing inside is lost: readings and subfolders move up one level."""
    with connect() as conn:
        row = conn.execute("SELECT parent_id FROM folders WHERE id = ? AND user_id = ?", (folder_id, user_id)).fetchone()
        if not row:
            return
        parent = row["parent_id"]
        conn.execute("UPDATE readings SET folder_id = ? WHERE user_id = ? AND folder_id = ?", (parent, user_id, folder_id))
        # Move subfolders up; rename on a name clash with an existing sibling.
        for child in conn.execute(
            "SELECT id, name FROM folders WHERE user_id = ? AND parent_id = ?", (user_id, folder_id)
        ).fetchall():
            name, n = child["name"], 2
            while conn.execute(
                "SELECT 1 FROM folders WHERE user_id = ? AND COALESCE(parent_id, 0) = COALESCE(?, 0) AND name = ? COLLATE NOCASE",
                (user_id, parent, name),
            ).fetchone():
                name, n = f"{child['name']} ({n})", n + 1
            conn.execute("UPDATE folders SET parent_id = ?, name = ? WHERE id = ?", (parent, name, child["id"]))
        conn.execute("DELETE FROM folders WHERE user_id = ? AND id = ?", (user_id, folder_id))


def _own_folder(conn, user_id: int, folder_id: int | None) -> int | None:
    if folder_id is None:
        return None
    row = conn.execute("SELECT id FROM folders WHERE id = ? AND user_id = ?", (folder_id, user_id)).fetchone()
    return row["id"] if row else None


# ---------- readings ----------

def readings(user_id: int, folder: str = "all") -> list[dict]:
    """folder: 'all', 'none' (not in a folder), or a folder id as text."""
    sql = (
        "SELECT r.id, r.title, r.kind, r.word_count, r.folder_id, r.updated_at, f.name AS folder_name, f.color AS folder_color "
        "FROM readings r LEFT JOIN folders f ON f.id = r.folder_id WHERE r.user_id = ?"
    )
    args: list = [user_id]
    if folder == "none":
        sql += " AND r.folder_id IS NULL"
    elif folder not in (None, "all"):
        sql += " AND r.folder_id = ?"
        args.append(int(folder))
    sql += " ORDER BY r.updated_at DESC"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def save_reading(user_id: int, doc: dict, highlights: dict, folder_id: int | None, reading_id: int | None = None) -> int:
    """Create a new saved reading, or update one the user already owns."""
    clean_doc = {k: doc[k] for k in ("title", "kind", "sections", "note") if k in doc}
    words = sum(len(p.split()) for s in doc.get("sections", []) for p in s.get("paragraphs", []))
    hl = json.dumps({str(k): v for k, v in (highlights or {}).items() if v in ("gold", "green", "blue")})
    with connect() as conn:
        folder_id = _own_folder(conn, user_id, folder_id)
        if reading_id:
            cur = conn.execute(
                "UPDATE readings SET title = ?, doc_json = ?, highlights_json = ?, folder_id = ?, word_count = ?, "
                "updated_at = datetime('now') WHERE id = ? AND user_id = ?",
                (clean_doc.get("title", "Untitled"), json.dumps(clean_doc), hl, folder_id, words, reading_id, user_id),
            )
            if cur.rowcount:
                return reading_id
        (count,) = conn.execute("SELECT COUNT(*) FROM readings WHERE user_id = ?", (user_id,)).fetchone()
        if count >= MAX_READINGS:
            raise LibraryError(f"Your library is full ({MAX_READINGS} readings). Delete some to make room.")
        return conn.execute(
            "INSERT INTO readings (user_id, folder_id, title, kind, doc_json, highlights_json, word_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, folder_id, clean_doc.get("title", "Untitled"), clean_doc.get("kind", "text"), json.dumps(clean_doc), hl, words),
        ).lastrowid


def open_reading(user_id: int, reading_id: int) -> dict | None:
    """The saved reading as a studio document (with highlights and its id), or None."""
    with connect() as conn:
        row = conn.execute(
            "SELECT id, folder_id, doc_json, highlights_json FROM readings WHERE id = ? AND user_id = ?",
            (reading_id, user_id),
        ).fetchone()
    if not row:
        return None
    doc = json.loads(row["doc_json"])
    doc["highlights"] = json.loads(row["highlights_json"])
    doc["saved_id"] = row["id"]
    doc["folder_id"] = row["folder_id"]
    return doc


def move_reading(user_id: int, reading_id: int, folder_id: int | None) -> None:
    with connect() as conn:
        folder_id = _own_folder(conn, user_id, folder_id)
        conn.execute(
            "UPDATE readings SET folder_id = ? WHERE id = ? AND user_id = ?",
            (folder_id, reading_id, user_id),
        )


def delete_reading(user_id: int, reading_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM readings WHERE id = ? AND user_id = ?", (reading_id, user_id))
