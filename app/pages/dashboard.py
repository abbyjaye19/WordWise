"""My Dashboard — the student's library (folders + saved readings) and reading settings."""

from datetime import date

import dash
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, no_update

from components.layout import page_header
from components.progress_views import goal_item, goals_section, stat_tiles, week_chart, word_card, words_section
from components.settings_panel import DEFAULT_PREFS, LABELS, OPTIONS
from services import accounts, library, progress

dash.register_page(__name__, path="/dashboard", name="My Dashboard", order=5)


def _settings_card() -> html.Div:
    return html.Div(
        className="card",
        children=[
            html.H2("My reading settings"),
            html.Dl(id="dash-prefs", className="pref-list"),
            html.P("Change these any time with Reading settings at the top of the page.", className="muted"),
        ],
    )


def _signed_out() -> html.Div:
    return html.Div(
        [
            page_header("My Dashboard", "Your library, saved readings, and settings in one place.", eyebrow="You"),
            html.Section(
                className="section container",
                children=[
                    html.Div(
                        className="card callout",
                        children=[
                            html.Div(
                                [
                                    html.H2("Sign in to keep your readings."),
                                    html.P("With an account you can save what you upload, keep your highlights, and sort readings into folders."),
                                    dcc.Link("Sign in or create an account", href="/account", className="btn btn-primary"),
                                ]
                            ),
                            html.Div(className="callout-shape", **{"aria-hidden": "true"}),
                        ],
                    ),
                    html.Div(className="grid", children=[_settings_card()]),
                ],
            ),
        ]
    )


