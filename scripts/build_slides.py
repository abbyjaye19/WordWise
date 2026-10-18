"""Build deliverables/slides.html: a self-contained reveal.js deck (10 slides, works offline).

Usage, from the project folder:
    python scripts/build_slides.py

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


def img(name: str, alt: str, width: int = 1400, crop: int | None = None, cls: str = "") -> str:
    im = Image.open(SHOTS / f"{name}.png").convert("RGB")
    if crop and im.height > crop:
        im = im.crop((0, 0, im.width, crop))
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return f'<img class="{cls}" src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}" alt="{alt}">'


def svg_file(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    return s[s.index("<svg"):]


def svg_data_uri(path: Path) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode()


summary = json.loads((TOK / "summary.json").read_text(encoding="utf-8"))
proj = json.loads((TOK / "projections.json").read_text(encoding="utf-8"))
safety = json.loads((ROOT / "output" / "safety" / "results.json").read_text(encoding="utf-8"))
st = summary["settings"]
before, after = st["before"]["run2"]["session_cost_usd"], st["after"]["run2"]["session_cost_usd"]
typ = proj["monthly_usd"]["After (shared guide, cached)"]["typical"]
passed = sum(r["passed"] for r in safety)
UT = ROOT / "deliverables" / "user_testing.json"
if UT.exists():
    _ts = json.loads(UT.read_text(encoding="utf-8"))["testers"]
    _n = len(_ts)
    _tw, _tn = sum(t["time_with_s"] for t in _ts) / _n, sum(t["time_without_s"] for t in _ts) / _n
    _sw, _sn = sum(t["score_with"] for t in _ts) / _n, sum(t["score_without"] for t in _ts) / _n
    REAL_USERS = (f"<strong>Real users ({_n}):</strong> comprehension {_sn:.1f} → <strong>{_sw:.1f} / 3</strong>, "
                  f"reading time {(_tw - _tn) / _tn:+.0%} with WordWise")
else:
    REAL_USERS = "<strong>Real users:</strong> testing with students and families (results in the report)"
skyline = svg_data_uri(ROOT / "app" / "assets" / "skyline.svg")
books = svg_data_uri(ROOT / "app" / "assets" / "book-stack.svg")
shelf = svg_data_uri(ROOT / "app" / "assets" / "bookshelf.svg")

SLIDES = f"""
<section class="dark title" data-background-color="#0F1F3D">
  <p class="eyebrow">MGT 409 · Final project · {AUTHOR}</p>
  <h1>WordWise</h1>
  <p class="pitch">Reading, made to fit you: an AI reading studio for students with dyslexia.</p>
  <img class="skyline" src="{skyline}" alt="">
</section>

<section>
  <h2>The problem</h2>
  <div class="cols">
    <div>
      <p class="big-number">5–20%</p>
      <p class="small">of people have dyslexia (estimates vary: Yale Center for Dyslexia &amp; Creativity; Understood.org)</p>
    </div>
    <ul>
      <li>Reading is slow and tiring, so <strong>understanding</strong> suffers</li>
      <li>Expert tutoring works, but it's <strong>expensive and hard to find</strong> (IDA)</li>
      <li>Students juggle separate apps: read-aloud, dictionary, chatbot, search</li>
    </ul>
  </div>
  <p class="who">Who: students aged about 5 to 30, reading school books, assignments, and lecture slides</p>
</section>

<section>
  <h2>What's new</h2>
  <ul class="roomy">
    <li><strong>One studio for the student's own reading</strong>: upload a PDF, slides, or Word file</li>
    <li><strong>Help next to the original</strong>, never replacing it</li>
    <li><strong>Pitched at 4 reader levels</strong> (5–8, 9–12, 13–17, 18+)</li>
    <li><strong>Builds comprehension</strong>: "check yourself" questions, not just a summary</li>
    <li><strong>Guides homework</strong> instead of doing it, plus trusted resources and tutoring sites</li>
  </ul>
</section>

<section>
  <h2>Four focused agents, one guard layer</h2>
  <div class="diagram">{svg_file(ROOT / "deliverables" / "agent_diagram.svg")}</div>
