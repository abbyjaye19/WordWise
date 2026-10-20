"""Reading Studio: bring in a reading, change how it looks, listen, look up words,
highlight, and get AI help (explain / summarize / check understanding).

The reading itself is drawn in the browser by assets/studio.js (fast even for long
files, and it powers read-aloud word highlighting). Dash handles uploads and AI help.
"""

from __future__ import annotations

from datetime import date

import dash
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, no_update

from services import accounts, ai, documents, export, library, preferences, progress

dash.register_page(__name__, path="/reading-assistant", name="Reading Assistant", order=1)

LEVEL_OPTIONS = [{"label": label, "value": value} for value, label in ai.LEVELS.items()]


# ---------- layout pieces ----------

def _tool_btn(label: str, id_: str, pressed: bool | None = None, extra: str = "") -> html.Button:
    props = {"aria-pressed": "true" if pressed else "false"} if pressed is not None else {}
    return html.Button(label, id=id_, className=f"tool-btn {extra}".strip(), type="button", **props)


def _intake() -> html.Details:
    return html.Details(
        id="intake",
        className="card intake",
        open=True,
        children=[
            html.Summary(html.H2("Add or change your reading", className="intake-title")),
            html.Div(
                className="intake-grid",
                children=[
                    html.Div(
                        [
                            html.H3("Upload a file"),
                            dcc.Upload(
                                id="doc-upload",
                                className="upload-zone",
                                accept=".pdf,.pptx,.docx,.txt,.md",
                                max_size=documents.MAX_BYTES,
                                children=html.Div(
                                    [
                                        html.Strong("Choose a file"),
                                        html.Span(" or drag it here"),
                                        html.Br(),
                                        html.Span("PDF, slides (.pptx), Word (.docx), or text", className="muted"),
                                    ]
                                ),
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.H3("Paste text"),
                            dcc.Textarea(
                                id="paste-text",
                                className="paste-box",
                                placeholder="Paste a page from a book, an article, or your notes…",
                            ),
                            html.Button("Read this text", id="paste-btn", className="btn btn-secondary btn-small", n_clicks=0),
                        ]
                    ),
                    html.Div(
                        [
                            html.H3("Try a sample"),
                            html.Div(
                                className="sample-list",
                                children=[
                                    html.Button(
                                        [html.Strong(s["title"]), html.Span(s["level"], className="muted")],
                                        id={"type": "sample-btn", "id": s["id"]},
                                        className="sample-btn",
                                        n_clicks=0,
                                    )
                                    for s in documents.samples()
                                ],
                            ),
                        ]
                    ),
                ],
            ),
            dcc.Loading(html.Div(id="doc-status", className="doc-status", role="status"), type="dot", color="#1B3366"),
        ],
    )


def _toolbar() -> html.Div:
    return html.Div(
        id="studio-toolbar",
        className="studio-toolbar",
        role="toolbar",
        **{"aria-label": "Reading tools"},
        children=[
            html.Div(
                className="tool-group",
                children=[
                    html.Span("Listen", className="tool-label"),
                    _tool_btn("▶ Read aloud", "tts-play", extra="tool-primary"),
                    _tool_btn("❚❚ Pause", "tts-pause"),
                    _tool_btn("■ Stop", "tts-stop"),
                    html.Button("⏮", id="tts-back", className="tool-btn tool-icon", type="button", title="Back one sentence", **{"aria-label": "Back one sentence"}),
                    html.Button("⟲ Replay", id="tts-replay", className="tool-btn", type="button", title="Replay this sentence"),
                    html.Button("⏭", id="tts-next", className="tool-btn tool-icon", type="button", title="Next sentence", **{"aria-label": "Next sentence"}),
                    html.Span(
                        className="speed-ctl",
                        role="group",
                        **{"aria-label": "Read-aloud speed"},
                        children=[
                            html.Button("−", id="tts-slower", className="tool-btn tool-icon", type="button", title="Slower", **{"aria-label": "Slower"}),
                            html.Span("Normal · 1×", id="tts-speed-label", className="speed-label", **{"aria-live": "polite"}),
                            html.Button("+", id="tts-faster", className="tool-btn tool-icon", type="button", title="Faster", **{"aria-label": "Faster"}),
                        ],
                    ),
                    html.Label(
                        [
                            html.Span("Voice", className="sr-only"),
                            # Filled by assets/studio.js with this browser's English voices, the most natural first.
                            html.Select(id="tts-voice", className="tool-select voice-select", title="Choose a voice"),
                        ]
                    ),
                    html.Button("Highlight: Both", id="tts-readalong", className="tool-btn", type="button",
                                title="What is highlighted while reading aloud: word, sentence, or both"),
                ],
            ),
            html.Div(
                className="tool-group",
                children=[
                    html.Span("Tap a word to", className="tool-label"),
                    _tool_btn("Look it up", "mode-lookup", pressed=True),
                    _tool_btn("Highlight", "mode-highlight", pressed=False),
                    _tool_btn("Read from there", "mode-read", pressed=False),
                ],
            ),
            html.Div(
                className="tool-group",
                children=[
                    html.Span("Marker", className="tool-label"),
                    html.Button(html.Span("Yellow", className="sr-only"), id="color-gold", className="swatch hl-gold", **{"aria-pressed": "true", "title": "Yellow"}),
                    html.Button(html.Span("Green", className="sr-only"), id="color-green", className="swatch hl-green", **{"aria-pressed": "false", "title": "Green"}),
                    html.Button(html.Span("Blue", className="sr-only"), id="color-blue", className="swatch hl-blue", **{"aria-pressed": "false", "title": "Blue"}),
                    _tool_btn("Clear", "tool-clear"),
                ],
            ),
            html.Div(
                className="tool-group",
                children=[
                    html.Span("Focus", className="tool-label"),
                    _tool_btn("Reading ruler", "tool-ruler", pressed=False),
                    _tool_btn("One paragraph", "tool-focus", pressed=False),
                    _tool_btn("Aa Text settings", "studio-settings"),
                ],
            ),
        ],
    )


def _level_bar() -> html.Div:
    """Reading Levels: switch the whole reading between the original and AI versions."""
    return html.Div(
        id="level-bar",
        className="level-bar",
        hidden=True,
        children=[
            html.Span("Reading level", className="tool-label"),
            html.Div(
                className="segmented",
                role="group",
                **{"aria-label": "Reading level"},
                children=[
                    _tool_btn("Original", "view-original", pressed=True),
                    _tool_btn("Simplified wording", "view-simplified", pressed=False),
                    _tool_btn("Detailed explanation", "view-detailed", pressed=False),
                ],
            ),
            html.Button("Show original too", id="view-showorig", className="tool-btn", type="button", hidden=True, **{"aria-pressed": "false"}),
            html.Span(id="view-status", className="view-status", role="status"),
        ],
    )


def _help_panel() -> html.Aside:
    return html.Aside(
        className="help-panel",
        **{"aria-label": "Reading help"},
        children=[
            html.Div(
                className="help-block",
                children=[
                    html.H3("Who is reading?"),
                    html.P("We'll explain things at this level.", className="muted"),
                    dcc.RadioItems(
                        id="reader-level",
                        options=LEVEL_OPTIONS,
                        value="13-17",
                        persistence=True,
                        persistence_type="local",
                        className="choice-row compact",
                        inputClassName="choice-input",
                        labelClassName="choice-label",
                    ),
                ],
            ),
            html.Div(
                className="help-block",
                children=[
                    html.H3("Understand a part"),
                    html.Div(id="selection-preview", className="selection-preview"),
                    html.Div(
                        className="btn-stack",
                        children=[
                            html.Button("Make it simpler", id="explain-simpler", className="btn btn-primary btn-small", n_clicks=0, disabled=True),
                            html.Button("Give me an example", id="explain-example", className="btn btn-secondary btn-small", n_clicks=0, disabled=True),
                            html.Button("Break it into steps", id="explain-steps", className="btn btn-secondary btn-small", n_clicks=0, disabled=True),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="help-block",
                children=[
                    html.H3("Look up a word"),
                    html.Div(
                        className="lookup-row",
                        children=[
                            html.Label("Word to look up", htmlFor="lookup-input", className="sr-only"),
                            dcc.Input(id="lookup-input", type="text", placeholder="Type a word", className="text-input"),
                            html.Button("Look up", id="lookup-btn", className="btn btn-secondary btn-small", n_clicks=0),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="help-block",
                children=[
                    html.H3("Sum it up"),
                    html.P("Get the big idea, key points, and questions to check yourself.", className="muted"),
                    dcc.Dropdown(id="summary-scope", clearable=False, searchable=False, className="scope-dropdown"),
                    html.Button("Summarize", id="summarize-btn", className="btn btn-primary btn-small", n_clicks=0, disabled=True),
                ],
            ),
            html.Div(
                className="help-block",
                id="checkin",
                children=[
                    html.H3("How did it go?"),
                    html.P("After reading, tell us how well you understood it. It shows on your dashboard.", className="muted"),
                    dcc.RadioItems(
                        id="check-rating",
                        options=[{"label": f"{n} · {lab}", "value": n} for n, lab in progress.RATING_LABELS.items()],
                        className="choice-row compact",
                        inputClassName="choice-input",
                        labelClassName="choice-label",
                    ),
                    html.P("What made it hard? (optional)", className="muted small check-hard-label"),
                    dcc.Checklist(
                        id="check-hard",
                        options=[{"label": lab, "value": key} for key, lab in progress.HARD_REASONS.items()],
                        value=[],
                        className="choice-row compact",
                        inputClassName="choice-input",
                        labelClassName="choice-label",
                    ),
                    html.Button("Save check-in", id="check-save", className="btn btn-secondary btn-small", n_clicks=0),
                    html.Div(id="check-status", role="status"),
                ],
            ),
            html.Div(
                className="help-block",
                children=[
                    html.H3("Still stuck?"),
                    html.P("Chat with the AI Tutor about this reading. It can see what you're reading.", className="muted"),
                    dcc.Link("Ask the AI Tutor →", href="/ai-tutor", className="btn btn-secondary btn-small"),
                ],
            ),
            dcc.Loading(
                html.Div(id="help-output", className="help-output", **{"aria-live": "polite"}),
                type="dot",
                color="#1B3366",
            ),
        ],
    )


def _doc_actions(user: dict | None) -> html.Div:
    """Save to the library (signed in) and download/print (everyone)."""
    folders = library.folders(user["id"]) if user else []
    folder_options = [{"label": "Not in a folder", "value": "none"}] + [
        {"label": f"📁 {f['path']}", "value": str(f["id"])} for f in folders
    ]
    save_group = html.Div(
        className="action-group",
        hidden=not user,
        children=[
            html.Span("Save", className="tool-label"),
            dcc.Dropdown(
                id="save-folder",
                options=folder_options,
                value="none",
                clearable=False,
                searchable=False,
                className="save-folder",
            ),
            html.Button("Save to my library", id="save-btn", className="btn btn-primary btn-small", n_clicks=0),
        ],
    )
    signin_group = html.Div(
        className="action-group",
        hidden=bool(user),
        children=[dcc.Link("Sign in to save this reading", href="/account", className="text-link")],
    )
    export_group = html.Div(
        className="action-group",
        children=[
            html.Span("Download", className="tool-label"),
            html.Button("Word (.docx)", id="export-docx", className="tool-btn", n_clicks=0),
            html.Button("Web page (.html)", id="export-html", className="tool-btn", n_clicks=0),
            html.Button("Print or PDF", id="export-print", className="tool-btn", type="button"),
        ],
    )
    return html.Div(
        id="doc-actions",
        className="doc-actions",
        hidden=True,
        children=[
            html.Div([save_group, signin_group, export_group], className="doc-actions-row"),
            html.Div(id="save-status", role="status"),
            html.Div(id="today-reading"),
            html.P(
                "Downloads keep your highlights, font, text size, spacing, and background.",
                className="muted small",
            ),
        ],
    )


def layout(open: str | None = None, **_query):  # noqa: A002 - "open" is the URL parameter name
    user = accounts.current_user()
    opened = None
    if user and open and str(open).isdigit():
        opened = library.open_reading(user["id"], int(open))
    store_kwargs = {"data": opened} if opened else {}
    return _layout(user, store_kwargs, bad_link=bool(open) and not opened)


def _layout(user, store_kwargs, bad_link: bool):
    return html.Div(
    [
        dcc.Store(id="doc-store", storage_type="session", **store_kwargs),
        dcc.Store(id="word-request"),
        dcc.Store(id="selection-store"),
        dcc.Store(id="highlights-store"),
        dcc.Store(id="reading-beat"),
        dcc.Store(id="tool-beat"),
        dcc.Store(id="view-store", storage_type="session"),
        dcc.Store(id="tts-fixes"),
        dcc.Download(id="download"),
        html.Div(id="reader-sink", hidden=True),
        html.Div(id="view-sink", hidden=True),
        html.Div(id="tool-sink", hidden=True),
        html.Div(
            className="container-wide",
            children=html.P(
                "! We couldn't open that saved reading. Make sure you're signed in to the right account.",
                className="status-error",
            ),
        )
        if bad_link
        else None,
        html.Section(
            className="studio-head",
            children=html.Div(
                className="container-wide",
                children=[
                    html.P("Read", className="eyebrow"),
                    html.H1("Reading Studio"),
                    html.P(
                        "Bring in anything you need to read. Make it easier to see, listen to it, "
                        "and get help with the hard parts.",
                        className="lead",
                    ),
                ],
            ),
        ),
        html.Div(className="container-wide", children=[_intake()]),
        html.Div(
            className="container-wide studio-main",
            children=[
                html.Div(
                    className="reader-col",
                    children=[
                        _toolbar(),
                        html.Div(id="doc-title", className="doc-title"),
                        _doc_actions(user),
                        _level_bar(),
                        html.Div(
                            id="reader-empty",
                            className="reader-empty dots",
                            children=html.Div(
                                className="reader-empty-inner",
                                children=[
                                    html.H2("Your reading will show up here."),
                                    html.P("Upload a file, paste some text, or try a sample above."),
                                ],
                            ),
                        ),
                        # Filled by assets/studio.js — Dash never puts children here.
                        html.Div(id="reader", className="reader", lang="en"),
                    ],
                ),
                _help_panel(),
            ],
        ),
    ]
    )


# ---------- callbacks: loading a reading ----------

@callback(
    Output("doc-store", "data"),
    Output("doc-status", "children"),
    Input("doc-upload", "contents"),
    Input("paste-btn", "n_clicks"),
    Input({"type": "sample-btn", "id": ALL}, "n_clicks"),
    State("doc-upload", "filename"),
    State("paste-text", "value"),
    prevent_initial_call=True,
)
def load_document(contents, _paste, _samples, filename, pasted):
    trig = ctx.triggered_id
    if trig is None or (isinstance(trig, dict) and not ctx.triggered[0]["value"]):
        return no_update, no_update
    try:
        if trig == "doc-upload":
            if not contents:
                return no_update, no_update
            doc = documents.from_upload(contents, filename)
        elif trig == "paste-btn":
            if not (pasted or "").strip():
                return no_update, _status("Paste some text in the box first.", ok=False)
            doc = documents.from_text(pasted)
        else:
            doc = documents.from_sample(trig["id"])
    except documents.DocumentError as exc:
        return no_update, _status(str(exc), ok=False)
    words = sum(len(p.split()) for s in doc["sections"] for p in s["paragraphs"])
    msg = f"Ready: “{doc['title']}” · about {words:,} words."
    if doc.get("note"):
        msg += " " + doc["note"]
    return doc, _status(msg, ok=True)


def _status(text: str, ok: bool) -> html.P:
    icon = "✓ " if ok else "! "
    return html.P([html.Span(icon, **{"aria-hidden": "true"}), text], className="status-ok" if ok else "status-error")


@callback(
    Output("summary-scope", "options"),
    Output("summary-scope", "value"),
    Output("summarize-btn", "disabled"),
    Output("reader-empty", "hidden"),
    Output("doc-title", "children"),
    Output("intake", "open"),
    Output("doc-actions", "hidden"),
    Output("save-btn", "children"),
    Output("save-folder", "value"),
    Output("level-bar", "hidden"),
    Input("doc-store", "data"),
)
def on_document(doc):
    if not doc:
        return [{"label": "Whole reading", "value": "all"}], "all", True, False, None, True, True, "Save to my library", "none", True
    options = [{"label": "Whole reading", "value": "all"}]
    if len(doc["sections"]) > 1:
        options += [{"label": s["label"], "value": str(i)} for i, s in enumerate(doc["sections"])]
    saved = bool(doc.get("saved_id"))
    tag = "Saved in your library" if saved else "Now reading"
    title = html.Div([html.Span(tag, className="tag"), html.H2(doc["title"])])
    folder = str(doc["folder_id"]) if doc.get("folder_id") else "none"
    return options, "all", False, True, title, False, False, "Save changes" if saved else "Save to my library", folder, False


# ---------- callbacks: save + export ----------

@callback(
    Output("doc-store", "data", allow_duplicate=True),
    Output("save-status", "children"),
    Input("save-btn", "n_clicks"),
    State("doc-store", "data"),
    State("highlights-store", "data"),
    State("save-folder", "value"),
    prevent_initial_call=True,
)
def save_reading(n, doc, highlights, folder):
    if not n or not doc:
        return no_update, no_update
    user = accounts.current_user()
    if not user:
        return no_update, _status("Please sign in to save. Your reading is still here.", ok=False)
    folder_id = None if folder in (None, "none") else int(folder)
    try:
        rid = library.save_reading(user["id"], doc, highlights or {}, folder_id, doc.get("saved_id"))
    except library.LibraryError as exc:
        return no_update, _status(str(exc), ok=False)
    where = "your library" if folder_id is None else "your folder"
    updated = {**doc, "saved_id": rid, "folder_id": folder_id, "highlights": highlights or {}}
    return updated, _status(f"Saved to {where} with {len(highlights or {})} highlighted words.", ok=True)


@callback(
    Output("download", "data"),
    Input("export-docx", "n_clicks"),
    Input("export-html", "n_clicks"),
    State("doc-store", "data"),
    State("highlights-store", "data"),
    State("a11y-prefs", "data"),
    prevent_initial_call=True,
)
def download(_docx, _html, doc, highlights, prefs):
    if not doc or not ctx.triggered[0]["value"]:
        return no_update
    if ctx.triggered_id == "export-docx":
        data = export.to_docx(doc, highlights or {}, prefs)
        return dcc.send_bytes(data, export.safe_filename(doc.get("title"), "docx"))
    return dict(content=export.to_html(doc, highlights or {}, prefs), filename=export.safe_filename(doc.get("title"), "html"))


dash.clientside_callback(
    "function (doc, view) { if (window.WW) { window.WW.render(doc, view); } return ''; }",
    Output("reader-sink", "children"),
    Input("doc-store", "data"),
    Input("view-store", "data"),
)

# Show the saved speed / highlight style on the toolbar as soon as the page opens.
dash.clientside_callback(
    "function (_id, _prefs) { if (window.WW && window.WW.refreshTools) { setTimeout(window.WW.refreshTools, 0); } return ''; }",
    Output("tool-sink", "children"),
    Input("studio-toolbar", "id"),
    Input("a11y-prefs", "data"),
)


# ---------- callbacks: Reading Levels (original / simplified / detailed) ----------

def _paragraphs(doc: dict) -> list[str]:
    return [p for s in doc["sections"] for p in s["paragraphs"]]


@callback(
    Output("view-store", "data"),
    Output("view-status", "children"),
    Input("view-original", "n_clicks"),
    Input("view-simplified", "n_clicks"),
    Input("view-detailed", "n_clicks"),
    Input("reader-level", "value"),
    Input("doc-store", "data"),
    State("view-store", "data"),
    prevent_initial_call=True,
    running=[
        (Output("view-simplified", "disabled"), True, False),
        (Output("view-detailed", "disabled"), True, False),
        (Output("view-status", "className"), "view-status working", "view-status"),
    ],
)
def change_view(_o, _s, _d, level, doc, view):
    trig = ctx.triggered_id
    if not doc:
        return None, ""
    paras = _paragraphs(doc)
    fits = bool(view) and view.get("title") == doc["title"] and view.get("count") == len(paras)
    if trig == "doc-store":  # a new reading starts in its original wording (saving keeps the view)
        return (no_update, no_update) if fits else (None, "")
    if trig == "view-original":
        return None, ""
    if trig == "reader-level":
        if not fits:
            return no_update, no_update
        mode = view["mode"]  # same view, new reader level
    else:
        mode = "simplified" if trig == "view-simplified" else "detailed"
    user = accounts.current_user()
    try:
        rewritten, covered = ai.rewrite(paras, mode, level or "13-17", _profile(user))
    except ai.AIError as exc:
        return no_update, _status(str(exc), ok=False)
    if user:
        progress.log_tool(user["id"], f"{mode}_view")
    data = {"mode": mode, "level": level, "title": doc["title"], "count": len(paras), "covered": covered, "paras": rewritten}
    return data, ""


# ---------- callbacks: Pronunciation Helper (so read-aloud says words like "read" correctly) ----------

@callback(Output("tts-fixes", "data"), Input("doc-store", "data"), Input("view-store", "data"))
def pronunciation_fixes(doc, view):
    """Runs in the background when a reading (or an AI view of it) opens; read-aloud uses the
    result as soon as it arrives. If it fails, read-aloud still works with the voice's own guesses."""
    if not doc:
        return {}
    paras = _paragraphs(doc)
    if view and view.get("title") == doc["title"] and view.get("count") == len(paras):
        covered = view.get("covered", 0)
        paras = list(view.get("paras") or [])[:covered] + paras[covered:]  # what's on screen
    try:
        return ai.pronunciation(paras)
    except ai.AIError:
        return no_update


dash.clientside_callback(
    "function (fixes) { if (window.WW && window.WW.setFixes) { window.WW.setFixes(fixes); } return ''; }",
    Output("view-sink", "children"),
    Input("tts-fixes", "data"),
)


def _profile(user: dict | None) -> str:
    """The student's self-reported profile, given to the AI so help adapts to them."""
    if not user:
        return ""
    return preferences.profile_context(preferences.load_profile(user["id"]), progress.recent_comprehension(user["id"]))


# ---------- callbacks: tool use + comprehension check-ins (for My Dashboard insights) ----------

@callback(Output("tool-sink", "title"), Input("tool-beat", "data"), prevent_initial_call=True)
def log_tool_use(beat):
    user = accounts.current_user()
    if user and beat and beat.get("tool") in ("read_aloud", "replay", "highlighter", "ruler", "focus"):
        progress.log_tool(user["id"], beat["tool"])
    return no_update


@callback(
    Output("check-status", "children"),
    Output("check-rating", "value"),
    Output("check-hard", "value"),
    Input("check-save", "n_clicks"),
    State("check-rating", "value"),
    State("check-hard", "value"),
    State("doc-store", "data"),
    prevent_initial_call=True,
)
def save_check_in(n, rating, hard, doc):
    if not n:
        return no_update, no_update, no_update
    user = accounts.current_user()
    if not user:
        return html.P(["Sign in to save check-ins. ", dcc.Link("Sign in", href="/account", className="text-link")], className="muted"), no_update, no_update
    if not rating:
        return _status("Pick how well you understood it first.", ok=False), no_update, no_update
    progress.add_check(user["id"], (doc or {}).get("title", ""), int(rating), hard or [])
    progress.log_tool(user["id"], "check_in")
    msg = html.P(["✓ Saved. See it on ", dcc.Link("your dashboard", href="/dashboard#insights", className="text-link"), "."], className="status-ok")
    return msg, None, []


@callback(
    Output("selection-preview", "children"),
    Output("explain-simpler", "disabled"),
    Output("explain-example", "disabled"),
    Output("explain-steps", "disabled"),
    Input("selection-store", "data"),
)
def on_selection(sel):
    text = (sel or {}).get("text", "").strip()
    if not text:
        return html.P("Drag across a sentence or paragraph in your reading to select it.", className="muted"), True, True, True
    short = text if len(text) <= 160 else text[:157] + "…"
    return html.Blockquote(short, className="selection-quote"), False, False, False


# ---------- callbacks: AI help ----------

@callback(
    Output("help-output", "children"),
    Input("word-request", "data"),
    Input("lookup-btn", "n_clicks"),
    Input("lookup-input", "n_submit"),
    Input("explain-simpler", "n_clicks"),
    Input("explain-example", "n_clicks"),
    Input("explain-steps", "n_clicks"),
    Input("summarize-btn", "n_clicks"),
    State("lookup-input", "value"),
    State("selection-store", "data"),
    State("doc-store", "data"),
    State("reader-level", "value"),
    State("summary-scope", "value"),
    prevent_initial_call=True,
)
def help_me(word_req, _lb, _ls, _s, _e, _st, _sum, typed, sel, doc, level, scope):
    trig = ctx.triggered_id
    level = level or "13-17"
    user = accounts.current_user()
    profile = _profile(user)

    def used(tool):
        if user:
            progress.log_tool(user["id"], tool)

    try:
        if trig == "word-request" and word_req:
            word = word_req.get("word", "").strip()
            if not word:
                return no_update
            sentence = word_req.get("sentence", "")
            card = _word_card(word, ai.word_help(word, sentence, level, profile), sentence, (doc or {}).get("title", ""))
            used("word_help")
            return card
        if trig in ("lookup-btn", "lookup-input"):
            word = (typed or "").strip().split(" ")[0]
            if not word:
                return _error_card("Type a word in the box first.")
            card = _word_card(word, ai.word_help(word, "", level, profile))
            used("word_help")
            return card
        if trig in ("explain-simpler", "explain-example", "explain-steps"):
            text = (sel or {}).get("text", "").strip()
            if not text:
                return _error_card("Select some text in your reading first.")
            mode = trig.split("-")[1]
            card = _explain_card(mode, ai.explain(text, mode, level, profile))
            used("explain")
            return card
        if trig == "summarize-btn" and doc:
            idx = None if scope in (None, "all") else int(scope)
            label = "Whole reading" if idx is None else doc["sections"][idx]["label"]
            summary, trimmed = ai.summarize(documents.section_text(doc, idx), label, level, profile)
            used("summary")
            return _summary_card(label, summary, trimmed)
    except ai.AIError as exc:
        return _error_card(str(exc))
    return no_update


@callback(
    Output("save-word-status", "children"),
    Output("save-word-btn", "children"),
    Input("save-word-btn", "n_clicks"),
    State("word-data", "data"),
    prevent_initial_call=True,
)
def save_word(n, info):
    if not n or not info:
        return no_update, no_update
    user = accounts.current_user()
    if not user:
        return html.P(["Sign in to save words. ", dcc.Link("Sign in", href="/account", className="text-link")], className="muted"), no_update
    try:
        progress.save_word(user["id"], info)
    except progress.ProgressError as exc:
        return html.P(["! ", str(exc)], className="status-error"), no_update
    progress.log_tool(user["id"], "save_word")
    return html.P(["✓ Saved to ", dcc.Link("your word bank", href="/dashboard#words", className="text-link"), "."], className="status-ok"), "★ Saved"


@callback(
    Output("today-reading", "children"),
    Input("reading-beat", "data"),
)
def log_reading_time(beat):
    """The browser reports active reading time; signed-in students see today's progress."""
    user = accounts.current_user()
    if not user:
        return None
    if beat and beat.get("seconds"):
        progress.log_reading(user["id"], beat.get("day", ""), beat.get("seconds", 0), beat.get("title", ""))
    day = (beat or {}).get("day")
    today = date.fromisoformat(day) if day and progress.DAY_RE.match(day) else date.today()
    minutes = progress.minutes_by_day(user["id"], today, 1)[0]["minutes"]
    goal = progress.daily_goal(user["id"])
    pct = min(100, round(100 * minutes / goal)) if goal else 0
    return html.Div(
        className="today-reading",
        children=[
            html.Span("Today", className="tool-label"),
            html.Div(className="mini-meter", children=html.Div(className="mini-meter-fill", style={"width": f"{pct}%"})),
            html.Span(f"{minutes} of {goal} min" + (" · goal met ✓" if minutes >= goal else "")),
            dcc.Link("Goals", href="/dashboard#goals", className="text-link"),
        ],
    )


# ---------- AI answer cards (always labeled, always separate from the reading) ----------

def _listen_btn(text: str) -> html.Button:
    return html.Button("🔊 Listen", className="tool-btn speak-btn", type="button", **{"data-say": text})


def _ai_card(kind: str, children: list, say: str) -> html.Div:
    return html.Div(
        className="ai-panel ai-answer",
        children=[
            html.Div(className="ai-answer-head", children=[html.P(f"AI help · {kind}", className="ai-label"), _listen_btn(say)]),
            *children,
            html.P("AI can make mistakes. Check with your reading or a teacher.", className="ai-disclaimer"),
        ],
    )


def _word_card(word: str, w, sentence: str = "", source_title: str = "") -> html.Div:
    say = f"{word}. {w.meaning_here} For example: {w.example}"
    info = {
        "word": word, "syllables": w.syllables, "say_it": w.say_it, "part_of_speech": w.part_of_speech,
        "meaning": w.meaning_here, "synonyms": w.synonyms, "example": w.example,
        "sentence": sentence, "source_title": source_title,
    }
    return _ai_card(
        "Word",
        [
            dcc.Store(id="word-data", data=info),
            html.Div(
                className="word-head",
                children=[
                    html.H3(word, className="word-title"),
                    html.Button("☆ Save word", id="save-word-btn", className="btn btn-secondary btn-small", n_clicks=0),
                ],
            ),
            html.Div(id="save-word-status", role="status"),
            html.P([html.Strong(w.syllables), html.Span(f"  ·  say it: {w.say_it}", className="muted")]),
            html.Span(w.part_of_speech, className="tag"),
            html.H4("What it means here"),
            html.P(w.meaning_here),
            html.H4("Other words you could use") if w.synonyms else None,
            html.Div([html.Span(s, className="chip") for s in w.synonyms], className="chips") if w.synonyms else None,
            html.H4("Example"),
            html.P(w.example),
        ],
        say,
    )


EXPLAIN_TITLES = {"simpler": "Simpler words", "example": "An example", "steps": "Step by step"}


def _explain_card(mode: str, x) -> html.Div:
    points = html.Ol if mode == "steps" else html.Ul
    return _ai_card(
        EXPLAIN_TITLES[mode],
        [
            html.H3(x.heading),
            points([html.Li(p) for p in x.points], className="ai-points"),
            html.H4("Tricky words") if x.tricky_words else None,
            html.Dl([el for t in x.tricky_words for el in (html.Dt(t.word), html.Dd(t.meaning))], className="mini-dl") if x.tricky_words else None,
        ],
        x.heading + ". " + " ".join(x.points),
    )


def _summary_card(label: str, s, trimmed: bool) -> html.Div:
    return _ai_card(
        f"Summary · {label}",
        [
            html.H3("The big idea"),
            html.P(s.big_idea),
            html.H4("Key points"),
            html.Ul([html.Li(p) for p in s.key_points], className="ai-points"),
            html.H4("Words to know") if s.words_to_know else None,
            html.Dl([el for t in s.words_to_know for el in (html.Dt(t.word), html.Dd(t.meaning))], className="mini-dl") if s.words_to_know else None,
            html.H4("Check yourself"),
            html.P("Try to answer in your head first. Then tap to see an answer.", className="muted"),
            *[
                html.Details([html.Summary(q.question), html.P(q.answer)], className="check-q")
                for q in s.check_questions
            ],
            html.P("This reading is long, so the summary covers the first part only.", className="muted") if trimmed else None,
        ],
        "The big idea. " + s.big_idea + " Key points. " + " ".join(s.key_points),
    )


def _error_card(text: str) -> html.Div:
    return html.Div(className="notice-error", role="alert", children=[html.Span("! ", **{"aria-hidden": "true"}), text])
