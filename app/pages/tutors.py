"""Tutor Directory — legitimate tutoring sites and directories where families find tutors themselves.

WordWise does not list or vet individual tutors. Content lives in data/tutoring_sites.json.
"""

import json
from functools import lru_cache

import dash
from dash import Input, Output, callback, dcc, html

from components.layout import page_header
from config import DATA_DIR

dash.register_page(__name__, path="/tutors", name="Tutor Directory", order=3)

AGE_OPTIONS = {"any": "Any age", "kids": "Kids (5–12)", "teens": "Teens (13–17)", "adults": "Adults (18+)"}
FORMAT_OPTIONS = {"any": "Online or in person", "online": "Online", "in-person": "In person"}
COST_OPTIONS = {"any": "Any cost", "free": "Free or low cost", "search-free": "Free to search", "paid": "Paid"}
FORMAT_LABELS = {"online": "Online", "in-person": "In person"}
AGE_LABELS = {"kids": "Kids", "teens": "Teens", "adults": "Adults"}


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads((DATA_DIR / "tutoring_sites.json").read_text(encoding="utf-8"))


def _ext(children, href: str, className: str = "") -> html.A:
    kids = children if isinstance(children, list) else [children]
    return html.A(
        [*kids, html.Span(" (opens in a new tab)", className="sr-only")],
        href=href, target="_blank", rel="noopener noreferrer", className=className,
    )


def _filter(label: str, id_: str, options: dict) -> html.Div:
    return html.Div(
        className="tutor-filter",
        children=[
            html.H3(label),
            dcc.RadioItems(
                id=id_,
                options=[{"label": v, "value": k} for k, v in options.items()],
                value="any",
                className="choice-row compact",
                inputClassName="choice-input",
            ),
        ],
    )


def _site_card(s: dict) -> html.Div:
    cost_class = {"free": "kind-med", "search-free": "kind-gov"}.get(s["cost"], "kind-npo")
    return html.Div(
        className="card site-card",
        children=[
            html.Div(
                className="site-head",
                children=[
                    html.Div([html.H3(s["name"]), html.P(s["org"], className="link-org")]),
                    html.Span(s["cost_label"], className=f"kind {cost_class}"),
                ],
            ),
            html.P(s["what"], className="site-what"),
            html.Div(
                className="site-tags",
                children=[html.Span(AGE_LABELS[a], className="mini-tag") for a in s["ages"]]
                + [html.Span(s.get("local") or " or ".join(FORMAT_LABELS[f] for f in s["format"]), className="mini-tag mini-tag-place")],
            ),
            html.P([html.Strong("How: "), s["how"]], className="site-how"),
            html.P(["ⓘ ", s["note"]], className="muted site-note") if s.get("note") else None,
            _ext(["Visit site", html.Span(" ↗", **{"aria-hidden": "true"})], s["url"], "btn btn-secondary btn-small"),
        ],
    )


def layout(**_query):
    d = _data()
    c = d["checklist"]
    return html.Div(
        [
            page_header(
                "Tutor Directory",
                "Trusted places to find a reading tutor or specialist. Explore the sites, then reach out to the people who fit you best.",
                eyebrow="Find support",
                theme="tutors",
            ),
            html.Section(
                className="section container",
                children=[
                    html.Div(
                        className="card callout tutor-ai-callout",
                        children=[
                            html.Div(
                                [
                                    html.H2("Need help right now?"),
                                    html.P("Ask the WordWise AI Tutor any time. It's free and answers in seconds, at your reading level. It's great for quick questions while you look for a person."),
                                    dcc.Link("Ask the AI Tutor", href="/ai-tutor", className="btn btn-primary"),
                                ]
                            ),
                            html.Div(className="callout-shape", **{"aria-hidden": "true"}),
                        ],
                    ),
                    html.Div(
                        className="card trust-note",
                        children=[
                            html.Div("◆", className="trust-mark", **{"aria-hidden": "true"}),
                            html.Div(
                                [
                                    html.H2("How this directory works"),
                                    html.P(
                                        "WordWise lists well-known organizations, official certification directories, and nonprofit "
                                        "programs. We don't list or check individual tutors. You choose and contact them yourself. "
                                        f"All links were checked on {d['checked']}."
                                    ),
                                ]
                            ),
                        ],
                    ),
                    html.Div(
                        className="tutor-filters",
                        children=[
                            _filter("Who is it for?", "tut-age", AGE_OPTIONS),
                            _filter("Format", "tut-format", FORMAT_OPTIONS),
                            _filter("Cost", "tut-cost", COST_OPTIONS),
                        ],
                    ),
                    html.P(id="tut-count", className="muted", role="status"),
                    html.Div(id="tut-results"),
                    html.Div(
                        id="checklist",
                        className="card checklist",
                        children=[
                            html.H2("Before you choose a tutor: a checklist"),
                            html.Ol([html.Li(item) for item in c["items"]], className="check-list"),
                            html.P(
                                [
                                    "Based on the International Dyslexia Association's ",
                                    _ext(c["source"]["title"], c["source"]["url"]),
                                    " fact sheet and ",
                                    _ext(c["directory_source"]["title"], c["directory_source"]["url"]),
                                    " guidance.",
                                ],
                                className="muted",
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )


@callback(
    Output("tut-results", "children"),
    Output("tut-count", "children"),
    Input("tut-age", "value"),
    Input("tut-format", "value"),
    Input("tut-cost", "value"),
)
def filter_sites(age, fmt, cost):
    d = _data()
    sites = [
        s for s in d["sites"]
        if (age in (None, "any") or age in s["ages"])
        and (fmt in (None, "any") or fmt in s["format"])
        and (cost in (None, "any") or s["cost"] == cost)
    ]
    sections = []
    for g in d["groups"]:
        items = [s for s in sites if s["group"] == g["id"]]
        if items:
            sections.append(
                html.Section(
                    className="tutor-group",
                    children=[
                        html.H2(g["title"]),
                        html.P(g["intro"], className="topic-intro"),
                        html.Div([_site_card(s) for s in items], className="site-grid"),
                    ],
                )
            )
    if not sections:
        sections = [html.P("Nothing matches all of those choices. Try changing a filter.", className="notice-error")]
    return sections, f"Showing {len(sites)} of {len(d['sites'])} places."
