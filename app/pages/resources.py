"""Resources — plain-language guides built from trusted health, education, and research sources."""

import dash
from dash import Input, Output, callback, dcc, html

from components.layout import page_header
from services import resources

dash.register_page(__name__, path="/resources", name="Resources", order=4)

KIND_CLASS = {
    "Government health": "kind-gov",
    "Government": "kind-gov",
    "Government-funded": "kind-gov",
    "Medical center": "kind-med",
    "Medical organization": "kind-med",
    "University": "kind-uni",
    "Nonprofit": "kind-npo",
    "Testing organization": "kind-npo",
}


def _short(org: str) -> str:
    return org.split(" · ")[-1] if org.startswith(("NIH", "ADA.gov", "Library")) else org.split(" · ")[0].split(" (")[0]


def _ext(children, href: str, className: str = "") -> html.A:
    return html.A(
        [*([children] if not isinstance(children, list) else children), html.Span(" (opens in a new tab)", className="sr-only")],
        href=href,
        target="_blank",
        rel="noopener noreferrer",
        className=className,
    )


def _topic(t: dict, sources: dict) -> html.Section:
    say = t["title"] + ". " + t["intro"] + " " + " ".join(p["text"] for p in t["points"])
    return html.Section(
        id=t["id"],
        className="card topic",
        children=[
            html.Div(
                className="topic-head",
                children=[
                    html.Div(t["icon"], className="feature-icon", **{"aria-hidden": "true"}),
                    html.Div([html.H2(t["title"]), html.P(t["intro"], className="topic-intro")]),
                    html.Button("🔊 Listen", className="tool-btn speak-btn", type="button", **{"data-say": say}),
                ],
            ),
            html.H3("Key facts"),
            html.Ul(
                className="fact-list",
                children=[
                    html.Li(
                        [
                            html.Span(p["text"]),
                            html.Span(
                                [html.Span("Source: ", className="cite-label")]
                                + [
                                    el
                                    for i, sid in enumerate(p["src"])
                                    for el in ([", "] if i else []) + [_ext(_short(sources[sid]["org"]), sources[sid]["url"], "cite")]
                                ],
                                className="cite-row",
                            ),
                        ]
                    )
                    for p in t["points"]
                ],
            ),
            html.H3("Read more from trusted sources"),
            html.Div(
                className="link-grid",
                children=[
                    html.Div(
                        className="link-card",
                        children=[
                            html.Div(
                                [
                                    html.Span(s["kind"], className=f"kind {KIND_CLASS.get(s['kind'], 'kind-npo')}"),
                                    html.Span(s["org"], className="link-org"),
                                ],
                                className="link-meta",
                            ),
                            _ext([s["title"], html.Span(" ↗", **{"aria-hidden": "true"})], s["url"], "link-title"),
                            html.P(s["blurb"]),
                        ],
                    )
                    for s in t["links"]
                ],
            ),
        ],
    )


def layout(**_query):
    data = resources.load()
    return html.Div(
        [
            page_header(
                "Resources",
                "Trusted, plain-language information about dyslexia and reading differences, for students, families, and adults.",
                eyebrow="Learn",
                theme="resources",
            ),
            html.Section(
                className="section container",
                children=[
                    html.Div(
                        className="card trust-note",
                        children=[
                            html.Div("◆", className="trust-mark", **{"aria-hidden": "true"}),
                            html.Div(
                                [
                                    html.H2("Where this information comes from"),
                                    html.P(
                                        "We only link to government health and education agencies, medical centers, university "
                                        "research centers, and long-standing nonprofits. Every fact below links to its source. "
                                        f"Links were checked on {data['checked']}."
                                    ),
                                    html.P(
                                        [
                                            html.Strong("This is not medical advice. "),
                                            "WordWise can't diagnose dyslexia. If you have questions, talk to a doctor, a school "
                                            "psychologist, or a reading specialist.",
                                        ]
                                    ),
                                ]
                            ),
                        ],
                    ),
                    html.Div(
                        className="resource-filter",
                        children=[
                            html.H2("Show resources for", className="filter-title"),
                            dcc.RadioItems(
                                id="res-audience",
                                options=[{"label": v, "value": k} for k, v in resources.AUDIENCES.items()],
                                value="all",
                                className="choice-row",
                                inputClassName="choice-input",
                            ),
                        ],
                    ),
                    html.Nav(id="res-jump", className="topic-jump", **{"aria-label": "Resource topics"}),
                    html.Div(id="res-topics", className="topics"),
                ],
            ),
        ]
    )


@callback(
    Output("res-topics", "children"),
    Output("res-jump", "children"),
    Input("res-audience", "value"),
)
def show_topics(audience):
    data = resources.load()
    topics = resources.topics_for(audience or "all")
    jump = [html.A(t["title"], href=f"#{t['id']}", className="jump-link") for t in topics]
    return [_topic(t, data["sources"]) for t in topics], jump
