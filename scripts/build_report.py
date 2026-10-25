"""Build deliverables/report.html: one self-contained file (all images embedded).

Usage, from the project folder:
    python scripts/build_report.py

Numbers come straight from the evidence files, so the report always matches them:
  output/tokenomics/summary.json, projections.json, quality_check.md
  output/safety/results.json
  deliverables/screenshots/*.png, deliverables/agent_diagram.svg
User-testing results go in deliverables/user_testing.json (see USER_TESTING below).
"""

from __future__ import annotations

import base64
import html
import io
import json
from datetime import date
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "deliverables" / "screenshots"
OUT = ROOT / "deliverables" / "report.html"
TOK = ROOT / "output" / "tokenomics"
SAFETY = ROOT / "output" / "safety" / "results.json"
USER_TESTING = ROOT / "deliverables" / "user_testing.json"

AUTHOR = "Abby Jaye"
REPO = "https://github.com/abbyjaye19/WordWise"
E = html.escape


# ---------- helpers ----------

def img(name: str, alt: str, width: int = 1300, caption: str | None = None, cls: str = "", crop: int | None = None) -> str:
    """Embed a screenshot as a compressed JPEG data URI. crop keeps only the top `crop` pixels."""
    im = Image.open(SHOTS / f"{name}.png").convert("RGB")
    if crop and im.height > crop:
        im = im.crop((0, 0, im.width, crop))
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    data = base64.b64encode(buf.getvalue()).decode()
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return f'<figure class="{cls}"><img src="data:image/jpeg;base64,{data}" alt="{E(alt)}">{cap}</figure>'


