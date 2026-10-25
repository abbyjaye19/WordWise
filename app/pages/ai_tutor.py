"""AI Tutor — a free, fast chat tutor at the student's level, optionally about their current reading."""

import dash
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, no_update

from services import accounts, ai, documents, preferences, progress

dash.register_page(__name__, path="/ai-tutor", name="AI Tutor", order=7)

LEVEL_OPTIONS = [{"label": label, "value": value} for value, label in ai.LEVELS.items()]
PREF_KEYS = list(preferences.SETTINGS)
STARTERS = [
    "Help me find my best reading settings.",
    "What is this reading mostly about?",
    "Quiz me on my reading with 3 questions.",
    "Explain a hard word to me.",
    "How can I remember what I read?",
    "Help me plan a paragraph.",
]
MAX_MESSAGES = 60  # per chat, to keep sessions (and costs) in check


def layout(**_query):
    return html.Div(
        [
            dcc.Store(id="chat-history", storage_type="session"),  # survives refreshes in this tab
            dcc.Store(id="chat-pending"),
            dcc.Store(id="doc-store", storage_type="session"),  # same key as the Reading Studio, read-only here
            html.Div(id="chat-scroll-sink", hidden=True),
            html.Section(
                className="studio-head ph-ai-tutor",
                children=html.Div(
                    className="container-wide",
                    children=[
                        html.P("Ask", className="eyebrow"),
                        html.H1("AI Tutor"),
                        html.P(
                            "Ask anything about your reading or your schoolwork. It's free, it answers in seconds, "
                            "and it explains things at your level.",
                            className="lead",
                        ),
                    ],
                ),
            ),
            html.Div(
                className="container-wide tutor-layout",
                children=[
                    html.Div(
                        className="card chat-card",
                        children=[
                            html.Div(id="chat-messages", className="chat-messages", role="log", **{"aria-live": "polite"}),
                            html.Div(
                                id="chat-typing",
                                className="chat-typing",
                                hidden=True,
                                children=[html.Span("AI Tutor is thinking"), html.Span(className="typing-dots", children=[html.I(), html.I(), html.I()])],
                            ),
                            html.Div(
                                className="chat-input-row",
                                children=[
                                    html.Label("Your question", htmlFor="chat-input", className="sr-only"),
                                    dcc.Textarea(
                                        id="chat-input",
                                        className="chat-input",
                                        placeholder="Type your question… (Enter to send, Shift+Enter for a new line)",
                                        maxLength=ai.MAX_CHAT_MESSAGE,
                                    ),
                                    html.Button("Send", id="chat-send", className="btn btn-primary", n_clicks=0),
                                ],
                            ),
                            html.P(
                                "The AI Tutor can make mistakes. Check important facts with your reading, a teacher, or a parent. "
                                "Please don't share personal information like your address or phone number.",
                                className="ai-disclaimer chat-disclaimer",
                            ),
                        ],
                    ),
                    html.Aside(
                        className="help-panel tutor-side",
                        children=[
                            html.Div(
                                className="help-block",
                                children=[
                                    html.H3("Who is reading?"),
                                    dcc.RadioItems(
                                        id="tutor-level",
                                        options=LEVEL_OPTIONS,
                                        value="13-17",
                                        persistence=True,
                                        persistence_type="local",
                                        className="choice-row compact",
                                        inputClassName="choice-input",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="help-block",
                                children=[
                                    html.H3("Your reading"),
                                    html.Div(id="tutor-reading-info"),
                                    dcc.Checklist(
                                        id="tutor-use-reading",
                                        options=[{"label": "Let the tutor see my current reading", "value": "yes"}],
                                        value=["yes"],
                                        className="choice-row compact",
                                        inputClassName="choice-input",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="help-block",
                                children=[
                                    html.H3("Try asking"),
                                    html.Div(
                                        className="starter-list",
                                        children=[
                                            html.Button(s, id={"type": "chat-starter", "text": s}, className="sample-btn", n_clicks=0)
                                            for s in STARTERS
                                        ],
                                    ),
                                ],
                            ),
                            html.Button("Start a new chat", id="chat-clear", className="btn btn-secondary btn-small", n_clicks=0),
                            html.P(
                                [
                                    "Want a person to work with? ",
                                    dcc.Link("Find a human tutor", href="/tutors", className="text-link"),
                                ],
                                className="muted tutor-human",
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )


# 1) Student sends: add their message right away (in the browser) and flag a reply as pending.
dash.clientside_callback(
    """
    function (sendClicks, starterClicks, clearClicks, text, history) {
        const trig = dash_clientside.callback_context.triggered_id;
        const nu = dash_clientside.no_update;
        if (!trig) { return [nu, nu, nu]; }
        if (trig === "chat-clear") { return [[], "", nu]; }
        let msg = (typeof trig === "object" && trig.type === "chat-starter") ? trig.text : (text || "");
        msg = msg.trim();
        if (!msg) { return [nu, nu, nu]; }
        history = (history || []).slice();
        const typing = document.getElementById("chat-typing");
        if (typing && !typing.hidden) { return [nu, nu, nu]; }  // a reply is on its way
        history.push({role: "user", content: msg.slice(0, %d)});
        return [history, "", Date.now()];
    }
    """
    % ai.MAX_CHAT_MESSAGE,
    Output("chat-history", "data"),
    Output("chat-input", "value"),
    Output("chat-pending", "data"),
    Input("chat-send", "n_clicks"),
    Input({"type": "chat-starter", "text": ALL}, "n_clicks"),
    Input("chat-clear", "n_clicks"),
    State("chat-input", "value"),
    State("chat-history", "data"),
    prevent_initial_call=True,
)


# 1b) Coming back to the page with a question that never got its answer (e.g. the student left
#     mid-reply): ask again once, on page load only.
dash.clientside_callback(
    """
    function (history) {
        // Only the first run after this page is drawn counts (the chat box is new on every visit).
        const box = document.getElementById("chat-messages");
        if (!box || box.dataset.resumeChecked) { return dash_clientside.no_update; }
        box.dataset.resumeChecked = "1";
        const last = (history || [])[(history || []).length - 1];
        return (last && last.role === "user") ? Date.now() : dash_clientside.no_update;
    }
    """,
    Output("chat-pending", "data", allow_duplicate=True),
    Input("chat-history", "data"),
    prevent_initial_call="initial_duplicate",
)


# 2) Server: ask the AI Tutor and append its answer.
@callback(
    Output("chat-history", "data", allow_duplicate=True),
    Input("chat-pending", "data"),
    State("chat-history", "data"),
    State("tutor-level", "value"),
    State("tutor-use-reading", "value"),
    State("doc-store", "data"),
    State("a11y-prefs", "data"),
    prevent_initial_call=True,
    running=[
        (Output("chat-typing", "hidden"), False, True),
        (Output("chat-send", "disabled"), True, False),
    ],
)
def answer(pending, history, level, use_reading, doc, prefs):
    history = list(history or [])
    if not pending or not history or history[-1].get("role") != "user":
        return no_update
    if len(history) >= MAX_MESSAGES:
        history.append({"role": "assistant", "content": "This chat is getting long. Press “Start a new chat” to keep going.", "error": True})
        return history
    reading = documents.section_text(doc) if (doc and use_reading and "yes" in use_reading) else None
    user = accounts.current_user()
    profile, usage = "", ""
    if user:
        uid = user["id"]
        profile = preferences.profile_context(preferences.load_profile(uid), progress.recent_comprehension(uid))
        usage = _usage(uid)
        progress.log_tool(uid, "tutor")
    try:
        out = ai.tutor_reply(history, level or "13-17", reading, profile, prefs, usage)
        msg = {"role": "assistant", "content": out.reply}
        if out.suggestions:
            msg["suggestions"] = [s.model_dump() for s in out.suggestions]
            msg["applied"] = {}
        history.append(msg)
    except ai.AIError as exc:
        history.append({"role": "assistant", "content": str(exc), "error": True})
    return history


def _usage(uid: int) -> str:
    """Recent activity the tutor can use when suggesting settings."""
    parts = []
    tools = progress.tool_counts(uid)[:5]
    if tools:
        parts.append("Most-used tools (30 days): " + ", ".join(f"{t['label']} ({t['count']})" for t in tools) + ".")
    hard = progress.hard_reason_counts(uid)[:3]
    if hard:
        parts.append("Often hard in their check-ins: " + ", ".join(f"{h.lower()} ({n})" for h, n in hard) + ".")
    return ("Recent activity: " + " ".join(parts)) if parts else ""


# 2b) Apply (or undo) a setting the tutor suggested. Changing the setting controls saves it like any other choice.
@callback(
    [Output(f"pref-{k}", "value", allow_duplicate=True) for k in PREF_KEYS] + [Output("chat-history", "data", allow_duplicate=True)],
    Input({"type": "sugg-apply", "m": ALL, "k": ALL}, "n_clicks"),
    Input({"type": "sugg-undo", "m": ALL, "k": ALL}, "n_clicks"),
    Input({"type": "sugg-all", "m": ALL}, "n_clicks"),
    State("chat-history", "data"),
    State("a11y-prefs", "data"),
    prevent_initial_call=True,
)
def apply_suggestion(_apply, _undo, _all, history, prefs):
    trig = ctx.triggered_id
    if not trig or not ctx.triggered[0]["value"] or not history:
        return [no_update] * (len(PREF_KEYS) + 1)
    history = [dict(m) for m in history]
    i = trig["m"]
    if not (0 <= i < len(history)) or not history[i].get("suggestions"):
        return [no_update] * (len(PREF_KEYS) + 1)
    msg = history[i]
    current = preferences.clean(prefs)
    applied = dict(msg.get("applied") or {})
    changes = {}
    if trig["type"] == "sugg-undo":
        key = trig["k"]
        if key in applied:
            changes[key] = applied.pop(key)
    else:
        keys = [trig["k"]] if trig["type"] == "sugg-apply" else [s["setting"] for s in msg["suggestions"]]
        for s in msg["suggestions"]:
            if s["setting"] in keys and s["setting"] not in applied and s["value"] in preferences.ALLOWED.get(s["setting"], ()):
                applied[s["setting"]] = current[s["setting"]]  # remember the old value for Undo
                changes[s["setting"]] = s["value"]
    msg["applied"] = applied
    return [changes.get(k, no_update) for k in PREF_KEYS] + [history]


# 3) Draw the conversation.
@callback(Output("chat-messages", "children"), Input("chat-history", "data"))
def render(history):
    if not history:
        return html.Div(
            className="chat-empty",
            children=[
                html.Div("?", className="feature-icon", **{"aria-hidden": "true"}),
                html.H2("Hi! What would you like help with?"),
                html.P("Ask a question, or tap one of the ideas on the side to get started."),
            ],
        )
    bubbles = []
    for i, m in enumerate(history):
        if m["role"] == "user":
            bubbles.append(html.Div(html.P(m["content"]), className="bubble bubble-user"))
        elif m.get("error"):
            bubbles.append(html.Div(className="notice-error bubble-error", role="alert", children=["! ", m["content"]]))
        else:
            bubbles.append(
                html.Div(
                    className="bubble bubble-tutor ai-panel",
                    children=[
                        html.Div(
                            className="ai-answer-head",
                            children=[
                                html.P("AI Tutor", className="ai-label"),
                                html.Button("🔊 Listen", className="tool-btn speak-btn", type="button", **{"data-say": m["content"].replace("*", "")}),
                            ],
                        ),
                        dcc.Markdown(m["content"], className="bubble-md"),
                        _suggestion_card(i, m) if m.get("suggestions") else None,
                    ],
                )
            )
    return bubbles


def _suggestion_card(i: int, m: dict) -> html.Div:
    """Setting changes the tutor suggested, each with Apply / Undo."""
    applied = m.get("applied") or {}
    rows = []
    for s in m["suggestions"]:
        key = s["setting"]
        if key not in preferences.SETTINGS:
            continue
        label = preferences.SETTINGS[key][0]
        new = preferences.label_of(key, s["value"])
        if key in applied:
            action = html.Span(
                [
                    html.Span("✓ Applied", className="sugg-done"),
                    html.Button("Undo", id={"type": "sugg-undo", "m": i, "k": key}, className="link-btn", n_clicks=0,
                                title=f"Go back to {preferences.label_of(key, applied[key])}"),
                ]
            )
        else:
            action = html.Button("Apply", id={"type": "sugg-apply", "m": i, "k": key}, className="btn btn-primary btn-small", n_clicks=0)
        rows.append(
            html.Li(
                className="sugg-row",
                children=[
                    html.Div([html.Strong(f"{label}: {new}"), html.Span(s["reason"], className="sugg-reason")], className="sugg-text"),
                    action,
                ],
            )
        )
    pending = [s for s in m["suggestions"] if s["setting"] not in applied]
    return html.Div(
        className="sugg-card",
        children=[
            html.P("Settings to try", className="ai-label"),
            html.Ul(rows, className="sugg-list"),
            html.Button("Apply all", id={"type": "sugg-all", "m": i}, className="btn btn-secondary btn-small", n_clicks=0)
            if len(pending) > 1 else None,
            html.P("You can change these any time in Reading settings (Aa).", className="muted small"),
        ],
    )


@callback(Output("tutor-reading-info", "children"), Input("doc-store", "data"))
def reading_info(doc):
    if not doc:
        return html.P(
            ["No reading open. ", dcc.Link("Open one in the Reading Studio", href="/reading-assistant", className="text-link"), " to ask about it."],
            className="muted",
        )
    return html.P([html.Strong(doc.get("title", "Your reading")), html.Span(" is open in the Reading Studio.", className="muted")])


# Keep the newest message in view, and make Enter send.
dash.clientside_callback(
    """
    function (children) {
        const box = document.getElementById("chat-messages");
        if (box) { setTimeout(() => { box.scrollTop = box.scrollHeight; }, 30); }
        const input = document.getElementById("chat-input");
        if (input && !input.dataset.enterHooked) {
            input.dataset.enterHooked = "1";
            input.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
                    e.preventDefault();
                    const send = document.getElementById("chat-send");
                    if (send && !send.disabled) { send.click(); }
                }
            });
        }
        return "";
    }
    """,
    Output("chat-scroll-sink", "children"),
    Input("chat-messages", "children"),
)
