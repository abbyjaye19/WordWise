---
name: wordwise-design
description: WordWise visual design system (navy + cream, formal but friendly, dyslexia-friendly, playful polka dots/geometric shapes, optional Yale campus line art). Use whenever building or styling ANY part of the WordWise project — app pages, components, CSS, Dash layouts, charts, report.html, or slides.html. Overrides the default black-pink style.
---

# WordWise Design System

**Feel:** formal and trustworthy, like a well-run university office, but warm, calm, and easy to use. Professional first, with small touches of fun. **Do not use the black-pink theme anywhere in this project.**

Apply this to the app, `deliverables/report.html`, and `deliverables/slides.html` so all three look like one product.

## 1. Color palette

| Token | Hex | Use |
|---|---|---|
| `--navy-900` | `#0F1F3D` | Main text, header/footer background |
| `--navy-700` | `#1B3366` | Primary buttons, headings, links |
| `--navy-500` | `#3C5A8F` | Hover states, secondary accents, icons |
| `--navy-100` | `#DCE3F0` | Selected states, soft highlights, tags |
| `--cream-50` | `#FBF8F1` | Page background (off-white cream; never pure `#FFF`) |
| `--cream-100` | `#F4EEE1` | Cards, panels, reading surface |
| `--cream-300` | `#E6DCC6` | Borders, dividers, polka-dot color on cream |
| `--brass-500` | `#B08D57` | Small accents only: rules, badges, the "verified" mark |
| `--sage-600` | `#4F7A5A` | Success |
| `--brick-600` | `#A2463A` | Errors and warnings (pair it with an icon and text, never color alone) |

Rules:
- Use navy for content and cream for surfaces. Brass is a sparing accent and should cover less than 5% of any screen.
- Body text is `--navy-900` on `--cream-50` or `--cream-100`, which passes WCAG AAA contrast. Keep every text pair at or above 4.5:1.
- Never put text on a busy pattern. Patterns sit only behind empty areas or behind a solid panel.

```css
:root {
  --navy-900:#0F1F3D; --navy-700:#1B3366; --navy-500:#3C5A8F; --navy-100:#DCE3F0;
  --cream-50:#FBF8F1;  --cream-100:#F4EEE1; --cream-300:#E6DCC6;
  --brass-500:#B08D57; --sage-600:#4F7A5A; --brick-600:#A2463A;
  --font-display:"Libre Baskerville", Georgia, serif;
  --font-body:"Atkinson Hyperlegible", "Lexend", Verdana, sans-serif;
  --radius:12px; --shadow:0 2px 10px rgba(15,31,61,.08);
}
```

## 2. Typography (formal and readable)

- **Headings:** `Libre Baskerville`, a serif face that gives the formal, collegiate look. Use it only for headings and the logo.
- **Body and UI:** `Atkinson Hyperlegible` (fallback `Lexend`). Both were designed for legibility and work well for readers with dyslexia.
- Load both from Google Fonts. In `report.html` and `slides.html`, keep the system fallbacks so the files still look right offline.
- Base body size is 18px, line-height is 1.6, and lines stay under about 70 characters (`max-width: 68ch`).
- Text is left-aligned. **Never justify text, and never italicize body text.** Use bold for emphasis.
- Use sentence case for headings and buttons. Avoid writing whole lines in capitals.

## 3. Layout and components

- Use generous white space, an 8px spacing scale, and a centered content column (max width about 1100px).
- **Header:** solid `--navy-900` bar with the WordWise logo in cream serif type, plus a thin brass rule underneath.
- **Cards:** `--cream-100` background, 1px `--cream-300` border, `--radius` corners, and a soft shadow.
- **Primary button:** `--navy-700` background, cream text, 12px×20px padding, slightly rounded corners, with a visible focus ring (`outline: 3px solid var(--brass-500)`).
- **Secondary button:** cream background, navy border and text.
- Pair every button and nav item with a **text label**. Icons are optional extras, never the only cue.
- **AI-generated text** always sits in a visually distinct panel: a `--navy-100` background, a left border in `--navy-500`, and a small "AI explanation" label. It always appears next to the original text, never replacing it.
- **Navigation:** at most 5 top-level items, each with a plain-language label (for example "Read", "Explain", "Resources", "Find a tutor", "My dashboard").
- Interactive targets are at least 44px tall. Every interaction must work with the keyboard alone.

