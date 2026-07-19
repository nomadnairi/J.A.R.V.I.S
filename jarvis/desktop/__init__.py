"""
Desktop control.

Lets the assistant act on the computer — type text, press keys, move/click the
mouse, take a screenshot, open a URL. Every action requires the
``DESKTOP_CONTROL`` capability (off by default) and is audited. GUI actions use
the optional ``pyautogui`` package and only work on a real desktop session.
"""

from jarvis.desktop.controller import DesktopController

__all__ = ["DesktopController"]