def svg_inline(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    return s[s.index("<svg"):]


def money(x: float, places: int = 5) -> str:
    return f"${x:,.{places}f}"


def bar_chart(rows: list[tuple[str, float, str]], title: str, unit_fmt) -> str:
    """Single-series horizontal bar chart (inline SVG). Colors validated against the cream surface."""
    w, left, bar_h, gap = 680, 190, 26, 18
    top = max(v for _, v, _ in rows) or 1
    h = len(rows) * (bar_h + gap) + 30
    parts = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{E(title)}">']
    for i, (label, v, note) in enumerate(rows):
        y = 10 + i * (bar_h + gap)
        bw = max((w - left - 230) * v / top, 2 if v else 0)  # leave room for the value label
        parts.append(f'<text x="{left - 10}" y="{y + 17}" text-anchor="end" class="cl">{E(label)}</text>')
        parts.append(f'<rect x="{left}" y="{y}" width="{bw:.1f}" height="{bar_h}" rx="4" fill="#1B3366"/>')
        parts.append(f'<text x="{left + bw + 8:.1f}" y="{y + 17}" class="cv">{E(unit_fmt(v))}{(" · " + E(note)) if note else ""}</text>')
    parts.append(f'<line x1="{left}" y1="4" x2="{left}" y2="{h - 20}" stroke="#E6DCC6" stroke-width="1"/>')
    parts.append("</svg>")
    return "".join(parts)


# ---------- evidence ----------

summary = json.loads((TOK / "summary.json").read_text(encoding="utf-8"))
proj = json.loads((TOK / "projections.json").read_text(encoding="utf-8"))
safety = json.loads(SAFETY.read_text(encoding="utf-8"))
st = summary["settings"]
before, after = st["before"]["run2"], st["after"]["run2"]
klass = st["class_repeat"]["run2"]
wl, wm = after["per_feature"]["word_help"], st["effort_med"]["run2"]["per_feature"]["word_help"]
prices = summary["prices_per_1m"]
saving = 1 - after["session_cost_usd"] / before["session_cost_usd"]
monthly = proj["monthly_usd"]
typ_after = monthly["After (shared guide, cached)"]["typical"]
typ_before = monthly["Before (short prompts, no caching)"]["typical"]
cached_share = after["cached_input_tokens"] / after["input_tokens"]
user_testing = json.loads(USER_TESTING.read_text(encoding="utf-8")) if USER_TESTING.exists() else None


# ---------- sections ----------

def sec_title() -> str:
    return f"""
<header class="title-page">
  <p class="eyebrow">MGT 409 · AI Foundations for Managers · Final project</p>
  <h1>WordWise</h1>
  <p class="subtitle">Reading support that fits you: an AI reading studio for students with dyslexia and other reading challenges.</p>
  <dl class="meta">
    <dt>Author</dt><dd>{AUTHOR}</dd>
    <dt>Repository</dt><dd><a href="{REPO}">{REPO}</a></dd>
    <dt>App</dt><dd>Runs locally from the repository in about 2 minutes (tested from a fresh clone); see the README. Demo login: <code>demo</code> / <code>wordwise-demo</code> after <code>python scripts/seed_demo.py</code>.</dd>
    <dt>Date</dt><dd>{date.today():%B %d, %Y}</dd>
  </dl>
  <p class="oneliner"><strong>In one sentence:</strong> WordWise lets a student bring in any reading (a PDF, lecture slides, or a Word file), make it easier to see and hear, and get AI explanations pitched at their age, shown right next to the original text, with quick questions that check they understood it.</p>
  {img("trace_0_home", "WordWise home page with navy hero, campus skyline, and feature cards", 1300, "Figure 1. The WordWise home page.", cls="w90")}
</header>"""


def sec_motivation() -> str:
    return f"""
<section>
<h2>1. Motivation</h2>
<h3>Why I built it</h3>
<p>This project comes from my own experience. I have double-deficit dyslexia: difficulty with both phonological awareness (working with the sounds in words) and rapid naming (quickly retrieving the names of familiar symbols such as letters), a combination associated with more severe reading difficulties than either deficit alone.<sup><a href="#s13">13</a></sup> Learning to read, and especially understanding what I read, was hard, and reading and listening comprehension remain the areas I work hardest at. In college I worked with a reading specialist whose sessions did for me much of what WordWise now does: helping me get through assigned readings and genuinely understand them. That experience showed me how valuable this kind of support is, and how much a tool that provides it would have helped me when I was first learning to read. It was also difficult to find trustworthy resources; they were scattered across many sites. WordWise is designed to be the home base I was looking for: help with a student's own readings, plus vetted information and routes to human specialists. Because no two readers with dyslexia struggle in the same way, it also adapts to what each student reports finding hard.</p>
<h3>Who has the problem</h3>
<p>Students from about age 5 to 30 who find reading hard, especially students with dyslexia. Prevalence depends on the definition used. The International Dyslexia Association reports that 6–7% of U.S. students are classified as having a learning disability and that about 85% of them have a primary disability in reading and language processing, which implies roughly 5–6% of students are formally identified; it adds that "perhaps as many as 15–20%" of the population have some symptoms of dyslexia, most of whom never qualify for special education.<sup><a href="#s12">12</a></sup> Other estimates fall in the same range (5–17.5% per Understood.org; up to 20% per the Yale Center for Dyslexia &amp; Creativity).<sup><a href="#s1">1</a>,<a href="#s2">2</a></sup> The gap between the identified and symptomatic populations is the core opportunity: most struggling readers receive no formal support.</p>
<p>Dyslexia makes it hard to connect letters to the sounds they make, so reading is slow and effortful. It has nothing to do with intelligence.<sup><a href="#s1">1</a>,<a href="#s3">3</a></sup> The National Institutes of Health lists common signs as trouble sounding out words, spelling mistakes, slow reading, and trouble understanding what was just read.<sup><a href="#s4">4</a></sup> That last one matters most for school: when decoding takes all of a student's effort, comprehension suffers.</p>
<h3>How they handle it today</h3>
<ul>
  <li><strong>Specialized tutoring.</strong> The most effective help is intensive instruction from specially trained teachers.<sup><a href="#s5">5</a></sup> The International Dyslexia Association notes that "specialized instruction is expensive" and that many families can't find it.<sup><a href="#s6">6</a></sup></li>
  <li><strong>School accommodations</strong> such as extra time and audio text, through an IEP or 504 plan.<sup><a href="#s7">7</a></sup> These mostly apply at school, not at home on a Tuesday night with a chapter to read.</li>
  <li><strong>Separate tools</strong>: a text-to-speech app, an online dictionary, a general chatbot, a search engine for resources. Each solves one piece, and a struggling reader has to juggle all of them.</li>
</ul>
<h3>What it costs them</h3>
<p>The cost is time and confidence. A student who reads slowly spends far longer on the same assignment, and without help in the moment they may finish the reading without understanding it. Families pay for tutoring if they can, and reading difficulties can grow more serious as schoolwork gets harder.<sup><a href="#s11">11</a></sup> Adults are affected too: dyslexia is lifelong, and many adults were never diagnosed.<sup><a href="#s2">2</a></sup></p>
</section>"""


def sec_new() -> str:
    return f"""
<section>
<h2>2. What is new</h2>
<p>Pieces of WordWise exist elsewhere: browsers can read text aloud, dictionaries define words, accessible-book libraries like Bookshare and the Library of Congress provide accessible ebooks and audiobooks,<sup><a href="#s8">8</a></sup> and general chatbots can explain things. What is new is putting the pieces together around the student's own reading and around <em>understanding</em>, not just decoding:</p>
<table>
<thead><tr><th>Typical alternative</th><th>What WordWise does differently</th><th>Why it matters</th></tr></thead>
<tbody>
<tr><td>Text-to-speech app</td><td>Read-aloud with word-by-word highlighting <em>inside</em> the same view where the student highlights, looks up words, and asks for help</td><td>No switching between apps; the student keeps their place</td></tr>
<tr><td>Dictionary</td><td>The Word Coach explains the word <strong>as used in this sentence</strong>, at the student's age level, with syllables, how to say it, simpler synonyms, and an example</td><td>Dictionaries list every meaning; a struggling reader needs the one that fits</td></tr>
<tr><td>General chatbot</td><td>Help appears <strong>next to the original text</strong> (never replacing it), is pitched at four reader levels (5–8, 9–12, 13–17, 18+), guides homework instead of doing it, and checks understanding with "check yourself" questions</td><td>Builds comprehension and keeps the student doing the reading</td></tr>
<tr><td>Summarizer</td><td>A summary is one small part: the Comprehension Coach adds key words and three questions whose answers are hidden until tapped</td><td>A summary alone can replace reading; questions make the student engage with it</td></tr>
<tr><td>Separate resource searches</td><td>A built-in resource hub from trusted medical, government, and university sources, plus a directory of certified tutoring organizations and free programs</td><td>Help is easier to find, and the sources are trustworthy</td></tr>
</tbody></table>
<p>WordWise also keeps the student's work: saved readings with highlights, color-coded folders, a word bank, and reading goals. And it is cheap enough to give away: about <strong>{money(typ_after['1'], 3)} per student per month</strong> in AI costs (Section 4).</p>
</section>"""


def sec_agents() -> str:
    pf = after["per_feature"]
    return f"""
<section>
<h2>3. The agents</h2>
<p>WordWise has four AI helpers. Each is a single, focused agent with its own instructions and a fixed answer format. None has tools or can take actions; each button press makes exactly one model call. Everything that doesn't need AI (read-aloud, highlighting, the reading ruler, folders, exports) runs without it, which keeps costs low and the app usable even when AI is unavailable.</p>
<div class="diagram">{svg_inline(ROOT / "deliverables" / "agent_diagram.svg")}<p class="figcap">Figure 2. How the agents are organized. Every request passes through one guard layer and one shared, cached prompt.</p></div>
<table>
<thead><tr><th>Agent</th><th>Role</th><th>Input → output</th><th>Measured cost / call</th></tr></thead>
<tbody>
<tr><td><strong>Word Coach</strong></td><td>Explain one tapped word in context</td><td>word + its sentence + reader level → <code>WordHelp</code>: syllables, say-it, part of speech, meaning here, synonyms, example</td><td>{money(pf['word_help']['avg_cost_usd'], 6)}</td></tr>
<tr><td><strong>Explainer</strong></td><td>Re-explain a selected passage</td><td>passage + mode (simpler / example / steps) → <code>Explanation</code>: heading, points, tricky words</td><td>{money(pf['explain']['avg_cost_usd'], 6)}</td></tr>
<tr><td><strong>Comprehension Coach</strong></td><td>Summarize and check understanding</td><td>reading (or one page) → <code>Summary</code>: big idea, key points, words to know, 3 questions with answers</td><td>{money(pf['summarize']['avg_cost_usd'], 6)}</td></tr>
<tr><td><strong>AI Tutor</strong></td><td>Free-form chat tutor</td><td>last 12 chat turns + the open reading → short answer</td><td>{money(pf['tutor_chat']['avg_cost_usd'], 6)}</td></tr>
</tbody></table>
<h3>Model choice</h3>
<p>Every helper uses <code>gpt-6-luna</code> through the course's Portkey gateway. It is the course's required model, and it fits the job: the tasks are short, well-defined language tasks, and the model's structured-output support lets three helpers return a fixed JSON shape that the app renders reliably (and that also makes prompt injection harder, Section 5). Reasoning effort is set to "low": at "medium", a word lookup cost {100 * (wm['avg_cost_usd'] / wl['avg_cost_usd'] - 1):.0f}% more and took {100 * (wm['avg_seconds'] / wl['avg_seconds'] - 1):.0f}% longer with no visible gain for these short tasks. The app also checks that every reply really came from <code>gpt-6-luna</code> and stops otherwise.</p>
<h3>A traced run</h3>
<p>One student session, captured from the running app with the demo account (reader level 13–17):</p>
<ol class="trace">
<li><strong>Bring in a reading and make it comfortable.</strong> The student opens "How Plants Make Food", turns on large text and wide spacing, and highlights two words. No AI is used.{img("trace_1_reading_studio", "Reading Studio with large text, wide spacing, and two highlighted words", 1300, cls="w80")}</li>
<li><strong>Tap a word → Word Coach.</strong> Tapping "chlorophyll" sends the word, its sentence, and the reader level. The answer comes back as a fixed <code>WordHelp</code> object and appears in a labeled panel beside the text, with Listen and Save word buttons.</li>
<li><strong>Select a passage → Explainer.</strong> The student drags across a paragraph and taps "Make it simpler."</li>
<li><strong>Sum it up → Comprehension Coach.</strong> The big idea, key points, words to know, and three questions whose answers stay hidden until tapped.
<div class="grid3">{img("trace_2_word_coach", "Word Coach answer for chlorophyll", 520, "Word Coach")}{img("trace_3_explainer", "Explainer answer in simpler words", 520, "Explainer")}{img("trace_4_comprehension_coach", "Summary with check-yourself questions", 520, "Comprehension Coach (top part)", crop=1500)}</div></li>
<li><strong>Still stuck → AI Tutor.</strong> The tutor sees the open reading and answers in plain words, citing the reading.{img("trace_5_ai_tutor", "AI Tutor chat answering why plants need sunlight", 1300, cls="w70", crop=820)}</li>
<li><strong>Progress is saved.</strong> Reading time counts toward a daily goal, saved words go to a word bank, and readings live in color-coded folders.{img("trace_6_reading_goals", "Reading goals with a 7-day chart and personal goals", 1300, cls="w80", crop=1250)}</li>
</ol>
</section>"""


def sec_tokenomics() -> str:
    pf = after["per_feature"]
    rows_pf = "".join(
        f"<tr><td>{E(name)}</td><td>{v['avg_input']:,}</td><td>{v['avg_cached']:,}</td><td>{v['avg_output']}</td><td>{money(v['avg_cost_usd'], 6)}</td><td>{v['avg_seconds']} s</td></tr>"
        for name, v in (("Word Coach", pf["word_help"]), ("Explainer", pf["explain"]), ("Comprehension Coach", pf["summarize"]), ("AI Tutor", pf["tutor_chat"])))
    m_rows = ""
    for scen, label in (("Before (short prompts, no caching)", "Before"), ("After (shared guide, cached)", "After (used)")):
        for usage in ("light", "typical", "heavy"):
            v = monthly[scen][usage]
            m_rows += f"<tr><td>{label}</td><td>{usage} ({proj['assumptions']['sessions_per_month'][usage]} sessions)</td><td>{money(v['1'], 3)}</td><td>{money(v['100'], 2)}</td><td>{money(v['10000'], 2)}</td></tr>"
    chart = bar_chart([
        ("Before: short prompts", before["session_cost_usd"], "never cached"),
        ("After: cached guide", after["session_cost_usd"], f"{saving:.0%} cheaper"),
        ("Classmate repeats it", klass["session_cost_usd"], f"{klass['gateway_hits']} of {klass['calls']} replayed"),
    ], "Measured cost per study session", lambda v: money(v, 5))
    return f"""
<section>
<h2>4. Tokenomics</h2>
<p>All numbers below are measured from real calls by <code>scripts/measure_tokenomics.py</code> (raw data in <code>output/tokenomics/</code>). Prices for <code>gpt-6-luna</code> per million tokens: input ${prices['input_per_1m']:.2f}, cached input ${prices['cached_input_per_1m']:.2f}, cache write ${prices['cache_write_per_1m']:.3f}, output ${prices['output_per_1m']:.2f}.</p>
<p>A <strong>study session</strong> is what a student does in one sitting: 8 word lookups, 3 explain requests, 1 summary, and 4 AI Tutor messages (16 model calls).</p>
<h3>Per run and per session</h3>
<table>
<thead><tr><th>Setting</th><th>Input tokens</th><th>Cached input</th><th>Output (reasoning)</th><th>Cost / session</th></tr></thead>
<tbody>
<tr><td>Before: short prompts</td><td>{before['input_tokens']:,}</td><td>{before['cached_input_tokens']:,}</td><td>{before['output_tokens']:,} ({before['reasoning_tokens']})</td><td>{money(before['session_cost_usd'])}</td></tr>
<tr><td><strong>After: cached shared guide (used)</strong></td><td>{after['input_tokens']:,}</td><td>{after['cached_input_tokens']:,}</td><td>{after['output_tokens']:,} ({after['reasoning_tokens']})</td><td><strong>{money(after['session_cost_usd'])}</strong></td></tr>
<tr><td>Same session repeated by a classmate</td><td>{klass['input_tokens']:,}</td><td>replayed</td><td>replayed</td><td>{money(klass['session_cost_usd'])}</td></tr>
</tbody></table>
{chart}
<table>
<thead><tr><th>Agent (after, warm)</th><th>Avg input</th><th>Avg cached</th><th>Avg output</th><th>Avg cost / call</th><th>Avg time</th></tr></thead>
<tbody>{rows_pf}</tbody></table>
<h3>Per user per month, and at scale</h3>
<p>Usage is an assumption: a light user has 4 sessions a month, a typical user 12 (three a week), and a heavy user 30. AI cost only; read-aloud uses the browser's free built-in voices and the reading tools use no AI.</p>
<table>
<thead><tr><th>Prompts</th><th>Usage</th><th>1 user / month</th><th>100 users</th><th>10,000 users</th></tr></thead>
<tbody>{m_rows}</tbody></table>
<p>A typical student costs about <strong>{money(typ_after['1'], 3)} a month</strong>, so 10,000 typical students cost about <strong>{money(typ_after['10000'], 0)} a month</strong>. Even a heavy user (30 sessions a month) costs about {money(monthly["After (shared guide, cached)"]["heavy"]["1"] * 12, 2)} a year.</p>
<h3>Cost-cutting steps, with evidence</h3>
<ol>
<li><strong>Make the fixed prompt cacheable.</strong> The first logs showed 0 cached tokens on every call. A test found why: with the same instructions sent repeatedly, prompts of about 720 tokens were never cached, while prompts of about 1,900 tokens were cached from the second call on, consistent with the documented 1,024-token minimum. Our prompts were about 650 tokens. Every helper now starts with the same reader-level guide (<code>prompts/reading_levels.md</code>), which pushes the fixed part past the minimum. Input tokens doubled, but {cached_share:.0%} of them are now billed at the cached rate (10× cheaper), so a session costs <strong>{saving:.0%} less</strong> ({money(before['session_cost_usd'])} → {money(after['session_cost_usd'])}).</li>
<li><strong>Count Portkey's replay cache.</strong> The course gateway replays identical requests from its cache without calling the model (response header <code>x-portkey-cache-status: HIT</code>). When a classmate looked up the same words in the same reading, all {klass['calls']} calls were replayed for $0. The app reads that header and logs replays as free, which matters for classes reading the same assignment.</li>
<li><strong>Low reasoning effort.</strong> Medium effort made a word lookup {100 * (wm['avg_cost_usd'] / wl['avg_cost_usd'] - 1):.0f}% more expensive ({money(wl['avg_cost_usd'], 6)} → {money(wm['avg_cost_usd'], 6)}) and slower.</li>
<li><strong>No AI where it isn't needed</strong>, an in-app answer cache for repeat clicks, input caps (3,000 characters per selection, 40,000 per summary, last 12 chat turns), and a daily spending cap.</li>
</ol>
<h3>Trade-offs</h3>
<p>Did the longer prompt change quality? <code>scripts/quality_check.py</code> asked the Word Coach about the same 6 words at ages 5–8 and 18+, with and without the guide. Average sentence length for ages 5–8 went from 9.3 to 8.9 words, and no answer used filler openers either way; some answers got clearer (for example, "Stomata are tiny holes in leaves" instead of a 10-word sentence). So the saving did not cost quality. The same check found a real limit, listed in Section 7: only 2 of 6 answers for ages 5–8 kept every sentence under 10 words.</p>
<p>One more trade-off: the default daily spending cap ($2) protects a class demo, but 10,000 typical students would spend about {money(typ_after['10000'] / 30, 2)} a day, so the cap must be raised (one setting) or turned into per-student limits at that scale.</p>
</section>"""


def sec_safety() -> str:
    passed = sum(r["passed"] for r in safety)
    rows = "".join(
        f"<tr><td>{E(r['risk'])}</td><td>{E(r['attack'])}</td><td>{E(r['defense'])}</td><td>{'Pass' if r['passed'] else 'Fail'}</td></tr>" for r in safety)
    return f"""
<section>
<h2>5. Safety</h2>
<p>WordWise is for students as young as 5, so safety covers both the AI and the app around it. Defenses are layered: the provider's content filter, our own guard layer, careful prompts, and app-level controls. <code>scripts/safety_eval.py</code> attacks the app and records what happened; the latest run passed <strong>{passed} of {len(safety)}</strong> checks (every AI reply is saved in <code>output/safety/results.md</code>). On the first run two checks failed, but reading the replies showed the AI had answered correctly ("The passage doesn’t say...") and my checker had missed the curly apostrophe; I fixed the checker, not the AI.</p>
<table class="small">
<thead><tr><th>Risk</th><th>Attack tried</th><th>Defense</th><th>Result</th></tr></thead>
<tbody>{rows}</tbody></table>
<h3>Defenses working</h3>
<div class="grid2">
{img("safety_1_injected_reading", "A reading with a hidden instruction to the AI outlined in red", 900, "A planted instruction inside an uploaded reading tells the AI to give fake test answers and ask for the student's address.")}
{img("safety_2_injection_ignored_by_tutor", "The AI Tutor summarizes the bees reading normally", 900, "The AI Tutor treats it as text, not orders: it summarizes the reading and does neither.")}
{img("safety_3_content_filter_block", "Safety filter message", 600, "The same attack against the summary is blocked upstream by Azure's content filter; the student sees an honest message.")}
{img("safety_4_essay_request_redirected", "Tutor offers an essay plan instead of writing it", 900, "Asked to write a graded essay, the tutor offers a plan instead.")}
{img("safety_5_wellbeing_response", "Tutor responds with care and gives 988 and 911", 900, "A student in distress gets a caring reply that names a trusted adult, 988, and 911.")}
{img("safety_7_password_lockout", "Sign-in locked after repeated wrong passwords", 600, "Password guessing is paused after 5 misses.")}
{img("safety_8_spending_cap", "Daily AI limit message", 600, "At the daily spending cap, AI help pauses; reading tools keep working.")}
</div>
{img("safety_6_other_account_blocked", "Another account cannot open a saved reading", 1300, "Another student cannot open someone else's saved reading, even with its link. Every library query is filtered by the signed-in user.", cls="w70", crop=420)}
<p>Other protections: passwords are stored only as salted scrypt hashes; the login cookie is signed and not readable by page scripts; accounts and saved work stay in a local database the AI never sees; students under 13 are asked to create an account with a parent; AI help is always labeled and shown beside the original; and WordWise never claims to diagnose dyslexia.</p>

</section>"""


SURVEY_ITEMS = [
    ("easy_to_use", "WordWise was easy to use"),
    ("right_level", "Explanations were at the right level"),
    ("helped_understand", "WordWise helped me understand the reading"),
    ("less_tiring", "Reading felt less tiring"),
    ("ai_help_distinct", "I could tell the AI help apart from the reading"),
    ("would_use", "I would use WordWise for my own reading"),
]


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(round(seconds % 60)):02d}"


