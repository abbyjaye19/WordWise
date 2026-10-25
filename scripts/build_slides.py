"""Build deliverables/slides.html: a consulting-style, self-contained reveal.js deck (10 slides, offline).

Audience: the professor and TAs. Every slide has an action title (the takeaway as a sentence),
one main exhibit, a section tracker, and a source line. The student-friendly tone is for the app only.

Usage, from the project folder:
    python scripts/build_slides.py
    python scripts/check_slides.py     # renders every slide and flags overflow / cut-off content

reveal.js (MIT, scripts/vendor/revealjs) and every image are embedded. Numbers come from the same
evidence files as the report. Ratings on the landscape matrix and positions on the risk heat map
are the author's assessment and are labeled as such on the slides.
"""

from __future__ import annotations

import base64
import io
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "deliverables" / "screenshots"
VENDOR = ROOT / "scripts" / "vendor" / "revealjs"
OUT = ROOT / "deliverables" / "slides.html"
TOK = ROOT / "output" / "tokenomics"

AUTHOR = "Abby Jaye"
REPO = "github.com/abbyjaye19/WordWise"

NAVY = "#0F1F3D"
GREEN7, GREEN5, MINT1 = "#2F6B49", "#5E9A6E", "#E1F0DC"  # pastel green theme: fills green, text navy
CREAM, CREAM1, CREAM3 = "#FBF8F1", "#F4EEE1", "#E6DCC6"
BRASS, BRASS_DARK, MUTED, GREEN = "#B08D57", "#8A6630", "#4A5874", "#3E6B48"
SKY = "#A9D3A0"  # light green (was sky blue)
FONT = "font-family:'Atkinson Hyperlegible',Verdana,sans-serif"


# ---------- evidence ----------

summary = json.loads((TOK / "summary.json").read_text(encoding="utf-8"))
proj = json.loads((TOK / "projections.json").read_text(encoding="utf-8"))
safety = json.loads((ROOT / "output" / "safety" / "results.json").read_text(encoding="utf-8"))
st = summary["settings"]
before, after, klass = st["before"]["run2"], st["after"]["run2"], st["class_repeat"]["run2"]
pf = after["per_feature"]
wl, wm = pf["word_help"], st["effort_med"]["run2"]["per_feature"]["word_help"]
m = proj["monthly_usd"]
typ = m["After (shared guide, cached)"]["typical"]
light = m["After (shared guide, cached)"]["light"]
heavy = m["After (shared guide, cached)"]["heavy"]
saving = 1 - after["session_cost_usd"] / before["session_cost_usd"]
cached_share = after["cached_input_tokens"] / after["input_tokens"]
passed, total_checks = sum(r["passed"] for r in safety), len(safety)
effort_cost = 100 * (wm["avg_cost_usd"] / wl["avg_cost_usd"] - 1)
effort_time = 100 * (wm["avg_seconds"] / wl["avg_seconds"] - 1)

UT = ROOT / "deliverables" / "user_testing.json"
if UT.exists():
    _ts = json.loads(UT.read_text(encoding="utf-8"))["testers"]
    _timed = [t for t in _ts if t.get("time_with_s") is not None]
    _fixes = sum(len(t.get("changes", [])) for t in _ts)
    if _timed:
        _n = len(_timed)
        _tw, _tn = sum(t["time_with_s"] for t in _timed) / _n, sum(t["time_without_s"] for t in _timed) / _n
        _sw, _sn = sum(t["score_with"] for t in _timed) / _n, sum(t["score_without"] for t in _timed) / _n
        EVAL_STATUS = (f"<strong>Pilot results ({_n}):</strong> comprehension {_sn:.1f} → {_sw:.1f} / 3; "
                       f"reading time {(_tw - _tn) / _tn:+.0%} with WordWise")
    else:
        EVAL_STATUS = (f"<strong>Pilot:</strong> {len(_ts)} observed user sessions; feedback led to {_fixes} shipped fixes. "
                       "Timed comprehension study with target students is next")
else:
    EVAL_STATUS = "<strong>Status:</strong> pilot protocol and materials complete; sessions in progress"


# ---------- generic helpers ----------

def money(x: float, p: int = 5) -> str:
    return f"${x:,.{p}f}"


def img(name: str, alt: str, width: int = 1400, crop: tuple[int, int] | None = None) -> str:
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


SECTIONS = ["Summary", "Problem", "Landscape", "Solution", "Architecture", "Design", "Economics", "Risk", "Impact"]


def frame(n: int, section: str, title: str, body: str, source: str, exhibit: str | None = None, implication: str | None = None) -> str:
    tracker = "".join(f'<span class="{"on" if s == section else ""}">{s}</span>' for s in SECTIONS)
    ex = f'<p class="exhibit">{exhibit}</p>' if exhibit else ""
    imp = f'<div class="implication"><span>Implication</span><p>{implication}</p></div>' if implication else ""
    return f"""
<section class="cs">
  <div class="tracker">{tracker}</div>
  <h2 class="action">{title}</h2>
  {ex}
  <div class="body">{body}</div>
  {imp}
  <p class="source">{source}</p>
  <div class="foot"><span>WordWise · {AUTHOR} · MGT 409 final project</span><span>{n}</span></div>
</section>"""


