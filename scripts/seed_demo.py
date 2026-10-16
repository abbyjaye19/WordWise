"""Create a ready-to-explore demo account (no AI calls, no API key needed).

Usage, from the project folder:
    python scripts/seed_demo.py           # create the demo account if it doesn't exist
    python scripts/seed_demo.py --reset   # delete and recreate it (only the demo account)

Then sign in with:  username "demo"  ·  password "wordwise-demo"

The demo account gets:
  - color-coded folders and subfolders, with the 4 sample readings saved in them (with highlights)
  - saved words (some marked "I know it")
  - 7 days of reading time, so the goals chart and streak have data
  - a daily goal and a few personal goals with due dates
Only the demo account is touched; other accounts are left alone.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from werkzeug.security import generate_password_hash  # noqa: E402

from services import documents, library, progress  # noqa: E402
from services.db import DB_PATH, connect  # noqa: E402

USERNAME = "demo"
PASSWORD = "wordwise-demo"
EMAIL = "demo@wordwise.example"

FOLDERS = [  # (name, color, parent name or None)
    ("Science", "green", None),
    ("Biology", "gold", "Science"),
    ("English", "purple", None),
    ("Fables", "sky", "English"),
    ("History", "red", None),
    ("College", "navy", None),
    ("Economics", "gray", "College"),
]

READINGS = [  # (sample id, folder, {word to highlight: color})
    ("photosynthesis", "Biology", {"photosynthesis": "gold", "chlorophyll": "green", "glucose": "blue"}),
    ("fox-and-crow", "Fables", {"proud": "gold", "cheese": "green"}),
    ("industrial-revolution", "History", {"capital": "gold", "reforms": "green", "unions": "blue"}),
    ("opportunity-cost", "Economics", {"forgone": "gold", "trade-off": "green"}),
]

WORDS = [  # hand-written so the script needs no AI calls
    dict(word="photosynthesis", syllables="pho-to-syn-the-sis", say_it="FOH-toh-SIN-thuh-sis", part_of_speech="noun",
         meaning="The way plants use sunlight to make their own food.", synonyms=["plant food-making"],
         example="Photosynthesis happens mostly in the leaves.", source_title="How Plants Make Food", known=True),
    dict(word="chlorophyll", syllables="chlo-ro-phyll", say_it="KLOR-uh-fil", part_of_speech="noun",
         meaning="The green material in leaves that catches energy from sunlight.", synonyms=["green pigment"],
         example="Chlorophyll makes leaves look green.", source_title="How Plants Make Food", known=False),
    dict(word="stomata", syllables="sto-ma-ta", say_it="STOH-muh-tuh", part_of_speech="noun",
         meaning="Tiny openings in a leaf that let air in and out.", synonyms=["leaf openings", "pores"],
         example="Stomata let carbon dioxide into the leaf.", source_title="How Plants Make Food", known=False),
    dict(word="proud", syllables="proud", say_it="PROWD", part_of_speech="adjective",
         meaning="Feeling very pleased with yourself.", synonyms=["pleased", "pleased with yourself"],
         example="The crow felt proud when the fox praised her.", source_title="The Fox and the Crow", known=True),
    dict(word="capital", syllables="cap-i-tal", say_it="KAP-ih-tul", part_of_speech="noun",
         meaning="Money that people use to start or grow a business.", synonyms=["money to invest", "funds"],
         example="Merchants used their capital to build factories.", source_title="The Industrial Revolution", known=False),
    dict(word="reforms", syllables="re-forms", say_it="rih-FORMZ", part_of_speech="noun",
         meaning="Changes made to fix something unfair or not working well.", synonyms=["changes", "improvements"],
         example="New reforms limited how long children could work.", source_title="The Industrial Revolution", known=False),
    dict(word="forgone", syllables="for-gone", say_it="for-GON", part_of_speech="adjective",
         meaning="Given up; not chosen.", synonyms=["given up", "passed up"],
         example="The forgone wages were the cost of studying.", source_title="Lecture Notes: Opportunity Cost", known=False),
]

MINUTES_LAST_7_DAYS = [12, 0, 18, 9, 16, 20, 17]  # oldest -> today; goal 15 gives a 3-day streak
DAILY_GOAL = 15
GOALS = [  # (text, days from today or None, done)
    ("Read The Fox and the Crow with my little brother", -1, True),
    ("Practice my saved words for 10 minutes", 1, False),
    ("Finish chapter 3 of my science book", 2, False),
    ("Finish the Industrial Revolution reading", 5, False),
    ("Read one book just for fun this month", None, False),
]


def _bare(token: str) -> str:
    return re.sub(r"^[^\w]+|[^\w]+$", "", token).lower()


def highlight_map(doc: dict, words: dict) -> dict:
    """{word_index: color} using the same word numbering as the Reading Studio (runs of non-space characters)."""
    out, i = {}, 0
    for section in doc["sections"]:
        for para in section["paragraphs"]:
            for m in re.finditer(r"\S+", para):
                color = words.get(_bare(m.group()))
                if color:
                    out[str(i)] = color
                i += 1
    return out


def find_demo() -> int | None:
    with connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ? COLLATE NOCASE", (USERNAME,)).fetchone()
    return row["id"] if row else None


def delete_demo(user_id: int) -> None:
    with connect() as conn:  # foreign keys cascade to folders, readings, words, goals, reading log
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def create_demo() -> int:
    with connect() as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (USERNAME, EMAIL, generate_password_hash(PASSWORD)),
        ).lastrowid

    folder_ids: dict[str, int] = {}
    for name, color, parent in FOLDERS:
        folder_ids[name] = library.create_folder(uid, name, color, folder_ids.get(parent))

    for sample_id, folder, marks in READINGS:
        doc = documents.from_sample(sample_id)
        library.save_reading(uid, doc, highlight_map(doc, marks), folder_ids[folder])

    for w in WORDS:
        progress.save_word(uid, {k: v for k, v in w.items() if k != "known"})
    with connect() as conn:
        for w in WORDS:
            if w["known"]:
                conn.execute("UPDATE saved_words SET known = 1 WHERE user_id = ? AND word = ?", (uid, w["word"]))

    today = date.today()
    with connect() as conn:  # past days written directly (the app itself only accepts today/yesterday)
        for offset, minutes in zip(range(len(MINUTES_LAST_7_DAYS) - 1, -1, -1), MINUTES_LAST_7_DAYS):
            if minutes:
                conn.execute(
                    "INSERT INTO reading_log (user_id, day, seconds) VALUES (?, ?, ?)",
                    (uid, (today - timedelta(days=offset)).isoformat(), minutes * 60),
                )
    progress.set_daily_goal(uid, DAILY_GOAL)
    for text, days, done in GOALS:
        due = (today + timedelta(days=days)).isoformat() if days is not None else None
        progress.add_goal(uid, text, due)
    with connect() as conn:
        for text, _days, done in GOALS:
            if done:
                conn.execute("UPDATE personal_goals SET done = 1 WHERE user_id = ? AND text = ?", (uid, text))
    return uid


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the WordWise demo account.")
    parser.add_argument("--reset", action="store_true", help="delete the demo account first, then recreate it")
    args = parser.parse_args()

    existing = find_demo()
    if existing and not args.reset:
        print(f'The demo account already exists. Sign in with "{USERNAME}" / "{PASSWORD}".')
        print("Run with --reset to start it over.")
        return
    if existing:
        delete_demo(existing)
        print("Deleted the old demo account.")

    uid = create_demo()
    t = progress.word_counts(uid)
    print(f"Demo account ready in {DB_PATH}")
    print(f"  folders: {len(library.folders(uid))} · readings: {len(library.readings(uid))} · "
          f"saved words: {t['total']} ({t['known']} known) · goals: {len(progress.personal_goals(uid))}")
    print(f'Sign in at http://127.0.0.1:8050/account with "{USERNAME}" / "{PASSWORD}"')


if __name__ == "__main__":
    main()
