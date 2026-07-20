"""
Visual theme for the desktop app — a sleek dark "arc-reactor" look.

Everything here is pure strings/helpers (no Qt import), so it stays testable
and the palette can be reused for chat-bubble HTML. Colours are tuned for a
deep, slightly blue-black background with a cyan accent, generous spacing and
rounded panels.
"""

from __future__ import annotations

# -- palette ------------------------------------------------------------------

BG = "#0b0f14"            # window background (near-black, cool)
BG_PANEL = "#121821"      # cards / panels
BG_ELEVATED = "#1a2230"   # inputs, hovered rows
BORDER = "#243043"        # hairline borders
TEXT = "#e6edf3"          # primary text
TEXT_MUTED = "#8b98a9"    # secondary text
ACCENT = "#22d3ee"        # arc-reactor cyan
ACCENT_DIM = "#0e7490"    # pressed / darker accent
ACCENT_SOFT = "#0b3a44"   # accent-tinted fill
DANGER = "#f87171"
SUCCESS = "#34d399"

# Font stack — no bundled fonts needed; these look clean across OSes.
FONT_STACK = ('"Segoe UI", "SF Pro Display", "Inter", "Helvetica Neue", '
            "system-ui, Arial, sans-serif")
MONO_STACK = '"JetBrains Mono", "Cascadia Code", "SF Mono", Consolas, monospace'


def stylesheet() -> str:
    """Return the global Qt style sheet."""
    return f"""
    * {{
        font-family: {FONT_STACK};
        font-size: 14px;
        color: {TEXT};
        outline: none;
    }}
    QMainWindow, QDialog {{ background: {BG}; }}
    QWidget#Card {{
        background: {BG_PANEL};
        border: 1px solid {BORDER};
        border-radius: 16px;
    }}

    /* Header bar */
    QWidget#Header {{ background: {BG}; border-bottom: 1px solid {BORDER}; }}
    QLabel#Wordmark {{
        font-family: {MONO_STACK};
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 3px;
        color: {TEXT};
    }}
    QLabel#StatusDot {{ color: {SUCCESS}; font-size: 13px; }}
    QLabel#Subtle {{ color: {TEXT_MUTED}; font-size: 13px; }}
    QLabel#Hint {{ color: {TEXT_MUTED}; font-size: 12px; }}
    QLabel#Title {{ font-size: 22px; font-weight: 700; }}

    /* Tabs → pill-style top bar */
    QTabWidget::pane {{ border: none; background: {BG}; }}
    QTabBar {{ qproperty-drawBase: 0; }}
    QTabBar::tab {{
        background: transparent;
        color: {TEXT_MUTED};
        padding: 9px 18px;
        margin: 6px 4px;
        border-radius: 10px;
        font-weight: 600;
    }}
    QTabBar::tab:hover {{ color: {TEXT}; background: {BG_ELEVATED}; }}
    QTabBar::tab:selected {{ color: {BG}; background: {ACCENT}; }}

    /* Inputs */
    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {{
        background: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 9px 12px;
        selection-background-color: {ACCENT_DIM};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border: 1px solid {ACCENT};
    }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background: {BG_PANEL};
        border: 1px solid {BORDER};
        selection-background-color: {ACCENT_SOFT};
        border-radius: 8px;
    }}

    /* Buttons */
    QPushButton {{
        background: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 9px 18px;
        font-weight: 600;
    }}
    QPushButton:hover {{ border: 1px solid {ACCENT}; color: {ACCENT}; }}
    QPushButton:pressed {{ background: {BG_PANEL}; }}
    QPushButton#Primary {{
        background: {ACCENT}; color: {BG}; border: none;
    }}
    QPushButton#Primary:hover {{ background: #38dbf0; color: {BG}; }}
    QPushButton#Primary:pressed {{ background: {ACCENT_DIM}; }}
    QPushButton#Danger:hover {{ border: 1px solid {DANGER}; color: {DANGER}; }}
    QPushButton#Record {{
        background: {ACCENT_SOFT}; border: 1px solid {ACCENT};
        color: {ACCENT}; font-size: 16px; border-radius: 32px;
    }}

    /* Check / radio */
    QCheckBox, QRadioButton {{ spacing: 8px; padding: 4px 0; }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px; height: 18px;
        border: 1px solid {BORDER}; border-radius: 5px;
        background: {BG_ELEVATED};
    }}
    QRadioButton::indicator {{ border-radius: 9px; }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {ACCENT}; border: 1px solid {ACCENT};
    }}

    /* Scrollbars */
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
    QScrollBar::handle:vertical {{
        background: {BORDER}; border-radius: 5px; min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
    """


# -- chat rendering -----------------------------------------------------------

def bubble_html(role: str, text: str) -> str:
    """Return an HTML fragment for one chat message bubble."""
    safe = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;").replace("\n", "<br>")
    if role == "user":
        return (
            f'<div style="margin:10px 0; text-align:right;">'
            f'<span style="display:inline-block; max-width:78%; text-align:left;'
            f' background:{ACCENT_SOFT}; color:{TEXT}; border:1px solid {ACCENT_DIM};'
            f' padding:9px 13px; border-radius:14px 14px 4px 14px;">{safe}</span>'
            f'</div>'
        )
    if role == "system":
        return (f'<div style="margin:8px 0; text-align:center; color:{TEXT_MUTED};'
                f' font-size:12px;">{safe}</div>')
    return (
        f'<div style="margin:10px 0; text-align:left;">'
        f'<span style="display:inline-block; max-width:78%;'
        f' background:{BG_PANEL}; color:{TEXT}; border:1px solid {BORDER};'
        f' padding:9px 13px; border-radius:14px 14px 14px 4px;">{safe}</span>'
        f'</div>'
    )
