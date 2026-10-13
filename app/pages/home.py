"""Landing page."""

import dash
from dash import dcc, html

from components.layout import divider

dash.register_page(__name__, path="/", name="Home", order=0)

FEATURES = [
    {
        "icon": "Aa",
        "title": "Reading Assistant",
        "body": "Upload a PDF, lecture slides, or a book page. Make the text bigger, space it out, highlight it, or have it read aloud.",
        "href": "/reading-assistant",
        "cta": "Start reading",
    },
    {
        "icon": "?",
        "title": "Explain it my way",
        "body": "Tap a word for its meaning and synonyms. Select a hard part for simpler words, an example, or steps. The original stays on screen.",
        "href": "/reading-assistant",
        "cta": "Try it on a sample",
    },
    {
        "icon": "◎",
        "title": "Tutor Directory",
        "body": "Ask the free AI Tutor any time, or find trusted directories of certified reading specialists and free tutoring programs.",
        "href": "/tutors",
        "cta": "Find a tutor",
    },
    {
        "icon": "≡",
        "title": "Resources",
        "body": "Clear guides on dyslexia, school accommodations, evaluations, and helpful technology.",
        "href": "/resources",
        "cta": "Browse resources",
    },
]

STEPS = [
    ("1", "Bring your reading", "Upload a PDF, slides, or a Word file, or paste a page."),
    ("2", "Make it yours", "Set the font, size, spacing, and background you like best."),
    ("3", "Understand it", "Listen along, look up words, and check yourself with quick questions."),
]


def _feature(f):
    return html.Div(
        className="card feature-card",
        children=[
            html.Div(f["icon"], className="feature-icon", **{"aria-hidden": "true"}),
            html.H3(f["title"]),
            html.P(f["body"]),
            dcc.Link([f["cta"], html.Span(" →", **{"aria-hidden": "true"})], href=f["href"], className="text-link"),
        ],
    )


layout = html.Div(
    [
        # Hero
        html.Section(
            className="hero dots-navy",
            children=[
                html.Div(className="geo geo-circle", **{"aria-hidden": "true"}),
                html.Div(className="geo geo-arc", **{"aria-hidden": "true"}),
                html.Div(
                    className="container hero-inner",
                    children=[
                        html.Div(
                            className="hero-text",
                            children=[
                                html.P("For students ages 5 to 30 · dyslexia and reading differences", className="eyebrow eyebrow-light"),
                                html.H1("Reading, made to fit you."),
                                html.P(
                                    "Bring the books, school readings, and lecture slides you already have. "
                                    "WordWise helps you see them, hear them, and understand them — "
                                    "for school or just for fun.",
                                    className="lead",
                                ),
                                html.Div(
                                    className="btn-row",
                                    children=[
                                        dcc.Link("Start reading", href="/reading-assistant", className="btn btn-primary btn-on-dark"),
                                        dcc.Link("Find a tutor", href="/tutors", className="btn btn-ghost"),
                                    ],
                                ),
                            ],
                        ),
                        html.Img(src="/assets/skyline.svg", alt="", className="hero-skyline"),
                    ],
                ),
            ],
        ),
        # Why
        html.Section(
            className="section container narrow",
            children=[
                html.H2("Reading should not feel like a wall."),
                html.P(
                    [
                        "Dyslexia is common. Some researchers estimate it affects as many as ",
                        html.Strong("1 in 5 people"),
                        ". It has nothing to do with how smart someone is. "
                        "But most text is not built for the way many people read. "
                        "Help is spread across many places, and it can be hard to know where to start.",
                    ]
                ),
                html.P(
                    [
                        "WordWise brings the tools and the support into one calm place. ",
                        html.Span("Source: ", className="muted"),
                        html.A(
                            "Yale Center for Dyslexia & Creativity",
                            href="https://dyslexia.yale.edu/dyslexia/dyslexia-faq/",
                            target="_blank",
                            rel="noopener",
                            className="muted",
                        ),
                        html.Span(".", className="muted"),
                    ]
                ),
            ],
        ),
        divider(),
        # Features
        html.Section(
            className="section container",
            children=[
                html.H2("How WordWise helps", className="center"),
                html.Div([_feature(f) for f in FEATURES], className="grid grid-4"),
            ],
        ),
        # Steps
        html.Section(
            className="section band dots",
            children=html.Div(
                className="container",
                children=[
                    html.H2("How it works", className="center"),
                    html.Ol(
                        [
                            html.Li(
                                className="step",
                                children=[
                                    html.Span(n, className="step-num", **{"aria-hidden": "true"}),
                                    html.Div([html.H3(t), html.P(b)]),
                                ],
                            )
                            for n, t, b in STEPS
                        ],
                        className="steps",
                    ),
                ],
            ),
        ),
        # Settings invite
        html.Section(
            className="section container",
            children=html.Div(
                className="card callout",
                children=[
                    html.Div(
                        [
                            html.H2("Try it now: change how this page looks."),
                            html.P(
                                "Open Reading settings at the top of any page. Pick a bigger font, more space between lines, "
                                "or a softer background. WordWise remembers your choices."
                            ),
                        ]
                    ),
                    html.Div(className="callout-shape", **{"aria-hidden": "true"}),
                ],
            ),
        ),
        # Trust
        html.Section(
            className="section container",
            children=[
                html.H2("Our promise", className="center"),
                html.Div(
                    className="grid grid-3 promise",
                    children=[
                        html.Div(className="card", children=[html.H3("Your text stays yours"), html.P("We only use what you paste to help you read it.")]),
                        html.Div(className="card", children=[html.H3("The original is always there"), html.P("AI help appears next to your text. It never replaces it.")]),
                        html.Div(className="card", children=[html.H3("Support, not diagnosis"), html.P("WordWise helps you read. It does not diagnose or replace a specialist.")]),
                    ],
                ),
            ],
        ),
    ]
)
