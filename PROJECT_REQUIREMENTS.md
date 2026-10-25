# Final Project Requirements — Checklist

Source: https://zlisto.github.io/mgt_409_fa26/project_requirements.html (reviewed 2026-10-12)

**Due:** Monday, October 26, 2026, 6:00 PM on Canvas. Solo project.
**Goal:** An AI agent app that does something useful for real people; show how it works, what it costs, and how it is kept safe.

## Deliverables

- [x] **GitHub repo** — public: https://github.com/abbyjaye19/WordWise
  - [x] All code needed to run the app
  - [x] `README.md` with step-by-step run instructions (tested from a fresh clone 2026-10-15)
  - [x] `.env.example` with key names only
  - [x] No real `.env` / `PORTKEY_API_KEY` committed (scanned before first push)
- [x] **`report.html`** — 15 printed letter pages, images embedded (`scripts/build_report.py`); updated 2026-10-25 for 6 agents, current costs, 15/15 safety, 3 user tests
- [x] **`slides.html`** — 10 slides, reveal.js embedded, works offline (`scripts/build_slides.py`)
- [ ] **Demo video** (optional) — 2–3 min screen recording

Both HTML files must open by double-click on any computer with all screenshots visible.

## Technical rules

- **Model:** course key `PORTKEY_API_KEY` with **`gpt-6-luna` only** (or own key, e.g. `OPENAI_API_KEY`, paid by me).
- **`.env` lookup:** repo folder first, then one folder up. Only `PORTKEY_API_KEY` / `OPENAI_API_KEY` names. Test by moving `.env` up a folder.
- **Run:** hosted online (live until grades posted) *or* runs locally from a fresh clone via README.
- **10-minute rule:** not running within 10 min of following README → 0 for "staff can run it."
- **Large data:** ship a small test dataset; README explains switching to full data.
- **Dry run:** fresh clone in a new folder, `.env` one level up, follow README, use the app.

## Report sections (in order)

1. Title and links — name, my name, repo link, app link, one-sentence description
2. Motivation — who has the problem, how they handle it now, what it costs them
3. What is new — existing alternatives, what's different, why it matters
4. The agents — roles, tools, organization diagram, model choices, one traced run with screenshots
5. Tokenomics — measured input / cached input / output tokens per run; cost per run, per user/month, at 100 and 10,000 users; cost cuts and tradeoffs with evidence
6. Safety — prompt injection, data leakage, invented facts, wrong actions, infinite loops, overspending; show ≥1 defense working
7. Impact — quantified results (money, time, quality, reach) with sources; honest limits
8. Limits and next steps

## Slides (≤10, reveal.js, app colors, big text)

Title/pitch · Problem · What's new · Agent diagram · Demo screenshots · Cost · Safety · Impact · What's next

## Grading (100)

| Component | Pts | Breakdown |
|---|---|---|
| Idea | 21 | Novelty and real-world value |
| App | 30 | Works end to end 15 · staff can run it 5 · look and feel 10 |
| Report | 41 | Motivation & new 8 · agent design 10 · tokenomics 8 · safety 8 · impact 5 · design 2 |
| Slides | 8 | Content 6 · design 2 |

- **Tier 3** needs real evidence: a real user trying the app, measured time/quality gains, org-scale cost analysis.
- Overdone ideas (summarizers, chat-with-PDF, …) are capped at Tier 1 without a real twist — WordWise must not read as "just a summarizer."
- Sections missing required evidence (real token counts, defense screenshots, real-user feedback, sourced numbers) get at most half credit.

## Evidence to collect as we build

- [x] Token logs per run (`output/usage_log.jsonl`, `output/tokenomics/`)
- [x] Screenshots: traced run + 8 defenses (`deliverables/screenshots/`)
- [x] Real-user feedback: 3 observed sessions (Oct 19 and 25) in `deliverables/user_testing.json`; 9 fixes shipped. Timed pilot not run (stated as a limit)
- [x] Sourced statistics on dyslexia prevalence and the cost/availability of specialized instruction (no sourced dollar figure for tutoring)

## Remaining before submission (as of 2026-10-25)

- [x] Run 1–3 user tests, add results to `deliverables/user_testing.json`, rebuild report + slides
- [ ] Proofread report and slides
- [ ] Optional demo video
- [x] Final fresh-clone dry run (2026-10-25, commit 6a17ee7): 68 s install, all pages, demo, and AI help work with `.env` one folder up
- [ ] Submit on Canvas: repo link, `report.html`, `slides.html` (and video if made)
