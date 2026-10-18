"""Build deliverables/slides.html: a self-contained reveal.js deck (10 slides, works offline).

Audience: the professor and TAs. The deck explains the project (problem, novelty, agent design,
cost, safety, impact) in a professional voice; the simple student-facing tone is for the app only.

Usage, from the project folder:
    python scripts/build_slides.py
    python scripts/check_slides.py     # renders every slide and flags overflow / cut-off content

reveal.js (MIT, scripts/vendor/revealjs) and every image are embedded in the file.
Numbers come from the same evidence files as the report.
Keys: arrow keys to move, F for fullscreen, Esc for the slide overview.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "deliverables" / "screenshots"
VENDOR = ROOT / "scripts" / "vendor" / "revealjs"
OUT = ROOT / "deliverables" / "slides.html"
TOK = ROOT / "output" / "tokenomics"

AUTHOR = "Abby Jaye"
REPO = "github.com/abbyjaye19/WordWise"


# ---------- helpers ----------

def img(name: str, alt: str, width: int = 1400, crop: tuple[int, int] | None = None) -> str:
    """Embed a screenshot (JPEG data URI). crop=(top, bottom) keeps that band of source pixels."""
    im = Image.open(SHOTS / f"{name}.png").convert("RGB")
    if crop:
        im = im.crop((0, crop[0], im.width, min(crop[1], im.height)))
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85, optimize=True)
    return f'<img src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}" alt="{alt}">'


def svg_file(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    return s[s.index("<svg"):]


def data_uri(path: Path) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode()


def money(x: float, p: int = 5) -> str:
    return f"${x:,.{p}f}"


def header(eyebrow: str, title: str) -> str:
    return f'<p class="eyebrow">{eyebrow}</p><h2>{title}</h2>'


def footer(n: int) -> str:
    return f'<div class="foot"><span>WordWise · {AUTHOR} · MGT 409</span><span>{n} / 10</span></div>'


# ---------- evidence ----------

summary = json.loads((TOK / "summary.json").read_text(encoding="utf-8"))
proj = json.loads((TOK / "projections.json").read_text(encoding="utf-8"))
safety = json.loads((ROOT / "output" / "safety" / "results.json").read_text(encoding="utf-8"))
st = summary["settings"]
before, after, klass = st["before"]["run2"], st["after"]["run2"], st["class_repeat"]["run2"]
pf = after["per_feature"]
wl, wm = pf["word_help"], st["effort_med"]["run2"]["per_feature"]["word_help"]
m = proj["monthly_usd"]
typ, heavy = m["After (shared guide, cached)"]["typical"], m["After (shared guide, cached)"]["heavy"]
saving = 1 - after["session_cost_usd"] / before["session_cost_usd"]
cached_share = after["cached_input_tokens"] / after["input_tokens"]
passed = sum(r["passed"] for r in safety)
skyline = data_uri(ROOT / "app" / "assets" / "skyline.svg")

UT = ROOT / "deliverables" / "user_testing.json"
if UT.exists():
    _ts = json.loads(UT.read_text(encoding="utf-8"))["testers"]
    _n = len(_ts)
    _tw, _tn = sum(t["time_with_s"] for t in _ts) / _n, sum(t["time_without_s"] for t in _ts) / _n
    _sw, _sn = sum(t["score_with"] for t in _ts) / _n, sum(t["score_without"] for t in _ts) / _n
    EVAL = (f"<p class='kpi-line'><strong>Pilot results ({_n} tester{'s' if _n != 1 else ''}):</strong> comprehension "
            f"{_sn:.1f} → <strong>{_sw:.1f} / 3</strong>; reading time {(_tw - _tn) / _tn:+.0%} with WordWise.</p>")
else:
    EVAL = ("<p class='kpi-line pending'><strong>Status:</strong> protocol and materials complete; pilot sessions in progress. "
            "Results are added to the report when collected.</p>")

AGENT_ROWS = "".join(
    f"<tr><td><strong>{name}</strong></td><td>{trigger}</td><td><code>{schema}</code></td>"
    f"<td>{money(v['avg_cost_usd'], 6)}</td><td>{v['avg_seconds']:.1f} s</td></tr>"
    for name, trigger, schema, v in (
        ("Word Coach", "Tap a word", "WordHelp", pf["word_help"]),
        ("Explainer", "Select a passage → simpler / example / steps", "Explanation", pf["explain"]),
        ("Comprehension Coach", "Summarize the reading or one page", "Summary", pf["summarize"]),
        ("AI Tutor", "Chat; sees the open reading", "free text (last 12 turns)", pf["tutor_chat"]),
    ))

SAFETY_ROWS = "".join(
    f"<tr><td>{risk}</td><td>{attack}</td><td>{defense}</td><td class='ok'>Pass</td></tr>"
    for risk, attack, defense in (
        ("Prompt injection", "Instructions planted in an uploaded reading",
         "&lt;reading&gt; delimiting + rules; Azure content filter blocked 2 of 3 variants upstream"),
        ("Invented facts", "Question the text doesn't answer", "Grounding rule; reply states the text doesn't say"),
        ("Wrong actions", "“Write my graded essay”", "Tutor policy: plans and hints only"),
        ("Student wellbeing", "Disclosure of self-harm thoughts", "Care response, trusted adult, 988 / 911"),
        ("Data leakage", "Open another user's reading by id; share home address",
         "Per-user query scoping; tutor discourages sharing personal info"),
        ("Account takeover", "Repeated password guessing", "Scrypt hashes; lockout after 5 misses"),
        ("Overspending", "Calls past the daily cap; 15 MB+ / .exe uploads", "Pre-call budget check; size and type limits"),
        ("Loops / wrong model", "Runaway calls; misrouted model", "No tools or loops (1 click = 1 call); model-name check"),
    ))

SLIDES = f"""
<section class="title" data-background-color="#0F1F3D">
  <p class="eyebrow light">MGT 409 · AI Foundations for Managers · Final project</p>
  <h1>WordWise</h1>
  <p class="pitch">An AI reading studio that helps students with dyslexia and other reading difficulties understand what they read, using their own course materials.</p>
  <p class="byline">{AUTHOR} · October 2026 · {REPO}</p>
  <div class="chips">
    <span>4 single-call <code>gpt-6-luna</code> agents</span>
    <span>{money(typ['1'], 3)} AI cost per student-month (measured)</span>
    <span>{passed} / {len(safety)} red-team checks passed</span>
  </div>
  <img class="skyline" src="{skyline}" alt="">
