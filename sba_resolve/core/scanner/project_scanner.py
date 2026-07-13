\
"""
SBA AI Studio
Project Scanner
Version 4.1.0
CORE-006

Uses the canonical MediaFile model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from sba_resolve.core.models.media_file import MediaFile

SUPPORTED_EXTENSIONS={
    ".mp4",".mov",".mxf",".avi",
    ".mp3",".wav",".m4a",".aac",".flac",
    ".jpg",".jpeg",".png",".dng",".tif",".tiff",".braw"
}

SKIP_FOLDERS={
    "__pycache__",".git",".idea",".vs",
    "CacheClip","Proxy","Optimized Media"
}


class ProjectScanner:

    def __init__(self, root_folder: str|Path):
        self.root=Path(root_folder)

    def scan(self, progress:Callable[[Path],None]|None=None)->list[MediaFile]:

        if not self.root.exists():
            raise FileNotFoundError(self.root)

        media:list[MediaFile]=[]

        for path in self.root.rglob("*"):

            if not path.is_file():
                continue

            if any(part in SKIP_FOLDERS for part in path.parts):
                continue

            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            if progress:
                progress(path)

            stat=path.stat()

            media.append(
                MediaFile(
                    filename=path.name,
                    full_path=path,
                    relative_path=path.relative_to(self.root),
                    extension=path.suffix.lower(),
                    size=stat.st_size,
                )
            )

        media.sort(key=lambda m: str(m.relative_path).lower())
        return media