def user_testing_html(ut: dict) -> str:
    """Observed sessions (who, what they did, feedback, what changed) plus, if any tester did the timed
    protocol, the with-vs-without table and survey averages. Nothing is shown that wasn't measured."""
    ts = ut["testers"]
    n = len(ts)
    timed = [t for t in ts if t.get("time_with_s") is not None]
    out = [f"<h3>Real users ({n} tester{'s' if n != 1 else ''}, {E(ut.get('dates', ''))})</h3>",
           f"<p>{E(ut.get('method', ''))}</p>"]
    rows = "".join(
        f"<tr><td>{E(t['id'])}</td><td>{E(t['who'])}</td><td>{E(t.get('what_they_did', ''))}</td>"
        f"<td><ul>{''.join(f'<li>{E(p)}</li>' for p in t.get('problems', []))}</ul></td>"
        f"<td><ul>{''.join(f'<li>{E(c)}</li>' for c in t.get('changes', []))}</ul></td></tr>"
        for t in ts)
    out.append("<table class=\"ut-table\"><thead><tr><th>Tester</th><th>Who</th><th>What they did</th><th>Problems found</th>"
               f"<th>What we changed</th></tr></thead><tbody>{rows}</tbody></table>")
    quotes = "".join(f"<li>“{E(q)}” ({E(t['id'])})</li>" for t in ts for q in t.get("quotes", []))
    if quotes:
        out.append(f"<h3>In their words</h3><ul>{quotes}</ul><p class=\"note\">Quotes lightly edited for spelling.</p>")
    if timed:
        m = len(timed)
        avg = lambda key: sum(t[key] for t in timed) / m  # noqa: E731
        tw, tn, sw, sn = avg("time_with_s"), avg("time_without_s"), avg("score_with"), avg("score_without")
        trows = "".join(
            f"<tr><td>{E(t['id'])}</td><td>{mmss(t['time_without_s'])} ({t['passage_without']})</td><td>{mmss(t['time_with_s'])} ({t['passage_with']})</td>"
            f"<td>{t['score_without']:g} / 3</td><td>{t['score_with']:g} / 3</td></tr>" for t in timed)
        survey = "".join(f"<tr><td>{E(label)}</td><td>{sum(t['survey'][key] for t in timed) / m:.1f} / 5</td></tr>" for key, label in SURVEY_ITEMS)
        out.append(f"""<h3>Timed comparison ({m} tester{'s' if m != 1 else ''})</h3>
<table><thead><tr><th>Tester</th><th>Time without</th><th>Time with</th><th>Score without</th><th>Score with</th></tr></thead><tbody>{trows}
<tr><td><strong>Average</strong></td><td><strong>{mmss(tn)}</strong></td><td><strong>{mmss(tw)}</strong></td><td><strong>{sn:.1f} / 3</strong></td><td><strong>{sw:.1f} / 3</strong></td></tr></tbody></table>
<p>With WordWise, reading time changed by <strong>{(tw - tn) / tn:+.0%}</strong> and comprehension by <strong>{sw - sn:+.1f}</strong> points out of 3.</p>
<table><thead><tr><th>Survey statement</th><th>Average (1–5)</th></tr></thead><tbody>{survey}</tbody></table>""")
    else:
        out.append("<p><strong>What this evidence does and doesn't show.</strong> These sessions show that new users could use WordWise without instructions and they found real usability problems, each of which was fixed. They do not measure reading time or comprehension gains: no tester did the timed with/without protocol, all three know the author, and none is currently a struggling student reader (one tested on behalf of a brother with reading-comprehension difficulties). A timed pilot with students in the target group is the next step (protocol ready in <code>deliverables/user_testing/testing_kit.html</code>).</p>")
    return "\n".join(out)


