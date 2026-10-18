# WordWise

An AI reading-support website for people with dyslexia and other reading challenges: adjustable reading tools, "explain it my way" help on hard passages, and a guide to resources and tutors.

> 🚧 In development. The Reading Studio works end to end; the tutor directory, resources, and accounts come next.

**Who it's for:** students aged about 5 to 30 reading books (for school or fun), class materials, and lecture slides, especially readers with dyslexia. The focus is easier reading **and** better comprehension.

## Run it locally

You need Python 3.10 or newer. Setup takes about 2 minutes; it was tested from a fresh clone on 2026-10-15.

1. Clone this repo and open a terminal in the project folder:
   ```bash
   git clone https://github.com/abbyjaye19/WordWise.git
   cd WordWise
   ```
2. Put a `.env` file containing `PORTKEY_API_KEY=...` in this folder **or** the folder one level up. See `.env.example`. Without a key the site still runs and every non-AI reading tool still works; only the AI help buttons show a message.
3. (Recommended) Make a clean virtual environment so other packages on your computer can't interfere:
   - Windows:
     ```bash
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - Mac or Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
4. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the site. On Mac or Linux without a virtual environment, use `python3` instead of `python`:
   ```bash
   python app/main.py
   ```
6. Open **http://127.0.0.1:8050** in your browser. On first run the app creates its own local database (`data/wordwise.db`), so start by making an account with **Sign in → Create an account**.
7. To stop the site, press `Ctrl+C` in the terminal.

### Optional: load a demo account (recommended for graders)

To explore the library, folders, saved words, and reading goals without setting anything up, run this once (no API key needed, no AI calls):

```bash
python scripts/seed_demo.py
```

Then sign in with username **`demo`** and password **`wordwise-demo`**. You'll find:
- color-coded folders and subfolders holding the 4 sample readings, with highlights
- 7 saved words
- a week of reading time with a 3-day streak
- personal goals with due dates

Run `python scripts/seed_demo.py --reset` to start the demo account over. Other accounts are never touched.

If port 8050 is already in use, pick another one: `WORDWISE_PORT=8060 python app/main.py` (Mac/Linux), or on Windows run `set WORDWISE_PORT=8060` first.

## What works now

- **Reading Studio** (Reading Assistant in the menu):
  - Bring in a reading: upload a PDF, PowerPoint (`.pptx`), Word (`.docx`), or `.txt` file, paste text, or pick one of 4 samples (ages 5–8 up to college).
  - **Read along:** read aloud with the current sentence and word highlighted as they're spoken (choose word, sentence, or both). You can pause, go back a sentence, replay a sentence, or skip ahead, and change the speed (5 steps) while it plays. This uses the browser's built-in voices, so it's free and needs no key.
  - **Reading levels:** switch the whole reading between **Original**, **Simplified wording**, and **Detailed explanation**. The AI versions keep the meaning, are clearly marked as AI, and can show the original under each paragraph. Highlights always belong to the original text.
  - Tap a word to look it up, highlight it (3 marker colors), or start reading aloud from there. There's also a reading ruler and a one-paragraph focus mode.
  - **How did it go?** After reading, a quick check-in: how well you understood it (1–5) and what made it hard.
  - AI help at the reader's level (ages 5–8, 9–12, 13–17, 18+), adapted to what the student says they find hard:
    - **Word Coach:** meaning in this sentence, syllables, how to say it, synonyms, and an example.
    - **Explainer:** simpler words, an example, or step-by-step for a selected passage.
    - **Comprehension Coach:** big idea, key points, words to know, and "check yourself" questions with answers you tap to reveal.
  - AI answers are always labeled and shown beside the original text, and each has a 🔊 Listen button.
- **Accounts:** create an account with a username, email, and password, then sign in with either the username or the email.
- **Library** (My Dashboard): saved readings keep their highlights and stay saved through refreshes and across visits. You can:
  - make color-coded folders (7 colors) and subfolders up to 3 levels deep
  - move readings between folders
  - open a saved reading back in the studio
  - delete readings or folders (deleting a folder keeps its readings)
- **Reading insights** (My Dashboard): reading sessions (time per reading), the tools you use most, saved words, and your comprehension check-ins over time, plus what made reading hard.
- **What I want to work on** (My Dashboard): rate 8 areas (understanding what I read or hear, sounding out words, word meanings, spelling, speed, focus, remembering) and pick a top priority. Every AI helper and the AI Tutor use this to adapt, and the dashboard shows exactly how ("How WordWise adapts for you"). Every student reads differently, so there is no single "dyslexia mode".
- **Reading goals** (My Dashboard):
  - Pick a daily minutes goal, and see today's progress, your streak, this week's total, and a 7-day chart.
  - Keep a checklist of your own goals with optional due dates.
  - Reading time is counted only while a reading is open in the studio, the tab is visible, and you're active (or read-aloud is playing).
  - The server caps each time report.
- **My words:**
  - Press **☆ Save word** on any Word Coach answer to add it to your word bank, along with its meaning, syllables, synonyms, example, and the reading it came from.
  - Review your words on My Dashboard. You can search them, filter by "Still learning" or "I know it", use quiz mode to hide meanings, or listen to each one.
- **Download** a reading the way you set it up, with your highlights, font, size, spacing, and background: **Word (.docx)**, **Web page (.html)**, or **Print / Save as PDF**. Downloading doesn't need an account.
- **Resources:** 6 plain-language topics, each with a 🔊 Listen button and an audience filter (students, parents, adults, teachers). The topics are understanding dyslexia, signs and evaluation, accommodations, technology, parents, and adults. Every fact links to its source. The 35 sources are all from government health or education agencies, medical centers, a university research center, or established nonprofits. The content lives in `data/resources.json`, with the date the links were last checked.
- **AI Tutor** (`/ai-tutor`, plus the floating "Ask the AI Tutor" button on every page): a free chat tutor at the student's reading level.
  - It can see the reading that's open in the studio.
  - Press Enter to send, and each answer has a 🔊 Listen button.
  - It guides students through homework rather than doing it for them, and points to 988 or a trusted adult if a student says they're unsafe.
  - Chats survive refreshes within the browser tab.
  - **Finds your best settings with you:** tell it what's hard ("the lines blur", "the voice is too fast") or tap "Help me find my best reading settings". It suggests 1–3 setting changes, each with **Apply** and **Undo**, then asks how they feel so you can adjust together. It only suggests real settings (checked in code), using your current settings, your profile, and your check-ins.
- **Tutor Directory:** 15 legitimate places to find a tutor yourself, filterable by age, format, and cost:
  - official certified-specialist directories (IDA, CERI, Wilson, ALTA, Barton, ASHA)
  - free or low-cost programs (Children's Dyslexia Centers, New Haven Reads, Reading Partners, ProLiteracy)
  - Lindamood-Bell
  - general tutoring sites
  - Khan Academy

  It also has a "before you choose a tutor" checklist based on IDA guidance. WordWise doesn't list or check individual tutors. The data is in `data/tutoring_sites.json`.
- **Reading settings** (top right on every page): text size, font, spacing, background, contrast, line length, read-aloud speed, and read-along highlight. They apply on every page right away, are remembered in the browser, and are saved to your account when signed in (so they follow you to another device). **Clear all preferences** resets everything to the defaults.
- The other sections are placeholders for now.

## Test data

`data/sample/passages.json` holds 4 short original passages for quick testing. Any PDF, slides, or Word file can be uploaded for real use (limits: 15 MB, 60 pages/slides).

## Accounts and saved data

- Accounts, folders, and saved readings are stored in a local SQLite file, `data/wordwise.db`. It's created automatically on first run and is **not** committed to git, so a fresh clone starts with no accounts.
- Passwords are stored only as salted scrypt hashes. The login cookie is signed, HttpOnly, and SameSite=Lax, and lasts 30 days. The signing key is generated once into `data/.secret_key` (also not committed); you can set `WORDWISE_SECRET_KEY` to override it.
- Every library query is limited to the signed-in user. Sign-in pauses for 5 minutes after 5 wrong passwords.
- Students under 13 are asked to create an account with a parent or guardian.

## Deliverables

- `deliverables/report.html`: the full report, 14 printed pages. It's a single file with all images embedded.
- `deliverables/slides.html`: a 10-slide reveal.js deck that works offline. Use the arrow keys to move between slides, F for fullscreen, and Esc for an overview.
- `deliverables/agent_diagram.svg` and `deliverables/screenshots/`: the figures used in both.

Rebuild everything from the evidence files (report and slides need Pillow; screenshots need `pip install playwright` and Microsoft Edge):

```bash
python scripts/safety_eval.py
python scripts/capture_screenshots.py
python scripts/build_report.py
python scripts/build_slides.py
```

## Tokenomics (measured)

The numbers come from real calls; see `output/tokenomics/projections.md`. To reproduce them (needs a key, costs about $0.01):

```bash
python scripts/measure_tokenomics.py
python scripts/project_costs.py
python scripts/quality_check.py
```

- One study session is 16 AI calls (8 word lookups, 3 explains, 1 summary, 4 tutor messages). It costs **$0.00137**.
- That's **29% less** than before (**$0.00194**). Every helper now starts with the same reader-level guide (`prompts/reading_levels.md`), which pushes the fixed instructions past the 1,024-token minimum for prompt caching. About 89% of input tokens are then billed at the cached rate, which is 10x cheaper. A quality check found no loss, so this saving is free.
- When a classmate makes the exact same request, Portkey replays the stored answer for **$0**. The app reads `x-portkey-cache-status` and logs those calls as free.
- Reasoning effort "low" is used because "medium" costs 93% more per word lookup and is 65% slower.
- A typical student (12 sessions a month) costs about **$0.017/month**. That's **$1.65/month for 100 students** and **$165/month for 10,000** (AI only).

## AI cost and safety (so far)

- The only model used is `gpt-6-luna` via Portkey (`app/services/ai.py`). The app checks the model name on every reply.
- Every call is logged to `output/usage_log.jsonl` with input, cached, and output tokens and its cost (prices are in `data/prices.json`).
- **Daily spending cap:** `$2.00` by default. Change it with the environment variable `WORDWISE_DAILY_BUDGET_USD`. After the cap, the AI buttons pause and all the reading tools keep working.
- Repeat questions are answered from a cache, so they cost nothing.
- Uploaded text is wrapped in `<reading>` tags, and the prompts tell the model to treat it as content, never as instructions. Selections are capped at 3,000 characters and summaries at 40,000.

## Project layout

| Path | Purpose |
|---|---|
| `app/main.py` | Starts the website; holds the shared layout and callbacks |
| `app/config.py` | Paths, `.env` loading (this folder, then one folder up), and the model name |
| `app/pages/` | One file per page. A new file with `dash.register_page` becomes a new page |
| `app/components/` | Header, footer, settings panel, and shared building blocks |
| `app/services/` | `ai.py` (AI helpers, logging, budget), `documents.py` (file reading), `schemas.py` (AI answer shapes), `db.py` / `accounts.py` / `library.py` (accounts and saved readings), `export.py` (Word/HTML downloads) |
| `app/assets/` | `style.css` (design system), `studio.css` and `studio.js` (Reading Studio tools), `library.css` (accounts, library, print layout), `skyline.svg` (campus line art) |
| `prompts/` | System prompts: `shared_rules.md` plus one per AI helper |
| `data/sample/` | Small test dataset |
| `output/` | Token/cost logs and run traces |
| `tests/` | Tests, including safety checks |
| `deliverables/` | `report.html`, `slides.html`, and screenshots |
| `AI_prompts.md` | Log of every prompt given to the vibe coder |
| `PROJECT_REQUIREMENTS.md` | Course requirements checklist |
