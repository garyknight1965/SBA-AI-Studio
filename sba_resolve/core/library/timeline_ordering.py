"""
============================================================
SBA AI Studio
Timeline Ordering
Version : 4.0.0 Alpha
Sprint : ML-005
============================================================
"""

from __future__ import annotations

from datetime import datetime

from sba_resolve.core.models.media_library import MediaLibrary
from sba_resolve.core.models.media_file import MediaFile


class TimelineOrdering:

    def __init__(self, library: MediaLibrary) -> None:
        self._library = library

    def chronological(self) -> list[MediaFile]:
        return sorted(
            self._library,
            key=lambda m: (
                m.created if m.created else datetime.min,
                m.filename.lower(),
            ),
        )

    def by_camera(self) -> list[MediaFile]:
        return sorted(
            self._library,
            key=lambda m: (
                m.camera_make.lower(),
                m.camera_model.lower(),
                m.created if m.created else datetime.min,
                m.filename.lower(),
            ),
        )

    def grouped_by_day(self) -> dict[str, list[MediaFile]]:
        result: dict[str, list[MediaFile]] = {}

        for media in self.chronological():
            if media.created:
                key = media.created.strftime("%Y-%m-%d")
            else:
                key = "Unknown"

            result.setdefault(key, []).append(media)

        return result