def sec_impact() -> str:
    if user_testing:
        testing = user_testing_html(user_testing)
    else:
        testing = """<div class="pending"><strong>Pending: real-user testing.</strong> This section will report 1–3 real users (for example a student with dyslexia, a parent, or a tutor): what they read, how long it took with and without WordWise, which tools they used, and their own words. Add results to <code>deliverables/user_testing.json</code> and rebuild.</div>"""
    return f"""
<section>
<h2>6. Impact</h2>
<h3>Reach</h3>
<p>Using the IDA figures,<sup><a href="#s12">12</a></sup> a school of 1,000 students has roughly 50–60 formally identified students and up to 150–200 with some symptoms of dyslexia, most of whom receive no formal support. Because the reading tools need no AI and the AI costs about {money(typ_after['1'], 3)} per typical student per month, a whole school of 1,000 typical users would cost about {money(typ_after['1'] * 1000, 0)} a month in AI.</p>
<h3>Money</h3>
<p>Specialized instruction is effective but expensive and hard to find.<sup><a href="#s5">5</a>,<a href="#s6">6</a></sup> WordWise doesn't replace a trained tutor. It makes the hours between tutoring sessions more productive, and its Tutor Directory points families to free and low-cost options, such as Children's Dyslexia Centers ("minimal or no cost") and New Haven Reads (free one-on-one tutoring, grades 1–12).<sup><a href="#s9">9</a>,<a href="#s10">10</a></sup></p>
<h3>Time and quality</h3>
<p>Measured in the app: an answer arrives in about {wl['avg_seconds']} seconds for a word and {after['per_feature']['summarize']['avg_seconds']} seconds for a full summary with questions. The student never leaves the page, and the answer matches their sentence and age level. Read-aloud with word highlighting starts instantly and is free.</p>
{testing}
<h3>Honest limits on these claims</h3>
<p>{"The user tests are a small pilot of observed sessions, not a controlled study: they show usability, not reading gains, and long-term gains would need a much longer study." if user_testing else "Time savings for real students are not yet measured, and reading gains would need a much longer study."} The reach estimate depends on prevalence figures that experts disagree on.</p>
</section>"""


