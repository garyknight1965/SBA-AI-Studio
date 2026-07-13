"""
============================================================
SBA AI Studio
Library Search
Version : 4.0.0 Alpha
Sprint : ML-005
============================================================
"""

from __future__ import annotations

from sba_resolve.core.models.media_library import MediaLibrary
from sba_resolve.core.models.media_file import MediaFile


class LibrarySearch:

    def __init__(self, library: MediaLibrary) -> None:
        self._library = library

    def filename(self, text: str) -> list[MediaFile]:
        text = text.lower()
        return [m for m in self._library if text in m.filename.lower()]

    def camera(self, text: str) -> list[MediaFile]:
        text = text.lower()
        return [
            m for m in self._library
            if text in m.camera_make.lower()
            or text in m.camera_model.lower()
        ]

    def category(self, text: str) -> list[MediaFile]:
        text = text.lower()
        return [m for m in self._library if text in m.category.lower()]

    def tag(self, text: str) -> list[MediaFile]:
        text = text.lower()
        return [
            m for m in self._library
            if any(text in tag.lower() for tag in m.tags)
        ]

    def extension(self, ext: str) -> list[MediaFile]:
        ext = ext.lower()
        if not ext.startswith("."):
            ext = "." + ext
        return [m for m in self._library if m.extension.lower() == ext]