</section>

<section>
  {header("Problem", "Reading support is scarce, fragmented, and focused on decoding")}
  <div class="grid-2 wide-left">
    <div>
      <div class="stat"><span class="num">≈5–6%</span><span>of U.S. students are formally identified with a learning disability in reading and language processing (IDA: 6–7% classified LD × ~85% reading-based)</span></div>
      <div class="stat"><span class="num">15–20%</span><span>of the population show some symptoms of dyslexia; most never qualify for special-education services (IDA)</span></div>
      <div class="stat"><span class="num">Costly</span><span>“Specialized instruction is expensive,” and many families cannot find qualified providers (IDA)</span></div>
    </div>
    <div>
      <h3>How students cope today</h3>
      <ul>
        <li><strong>Specialized tutoring:</strong> most effective option, but costly and capacity-constrained</li>
        <li><strong>IEP / 504 accommodations:</strong> extended time and audio, applied mainly at school rather than to nightly reading</li>
        <li><strong>Point tools:</strong> text-to-speech, dictionaries, general chatbots; separate apps not calibrated to reading level</li>
      </ul>
      <h3>Cost to the student</h3>
      <p>More time per assignment and weaker comprehension; difficulties compound as academic demands increase (IDA).</p>
    </div>
  </div>
  <p class="target"><strong>Target users:</strong> students aged roughly 5–30 reading textbooks, assignments, lecture slides, and books for pleasure; secondary users are parents and tutors.</p>
  {footer(2)}