def sec_limits() -> str:
    return """
<section>
<h2>7. Limits and next steps</h2>
<h3>Limits</h3>
<ul>
<li><strong>Age-level control isn't perfect.</strong> Only 2 of 6 Word Coach answers for ages 5–8 kept every sentence under 10 words (Section 4).</li>
<li><strong>Scanned PDFs can't be read</strong>: there is no text recognition (OCR) yet.</li>
<li><strong>Read-aloud quality depends on the browser's voices</strong>, and word highlighting needs voices that report word boundaries.</li>
<li><strong>Local only.</strong> Accounts live in a local database; hosting would need a managed database, backups, and a privacy review, especially for students under 13.</li>
<li><strong>Safety checks use simple text rules</strong> plus human review of the saved replies; a larger attack set and an automated grader would be stronger.</li>
<li><strong>The daily spending cap is global</strong>, not per student.</li>
<li><strong>Not a diagnosis or a tutor.</strong> WordWise supports reading; it doesn't replace evaluation or specialized instruction.</li>
</ul>
<h3>Next steps</h3>
<ol>
<li>Test with real students, parents, and tutors, and measure time per assignment and quiz accuracy with and without WordWise.</li>
<li>Tighten age-level answers (a short self-check against the length target before showing an answer).</li>
<li>Add OCR for scanned pages and photos of book pages.</li>
<li>Host it with per-student spending limits, a managed database, and a teacher view for a class reading the same assignment (which Portkey's replay cache makes cheaper).</li>
<li>Grow the word bank into spaced-repetition practice.</li>
</ol>
</section>"""


