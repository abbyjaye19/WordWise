"""Sign in / create an account."""

import dash
from dash import Input, Output, State, callback, dcc, html, no_update

from components.layout import page_header
from services import accounts

dash.register_page(__name__, path="/account", name="Account", order=6)


def _field(label: str, id_: str, type_: str = "text", autocomplete: str = "off") -> html.Div:
    return html.Div(
        className="field",
        children=[
            html.Label(label, htmlFor=id_),
            dcc.Input(id=id_, type=type_, className="text-input", autoComplete=autocomplete, debounce=False),
        ],
    )


def layout(**_query):
    user = accounts.current_user()
    if user:
        return html.Div(
            [
                page_header("Your account", "You're signed in. Your readings and folders are saved to your account.", eyebrow="Account", theme="account"),
                html.Section(
                    className="section container narrow",
                    children=html.Div(
                        className="card",
                        children=[
                            html.Dl(
                                [html.Dt("Username"), html.Dd(user["username"]), html.Dt("Email"), html.Dd(user["email"])],
                                className="pref-list",
                            ),
                            html.Div(
                                className="btn-row",
                                children=[
                                    dcc.Link("Go to my library", href="/dashboard", className="btn btn-primary"),
                                    html.A("Sign out", href="/logout", className="btn btn-secondary"),
                                ],
                            ),
                        ],
                    ),
                ),
            ]
        )

    return html.Div(
        [
            dcc.Location(id="auth-redirect", refresh=True),
            page_header(
                "Sign in or create an account",
                "An account keeps your readings, highlights, and folders safe, so they are still here next time.",
                eyebrow="Account",
                theme="account",
            ),
            html.Section(
                className="section container auth-grid",
                children=[
                    html.Div(
                        className="card",
                        children=[
                            html.H2("Sign in"),
                            _field("Username or email", "signin-id", autocomplete="username"),
                            _field("Password", "signin-password", "password", autocomplete="current-password"),
                            html.Button("Sign in", id="signin-btn", className="btn btn-primary", n_clicks=0),
                            html.Div(id="signin-msg", role="alert"),
                        ],
                    ),
                    html.Div(
                        className="card",
                        children=[
                            html.H2("Create an account"),
                            _field("Username", "signup-username", autocomplete="username"),
                            _field("Email", "signup-email", "email", autocomplete="email"),
                            _field("Password (at least 8 characters)", "signup-password", "password", autocomplete="new-password"),
                            _field("Type your password again", "signup-confirm", "password", autocomplete="new-password"),
                            html.Button("Create account", id="signup-btn", className="btn btn-primary", n_clicks=0),
                            html.Div(id="signup-msg", role="alert"),
                            html.P(
                                "Under 13? Please ask a parent or guardian to create the account with you.",
                                className="muted",
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )


def _error(text: str) -> html.P:
    return html.P([html.Span("! ", **{"aria-hidden": "true"}), text], className="status-error form-msg")


@callback(
    Output("auth-redirect", "href", allow_duplicate=True),
    Output("signin-msg", "children"),
    Input("signin-btn", "n_clicks"),
    Input("signin-password", "n_submit"),
    State("signin-id", "value"),
    State("signin-password", "value"),
    prevent_initial_call=True,
)
def do_sign_in(_n, _s, identifier, password):
    try:
        accounts.sign_in(identifier, password)
    except accounts.AccountError as exc:
        return no_update, _error(str(exc))
    return "/dashboard", None


@callback(
    Output("auth-redirect", "href", allow_duplicate=True),
    Output("signup-msg", "children"),
    Input("signup-btn", "n_clicks"),
    Input("signup-confirm", "n_submit"),
    State("signup-username", "value"),
    State("signup-email", "value"),
    State("signup-password", "value"),
    State("signup-confirm", "value"),
    prevent_initial_call=True,
)
def do_sign_up(_n, _s, username, email, password, confirm):
    try:
        accounts.create_account(username, email, password, confirm)
    except accounts.AccountError as exc:
        return no_update, _error(str(exc))
    return "/dashboard", None
