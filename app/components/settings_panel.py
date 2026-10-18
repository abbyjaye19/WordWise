"""Reading settings panel: text, page, and read-aloud preferences.

Choices are saved in the browser (dcc.Store, local storage) so they apply on every page and
carry across visits. Signed-in students also have them saved to their account, so they follow
them to another device. The list of settings lives in services/preferences.py.
"""

from __future__ import annotations

from dash import dcc, html

from services.preferences import DEFAULTS, SETTINGS

DEFAULT_PREFS = DEFAULTS
OPTIONS = {k: [{"label": lab, "value": val} for val, lab in v[1]] for k, v in SETTINGS.items()}
LABELS = {k: v[0] for k, v in SETTINGS.items()}

GROUPS = [
    ("Text", ["size", "font", "spacing"]),
    ("Page", ["theme", "contrast", "linewidth"]),
    ("Read aloud", ["rate", "readalong"]),
]


def _group(key: str) -> html.Fieldset:
    return html.Fieldset(
        className="setting-group",
        children=[
            html.Legend(LABELS[key]),
            dcc.RadioItems(
                id=f"pref-{key}",
                options=OPTIONS[key],
                value=DEFAULT_PREFS[key],
                className="choice-row",
                inputClassName="choice-input",
                labelClassName="choice-label",
            ),
        ],
    )


def settings_panel() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="a11y-prefs", storage_type="local"),
            html.Div(id="a11y-sink", hidden=True),
            html.Aside(
                id="a11y-panel",
                className="settings-panel",
                hidden=True,
                role="dialog",
                **{"aria-label": "Reading settings"},
                children=[
                    html.Div(
                        className="settings-head",
                        children=[
                            html.H2("Reading settings"),
                            html.Button("Close", id="a11y-close", className="btn btn-secondary btn-small", n_clicks=0),
                        ],
                    ),
                    html.P(
                        "Pick what feels easiest to read. Your choices apply on every page. "
                        "If you are signed in, they are saved to your account too.",
                        className="settings-intro",
                    ),
                    html.P(
                        ["Not sure what works best? ", dcc.Link("Ask the AI Tutor", href="/ai-tutor"), " to help you try settings."],
                        className="settings-intro settings-tip",
                    ),
                    *[
                        html.Section(className="settings-section", children=[html.H3(title), *[_group(k) for k in keys]])
                        for title, keys in GROUPS
                    ],
                    dcc.ConfirmDialogProvider(
                        html.Button("Clear all preferences", id="a11y-reset-btn", className="btn btn-secondary", n_clicks=0),
                        id="a11y-reset",
                        message="Clear all your reading preferences and go back to the default settings?",
                    ),
                    html.P(id="a11y-status", className="settings-status", role="status"),
                ],
            ),
        ]
    )