SOURCES = [
    ("Yale Center for Dyslexia & Creativity, “Dyslexia FAQ”", "https://dyslexia.yale.edu/dyslexia/dyslexia-faq/"),
    ("Understood.org, “Dyslexia in adults”", "https://www.understood.org/en/articles/dyslexia-in-adults"),
    ("NHS (UK), “Dyslexia”", "https://www.nhs.uk/conditions/dyslexia/"),
    ("NIH NICHD, “What are the symptoms of reading disorders?”", "https://www.nichd.nih.gov/health/topics/reading/conditioninfo/symptoms"),
    ("NIH NICHD, “What are the treatments for reading disorders?”", "https://www.nichd.nih.gov/health/topics/reading/conditioninfo/treatment"),
    ("International Dyslexia Association, “Evaluating professionals”", "https://dyslexiaida.org/evaluating-professionals-fact-sheet/"),
    ("Understood.org, “The difference between IEPs and 504 plans”", "https://www.understood.org/en/articles/the-difference-between-ieps-and-504-plans"),
    ("Library of Congress NLS, “Eligibility”", "https://www.loc.gov/nls/about/eligibility-for-nls-services/"),
    ("Children's Dyslexia Centers, “Services”", "https://childrensdyslexiacenters.org/get-help/services/"),
    ("New Haven Reads, “Tutoring”", "https://newhavenreads.org/programs/tutoring"),
    ("International Dyslexia Association, “Dyslexia assessment: what is it and how can it help?”", "https://dyslexiaida.org/dyslexia-assessment-what-is-it-and-how-can-it-help/"),
    ("International Dyslexia Association, “Dyslexia basics”", "https://dyslexiaida.org/dyslexia-basics/"),
    ("Norton et al., “Functional neuroanatomical evidence for the double-deficit hypothesis of developmental dyslexia,” Neuropsychologia 61 (2014)", "https://pmc.ncbi.nlm.nih.gov/articles/PMC4339699/"),
]


