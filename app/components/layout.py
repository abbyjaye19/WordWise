"""Site shell: header + navigation, footer, and shared building blocks."""

from __future__ import annotations

from dash import dcc, html

# One place to rename or reorder the main sections.
NAV_ITEMS = [
    {"label": "Reading Assistant", "href": "/reading-assistant"},
    {"label": "Learning Tools", "href": "/learning-tools"},
    {"label": "Tutor Directory", "href": "/tutors"},
    {"label": "Resources", "href": "/resources"},
    {"label": "My Dashboard", "href": "/dashboard"},
]


def nav_link_id(href: str) -> str:
    return "nav" + href.replace("/", "-")


def header() -> html.Header:
    return html.Header(
        className="site-header",
        children=html.Div(
            className="header-inner",
            children=[
                dcc.Link(
                    [html.Span("◆", className="logo-mark", **{"aria-hidden": "true"}), "WordWise"],
                    href="/",
                    className="logo",
                ),
                html.Nav(
                    html.Ul(
                        [
                            html.Li(dcc.Link(item["label"], href=item["href"], id=nav_link_id(item["href"]), className="nav-link"))
                            for item in NAV_ITEMS
                        ],
                        className="nav-list",
                    ),
                    className="main-nav",
                    **{"aria-label": "Main"},
                ),
                html.Div(id="account-slot", className="account-slot"),
                html.Button(
                    "Reading settings",
                    id="a11y-open",
                    className="btn btn-settings",
                    n_clicks=0,
                    **{"aria-controls": "a11y-panel"},
                ),
            ],
        ),
    )


def footer() -> html.Footer:
    return html.Footer(
        className="site-footer dots-navy",
        children=html.Div(
            className="footer-inner",
            children=[
                html.Img(src="/assets/skyline.svg", alt="", className="footer-skyline"),
                html.Div(
                    [
                        html.P([html.Strong("WordWise"), " — reading support that fits you."]),
                        html.P(
                            "WordWise is a learning and accessibility tool. It does not diagnose dyslexia "
                            "or replace a trained reading specialist.",
                            className="footer-note",
                        ),
                        html.P("A student project for MGT 409. Not affiliated with Yale University.", className="footer-note"),
                    ]
                ),
            ],
        ),
    )


def page_header(title: str, intro: str, eyebrow: str | None = None) -> html.Section:
    """Top band used on every inner page."""
    return html.Section(
        className="page-header dots",
        children=html.Div(
            className="container page-header-inner",
            children=[
                html.P(eyebrow, className="eyebrow") if eyebrow else None,
                html.H1(title),
                html.P(intro, className="lead"),
                html.Img(src="/assets/book-stack.svg", alt="", className="header-books"),
            ],
        ),
    )


def divider() -> html.Div:
    return html.Div(className="divider", children=html.Span("◆"), **{"aria-hidden": "true"})


def coming_soon_card(title: str, body: str, tag: str = "Coming soon") -> html.Div:
    return html.Div(
        className="card",
        children=[
            html.Span(tag, className="tag"),
            html.H3(title),
            html.P(body),
        ],
    )
