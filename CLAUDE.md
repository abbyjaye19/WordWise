# WordWise — notes for the coding agent

- Follow `PROJECT_REQUIREMENTS.md` (course final project rules). Due 2026-10-26, 6:00 PM.
- **Log every user prompt verbatim in `AI_prompts.md`**, grouped by phase/feature, with a note when a follow-up was needed and what the first prompt lacked.
- **Model:** only `gpt-6-luna` via `PORTKEY_API_KEY` (course rule; overrides the `gpt-5.6-luna` note in the parent `agents.md`).
- Load `.env` from this folder first, then one folder up. Never commit `.env`.
- Log input / cached input / output tokens for every AI call to `output/` — the report needs real numbers.
- Visual style: follow the `wordwise-design` skill (`.claude/skills/wordwise-design/SKILL.md`) — navy + cream, formal but friendly. **Do not use black-pink** (overrides parent `agents.md`). Any mascot/illustration is built in HTML/CSS/SVG, not generated images.
- If using Dash: run with debug/auto-reload off; kill the whole process tree when stopping; no duplicate servers.
- **Audience:** students ~5–30 reading books (school or pleasure), school materials, and lecture slides. Goal is easier reading *and* comprehension. AI answers adapt to the "Who is reading?" level (5–8 / 9–12 / 13–17 / 18+).
- Reading Studio architecture: `assets/studio.js` draws the reading into `#reader` (Dash never manages its children) and runs TTS/highlighter/ruler/focus; it talks to Dash via `dash_clientside.set_props` on `word-request` and `selection-store`. AI helpers live in `app/services/ai.py` with prompts in `prompts/`.
- Accounts/library: SQLite at `data/wordwise.db` (gitignored), Flask session holds `uid`; always scope queries by user id. Highlights are a `{word_index: color}` map; word indexes = order of `\S+` runs across all paragraphs (must match `studio.js` and `services/export.py`).
- Tutor Directory lists organizations/directories only (user's choice), never individual tutors. Only add links verified to load and facts quoted from the source page; note the check date.
- AI Tutor chat: `app/pages/ai_tutor.py` + `prompts/ai_tutor.md`; reads the studio's reading via the shared session `doc-store`.
- Don't present WordWise as a summarizer — the twist is adaptive reading + "explain it my way" next to the original text + support navigator.
- AI explanations must be visually distinct from source text; never claim to diagnose dyslexia; only mark tutors "verified" if they actually are.
