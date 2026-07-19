"""
SBA AI Studio Bootstrap
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# PACKAGING (2026-07-19): when running as a PyInstaller ONEFILE
# build, QtWebEngine (used by the Map panel) needs to be told
# explicitly where its helper process and resource files ended
# up after extraction (sys._MEIPASS), or it can fail to start -
# a known fragile point in PyInstaller onefile + QtWebEngine
# combinations. This must happen BEFORE QApplication/QWebEngineView
# are created. Running from source (not frozen) is unaffected -
# these environment variables are only set when frozen.
if getattr(sys, "frozen", False):
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        webengine_process = (
            Path(meipass) / "PySide6" / "QtWebEngineProcess.exe"
        )
        if webengine_process.exists():
            os.environ.setdefault(
                "QTWEBENGINEPROCESS_PATH", str(webengine_process)
            )
        os.environ.setdefault(
            "QTWEBENGINE_RESOURCES_PATH",
            str(Path(meipass) / "PySide6" / "resources"),
        )

from PySide6.QtWidgets import QApplication

from ui.windows.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())