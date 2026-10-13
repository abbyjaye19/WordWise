"""User accounts: sign up, sign in, and who is signed in.

Passwords are stored only as salted scrypt hashes (werkzeug). The signed-in
user id lives in Flask's signed session cookie.
"""

from __future__ import annotations

import re
import sqlite3
import time
from collections import defaultdict

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

from services.db import connect

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8

# Slow down password guessing: after 5 misses, wait 5 minutes.
_failures: dict[str, list[float]] = defaultdict(list)
MAX_FAILS, LOCK_SECONDS = 5, 300


class AccountError(ValueError):
    """A friendly, user-facing account problem."""


def create_account(username: str, email: str, password: str, confirm: str) -> dict:
    username, email = (username or "").strip(), (email or "").strip().lower()
    if not USERNAME_RE.match(username):
        raise AccountError("Pick a username with 3 to 30 letters or numbers (you can also use . _ -).")
    if not EMAIL_RE.match(email):
        raise AccountError("That email doesn't look right. Please check it.")
    if len(password or "") < MIN_PASSWORD:
        raise AccountError(f"Your password needs at least {MIN_PASSWORD} characters.")
    if password != confirm:
        raise AccountError("The two passwords don't match.")
    try:
        with connect() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, generate_password_hash(password)),
            )
            user_id = cur.lastrowid
    except sqlite3.IntegrityError as exc:
        raise AccountError("That username or email already has an account. Try signing in.") from exc
    _start_session(user_id)
    return {"id": user_id, "username": username}


def sign_in(identifier: str, password: str) -> dict:
    key = (identifier or "").strip().lower()
    recent = [t for t in _failures[key] if time.time() - t < LOCK_SECONDS]
    _failures[key] = recent
    if len(recent) >= MAX_FAILS:
        raise AccountError("Too many tries. Please wait a few minutes and try again.")
    with connect() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ? OR email = ?",
            (key, key),
        ).fetchone()
    if not row or not check_password_hash(row["password_hash"], password or ""):
        _failures[key].append(time.time())
        raise AccountError("That username/email and password don't match.")
    _failures.pop(key, None)
    _start_session(row["id"])
    return {"id": row["id"], "username": row["username"]}


def _start_session(user_id: int) -> None:
    session.clear()
    session.permanent = True
    session["uid"] = user_id


def sign_out() -> None:
    session.clear()


def current_user() -> dict | None:
    """The signed-in user, or None. Safe to call inside any Dash callback or page layout."""
    try:
        uid = session.get("uid")
    except RuntimeError:  # no request context
        return None
    if not uid:
        return None
    with connect() as conn:
        row = conn.execute("SELECT id, username, email FROM users WHERE id = ?", (uid,)).fetchone()
    return dict(row) if row else None