def t(x, y, text, size=15, fill=NAVY, weight=400, anchor="start", extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" style="{FONT}" {extra}>{text}</text>'


# ---------- exhibits ----------

def harvey(level: int) -> str:
    """Harvey ball, level 0-4."""
    r, c = 11, 13
    parts = [f'<svg class="hb" viewBox="0 0 26 26" width="26" height="26" role="img" aria-label="{level} of 4">',
             f'<circle cx="{c}" cy="{c}" r="{r}" fill="{CREAM}" stroke="{GREEN7}" stroke-width="2"/>']
    if level >= 4:
        parts.append(f'<circle cx="{c}" cy="{c}" r="{r}" fill="{GREEN7}"/>')
    elif level > 0:
        ang = 2 * math.pi * level / 4
        x, y = c + r * math.sin(ang), c - r * math.cos(ang)
        large = 1 if level > 2 else 0
        parts.append(f'<path d="M{c} {c} L{c} {c - r} A{r} {r} 0 {large} 1 {x:.2f} {y:.2f} Z" fill="{GREEN7}"/>')
    parts.append("</svg>")
    return "".join(parts)


def support_gap_svg() -> str:
    """Range bars: share with symptoms vs. formally identified (IDA)."""
    W, x0, x1 = 780, 250, 740
    scale = (x1 - x0) / 25
    X = lambda v: x0 + v * scale  # noqa: E731
    s = [f'<svg viewBox="0 0 {W} 330" class="exh" role="img" aria-label="15 to 20 percent show symptoms; about 5 to 6 percent are formally identified">']
    for v in range(0, 26, 5):
        s.append(f'<line x1="{X(v)}" y1="30" x2="{X(v)}" y2="250" stroke="{CREAM3}" stroke-width="1"/>')
        s.append(t(X(v), 272, f"{v}%", 14, MUTED, anchor="middle"))
    rows = [(70, "Show some symptoms", "of dyslexia", 15, 20, "15–20%"), (185, "Formally identified", "reading / language LD", 5, 6, "≈5–6%")]
    for y, l1, l2, lo, hi, lab in rows:
        s.append(t(x0 - 14, y + 18, l1, 16, NAVY, 700, "end"))
        s.append(t(x0 - 14, y + 38, l2, 14, MUTED, anchor="end"))
        s.append(f'<rect x="{x0}" y="{y}" width="{X(lo) - x0:.1f}" height="44" rx="4" fill="{GREEN7}"/>')
        s.append(f'<rect x="{X(lo) + 2:.1f}" y="{y}" width="{X(hi) - X(lo) - 2:.1f}" height="44" rx="4" fill="{SKY}"/>')
        s.append(t(X(hi) + 10, y + 29, lab, 20, NAVY, 700))
    gx0, gx1, gy = X(6), X(15), 150
    s.append(f'<path d="M{gx0} {gy - 12} L{gx0} {gy} L{gx1} {gy} L{gx1} {gy - 12}" fill="none" stroke="{BRASS_DARK}" stroke-width="2.5"/>')
    s.append(t((gx0 + gx1) / 2, gy + 22, "Support gap: ~9–15 points of the population", 15, BRASS_DARK, 700, "middle"))
    s.append(f'<rect x="{x0}" y="300" width="18" height="12" fill="{GREEN7}"/>' + t(x0 + 26, 311, "lower estimate", 13, MUTED))
    s.append(f'<rect x="{x0 + 150}" y="300" width="18" height="12" fill="{SKY}"/>' + t(x0 + 176, 311, "range to upper estimate", 13, MUTED))
    s.append("</svg>")
    return "".join(s)


def hbars_svg(rows: list[tuple[str, float, str]], unit_fmt, width=620, highlight: str | None = None) -> str:
    """Single-series horizontal bars with value labels."""
    left, bar_h, gap = 190, 34, 20
    top = max(v for _, v, _ in rows) or 1
    h = len(rows) * (bar_h + gap) + 10
    s = [f'<svg viewBox="0 0 {width} {h}" class="exh" role="img" aria-label="bar chart">']
    for i, (label, v, note) in enumerate(rows):
        y = 6 + i * (bar_h + gap)
        bw = max((width - left - 150) * v / top, 3)
        fill = BRASS_DARK if label == highlight else GREEN7
        s.append(t(left - 12, y + 22, label, 15, NAVY, 700, "end"))
        s.append(f'<rect x="{left}" y="{y}" width="{bw:.1f}" height="{bar_h}" rx="4" fill="{fill}"/>')
        s.append(t(left + bw + 10, y + 16, unit_fmt(v), 16, NAVY, 700))
        if note:
            s.append(t(left + bw + 10, y + 33, note, 12, MUTED))
    s.append(f'<line x1="{left}" y1="0" x2="{left}" y2="{h}" stroke="{CREAM3}"/>')
    s.append("</svg>")
    return "".join(s)


def waterfall_svg() -> str:
    """Cost per 1,000 study sessions: before -> caching -> after -> replay -> repeat."""
    b, a = before["session_cost_usd"] * 1000, after["session_cost_usd"] * 1000
    steps = [("Before", b, "total"), ("Prompt caching", a - b, "delta"), ("After (used)", a, "total"),
             ("Replay cache", -a, "delta"), ("Repeat session", klass["session_cost_usd"] * 1000, "total")]
    W, H, x0, base_y, top_y = 760, 380, 60, 300, 40
    scale = (base_y - top_y) / (b * 1.1)
    Y = lambda v: base_y - v * scale  # noqa: E731
    col_w, gap = 98, 40
    s = [f'<svg viewBox="0 0 {W} {H}" class="exh" role="img" aria-label="Cost waterfall per 1,000 sessions">']
    for v in (0, 0.5, 1.0, 1.5, 2.0):
        s.append(f'<line x1="{x0}" y1="{Y(v):.1f}" x2="{W - 10}" y2="{Y(v):.1f}" stroke="{CREAM3}"/>')
        s.append(t(x0 - 8, Y(v) + 5, f"${v:.1f}", 13, MUTED, anchor="end"))
    running = 0.0
    prev_top = None
    for i, (label, v, kind) in enumerate(steps):
        x = x0 + 20 + i * (col_w + gap)
        if kind == "total":
            y_top, y_bot, fill, running = Y(v), Y(0), GREEN7, v
            lab = f"${v:.2f}"
        else:
            start, end = running, running + v
            y_top, y_bot, fill, running = Y(max(start, end)), Y(min(start, end)), BRASS_DARK, end
            lab = f"−${abs(v):.2f}"
        hgt = max(y_bot - y_top, 2)
        s.append(f'<rect x="{x}" y="{y_top:.1f}" width="{col_w}" height="{hgt:.1f}" rx="3" fill="{fill}"/>')
        s.append(t(x + col_w / 2, y_top - 8, lab, 16, NAVY, 700, "middle"))
        s.append(t(x + col_w / 2, base_y + 24, label, 14, NAVY, 700, "middle"))
        if prev_top is not None:
            s.append(f'<line x1="{x - gap}" y1="{prev_top:.1f}" x2="{x}" y2="{prev_top:.1f}" stroke="{MUTED}" stroke-dasharray="3 3"/>')
        prev_top = Y(running)
    s.append(t(x0 + 20 + 1 * (col_w + gap) + col_w / 2, base_y + 44, f"−{saving:.0%}", 14, BRASS_DARK, 700, "middle"))
    s.append(t(x0 + 20 + 3 * (col_w + gap) + col_w / 2, base_y + 44, f"{klass['gateway_hits']}/{klass['calls']} hits", 14, BRASS_DARK, 700, "middle"))
    s.append("</svg>")
    return "".join(s)


def heatmap_svg() -> str:
    """3x3 likelihood x impact grid with numbered risks (author's pre-mitigation assessment)."""
    risks = {  # number: (likelihood 0-2, impact 0-2)
        1: (2, 2), 2: (2, 1), 3: (2, 1), 4: (0, 2), 5: (1, 2), 6: (1, 1), 7: (1, 1), 8: (0, 1),
    }
    ramp = {0: "#F0F7EC", 1: MINT1, 2: "#BFDDB7", 3: "#6FA57C", 4: GREEN7}
    cell, x0, y0 = 128, 120, 20
    s = [f'<svg viewBox="0 0 540 470" class="exh" role="img" aria-label="Risk heat map">']
    for li in range(3):
        for im in range(3):
            x, y = x0 + li * cell, y0 + (2 - im) * cell
            s.append(f'<rect x="{x}" y="{y}" width="{cell - 4}" height="{cell - 4}" rx="6" fill="{ramp[li + im]}"/>')
    for i, lab in enumerate(["Low", "Medium", "High"]):
        s.append(t(x0 + i * cell + cell / 2 - 2, y0 + 3 * cell + 22, lab, 14, MUTED, anchor="middle"))
        s.append(t(x0 - 12, y0 + (2 - i) * cell + cell / 2 + 4, lab, 14, MUTED, anchor="end"))
    s.append(t(x0 + 1.5 * cell, y0 + 3 * cell + 48, "Likelihood (before defenses)", 15, NAVY, 700, "middle"))
    s.append(t(28, y0 + 1.5 * cell, "Impact", 15, NAVY, 700, "middle", f'transform="rotate(-90 28 {y0 + 1.5 * cell})"'))
    placed: dict[tuple[int, int], int] = {}
    for n, (li, im) in risks.items():
        k = placed.get((li, im), 0)
        placed[(li, im)] = k + 1
        cx = x0 + li * cell + 36 + (k % 2) * 50
        cy = y0 + (2 - im) * cell + 40 + (k // 2) * 46
        s.append(f'<circle cx="{cx}" cy="{cy}" r="17" fill="{BRASS}" stroke="{NAVY}" stroke-width="2"/>')
        s.append(t(cx, cy + 6, str(n), 16, NAVY, 700, "middle"))
    s.append("</svg>")
    return "".join(s)


def layers_svg() -> str:
    """Defense in depth: nested layers, outermost first."""
    layers = [
        ("Provider", "Azure content filter blocks jailbreak attempts upstream", "#F0F7EC", NAVY),
        ("App controls", "Auth, per-user data scoping, lockout, upload limits", MINT1, NAVY),
        ("Guard layer", "Budget cap, input caps, <reading> delimiting, model check, logging", "#BFDDB7", NAVY),
        ("Prompt policy", "Grounding, homework integrity, wellbeing, privacy", GREEN7, CREAM),
    ]
    s = ['<svg viewBox="0 0 560 330" class="exh" role="img" aria-label="Four nested defense layers">']
    for i, (name, desc, fill, ink) in enumerate(layers):
        inset = i * 26
        x, y, w, h = 10 + inset, 10 + inset * 1.0, 540 - 2 * inset, 310 - 2 * inset
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{GREEN7}" stroke-width="1.5"/>')
        s.append(t(x + 14, y + 20, name.upper(), 12, ink, 700, extra='letter-spacing="1"'))
    s.append(t(280, 152, "Model call", 20, CREAM, 700, "middle"))
    s.append(t(280, 178, "gpt-6-luna", 15, CREAM1, 400, "middle"))
    s.append("</svg>")
    descs = "".join(f"<li><strong>{n}:</strong> {d.replace('<', '&lt;').replace('>', '&gt;')}</li>" for n, d, _, _ in layers)
    return "".join(s), descs


def roadmap_svg() -> str:
    cols = ["Now · Oct 2026", "Next term", "6–12 months"]
    rows = [
        ("Evaluation", [(0, 1, "Pilot: 1–3 users, timed A/B", GREEN7), (1, 3, "Classroom study: time per assignment, quiz accuracy", GREEN5)]),
        ("Product", [(0, 1, "Reading studio, 4 agents", GREEN7), (1, 2, "Reader-level self-check", GREEN5), (2, 3, "OCR for scans and photos", GREEN5)]),
        ("Platform & cost", [(0, 1, "Local app, global cap", GREEN7), (1, 3, "Hosted version, per-student limits, teacher view", GREEN5)]),
        ("Safety & privacy", [(0, 1, "13/13 red-team checks", GREEN7), (1, 2, "Larger attack set", GREEN5), (2, 3, "COPPA / privacy review", GREEN5)]),
    ]
    W, lab_w, top, row_h = 1460, 190, 44, 50
    col_w = (W - lab_w) / 3
    s = [f'<svg viewBox="0 0 {W} {top + len(rows) * row_h + 8}" class="exh" role="img" aria-label="Roadmap">']
    for i, c in enumerate(cols):
        x = lab_w + i * col_w
        s.append(f'<rect x="{x + 2}" y="0" width="{col_w - 4}" height="32" rx="6" fill="{CREAM1}" stroke="{CREAM3}"/>')
        s.append(t(x + col_w / 2, 22, c, 15, NAVY, 700, "middle"))
    for r, (name, bars) in enumerate(rows):
        y = top + r * row_h
        s.append(t(lab_w - 14, y + 26, name, 15, NAVY, 700, "end"))
        s.append(f'<line x1="{lab_w}" y1="{y + row_h - 4}" x2="{W}" y2="{y + row_h - 4}" stroke="{CREAM3}"/>')
        for c0, c1, label, fill in bars:
            x = lab_w + c0 * col_w + 4
            w = (c1 - c0) * col_w - 8
            s.append(f'<rect x="{x:.1f}" y="{y + 4}" width="{w:.1f}" height="34" rx="17" fill="{fill}"/>')
            s.append(t(x + 16, y + 26, label, 14, CREAM, 700))
    s.append("</svg>")
    return "".join(s)


def chevrons(steps: list[str]) -> str:
    return '<div class="chevrons">' + "".join(
        f'<div class="chev"><span class="n">{i}</span><span>{s}</span></div>' for i, s in enumerate(steps, 1)) + "</div>"


# ---------- slides ----------

skyline = data_uri(ROOT / "app" / "assets" / "skyline.svg")

LANDSCAPE = [  # (option, affordable, at home, own material, builds comprehension, reader-level fit)
    ("Specialized tutoring", 1, 2, 4, 4, 4),
    ("IEP / 504 accommodations", 4, 1, 2, 1, 2),
    ("Text-to-speech apps", 4, 4, 4, 1, 0),
    ("Dictionaries", 4, 4, 2, 1, 1),
    ("General chatbots", 3, 4, 4, 2, 2),
    ("WordWise", 4, 4, 4, 3, 3),
]


def landscape_table() -> str:
    head = "".join(f"<th>{h}</th>" for h in ("Option", "Affordable", "Available at home", "Works on own material", "Builds comprehension", "Fits reader level"))
    rows = ""
    for name, *scores in LANDSCAPE:
        cls = ' class="ours"' if name == "WordWise" else ""
        rows += f"<tr{cls}><td>{name}</td>" + "".join(f"<td class='c'>{harvey(v)}</td>" for v in scores) + "</tr>"
    return f'<table class="matrix"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'


def slide_title() -> str:
    return f"""
<section class="title" data-background-color="#0F1F3D">
  <p class="eyebrow light">MGT 409 · AI Foundations for Managers · Final project</p>
  <h1>WordWise</h1>
  <p class="pitch">An AI reading studio that helps students with dyslexia and other reading difficulties understand their own course materials, at a marginal cost of about {money(typ['1'], 3)} per student-month.</p>
  <p class="origin"><strong>Origin:</strong> built from lived experience. I have double-deficit dyslexia; in college, a reading specialist gave me the kind of support WordWise now automates.</p>
  <p class="byline">{AUTHOR} · October 2026 · {REPO}</p>
  <div class="chips">
    <span>4 single-call <code>gpt-6-luna</code> agents</span>
    <span>−{saving:.0%} session cost via prompt caching</span>
    <span>{passed} / {total_checks} red-team checks passed</span>
  </div>
  <img class="skyline" src="{skyline}" alt="">
</section>"""


def slide_summary() -> str:
    body = f"""
<div class="scr">
  <div><p class="scr-h">Situation</p><p>About 5–6% of U.S. students are formally identified with a reading-based learning disability, and up to 15–20% of people show some symptoms of dyslexia.</p><p>The most effective help, specialized instruction, is expensive and hard to find.</p></div>
  <div><p class="scr-h">Complication</p><p>Most struggling readers never qualify for formal support. They piece together separate tools (text-to-speech, dictionaries, general chatbots) that don't share context, ignore reading level, and can replace the reading instead of building comprehension.</p></div>
  <div class="res"><p class="scr-h">Resolution</p><p>WordWise: one workspace on the student's own PDFs, slides, and documents, with read-aloud and display controls, plus four focused AI agents that explain text <em>beside</em> the original at one of four reader levels and check understanding with questions.</p></div>
</div>
<div class="metrics">
  <div><span class="mv">{money(typ['1'], 3)}</span><span class="ml">AI cost per typical student-month (measured)</span></div>
  <div><span class="mv">−{saving:.0%}</span><span class="ml">session cost after making prompts cacheable</span></div>
  <div><span class="mv">{wl['avg_seconds']:.1f} s</span><span class="ml">average word-lookup latency</span></div>
  <div><span class="mv">{passed}/{total_checks}</span><span class="ml">red-team checks passed</span></div>
</div>"""
    return frame(2, "Summary", "WordWise closes the gap between who needs reading support and who receives it, at near-zero marginal cost",
                 body, "Source: International Dyslexia Association (prevalence; cost of instruction); WordWise measurements (output/tokenomics, output/safety).",
                 implication=f"Comprehension support can be offered to every struggling reader, not only the formally identified, for under {money(heavy['1'], 2)} per student-month even at heavy use.")


def slide_problem() -> str:
    body = f"""
<div class="g2 w55">
  <div class="panel">{support_gap_svg()}</div>
  <div class="stack">
    <div class="box"><p class="bh">1 · Support is rationed</p><p>Special-education status reaches the formally identified ~5–6%; most of the 15–20% with symptoms “will not qualify” yet “are likely to struggle” (IDA).</p></div>
    <div class="box"><p class="bh">2 · The best help is scarce</p><p>Intensive instruction from trained teachers is most effective (NIH NICHD), but “specialized instruction is expensive” and many families can't find it (IDA).</p></div>
    <div class="box"><p class="bh">3 · The cost compounds</p><p>Slow decoding consumes the effort comprehension needs; difficulties grow as academic demands increase (IDA).</p></div>
    <div class="box founder"><p class="bh">Founder insight</p><p>I have double-deficit dyslexia. A college reading specialist gave me this kind of support, and trustworthy resources were hard to find. WordWise packages that support in one home base.</p></div>
  </div>
</div>"""
    return frame(3, "Problem", "Most struggling readers fall outside formal support, and the help that works best is the hardest to get",
                 body, "Source: International Dyslexia Association, “Dyslexia basics” (6–7% of students classified LD, ~85% reading-based; 15–20% with symptoms), “Evaluating professionals”, “Dyslexia assessment”; NIH NICHD, reading-disorder treatments.",
                 "Exhibit 1 · Share of population, by level of reading difficulty",
                 "The design target is the unserved middle: at-home, low-cost, comprehension-focused help that does not depend on formal identification.")


def slide_landscape() -> str:
    body = f"""
<div class="g2 w62">
  <div>{landscape_table()}<p class="legend">{harvey(0)} none &nbsp; {harvey(2)} partial &nbsp; {harvey(4)} strong</p></div>
  <div class="stack">
    <p class="side-h">Where WordWise differs</p>
    <div class="num-box"><span>1</span><p><strong>Comprehension, not just access:</strong> explanations sit beside the original and end in “check yourself” questions</p></div>
    <div class="num-box"><span>2</span><p><strong>Reader-level control:</strong> four levels (5–8 to 18+) applied to every agent</p></div>
    <div class="num-box"><span>3</span><p><strong>One context:</strong> read-aloud, highlights, word help, and tutor all work on the same open document</p></div>
    <div class="num-box"><span>4</span><p><strong>Built-in integrity:</strong> the tutor plans and hints; it doesn't write graded work</p></div>
  </div>
</div>"""
    return frame(4, "Landscape", "No existing option combines affordability, at-home access, and comprehension support for this user",
                 body, "Note: ratings are the author's qualitative assessment of each option for a struggling reader working at home; WordWise is rated 3 of 4 on comprehension and level fit pending user testing.",
                 "Exhibit 2 · How current options serve a struggling reader",
                 "WordWise complements specialized tutoring rather than replacing it: it covers the hours between sessions and the students who never get a tutor.")


def slide_solution() -> str:
    body = f"""
{chevrons(["Upload PDF, slides, or Word", "Set size, spacing, and read aloud", "Tap a word: Word Coach", "Select or summarize: Explainer, Comprehension Coach", "Ask the AI Tutor; save words and goals"])}
<div class="shots3">
  <figure><span class="badge">1–2</span>{img("trace_1_reading_studio", "Reading Studio", 1500, crop=(140, 1250))}<figcaption><strong>Reading Studio.</strong> Display, highlighter, ruler, and read-aloud with word highlighting; no AI cost</figcaption></figure>
  <figure><span class="badge">3</span>{img("trace_2_word_coach", "Word Coach card", 520, crop=(0, 760))}<figcaption><strong>Word Coach.</strong> Meaning in this sentence, at the reader's level</figcaption></figure>
  <figure><span class="badge">4</span>{img("trace_4_comprehension_coach", "Summary with questions", 520, crop=(0, 940))}<figcaption><strong>Comprehension Coach.</strong> Big idea, key points, and a quiz</figcaption></figure>
</div>"""
    return frame(5, "Solution", "One workspace takes a student from upload to understanding without leaving their own material",
                 body, "Source: screenshots captured from the running app (scripts/capture_screenshots.py), demo account, reader level 13–17.",
                 "Exhibit 3 · A study session in five steps")


def slide_architecture() -> str:
    body = f"""
<div class="g2 w64">
  <div class="panel">{svg_file(ROOT / "deliverables" / "agent_diagram.svg")}</div>
  <div class="stack">
    <div class="num-box"><span>1</span><p><strong>AI only where it adds value.</strong> Display, read-aloud, highlights, and folders cost $0.</p></div>
    <div class="num-box"><span>2</span><p><strong>Single-call, tool-less agents.</strong> One click = one call; no loops, so cost and failure modes are bounded.</p></div>
    <div class="num-box"><span>3</span><p><strong>One guard layer</strong> on every call: budget cap, input caps, <code>&lt;reading&gt;</code> delimiting, model check, logging.</p></div>
    <div class="num-box"><span>4</span><p><strong>One shared, cached prefix</strong> (safety rules + reader-level guide) across agents.</p></div>
    <div class="num-box"><span>5</span><p><strong>Student data stays local:</strong> accounts and saved work never reach the model.</p></div>
  </div>
</div>"""
    return frame(6, "Architecture", "Four single-call agents sit behind one guard layer, so cost and failure modes stay bounded",
                 body, "Source: app/services/ai.py, prompts/; per-call costs are measured warm-cache averages (output/tokenomics/summary.json).",
                 "Exhibit 4 · System architecture")


def slide_design() -> str:
    rows = [
        ("Agent structure", "Tool-using agent loop vs. single-call agents", "Single-call, tool-less", "Design choice: bounds cost per click and removes loop risk (red-team check passed)"),
        ("Output format", "Free text vs. JSON schema", "JSON schema for 3 of 4 agents", "Design choice: reliable rendering; all 3 injection attempts ignored or blocked"),
        ("Reasoning effort", "low vs. medium", "low", f"A/B tested: medium raised word-lookup cost {effort_cost:.0f}% and latency {effort_time:.0f}%"),
        ("Prompt design", "Short role prompts vs. shared cached guide", "Shared guide (~1,600-token prefix)", f"A/B tested: −{saving:.0%} per session; no quality loss in a 6-word check"),
        ("Model", "Course-mandated gpt-6-luna", "gpt-6-luna, verified per reply", "Constraint: small, fast model suits short structured tasks"),
    ]
    tbl = "".join(f"<tr><td><strong>{a}</strong></td><td>{b}</td><td class='pick'>{c}</td><td>{d}</td></tr>" for a, b, c, d in rows)
    bars = hbars_svg([
        ("Word Coach", pf["word_help"]["avg_cost_usd"] * 1000, f"{pf['word_help']['avg_seconds']:.1f} s"),
        ("Explainer", pf["explain"]["avg_cost_usd"] * 1000, f"{pf['explain']['avg_seconds']:.1f} s"),
        ("Comprehension Coach", pf["summarize"]["avg_cost_usd"] * 1000, f"{pf['summarize']['avg_seconds']:.1f} s"),
        ("AI Tutor", pf["tutor_chat"]["avg_cost_usd"] * 1000, f"{pf['tutor_chat']['avg_seconds']:.1f} s"),
    ], lambda v: f"${v:.2f}", width=560, highlight="Comprehension Coach")
    body = f"""
<div class="g2 w62">
  <table class="decisions"><thead><tr><th>Decision</th><th>Options considered</th><th>Choice</th><th>Basis</th></tr></thead><tbody>{tbl}</tbody></table>
  <div class="panel"><p class="side-h">Cost per 1,000 calls, and latency</p>{bars}<p class="legend">The summary is the costliest call because it writes the most output; it is used least often.</p></div>
</div>"""
    return frame(7, "Design", "Key design choices rest on evidence: two were A/B tested, and the rest bound cost and risk by construction",
                 body, "Source: scripts/measure_tokenomics.py and scripts/quality_check.py (warm-cache averages); scripts/safety_eval.py.",
                 "Exhibit 5 · Decision log and measured cost per agent",
                 "In both A/B tests the cheaper option carried no measured quality penalty (and low effort was also faster), so controlling cost did not trade off the student experience.")


def slide_economics() -> str:
    body = f"""
<div class="g2 w55">
  <div class="panel"><p class="side-h">Cost per 1,000 study sessions (16 calls each)</p>{waterfall_svg()}</div>
  <div class="stack">
    <table class="scale"><thead><tr><th>Monthly AI cost</th><th>1 user</th><th>100</th><th>10,000</th></tr></thead><tbody>
      <tr><td>Light (4 sessions)</td><td>{money(light['1'], 3)}</td><td>{money(light['100'], 2)}</td><td>{money(light['10000'], 0)}</td></tr>
      <tr class="hl"><td>Typical (12 sessions)</td><td>{money(typ['1'], 3)}</td><td>{money(typ['100'], 2)}</td><td>{money(typ['10000'], 0)}</td></tr>
      <tr><td>Heavy (30 sessions)</td><td>{money(heavy['1'], 3)}</td><td>{money(heavy['100'], 2)}</td><td>{money(heavy['10000'], 0)}</td></tr>
    </tbody></table>
    <div class="box"><p class="bh">Why caching worked</p><p>Prompts of ~650 tokens sat below the provider's 1,024-token caching minimum (0 cached tokens on every call). A shared ~1,600-token prefix now has {cached_share:.0%} of input billed at the cached rate (10× cheaper).</p></div>
    <div class="box"><p class="bh">Scale implication</p><p>The $2/day default cap protects a demo; at 10,000 typical users spend is ~{money(typ['10000'] / 30, 2)}/day, so the cap must become per-student.</p></div>
  </div>
</div>"""
    return frame(8, "Economics", f"Prompt caching cut session cost {saving:.0%}; 10,000 typical students would cost about {money(typ['10000'], 0)} a month in AI",
                 body, f"Source: measured with scripts/measure_tokenomics.py; gpt-6-luna prices per 1M tokens: input $0.10, cached $0.01, cache write $0.125, output $0.50. Usage levels (4 / 12 / 30 sessions a month) are assumptions.",
                 "Exhibit 6 · Unit economics")


def slide_risk() -> str:
    names = ["Prompt injection via uploaded text", "Invented facts", "Academic dishonesty (essay request)", "Student wellbeing disclosure",
             "Cross-account data access", "Account takeover", "Overspending", "Runaway calls / wrong model"]
    legend = "".join(f"<li><span>{i}</span>{n}</li>" for i, n in enumerate(names, 1))
    layers, layer_list = layers_svg()
    body = f"""
<div class="g3">
  <div class="panel"><p class="side-h">Risks before defenses</p>{heatmap_svg()}</div>
  <div><p class="side-h">Risk register</p><ol class="risks">{legend}</ol>
    <div class="result"><span class="mv">{passed}/{total_checks}</span><span class="ml">red-team checks passed, incl. 3 injection variants; replies saved for review</span></div></div>
  <div class="panel"><p class="side-h">Defense in depth</p>{layers}<ul class="layers">{layer_list}</ul></div>
</div>"""
    return frame(9, "Risk", f"Layered defenses stopped all {total_checks} red-team attacks, including prompt injection hidden in uploaded readings",
                 body, "Note: heat-map positions are the author's pre-mitigation assessment. Results: scripts/safety_eval.py (output/safety/results.md); two of three injection variants were blocked upstream by Azure's content filter.",
                 "Exhibit 7 · Risk heat map, register, and defense layers")


def slide_impact() -> str:
    body = f"""
<div class="kpis">
  <div><span class="mv">50–200</span><span class="ml">students in a 1,000-student school who could benefit (5–6% identified, up to 15–20% with symptoms)</span></div>
  <div><span class="mv">{money(typ['1'] * 1000, 0)}/mo</span><span class="ml">AI cost to serve 1,000 typical users; reading tools cost $0 per use</span></div>
  <div><span class="mv">{wl['avg_seconds']:.1f}–{pf['summarize']['avg_seconds']:.1f} s</span><span class="ml">measured response time, word lookup to full summary with quiz</span></div>
  <div><span class="mv">2 free</span><span class="ml">tutoring programs and 6 certified-practitioner registries surfaced to families</span></div>
</div>
<p class="side-h">Roadmap, including today's known limits</p>
<div class="panel">{roadmap_svg()}</div>
<p class="status">{EVAL_STATUS}. Pilot design: within-subject, counterbalanced passages (grade 5.9 / 6.9), timed reading, 3 scored comprehension questions, 6-item survey.</p>"""
    return frame(10, "Impact", "Low marginal cost makes school-wide access feasible; the next step is proving comprehension gains with users",
                 body, f"Source: IDA (prevalence); WordWise measurements; deliverables/user_testing/testing_kit.html. Repository: {REPO} · demo: python scripts/seed_demo.py, sign in as demo / wordwise-demo.",
                 "Exhibit 8 · Impact metrics and roadmap")


SLIDES = "".join([slide_title(), slide_summary(), slide_problem(), slide_landscape(), slide_solution(),
                  slide_architecture(), slide_design(), slide_economics(), slide_risk(), slide_impact()])

CSS = """
:root { --navy:#0F1F3D; --navy7:#1B3366; --navy5:#3C5A8F; --navy1:#DCE3F0; --green7:#24503A; --green6:#3F7350; --mint1:#E1F0DC; --cream:#FBF8F1; --cream1:#F4EEE1; --cream3:#E6DCC6; --brass:#B08D57; --brassd:#8A6630; --muted:#4A5874; }
.reveal-viewport { background:var(--cream); }
.reveal { font-family:"Atkinson Hyperlegible", Verdana, sans-serif; font-size:20px; color:var(--navy); line-height:1.38; }
.reveal .slides section { text-align:left; height:100%; box-sizing:border-box; }
.reveal h1, .reveal h2 { font-family:"Libre Baskerville", Georgia, serif; color:var(--navy7); letter-spacing:0; text-transform:none; }
.reveal strong { color:var(--navy7); } .reveal em { font-style:normal; font-weight:700; }
.reveal code { font-size:.85em; background:var(--cream1); padding:1px 6px; border-radius:5px; }
.reveal p { margin:0 0 8px; }
.reveal svg.exh { width:100%; height:auto; display:block; }

/* consulting frame */
.reveal section.cs { padding:26px 56px 66px; }
.reveal .tracker { display:flex; gap:6px; justify-content:flex-end; margin-bottom:10px; }
.reveal .tracker span { font-size:12px; padding:3px 10px; border-radius:999px; color:var(--muted); border:1px solid var(--cream3); }
.reveal .tracker span.on { background:var(--green7); color:var(--cream); border-color:var(--green7); font-weight:700; }
.reveal h2.action { font-size:31px; line-height:1.25; margin:0 0 6px; padding-bottom:12px; border-bottom:3px solid var(--brass); max-width:1480px; }
.reveal .exhibit { font-size:14px; font-weight:700; color:var(--brassd); letter-spacing:.04em; margin:10px 0 10px; }
.reveal .body { margin-top:14px; }
.reveal .source { position:absolute; left:56px; right:56px; bottom:40px; font-size:12.5px; color:var(--muted); line-height:1.3; margin:0; }
.reveal .foot { position:absolute; left:56px; right:150px; bottom:14px; display:flex; justify-content:space-between; font-size:12.5px; color:var(--muted); border-top:1px solid var(--cream3); padding-top:5px; }

/* layout */
.reveal .g2 { display:grid; grid-template-columns:1fr 1fr; gap:34px; align-items:start; }
.reveal .g2.w55 { grid-template-columns:1.2fr 1fr; } .reveal .g2.w62 { grid-template-columns:1.65fr 1fr; } .reveal .g2.w64 { grid-template-columns:1.75fr 1fr; }
.reveal .g3 { display:grid; grid-template-columns:1fr 0.95fr 1.05fr; gap:26px; align-items:start; }
.reveal .panel { background:#fff; border:1px solid var(--cream3); border-radius:12px; padding:14px 16px; }
.reveal .stack { display:flex; flex-direction:column; gap:12px; }
.reveal .box { background:var(--cream1); border-left:5px solid var(--green6); border-radius:8px; padding:12px 16px; }
.reveal .box p { font-size:17.5px; margin:0; } .reveal .box p.bh { font-weight:700; color:var(--navy7); font-size:18px; margin-bottom:4px; }
.reveal .side-h { font-family:"Libre Baskerville", Georgia, serif; font-weight:700; color:var(--navy7); font-size:18px; margin:0 0 10px; }
.reveal .num-box { display:grid; grid-template-columns:38px 1fr; gap:12px; align-items:start; }
.reveal .num-box span { width:34px; height:34px; border-radius:50%; background:var(--green7); color:var(--cream); font-weight:700; display:grid; place-items:center; font-size:17px; }
.reveal .num-box p { margin:4px 0 0; font-size:17.5px; }
.reveal .legend { font-size:14px; color:var(--muted); margin-top:8px; display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
.reveal .legend .hb { width:18px; height:18px; }

/* executive summary */
.reveal .scr { display:grid; grid-template-columns:1fr 1fr 1fr; gap:0; margin-top:6px; }
.reveal .scr > div { padding:18px 24px 20px; background:var(--cream1); border-right:2px solid var(--cream); position:relative; min-height:300px; }
.reveal .scr > div.res { background:var(--mint1); }
.reveal .scr p { font-size:19.5px; }
.reveal .scr-h { font-family:"Libre Baskerville", Georgia, serif; font-weight:700; color:var(--cream) !important; background:var(--green7); margin:-18px -24px 16px !important; padding:10px 24px; font-size:20px !important; clip-path:polygon(0 0, calc(100% - 22px) 0, 100% 50%, calc(100% - 22px) 100%, 0 100%); }
.reveal .res .scr-h { background:var(--brassd); }
.reveal .metrics, .reveal .kpis { display:grid; grid-template-columns:repeat(4, 1fr); gap:14px; margin-top:22px; }
.reveal .metrics div, .reveal .kpis div { border-top:4px solid var(--brass); background:#fff; border-radius:0 0 10px 10px; padding:12px 16px; box-shadow:0 1px 4px rgba(15,31,61,.08); }
.reveal .mv { display:block; font-family:"Libre Baskerville", Georgia, serif; font-weight:700; font-size:34px; color:var(--navy7); line-height:1.1; }
.reveal .ml { display:block; font-size:15.5px; color:var(--navy); margin-top:4px; line-height:1.3; }
.reveal .kpis { margin:0 0 18px; }

/* tables */
.reveal table { width:100%; border-collapse:collapse; margin:0; }
.reveal table th { background:var(--green7); color:var(--cream); text-align:left; padding:8px 10px; border:none; font-size:15px; font-weight:700; }
.reveal table td { padding:7px 10px; border:none; border-bottom:1px solid var(--cream3); vertical-align:middle; font-size:16px; }
.reveal table tr:nth-child(even) td { background:var(--cream1); }
.reveal table tr.hl td { background:var(--mint1); font-weight:700; }
.reveal table.matrix th { text-align:center; } .reveal table.matrix th:first-child { text-align:left; }
.reveal table.matrix td { font-size:17px; padding:9px 10px; } .reveal td.c { text-align:center; }
.reveal table.matrix tr.ours td { background:var(--mint1); font-weight:700; border-top:2px solid var(--green7); border-bottom:2px solid var(--green7); }
.reveal table.decisions td { font-size:15.5px; vertical-align:top; } .reveal td.pick { font-weight:700; color:var(--navy7); }
.reveal table.scale td { font-size:16.5px; }

/* solution */
.reveal .chevrons { display:flex; gap:4px; margin:2px 0 16px; }
.reveal .chev { flex:1; background:var(--green7); color:var(--cream); padding:10px 26px 10px 30px; font-size:15.5px; font-weight:700; display:flex; align-items:center; gap:10px; clip-path:polygon(0 0, calc(100% - 18px) 0, 100% 50%, calc(100% - 18px) 100%, 0 100%, 18px 50%); min-height:56px; line-height:1.25; }
.reveal .chev:first-child { clip-path:polygon(0 0, calc(100% - 18px) 0, 100% 50%, calc(100% - 18px) 100%, 0 100%); padding-left:16px; }
.reveal .chev:nth-child(even) { background:var(--navy5); }
.reveal .chev .n { width:26px; height:26px; flex:none; border-radius:50%; background:var(--brass); color:var(--navy); display:grid; place-items:center; font-size:14px; }
.reveal .shots3 { display:grid; grid-template-columns:2.3fr 1fr 1fr; gap:20px; }
.reveal figure { margin:0; position:relative; }
.reveal figure img { display:block; width:100%; height:430px; object-fit:contain; object-position:top; border:1px solid var(--cream3); border-radius:10px; background:var(--cream1); margin:0; max-width:100%; max-height:none; box-sizing:border-box; }
.reveal figcaption { font-size:15px; color:var(--navy); margin-top:6px; line-height:1.3; }
.reveal .badge { position:absolute; top:-10px; left:-10px; z-index:2; background:var(--brass); color:var(--navy); font-weight:700; font-size:14px; padding:4px 10px; border-radius:999px; border:2px solid var(--navy); }

/* risk */
.reveal ol.risks { list-style:none; margin:0 0 14px; padding:0; }
.reveal ol.risks li { display:grid; grid-template-columns:30px 1fr; gap:10px; align-items:center; font-size:16px; margin:0 0 7px; }
.reveal ol.risks li span { width:26px; height:26px; border-radius:50%; background:var(--brass); border:2px solid var(--navy); font-weight:700; display:grid; place-items:center; font-size:13px; }
.reveal .result { background:var(--green7); border-radius:10px; padding:12px 16px; }
.reveal .result .mv { color:var(--cream); } .reveal .result .ml { color:var(--cream1); }
.reveal ul.layers { margin:10px 0 0 1em; } .reveal ul.layers li { font-size:14.5px; margin-bottom:4px; }

/* implication banner */
.reveal .implication { margin-top:22px; display:grid; grid-template-columns:150px 1fr; align-items:stretch; border-radius:10px; overflow:hidden; box-shadow:0 1px 4px rgba(15,31,61,.12); }
.reveal .implication span { background:var(--brassd); color:var(--cream); font-weight:700; font-size:16px; display:grid; place-items:center; letter-spacing:.04em; }
.reveal .implication p { background:var(--green7); color:var(--cream); margin:0; padding:14px 20px; font-size:19px; line-height:1.35; }

/* impact */
.reveal .status { margin-top:12px; font-size:16px; background:var(--cream1); border:2px dashed var(--brass); border-radius:10px; padding:9px 14px; }

/* title */
.reveal section.title { color:var(--cream); padding:90px 90px; background-image:radial-gradient(rgba(251,248,241,.08) 3px, transparent 3px); background-size:32px 32px; }
.reveal section.title h1 { font-size:120px; color:var(--cream); margin:14px 0 18px; }
.reveal .eyebrow { font-size:22px; font-weight:700; color:var(--brass); letter-spacing:.06em; margin:0; }
.reveal section.title .pitch { font-size:31px; color:var(--cream1); max-width:1060px; line-height:1.35; margin-bottom:22px; }
.reveal section.title .origin { font-size:21px; color:var(--cream); max-width:1060px; line-height:1.4; margin:0 0 18px; padding:10px 16px; border-left:4px solid var(--brass); background:rgba(225,240,220,.10); }
.reveal .box.founder { background:var(--mint1); border-left-color:var(--brass); }
.reveal section.title .origin strong { color:var(--brass); }
.reveal section.title .byline { font-size:21px; color:var(--cream3); }
.reveal section.title .chips { display:flex; gap:14px; margin-top:30px; flex-wrap:wrap; max-width:920px; }
.reveal section.title .chips span { font-size:18px; padding:8px 16px; border:2px solid var(--brass); border-radius:999px; color:var(--cream); }
.reveal section.title code { background:rgba(251,248,241,.14); color:var(--cream); }
.reveal section.title .skyline { position:absolute; right:60px; bottom:50px; width:500px; border:none; }
.reveal .slide-number { display:none; }
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