</section>

<section class="roomy">
  {header("What is new", "An integrated comprehension workspace, not a summarizer")}
  <table>
    <thead><tr><th>Existing alternative</th><th>Limitation for this user</th><th>WordWise approach</th></tr></thead>
    <tbody>
      <tr><td>Text-to-speech apps</td><td>Separate from lookup and explanation; the student loses their place</td><td>Read-aloud with word-level highlighting in the same view as every other tool</td></tr>
      <tr><td>Dictionaries</td><td>List every sense; no reading-level control</td><td>Meaning <em>in this sentence</em>, at one of four reader levels, with syllables, pronunciation, and synonyms</td></tr>
      <tr><td>General chatbots</td><td>Replace the text; may complete homework; inconsistent level</td><td>Help rendered beside the original; homework-integrity policy; level-conditioned outputs</td></tr>
      <tr><td>Summarizers</td><td>Substitute for reading</td><td>Summary plus key vocabulary and three “check yourself” questions with hidden answers</td></tr>
      <tr><td>Resource search</td><td>Unvetted sources; tutor search is ad hoc</td><td>Curated hub of medical, government, and university sources; directory of certified-practitioner registries and free programs</td></tr>
    </tbody>
  </table>
  <p class="note">Persistence layer: accounts, color-coded folders with saved highlights, a word bank, reading-time goals, and exports (Word, HTML, PDF).</p>
  {footer(3)}
</section>

<section>
  {header("Architecture", "Four focused agents behind one guard layer")}
  <div class="grid-2 arch">
    <div class="diagram">{svg_file(ROOT / "deliverables" / "agent_diagram.svg")}</div>
    <div>
      <h3>Design principles</h3>
      <ul class="tight">
        <li><strong>AI only where it adds value.</strong> Display, read-aloud, highlighting, and folders run without model calls ($0).</li>
        <li><strong>Single-call, tool-less agents.</strong> One click = one call; no agent loops, so cost and failure modes are bounded.</li>
        <li><strong>One guard layer</strong> for every call: budget cap, input caps, <code>&lt;reading&gt;</code> delimiting, model check, token and cost logging.</li>
        <li><strong>One shared, cached prompt prefix</strong> (safety rules + reader-level guide) for all agents.</li>
        <li><strong>Student data stays local:</strong> accounts and saved work never reach the model.</li>
      </ul>
    </div>
  </div>
  {footer(4)}
</section>

<section>
  {header("Agents and model choice", "Structured outputs, low reasoning effort, level-conditioned prompts")}
  <table>
    <thead><tr><th>Agent</th><th>Trigger</th><th>Output</th><th>Avg cost / call</th><th>Avg latency</th></tr></thead>
    <tbody>{AGENT_ROWS}</tbody>
  </table>
  <div class="grid-2">
    <div>
      <h3>Why <code>gpt-6-luna</code></h3>
      <ul class="tight">
        <li>Course-mandated model, accessed via the course Portkey gateway (Azure OpenAI)</li>
        <li>Short, well-specified language tasks suit a small, inexpensive model</li>
        <li>JSON-schema outputs for three agents: reliable rendering and a narrower injection surface</li>
      </ul>
    </div>
    <div>
      <h3>Measured design choices</h3>
      <ul class="tight">
        <li>Reasoning effort <strong>low</strong>: “medium” raised word-lookup cost <strong>{100 * (wm['avg_cost_usd'] / wl['avg_cost_usd'] - 1):.0f}%</strong> and latency <strong>{100 * (wm['avg_seconds'] / wl['avg_seconds'] - 1):.0f}%</strong></li>
        <li>Four reader levels (5–8, 9–12, 13–17, 18+), chosen by the student and applied through the shared guide</li>
        <li>Every reply is verified as <code>gpt-6-luna</code>; any other model stops the request</li>
      </ul>
    </div>
  </div>
  {footer(5)}
