"""Friendly page for unknown links."""

import dash
from dash import dcc, html

dash.register_page(__name__, path="/404")

layout = html.Section(
    className="section container narrow center",
    children=[
        html.H1("We can't find that page."),
        html.P("The link may be old or mistyped."),
        dcc.Link("Go to the home page", href="/", className="btn btn-primary"),
    ],
)
