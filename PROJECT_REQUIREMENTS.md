# Final Project Requirements — Checklist

Source: https://zlisto.github.io/mgt_409_fa26/project_requirements.html (reviewed 2026-10-12)

**Due:** Monday, October 26, 2026, 6:00 PM on Canvas. Solo project.
**Goal:** An AI agent app that does something useful for real people; show how it works, what it costs, and how it is kept safe.

## Deliverables

- [ ] **GitHub repo** — public, or private with `zlisto` added as collaborator
  - [ ] All code needed to run the app
  - [ ] `README.md` with step-by-step run instructions (or online link)
  - [ ] `.env.example` with key names only
  - [ ] No real `.env` / `PORTKEY_API_KEY` committed
- [ ] **`report.html`** — single self-contained file, 10–15 printed letter pages, images embedded
- [ ] **`slides.html`** — single self-contained reveal.js deck, max 10 slides, images embedded
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

- [ ] Token logs per run (`output/`)
- [ ] Screenshots: good runs, bad runs, defenses firing (`deliverables/screenshots/`)
- [ ] Real-user feedback (someone with dyslexia / a tutor / a parent)
- [ ] Sourced statistics on dyslexia prevalence and tutoring costs