## 4. Fun touches (polka dots and geometry)

Keep these subtle, decorative, and at low contrast. They should never compete with reading.

```css
/* Polka dots for hero bands, empty states, and slide backgrounds */
.dots { background-color:var(--cream-50);
  background-image:radial-gradient(var(--cream-300) 2px, transparent 2px);
  background-size:22px 22px; }
.dots-navy { background-color:var(--navy-900);
  background-image:radial-gradient(rgba(251,248,241,.10) 2px, transparent 2px);
  background-size:22px 22px; }
```

- **Geometric accents:** use simple CSS or inline-SVG circles, half-circles, quarter-arcs, and diamonds in navy, cream, and brass. Place them in hero corners, section dividers, and slide title cards.
- A thin brass diamond or line divider (`◆` between rules) works as the formal section break.
- On reading surfaces, use **no patterns**. The Reading Studio stays calm and plain.
- Respect `prefers-reduced-motion` and keep any animation subtle (a fade or slide of 200ms or less).

## 5. Yale / campus illustration (tentative, may change)

- Optional: an illustrated skyline in cartoon line-art style, showing for example Harkness Tower, Sterling Memorial Library, and the Old Campus gates.
- Build it as **inline SVG or HTML/CSS shapes, never a generated or downloaded image**. Use navy strokes on cream or cream strokes on navy, with flat shapes and rounded line caps.
- Use it in the hero/landing band, in the footer, and on the title slide. Never place it behind body text.
- **Do not use official Yale logos, the shield, or wordmarks.** The illustrations are original, generic collegiate art.
- Keep it in one reusable component (for example `app/assets/skyline.svg` or a single function) so it is easy to swap out if the direction changes.

## 5b. Cartoon library books (in use)

- The library theme uses three illustrations, all generated as plain SVG by `scripts/make_books.py`:
  - `app/assets/bookshelf.svg`: a shelf strip above the footer on every page
  - `book-stack.svg`: at the right of page headers
  - `open-book.svg`: in empty states and callouts
- Style: chunky navy (#0F1F3D) outlines, palette-colored spines (navy, sky, green, gold, red, purple) with gold or cream bands, and a wooden shelf in #8A6630.
- They are decorative only (`alt=""` or `aria-hidden`), hidden on narrow screens and in print, and never placed behind text. Reuse these files instead of drawing new styles.

## 6. Voice and microcopy

- Write in plain, warm, respectful language at about an 8th-grade reading level. Use short sentences and one idea per sentence.
- Say "Make this simpler" rather than "Simplify the selected passage." Say "We couldn't read that file. Try a .txt or .pdf." rather than "Error 415."
- Never imply a diagnosis. Never label a tutor "verified" unless they actually are.

## 7. Charts, report, and slides

- **Chart series:** `--navy-700`, `--brass-500`, `--navy-500`, `--sage-600`, `--cream-300`, plotted on a cream background with navy axis text.
- **`report.html`:** cream page, navy serif headings, brass rules between sections, with print styles for letter-size paper.
- **`slides.html` (reveal.js):**
  - Title and section slides use a navy background with polka dots.
  - Content slides use a cream background.
  - Text is large (at least 32px body).
  - The skyline appears on the title slide.

## Checklist before shipping any screen

- [ ] Only palette colors are used, with no black-pink anywhere
- [ ] Body text is at least 18px, line-height at least 1.5, left-aligned, with no italics
- [ ] Every text pair has contrast of at least 4.5:1
- [ ] Every button has a text label and a visible focus ring
- [ ] AI text is visually distinct and sits next to the original
- [ ] Patterns and illustrations never sit behind text