</section>

<section>
  <h2>Demo</h2>
  <div class="demo">
    <div class="demo-main">{img("trace_1_reading_studio", "Reading Studio with large text and highlights", 1400, crop=1250)}<p class="cap">Read aloud, highlight, ruler, focus, text settings</p></div>
    <div class="demo-side">{img("trace_2_word_coach", "Word Coach card", 520, crop=1250)}<p class="cap">Tap a word</p></div>
    <div class="demo-side">{img("trace_4_comprehension_coach", "Summary with questions", 520, crop=1300)}<p class="cap">Check yourself</p></div>
  </div>
</section>

<section>
  <h2>Cost to run</h2>
  <div class="cols">
    <div>
      <p class="big-number">${typ['1']:.3f}</p>
      <p class="small">per typical student per month (12 study sessions, AI only, measured)</p>
      <p class="big-number">${typ['10000']:,.0f}</p>
      <p class="small">per month for 10,000 students</p>
    </div>
    <ul>
      <li>Measured session: <strong>${before:.5f} → ${after:.5f}</strong> (−{1 - after / before:.0%})</li>
      <li>How: one shared reader-level guide pushed prompts past the <strong>1,024-token cache minimum</strong>, so most input is 10× cheaper</li>
      <li>Same request from a classmate: <strong>$0</strong> (Portkey replay cache)</li>
      <li>Read-aloud and reading tools: <strong>no AI, no cost</strong></li>
    </ul>
  </div>
</section>

<section>
  <h2>Safety: {passed} of {len(safety)} attacks stopped</h2>
  <div class="cols safety">
    <div>{img("safety_1_injected_reading", "Reading with a planted instruction", 900)}<p class="cap">A planted instruction tries to get the AI to give fake answers and ask for an address…</p></div>
    <div>{img("safety_2_injection_ignored_by_tutor", "Tutor ignores the planted instruction", 900, crop=900)}<p class="cap">…the tutor treats it as text. Other attacks were blocked upstream by Azure's filter.</p></div>
  </div>
  <p class="small">Also tested: essay request becomes a plan · 988 shown to a student in distress · other accounts blocked · password lockout · spending cap · wrong-model check</p>
</section>

<section>
  <h2>Impact</h2>
  <ul class="roomy">
    <li><strong>Reach:</strong> roughly 50–200 students in a school of 1,000 could benefit</li>
    <li><strong>Money:</strong> about <strong>${typ['1'] * 1000:,.0f} a month</strong> in AI for 1,000 typical students; points families to free tutoring</li>
    <li><strong>Time:</strong> answers in about 2–5 seconds, right next to the text</li>
    <li>{REAL_USERS}</li>
  </ul>
</section>

<section>
  <h2>What's next</h2>
  <ul class="roomy">
    <li>Measure time and quiz scores with real students</li>
    <li>Tighter answers for ages 5–8</li>
    <li>Text recognition (OCR) for scanned pages and photos of book pages</li>
    <li>Host it with per-student limits and a teacher view for shared assignments</li>
  </ul>
</section>

<section class="dark end" data-background-color="#0F1F3D">
  <h2>Try it</h2>
  <p class="pitch">{REPO}</p>
  <p class="small light">Run <code>python scripts/seed_demo.py</code>, then sign in as <code>demo</code> / <code>wordwise-demo</code></p>
  <img class="books" src="{books}" alt="">
