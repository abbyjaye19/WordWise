"""Reading settings panel: text size, spacing, font, and background.

Choices are saved in the browser (dcc.Store, local storage) so they carry
across visits. Later, signed-in users can sync them to their account.
"""

from __future__ import annotations

from dash import dcc, html

DEFAULT_PREFS = {"size": "m", "spacing": "normal", "font": "atkinson", "theme": "cream"}

OPTIONS = {
    "size": [
        {"label": "Small", "value": "s"},
        {"label": "Medium", "value": "m"},
        {"label": "Large", "value": "l"},
        {"label": "Extra large", "value": "xl"},
    ],
    "spacing": [
        {"label": "Normal", "value": "normal"},
        {"label": "Wide", "value": "wide"},
        {"label": "Extra wide", "value": "xwide"},
    ],
    "font": [
        {"label": "Atkinson Hyperlegible", "value": "atkinson"},
        {"label": "Lexend", "value": "lexend"},
        {"label": "Verdana", "value": "verdana"},
    ],
    "theme": [
        {"label": "Cream", "value": "cream"},
        {"label": "Soft blue", "value": "blue"},
        {"label": "Dark navy", "value": "dark"},
    ],
}

LABELS = {"size": "Text size", "spacing": "Line and letter spacing", "font": "Font", "theme": "Background"}


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
                    html.P("Pick what feels easiest to read. We save your choices on this device.", className="settings-intro"),
                    *[_group(k) for k in OPTIONS],
                    html.Button("Reset to default", id="a11y-reset", className="btn btn-secondary", n_clicks=0),
                ],
            ),
        ]
    )
