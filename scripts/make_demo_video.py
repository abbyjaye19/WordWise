"""Record a narrated, captioned demo walkthrough of WordWise (about 3 minutes).

Usage, from the project folder (needs PORTKEY_API_KEY for the AI steps; dev tools only):
    pip install playwright edge-tts imageio-ffmpeg
    python scripts/make_demo_video.py

What it does
  1. Writes the narration for each scene with a natural Microsoft neural voice (edge-tts) and
     measures how long each line takes.
  2. Starts its own copy of the app with a throwaway database and the demo account (your real
     accounts are never touched), then drives a real Edge browser through one study session,
     showing a pointer and an on-screen caption for every line of narration.
  3. Lines the narration up with the recording and saves deliverables/demo_video.mp4.
The narrator is an AI voice; the app, the clicks, and every AI answer on screen are real.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from capture_screenshots import seed, start_server, stop_server  # noqa: E402  (same throwaway-server helpers)

import capture_screenshots  # noqa: E402

PORT = 8062
capture_screenshots.PORT = PORT
capture_screenshots.BASE = BASE = f"http://127.0.0.1:{PORT}"
OUT = ROOT / "deliverables" / "demo_video.mp4"
VOICE, RATE = "en-US-AvaNeural", "-4%"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
DEMO_PDF = ROOT / "data" / "sample" / "demo_professor_email.pdf"
AI_WAIT = 90_000

# A visible pointer (screen recordings don't show the mouse) and a caption bar for the narration.
OVERLAY = """
(() => {
  const css = `#demo-cursor{position:fixed;z-index:99999;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;
    background:rgba(176,141,87,.55);border:2px solid #0F1F3D;pointer-events:none;transition:transform .12s;left:-50px;top:-50px}
    #demo-cursor.down{transform:scale(.6);background:rgba(36,80,58,.75)}
    #demo-cap{position:fixed;z-index:99998;left:50%;bottom:22px;transform:translateX(-50%);max-width:1100px;width:calc(100% - 160px);
    background:rgba(15,31,61,.92);color:#FBF8F1;font:600 21px/1.4 "Atkinson Hyperlegible",Verdana,sans-serif;padding:12px 22px;
    border-radius:12px;border-left:6px solid #B08D57;box-shadow:0 6px 24px rgba(15,31,61,.35);pointer-events:none}
    #demo-cap:empty{display:none} .tutor-fab{display:none!important}`;
  const add = () => {
    if (document.getElementById("demo-cursor")) return;
    const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
    const c = document.createElement("div"); c.id = "demo-cursor"; document.body.appendChild(c);
    const cap = document.createElement("div"); cap.id = "demo-cap"; document.body.appendChild(cap);
    if (window.__capText) cap.textContent = window.__capText;
  };
  document.addEventListener("DOMContentLoaded", add);
  document.addEventListener("mousemove", e => { const c = document.getElementById("demo-cursor"); if (c) { c.style.left = e.clientX + "px"; c.style.top = e.clientY + "px"; } }, true);
  document.addEventListener("mousedown", () => { const c = document.getElementById("demo-cursor"); if (c) c.classList.add("down"); }, true);
  document.addEventListener("mouseup", () => { const c = document.getElementById("demo-cursor"); if (c) c.classList.remove("down"); }, true);
  window.__setCap = t => { window.__capText = t; add(); const cap = document.getElementById("demo-cap"); if (cap) cap.textContent = t; };
  try { localStorage.setItem("ww-voice", ""); } catch (e) {}
})();
"""


# ---------- browser helpers ----------

def caption(page: Page, text: str) -> None:
    page.evaluate("t => window.__setCap && window.__setCap(t)", text)


def glide(page: Page, selector, click: bool = True, nth: int = 0) -> None:
    """Move the visible pointer to an element (smoothly), then click it. `selector` may be a CSS string or a Locator."""
    el = page.locator(selector).nth(nth) if isinstance(selector, str) else selector
    el.scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    for _ in range(4):  # the sticky toolbar can sit on top of a target: scroll until it's really visible
        box = el.bounding_box()
        hit = el.evaluate("""(t, [x, y]) => { const e = document.elementFromPoint(x, y);
                                 return !!(e && (t === e || t.contains(e) || e.contains(t))); }""",
                          [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
        if hit:
            break
        page.evaluate("window.scrollBy({top: -260, behavior: 'smooth'})")
        page.wait_for_timeout(700)
    box = el.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=22)
    page.wait_for_timeout(250)
    if click:
        page.mouse.down(); page.wait_for_timeout(90); page.mouse.up()
        page.wait_for_timeout(350)


def smooth_scroll(page: Page, y: int, ms: int = 1200) -> None:
    page.evaluate("y => window.scrollTo({top: y, behavior: 'smooth'})", y)
    page.wait_for_timeout(ms)


def scroll_to(page: Page, selector: str, offset: int = 90) -> None:
    y = page.evaluate("([s, o]) => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().top + scrollY - o : 0; }", [selector, offset])
    smooth_scroll(page, y)


def select_text(page: Page, contains: str, first_word: int, last_word: int) -> None:
    """Select words [first_word, last_word] of the paragraph that contains `contains` (like a student dragging)."""
    page.evaluate("""([needle, a, b]) => {
        const p = [...document.querySelectorAll('#reader .r-p')].find(x => x.textContent.includes(needle));
        p.scrollIntoView({block: 'center'});
        const ws = p.querySelectorAll('.w'); const r = document.createRange();
        r.setStart(ws[a].firstChild, 0); r.setEnd(ws[b].firstChild, ws[b].textContent.length);
        const s = getSelection(); s.removeAllRanges(); s.addRange(r);
        document.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
    }""", [contains, first_word, last_word])


# ---------- the walkthrough: (narration, action) ----------

def s_home(p):
    p.goto(BASE); p.wait_for_selector("h1"); caption(p, NARR[0][0])
    p.wait_for_timeout(1500); scroll_to(p, ".founder-card", 200)


def s_signin(p):
    p.goto(f"{BASE}/account"); p.wait_for_selector("#signin-id"); caption(p, NARR[1][0])
    glide(p, "#signin-id"); p.keyboard.type("demo", delay=90)
    glide(p, "#signin-password"); p.keyboard.type("wordwise-demo", delay=60)
    glide(p, "#signin-btn"); p.wait_for_timeout(1500)


def s_upload(p):
    p.goto(f"{BASE}/reading-assistant"); p.wait_for_selector("#doc-upload"); caption(p, NARR[2][0])
    glide(p, "#doc-upload", click=False)
    p.set_input_files("#doc-upload input[type=file]", str(DEMO_PDF))
    p.wait_for_selector("#reader .w", timeout=20000); p.wait_for_timeout(800)
    scroll_to(p, "#tool-guide", 100)


def s_guide(p):
    caption(p, NARR[3][0]); p.wait_for_timeout(2500)
    glide(p, "#tool-guide > summary"); scroll_to(p, "#studio-toolbar", 100)


def s_settings(p):
    caption(p, NARR[4][0])
    glide(p, "#a11y-open")
    glide(p, "#pref-size label:has(input[value=l])")
    glide(p, "#pref-spacing label:has(input[value=wide])")
    glide(p, "#pref-theme label:has(input[value=green])")
    glide(p, "#pref-linewidth label:has(input[value=narrow])")
    glide(p, "#a11y-close"); scroll_to(p, "#reader", 140)


def s_readalong(p):
    caption(p, NARR[5][0])
    para = p.locator("#reader .r-p", has_text="cumulative").first
    para.evaluate("e => e.scrollIntoView({block: 'center'})"); p.wait_for_timeout(600)
    glide(p, "#mode-read")
    glide(p, para.locator(".w").first)  # "Read from there": start on a sentence that's in view
    p.wait_for_timeout(4500)
    glide(p, "#tts-faster"); p.wait_for_timeout(3000)
    glide(p, "#tts-stop"); glide(p, "#mode-lookup")


def s_word(p):
    caption(p, NARR[6][0])
    glide(p, "#reader .w:text-is('cumulative')")
    p.wait_for_selector("#word-output .word-title", timeout=AI_WAIT); p.wait_for_timeout(500)
    scroll_to(p, "#word-output", 160); p.wait_for_timeout(2500)


def s_explain(p):
    caption(p, NARR[7][0]); scroll_to(p, "#reader", 140)
    select_text(p, "accommodations", 0, 42); p.wait_for_timeout(1500)
    glide(p, "#explain-steps")
    p.wait_for_selector("#explain-output .ai-answer", timeout=AI_WAIT); p.wait_for_timeout(700)
    p.locator("#explain-output").scroll_into_view_if_needed(); p.wait_for_timeout(2500)


def s_levels(p):
    caption(p, NARR[8][0]); scroll_to(p, "#level-bar", 120)
    glide(p, "#view-simplified")
    p.wait_for_selector("#reader .r-ai-banner", timeout=AI_WAIT); p.wait_for_timeout(800)
    glide(p, "#view-showorig"); scroll_to(p, "#reader", 120); p.wait_for_timeout(3500)
    smooth_scroll(p, p.evaluate("scrollY") + 420, 1800)


def s_checkin(p):
    caption(p, NARR[9][0]); glide(p, "#view-original")
    scroll_to(p, "#checkin", 140)
    glide(p, "#check-rating label:has(input[value='3'])")
    glide(p, "#check-hard label:has(input[value=long_sentences])")
    glide(p, "#check-save"); p.wait_for_timeout(1500)


def s_tutor(p):
    p.goto(f"{BASE}/ai-tutor"); p.wait_for_selector("#chat-input"); caption(p, NARR[10][0])
    glide(p, "#chat-input"); p.keyboard.type("When I read, the lines blur together and the voice is too fast for me.", delay=28)
    glide(p, "#chat-send")
    p.wait_for_selector(".sugg-card", timeout=AI_WAIT); p.wait_for_timeout(800)
    p.locator(".sugg-card").scroll_into_view_if_needed(); p.wait_for_timeout(1500)
    glide(p, ".sugg-row button:has-text('Apply')"); p.wait_for_timeout(2500)


def s_dashboard(p):
    p.goto(f"{BASE}/dashboard"); p.wait_for_selector(".reading-card"); caption(p, NARR[11][0])
    p.wait_for_timeout(1200); scroll_to(p, "#insights", 90); p.wait_for_timeout(3500)
    scroll_to(p, "#profile", 90); p.wait_for_timeout(3000)


def s_support(p):
    p.goto(f"{BASE}/tutors"); p.wait_for_selector("h1"); caption(p, NARR[12][0])
    p.wait_for_timeout(1800); smooth_scroll(p, 900, 2000)
    p.goto(f"{BASE}/resources"); p.wait_for_selector("h1"); caption(p, NARR[12][0]); p.wait_for_timeout(1500)
    smooth_scroll(p, 700, 1800)


def s_close(p):
    p.goto(f"{BASE}/about"); p.wait_for_selector("h1"); caption(p, NARR[13][0])
    p.wait_for_timeout(1500); smooth_scroll(p, 260, 1500)


NARR = [
    ("This is WordWise, an AI reading studio for students with dyslexia. It was built by Abby Jaye, who has double-deficit dyslexia, as the tool she wished she had growing up.", s_home),
    ("A grader can sign in with the demo account. Everything you see next is the real app, running on a laptop.", s_signin),
    ("A student uploads something they actually have to read. Here, a busy email from a professor about a midterm.", s_upload),
    ("On a first visit, a quick guide explains every tool right where the student will use it.", s_guide),
    ("Reading settings change the whole site: bigger text, wider spacing, a soft green background, and shorter lines. They're saved to the student's account.", s_settings),
    ("Read-along speaks the text and highlights each sentence and word as it goes. Speed can change while it's reading.", s_readalong),
    ("Tapping a word asks the Word Coach. It explains the meaning in this sentence, at the student's level, with syllables and how to say it.", s_word),
    ("Selecting a passage and choosing Break it into steps turns dense rules into short, ordered steps, right under the button, and labeled as AI.", s_explain),
    ("Reading Levels rewrites the whole email in simpler wording, with the original one tap away under each paragraph, so the meaning can always be checked.", s_levels),
    ("After reading, a quick check-in records how well the student understood it and what made it hard.", s_checkin),
    ("The AI Tutor helps students find settings that work for them. It suggests changes, and nothing changes until the student taps Apply.", s_tutor),
    ("The dashboard turns all of this into insights, and the student's own profile of what they find hard shapes every AI answer.", s_dashboard),
    ("WordWise is also a home base for help: trusted resources, and real places to find a tutor or specialist.", s_support),
    ("Six focused AI agents, about two and a half cents per student per month, fifteen of fifteen safety checks passed, and shaped by real users. That's WordWise.", s_close),
]


# ---------- narration audio ----------

async def _speak(text: str, path: Path) -> None:
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(path))


def make_audio(tmp: Path) -> list[tuple[Path, float]]:
    clips = []
    for i, (text, _) in enumerate(NARR):
        mp3, wav = tmp / f"n{i:02d}.mp3", tmp / f"n{i:02d}.wav"
        asyncio.run(_speak(text, mp3))
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", "44100", "-ac", "1", str(wav)], check=True)
        with wave.open(str(wav)) as w:
            clips.append((wav, w.getnframes() / w.getframerate()))
    return clips


# ---------- record + mix ----------

def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    print("Writing narration...")
    clips = make_audio(tmp)
    print(f"  {len(clips)} lines, {sum(d for _, d in clips):.0f} s of narration")
    db = tmp / "demo.db"
    seed(db)
    server = start_server(db)
    starts = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, record_video_dir=str(tmp),
                                      record_video_size={"width": 1440, "height": 900})
            ctx.add_init_script(OVERLAY)
            page = ctx.new_page()
            t0 = time.perf_counter()
            page.set_default_timeout(30_000)
            for i, ((text, action), (_, dur)) in enumerate(zip(NARR, clips)):
                start = time.perf_counter() - t0
                starts.append(start)
                print(f"  scene {i + 1:2d} at {start:6.1f}s: {text[:60]}...")
                action(page)
                caption(page, text)
                left = dur + 0.6 - (time.perf_counter() - t0 - start)
                if left > 0:
                    page.wait_for_timeout(int(left * 1000))
            page.wait_for_timeout(1500)
            video = Path(page.video.path())
            ctx.close()
            browser.close()
    finally:
        stop_server(server)

    print("Mixing narration into the video...")
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", str(video)]
    for wav, _ in clips:
        cmd += ["-i", str(wav)]
    delays = "".join(f"[{i + 1}:a]adelay={int(s * 1000)}|{int(s * 1000)}[a{i}];" for i, s in enumerate(starts))
    mix = "".join(f"[a{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0:duration=longest[aout]"
    cmd += ["-filter_complex", delays + mix, "-map", "0:v", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print(f"Saved {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
