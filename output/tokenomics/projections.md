# WordWise tokenomics (measured)

Model: `gpt-6-luna` via Portkey. Prices per 1M tokens: input $0.1, cached input $0.01, cache write $0.125, output $0.5.

One **study session** = 8 word lookups + 3 explain requests + 1 summary + 4 AI Tutor messages (16 calls). The **current app** adds the Pronunciation Helper (when the reading opens) and one Reading Levels rewrite, all with a student profile (18 calls).

## Measured cost per session (warm prompt cache)

| Setting | Input tokens | Cached input | Output (reasoning) | Cost / session |
|---|---:|---:|---:|---:|
| Before: short prompts (never cached) | 13,244 | 2,147 | 1,559 (89) | $0.00194 |
| After: shared reader-level guide (cached) | 27,499 | 24,595 | 1,533 (35) | $0.00137 |
| **Current app (6 agents, profile; 18 calls)** | 39,316 | 34,321 | 2,209 (439) | **$0.00207** |
| Same session repeated by a classmate (Portkey replay: 16/16 hits) | 27,499 | — | — | $0.00000 |

Saving from the cached shared guide: **29% per session**. The cache costs a one-time write (about 1,600 tokens x $0.125/1M = $0.00020 per feature) whenever it expires; with steady use it stays warm.

## Cost per feature call (current app, warm)

| Feature | Avg input | Avg cached | Avg output | Avg cost | Avg seconds |
|---|---:|---:|---:|---:|---:|
| explain | 1,831 | 1,712 | 105 | $0.000084 | 1.85 |
| pronunciation | 2,249 | 2,246 | 270 | $0.000158 | 2.56 |
| rewrite | 2,025 | 1,769 | 197 | $0.000148 | 4.21 |
| summarize | 2,048 | 1,795 | 347 | $0.000223 | 2.85 |
| tutor_chat | 3,088 | 2,298 | 44 | $0.000143 | 1.66 |
| word_help | 1,894 | 1,773 | 113 | $0.000089 | 2.96 |

## Reasoning effort trade-off (word lookups)

| Effort | Avg output tokens (reasoning) | Avg cost | Avg seconds |
|---|---:|---:|---:|
| low (used) | 77 (0) | $0.000062 | 2.36 |
| medium | 191 (110) | $0.000119 | 3.89 |

Medium effort costs 93% more per lookup and is 65% slower.

## Monthly cost (AI only)

Assumed sessions per active user per month: light = 4, typical = 12, heavy = 30.

| Scenario | Usage | 1 user | 100 users | 10,000 users |
|---|---|---:|---:|---:|
| Current app (6 agents, student profile) | light | $0.008 | $0.83 | $82.84 |
| Current app (6 agents, student profile) | typical | $0.025 | $2.49 | $248.52 |
| Current app (6 agents, student profile) | heavy | $0.062 | $6.21 | $621.30 |
| Current + class repeats (25% replayed) | light | $0.006 | $0.62 | $62.13 |
| Current + class repeats (25% replayed) | typical | $0.019 | $1.86 | $186.39 |
| Current + class repeats (25% replayed) | heavy | $0.047 | $4.66 | $465.98 |
| Earlier design, before caching (16 calls) | light | $0.008 | $0.78 | $77.56 |
| Earlier design, before caching (16 calls) | typical | $0.023 | $2.33 | $232.68 |
| Earlier design, before caching (16 calls) | heavy | $0.058 | $5.82 | $581.70 |
| Earlier design, after caching (16 calls) | light | $0.005 | $0.55 | $54.96 |
| Earlier design, after caching (16 calls) | typical | $0.017 | $1.65 | $164.88 |
| Earlier design, after caching (16 calls) | heavy | $0.041 | $4.12 | $412.20 |

Not included: hosting (the app runs locally today) and read-aloud, which uses the browser's free built-in voices.
The reading tools themselves (fonts, spacing, highlighter, ruler, folders, exports) use no AI and cost nothing per use.
