"""
ExifTool Engine v4.2
Auto-detect bundled ExifTool.

v4.2 (2026-07-19, PACKAGING): fixed a real bug for the
PyInstaller-frozen build - the old project_root lookup
(Path(__file__).resolve().parents[3]) resolves inside a
temporary extraction folder once bundled into an .exe, not the
real install location, so the bundled ExifTool would never be
found once packaged. When frozen (sys.frozen is True), the
bundled path now resolves relative to the directory containing
the actual .exe instead. Running from source is unaffected -
same parents[3]-based path as before. Priority order (explicit
path -> bundled -> system PATH) is unchanged.
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
    When running as a PyInstaller-frozen .exe, this is next to
    the real executable. When running from source, this is the
    project root's tools/exiftool/ folder, exactly as before
    (three levels up from this file's real location:
    sba_resolve/core/metadata/).
    """

    if getattr(sys, "frozen", False):
        project_root = Path(sys.executable).resolve().parent
    else:
        project_root = Path(__file__).resolve().parents[3]

    return project_root / "tools" / "exiftool" / "exiftool.exe"


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