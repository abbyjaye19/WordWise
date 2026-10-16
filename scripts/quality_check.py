"""Does the cached reader-level guide change answer quality? (trade-off evidence for the report)

Usage, from the project folder (needs PORTKEY_API_KEY; about 24 small calls, well under $0.01):
    python scripts/quality_check.py

Asks the Word Coach about the same words at the youngest and oldest reader levels, with and without
the guide, and checks the answers against our own targets:
  - ages 5-8: every sentence under 10 words
  - no filler openers ("Great question", "Sure")
Writes output/tokenomics/quality_check.md with every answer, so a person can judge them too.
"""

from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from services import ai, documents  # noqa: E402

OUT = ROOT / "output" / "tokenomics" / "quality_check.md"
PLANTS = [p for s in documents.from_sample("photosynthesis")["sections"] for p in s["paragraphs"]]
HISTORY = [p for s in documents.from_sample("industrial-revolution")["sections"] for p in s["paragraphs"]]
COST = [p for s in documents.from_sample("opportunity-cost")["sections"] for p in s["paragraphs"]]
CASES = [("chlorophyll", PLANTS[1]), ("stomata", PLANTS[2]), ("capital", HISTORY[1]),
         ("reforms", HISTORY[3]), ("implicit", COST[2]), ("trade-off", COST[0])]
LEVELS = ["5-8", "18+"]
FILLER = re.compile(r"^(great question|sure|of course|good question)", re.I)


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def main() -> None:
    ai.EXTRA_HEADERS = {"x-portkey-cache-force-refresh": "true"}
    ai.USAGE_LOG = ROOT / "output" / "tokenomics" / "quality_calls.jsonl"
    results = []
    for guide in (False, True):
        ai.USE_LEVEL_GUIDE = guide
        ai.word_help.cache_clear()
        for level in LEVELS:
            for word, sentence in CASES:
                w = ai.word_help(word, sentence, level)
                sents = sentences(w.meaning_here)
                lens = [len(s.split()) for s in sents]
                results.append({"guide": guide, "level": level, "word": word, "meaning": w.meaning_here,
                                "example": w.example, "max_words": max(lens), "avg_words": statistics.mean(lens),
                                "filler": bool(FILLER.match(w.meaning_here))})

    def stats(guide, level):
        rs = [r for r in results if r["guide"] == guide and r["level"] == level]
        ok = sum(1 for r in rs if r["max_words"] < 10) if level == "5-8" else None
        return rs, statistics.mean(r["avg_words"] for r in rs), ok, sum(r["filler"] for r in rs)

    lines = ["# Quality check: does the cached reader-level guide change answers?", "",
             "Word Coach answers for the same 6 words, with and without the guide. Target for ages 5–8: every sentence under 10 words.", "",
             "| Setting | Level | Avg words per sentence | Answers meeting the 5–8 target | Filler openers |", "|---|---|---:|---:|---:|"]
    for guide in (False, True):
        for level in LEVELS:
            rs, avg, ok, filler = stats(guide, level)
            lines.append(f"| {'With guide (cached)' if guide else 'Without guide'} | {level} | {avg:.1f} | "
                         f"{f'{ok} of {len(rs)}' if ok is not None else '—'} | {filler} |")
    lines += ["", "## Every answer (meaning in context)", ""]
    for word, _ in CASES:
        lines.append(f"### {word}")
        for level in LEVELS:
            for guide in (False, True):
                r = next(x for x in results if x["word"] == word and x["level"] == level and x["guide"] == guide)
                lines.append(f"- **{level}, {'with' if guide else 'without'} guide** ({r['max_words']} words max): {r['meaning']}")
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:12]))
    print(f"\nWrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
