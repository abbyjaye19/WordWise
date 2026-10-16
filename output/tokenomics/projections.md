# WordWise tokenomics (measured)

Model: `gpt-6-luna` via Portkey. Prices per 1M tokens: input $0.1, cached input $0.01, cache write $0.125, output $0.5.

One **study session** = 8 word lookups + 3 explain requests + 1 summary + 4 AI Tutor messages (16 calls).

## Measured cost per session (warm prompt cache)

| Setting | Input tokens | Cached input | Output (reasoning) | Cost / session |
|---|---:|---:|---:|---:|
| Before: short prompts (never cached) | 13,244 | 2,147 | 1,559 (89) | $0.00194 |
| After: shared reader-level guide (cached) | 27,499 | 24,595 | 1,533 (35) | $0.00137 |
| Same session repeated by a classmate (Portkey replay: 16/16 hits) | 27,499 | — | — | $0.00000 |

Saving from the cached shared guide: **29% per session**. The cache costs a one-time write (about 1,600 tokens x $0.125/1M = $0.00020 per feature) whenever it expires; with steady use it stays warm.

## Cost per feature call (after, warm)

| Feature | Avg input | Avg cached | Avg output | Avg cost | Avg seconds |
|---|---:|---:|---:|---:|---:|
| explain | 1,576 | 1,511 | 108 | $0.000077 | 2.48 |
| summarize | 1,793 | 1,594 | 447 | $0.000264 | 4.71 |
| tutor_chat | 1,967 | 1,458 | 36 | $0.000096 | 1.89 |
| word_help | 1,639 | 1,580 | 77 | $0.000062 | 2.36 |

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
| Before (short prompts, no caching) | light | $0.008 | $0.78 | $77.56 |
| Before (short prompts, no caching) | typical | $0.023 | $2.33 | $232.68 |
| Before (short prompts, no caching) | heavy | $0.058 | $5.82 | $581.70 |
| After (shared guide, cached) | light | $0.005 | $0.55 | $54.96 |
| After (shared guide, cached) | typical | $0.017 | $1.65 | $164.88 |
| After (shared guide, cached) | heavy | $0.041 | $4.12 | $412.20 |
| After + class repeats (25% replayed) | light | $0.004 | $0.41 | $41.22 |
| After + class repeats (25% replayed) | typical | $0.012 | $1.24 | $123.66 |
| After + class repeats (25% replayed) | heavy | $0.031 | $3.09 | $309.15 |

Not included: hosting (the app runs locally today) and read-aloud, which uses the browser's free built-in voices.
The reading tools themselves (fonts, spacing, highlighter, ruler, folders, exports) use no AI and cost nothing per use.
