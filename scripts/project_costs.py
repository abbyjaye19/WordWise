"""Turn measured session costs into per-user and at-scale monthly costs.

Usage, from the project folder (run scripts/measure_tokenomics.py first):
    python scripts/project_costs.py

Reads  output/tokenomics/summary.json
Writes output/tokenomics/projections.md  and  output/tokenomics/projections.json

All usage numbers below are ASSUMPTIONS (stated in the report). Token counts and prices are measured.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "tokenomics"

# ---- assumptions (edit here) ----
SESSIONS_PER_MONTH = {"light": 4, "typical": 12, "heavy": 30}  # 1/week, 3/week, about daily
USER_COUNTS = [1, 100, 10_000]
CLASS_SHARE = 0.25  # in the "class" estimate: share of calls that are exact repeats Portkey replays for free
CACHE_PREFIX_TOKENS = 1_600  # measured: ~1,580 cached tokens per warm call (fixed instructions + answer format)


def main() -> None:
    s = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    st = s["settings"]
    before = st["before"]["run2"]["session_cost_usd"]
    after = st["after"]["run2"]["session_cost_usd"]
    word_low = st["after"]["run2"]["per_feature"]["word_help"]
    word_med = st["effort_med"]["run2"]["per_feature"]["word_help"]
    class_cost = after * (1 - CLASS_SHARE)

    scenarios = {"Before (short prompts, no caching)": before, "After (shared guide, cached)": after,
                 f"After + class repeats ({int(CLASS_SHARE * 100)}% replayed)": class_cost}
    proj = {name: {usage: {n: round(cost * sessions * n, 4) for n in USER_COUNTS}
                   for usage, sessions in SESSIONS_PER_MONTH.items()}
            for name, cost in scenarios.items()}

    p = s["prices_per_1m"]
    lines = [
        "# WordWise tokenomics (measured)",
        "",
        f"Model: `{s['model']}` via Portkey. Prices per 1M tokens: input ${p['input_per_1m']}, cached input "
        f"${p['cached_input_per_1m']}, cache write ${p['cache_write_per_1m']}, output ${p['output_per_1m']}.",
        "",
        "One **study session** = 8 word lookups + 3 explain requests + 1 summary + 4 AI Tutor messages (16 calls).",
        "",
        "## Measured cost per session (warm prompt cache)",
        "",
        "| Setting | Input tokens | Cached input | Output (reasoning) | Cost / session |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, label in (("before", "Before: short prompts (never cached)"), ("after", "After: shared reader-level guide (cached)")):
        e = st[key]["run2"]
        lines.append(f"| {label} | {e['input_tokens']:,} | {e['cached_input_tokens']:,} | {e['output_tokens']:,} ({e['reasoning_tokens']}) | ${e['session_cost_usd']:.5f} |")
    e = st["class_repeat"]["run2"]
    lines.append(f"| Same session repeated by a classmate (Portkey replay: {e['gateway_hits']}/{e['calls']} hits) | {e['input_tokens']:,} | — | — | ${e['session_cost_usd']:.5f} |")
    lines += [
        "",
        f"Saving from the cached shared guide: **{100 * (1 - after / before):.0f}% per session**. "
        f"The cache costs a one-time write (about {CACHE_PREFIX_TOKENS:,} tokens x ${p['cache_write_per_1m']}/1M = "
        f"${CACHE_PREFIX_TOKENS * p['cache_write_per_1m'] / 1e6:.5f} per feature) whenever it expires; with steady use it stays warm.",
        "",
        "## Cost per feature call (after, warm)",
        "",
        "| Feature | Avg input | Avg cached | Avg output | Avg cost | Avg seconds |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for f, v in st["after"]["run2"]["per_feature"].items():
        lines.append(f"| {f} | {v['avg_input']:,} | {v['avg_cached']:,} | {v['avg_output']} | ${v['avg_cost_usd']:.6f} | {v['avg_seconds']} |")
    lines += [
        "",
        "## Reasoning effort trade-off (word lookups)",
        "",
        "| Effort | Avg output tokens (reasoning) | Avg cost | Avg seconds |",
        "|---|---:|---:|---:|",
        f"| low (used) | {word_low['avg_output']} ({word_low['avg_reasoning']}) | ${word_low['avg_cost_usd']:.6f} | {word_low['avg_seconds']} |",
        f"| medium | {word_med['avg_output']} ({word_med['avg_reasoning']}) | ${word_med['avg_cost_usd']:.6f} | {word_med['avg_seconds']} |",
        "",
        f"Medium effort costs {100 * (word_med['avg_cost_usd'] / word_low['avg_cost_usd'] - 1):.0f}% more per lookup "
        f"and is {100 * (word_med['avg_seconds'] / word_low['avg_seconds'] - 1):.0f}% slower.",
        "",
        "## Monthly cost (AI only)",
        "",
        "Assumed sessions per active user per month: " + ", ".join(f"{k} = {v}" for k, v in SESSIONS_PER_MONTH.items()) + ".",
        "",
        "| Scenario | Usage | 1 user | 100 users | 10,000 users |",
        "|---|---|---:|---:|---:|",
    ]
    for name, by_usage in proj.items():
        for usage, by_n in by_usage.items():
            lines.append(f"| {name} | {usage} | ${by_n[1]:.3f} | ${by_n[100]:.2f} | ${by_n[10_000]:,.2f} |")
    lines += [
        "",
        "Not included: hosting (the app runs locally today) and read-aloud, which uses the browser's free built-in voices.",
        "The reading tools themselves (fonts, spacing, highlighter, ruler, folders, exports) use no AI and cost nothing per use.",
        "",
    ]
    (OUT / "projections.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "projections.json").write_text(json.dumps({"assumptions": {"sessions_per_month": SESSIONS_PER_MONTH, "class_share": CLASS_SHARE},
                                                      "session_cost_usd": {"before": before, "after": after, "class": class_cost},
                                                      "monthly_usd": proj}, indent=2), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