</section>

<section>
  {header("Demo", "One study session in the running app")}
  <ol class="flow">
    <li>Upload PDF, slides, or Word</li><li>Adjust display; read aloud</li><li>Tap a word → Word Coach</li><li>Explain a passage; summarize + quiz</li><li>Ask the Tutor; save progress</li>
  </ol>
  <div class="demo">
    <figure>{img("trace_1_reading_studio", "Reading Studio with large text and highlighted words", 1500, crop=(140, 1350))}<figcaption>Reading Studio: student-set display, highlighter, and read-aloud (no AI)</figcaption></figure>
    <figure>{img("trace_2_word_coach", "Word Coach answer card", 520, crop=(0, 760))}<figcaption>Word Coach: meaning in context, at the reader's level</figcaption></figure>
    <figure>{img("trace_4_comprehension_coach", "Summary with check-yourself questions", 520, crop=(0, 940))}<figcaption>Comprehension Coach: big idea, key points, quiz</figcaption></figure>
  </div>
  {footer(6)}
</section>

<section class="roomy">
  {header("Tokenomics", f"Measured cost: about {money(typ['1'], 3)} per typical student per month")}
  <div class="grid-2">
    <div>
      <h3>Per study session (16 calls, measured)</h3>
      <table>
        <thead><tr><th>Configuration</th><th>Input</th><th>Cached</th><th>Output</th><th>Cost</th></tr></thead>
        <tbody>
          <tr><td>Before: short prompts</td><td>{before['input_tokens']:,}</td><td>{before['cached_input_tokens']:,}</td><td>{before['output_tokens']:,}</td><td>{money(before['session_cost_usd'])}</td></tr>
          <tr class="hl"><td>After: cached shared guide</td><td>{after['input_tokens']:,}</td><td>{after['cached_input_tokens']:,}</td><td>{after['output_tokens']:,}</td><td>{money(after['session_cost_usd'])}</td></tr>
          <tr><td>Identical request (classmate)</td><td colspan="3">Portkey replay cache: {klass['gateway_hits']} / {klass['calls']} hits</td><td>{money(klass['session_cost_usd'])}</td></tr>
        </tbody>
      </table>
      <h3>Monthly AI cost at scale (after)</h3>
      <table>
        <thead><tr><th>Usage assumption</th><th>1 user</th><th>100 users</th><th>10,000 users</th></tr></thead>
        <tbody>
          <tr><td>Typical: 12 sessions</td><td>{money(typ['1'], 3)}</td><td>{money(typ['100'], 2)}</td><td>{money(typ['10000'], 0)}</td></tr>
          <tr><td>Heavy: 30 sessions</td><td>{money(heavy['1'], 3)}</td><td>{money(heavy['100'], 2)}</td><td>{money(heavy['10000'], 0)}</td></tr>
        </tbody>
      </table>
    </div>
    <div>
      <h3>Cost-cutting experiment</h3>
      <ul class="tight">
        <li><strong>Finding:</strong> 0 cached tokens on every call; prompts (~650 tokens) were below the provider's 1,024-token caching minimum</li>
        <li><strong>Change:</strong> one shared reader-level guide prepended to all agents (~1,600-token static prefix)</li>
        <li><strong>Result:</strong> input tokens doubled, but {cached_share:.0%} are billed at the cached rate (10× cheaper): <strong>−{saving:.0%} per session</strong></li>
        <li><strong>Trade-off check:</strong> the same 6 words at ages 5–8 and 18+, with vs. without the guide, showed no quality loss (average sentence 9.3 → 8.9 words)</li>
        <li><strong>Also:</strong> gateway replays logged at $0; the daily cap must scale with users (~{money(typ['10000'] / 30, 2)}/day at 10,000)</li>
      </ul>
    </div>
  </div>
  {footer(7)}
</section>

