"""Render every slide of deliverables/slides.html and flag anything that overflows or is cut off.

Usage, from the project folder (needs playwright + Microsoft Edge):
    python scripts/check_slides.py            # writes PNGs to output/slide_check/
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "slide_check"

OVERFLOW_JS = """() => {
  const s = Reveal.getCurrentSlide(); const box = s.getBoundingClientRect(); const scale = Reveal.getScale();
  const out = [];
  s.querySelectorAll('*').forEach(el => {
    if (el.closest('svg') && el.tagName !== 'svg') return;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) return;
    const pos = getComputedStyle(el).position;
    if (r.right > box.right + 2 || r.bottom > box.bottom + 2 || r.left < box.left - 2)
      out.push(`${el.tagName.toLowerCase()}.${(el.className && el.className.baseVal === undefined ? el.className : '').toString().slice(0, 20)} ` +
               `overflows by ${Math.round(Math.max(r.right - box.right, r.bottom - box.bottom, box.left - r.left) / scale)}px`);
    if (el.scrollHeight > el.clientHeight + 4 && ['hidden', 'clip'].includes(getComputedStyle(el).overflowY))
      out.push(`${el.tagName.toLowerCase()} content clipped`);
  });
  return [...new Set(out)].slice(0, 6);
}"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    problems = 0
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 1600, "height": 900})
        pg.goto((ROOT / "deliverables" / "slides.html").as_uri())
        pg.wait_for_timeout(1200)
        n = pg.evaluate("Reveal.getTotalSlides()")
        for i in range(n):
            pg.evaluate(f"Reveal.slide({i})")
            pg.wait_for_timeout(700)
            issues = pg.evaluate(OVERFLOW_JS)
            pg.screenshot(path=str(OUT / f"slide_{i + 1:02d}.png"))
            print(f"slide {i + 1:2d}: {'OK' if not issues else 'ISSUES: ' + '; '.join(issues)}")
            problems += bool(issues)
        b.close()
    print(f"{n} slides, {problems} with issues. Images in {OUT.relative_to(ROOT)}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
