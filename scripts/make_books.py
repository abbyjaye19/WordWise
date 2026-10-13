"""Regenerate the WordWise book illustrations into app/assets/ (plain SVG, palette colors).

Usage:  python scripts/make_books.py app/assets
"""
import random
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
INK = "#0F1F3D"
COLORS = ["#1B3366", "#5B7FBF", "#4F7A5A", "#B08D57", "#A2463A", "#6B4E8A", "#2E4F8A", "#7A9A6E"]
LIGHT = "#F4EEE1"
GOLD_LIGHT = "#E9D3A6"
WOOD = "#8A6630"
WOOD_DARK = "#6E5025"


def book_spine(x, w, h, base, color, rng):
    y = base - h
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{color}" stroke="{INK}" stroke-width="2"/>']
    # gold/cream bands near top and bottom
    band = GOLD_LIGHT if color != "#B08D57" else LIGHT
    parts.append(f'<rect x="{x + 2}" y="{y + 8}" width="{w - 4}" height="3" fill="{band}"/>')
    parts.append(f'<rect x="{x + 2}" y="{base - 12}" width="{w - 4}" height="3" fill="{band}"/>')
    # a label plate on wider books
    if w >= 22 and rng.random() < 0.6:
        lh = rng.randint(14, 22)
        parts.append(f'<rect x="{x + 5}" y="{y + h * 0.35:.0f}" width="{w - 10}" height="{lh}" rx="2" fill="{LIGHT}" stroke="{INK}" stroke-width="1.5"/>')
    elif rng.random() < 0.5:
        parts.append(f'<circle cx="{x + w / 2}" cy="{y + h * 0.45:.0f}" r="{min(4, w / 4):.1f}" fill="{band}"/>')
    return "".join(parts)


def bookshelf(width=1200, height=128, seed=7):
    rng = random.Random(seed)
    base = 108
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMax slice" role="presentation">']
    x = 6
    last = None
    while x < width - 40:
        r = rng.random()
        if r < 0.06:  # a small horizontal stack
            for i, h in enumerate((14, 12, 16)):
                w = rng.randint(54, 70)
                c = rng.choice(COLORS)
                yy = base - sum((14, 12, 16)[: i + 1])
                parts.append(f'<rect x="{x + rng.randint(-3, 3)}" y="{yy}" width="{w}" height="{h}" rx="3" fill="{c}" stroke="{INK}" stroke-width="2"/>')
                parts.append(f'<line x1="{x + 6}" y1="{yy + h / 2}" x2="{x + w - 6}" y2="{yy + h / 2}" stroke="{GOLD_LIGHT}" stroke-width="2" stroke-linecap="round"/>')
            x += 80
            continue
        if r < 0.10:  # a leaning book
            w, h = rng.randint(16, 24), rng.randint(70, 90)
            c = rng.choice(COLORS)
            parts.append(f'<g transform="rotate(14 {x} {base})">{book_spine(x, w, h, base, c, rng)}</g>')
            x += w + 22
            continue
        w = rng.choice([14, 16, 18, 20, 22, 24, 26, 30])
        h = rng.randint(62, 96)
        c = rng.choice([k for k in COLORS if k != last])
        last = c
        parts.append(book_spine(x, w, h, base, c, rng))
        x += w + 2  # 2px gap between spines
        if rng.random() < 0.05:
            x += rng.randint(16, 30)
    # shelf plank
    parts.append(f'<rect x="0" y="{base}" width="{width}" height="12" fill="{WOOD}" stroke="{INK}" stroke-width="2"/>')
    parts.append(f'<rect x="0" y="{base + 12}" width="{width}" height="8" fill="{WOOD_DARK}"/>')
    parts.append("</svg>")
    return "".join(parts)


def book_stack():
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 150" role="presentation" fill="none" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round">']
    books = [  # x, y, w, h, color
        (12, 118, 146, 24, "#1B3366"),
        (22, 94, 128, 24, "#B08D57"),
        (8, 70, 140, 24, "#4F7A5A"),
        (26, 46, 118, 24, "#A2463A"),
    ]
    for x, y, w, h, c in books:
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{c}"/>')
        # page edges on the right
        s.append(f'<rect x="{x + w - 22}" y="{y + 4}" width="18" height="{h - 8}" rx="2" fill="{LIGHT}" stroke-width="1.5"/>')
        for k in range(1, 4):
            yy = y + 4 + k * (h - 8) / 4
            s.append(f'<line x1="{x + w - 20}" y1="{yy:.1f}" x2="{x + w - 6}" y2="{yy:.1f}" stroke-width="1"/>')
        s.append(f'<line x1="{x + 10}" y1="{y + h / 2}" x2="{x + w - 34}" y2="{y + h / 2}" stroke="{GOLD_LIGHT}" stroke-width="3"/>')
    # small open book on top
    s.append(f'<path d="M48 44 Q66 30 85 40 Q104 30 122 44 L122 46 L48 46 Z" fill="{LIGHT}"/>')
    s.append('<path d="M85 40 L85 46"/>')
    s.append('<path d="M56 41 Q66 35 78 39 M92 39 Q104 35 114 41" stroke-width="1.5"/>')
    # ribbon bookmark
    s.append(f'<path d="M120 70 L120 98 L114 92 L108 98 L108 70" fill="#6B4E8A" stroke-width="2"/>')
    s.append("</svg>")
    return "".join(s)


def open_book():
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 92" role="presentation" fill="none" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round">'
        f'<path d="M8 22 L8 82 Q40 72 70 84 Q100 72 132 82 L132 22" fill="#1B3366"/>'
        f'<path d="M14 14 Q42 6 70 20 L70 78 Q42 64 14 72 Z" fill="{LIGHT}"/>'
        f'<path d="M126 14 Q98 6 70 20 L70 78 Q98 64 126 72 Z" fill="{LIGHT}"/>'
        '<path d="M24 26 Q42 20 60 28 M24 36 Q42 30 60 38 M24 46 Q42 40 60 48 M24 56 Q38 51 50 56" stroke-width="1.6"/>'
        '<path d="M80 28 Q98 20 116 26 M80 38 Q98 30 116 36 M80 48 Q98 40 116 46" stroke-width="1.6"/>'
        f'<path d="M100 12 L100 32 L104 28 L108 32 L108 10" fill="#B08D57" stroke-width="2"/>'
        "</svg>"
    )


(OUT / "bookshelf.svg").write_text(bookshelf(), encoding="utf-8")
(OUT / "book-stack.svg").write_text(book_stack(), encoding="utf-8")
(OUT / "open-book.svg").write_text(open_book(), encoding="utf-8")
print("wrote 3 svgs")
