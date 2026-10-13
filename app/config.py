"""Project-wide settings: paths, .env loading, and the AI model name.

The course requires the app to look for `.env` in the repo folder first,
then in the folder one level above it.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"  # token/cost logs go here

for folder in (PROJECT_ROOT, PROJECT_ROOT.parent):
    if (folder / ".env").exists():
        load_dotenv(folder / ".env", override=False)

# Course rule: gpt-6-luna through Portkey is the only model allowed.
MODEL_NAME = "gpt-6-luna"
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY", "").strip()

def _secret_key() -> str:
    """Signs the login cookie. Made once and kept in data/.secret_key (never committed)."""
    if os.getenv("WORDWISE_SECRET_KEY"):
        return os.environ["WORDWISE_SECRET_KEY"]
    path = DATA_DIR / ".secret_key"
    if not path.exists():
        import secrets

        DATA_DIR.mkdir(exist_ok=True)
        path.write_text(secrets.token_hex(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


SECRET_KEY = _secret_key()

HOST = os.getenv("WORDWISE_HOST", "127.0.0.1")
PORT = int(os.getenv("WORDWISE_PORT", "8050"))
