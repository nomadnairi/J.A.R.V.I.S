# PyInstaller spec for the J.A.R.V.I.S. desktop app.
#
# Build on Windows (produces dist/JARVIS.exe):
#   pip install ".[gui]" pyinstaller
#   pyinstaller deploy/desktop/jarvis-desktop.spec
#
# The one-file exe bundles the engine and GUI; user settings live in
# %APPDATA%\JARVIS\desktop.json, so the exe itself stays portable.

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["../../jarvis/desktop_app/__main__.py"],
    pathex=[str(Path(SPECPATH).resolve().parents[1])],
    binaries=[],
    datas=[],
    hiddenimports=[
        "jarvis.desktop_app.app",
        "jarvis.integrations.telegram_channel",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tests"],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="JARVIS",
    console=False,
    icon=None,
    upx=False,
)