</section>
"""

CSS = f"""
:root {{ --navy:#0F1F3D; --navy7:#1B3366; --navy5:#3C5A8F; --navy1:#DCE3F0; --cream:#FBF8F1; --cream1:#F4EEE1; --cream3:#E6DCC6; --brass:#B08D57; }}
.reveal-viewport {{ background:var(--cream); }}
.reveal {{ font-family:"Atkinson Hyperlegible", Verdana, sans-serif; font-size:34px; color:var(--navy); }}
.reveal .slides section {{ text-align:left; height:100%; }}
.reveal h1, .reveal h2 {{ font-family:"Libre Baskerville", Georgia, serif; color:var(--navy7); letter-spacing:0; text-transform:none; }}
.reveal h1 {{ font-size:110px; margin:0 0 10px; color:var(--cream); }}
.reveal h2 {{ font-size:54px; margin:0 0 28px; padding-bottom:10px; border-bottom:3px solid var(--brass); display:inline-block; }}
.reveal strong {{ color:var(--navy7); }}
.reveal ul {{ margin:0; }} .reveal li {{ margin-bottom:14px; line-height:1.35; }}
.reveal ul.roomy li {{ margin-bottom:24px; }}
.reveal .dark {{ color:var(--cream); }}
.reveal .dark h2 {{ color:var(--cream); }}
.reveal section.dark {{ background-image:radial-gradient(rgba(251,248,241,.10) 3px, transparent 3px); background-size:30px 30px; padding:40px; }}
.reveal .eyebrow {{ color:var(--brass); font-weight:700; font-size:26px; margin:70px 0 18px; }}
.reveal .pitch {{ font-size:40px; color:var(--cream1); max-width:900px; line-height:1.3; }}
.reveal .skyline {{ position:absolute; right:0; bottom:20px; width:560px; }}
.reveal .books {{ position:absolute; right:60px; bottom:90px; width:220px; }}
.reveal .cols {{ display:grid; grid-template-columns:1fr 1.5fr; gap:50px; align-items:start; }}
.reveal .cols.safety {{ grid-template-columns:1fr 1fr; gap:30px; }}
.reveal .big-number {{ font-size:96px; font-weight:700; color:var(--navy7); margin:0; line-height:1; }}
.reveal .small {{ font-size:24px; color:#4A5874; margin:6px 0 24px; line-height:1.35; }}
.reveal .small.light {{ color:var(--cream1); }}
.reveal .who {{ margin-top:30px; font-size:28px; background:var(--navy1); padding:14px 20px; border-radius:12px; border-left:6px solid var(--navy5); }}
.reveal .cap {{ font-size:20px; color:#4A5874; margin:6px 0 0; }}
.reveal img {{ border-radius:10px; border:2px solid var(--cream3); margin:0; max-width:100%; }}
.reveal .skyline, .reveal .books {{ border:none; }}
.reveal .diagram svg {{ width:100%; height:auto; max-height:560px; }}
.reveal .demo {{ display:grid; grid-template-columns:2.2fr 1fr 1fr; gap:18px; align-items:start; }}
.reveal .demo img {{ max-height:500px; object-fit:cover; object-position:top; width:100%; }}
.reveal .safety img {{ max-height:380px; object-fit:cover; object-position:top; width:100%; }}
.reveal code {{ background:rgba(251,248,241,.15); padding:2px 8px; border-radius:6px; font-size:.9em; }}
.reveal .slide-number {{ background:transparent; color:var(--navy5); font-size:18px; }}
.reveal .controls {{ color:var(--brass); }}
.reveal .progress {{ color:var(--brass); }}
.reveal section:not(.dark)::after {{ content:""; position:absolute; left:-40px; right:-40px; bottom:-30px; height:70px; background:url("{shelf}") repeat-x left bottom / auto 70px; opacity:.9; }}
"""


def main() -> None:
    reveal_css = (VENDOR / "reveal.css").read_text(encoding="utf-8")
    reveal_js = (VENDOR / "reveal.js").read_text(encoding="utf-8")
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WordWise · Slides</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Libre+Baskerville:wght@700&display=swap">
<style>{reveal_css}</style>
<style>{CSS}</style>
</head><body>
<div class="reveal"><div class="slides">{SLIDES}</div></div>
<script>{reveal_js}</script>
<script>Reveal.initialize({{ hash: true, slideNumber: "c/t", width: 1280, height: 720, margin: 0.06, transition: "fade", controls: true, progress: true }});</script>
<!-- reveal.js 5.2 (c) Hakim El Hattab, MIT license: scripts/vendor/revealjs/LICENSE -->
</body></html>"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB), {SLIDES.count('<section')} slides")


if __name__ == "__main__":
    main()
