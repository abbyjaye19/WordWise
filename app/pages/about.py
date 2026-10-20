"""About — why WordWise exists: Abby's story of growing up with double-deficit dyslexia."""

from pathlib import Path

import dash
from dash import dcc, html

from components.layout import page_header

dash.register_page(__name__, path="/about", name="About", order=8)

ASSETS = Path(__file__).resolve().parents[1] / "assets"
PHOTO_NAMES = ("abby.jpg", "abby.jpeg", "abby.png", "abby.webp")  # drop a photo into app/assets/ to show it

DOUBLE_DEFICIT_SOURCE = "https://pmc.ncbi.nlm.nih.gov/articles/PMC4339699/"


def _portrait() -> html.Div:
    photo = next((n for n in PHOTO_NAMES if (ASSETS / n).exists()), None)
    if photo:
        return html.Div(html.Img(src=f"/assets/{photo}", alt="Abby Jaye", className="about-photo"), className="about-portrait")
    return html.Div(
        html.Div("AJ", className="about-monogram", **{"aria-hidden": "true"}),
        className="about-portrait",
    )


def _story() -> html.Div:
    return html.Div(
        className="about-story",
        children=[
            html.P("Hi, I'm Abby Jaye. I built WordWise.", className="about-hello"),
            html.P(
                [
                    "I have ",
                    html.Strong("double-deficit dyslexia"),
                    ". Learning to read was hard for me, and understanding what I read was even harder. "
                    "Reading and listening comprehension are still the parts I work hardest at.",
                ]
            ),
            html.P(
                "In college, I started working with a reading specialist. Our sessions did for me a lot of what WordWise "
                "now does: they helped me get through my readings and actually understand them. That's when I realized "
                "how useful a tool like this would have been when I was first learning to read, and how much it could help "
                "other people who struggle the way I did."
            ),
            html.P(
                "Finding help wasn't easy, either. Resources were scattered across many websites, and it was hard to know "
                "which ones to trust or where to start. I wanted one home base: a place to read your own assignments with "
                "support built in, and to find trusted information and real people when you need more help."
            ),
            html.P("WordWise is the tool I wish I'd had.", className="about-wish"),
        ],
    )


def _double_deficit() -> html.Div:
    return html.Div(
        className="card about-dd",
        children=[
            html.H2("What is double-deficit dyslexia?"),
            html.P(
                "Researchers describe two separate skills that can make reading hard when they don't come easily:"
            ),
            html.Ul(
                [
                    html.Li([html.Strong("Phonological awareness: "), "hearing and working with the sounds inside words."]),
                    html.Li([html.Strong("Rapid naming: "), "how quickly the brain can find and say the names of familiar things, like letters."]),
                ]
            ),
            html.P(
                "Trouble with either one can cause reading difficulties. People with a double deficit have trouble with both, "
                "and research finds their reading difficulties tend to be more severe than when only one is affected."
            ),
            html.P(
                [
                    html.Span("Source: ", className="muted"),
                    html.A(
                        "Norton et al., “Functional neuroanatomical evidence for the double-deficit hypothesis of developmental dyslexia,” Neuropsychologia (2014)",
                        href=DOUBLE_DEFICIT_SOURCE,
                        target="_blank",
                        rel="noopener",
                        className="muted",
                    ),
                ],
                className="small",
            ),
        ],
    )


PRINCIPLES = [
    ("Your own reading", "Bring the books, assignments, and slides you actually have to read, not practice passages."),
    ("Understanding, not shortcuts", "Help sits next to the original text and checks that you understood it. It never replaces the reading."),
    ("Built around you", "Everyone's dyslexia is different. Tell WordWise what's hard for you, and it changes how it helps."),
    ("A home base", "Trusted resources and real places to find a tutor or specialist, all in one place."),
]


def layout(**_query):
    return html.Div(
        [
            page_header("Why I built WordWise", "A tool for the reader I used to be, and for anyone who reads the way I do.", eyebrow="About"),
            html.Section(
                className="section container about-top",
                children=[_portrait(), _story()],
            ),
            html.Section(className="section container narrow", children=[_double_deficit()]),
            html.Section(
                className="section container",
                children=[
                    html.H2("What WordWise is built on", className="center"),
                    html.Div(
                        [html.Div(className="card", children=[html.H3(t), html.P(b)]) for t, b in PRINCIPLES],
                        className="grid grid-4",
                    ),
                ],
            ),
            html.Section(
                className="section container",
                children=html.Div(
                    className="card callout",
                    children=[
                        html.Div(
                            [
                                html.H2("If reading is hard for you too, you're not alone."),
                                html.P(
                                    "WordWise helps you read and understand. It doesn't diagnose dyslexia, and it doesn't replace a "
                                    "trained reading specialist. If you think you might have dyslexia, the Resources page explains "
                                    "how to get evaluated."
                                ),
                                html.Div(
                                    className="btn-row",
                                    children=[
                                        dcc.Link("Start reading", href="/reading-assistant", className="btn btn-primary"),
                                        dcc.Link("Resources", href="/resources", className="btn btn-secondary"),
                                        dcc.Link("Find a tutor", href="/tutors", className="btn btn-secondary"),
                                    ],
                                ),
                            ]
                        ),
                        html.Div(className="callout-shape", **{"aria-hidden": "true"}),
                    ],
                ),
            ),
        ]
    )
