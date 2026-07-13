"""
============================================================
SBA AI Studio
Media Library Service
Version : 1.0.0
Sprint : ML-008A
============================================================

High-level service responsible for importing media into the
MediaLibrary.

Pipeline

Folder
    ↓
MediaImportPipeline
    ↓
MediaLibrary
"""

from __future__ import annotations

from pathlib import Path

from sba_resolve.core.media_import_pipeline import MediaImportPipeline
from sba_resolve.core.models.media_library import MediaLibrary


class MediaLibraryService:
    """
    High-level Media Library service.

    This service is the public entry point for importing
    media into SBA AI Studio.
    """

    def __init__(self, exiftool_path: str | None = None):

        self.pipeline = MediaImportPipeline(
            exiftool_path=exiftool_path
        )

    def import_folder(
        self,
        folder: str | Path,
        progress=None,
    ) -> MediaLibrary:
        """
        Import an entire folder into a MediaLibrary.
        """

        library = MediaLibrary()

        media = self.pipeline.import_folder(
            folder,
            progress=progress,
        )

        library.add_many(media)

        library.sort_by_capture_time()

        return library

    @property
    def statistics(self):
        """
        Expose scanner statistics.
        """

        return self.pipeline.statistics