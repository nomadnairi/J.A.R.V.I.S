# PyInstaller spec for the J.A.R.V.I.S. desktop app (PyInstaller >= 6).
#
# Local build (produces dist/JARVIS[.exe] for the OS/arch you run it on):
#   pip install ".[gui]" pyinstaller
#   pyinstaller deploy/desktop/jarvis-desktop.spec
#
# CI builds set JARVIS_BUILD_NAME (e.g. JARVIS-windows-amd64) so artifacts
# for every platform/arch can live side by side. PyInstaller cannot
# cross-compile — each target is built on a matching runner
# (.github/workflows/desktop-build.yml).
#
# The one-file binary bundles Python, Qt (PySide6) and the whole engine —
# expect roughly 100-180 MB. User settings live outside the binary
# (%APPDATA%\JARVIS or ~/.config/jarvis), so it stays portable.

import os
from pathlib import Path

name = os.environ.get("JARVIS_BUILD_NAME", "JARVIS")

a = Analysis(
    ["../../jarvis/desktop_app/__main__.py"],
    pathex=[str(Path(SPECPATH).resolve().parents[1])],
    binaries=[],
    datas=[],
    hiddenimports=[
        "jarvis.desktop_app.app",
        "jarvis.desktop_app.engine_thread",
        "jarvis.integrations.telegram_channel",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tests", "tkinter"],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name=name,
    console=False,
    icon=None,
    upx=False,
)
