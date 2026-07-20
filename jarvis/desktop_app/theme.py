"""
Visual themes for the desktop app.

Several named palettes share one layout; :func:`stylesheet` builds the Qt style
sheet for a chosen theme and :func:`bubble_html` renders chat bubbles in the
matching colours. Everything here is pure strings (no Qt import), so it stays
testable and reusable.
"""

from __future__ import annotations

# Font stacks — no bundled fonts needed; these look clean across OSes.
FONT_STACK = ('"Segoe UI", "SF Pro Display", "Inter", "Helvetica Neue", '
            "system-ui, Arial, sans-serif")
MONO_STACK = '"JetBrains Mono", "Cascadia Code", "SF Mono", Consolas, monospace'

# -- palettes -----------------------------------------------------------------
# Each theme defines the same keys so the stylesheet template stays shared.

THEMES: dict[str, dict[str, str]] = {
    "arc": {
        "label": "Arc Reactor (cyan)",
        "bg": "#0b0f14", "panel": "#121821", "elevated": "#1a2230",
        "border": "#243043", "text": "#e6edf3", "muted": "#8b98a9",
        "accent": "#22d3ee", "accent_dim": "#0e7490", "accent_soft": "#0b3a44",
        "accent_hi": "#38dbf0", "danger": "#f87171", "success": "#34d399",
        "on_accent": "#0b0f14",
    },
    "mark42": {
        "label": "Mark 42 (red / gold)",
        "bg": "#120a0a", "panel": "#1c1211", "elevated": "#271817",
        "border": "#3d2422", "text": "#f4e9e6", "muted": "#b39a94",
        "accent": "#e63946", "accent_dim": "#8f1d26", "accent_soft": "#3a1416",
        "accent_hi": "#ff5964", "danger": "#f87171", "success": "#e2b13c",
        "on_accent": "#120a0a",
    },
    "nebula": {
        "label": "Nebula (violet)",
        "bg": "#0d0b1a", "panel": "#161329", "elevated": "#201b3a",
        "border": "#2f2850", "text": "#eae7f7", "muted": "#9a93bd",
        "accent": "#a855f7", "accent_dim": "#6d28d9", "accent_soft": "#241a44",
        "accent_hi": "#c084fc", "danger": "#f87171", "success": "#34d399",
        "on_accent": "#0d0b1a",
    },
    "emerald": {
        "label": "Emerald (green)",
        "bg": "#08120e", "panel": "#101d17", "elevated": "#16281f",
        "border": "#22392d", "text": "#e4f2ea", "muted": "#8bab9a",
        "accent": "#10b981", "accent_dim": "#0a7d58", "accent_soft": "#0c2c22",
        "accent_hi": "#34d399", "danger": "#f87171", "success": "#34d399",
        "on_accent": "#08120e",
    },
    "light": {
        "label": "Daylight (light)",
        "bg": "#f4f6fb", "panel": "#ffffff", "elevated": "#eef1f7",
        "border": "#d3dae6", "text": "#1a2230", "muted": "#5b6675",
        "accent": "#0ea5e9", "accent_dim": "#0369a1", "accent_soft": "#dbeefb",
        "accent_hi": "#38bdf8", "danger": "#dc2626", "success": "#059669",
        "on_accent": "#ffffff",
    },
}

DEFAULT_THEME = "arc"


def theme_names() -> list[tuple[str, str]]:
    """(key, human label) pairs for the theme picker."""
    return [(key, val["label"]) for key, val in THEMES.items()]


def _palette(name: str) -> dict[str, str]:
    return THEMES.get(name) or THEMES[DEFAULT_THEME]


