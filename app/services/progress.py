"""Saved words, reading time, and reading goals for signed-in students.

Every function takes the user id and every query is scoped to it.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

from services.db import connect

MAX_WORDS = 1_000
MAX_GOALS = 50
MAX_BEAT_SECONDS = 120  # one browser report can add at most this much time
GOAL_CHOICES = [5, 10, 15, 20, 30, 45, 60]
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ProgressError(ValueError):
    """A friendly, user-facing problem."""


# ---------- saved words ----------

def save_word(user_id: int, info: dict) -> bool:
    """Save (or refresh) a looked-up word. Returns True if it was new."""
    word = " ".join(str(info.get("word", "")).split())[:60]
    if not word:
        raise ProgressError("There's no word to save.")
    fields = {
        "syllables": str(info.get("syllables", ""))[:120],
        "say_it": str(info.get("say_it", ""))[:120],
        "part_of_speech": str(info.get("part_of_speech", ""))[:40],
        "meaning": str(info.get("meaning", ""))[:600],
        "synonyms_json": json.dumps([str(s)[:40] for s in (info.get("synonyms") or [])][:6]),
        "example": str(info.get("example", ""))[:400],
        "sentence": str(info.get("sentence", ""))[:600],
        "source_title": str(info.get("source_title", ""))[:120],
    }
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM saved_words WHERE user_id = ? AND word = ? COLLATE NOCASE", (user_id, word)
        ).fetchone()
        if existing:
            sets = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(f"UPDATE saved_words SET {sets} WHERE id = ?", (*fields.values(), existing["id"]))
            return False
        (count,) = conn.execute("SELECT COUNT(*) FROM saved_words WHERE user_id = ?", (user_id,)).fetchone()
        if count >= MAX_WORDS:
            raise ProgressError(f"Your word bank is full ({MAX_WORDS} words). Remove some you know well.")
        cols = ", ".join(fields)
        conn.execute(
            f"INSERT INTO saved_words (user_id, word, {cols}) VALUES (?, ?, {', '.join('?' * len(fields))})",
            (user_id, word, *fields.values()),
        )
        return True


def words(user_id: int, show: str = "all", search: str = "") -> list[dict]:
    sql = "SELECT * FROM saved_words WHERE user_id = ?"
    args: list = [user_id]
    if show == "learning":
        sql += " AND known = 0"
    elif show == "known":
        sql += " AND known = 1"
    if search.strip():
        sql += " AND (word LIKE ? OR meaning LIKE ?)"
        like = f"%{search.strip()[:40]}%"
        args += [like, like]
    sql += " ORDER BY created_at DESC, id DESC"
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(sql, args).fetchall()]
    for r in rows:
        r["synonyms"] = json.loads(r.pop("synonyms_json") or "[]")
    return rows


def word_counts(user_id: int) -> dict:
    with connect() as conn:
        total, known = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(known), 0) FROM saved_words WHERE user_id = ?", (user_id,)
        ).fetchone()
        week = conn.execute(
            "SELECT COUNT(*) FROM saved_words WHERE user_id = ? AND created_at >= datetime('now', '-7 days')", (user_id,)
        ).fetchone()[0]
    return {"total": total, "known": known, "learning": total - known, "this_week": week}


def set_known(user_id: int, word_id: int, known: bool) -> None:
    with connect() as conn:
        conn.execute("UPDATE saved_words SET known = ? WHERE id = ? AND user_id = ?", (int(known), word_id, user_id))


def delete_word(user_id: int, word_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM saved_words WHERE id = ? AND user_id = ?", (word_id, user_id))


# ---------- reading time ----------

def log_reading(user_id: int, day: str, seconds: int, title: str = "") -> None:
    """Add active reading time reported by the browser (capped, and only for today or yesterday)."""
    if not DAY_RE.match(day or ""):
        return
    seconds = max(0, min(int(seconds or 0), MAX_BEAT_SECONDS))
    reported = date.fromisoformat(day)
    if abs((reported - date.today()).days) > 1 or not seconds:
        return
    title = (" ".join(str(title or "").split()) or "Untitled reading")[:120]
    with connect() as conn:
        conn.execute(
            "INSERT INTO reading_log (user_id, day, seconds) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, day) DO UPDATE SET seconds = seconds + excluded.seconds",
            (user_id, day, seconds),
        )
        conn.execute(
            "INSERT INTO reading_sessions (user_id, day, title, seconds) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, day, title) DO UPDATE SET seconds = seconds + excluded.seconds",
            (user_id, day, title, seconds),
        )


def session_summary(user_id: int, days: int = 30) -> dict:
    """Reading sessions (one per reading per day) in the last `days` days."""
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    with connect() as conn:
        n, seconds, titles = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(seconds), 0), COUNT(DISTINCT title) FROM reading_sessions WHERE user_id = ? AND day >= ?",
            (user_id, since),
        ).fetchone()
    return {"sessions": n, "minutes": round(seconds / 60), "readings": titles}


def recent_sessions(user_id: int, limit: int = 8) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT day, title, seconds FROM reading_sessions WHERE user_id = ? ORDER BY day DESC, seconds DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"day": r["day"], "title": r["title"], "minutes": max(1, round(r["seconds"] / 60))} for r in rows]


# ---------- tool usage ----------

TOOLS = {  # event key -> label shown on the dashboard
    "read_aloud": "Read aloud", "replay": "Replay sentence", "highlighter": "Highlighter", "ruler": "Reading ruler",
    "focus": "One-paragraph focus", "settings": "Reading settings", "word_help": "Word Coach", "explain": "Explainer",
    "summary": "Sum it up", "simplified_view": "Simplified view", "detailed_view": "Detailed view",
    "tutor": "AI Tutor", "save_word": "Save word", "check_in": "Comprehension check-in",
}


def log_tool(user_id: int, tool: str, count: int = 1) -> None:
    if tool not in TOOLS:
        return
    with connect() as conn:
        conn.execute(
            "INSERT INTO tool_events (user_id, day, tool, count) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, day, tool) DO UPDATE SET count = count + excluded.count",
            (user_id, date.today().isoformat(), tool, max(1, min(int(count), 50))),
        )


def tool_counts(user_id: int, days: int = 30) -> list[dict]:
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    with connect() as conn:
        rows = conn.execute(
            "SELECT tool, SUM(count) AS n FROM tool_events WHERE user_id = ? AND day >= ? GROUP BY tool ORDER BY n DESC",
            (user_id, since),
        ).fetchall()
    return [{"tool": r["tool"], "label": TOOLS.get(r["tool"], r["tool"]), "count": r["n"]} for r in rows]


# ---------- comprehension check-ins ----------

HARD_REASONS = {
    "words": "Hard words", "long_sentences": "Long sentences", "main_idea": "Finding the main idea",
    "remembering": "Remembering it", "listening": "Following the read-aloud", "focus": "Staying focused",
}
RATING_LABELS = {1: "Not at all", 2: "A little", 3: "Mostly", 4: "Well", 5: "Very well"}


def add_check(user_id: int, title: str, rating: int, hard: list[str]) -> None:
    if int(rating) not in RATING_LABELS:
        raise ProgressError("Please pick how well you understood it.")
    hard = [h for h in (hard or []) if h in HARD_REASONS]
    with connect() as conn:
        conn.execute(
            "INSERT INTO comprehension_checks (user_id, day, title, rating, hard_json) VALUES (?, ?, ?, ?, ?)",
            (user_id, date.today().isoformat(), (title or "Untitled reading")[:120], int(rating), json.dumps(hard)),
        )


def checks(user_id: int, limit: int = 10) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT day, title, rating, hard_json FROM comprehension_checks WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"day": r["day"], "title": r["title"], "rating": r["rating"], "hard": json.loads(r["hard_json"])} for r in rows]


def recent_comprehension(user_id: int, n: int = 5) -> float | None:
    rs = [c["rating"] for c in checks(user_id, n)]
    return sum(rs) / len(rs) if rs else None


def hard_reason_counts(user_id: int, limit: int = 30) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for c in checks(user_id, limit):
        for h in c["hard"]:
            counts[h] = counts.get(h, 0) + 1
    return sorted(((HARD_REASONS[k], v) for k, v in counts.items()), key=lambda kv: -kv[1])


def minutes_by_day(user_id: int, end: date, days: int = 7) -> list[dict]:
    start = end - timedelta(days=days - 1)
    with connect() as conn:
        rows = dict(
            conn.execute(
                "SELECT day, seconds FROM reading_log WHERE user_id = ? AND day BETWEEN ? AND ?",
                (user_id, start.isoformat(), end.isoformat()),
            ).fetchall()
        )
    return [
        {"day": d, "minutes": round(rows.get(d.isoformat(), 0) / 60)}
        for d in (start + timedelta(days=i) for i in range(days))
    ]


def streak(user_id: int, today: date, goal_minutes: int) -> int:
    """Days in a row the goal was met, ending today (or yesterday if today isn't done yet)."""
    history = minutes_by_day(user_id, today, 60)
    met = [h["minutes"] >= goal_minutes for h in history]
    if not met[-1]:
        met = met[:-1]  # today still in progress: don't break the streak yet
    count = 0
    for m in reversed(met):
        if not m:
            break
        count += 1
    return count


# ---------- goals ----------

def daily_goal(user_id: int) -> int:
    with connect() as conn:
        row = conn.execute("SELECT daily_minutes FROM reading_goal WHERE user_id = ?", (user_id,)).fetchone()
    return row["daily_minutes"] if row else 15


def set_daily_goal(user_id: int, minutes: int) -> None:
    if minutes not in GOAL_CHOICES:
        raise ProgressError("Please pick one of the goal options.")
    with connect() as conn:
        conn.execute(
            "INSERT INTO reading_goal (user_id, daily_minutes) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET daily_minutes = excluded.daily_minutes",
            (user_id, minutes),
        )


def personal_goals(user_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, text, due, done FROM personal_goals WHERE user_id = ? "
            "ORDER BY done, CASE WHEN due IS NULL THEN 1 ELSE 0 END, due, id",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_goal(user_id: int, text: str, due: str | None) -> None:
    text = " ".join((text or "").split())[:140]
    if not text:
        raise ProgressError("Type your goal first, for example “Finish chapter 3”.")
    due = due[:10] if due and DAY_RE.match(due[:10]) else None
    with connect() as conn:
        (count,) = conn.execute("SELECT COUNT(*) FROM personal_goals WHERE user_id = ?", (user_id,)).fetchone()
        if count >= MAX_GOALS:
            raise ProgressError(f"You can have up to {MAX_GOALS} goals. Remove finished ones to add more.")
        conn.execute("INSERT INTO personal_goals (user_id, text, due) VALUES (?, ?, ?)", (user_id, text, due))


def set_goal_done(user_id: int, goal_id: int, done: bool) -> None:
    with connect() as conn:
        conn.execute("UPDATE personal_goals SET done = ? WHERE id = ? AND user_id = ?", (int(done), goal_id, user_id))


def delete_goal(user_id: int, goal_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM personal_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
