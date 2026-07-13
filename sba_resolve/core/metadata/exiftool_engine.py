\
"""
ExifTool Engine v4.1
Auto-detect bundled ExifTool.
"""
from __future__ import annotations
import json, shutil, subprocess
from pathlib import Path

class ExifToolEngine:

    def __init__(self, exiftool_path:str|None=None):
        project_root=Path(__file__).resolve().parents[3]
        bundled=project_root/"tools"/"exiftool"/"exiftool.exe"

        candidates=[
            Path(exiftool_path) if exiftool_path else None,
            bundled,
            Path(shutil.which("exiftool")) if shutil.which("exiftool") else None,
        ]

        self.exiftool=None
        for c in candidates:
            if c and c.exists():
                self.exiftool=str(c)
                break

        if self.exiftool is None:
            raise FileNotFoundError(
                f"ExifTool not found.\nExpected: {bundled}\n"
                "or provide exiftool_path."
            )

    def _run(self,args):
        r=subprocess.run(
            [self.exiftool,*args],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(r.stdout)

    def read(self,files):
        if not files:
            return []
        return self._run(["-j","-n",*map(str,files)])

    def read_folder(self,folder):
        return self._run(["-j","-r",str(folder)])
