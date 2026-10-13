"""Curated resource hub content (data/resources.json).

Every link is from a government health or education agency, an academic
medical center or medical society, a university research center, or an
established nonprofit, and was checked on the date in the file.
"""

from __future__ import annotations

import json
from functools import lru_cache

from config import DATA_DIR

RESOURCES_PATH = DATA_DIR / "resources.json"

AUDIENCES = {
    "all": "Everyone",
    "students": "Students",
    "parents": "Parents & families",
    "adults": "Adults",
    "educators": "Teachers",
}


@lru_cache(maxsize=1)
def load() -> dict:
    data = json.loads(RESOURCES_PATH.read_text(encoding="utf-8"))
    for topic in data["topics"]:  # fail fast on a typo'd source id
        for sid in topic["links"] + [s for p in topic["points"] for s in p["src"]]:
            if sid not in data["sources"]:
                raise KeyError(f"resources.json: unknown source id {sid!r} in topic {topic['id']!r}")
    return data


def topics_for(audience: str = "all") -> list[dict]:
    """Topics (and their links) relevant to one audience."""
    data = load()
    out = []
    for t in data["topics"]:
        if audience != "all" and audience not in t["audience"]:
            continue
        links = [
            {"id": sid, **data["sources"][sid]}
            for sid in t["links"]
            if audience == "all" or audience in data["sources"][sid]["audience"]
        ]
        out.append({**t, "links": links})
    return out
