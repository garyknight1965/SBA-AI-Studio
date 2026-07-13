"""
============================================================
SBA AI Studio
Duplicate Detection Service
Version : 1.0.0
Sprint : ML-008B
============================================================
"""

from __future__ import annotations

from collections import defaultdict

from sba_resolve.core.models.duplicate_group import DuplicateGroup
from sba_resolve.core.models.media_file import MediaFile
from sba_resolve.core.models.media_library import MediaLibrary


class DuplicateDetectionService:
    """
    Detects duplicate media using multiple strategies.

    Current strategies:
        1. Filename + Size
        2. Capture Time + Size

    Future:
        • SHA256
        • Duration + Resolution
        • GPS
        • AI Similarity
    """

    def find_duplicates(
        self,
        library: MediaLibrary,
    ) -> list[DuplicateGroup]:

        groups: list[DuplicateGroup] = []

        groups.extend(self._filename_size(library))

        groups.extend(self._capture_time_size(library))

        return groups

    # -----------------------------------------------------

    def _filename_size(
        self,
        library: MediaLibrary,
    ) -> list[DuplicateGroup]:

        lookup: dict[str, list[MediaFile]] = defaultdict(list)

        for media in library:

            key = (
                f"{media.filename.lower()}|"
                f"{media.size}"
            )

            lookup[key].append(media)

        return [
            DuplicateGroup(key, files)
            for key, files in lookup.items()
            if len(files) > 1
        ]

    # -----------------------------------------------------

    def _capture_time_size(
        self,
        library: MediaLibrary,
    ) -> list[DuplicateGroup]:

        lookup: dict[str, list[MediaFile]] = defaultdict(list)

        for media in library:

            if media.created is None:
                continue

            key = (
                f"{media.created.isoformat()}|"
                f"{media.size}"
            )

            lookup[key].append(media)

        return [
            DuplicateGroup(key, files)
            for key, files in lookup.items()
            if len(files) > 1
        ]