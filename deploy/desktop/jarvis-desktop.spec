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
    # Ship the Command Deck web dashboard so the desktop app can render it.
    datas=[
        ("../../jarvis/api/static/dashboard.html", "jarvis/api/static"),
    ],
    hiddenimports=[
        "jarvis.desktop_app.app",
        "jarvis.desktop_app.engine_thread",
        "jarvis.integrations.telegram_channel",
        # The bundled local API (Command Deck) — uvicorn's dynamic imports.
        "uvicorn.loops.auto", "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.off",
        "uvicorn.logging",
    ],
    hookspath=[],
    runtime_hooks=[],
    # Drop modules we never import — smaller binary and lower memory at import
    # time. Heavy optional Qt modules (WebEngine, Quick/QML, 3D, Charts,
    # PDF, …) are not used by the app, only QtWidgets/Gui/Core/Multimedia.
    excludes=[
        "tests", "tkinter", "PyQt5", "PySide2", "matplotlib", "IPython",
        "pytest", "pandas",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel",
        "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQml",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtDesigner", "PySide6.QtTest", "PySide6.QtSql",
        "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtSensors",
        "PySide6.QtSerialPort", "PySide6.QtWebSockets",
    ],
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
