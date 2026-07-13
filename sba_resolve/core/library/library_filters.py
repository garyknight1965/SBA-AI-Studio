"""
============================================================
SBA AI Studio
Library Filters
Version : 4.0.0 Alpha
Sprint : ML-005
============================================================
"""

from __future__ import annotations

from sba_resolve.core.models.media_library import MediaLibrary
from sba_resolve.core.models.media_file import MediaFile


class LibraryFilters:

    def __init__(self, library: MediaLibrary) -> None:
        self._library = library

    def by_camera(self, camera: str) -> list[MediaFile]:
        camera = camera.lower()
        return [
            m for m in self._library
            if camera in m.camera_make.lower()
            or camera in m.camera_model.lower()
        ]

    def by_category(self, category: str) -> list[MediaFile]:
        category = category.lower()
        return [
            m for m in self._library
            if m.category.lower() == category
        ]

    def by_extension(self, extension: str) -> list[MediaFile]:
        extension = extension.lower()
        if not extension.startswith("."):
            extension = "." + extension
        return [
            m for m in self._library
            if m.extension.lower() == extension
        ]

    def by_favorites(self) -> list[MediaFile]:
        return [m for m in self._library if m.favorite]

    def by_rejected(self, rejected: bool = True) -> list[MediaFile]:
        return [m for m in self._library if m.rejected is rejected]

    def by_imported(self) -> list[MediaFile]:
        return [m for m in self._library if m.imported]

    def by_verified(self) -> list[MediaFile]:
        return [m for m in self._library if m.verified]

    def by_resolution(self, width: int, height: int) -> list[MediaFile]:
        return [
            m for m in self._library
            if m.width == width and m.height == height
        ]