def layout(**_query):
    user = accounts.current_user()
    if not user:
        return _signed_out()
    return html.Div(
        [
            dcc.Store(id="lib-refresh", data=0),
            page_header("My Dashboard", f"Welcome back, {user['username']}. Here is your library.", eyebrow="You"),
            html.Section(
                className="section container-wide library",
                children=[
                    html.Aside(
                        className="card folder-panel",
                        children=[
                            html.H2("Folders"),
                            dcc.RadioItems(id="folder-pick", value="all", className="folder-list", inputClassName="choice-input"),
                            html.Div(
                                id="folder-tools",
                                className="folder-tools",
                                hidden=True,
                                children=[
                                    html.H3("Folder color"),
                                    dcc.RadioItems(id="folder-color", options=_color_options(), className="swatch-row", inputClassName="swatch-input"),
                                    dcc.ConfirmDialogProvider(
                                        html.Button("Delete this folder", id="delete-folder-btn", className="btn btn-secondary btn-small btn-danger"),
                                        id="delete-folder-confirm",
                                        message="Delete this folder? Nothing inside is lost: its readings and subfolders move up one level.",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="new-folder-box",
                                children=[
                                    html.H3("New folder"),
                                    html.Label("Folder name", htmlFor="new-folder-name", className="sr-only"),
                                    dcc.Input(id="new-folder-name", type="text", placeholder="Folder name", className="text-input", maxLength=60),
                                    html.Label("Put it inside", htmlFor="new-folder-parent", className="mini-label"),
                                    dcc.Dropdown(id="new-folder-parent", clearable=False, searchable=False, className="move-dropdown wide"),
                                    html.Span("Color", className="mini-label"),
                                    dcc.RadioItems(id="new-folder-color", options=_color_options(), value="navy", className="swatch-row", inputClassName="swatch-input"),
                                    html.Button("Add folder", id="new-folder-btn", className="btn btn-primary btn-small", n_clicks=0),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="library-main",
                        children=[
                            html.Div(
                                className="library-head",
                                children=[
                                    html.H2(id="library-title"),
                                    dcc.Link("+ Add a reading", href="/reading-assistant", className="btn btn-primary btn-small"),
                                ],
                            ),
                            html.Div(id="lib-status", role="status"),
                            html.Div(id="subfolder-chips", className="subfolder-chips"),
                            html.Div(id="reading-list", className="reading-list"),
                        ],
                    ),
                ],
            ),
            goals_section(user["id"]),
            words_section(),
            html.Section(className="section container-wide progress-section", children=html.Div(className="grid grid-3", children=[_settings_card()])),
        ]
    )


# ---------- settings summary (works signed in or out) ----------

@callback(Output("dash-prefs", "children"), Input("a11y-prefs", "data"))
def show_prefs(prefs):
    prefs = {**DEFAULT_PREFS, **(prefs or {})}
    items = []
    for key, label in LABELS.items():
        nice = next((o["label"] for o in OPTIONS[key] if o["value"] == prefs[key]), prefs[key])
        items += [html.Dt(label), html.Dd(nice)]
    return items


# ---------- library ----------

KIND_LABELS = {"pdf": "PDF", "slides": "Slides", "docx": "Word", "text": "Text"}


def _hex(color: str | None) -> str:
    return library.COLORS.get(color or "navy", library.COLORS["navy"])[1]


def _color_options() -> list[dict]:
    return [
        {
            "label": html.Span(
                [html.Span(className="swatch-dot", style={"background": hexv}), html.Span(name, className="sr-only")],
                title=name,
            ),
            "value": key,
        }
        for key, (name, hexv) in library.COLORS.items()
    ]


def _dot(color: str | None) -> html.Span:
    return html.Span(className="folder-dot", style={"background": _hex(color)}, **{"aria-hidden": "true"})


def _folder_label(name, count, depth=0, color=None, icon=None):
    return html.Span(
        className="folder-label",
        style={"paddingLeft": f"{depth * 18}px"},
        children=[
            html.Span("↳", className="folder-branch", **{"aria-hidden": "true"}) if depth else None,
            _dot(color) if color else html.Span(icon or "", className="folder-icon", **{"aria-hidden": "true"}),
            html.Span(name, className="folder-name"),
            html.Span(str(count), className="folder-count"),
        ],
    )


@callback(
    Output("folder-pick", "options"),
    Output("folder-pick", "value"),
    Output("reading-list", "children"),
    Output("library-title", "children"),
    Output("folder-tools", "hidden"),
    Output("folder-color", "value"),
    Output("new-folder-parent", "options"),
    Output("new-folder-parent", "value"),
    Output("subfolder-chips", "children"),
    Input("lib-refresh", "data"),
    Input("folder-pick", "value"),
)
def render_library(_refresh, picked):
    user = accounts.current_user()
    if not user:
        return [], "all", None, "", True, None, [], None, None
    uid = user["id"]
    tree = library.folders(uid)
    by_id = {str(f["id"]): f for f in tree}
    picked = picked if picked in ({"all", "none"} | set(by_id)) else "all"
    current = by_id.get(picked)

    options = [
        {"label": _folder_label("All readings", len(library.readings(uid, "all")), icon="▤"), "value": "all"},
        {"label": _folder_label("Not in a folder", len(library.readings(uid, "none")), icon="○"), "value": "none"},
    ] + [{"label": _folder_label(f["name"], f["n"], f["depth"], f["color"]), "value": str(f["id"])} for f in tree]

    if current:
        title = html.Span([_dot(current["color"]), current["path"]], className="lib-title")
    else:
        title = "All readings" if picked == "all" else "Not in a folder"
    parent_options = [{"label": "Top level", "value": "top"}] + [
        {"label": f["path"], "value": str(f["id"])} for f in tree if f["depth"] + 1 < library.MAX_DEPTH
    ]
    parent_value = picked if current and current["depth"] + 1 < library.MAX_DEPTH else "top"

    subs = [f for f in tree if current and f["parent_id"] == current["id"]]
    chips = None
    if subs:
        chips = [html.Span("Subfolders:", className="tool-label")] + [
            html.Button(
                [_dot(f["color"]), f"{f['name']} ({f['n']})"],
                id={"type": "open-folder", "id": f["id"]},
                className="folder-chip",
                n_clicks=0,
            )
            for f in subs
        ]

    move_options = [{"label": "Not in a folder", "value": "none"}] + [{"label": f["path"], "value": str(f["id"])} for f in tree]
    rows = library.readings(uid, picked)
    if not rows:
        body = html.Div(
            className="reader-empty dots",
            children=html.Div(
                className="reader-empty-inner",
                children=[
                    html.H3("Nothing here yet."),
                    html.P("Open a reading in the Reading Studio and press “Save to my library”."),
                ],
            ),
        )
    else:
        body = [_reading_card(r, picked, move_options, by_id) for r in rows]
    return (
        options, picked, body, title, current is None, current["color"] if current else None,
        parent_options, parent_value, chips,
    )


def _reading_card(r, picked, move_options, by_id):
    folder = by_id.get(str(r["folder_id"])) if r["folder_id"] else None
    return html.Div(
        className="card reading-card",
        style={"borderLeft": f"6px solid {_hex(folder['color'])}"} if folder else {},
        children=[
            html.Div(
                [
                    html.Span(KIND_LABELS.get(r["kind"], "Text"), className="tag"),
                    html.H3(r["title"]),
                    html.P(
                        [f"{r['word_count']:,} words · saved {r['updated_at'][:10]}"]
                        + ([" · ", _dot(folder["color"]), folder["path"]] if folder and picked == "all" else []),
                        className="muted",
                    ),
                ]
            ),
            html.Div(
                className="reading-actions",
                children=[
                    dcc.Link("Open", href=f"/reading-assistant?open={r['id']}", className="btn btn-primary btn-small"),
                    html.Div(
                        className="move-to",
                        children=[
                            html.Span("Move to", className="tool-label"),
                            dcc.Dropdown(
                                id={"type": "move-reading", "id": r["id"]},
                                options=move_options,
                                value=str(r["folder_id"]) if r["folder_id"] else "none",
                                clearable=False,
                                searchable=False,
                                className="move-dropdown",
                            ),
                        ],
                    ),
                    dcc.ConfirmDialogProvider(
                        html.Button("Delete", className="btn btn-secondary btn-small btn-danger"),
                        id={"type": "delete-reading", "id": r["id"]},
                        message=f"Delete “{r['title']}” from your library? This can't be undone.",
                    ),
                ],
            ),
        ],
    )


@callback(
    Output("folder-pick", "value", allow_duplicate=True),
    Input({"type": "open-folder", "id": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_subfolder(_clicks):
    if not ctx.triggered_id or not ctx.triggered[0]["value"]:
        return no_update
    return str(ctx.triggered_id["id"])


@callback(
    Output("lib-refresh", "data"),
    Output("lib-status", "children"),
    Output("new-folder-name", "value"),
    Input("new-folder-btn", "n_clicks"),
    Input("new-folder-name", "n_submit"),
    Input("delete-folder-confirm", "submit_n_clicks"),
    Input("folder-color", "value"),
    Input({"type": "move-reading", "id": ALL}, "value"),
    Input({"type": "delete-reading", "id": ALL}, "submit_n_clicks"),
    State("new-folder-name", "value"),
    State("new-folder-parent", "value"),
    State("new-folder-color", "value"),
    State("folder-pick", "value"),
    State("lib-refresh", "data"),
    prevent_initial_call=True,
)
def library_action(_add, _add_enter, _del_folder, color, _moves, _dels, new_name, parent, new_color, picked, refresh):
    user = accounts.current_user()
    trig = ctx.triggered_id
    nothing = (no_update, no_update, no_update)
    if not user or trig is None or not ctx.triggered[0]["value"]:
        return nothing
    uid, bump = user["id"], (refresh or 0) + 1
    real_folder = picked not in ("all", "none", None)
    try:
        if trig in ("new-folder-btn", "new-folder-name"):
            parent_id = None if parent in (None, "top") else int(parent)
            library.create_folder(uid, new_name, new_color or "navy", parent_id)
            return bump, _ok(f"Folder “{' '.join(new_name.split())}” added."), ""
        if trig == "folder-color" and real_folder:
            current = next((f for f in library.folders(uid) if str(f["id"]) == picked), None)
            if not current or current["color"] == color:
                return nothing  # the panel just redrew
            library.set_folder_color(uid, int(picked), color)
            return bump, _ok("Folder color changed."), no_update
        if trig == "delete-folder-confirm" and real_folder:
            library.delete_folder(uid, int(picked))
            return bump, _ok("Folder deleted. Everything inside moved up one level."), no_update
        if isinstance(trig, dict) and trig["type"] == "move-reading":
            target = None if ctx.triggered[0]["value"] == "none" else int(ctx.triggered[0]["value"])
            current = library.open_reading(uid, trig["id"])
            if not current or current.get("folder_id") == target:
                return nothing  # list just redrew; nothing moved
            library.move_reading(uid, trig["id"], target)
            return bump, _ok("Reading moved."), no_update
        if isinstance(trig, dict) and trig["type"] == "delete-reading":
            library.delete_reading(uid, trig["id"])
            return bump, _ok("Reading deleted."), no_update
    except library.LibraryError as exc:
        return no_update, html.P(["! ", str(exc)], className="status-error"), no_update
    return nothing


def _ok(text: str) -> html.P:
    return html.P(["✓ ", text], className="status-ok")


# ---------- reading goals ----------

@callback(
    Output("goal-stats", "children"),
    Output("goal-chart", "children"),
    Output("goal-list", "children"),
    Input("goals-refresh", "data"),
)
def render_goals(_refresh):
    user = accounts.current_user()
    if not user:
        return None, None, None
    uid, today = user["id"], date.today()
    goal = progress.daily_goal(uid)
    days = progress.minutes_by_day(uid, today, 7)
    tiles = stat_tiles(
        days[-1]["minutes"], goal, progress.streak(uid, today, goal),
        sum(d["minutes"] for d in days), progress.word_counts(uid)["this_week"],
    )
    goals = progress.personal_goals(uid)
    items = [goal_item(g, today) for g in goals] or [html.Li("No goals yet. Add one above!", className="muted goal-empty")]
    return tiles, week_chart(days, goal, today), items


@callback(
    Output("goals-refresh", "data"),
    Output("goal-status", "children"),
    Output("goal-text", "value"),
    Output("goal-due", "date"),
    Input("goal-minutes", "value"),
    Input("goal-add-btn", "n_clicks"),
    Input("goal-text", "n_submit"),
    Input({"type": "goal-done", "id": ALL}, "value"),
    Input({"type": "goal-del", "id": ALL}, "n_clicks"),
    State("goal-text", "value"),
    State("goal-due", "date"),
    State("goals-refresh", "data"),
    prevent_initial_call=True,
)
def goal_action(minutes, _add, _enter, _dones, _dels, text, due, refresh):
    user = accounts.current_user()
    trig = ctx.triggered_id
    nothing = (no_update,) * 4
    if not user or trig is None:
        return nothing
    uid, bump = user["id"], (refresh or 0) + 1
    try:
        if trig == "goal-minutes" and minutes:
            if progress.daily_goal(uid) == minutes:
                return nothing
            progress.set_daily_goal(uid, minutes)
            return bump, _ok(f"Daily goal set to {minutes} minutes."), no_update, no_update
        if trig in ("goal-add-btn", "goal-text") and ctx.triggered[0]["value"]:
            progress.add_goal(uid, text, due)
            return bump, _ok("Goal added."), "", None
        if isinstance(trig, dict) and trig["type"] == "goal-done":
            done = "done" in (ctx.triggered[0]["value"] or [])
            current = next((g for g in progress.personal_goals(uid) if g["id"] == trig["id"]), None)
            if not current or bool(current["done"]) == done:
                return nothing  # list just redrew
            progress.set_goal_done(uid, trig["id"], done)
            return bump, _ok("Nice work! Goal done." if done else "Goal moved back to your list."), no_update, no_update
        if isinstance(trig, dict) and trig["type"] == "goal-del" and ctx.triggered[0]["value"]:
            progress.delete_goal(uid, trig["id"])
            return bump, _ok("Goal removed."), no_update, no_update
    except progress.ProgressError as exc:
        return no_update, html.P(["! ", str(exc)], className="status-error"), no_update, no_update
    return nothing


# ---------- saved words ----------

@callback(
    Output("word-list", "children"),
    Output("word-counts", "children"),
    Input("words-refresh", "data"),
    Input("word-search", "value"),
    Input("word-show", "value"),
    Input("word-quiz", "value"),
)
def render_words(_refresh, search, show, quiz):
    user = accounts.current_user()
    if not user:
        return None, None
    uid = user["id"]
    c = progress.word_counts(uid)
    counts = [
        html.Span([html.Strong(str(c["total"])), " saved"], className="mini-tag"),
        html.Span([html.Strong(str(c["learning"])), " learning"], className="mini-tag mini-tag-place"),
        html.Span([html.Strong(str(c["known"])), " known"], className="mini-tag kind-med"),
    ]
    rows = progress.words(uid, show or "all", search or "")
    if not rows:
        msg = "No words match." if (search or show not in (None, "all")) else "No saved words yet."
        return html.Div(className="reader-empty dots", children=html.Div(className="reader-empty-inner", children=[html.H3(msg), html.P("Look up a word in the Reading Studio and save it here to practice.")])), counts
    quiz_on = "quiz" in (quiz or [])
    return [word_card(w, quiz_on) for w in rows], counts


@callback(
    Output("words-refresh", "data"),
    Input({"type": "word-known", "id": ALL}, "n_clicks"),
    Input({"type": "word-del", "id": ALL}, "n_clicks"),
    State("words-refresh", "data"),
    prevent_initial_call=True,
)
def word_action(_known, _dels, refresh):
    user = accounts.current_user()
    trig = ctx.triggered_id
    if not user or not isinstance(trig, dict) or not ctx.triggered[0]["value"]:
        return no_update
    uid = user["id"]
    if trig["type"] == "word-del":
        progress.delete_word(uid, trig["id"])
    else:
        current = next((w for w in progress.words(uid) if w["id"] == trig["id"]), None)
        if current:
            progress.set_known(uid, trig["id"], not current["known"])
    return (refresh or 0) + 1
