"""Reading insights and "What I want to work on" for My Dashboard.

Charts follow the same rules as the 7-day chart: one series each (so no legend), the value
printed on every bar, and a screen-reader table with the same numbers.
"""

from __future__ import annotations

from datetime import date

from dash import dcc, html

from services import preferences, progress


# ---------- layout ----------

def insights_section() -> html.Section:
    return html.Section(
        id="insights",
        className="section container-wide progress-section",
        children=[
            dcc.Store(id="insights-load", data=0),
            html.Div(
                className="card",
                children=[
                    html.Div(
                        className="section-head",
                        children=html.Div(
                            [
                                html.H2("Reading insights"),
                                html.P("Your last 30 days: reading sessions, the tools you use, saved words, and how well you understood.", className="muted"),
                            ]
                        ),
                    ),
                    html.Div(id="insights-body"),
                ],
            ),
        ],
    )


def profile_section(user_id: int) -> html.Section:
    prof = preferences.load_profile(user_id)
    ratings = prof["ratings"]
    rows = [
        html.Div(
            className="prof-row",
            children=[
                html.Span(label, className="prof-label", id=f"prof-label-{key}"),
                dcc.RadioItems(
                    id={"type": "prof-rate", "k": key},
                    options=[{"label": lab, "value": n} for n, lab in preferences.LEVELS.items()],
                    value=ratings.get(key, 0),
                    className="choice-row compact prof-choices",
                    inputClassName="choice-input",
                    labelClassName="choice-label",
                ),
            ],
        )
        for key, (label, _how) in preferences.CHALLENGES.items()
    ]
    return html.Section(
        id="profile",
        className="section container-wide progress-section",
        children=html.Div(
            className="profile-grid",
            children=[
                html.Div(
                    className="card",
                    children=[
                        html.H2("What I want to work on"),
                        html.P(
                            "Everyone reads differently. Rate each area, and WordWise will shape its help around you. "
                            "This isn't a test, and you can change it any time.",
                            className="muted",
                        ),
                        html.Div(rows, className="prof-rows"),
                        html.Div(
                            className="prof-priority",
                            children=[
                                html.Label("My top priority", htmlFor="prof-priority", className="mini-label"),
                                dcc.Dropdown(
                                    id="prof-priority",
                                    options=[{"label": lab, "value": k} for k, (lab, _h) in preferences.CHALLENGES.items()],
                                    value=prof["priority"],
                                    placeholder="Pick one (optional)",
                                    searchable=False,
                                    className="move-dropdown wide",
                                ),
                            ],
                        ),
                        html.Div(
                            className="btn-stack",
                            children=[
                                html.Button("Save", id="prof-save", className="btn btn-primary btn-small", n_clicks=0),
                                dcc.ConfirmDialogProvider(
                                    html.Button("Clear my answers", className="btn btn-secondary btn-small"),
                                    id="prof-clear",
                                    message="Clear your answers about what you want to work on?",
                                ),
                            ],
                        ),
                        html.Div(id="prof-status", role="status"),
                    ],
                ),
                html.Div(
                    className="card adapt-card",
                    children=[
                        html.H2("How WordWise adapts for you"),
                        html.Div(id="prof-adapts"),
                    ],
                ),
            ],
        ),
    )


# ---------- pieces drawn by callbacks ----------

def adapt_list(profile: dict) -> list:
    items = preferences.adaptations(profile)
    if not items:
        return [
            html.P("Rate the areas on the left and save. WordWise will then tell you here how it changes its help.", className="muted"),
        ]
    return [
        html.P("The Word Coach, Explainer, Sum it up, Reading Levels, and the AI Tutor all use this:", className="muted"),
        html.Ul([html.Li(_adapt_item(t)) for t in items], className="adapt-list"),
        html.P(
            ["Not sure which text settings suit you? ", dcc.Link("Ask the AI Tutor to suggest some", href="/ai-tutor", className="text-link"), "."],
            className="muted small",
        ),
    ]


def _adapt_item(text: str):
    head, _, rest = text.partition(": ")
    return [html.Strong(head), html.Br(), html.Span(rest)]


def insights_body(user_id: int) -> list:
    summary = progress.session_summary(user_id)
    words = progress.word_counts(user_id)
    recent = progress.checks(user_id, 10)
    avg = progress.recent_comprehension(user_id)
    tiles = html.Div(
        className="stat-row stat-row-4",
        children=[
            _tile("Reading sessions", str(summary["sessions"]), "", f"{summary['readings']} different readings"),
            _tile("Time reading", str(summary["minutes"]), "min", "in the Reading Studio"),
            _tile("Saved words", str(words["total"]), "", f"{words['learning']} still learning · {words['known']} known"),
            _tile("Understanding", f"{avg:.1f}" if avg is not None else "–", "of 5" if avg is not None else "",
                  "average of your last 5 check-ins" if avg is not None else "Do a check-in after reading"),
        ],
    )
    return [
        tiles,
        html.Div(
            className="insights-grid",
            children=[
                html.Div([html.H3("Tools you use most"), tools_chart(progress.tool_counts(user_id))], className="insight-block"),
                html.Div([html.H3("Recent reading sessions"), sessions_list(progress.recent_sessions(user_id))], className="insight-block"),
                html.Div([html.H3("How well you understood"), checks_chart(recent)], className="insight-block"),
                html.Div([html.H3("What made reading hard"), hard_list(progress.hard_reason_counts(user_id))], className="insight-block"),
            ],
        ),
    ]


