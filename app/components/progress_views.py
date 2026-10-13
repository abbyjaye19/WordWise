"""Reading goals and saved-words sections for My Dashboard."""

from __future__ import annotations

from datetime import date

from dash import dcc, html

from services import progress


# ---------- layout ----------

def goals_section(user_id: int) -> html.Section:
    return html.Section(
        id="goals",
        className="section container-wide progress-section",
        children=[
            dcc.Store(id="goals-refresh", data=0),
            html.Div(
                className="card",
                children=[
                    html.Div(
                        className="section-head",
                        children=[
                            html.Div([html.H2("Reading goals"), html.P("Time counts while you read in the Reading Studio.", className="muted")]),
                            html.Div(
                                className="goal-pick",
                                children=[
                                    html.Label("My daily goal", htmlFor="goal-minutes", className="mini-label"),
                                    dcc.Dropdown(
                                        id="goal-minutes",
                                        options=[{"label": f"{m} minutes a day", "value": m} for m in progress.GOAL_CHOICES],
                                        value=progress.daily_goal(user_id),
                                        clearable=False,
                                        searchable=False,
                                        className="move-dropdown",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(id="goal-stats", className="stat-row"),
                    html.Div(id="goal-chart"),
                    html.Div(
                        className="personal-goals",
                        children=[
                            html.H3("My goals"),
                            html.P("Add things you want to finish, like “Read chapter 3 by Friday.”", className="muted"),
                            html.Div(
                                className="goal-add",
                                children=[
                                    html.Label("New goal", htmlFor="goal-text", className="sr-only"),
                                    dcc.Input(id="goal-text", type="text", placeholder="My goal…", className="text-input", maxLength=140),
                                    dcc.DatePickerSingle(
                                        id="goal-due",
                                        placeholder="Due date (optional)",
                                        clearable=True,
                                        display_format="MMM D, YYYY",
                                        min_date_allowed=date.today(),
                                        className="goal-date",
                                    ),
                                    html.Button("Add goal", id="goal-add-btn", className="btn btn-primary btn-small", n_clicks=0),
                                ],
                            ),
                            html.Div(id="goal-status", role="status"),
                            html.Ul(id="goal-list", className="goal-list"),
                        ],
                    ),
                ],
            ),
        ],
    )


def words_section() -> html.Section:
    return html.Section(
        id="words",
        className="section container-wide progress-section",
        children=[
            dcc.Store(id="words-refresh", data=0),
            html.Div(
                className="card",
                children=[
                    html.Div(
                        className="section-head",
                        children=[
                            html.Div(
                                [
                                    html.H2("My words"),
                                    html.P(
                                        ["Tap any word in the Reading Studio, then press ", html.Strong("☆ Save word"), "."],
                                        className="muted",
                                    ),
                                ]
                            ),
                            html.Div(id="word-counts", className="word-counts"),
                        ],
                    ),
                    html.Div(
                        className="word-controls",
                        children=[
                            html.Label("Search my words", htmlFor="word-search", className="sr-only"),
                            dcc.Input(id="word-search", type="search", placeholder="Search my words", className="text-input", debounce=True),
                            dcc.RadioItems(
                                id="word-show",
                                options=[
                                    {"label": "All", "value": "all"},
                                    {"label": "Still learning", "value": "learning"},
                                    {"label": "I know it", "value": "known"},
                                ],
                                value="all",
                                className="choice-row compact",
                                inputClassName="choice-input",
                            ),
                            dcc.Checklist(
                                id="word-quiz",
                                options=[{"label": "Quiz me (hide meanings)", "value": "quiz"}],
                                value=[],
                                className="choice-row compact",
                                inputClassName="choice-input",
                            ),
                        ],
                    ),
                    html.Div(id="word-list", className="word-grid"),
                ],
            ),
        ],
    )


# ---------- pieces ----------

def stat_tiles(minutes_today: int, goal: int, streak_days: int, week_minutes: int, words_week: int) -> list:
    pct = min(100, round(100 * minutes_today / goal)) if goal else 0
    met = minutes_today >= goal
    return [
        html.Div(
            className="stat-tile stat-hero",
            children=[
                html.P("Today", className="stat-label"),
                html.P([html.Span(str(minutes_today), className="stat-value"), html.Span(f" of {goal} min", className="stat-unit")]),
                html.Div(className="meter", role="img", **{"aria-label": f"{pct} percent of today's goal"}, children=html.Div(className="meter-fill", style={"width": f"{pct}%"})),
                html.P("Goal met. Great reading!" if met else f"{goal - minutes_today} min to go", className="stat-note"),
            ],
        ),
        _tile("Streak", f"{streak_days}", "day" if streak_days == 1 else "days", "Days in a row you met your goal"),
        _tile("This week", f"{week_minutes}", "min", "Minutes read in the last 7 days"),
        _tile("New words", f"{words_week}", "this week", "Words saved in the last 7 days"),
    ]


def _tile(label, value, unit, note):
    return html.Div(
        className="stat-tile",
        children=[
            html.P(label, className="stat-label"),
            html.P([html.Span(value, className="stat-value"), html.Span(f" {unit}", className="stat-unit")]),
            html.P(note, className="stat-note"),
        ],
    )


def week_chart(days: list[dict], goal: int, today: date) -> html.Div:
    """Single-series column chart (minutes per day) with a labeled goal line.

    One series, so no legend: the heading names it. Goal-met days also get a ✓
    under the bar, so meeting the goal never relies on height alone; a table
    version is available for screen readers.
    """
    top = max([goal * 1.25] + [d["minutes"] for d in days]) or 1
    goal_pct = 100 * goal / top
    peak = max(days, key=lambda d: d["minutes"])
    cols = []
    for d in days:
        is_today = d["day"] == today
        h = 100 * d["minutes"] / top
        met = d["minutes"] >= goal
        tip = f"{d['day'].strftime('%a %b')} {d['day'].day}: {d['minutes']} min" + (" · goal met" if met else "")
        show_value = is_today or (d is peak and d["minutes"] > 0)
        cols.append(
            html.Div(
                className="wk-col" + (" wk-today" if is_today else ""),
                children=[
                    html.Div(
                        className="wk-plot",
                        children=html.Div(
                            className="wk-bar" + (" wk-empty" if not d["minutes"] else ""),
                            style={"height": f"{max(h, 1.5) if d['minutes'] else 0}%"},
                            tabIndex="0",
                            title=tip,
                            **{"data-tip": tip, "aria-label": tip},
                            children=html.Span(str(d["minutes"]), className="wk-value") if show_value else None,
                        ),
                    ),
                    html.Span("Today" if is_today else d["day"].strftime("%a"), className="wk-day"),
                    html.Span("✓" if met else "", className="wk-met", **{"aria-hidden": "true"}),
                ],
            )
        )
    return html.Div(
        className="week-chart-wrap",
        children=[
            html.H3("Minutes read, last 7 days"),
            html.Div(
                className="week-chart",
                role="img",
                **{"aria-label": f"Bar chart of minutes read each day for the last 7 days. Goal: {goal} minutes a day."},
                children=[
                    html.Div(className="wk-goal", style={"bottom": f"{goal_pct}%"}, children=html.Span(f"Goal {goal} min", className="wk-goal-label")),
                    *cols,
                ],
            ),
            html.Table(
                className="sr-only",
                children=[
                    html.Caption("Minutes read per day"),
                    html.Thead(html.Tr([html.Th("Day"), html.Th("Minutes"), html.Th("Goal met")])),
                    html.Tbody([html.Tr([html.Td(d["day"].isoformat()), html.Td(d["minutes"]), html.Td("yes" if d["minutes"] >= goal else "no")]) for d in days]),
                ],
            ),
        ],
    )


def goal_item(g: dict, today: date) -> html.Li:
    due = date.fromisoformat(g["due"]) if g.get("due") else None
    due_label, due_class = None, "goal-due"
    if due:
        days_left = (due - today).days
        if g["done"]:
            due_label = f"Due {due.strftime('%b')} {due.day}"
        elif days_left < 0:
            due_label, due_class = f"! Overdue since {due.strftime('%b')} {due.day}", "goal-due overdue"
        elif days_left == 0:
            due_label, due_class = "Due today", "goal-due soon"
        elif days_left == 1:
            due_label, due_class = "Due tomorrow", "goal-due soon"
        else:
            due_label = f"Due {due.strftime('%a, %b')} {due.day}"
    return html.Li(
        className="goal-item" + (" done" if g["done"] else ""),
        children=[
            dcc.Checklist(
                id={"type": "goal-done", "id": g["id"]},
                options=[{"label": g["text"], "value": "done"}],
                value=["done"] if g["done"] else [],
                className="goal-check",
                inputClassName="choice-input",
            ),
            html.Span(due_label, className=due_class) if due_label else None,
            html.Button("Remove", id={"type": "goal-del", "id": g["id"]}, className="link-btn", n_clicks=0, **{"aria-label": f"Remove goal: {g['text']}"}),
        ],
    )


def word_card(w: dict, quiz: bool) -> html.Div:
    meaning_block = [
        html.P(w["meaning"], className="word-meaning"),
        html.Div([html.Span(s, className="chip") for s in w["synonyms"]], className="chips") if w["synonyms"] else None,
        html.P(["Example: ", w["example"]], className="word-example") if w["example"] else None,
    ]
    say = f"{w['word']}. {w['meaning']}"
    return html.Div(
        className="word-card" + (" known" if w["known"] else ""),
        children=[
            html.Div(
                className="word-card-head",
                children=[
                    html.Div(
                        [
                            html.H3(w["word"]),
                            html.P(
                                [html.Strong(w["syllables"]), f" · say it: {w['say_it']}" if w["say_it"] else "", f" · {w['part_of_speech']}" if w["part_of_speech"] else ""],
                                className="word-sound",
                            ),
                        ]
                    ),
                    html.Button("🔊", className="tool-btn speak-btn icon-btn", type="button", title="Listen", **{"data-say": say, "aria-label": f"Listen to {w['word']}"}),
                ],
            ),
            html.Details([html.Summary("Show meaning"), *meaning_block], className="word-reveal") if quiz else html.Div(meaning_block),
            html.P(f"From: {w['source_title']}", className="word-source") if w["source_title"] else None,
            html.Div(
                className="word-actions",
                children=[
                    html.Button(
                        "✓ I know it" if not w["known"] else "↺ Still learning",
                        id={"type": "word-known", "id": w["id"]},
                        className="btn btn-secondary btn-small",
                        n_clicks=0,
                    ),
                    html.Button("Remove", id={"type": "word-del", "id": w["id"]}, className="link-btn", n_clicks=0, **{"aria-label": f"Remove {w['word']}"}),
                ],
            ),
        ],
    )
