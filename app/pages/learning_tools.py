"""Learning Tools — placeholder."""

import dash
from dash import dcc, html

from components.layout import coming_soon_card, page_header

dash.register_page(__name__, path="/learning-tools", name="Learning Tools", order=2)

IN_STUDIO = "Ready in the Reading Studio"

layout = html.Div(
    [
        page_header(
            "Learning Tools",
            "Small tools that make reading practice easier, one skill at a time.",
            eyebrow="Practice",
        ),
        html.Section(
            className="section container",
            children=html.Div(
                className="grid grid-3",
                children=[
                    html.Div(
                        className="card",
                        children=[
                            html.Span("Ready now", className="tag"),
                            html.H3("AI Tutor"),
                            html.P("A free chat tutor that answers questions about your reading or schoolwork, at your level."),
                            dcc.Link("Ask the AI Tutor", href="/ai-tutor", className="btn btn-primary btn-small"),
                        ],
                    ),
                    coming_soon_card("Word breakdown", "See a hard word split into syllables, with how to say it and what it means.", tag=IN_STUDIO),
                    coming_soon_card("Reading ruler", "A guide that follows your line so you don't lose your place.", tag=IN_STUDIO),
                    coming_soon_card("My word bank", "Save new words and review them later."),
                    coming_soon_card("Check my understanding", "A few friendly questions after you read. No grades.", tag=IN_STUDIO),
                    coming_soon_card("Focus mode", "Show one paragraph at a time.", tag=IN_STUDIO),
                ],
            ),
        ),
    ]
)
