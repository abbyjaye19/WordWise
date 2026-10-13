"""AI Tutor — a free, fast chat tutor at the student's level, optionally about their current reading."""

import dash
from dash import ALL, Input, Output, State, callback, dcc, html, no_update

from services import ai, documents

dash.register_page(__name__, path="/ai-tutor", name="AI Tutor", order=7)

LEVEL_OPTIONS = [{"label": label, "value": value} for value, label in ai.LEVELS.items()]
STARTERS = [
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
                className="studio-head",
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
    prevent_initial_call=True,
    running=[
        (Output("chat-typing", "hidden"), False, True),
        (Output("chat-send", "disabled"), True, False),
    ],
)
def answer(pending, history, level, use_reading, doc):
    history = list(history or [])
    if not pending or not history or history[-1].get("role") != "user":
        return no_update
    if len(history) >= MAX_MESSAGES:
        history.append({"role": "assistant", "content": "This chat is getting long. Press “Start a new chat” to keep going.", "error": True})
        return history
    reading = documents.section_text(doc) if (doc and use_reading and "yes" in use_reading) else None
    try:
        reply = ai.tutor_reply(history, level or "13-17", reading)
        history.append({"role": "assistant", "content": reply})
    except ai.AIError as exc:
        history.append({"role": "assistant", "content": str(exc), "error": True})
    return history


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
    for m in history:
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
                    ],
                )
            )
    return bubbles


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