def sec_sources() -> str:
    items = "".join(f'<li id="s{i}">{E(t)}. <a href="{u}">{u}</a></li>' for i, (t, u) in enumerate(SOURCES, 1))
    return f'<section class="sources"><h2>Sources</h2><p>All links checked October 2026.</p><ol>{items}</ol></section>'


CSS = """
:root { --navy:#0F1F3D; --navy7:#1B3366; --navy5:#3C5A8F; --navy1:#DCE3F0; --cream:#FBF8F1; --cream1:#F4EEE1; --cream3:#E6DCC6; --brass:#B08D57; --muted:#4A5874; }
* { box-sizing:border-box; }
body { margin:0; background:var(--cream); color:var(--navy); font-family:"Atkinson Hyperlegible", Verdana, sans-serif; font-size:10.5pt; line-height:1.5; }
main { max-width:8.5in; margin:0 auto; padding:0.6in 0.75in; background:var(--cream); }
h1, h2, h3 { font-family:"Libre Baskerville", Georgia, serif; color:var(--navy7); line-height:1.25; }
h1 { font-size:34pt; margin:0 0 6px; }
h2 { font-size:19pt; margin:28px 0 10px; padding-bottom:6px; border-bottom:2px solid var(--brass); }
h3 { font-size:13pt; margin:18px 0 6px; }
p, li { max-width:100%; }
a { color:var(--navy7); }
code { font-size:.9em; background:var(--cream1); padding:1px 4px; border-radius:3px; }
em { font-style:normal; font-weight:700; }
.eyebrow { color:var(--brass); font-weight:700; letter-spacing:.04em; margin:0; font-size:10pt; }
.subtitle { font-size:14pt; color:var(--navy5); margin:0 0 16px; }
.meta { display:grid; grid-template-columns:110px 1fr; gap:4px 12px; margin:14px 0; font-size:10.5pt; }
.meta dt { font-weight:700; } .meta dd { margin:0; }
.oneliner { background:var(--navy1); border-left:5px solid var(--navy5); padding:10px 14px; border-radius:8px; }
table { width:100%; border-collapse:collapse; margin:10px 0 14px; font-size:9.8pt; line-height:1.4; }
th { background:var(--navy7); color:var(--cream); text-align:left; padding:6px 8px; }
td { border-bottom:1px solid var(--cream3); padding:6px 8px; vertical-align:top; }
table.ut-table { font-size:8.8pt; line-height:1.3; } table.ut-table td { padding:4px 6px; } table.ut-table ul { margin:0; padding-left:14px; } table.ut-table li { margin:0 0 2px; }
table.ut-table th:nth-child(2) { width:17%; } table.ut-table th:nth-child(3) { width:16%; } table.ut-table th:nth-child(1) { width:7%; }
tr:nth-child(even) td { background:var(--cream1); }
table.small { font-size:8.8pt; }
figure { margin:10px 0 14px; }
figure img { width:100%; border:1px solid var(--cream3); border-radius:8px; display:block; }
figure.narrow { max-width:3.1in; }
figure.tall img { max-height:7.2in; width:auto; max-width:100%; }
figcaption, .figcap { font-size:9pt; color:var(--muted); margin-top:4px; }
.diagram svg { width:100%; height:auto; border:1px solid var(--cream3); border-radius:8px; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; align-items:start; }
.grid3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; align-items:start; margin-top:8px; }
figure.w90 { max-width:90%; } figure.w80 { max-width:80%; } figure.w70 { max-width:70%; }
.trace > li { margin-bottom:12px; }
.chart { width:100%; max-width:6.6in; height:auto; margin:6px 0 12px; }
.chart .cl { font-size:12px; fill:var(--navy); } .chart .cv { font-size:12px; fill:var(--navy); font-weight:700; }
.pending { border:2px dashed var(--brass); background:var(--cream1); padding:12px 14px; border-radius:8px; }
.sources li { font-size:9.5pt; word-break:break-word; }
sup a { text-decoration:none; }
@page { size:letter; margin:0.55in; }
@media print {
  body { background:#fff; } main { padding:0; max-width:none; background:#fff; }
  h2 { break-after:avoid; } figure, table, .diagram { break-inside:avoid; }
  .title-page { break-after:page; }
  * { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
}
"""


def main() -> None:
    body = "".join([sec_title(), sec_motivation(), sec_new(), sec_agents(), sec_tokenomics(), sec_safety(), sec_impact(), sec_limits(), sec_sources()])
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WordWise · Final project report</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Libre+Baskerville:wght@400;700&display=swap">
<style>{CSS}</style></head>
<body><main>{body}</main></body></html>"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
