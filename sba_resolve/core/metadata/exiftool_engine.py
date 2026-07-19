"""
ExifTool Engine v4.3
Auto-detect bundled ExifTool.

v4.2 (2026-07-19, PACKAGING) attempted a sys.frozen-aware fix
using sys.executable's folder - WRONG for a PyInstaller onefile
build: bundled data files extract to a temporary folder
(sys._MEIPASS) fresh on every launch, not next to the real .exe
(that location is reserved for settings.json, which must persist
across runs and stay user-editable - a completely different
requirement from a bundled binary like ExifTool, which doesn't
need to persist).

v4.3 (2026-07-19) fixes this properly: when frozen, resolves the
bundled ExifTool relative to sys._MEIPASS (the real onefile
extraction location) instead. Running from source is unaffected.
Priority order (explicit path -> bundled -> system PATH) is
unchanged.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _bundled_exiftool_path() -> Path:
    """
    Resolves the bundled tools/exiftool/exiftool.exe location.

    When running as a PyInstaller ONEFILE build, bundled data
    files are extracted fresh to a temporary folder on every
    launch, exposed via sys._MEIPASS - this is the correct
    location to look for a bundled binary, NOT next to the real
    .exe (sys.executable), which stays constant across runs and
    is reserved for things that must persist (settings.json).

    When running from source, this is the project root's
    tools/exiftool/ folder, exactly as before (three levels up
    from this file's real location: sba_resolve/core/metadata/).
    """

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / "tools" / "exiftool" / "exiftool.exe"

    return (
        Path(__file__).resolve().parents[3]
        / "tools" / "exiftool" / "exiftool.exe"
    )


class ExifToolEngine:
    def __init__(self, exiftool_path: str | None = None):
        bundled = _bundled_exiftool_path()
        candidates = [
            Path(exiftool_path) if exiftool_path else None,
            bundled,
            Path(shutil.which("exiftool")) if shutil.which("exiftool") else None,
        ]
        self.exiftool = None
        for c in candidates:
            if c and c.exists():
                self.exiftool = str(c)
                break
        if self.exiftool is None:
            raise FileNotFoundError(
                f"ExifTool not found.\nExpected: {bundled}\n"
                "or provide exiftool_path."
            )

    def _run(self, args):
        r = subprocess.run(
            [self.exiftool, *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(r.stdout)

    def read(self, files):
        if not files:
            return []
        return self._run(["-j", "-n", *map(str, files)])

    def read_folder(self, folder):
        return self._run(["-j", "-r", str(folder)])