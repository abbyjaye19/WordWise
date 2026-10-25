"""Tool Guide — what every reading tool does. The same guide also opens inside the Reading Studio."""

import dash
from dash import dcc, html

from components.layout import page_header
from components.tool_guide import guide_cards

dash.register_page(__name__, path="/learning-tools", name="Tool Guide", order=6)

layout = html.Div(
    [
        page_header(
            "Tool Guide",
            "Every reading tool in one place. You'll find the same guide at the top of the Reading Studio.",
            eyebrow="How it works",
            theme="tools",
        ),
        html.Section(
            className="section container",
            children=[
                html.Div(
                    className="card callout guide-start",
                    children=[
                        html.Div(
                            [
                                html.H2("The fastest way to learn is to try."),
                                html.P("Open a sample reading, then try one tool at a time. The guide stays one click away above the tools."),
                                dcc.Link("Open the Reading Studio", href="/reading-assistant", className="btn btn-primary"),
                            ]
                        ),
                        html.Div(className="callout-shape", **{"aria-hidden": "true"}),
                    ],
                ),
                html.Div(guide_cards(), className="grid grid-3 guide-cards"),
                html.Div(
                    className="card guide-card guide-more",
                    children=[
                        html.H2("Outside the Studio"),
                        html.Dl(
                            [
                                html.Dt(dcc.Link("AI Tutor", href="/ai-tutor", className="text-link")),
                                html.Dd("Chat about your reading or schoolwork. Tell it what's hard and it suggests settings you can apply with one tap."),
                                html.Dt(dcc.Link("My Dashboard", href="/dashboard", className="text-link")),
                                html.Dd("Your saved readings and folders, reading insights, goals, your word bank, and what you want to work on."),
                                html.Dt("Reading settings"),
                                html.Dd("Top right on every page. Saved to your account so they follow you."),
                            ]
                        ),
                    ],
                ),
            ],
        ),
    ]
)
