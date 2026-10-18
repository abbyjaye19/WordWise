"""Measure real token use and cost for one WordWise study session, under different settings.

Usage, from the project folder (needs PORTKEY_API_KEY; costs about $0.01 in total):
    python scripts/measure_tokenomics.py

What it does
  A "study session" = what one student does in one sitting in the Reading Studio:
    8 word lookups, 3 explain requests (simpler / example / steps), 1 summary, 4 AI Tutor messages.
  Each setting runs the session twice. Run 1 starts cold. Run 2 uses a different reader level, so
  every request is new but the fixed instructions are already in the provider's prompt cache. That is
  the normal case once many students use the app. Both runs force fresh model answers, so Portkey's
  replay cache doesn't hide the real cost.

Settings compared
  before       short shared prompt (~650 tokens) -> below the 1,024-token caching minimum
  after        shared prompt + reader-level guide (~1,300 tokens) -> cached at 10x lower price
  effort_med   same as "after" but reasoning effort "medium" instead of "low" (word lookups only)
  class_repeat a second student in the same class repeats run 2 exactly. Portkey replays identical
               requests from its cache (x-portkey-cache-status: HIT), so the model isn't called.

Writes
  output/tokenomics/calls.jsonl   every call with its token counts and cost
  output/tokenomics/summary.json  per-setting, per-feature, and per-session totals
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from services import ai, documents  # noqa: E402

OUT = ROOT / "output" / "tokenomics"
CALLS = OUT / "calls.jsonl"
SUMMARY = OUT / "summary.json"

PLANTS = documents.from_sample("photosynthesis")
HISTORY = documents.from_sample("industrial-revolution")
P = [p for s in PLANTS["sections"] for p in s["paragraphs"]]
H = [p for s in HISTORY["sections"] for p in s["paragraphs"]]

WORDS = [  # (word, sentence it appears in)
    ("chloroplasts", P[1]), ("chlorophyll", P[1]), ("pigment", P[1]), ("absorb", P[2]),
    ("stomata", P[2]), ("glucose", P[3]), ("deposits", H[1]), ("reforms", H[3]),
]
EXPLAINS = [(P[2], "simpler"), (H[2], "example"), (P[3], "steps")]
TUTOR_TURNS = [
    "Why did the Industrial Revolution start in Britain?",
    "What does capital mean here?",
    "Can you quiz me with one question?",
    "I think it's because they had coal. Is that right?",
]


def clear_caches() -> None:
    """Our own answer cache would make repeat runs free; turn it off so we measure the model."""
    ai.word_help.cache_clear()
    ai.explain.cache_clear()
    ai._summarize_cached.cache_clear()


def session(level: str = "9-12", only_words: bool = False) -> None:
    clear_caches()
    for word, sentence in WORDS:
        ai.word_help(word, sentence, level)
    if only_words:
        return
    for passage, mode in EXPLAINS:
        ai.explain(passage, mode, level)
    ai.summarize(documents.section_text(HISTORY), "Whole reading", level)
    history, reading = [], documents.section_text(HISTORY)
    for turn in TUTOR_TURNS:
        history.append({"role": "user", "content": turn})
        history.append({"role": "assistant", "content": ai.tutor_reply(history, level, reading).reply})


RUN_LEVELS = {1: "9-12", 2: "13-17"}
FORCE_FRESH = {"x-portkey-cache-force-refresh": "true"}


def run(setting: str, guide: bool, effort: str, only_words: bool = False, runs=(1, 2), fresh: bool = True) -> None:
    ai.USE_LEVEL_GUIDE, ai.REASONING_EFFORT = guide, effort
    ai.EXTRA_HEADERS = FORCE_FRESH if fresh else {}
    for run_no in runs:
        ai.LOG_EXTRA = {"setting": setting, "run": run_no}
        t = time.perf_counter()
        session(level=RUN_LEVELS[run_no], only_words=only_words)
        print(f"  {setting:12s} run {run_no}: {time.perf_counter() - t:5.1f}s")


def summarize_results() -> dict:
    rows = [json.loads(line) for line in CALLS.read_text(encoding="utf-8").splitlines()]
    out: dict = {"model": ai.MODEL_NAME, "prices_per_1m": ai.PRICES, "settings": {}}
    by = defaultdict(list)
    for r in rows:
        by[(r["setting"], r["run"])].append(r)
    for (setting, run_no), calls in sorted(by.items()):
        feats = defaultdict(list)
        for c in calls:
            feats[c["feature"].split("_")[0] if c["feature"].startswith("explain") else c["feature"]].append(c)
        entry = {
            "calls": len(calls),
            "session_cost_usd": round(sum(c["cost_usd"] for c in calls), 6),
            "input_tokens": sum(c["input_tokens"] for c in calls),
            "cached_input_tokens": sum(c["cached_input_tokens"] for c in calls),
            "cache_write_tokens": sum(c["cache_write_tokens"] for c in calls),
            "output_tokens": sum(c["output_tokens"] for c in calls),
            "reasoning_tokens": sum(c["reasoning_tokens"] for c in calls),
            "median_seconds": round(statistics.median(c["seconds"] for c in calls), 2),
            "gateway_hits": sum(1 for c in calls if c.get("gateway_cache") == "HIT"),
            "per_feature": {
                f: {
                    "calls": len(cs),
                    "avg_input": round(statistics.mean(c["input_tokens"] for c in cs)),
                    "avg_cached": round(statistics.mean(c["cached_input_tokens"] for c in cs)),
                    "avg_output": round(statistics.mean(c["output_tokens"] for c in cs)),
                    "avg_reasoning": round(statistics.mean(c["reasoning_tokens"] for c in cs)),
                    "avg_cost_usd": round(statistics.mean(c["cost_usd"] for c in cs), 7),
                    "avg_seconds": round(statistics.mean(c["seconds"] for c in cs), 2),
                }
                for f, cs in sorted(feats.items())
            },
        }
        out["settings"].setdefault(setting, {})[f"run{run_no}"] = entry
    return out


def main() -> None:
    if not ai.PORTKEY_API_KEY:
        sys.exit("PORTKEY_API_KEY is missing. Add it to .env (this folder or one level up).")
    OUT.mkdir(parents=True, exist_ok=True)
    if CALLS.exists():
        CALLS.unlink()
    ai.USAGE_LOG = CALLS  # keep measurement calls out of the app's usage log
    print("Measuring (about 1-2 minutes)...")
    run("before", guide=False, effort="low")
    run("after", guide=True, effort="low")
    run("effort_med", guide=True, effort="medium", only_words=True)
    run("class_repeat", guide=True, effort="low", runs=(2,), fresh=False)
    summary = summarize_results()
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nSession totals (run 2 = warm cache):")
    print(f"  {'setting':12s} {'run':>3s} {'calls':>5s} {'input':>7s} {'cached':>7s} {'output':>7s} {'reason':>7s} {'hits':>4s} {'cost $':>10s}")
    for setting, runs in summary["settings"].items():
        for run_name, e in runs.items():
            print(f"  {setting:12s} {run_name[-1]:>3s} {e['calls']:5d} {e['input_tokens']:7d} {e['cached_input_tokens']:7d} "
                  f"{e['output_tokens']:7d} {e['reasoning_tokens']:7d} {e['gateway_hits']:4d} {e['session_cost_usd']:10.6f}")
    print(f"\nWrote {CALLS.relative_to(ROOT)} and {SUMMARY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