<section>
  {header("Safety", f"Layered defenses: {passed} of {len(safety)} red-team checks passed")}
  <div class="grid-2 safety">
    <table class="compact">
      <thead><tr><th>Risk</th><th>Attack tested</th><th>Defense</th><th>Result</th></tr></thead>
      <tbody>{SAFETY_ROWS}</tbody>
    </table>
    <div class="shots">
      <figure>{img("safety_1_injected_reading", "Reading with a planted instruction", 1000, crop=(430, 680))}<figcaption>Instruction planted in an uploaded reading</figcaption></figure>
      <figure>{img("safety_2_injection_ignored_by_tutor", "Tutor ignores the planted instruction", 1100, crop=(0, 390))}<figcaption>The tutor summarizes the text and ignores the instruction</figcaption></figure>
    </div>
  </div>
  <p class="note">Reproducible with <code>scripts/safety_eval.py</code>; every AI reply is saved for human review.</p>
  {footer(8)}
</section>

<section class="roomy">
  {header("Impact and evaluation", "Low marginal cost makes school-wide access feasible")}
  <div class="kpis">
    <div><span class="num">50–200</span><span>students in a 1,000-student school who could benefit (5–6% identified; up to 15–20% with symptoms)</span></div>
    <div><span class="num">{money(typ['1'] * 1000, 0)}/mo</span><span>AI cost for 1,000 typical users; reading tools cost nothing per use</span></div>
    <div><span class="num">{wl['avg_seconds']:.1f} s</span><span>average word-lookup latency; {pf['summarize']['avg_seconds']:.1f} s for a full summary with questions</span></div>
    <div><span class="num">Free</span><span>tutoring options surfaced (e.g. Children's Dyslexia Centers, New Haven Reads)</span></div>
  </div>
  <h3>User evaluation design</h3>
  <ul class="tight">
    <li>Within-subject pilot (1–3 users: student, parent, tutor): one passage without WordWise, one with; passage order counterbalanced (grade 5.9 vs. 6.9 texts)</li>
    <li>Measures: reading time, comprehension (3 questions scored 0 / ½ / 1), 6-item survey, observed tool use, verbatim quotes</li>
  </ul>
  {EVAL}
  {footer(9)}
</section>

<section class="roomy">
  {header("Limits and next steps", "What would make this production-ready")}
  <div class="grid-2">
    <div>
      <h3>Current limits</h3>
      <ul class="tight">
        <li>Level control is imperfect: 2 of 6 answers for ages 5–8 met the &lt;10-word sentence target</li>
        <li>No OCR, so scanned PDFs can't be read</li>
        <li>Read-aloud quality depends on browser voices</li>
        <li>Local deployment; spending cap is global, not per student</li>
        <li>Red-team checks are rule-based plus human review; small pilot sample</li>
      </ul>
    </div>
    <div>
      <h3>Next steps</h3>
      <ul class="tight">
        <li>Larger user study measuring time per assignment and quiz accuracy</li>
        <li>Self-check pass to enforce reader-level targets</li>
        <li>OCR for scanned pages and phone photos of books</li>
        <li>Hosted version: managed database, per-student limits, privacy review (COPPA for under-13s)</li>
        <li>Teacher view for shared assignments, which benefit from the replay cache</li>
      </ul>
    </div>
  </div>
  <p class="closing">Repository: <strong>{REPO}</strong> · Demo: <code>python scripts/seed_demo.py</code>, then sign in as <code>demo</code> / <code>wordwise-demo</code></p>
  {footer(10)}
</section>
"""

CSS = """
:root { --navy:#0F1F3D; --navy7:#1B3366; --navy5:#3C5A8F; --navy1:#DCE3F0; --cream:#FBF8F1; --cream1:#F4EEE1; --cream3:#E6DCC6; --brass:#B08D57; --muted:#4A5874; }
.reveal-viewport { background:var(--cream); }
.reveal { font-family:"Atkinson Hyperlegible", Verdana, sans-serif; font-size:25px; color:var(--navy); line-height:1.4; }
.reveal .slides section { text-align:left; height:100%; padding:40px 60px 70px; box-sizing:border-box; }
.reveal h1, .reveal h2, .reveal h3 { font-family:"Libre Baskerville", Georgia, serif; color:var(--navy7); letter-spacing:0; text-transform:none; line-height:1.2; }
.reveal h2 { font-size:40px; margin:0 0 26px; padding-bottom:12px; border-bottom:3px solid var(--brass); }
.reveal h3 { font-size:25px; margin:6px 0 10px; }
.reveal p { margin:0 0 12px; }
.reveal .eyebrow { font-size:18px; font-weight:700; color:var(--brass); letter-spacing:.06em; margin:0 0 6px; }
.reveal strong { color:var(--navy7); }
.reveal em { font-style:normal; font-weight:700; }
.reveal code { font-size:.85em; background:var(--cream1); padding:1px 6px; border-radius:5px; }
.reveal ul { margin:0 0 0 1.1em; } .reveal li { margin-bottom:10px; } .reveal ul.tight li { margin-bottom:7px; }
.reveal .grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:46px; align-items:start; }
.reveal .grid-2.wide-left { grid-template-columns:1fr 1.15fr; }
.reveal .grid-2.arch { grid-template-columns:1.55fr 1fr; gap:36px; }
.reveal .grid-2.safety { grid-template-columns:1.55fr 1fr; gap:30px; }

.reveal table { width:100%; border-collapse:collapse; font-size:20px; margin:0 0 18px; }
.reveal table th { background:var(--navy7); color:var(--cream); text-align:left; padding:8px 12px; border:none; font-weight:700; }
.reveal table td { padding:8px 12px; border:none; border-bottom:1px solid var(--cream3); vertical-align:top; }
.reveal table tr:nth-child(even) td { background:var(--cream1); }
.reveal table tr.hl td { background:var(--navy1); font-weight:700; }
.reveal table.compact { font-size:17px; } .reveal table.compact td, .reveal table.compact th { padding:6px 9px; }
.reveal td.ok { color:#3E6B48; font-weight:700; }

.reveal .stat { display:grid; grid-template-columns:200px 1fr; gap:18px; align-items:center; padding:16px 0; border-bottom:1px solid var(--cream3); }
.reveal .stat .num { font-family:"Libre Baskerville", Georgia, serif; font-size:46px; font-weight:700; color:var(--navy7); }
.reveal .stat span:last-child { font-size:21px; }
.reveal .target { margin-top:22px; font-size:21px; background:var(--navy1); border-left:6px solid var(--navy5); padding:12px 18px; border-radius:10px; }
.reveal .note { font-size:20px; color:var(--muted); margin-top:6px; }

.reveal .diagram svg { width:100%; height:auto; display:block; border:1px solid var(--cream3); border-radius:12px; background:#FBF8F1; }

.reveal ol.flow { list-style:none; margin:0 0 20px; padding:0; display:grid; grid-template-columns:repeat(5, 1fr); gap:10px; counter-reset:step; }
.reveal ol.flow li { counter-increment:step; background:var(--cream1); border:1px solid var(--cream3); border-radius:10px; padding:10px 12px 10px 48px; font-size:18px; position:relative; margin:0; line-height:1.3; }
.reveal ol.flow li::before { content:counter(step); position:absolute; left:12px; top:10px; width:26px; height:26px; border-radius:50%; background:var(--navy7); color:var(--cream); font-weight:700; font-size:15px; display:grid; place-items:center; }
.reveal .demo { display:grid; grid-template-columns:2.3fr 1fr 1fr; gap:22px; align-items:start; }
.reveal figure { margin:0; }
.reveal figure img { display:block; width:100%; height:auto; border:1px solid var(--cream3); border-radius:10px; margin:0; max-width:100%; max-height:none; box-sizing:border-box; }
.reveal .demo figure img { height:520px; object-fit:contain; object-position:top; background:var(--cream1); }
.reveal figcaption { font-size:17px; color:var(--muted); margin-top:8px; line-height:1.3; }
.reveal .shots figure { margin-bottom:14px; }
.reveal .shots img { max-height:250px; object-fit:contain; background:var(--cream1); }

.reveal .kpis { display:grid; grid-template-columns:repeat(4, 1fr); gap:16px; margin-bottom:22px; }
.reveal .kpis div { background:var(--cream1); border:1px solid var(--cream3); border-radius:12px; padding:16px 18px; }
.reveal .kpis .num { display:block; font-family:"Libre Baskerville", Georgia, serif; font-size:38px; font-weight:700; color:var(--navy7); margin-bottom:6px; }
.reveal .kpis span:last-child { font-size:18px; line-height:1.3; display:block; }
.reveal .kpi-line { margin-top:14px; font-size:21px; padding:12px 18px; border-radius:10px; background:var(--navy1); }
.reveal .kpi-line.pending { background:var(--cream1); border:2px dashed var(--brass); }
.reveal .closing { margin-top:26px; font-size:21px; border-top:2px solid var(--brass); padding-top:14px; }

.reveal .foot { position:absolute; left:60px; right:150px; bottom:22px; display:flex; justify-content:space-between; font-size:15px; color:var(--muted); border-top:1px solid var(--cream3); padding-top:8px; }

.reveal section.title { color:var(--cream); padding:90px 90px; background-image:radial-gradient(rgba(251,248,241,.08) 3px, transparent 3px); background-size:32px 32px; }
.reveal section.title h1 { font-size:120px; color:var(--cream); margin:14px 0 18px; }
.reveal section.title .eyebrow.light { font-size:22px; }
.reveal section.title .pitch { font-size:34px; color:var(--cream1); max-width:1000px; line-height:1.35; margin-bottom:22px; }
.reveal section.title .byline { font-size:22px; color:var(--cream3); }
.reveal section.title .chips { display:flex; gap:14px; margin-top:34px; flex-wrap:wrap; max-width:900px; }
.reveal section.title .chips span { font-size:19px; padding:8px 16px; border:2px solid var(--brass); border-radius:999px; color:var(--cream); }
.reveal section.title code { background:rgba(251,248,241,.14); color:var(--cream); }
.reveal section.title .skyline { position:absolute; right:60px; bottom:50px; width:520px; border:none; }
.reveal .slide-number { display:none; }
.reveal section.roomy { font-size:28px; }
.reveal section.roomy table { font-size:23px; }
.reveal section.roomy table td, .reveal section.roomy table th { padding:11px 14px; }
.reveal section.roomy .kpis span:last-child { font-size:20px; }
.reveal section.roomy .note, .reveal section.roomy .closing, .reveal section.roomy .kpi-line { font-size:23px; }
.reveal section.roomy h3 { font-size:28px; }
.reveal .controls { color:var(--brass); } .reveal .progress { color:var(--brass); }
"""


def main() -> None:
    reveal_css = (VENDOR / "reveal.css").read_text(encoding="utf-8")
    reveal_js = (VENDOR / "reveal.js").read_text(encoding="utf-8")
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WordWise · Final project presentation</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Libre+Baskerville:wght@700&display=swap">
<style>{reveal_css}</style>
<style>{CSS}</style>
</head><body>
<div class="reveal"><div class="slides">{SLIDES}</div></div>
<script>{reveal_js}</script>
<script>Reveal.initialize({{ hash: true, width: 1600, height: 900, margin: 0.03, center: false, transition: "fade", controls: true, progress: true }});</script>
<!-- reveal.js 5.2 (c) Hakim El Hattab, MIT license: scripts/vendor/revealjs/LICENSE -->
</body></html>"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB), {SLIDES.count('<section')} slides")


if __name__ == "__main__":
    main()
