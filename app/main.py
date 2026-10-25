"""WordWise — start the website.

Run from the project folder:  python app/main.py
Then open http://127.0.0.1:8050 in your browser.
"""

from __future__ import annotations

from datetime import timedelta

import dash
from dash import Input, Output, State, ctx, dcc, html
from flask import redirect

from components.layout import NAV_ITEMS, footer, header, nav_link_id
from components.settings_panel import DEFAULT_PREFS, OPTIONS, settings_panel
from config import HOST, PORT, SECRET_KEY
from services import accounts, preferences, progress

FONTS = (
    "https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700"
    "&family=Lexend:wght@400;600&family=Libre+Baskerville:wght@400;700&display=swap"
)

app = dash.Dash(
    __name__,
    use_pages=True,
    title="WordWise — reading support that fits you",
    external_stylesheets=[FONTS],
    suppress_callback_exceptions=True,
)

# Login sessions: signed cookie, not readable by page scripts, kept for 30 days.
server = app.server
server.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)


@server.route("/logout")
def logout():
    accounts.sign_out()
    return redirect("/")

# Apply saved reading settings before first paint (avoids a flash of the default theme).
app.index_string = app.index_string.replace(
    "{%css%}",
    """{%css%}
        <script>
          try {
            const p = JSON.parse(localStorage.getItem("a11y-prefs") || "{}") || {};
            for (const k of %PREF_KEYS%) if (p[k]) document.documentElement.dataset[k] = p[k];
          } catch (e) {}
        </script>""".replace("%PREF_KEYS%", str(list(OPTIONS)).replace("'", '"')),
)

app.layout = html.Div(
    [
        dcc.Location(id="url"),
        html.A("Skip to main content", href="#main", className="skip-link"),
        header(),
        settings_panel(),
        html.Main(dash.page_container, id="main", tabIndex="-1"),
        html.Div(className="bookshelf", **{"aria-hidden": "true"}),  # library shelf above the footer
        footer(),
        dcc.Link(
            [html.Span(className="tutor-fab-dot", **{"aria-hidden": "true"}), "Ask the AI Tutor"],
            href="/ai-tutor",
            id="tutor-fab",
            className="tutor-fab",
        ),
    ]
)

PREF_KEYS = list(OPTIONS)


@app.callback(
    [Output(f"pref-{k}", "value") for k in PREF_KEYS] + [Output("a11y-prefs", "data"), Output("a11y-status", "children")],
    [Input(f"pref-{k}", "value") for k in PREF_KEYS] + [Input("a11y-reset", "submit_n_clicks")],
    State("a11y-prefs", "data"),
)
def sync_prefs(*args):
    """Keep the settings controls, this browser, and the student's account in step."""
    *values, _reset, saved = args
    user = accounts.current_user()
    status = ""
    if ctx.triggered_id == "a11y-reset":
        prefs = dict(DEFAULT_PREFS)
        if user:
            preferences.save(user["id"], None)
        status = "All preferences cleared. You're back to the default settings."
    elif ctx.triggered_id is None:  # first page load: account choices win, then this browser's
        account_prefs = preferences.load(user["id"]) if user else None
        prefs = account_prefs or preferences.clean(saved)
        if user and not account_prefs and saved:
            preferences.save(user["id"], prefs)  # first sign-in on this device: keep what they set up
    else:
        prefs = preferences.clean(dict(zip(PREF_KEYS, values)))
        if user:
            preferences.save(user["id"], prefs)
            progress.log_tool(user["id"], "settings")
    return [prefs[k] for k in PREF_KEYS] + [prefs, status]


# Apply preferences instantly in the browser as data-* attributes on <html>.
app.clientside_callback(
    """
    function (prefs) {
        prefs = prefs || {};
        const root = document.documentElement;
        %PREF_KEYS%.forEach(k => { if (prefs[k]) root.dataset[k] = prefs[k]; });
        return "";
    }
    """.replace("%PREF_KEYS%", str(PREF_KEYS).replace("'", '"')),
    Output("a11y-sink", "children"),
    Input("a11y-prefs", "data"),
)

# "Clear all preferences" also forgets remembered helper choices (like the reader level).
app.clientside_callback(
    """
    function (n) {
        if (!n) { return window.dash_clientside.no_update; }
        try {
            Object.keys(localStorage).filter(k => k.startsWith("_dash_persistence")).forEach(k => localStorage.removeItem(k));
            ["ww-voice", "ww-guide-seen"].forEach(k => localStorage.removeItem(k));  // chosen voice; show the Quick guide again
        } catch (e) {}
        return window.dash_clientside.no_update;
    }
    """,
    Output("a11y-sink", "title"),
    Input("a11y-reset", "submit_n_clicks"),
    prevent_initial_call=True,
)


app.clientside_callback(
    """
    function (openClicks, closeClicks, hidden) {
        const id = dash_clientside.callback_context.triggered_id;
        if (id === "a11y-open") { return !hidden; }
        if (id === "a11y-close") { return true; }
        return hidden;
    }
    """,
    Output("a11y-panel", "hidden"),
    Input("a11y-open", "n_clicks"),
    Input("a11y-close", "n_clicks"),
    State("a11y-panel", "hidden"),
)


@app.callback(
    [Output(nav_link_id(item["href"]), "className") for item in NAV_ITEMS],
    Input("url", "pathname"),
)
def highlight_nav(pathname):
    active = [bool(pathname) and pathname.startswith(item["href"]) for item in NAV_ITEMS]
    return ["nav-link active" if a else "nav-link" for a in active]


@app.callback(Output("tutor-fab", "style"), Input("url", "pathname"))
def hide_fab_on_tutor(pathname):
    return {"display": "none"} if pathname == "/ai-tutor" else {}


@app.callback(Output("account-slot", "children"), Input("url", "pathname"))
def account_slot(_pathname):
    user = accounts.current_user()
    if not user:
        return dcc.Link("Sign in", href="/account", className="btn btn-settings")
    return html.Details(
        className="account-menu",
        children=[
            html.Summary([html.Span("●", className="avatar-dot", **{"aria-hidden": "true"}), user["username"]], className="btn btn-settings"),
            html.Div(
                className="account-pop",
                children=[
                    dcc.Link("My library", href="/dashboard", className="account-link"),
                    dcc.Link("Account", href="/account", className="account-link"),
                    html.A("Sign out", href="/logout", className="account-link"),
                ],
            ),
        ],
    )


if __name__ == "__main__":
    # Debug and the auto-reloader stay off so one edit never spawns extra servers.
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
