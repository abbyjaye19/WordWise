"""What each reading tool does, written once and shown in two places:
the "Quick guide" inside the Reading Studio (where students actually use the tools) and the Tool Guide page.
"""

from __future__ import annotations

from dash import dcc, html

# (group, where to find it, [(tool, what it does)])
GUIDE = [
    ("Reading level", "Bar above your reading", [
        ("Original", "Your reading exactly as written."),
        ("Simplified wording", "The same meaning in easier words and shorter sentences, written by AI."),
        ("Detailed explanation", "The same ideas explained more fully, with key terms defined."),
        ("Show original too", "Puts the real text under each AI paragraph so you can compare."),
    ]),
    ("Listen", "Toolbar", [
        ("▶ Read aloud", "Reads to you and highlights each sentence and word as it's spoken."),
        ("⏮ ⟲ ⏭", "Go back a sentence, replay this sentence, or skip ahead."),
        ("− Speed +", "Slower or faster, even while it's reading."),
        ("Voice", "Pick the voice you like best. The ★ one sounds the most natural."),
        ("Highlight", "Choose word, sentence, or both."),
    ]),
    ("Tap a word", "Toolbar, then tap a word", [
        ("Look it up", "What the word means in this sentence, its syllables, and how to say it. Save it to your word bank."),
        ("Highlight", "Mark words with a yellow, green, or blue marker. Saved with your reading."),
        ("Read from there", "Start reading aloud from the word you tap."),
    ]),
    ("Stay focused", "Toolbar", [
        ("Reading ruler", "A band that follows your line so you don't lose your place."),
        ("One paragraph", "Fades everything except the paragraph you're on."),
        ("Aa Text settings", "Text size, font, spacing, background, contrast, and line length."),
    ]),
    ("Get help", "Panel on the right", [
        ("Understand a part", "Drag across a sentence, then pick: simpler, an example, or steps."),
        ("Sum it up", "The big idea, key points, words to know, and questions to check yourself."),
        ("How did it go?", "Rate how well you understood. It shows on your dashboard."),
        ("AI Tutor", "Ask anything about your reading. It can also suggest settings to try."),
    ]),
]


def quick_guide() -> html.Details:
    """Collapsible guide that sits above the Reading Studio tools. Opens on a first visit (see studio.js)."""
    return html.Details(
        id="tool-guide",
        className="tool-guide",
        children=[
            html.Summary([html.Span("?", className="guide-q", **{"aria-hidden": "true"}), "Quick guide: what each tool does"]),
            html.Div(
                className="guide-grid",
                children=[
                    html.Div(
                        className="guide-group",
                        children=[
                            html.H3(group),
                            html.P(where, className="guide-where"),
                            html.Dl([el for name, what in tools for el in (html.Dt(name), html.Dd(what))]),
                        ],
                    )
                    for group, where, tools in GUIDE
                ],
            ),
            html.P(
                ["Tip: everything you change is remembered. ", dcc.Link("See the full Tool Guide", href="/learning-tools", className="text-link"), "."],
                className="muted small guide-foot",
            ),
        ],
    )


def guide_cards() -> list:
    """One card per group for the Tool Guide page."""
    return [
        html.Div(
            className="card guide-card",
            children=[
                html.P(where, className="guide-where"),
                html.H2(group),
                html.Dl([el for name, what in tools for el in (html.Dt(name), html.Dd(what))]),
            ],
        )
        for group, where, tools in GUIDE
    ]
