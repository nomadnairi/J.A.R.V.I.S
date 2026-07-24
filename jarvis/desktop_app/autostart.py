"""
Cross-platform "start with the system" helper.

Best-effort and fully reversible — it only writes a small launcher file in the
OS autostart location and removes it again. No registry hacks, no admin rights.

* Windows: a ``.cmd`` in the Startup folder.
* Linux:   a ``.desktop`` in ``~/.config/autostart``.
* macOS:   a LaunchAgent ``.plist`` in ``~/Library/LaunchAgents``.

The GUI passes the command to run (usually the packaged exe path); tests pass a
temporary directory so nothing touches the real machine.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_ID = "jarvis-desktop"


def _entry_path(platform: str, base: Path | None) -> Path:
    home = Path.home()
    if platform == "win32":
        directory = base or (home / "AppData/Roaming/Microsoft/Windows/"
                            "Start Menu/Programs/Startup")
        return directory / f"{APP_ID}.cmd"
    if platform == "darwin":
        directory = base or (home / "Library/LaunchAgents")
        return directory / f"com.{APP_ID}.plist"
    directory = base or (home / ".config/autostart")
    return directory / f"{APP_ID}.desktop"


def _entry_body(platform: str, command: str) -> str:
    if platform == "win32":
        return f'@echo off\r\nstart "" {command}\r\n'
    if platform == "darwin":
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict>\n'
            f'  <key>Label</key><string>com.{APP_ID}</string>\n'
            '  <key>ProgramArguments</key><array>\n'
            f'    <string>{command}</string>\n'
            '  </array>\n'
            '  <key>RunAtLoad</key><true/>\n'
            '</dict></plist>\n'
        )
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=KER\n"
        f"Exec={command}\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def is_enabled(*, platform: str | None = None, base: Path | None = None) -> bool:
    return _entry_path(platform or sys.platform, base).exists()


def enable(command: str, *, platform: str | None = None,
        base: Path | None = None) -> Path:
    """Install the autostart entry; returns the file written."""
    platform = platform or sys.platform
    path = _entry_path(platform, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_entry_body(platform, command), encoding="utf-8")
    return path


def disable(*, platform: str | None = None, base: Path | None = None) -> None:
    """Remove the autostart entry if present."""
    _entry_path(platform or sys.platform, base).unlink(missing_ok=True)


def set_enabled(enabled: bool, command: str, *, platform: str | None = None,
                base: Path | None = None) -> None:
    if enabled:
        enable(command, platform=platform, base=base)
    else:
        disable(platform=platform, base=base)