def _tile(label, value, unit, note):
    return html.Div(
        className="stat-tile",
        children=[
            html.P(label, className="stat-label"),
            html.P([html.Span(value, className="stat-value"), html.Span(f" {unit}" if unit else "", className="stat-unit")]),
            html.P(note, className="stat-note"),
        ],
    )


def tools_chart(tools: list[dict]) -> html.Div:
    if not tools:
        return html.P("Use the Reading Studio tools and they'll show up here.", className="muted")
    tools = tools[:7]
    top = max(t["count"] for t in tools) or 1
    return html.Div(
        [
            html.Div(
                className="hbar-chart",
                role="img",
                **{"aria-label": "Bar chart of how often you used each tool in the last 30 days."},
                children=[
                    html.Div(
                        className="hbar-row",
                        children=[
                            html.Span(t["label"], className="hbar-label"),
                            html.Div(className="hbar-track", children=html.Div(className="hbar-fill", style={"width": f"{max(3, 100 * t['count'] / top):.0f}%"})),
                            html.Span(str(t["count"]), className="hbar-value"),
                        ],
                    )
                    for t in tools
                ],
            ),
            _sr_table("Times each tool was used", ["Tool", "Times"], [[t["label"], t["count"]] for t in tools]),
        ]
    )


def sessions_list(sessions: list[dict]) -> html.Div:
    if not sessions:
        return html.P("Read something in the Reading Studio while signed in to start your history.", className="muted")
    today = date.today().isoformat()
    return html.Ul(
        [
            html.Li(
                className="session-row",
                children=[
                    html.Span(_nice_day(s["day"], today), className="session-day"),
                    html.Span(s["title"], className="session-title"),
                    html.Span(f"{s['minutes']} min", className="session-min"),
                ],
            )
            for s in sessions
        ],
        className="session-list",
    )


def _nice_day(day: str, today: str) -> str:
    if day == today:
        return "Today"
    d = date.fromisoformat(day)
    return f"{d.strftime('%b')} {d.day}"


def checks_chart(checks: list[dict]) -> html.Div:
    if not checks:
        return html.P(
            ["No check-ins yet. After reading, use ", html.Strong("How did it go?"), " in the Reading Studio's help panel."],
            className="muted",
        )
    checks = list(reversed(checks))  # oldest first, left to right
    cols = [
        html.Div(
            className="ck-col",
            children=[
                html.Div(
                    className="ck-plot",
                    children=html.Div(
                        className="ck-bar",
                        style={"height": f"{20 * c['rating']}%"},
                        title=f"{c['title']} ({_nice_day(c['day'], '')}): {c['rating']} of 5, {progress.RATING_LABELS[c['rating']].lower()}",
                        children=html.Span(str(c["rating"]), className="ck-value"),
                    ),
                ),
                html.Span(_nice_day(c["day"], date.today().isoformat()), className="ck-day"),
            ],
        )
        for c in checks
    ]
    return html.Div(
        [
            html.Div(cols, className="ck-chart", role="img", **{"aria-label": "Bar chart of your last check-ins, rated 1 (not at all) to 5 (very well)."}),
            html.P("1 = not at all · 5 = very well. Hover a bar to see the reading.", className="muted small"),
            _sr_table("Comprehension check-ins", ["Day", "Reading", "Rating (1-5)"], [[c["day"], c["title"], c["rating"]] for c in checks]),
        ]
    )


def hard_list(counts: list[tuple[str, int]]) -> html.Div:
    if not counts:
        return html.P("When a check-in says what was hard, it's counted here. WordWise uses it to adapt.", className="muted")
    return html.Div(
        [
            html.Div([html.Span([label, html.Strong(f" ×{n}")], className="chip") for label, n in counts], className="chips"),
            html.P(
                ["Tip: add these to ", html.A("What I want to work on", href="#profile", className="text-link"), " so the AI focuses on them."],
                className="muted small",
            ),
        ]
    )


def _sr_table(caption: str, head: list[str], rows: list[list]) -> html.Table:
    return html.Table(
        className="sr-only",
        children=[
            html.Caption(caption),
            html.Thead(html.Tr([html.Th(h) for h in head])),
            html.Tbody([html.Tr([html.Td(v) for v in r]) for r in rows]),
        ],
    )
