"""Reading preferences and the student's reading profile: one definition used everywhere.

The settings panel, account sync, "Clear all preferences", and the AI Tutor's suggestions all read
SETTINGS below, so the tutor can only ever propose a value that really exists.
"""

from __future__ import annotations

import json

from services.db import connect

# key: (label, [(value, label), ...], default, short description used in the tutor prompt)
SETTINGS: dict[str, tuple[str, list[tuple[str, str]], str, str]] = {
    "size": ("Text size", [("s", "Small"), ("m", "Medium"), ("l", "Large"), ("xl", "Extra large")], "m", "text size"),
    "spacing": ("Line and letter spacing", [("normal", "Normal"), ("wide", "Wide"), ("xwide", "Extra wide")], "normal",
                "space between lines, letters, and words"),
    "font": ("Font", [("atkinson", "Atkinson Hyperlegible"), ("lexend", "Lexend"), ("verdana", "Verdana")], "atkinson", "typeface"),
    "theme": ("Background", [("cream", "Cream"), ("blue", "Soft blue"), ("dark", "Dark navy")], "cream", "background color"),
    "contrast": ("Contrast", [("normal", "Normal"), ("high", "High")], "normal", "text contrast"),
    "linewidth": ("Line length", [("narrow", "Short lines"), ("medium", "Medium"), ("wide", "Long lines")], "medium",
                  "how many words fit on one line"),
    "rate": ("Read-aloud speed", [("0.7", "Slower"), ("0.85", "Slow"), ("1", "Normal"), ("1.15", "Fast"), ("1.3", "Faster")], "1",
             "read-aloud speed"),
    "readalong": ("Read-along highlight", [("word", "Word"), ("sentence", "Sentence"), ("both", "Word + sentence")], "both",
                  "what is highlighted while reading aloud"),
}
DEFAULTS = {k: v[2] for k, v in SETTINGS.items()}
ALLOWED = {k: {val for val, _ in v[1]} for k, v in SETTINGS.items()}


def label_of(key: str, value: str) -> str:
    return next((lab for val, lab in SETTINGS[key][1] if val == value), value)


def clean(prefs: dict | None) -> dict:
    """Defaults + only known keys with allowed values."""
    out = dict(DEFAULTS)
    for k, v in (prefs or {}).items():
        if k in ALLOWED and str(v) in ALLOWED[k]:
            out[k] = str(v)
    return out


def describe(prefs: dict) -> str:
    p = clean(prefs)
    return "; ".join(f"{SETTINGS[k][0]}: {label_of(k, p[k])}" for k in SETTINGS)


def load(user_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT prefs_json FROM users WHERE id = ?", (user_id,)).fetchone()
    return clean(json.loads(row["prefs_json"])) if row and row["prefs_json"] else None


def save(user_id: int, prefs: dict | None) -> None:
    with connect() as conn:
        conn.execute("UPDATE users SET prefs_json = ? WHERE id = ?", (json.dumps(clean(prefs)) if prefs else None, user_id))


# ---------- reading profile (what the student wants to work on) ----------

# key: (label, how WordWise adapts)
CHALLENGES: dict[str, tuple[str, str]] = {
    "comprehension": ("Understanding what I read", "Break ideas into smaller steps, give an example, and check understanding with a question."),
    "listening": ("Understanding what I hear (read-aloud)", "Suggest slower read-aloud with sentence highlighting so text and audio line up."),
    "decoding": ("Sounding out words", "Show syllables and a say-it guide; keep sentences short."),
    "vocabulary": ("Knowing what words mean", "Define key words in plain language and point out tricky words."),
    "spelling": ("Spelling", "Show syllables and spelling patterns when explaining words."),
    "fluency": ("Reading speed", "Keep answers short and suggest read-along so reading feels less tiring."),
    "focus": ("Keeping my place / staying focused", "Suggest the reading ruler or one-paragraph focus; keep lists short."),
    "memory": ("Remembering what I read", "Recap the big idea and end with a quick recall question."),
}
LEVELS = {0: "Not a challenge", 1: "Sometimes", 2: "Big challenge"}


def load_profile(user_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT profile_json FROM users WHERE id = ?", (user_id,)).fetchone()
    data = json.loads(row["profile_json"]) if row and row["profile_json"] else {}
    ratings = {k: int(v) for k, v in (data.get("ratings") or {}).items() if k in CHALLENGES and int(v) in LEVELS}
    priority = data.get("priority") if data.get("priority") in CHALLENGES else None
    return {"ratings": ratings, "priority": priority}


def save_profile(user_id: int, ratings: dict, priority: str | None) -> None:
    data = {"ratings": {k: int(v) for k, v in ratings.items() if k in CHALLENGES and int(v) in LEVELS},
            "priority": priority if priority in CHALLENGES else None}
    with connect() as conn:
        conn.execute("UPDATE users SET profile_json = ? WHERE id = ?", (json.dumps(data), user_id))


def profile_context(profile: dict, recent_comprehension: float | None = None) -> str:
    """Short text given to the AI helpers (in the request, not the cached instructions)."""
    r = profile.get("ratings") or {}
    big = [CHALLENGES[k][0].lower() for k, v in r.items() if v == 2]
    some = [CHALLENGES[k][0].lower() for k, v in r.items() if v == 1]
    parts = []
    if profile.get("priority"):
        parts.append(f"Top priority: {CHALLENGES[profile['priority']][0].lower()}.")
    if big:
        parts.append("Big challenges: " + ", ".join(big) + ".")
    if some:
        parts.append("Sometimes hard: " + ", ".join(some) + ".")
    if recent_comprehension is not None:
        parts.append(f"Recent self-rated understanding: {recent_comprehension:.1f} out of 5.")
    return ("Student profile (self-reported): " + " ".join(parts)) if parts else ""


def adaptations(profile: dict) -> list[str]:
    """Plain-language list of how WordWise adapts, for the dashboard."""
    r = profile.get("ratings") or {}
    order = sorted((k for k, v in r.items() if v > 0), key=lambda k: (-(k == profile.get("priority")), -r[k]))
    return [f"{CHALLENGES[k][0]}: {CHALLENGES[k][1]}" for k in order]