def stylesheet(theme: str = DEFAULT_THEME) -> str:
    """Return the global Qt style sheet for *theme*."""
    p = _palette(theme)
    return f"""
    * {{
        font-family: {FONT_STACK};
        font-size: 14px;
        color: {p['text']};
        outline: none;
    }}
    QMainWindow, QDialog {{ background: {p['bg']}; }}
    QWidget#Card {{
        background: {p['panel']};
        border: 1px solid {p['border']};
        border-radius: 16px;
    }}
    QWidget#Header {{ background: {p['bg']}; border-bottom: 1px solid {p['border']}; }}
    QLabel#Wordmark {{
        font-family: {MONO_STACK};
        font-size: 20px; font-weight: 700; letter-spacing: 3px;
        color: {p['text']};
    }}
    QLabel#StatusDot {{ color: {p['success']}; font-size: 13px; }}
    QLabel#Subtle {{ color: {p['muted']}; font-size: 13px; }}
    QLabel#Hint {{ color: {p['muted']}; font-size: 12px; }}
    QLabel#Title {{ font-size: 22px; font-weight: 700; }}

    QTabWidget::pane {{ border: none; background: {p['bg']}; }}
    QTabBar {{ qproperty-drawBase: 0; }}
    QTabBar::tab {{
        background: transparent; color: {p['muted']};
        padding: 9px 18px; margin: 6px 4px; border-radius: 10px; font-weight: 600;
    }}
    QTabBar::tab:hover {{ color: {p['text']}; background: {p['elevated']}; }}
    QTabBar::tab:selected {{ color: {p['on_accent']}; background: {p['accent']}; }}

    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {{
        background: {p['elevated']}; border: 1px solid {p['border']};
        border-radius: 10px; padding: 9px 12px;
        selection-background-color: {p['accent_dim']};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border: 1px solid {p['accent']};
    }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background: {p['panel']}; border: 1px solid {p['border']};
        selection-background-color: {p['accent_soft']}; border-radius: 8px;
    }}

    QPushButton {{
        background: {p['elevated']}; border: 1px solid {p['border']};
        border-radius: 10px; padding: 9px 18px; font-weight: 600;
    }}
    QPushButton:hover {{ border: 1px solid {p['accent']}; color: {p['accent']}; }}
    QPushButton:pressed {{ background: {p['panel']}; }}
    QPushButton#Primary {{ background: {p['accent']}; color: {p['on_accent']}; border: none; }}
    QPushButton#Primary:hover {{ background: {p['accent_hi']}; color: {p['on_accent']}; }}
    QPushButton#Primary:pressed {{ background: {p['accent_dim']}; }}
    QPushButton#Danger:hover {{ border: 1px solid {p['danger']}; color: {p['danger']}; }}
    QPushButton#Record {{
        background: {p['accent_soft']}; border: 1px solid {p['accent']};
        color: {p['accent']}; font-size: 16px; border-radius: 32px;
    }}

    QCheckBox, QRadioButton {{ spacing: 8px; padding: 4px 0; }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px; height: 18px; border: 1px solid {p['border']};
        border-radius: 5px; background: {p['elevated']};
    }}
    QRadioButton::indicator {{ border-radius: 9px; }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {p['accent']}; border: 1px solid {p['accent']};
    }}

    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
    QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {p['muted']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
    """


def bubble_html(role: str, text: str, theme: str = DEFAULT_THEME) -> str:
    """Return an HTML fragment for one chat message bubble in *theme*."""
    p = _palette(theme)
    safe = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;").replace("\n", "<br>")
    if role == "user":
        return (
            f'<div style="margin:10px 0; text-align:right;">'
            f'<span style="display:inline-block; max-width:78%; text-align:left;'
            f" background:{p['accent_soft']}; color:{p['text']};"
            f" border:1px solid {p['accent_dim']};"
            f' padding:9px 13px; border-radius:14px 14px 4px 14px;">{safe}</span>'
            f'</div>'
        )
    if role == "system":
        return (f'<div style="margin:8px 0; text-align:center; color:{p["muted"]};'
                f' font-size:12px;">{safe}</div>')
    return (
        f'<div style="margin:10px 0; text-align:left;">'
        f'<span style="display:inline-block; max-width:78%;'
        f" background:{p['panel']}; color:{p['text']}; border:1px solid {p['border']};"
        f' padding:9px 13px; border-radius:14px 14px 14px 4px;">{safe}</span>'
        f'</div>'
    )
